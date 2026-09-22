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
3. **可重跑 / 幂等**：候选由 ``doc_type='standard' 且 domain_tags 里没有 CCS:`` **算出来**
   （不是记一份名单），所以补全再跑一遍就是 0 篇；标签靠 ``apply_ccs_tag`` 追加，
   重复补同一个号不会写第二条。
4. **失败清单如实**：三类失败（查无 / 网络失败 / 读不出）各自计数并列清单，
   **不合并成一句"部分失败"**，也不静默丢弃。
5. **同一时刻只跑一批**：拿不到锁回 ``ccs_backfill_busy``（409），**不排队**。
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime
from typing import Any

logger = logging.getLogger("ks.knowledge.ccs_backfill")

#: 一次最多补几篇（后台串行 + 限速；防"手一抖把 380 篇全打出去"）
MAX_BACKFILL_DOCS = 200
#: 不指定时一次补几篇（按一下按钮的合理批量；剩下的再按一次）
DEFAULT_BACKFILL_DOCS = 50
#: 每篇之间的间隔（秒）—— 与 ``resolve_ccs`` 内部的请求间隔叠加，别调成 0
DOC_PAUSE_S = 1.0

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
}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ─────────────────────────── 候选：算出来，不记名单 ───────────────────────────

#: 「这一篇缺分类号」的判据（**唯一所有者**；``plan`` 与 ``status`` 都从这里取）。
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
    （口径变化后刷新用）。

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


# ─────────────────────────── 后台跑 ───────────────────────────


def _run(items: list[dict], pause_s: float | None) -> None:
    """后台线程：串行补每一篇（状态写 ``_PROGRESS`` + ``doc_ccs_state``）。"""
    import time

    from src.core.knowledge import ccs_store
    from src.core.knowledge.ccs_fetcher import ccs_to_tag, resolve_ccs

    for idx, it in enumerate(items):
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
            state = ccs_store.get_ccs_state(doc_id)
            from src.core.storage.sqlite_db import get_db_connection
            row = get_db_connection().execute(
                "SELECT domain_tags FROM doc_meta WHERE doc_id=?", (doc_id,)).fetchone()
            if row is None:
                raise ValueError("文档不在库里了")
            if ccs_store.ccs_tag_of(row["domain_tags"]) and not it.get("force"):
                rec.update({"outcome": "skipped", "reason": "已经有分类号了（跳过）"})
                _PROGRESS["skipped"] += 1
                _PROGRESS["skipped_list"].append(rec)
                _PROGRESS["results"].append(rec)
                _PROGRESS["done"] = len(_PROGRESS["results"])
                _update_counts(rec)
                continue
            got = resolve_ccs(no, str(it.get("standard_name") or ""), pause_s=pause_s)
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
                    _PROGRESS["applied"] += int(bool(res["applied"]))
            else:
                ccs_store.record_ccs_lookup(doc_id, got)
        except Exception as exc:                             # noqa: BLE001
            logger.warning("补分类号失败 doc=%s", doc_id, exc_info=True)
            rec.update({"outcome": "network_failed",
                        "reason": f"补全中断（{type(exc).__name__}: {exc}）"})
            try:
                ccs_store.record_ccs_lookup(doc_id, {
                    "outcome": "network_failed", "reason": rec["reason"]})
            except Exception:                                # noqa: BLE001
                logger.warning("台账也写不进去 doc=%s", doc_id, exc_info=True)
        _PROGRESS["results"].append(rec)
        _PROGRESS["done"] = len(_PROGRESS["results"])
        _update_counts(rec)
        if rec.get("outcome") != "found":
            _PROGRESS["failures"].append(rec)
        if pause_s is None and idx + 1 < len(items):
            time.sleep(DOC_PAUSE_S)
        elif pause_s is not None and pause_s > 0 and idx + 1 < len(items):
            time.sleep(pause_s)
    _PROGRESS["running"] = False
    _PROGRESS["finished_at"] = _now()
    _release()


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


def start_ccs_backfill(doc_ids: list[str] | None = None, limit: int = DEFAULT_BACKFILL_DOCS,
                       force: bool = False, pause_s: float | None = None,
                       db_path: Any = None) -> dict:
    """起一批「补全分类号」：**立刻**返回，进度看 :func:`ccs_backfill_status`。

    ``{queued, started:[{doc_id, standard_no}], skipped:[{doc_id, reason}],
    plan:{total, already_have, truncated}}``；已有批次在跑 ⇒
    ``RuntimeError("ccs_backfill_busy")``（路由映射成 409）。
    """
    if not _LOCK.acquire(blocking=False):
        raise RuntimeError("ccs_backfill_busy")
    try:
        plan = plan_ccs_backfill(limit=limit, doc_ids=doc_ids, force=force,
                                db_path=db_path)
        items = [{**c, "force": bool(force)} for c in plan["candidates"]]
        _CANCEL.clear()
        _PROGRESS.update({
            "running": bool(items), "total": len(items), "done": 0,
            "found": 0, "not_found": 0, "network_failed": 0, "parse_failed": 0,
            "not_applicable": 0,
            "applied": 0, "skipped": 0, "cancel_requested": False, "cancelled": False,
            "started_at": _now(), "finished_at": None, "last_error": None,
            "results": [], "failures": [], "skipped_list": []})
        if not items:
            _release()
            return {"queued": 0, "started": [], "skipped": [], "plan": plan}
        threading.Thread(target=_run, args=(items, pause_s), daemon=True,
                         name="ks-ccs-backfill").start()
        return {"queued": len(items),
                "started": [{"doc_id": c["doc_id"], "standard_no": c["standard_no"]}
                            for c in plan["candidates"]],
                "skipped": [], "plan": plan}
    except Exception:
        # 起不来（参数错/查库错）⇒ 释放锁，别把「补全分类号」永久锁死
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
    """最近一批的进度（**如实**：running/done/total + 逐篇结果 + 失败清单）。

    额外带上"全库还缺几篇"（``missing``）——那是**现算的**，所以补完之后它自己会降，
    不靠进度计数器对齐。
    """
    snap = dict(_PROGRESS, results=list(_PROGRESS.get("results", [])),
                failures=list(_PROGRESS.get("failures", [])),
                skipped_list=list(_PROGRESS.get("skipped_list", [])))
    try:
        snap["missing"] = missing_ccs_count(db_path)
    except Exception as e:                                  # noqa: BLE001
        snap["missing"] = None
        snap["missing_error"] = f"{type(e).__name__}: {e}"
    return snap
