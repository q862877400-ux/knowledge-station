"""「补全分类号」——插件**自己**把没有 CCS 的文件补齐（2026-09-22，业主口径）。

════════ 为什么要有这个机制（业主原话）════════

> 「这 380 篇**不要手动去补**，我让你干的事情是**修这个知识库插件的问题**不是手动维护，
>   万一插件交付出去了你还怎么手动维护，你要找的是**修机制**，然后让插件**自己能靠自己的
>   机制完成工作**。」

⇒ 真库那 380 篇缺分类号的标准，**一篇都不许人去手改库**；产品里要有一个入口，
按一下，插件自己按修好的三层链（官方接口 → 网页抓取 → 本地兜底）逐篇补，并说清结果。

════════ 与「重来一次」（``reingest.py``）什么关系 ════════

**同一种形状，另一件事**：那边是"重新解析 PDF"（几十分钟一篇），这边是"重新查分类号"
（一篇一到几秒）。所以两边各自一份 ``_PROGRESS`` + 一把进程内锁 + 一个后台守护线程，
**不共用** —— 共用会让"解析跑着的时候补不了分类号"，而这两件事恰好都该能单独跑。

════════ 纪律（每一条都有理由）════════

1. **限速**：请求间隔取 ``CssnAdapter.PAUSE_S``（对 cssn 的礼貌速率的唯一所有者），
   每次查询自带；另外每篇之间再等一秒 —— 站点是别人家的，几百篇连打就是攻击。
2. **可中断**：``cancel`` 置一个事件，线程在**每篇之间**检查 ⇒ 点"停"就停，
   已补好的不丢、没轮到的保持原样（**不假装跑完了**，``cancelled`` 如实上报）。
3. **可重跑 / 幂等**（⚠ 2026-09-24 就地更正，留痕）：候选由 ``doc_type='standard'``
   且 ``domain_tags`` 里没有 ``CCS:`` **算出来**（不是记一份名单）。
   **错话（原文）**：「所以补全再跑一遍就是 0 篇；标签靠 ``apply_ccs_tag`` 追加，
   重复补同一个号不会写第二条。」
   **更正**：那句话**只对补到的篇成立，对没补到的篇是假的** —— 复核实测：第一次
   ``queued=1``（``not_found``）、第二次照样 ``queued=1``，且 ``checked_at`` 被改写。
   原因是候选判据只看"有没有 CCS 标签"：没补到的篇永远还是候选（``not_found`` /
   ``network_failed`` / ``parse_failed`` / ``not_applicable`` **都会重查**）——
   这正是"再点一次就能重试失败篇"的机制。补到的篇不会重进候选（除非 ``force=True``
   刷新）。⇒ 状态里的 ``missing_split`` 把这个拆开如实下发（没查过 / 查过没查到 /
   查过失败 / 不适用），界面才不会把"还剩 N 篇"说成"没补完"或"0 篇"。
   ⚠ 标签现在是 **一篇一条**（没有就加、有了就**替换**，见 ``ccs_store.apply_ccs_tag``）。
4. **失败清单如实**：三类失败（查无 / 网络失败 / 读不出）各自计数并列清单，
   **不合并成一句"部分失败"**，也不静默丢弃。**异常按类型归类**（复核 MED-1）：
   只有传输层的异常才算"网络失败"，代码缺陷**不许**冒充网络问题。
5. **同一时刻只跑一批**：拿不到锁回 ``ccs_backfill_busy``（409），**不排队**。
6. **补之前先备份（业主点名第①条）**：起线程**之前**写一份**精确回退记录**
   （``ccs_undo.write_undo_journal``，只记这一批会改的那几篇的改前样子，
   落在与快照同一个备份目录）——**写不成就一篇都不写**。一回退函数见
   ``ccs_undo.revert_ccs_backfill_journal``。
7. **说得清"还剩多少 / 为什么停"（业主点名第②条）**：``stop_reason`` 把
   "到量 / 候选扫完 / 到硬上限 / 被按停 / 一开始就没候选 / 勾选的跑完 / 出错"
   **各记各的值**（``STOP_REASON_LABELS``），**不许合并成一个"结束"**；
   ``missing_split`` 把"还剩几篇"按台账 ``outcome`` 拆开。
"""
from __future__ import annotations

import logging
import socket
import threading
import time
from datetime import datetime
from typing import Any

logger = logging.getLogger("ks.knowledge.ccs_backfill")

#: 一次最多补几篇（后台串行 + 限速；防"手一抖把 380 篇全打出去"）
MAX_BACKFILL_DOCS = 200
#: 不指定时一次补几篇（按一下按钮的合理批量；剩下的再按一次）
DEFAULT_BACKFILL_DOCS = 50
#: 每篇之间的间隔（秒）—— 与 ``resolve_ccs`` 内部的请求间隔叠加，别调成 0
DOC_PAUSE_S = 1.0
#: **「全部补完」一次的硬上限**（业主点名第③条）：到这儿就停、**如实说停在硬上限、
#: 还剩多少**，绝不假装补完。为什么要有它：真库 6417 篇标准、380 篇缺号，一篇一到几秒
#: 再加每篇 1 秒间隔 ⇒ 2000 篇 ≈ 3~5 小时。没有上限，"一次补完"就变成一个关不掉的
#: 几小时后台进程、中途出问题的损失面也大。到上限停（``hard_cap``），剩下的下次再点。
MAX_BACKFILL_ALL = 2000

# ───────────────────── 「为什么停」：各是各的值（不许合并） ─────────────────────
#
# 业主点名第②条："每批跑完后要说清为什么停"。所以这里是**七个互斥的值**，
# 不是一个 "finished"。界面的说法由后端下发（``STOP_REASON_LABELS``），
# 界面只兜底 —— 免得两个地方各写一套话、迟早说岔。
STOP_NO_CANDIDATES = "no_candidates"      # 一开始就没候选（按下去之前就没有缺号的）
STOP_EXHAUSTED = "exhausted"              # 候选扫完了（这一批没有剩余候选）
STOP_LIMIT = "limit"                      # 到了这一批的量（limit）就停
STOP_HARD_CAP = "hard_cap"                # 到了「全部补完」的硬上限就停（**不是**补完了）
STOP_SELECTED_DONE = "selected_done"      # 勾选的那几篇跑完了（全库还有别的没补）
STOP_CANCELLED = "cancelled"              # 被按停
STOP_ERROR = "error"                      # 这一批自己出错了（不是"补完了"）
STOP_REASON_LABELS: dict[str, str] = {
    STOP_NO_CANDIDATES: "一开始就没有候选（没有缺分类号的标准）",
    STOP_EXHAUSTED: "候选扫完了（这一批没有剩余候选）",
    STOP_LIMIT: "到了这一批的量就停（剩下的下次再补）",
    STOP_HARD_CAP: "到了硬上限就停（还剩没补的，不是补完了）",
    STOP_SELECTED_DONE: "勾选的那几篇跑完了（全库还有别的没补）",
    STOP_CANCELLED: "被按停（已补好的不丢，没轮到的保持原样）",
    STOP_ERROR: "这一批出错了（内部错误，不是补完了）",
}

_LOCK = threading.Lock()
_CANCEL = threading.Event()
_PROGRESS: dict[str, Any] = {
    "running": False, "total": 0, "done": 0,
    "found": 0, "not_found": 0, "network_failed": 0, "parse_failed": 0,
    "not_applicable": 0,
    "applied": 0, "skipped": 0,
    "cancel_requested": False, "cancelled": False,
    "started_at": None, "finished_at": None, "last_error": None,
    "results": [], "failures": [], "skipped_list": [],
    # 业主点名第②③条：为什么停 / 这是哪一批 / 分页到第几页 / 补前那份回退记录在哪
    "stop_reason": None, "scope": None, "force": False,
    "truncated": False, "hard_capped": False, "plan_total": 0,
    "page": 0, "pages": 0, "undo_journal": None,
}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ─────────────────────────── 候选：算出来，不记名单 ───────────────────────────

#: 「这一篇缺分类号」的判据（**唯一所有者**；``plan`` / ``status`` / ``summary`` 都从这里取）。
#: ⚠ 用 ``%"CCS:%``（带引号）而不是裸 ``%CCS:%``：``domain_tags`` 是 JSON 文本，
#: 一个 CCS 标签在里面的样子必然是 ``"CCS:…"`` —— 带引号就不会被"某个名字里恰好
#: 含 CCS: 字样"的非标签行误命中。
_MISSING_CCS_SQL = ("d.doc_type='standard'"
                    " AND (d.domain_tags IS NULL OR d.domain_tags NOT LIKE '%\"CCS:%')")


def plan_ccs_backfill(limit: int = 0, doc_ids: list[str] | None = None,
                      force: bool = False, db_path: Any = None) -> dict:
    """**只读**：这一批要补哪些篇。不写库、不联网、不起线程。

    ``doc_ids`` 给了就只在那几篇里选（界面勾选后按）；省略则全库扫（``doc_type='standard'``
    且 ``domain_tags`` 里没有 ``CCS:``）。``force=True`` 时**连已经有分类号的也重新查一遍**
    （口径变化后刷新用；标签是**替换**不是追加，别造出第二条）。

    返回 ``{"candidates": [{"doc_id","standard_no","standard_name"}...], "total": n,
    "already_have": 总数里已有分类号的篇数, "limit": …, "truncated": bool}``。
    """
    from src.core.storage.sqlite_db import get_db_connection

    lim = int(limit or 0)
    if lim < 0:
        raise ValueError("limit 不能为负")
    conn = get_db_connection(db_path)
    where = ["1=1"]
    args: list[Any] = []
    if doc_ids:
        ids = [str(d) for d in doc_ids if str(d).strip()]
        if not ids:
            raise ValueError("doc_ids 不能全是空串")
        if len(ids) > MAX_BACKFILL_DOCS:
            raise ValueError(f"一次最多 {MAX_BACKFILL_DOCS} 篇，收到 {len(ids)} 篇")
        where.append(f"d.doc_id IN ({','.join('?' * len(ids))})")
        args.extend(ids)
    if not force:
        where.append(_MISSING_CCS_SQL)
    sql = ("SELECT d.doc_id, d.standard_no, d.standard_name, d.doc_type"
           " FROM doc_meta d WHERE " + " AND ".join(where) +
           " ORDER BY d.standard_no")
    rows = [dict(r) for r in conn.execute(sql, args)]
    total = len(rows)
    hit = conn.execute(
        "SELECT COUNT(*) AS n FROM doc_meta d WHERE d.doc_type='standard'"
        " AND d.domain_tags LIKE '%\"CCS:%'").fetchone()["n"]
    truncated = False
    if lim > 0 and total > lim:
        rows = rows[:lim]
        truncated = True
    return {"candidates": rows, "total": total, "already_have": int(hit),
            "limit": lim, "truncated": truncated}


def missing_ccs_count(db_path: Any = None) -> int:
    """全库还有几篇标准没有分类号（界面显示"待补 N 篇"用；**只读**）。"""
    from src.core.storage.sqlite_db import get_db_connection
    conn = get_db_connection(db_path)
    return int(conn.execute(
        f"SELECT COUNT(*) AS n FROM doc_meta d WHERE {_MISSING_CCS_SQL}").fetchone()["n"])


def missing_ccs_split(db_path: Any = None) -> dict:
    """**"还剩几篇"拆开说**（业主点名第②条的诚实性要求；**只读、现算**）。

    只数"缺分类号的"（``_MISSING_CCS_SQL``）那一批，再按台账现状分成：

    * ``never_checked``      —— 台账里**没有这一行**：**从来没查过**；
    * ``checked_not_found``  —— ``outcome='not_found'``：查过，站点答了但都没有这个号；
    * ``checked_failed``     —— ``outcome in (network_failed, parse_failed)``：查过但**失败**
      （网络不通 / 读不出来 / 内部出错）；
    * ``not_applicable``     —— ``outcome='not_applicable'``：号不像标准号（真库那 7 篇法规），
      分类号对它**永远不适用** —— 这一桶**不能**并进"失败"（那不是失败，是本来就没有）；
    * ``found_but_untagged`` —— 台账说 ``found``、``domain_tags`` 里却没有标签
      （人工删过标签，或历史上事务不一致留下的痕迹）—— 单独一桶，免得数字对不上账。

    ⚠ **五桶之和 == total**（有一条用例钉这个恒等式）：拆开的数字必须能把 ``missing``
    解释干净，否则"还剩 N 篇"里就有几篇**谁都说不清去哪了**。
    """
    from src.core.storage.sqlite_db import get_db_connection
    conn = get_db_connection(db_path)
    row = conn.execute(
        "SELECT COUNT(*) AS total,"
        " SUM(CASE WHEN s.doc_id IS NULL THEN 1 ELSE 0 END) AS never_checked,"
        " SUM(CASE WHEN s.outcome='not_found' THEN 1 ELSE 0 END) AS checked_not_found,"
        " SUM(CASE WHEN s.outcome IN ('network_failed','parse_failed')"
        "          THEN 1 ELSE 0 END) AS checked_failed,"
        " SUM(CASE WHEN s.outcome='not_applicable' THEN 1 ELSE 0 END) AS not_applicable,"
        " SUM(CASE WHEN s.outcome='found' THEN 1 ELSE 0 END) AS found_but_untagged"
        " FROM doc_meta d LEFT JOIN doc_ccs_state s ON s.doc_id=d.doc_id"
        f" WHERE {_MISSING_CCS_SQL}").fetchone()
    return {k: int(row[k] or 0) for k in
            ("total", "never_checked", "checked_not_found", "checked_failed",
             "not_applicable", "found_but_untagged")}


# ─────────────────────── 异常归类（只有网络事故才算网络失败） ───────────────────────

#: **传输层**事故的异常类型：内置的连接/超时类型。
_NETWORK_EXC_BUILTINS: tuple[type, ...] = (ConnectionError, TimeoutError,
                                           socket.gaierror, socket.timeout)
#: 两个 HTTP 栈自己的异常**按模块名判**（``httpx`` / ``curl_cffi``）——
#: 故意不 ``import httpx``：``ccs_fetcher`` 的纪律是本模块绝不碰 httpx 的构造
#: （本机 ``NO_PROXY`` 含 ``[::1]`` 时 httpx **构造即抛** ``InvalidURL``，那正是
#: 当初"0.1 秒查无"的病根）。只比值类型，不引入依赖。
_NETWORK_EXC_MODULES: tuple[str, ...] = ("httpx", "curl_cffi")


def _is_network_exc(exc: BaseException) -> bool:
    """这个异常是不是**传输层**的（决定落台账时算不算"网络失败"）。"""
    if isinstance(exc, _NETWORK_EXC_BUILTINS):
        return True
    mod = (type(exc).__module__ or "")
    return any(mod == m or mod.startswith(m + ".") for m in _NETWORK_EXC_MODULES)


def classify_backfill_exception(exc: BaseException) -> dict:
    """一个异常 ⇒ **落库的 outcome** + 记流水的一行（复核 MED-1：按类型如实归类）。

    ⚠ 为什么"代码缺陷"落 ``parse_failed`` 而不是新造一个 outcome：``doc_ccs_state``
    的 ``outcome`` 有 ``CHECK`` 约束（``schema.sql``，真库**已建表**）——
    加第 6 个值会让**老库**写入时直接炸（``CHECK constraint failed``），
    而"纯追加、真库零迁移"是这一批的承诺。所以选**最近的那个桶**，
    但**真话写在 reason 与 attempts 里**：``layer=internal`` /
    ``result=internal_error``，审计与界面一眼能看出"这是代码缺陷，不是网络问题、
    也不是查无"。
    """
    detail = f"{type(exc).__name__}: {exc}"
    if _is_network_exc(exc):
        return {"outcome": "network_failed",
                "reason": f"补全时网络层出错（{detail}）",
                "attempt": {"layer": "transport", "keyword_form": None,
                            "result": "network_error", "detail": detail}}
    return {"outcome": "parse_failed",
            "reason": f"补全时内部出错（代码缺陷，不是网络问题、也不是查无）：{detail}",
            "attempt": {"layer": "internal", "keyword_form": None,
                        "result": "internal_error", "detail": detail}}


# ─────────────────────────── 后台跑 ───────────────────────────


def _paginate(items: list[dict], page_size: int | None = None) -> list[list[dict]]:
    """把整批切成**一页 ``MAX_BACKFILL_DOCS`` 篇**（「全部补完」按页串行跑）。

    ``page_size`` 省略时**现读** :data:`MAX_BACKFILL_DOCS`（不是 import 时绑定的默认值）
    ——否则用例/将来调参改了模块常量，分页还是老尺寸，这种"看起来改了其实没改"最难查。
    """
    size = int(page_size or MAX_BACKFILL_DOCS)
    if size <= 0:
        raise ValueError("page_size 必须为正")
    return [items[i:i + size] for i in range(0, len(items), size)]


def _wait_between(pause_s: float | None, done_n: int, total_n: int) -> None:
    """每篇之间歇一下（``pause_s`` 显式给了就用它；否则用 ``DOC_PAUSE_S``）。

    ⚠ 数的是**整批**已跑几篇（不是"这一页"）："全部补完"分页跑的时候，
    **页与页之间也要歇** —— 否则页边界就成了一个"一次性多打一篇"的缝隙。
    """
    if done_n >= total_n:
        return
    if pause_s is None:
        time.sleep(DOC_PAUSE_S)
    elif pause_s > 0:
        time.sleep(pause_s)


def _run(pages: list[list[dict]], pause_s: float | None) -> None:
    """后台线程：**分页串行**补每一篇（状态写 ``_PROGRESS`` + ``doc_ccs_state``）。

    ⚠ **整个函数体包在 try/finally 里**（复核 MED-5，2026-09-24）：循环体外的异常
    （例如 ``_update_counts`` 自己出错）以前会让 ``running`` 与 ``_LOCK`` **永久卡死**
    ——只能重启进程才能再按一次「补全分类号」。现在无论如何都会置 ``running=False``
    并放锁，并把"为什么停"如实记成 ``error``（**不是**"补完了"）。
    """
    from src.core.knowledge import ccs_store
    from src.core.knowledge.ccs_fetcher import ccs_to_tag, resolve_ccs

    total_n = sum(len(p) for p in pages)
    done_n = 0
    try:
        for page_no, page in enumerate(pages, start=1):
            _PROGRESS["page"] = page_no
            for it in page:
                if _CANCEL.is_set():
                    _PROGRESS["cancelled"] = True
                    _PROGRESS["skipped_list"].append(
                        {"doc_id": it["doc_id"], "standard_no": it["standard_no"],
                         "reason": "还没轮到就按了停"})
                    _PROGRESS["skipped"] += 1
                    continue
                doc_id = it["doc_id"]
                no = str(it.get("standard_no") or "")
                rec: dict[str, Any] = {"doc_id": doc_id, "standard_no": no,
                                       "standard_name": it.get("standard_name")}
                try:
                    # 幂等护栏：线程跑起来之后这一篇可能已被别处补上了（重复点、并发端点）
                    from src.core.storage.sqlite_db import get_db_connection
                    row = get_db_connection().execute(
                        "SELECT domain_tags FROM doc_meta WHERE doc_id=?",
                        (doc_id,)).fetchone()
                    if row is None:
                        raise ValueError("文档不在库里了")
                    if ccs_store.ccs_tag_of(row["domain_tags"]) and not it.get("force"):
                        rec.update({"outcome": "skipped",
                                    "reason": "已经有分类号了（跳过）"})
                        _PROGRESS["skipped"] += 1
                        _PROGRESS["skipped_list"].append(rec)
                        _PROGRESS["results"].append(rec)
                        _PROGRESS["done"] = len(_PROGRESS["results"])
                        _update_counts(rec)
                        continue
                    got = resolve_ccs(no, str(it.get("standard_name") or ""),
                                      pause_s=pause_s)
                    rec.update({"outcome": got.get("outcome"), "code": got.get("code"),
                                "sub": got.get("sub"), "source": got.get("source"),
                                "keyword_form": got.get("keyword_form"),
                                "matched_no": got.get("matched_no"),
                                "reason": got.get("reason"),
                                "n_attempts": len(got.get("attempts") or [])})
                    if got.get("outcome") == "found":
                        tag = ccs_to_tag(got, no)
                        if not tag:
                            # 链说命中了、却拼不出标签：这是**代码缺陷**，如实记失败，不许静默
                            rec.update({"outcome": "parse_failed",
                                        "reason": "查到了分类号但拼不出标签（内部不一致）"})
                            ccs_store.record_ccs_lookup(doc_id, {
                                "outcome": "parse_failed", "source": got.get("source"),
                                "keyword_form": got.get("keyword_form"),
                                "matched_no": got.get("matched_no"),
                                "code": got.get("code"), "sub": got.get("sub"),
                                "reason": rec["reason"], "attempts": got.get("attempts")})
                        else:
                            res = ccs_store.apply_ccs_tag(doc_id, tag, result=got)
                            rec["tag"] = tag
                            rec["applied"] = res["applied"]
                            rec["replaced"] = res.get("replaced")
                            _PROGRESS["applied"] += int(bool(res["applied"]))
                    else:
                        ccs_store.record_ccs_lookup(doc_id, got)
                except Exception as exc:                     # noqa: BLE001
                    # **按异常类型如实归类**（复核 MED-1）：只有传输层的事故才算网络失败，
                    # 代码缺陷落 parse_failed 桶、真话写进 reason 与 attempts（见
                    # classify_backfill_exception 的理由）。
                    cls = classify_backfill_exception(exc)
                    logger.warning("补分类号失败 doc=%s outcome=%s", doc_id,
                                   cls["outcome"], exc_info=True)
                    rec.update({"outcome": cls["outcome"], "reason": cls["reason"],
                                "internal_error": bool(cls["outcome"] != "network_failed")})
                    _PROGRESS["last_error"] = f"{no or doc_id}：{cls['reason']}"
                    try:
                        ccs_store.record_ccs_lookup(doc_id, {
                            "outcome": cls["outcome"], "reason": cls["reason"],
                            "attempts": [cls["attempt"]]})
                    except Exception:                        # noqa: BLE001
                        logger.warning("台账也写不进去 doc=%s", doc_id, exc_info=True)
                _PROGRESS["results"].append(rec)
                _PROGRESS["done"] = len(_PROGRESS["results"])
                _update_counts(rec)
                if rec.get("outcome") != "found":
                    _PROGRESS["failures"].append(rec)
                    if not _PROGRESS.get("last_error"):
                        _PROGRESS["last_error"] = (
                            f"{no or doc_id}：{rec.get('reason') or rec.get('outcome')}")
                done_n += 1
                _wait_between(pause_s, done_n, total_n)
    except Exception as exc:                                 # noqa: BLE001
        # 循环体外的异常（复核实测的那条路）：**如实记"出错"**，不许冒充"补完了"
        logger.error("补全分类号这一批自己出错了", exc_info=True)
        _PROGRESS["stop_reason"] = STOP_ERROR
        _PROGRESS["last_error"] = f"这一批自己出错了（{type(exc).__name__}: {exc}）"
    finally:
        # ⚠ 无论如何：说清为什么停 + 置 running 假 + 放锁（MED-5）
        if _PROGRESS.get("stop_reason") is None:
            _PROGRESS["stop_reason"] = _decide_stop_reason()
        _PROGRESS["running"] = False
        _PROGRESS["finished_at"] = _now()
        _release()


def _decide_stop_reason() -> str:
    """**为什么停**（取**一个**值，按优先级；各是各的值，不合并成"结束"）。

    优先级 = 谁更"具体"谁说话：``error``（异常路径自己设，不走这里）
    > ``cancelled``（有人按了停）> ``hard_cap``（"全部补完"撞了硬上限）
    > ``limit``（这一批到量）> ``selected_done``（勾选的跑完）> ``exhausted``。
    """
    if _PROGRESS.get("cancelled"):
        return STOP_CANCELLED
    if _PROGRESS.get("hard_capped"):
        return STOP_HARD_CAP
    if _PROGRESS.get("scope") == "selected":
        return STOP_SELECTED_DONE
    if _PROGRESS.get("truncated"):
        return STOP_LIMIT
    return STOP_EXHAUSTED


def _update_counts(rec: dict) -> None:
    key = str(rec.get("outcome") or "")
    if key in ("found", "not_found", "network_failed", "parse_failed",
               "not_applicable"):
        _PROGRESS[key] += 1


def _release() -> None:
    try:
        _LOCK.release()
    except RuntimeError:                                    # 理论上到不了
        logger.warning("补全锁释放异常（可能已被释放）")


def _reset_progress(*, total: int, scope: str, force: bool, truncated: bool,
                    hard_capped: bool, plan_total: int,
                    undo_journal: str | None) -> None:
    _PROGRESS.update({
        "running": bool(total), "total": total, "done": 0,
        "found": 0, "not_found": 0, "network_failed": 0, "parse_failed": 0,
        "not_applicable": 0,
        "applied": 0, "skipped": 0, "cancel_requested": False, "cancelled": False,
        "started_at": _now(), "finished_at": None, "last_error": None,
        "results": [], "failures": [], "skipped_list": [],
        "stop_reason": None, "scope": scope, "force": bool(force),
        "truncated": bool(truncated), "hard_capped": bool(hard_capped),
        "plan_total": int(plan_total), "page": 0, "pages": 0,
        "undo_journal": undo_journal})


def start_ccs_backfill(doc_ids: list[str] | None = None,
                       limit: int = DEFAULT_BACKFILL_DOCS,
                       force: bool = False, pause_s: float | None = None,
                       db_path: Any = None, all_docs: bool = False) -> dict:
    """起一批「补全分类号」：**立刻**返回，进度看 :func:`ccs_backfill_status`。

    * ``limit``（默认 :data:`DEFAULT_BACKFILL_DOCS` = 50 篇）—— 一批补几篇；
    * ``all_docs=True`` —— **「全部补完」**（业主点名第③条）：内部**按
      :data:`MAX_BACKFILL_DOCS` 一页一页串行**跑，直到没有候选或撞上硬上限
      :data:`MAX_BACKFILL_ALL`；到上限就**如实说停在硬上限、还剩多少**，不假装补完。
      与 ``doc_ids`` **不能同时用**（"全部"与"只补勾选的这几篇"是两件事，勾选本来
      就 ≤200 篇）；
    * ``force=True`` —— 连已经有分类号的也重查（**刷新**；标签是**替换**不是追加）。

    ⚠ **补之前先写一份精确回退记录**（``ccs_undo.write_undo_journal``，一批一份，
    落在与快照同一个备份目录）：写不成 ⇒ 抛 ``ccs_undo_failed``、**这一批一篇都不写**。
    一篇候选都没有时**不写**记录（没有要改的东西，不制造空文件）。

    返回 ``{queued, started, skipped, plan, undo_journal, pages, hard_capped}``；
    已有批次在跑 ⇒ ``RuntimeError("ccs_backfill_busy")``（路由映射成 409）。
    """
    if all_docs and doc_ids:
        raise ValueError("「全部补完」与「只补勾选的这几篇」不能同时用")
    if not _LOCK.acquire(blocking=False):
        raise RuntimeError("ccs_backfill_busy")
    try:
        plan = plan_ccs_backfill(limit=(0 if all_docs else limit), doc_ids=doc_ids,
                                 force=force, db_path=db_path)
        cands = list(plan["candidates"])
        hard_capped = False
        if all_docs and len(cands) > MAX_BACKFILL_ALL:
            cands = cands[:MAX_BACKFILL_ALL]
            hard_capped = True
        items = [{**c, "force": bool(force)} for c in cands]
        scope = "selected" if doc_ids else ("all" if all_docs else "library")
        undo_path: str | None = None
        if items:
            from src.core.knowledge import ccs_undo
            undo = ccs_undo.write_undo_journal(
                items, scope=scope, force=force,
                limit=(0 if all_docs else limit), db_path=db_path)
            undo_path = undo["path"]
        pages = _paginate(items)
        _CANCEL.clear()
        _reset_progress(total=len(items), scope=scope, force=force,
                        truncated=(False if all_docs else bool(plan["truncated"])),
                        hard_capped=hard_capped, plan_total=plan["total"],
                        undo_journal=undo_path)
        if not items:
            # 一开始就没候选：**不许**说成"跑完了/补完了"，如实给 no_candidates
            _PROGRESS["stop_reason"] = STOP_NO_CANDIDATES
            _PROGRESS["finished_at"] = _now()
            _release()
            return {"queued": 0, "started": [], "skipped": [], "plan": plan,
                    "undo_journal": None, "pages": 0, "hard_capped": False}
        _PROGRESS["pages"] = len(pages)
        threading.Thread(target=_run, args=(pages, pause_s), daemon=True,
                         name="ks-ccs-backfill").start()
        return {"queued": len(items),
                "started": [{"doc_id": c["doc_id"], "standard_no": c["standard_no"]}
                            for c in items],
                "skipped": [], "plan": plan, "undo_journal": undo_path,
                "pages": len(pages), "hard_capped": hard_capped}
    except Exception:
        # 起不来（参数错/查库错/**回退记录写不成**）⇒ 释放锁，别把「补全分类号」永久锁死
        if _LOCK.locked():
            _release()
        raise


def cancel_ccs_backfill() -> dict:
    """按"停"：置中断标志（线程在**每篇之间**检查）。已补好的不丢。

    返回 ``{"cancel_requested": True, "running": …, "done": …, "total": …}`` ——
    **不许**在还没真停下来时说"已停止"。
    """
    _CANCEL.set()
    _PROGRESS["cancel_requested"] = True
    return {"cancel_requested": True, "running": bool(_PROGRESS.get("running")),
            "done": _PROGRESS.get("done"), "total": _PROGRESS.get("total")}


def ccs_backfill_status(db_path: Any = None) -> dict:
    """最近一批的进度（**如实**：running/done/total + 逐篇结果 + 失败清单 + 为什么停）。

    ``missing`` 是**现算的**"全库还缺几篇"（补完之后它自己会降，不靠进度计数器对齐），
    并按业主点名第②条**拆开**成 ``missing_split``（没查过 / 查过没查到 / 查过失败 /
    不适用 / 台账说补到了却没标签）。

    ``stop_reason`` + ``stop_reason_label`` 说清**这一批为什么停**（各是各的值）；
    ``undo_journal`` 是**补前那份精确回退记录的路径**（没有做过就是 None）——
    要退回改前，把它交给 ``ccs_undo.revert_ccs_backfill_journal``。
    """
    snap = dict(_PROGRESS, results=list(_PROGRESS.get("results", [])),
                failures=list(_PROGRESS.get("failures", [])),
                skipped_list=list(_PROGRESS.get("skipped_list", [])))
    snap["stop_reason_label"] = STOP_REASON_LABELS.get(
        str(snap.get("stop_reason") or ""), None)
    snap["max_batch"] = MAX_BACKFILL_DOCS
    snap["default_batch"] = DEFAULT_BACKFILL_DOCS
    snap["max_all"] = MAX_BACKFILL_ALL
    try:
        snap["missing"] = missing_ccs_count(db_path)
        snap["missing_split"] = missing_ccs_split(db_path)
    except Exception as e:                                  # noqa: BLE001
        snap["missing"] = None
        snap["missing_split"] = None
        snap["missing_error"] = f"{type(e).__name__}: {e}"
    return snap
