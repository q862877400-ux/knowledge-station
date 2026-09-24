"""部委公告/规章 → 知识库**正文**入库（切片②，开发史 §10.189 / §10.190）。

**只做这一件事**：给一条"已发现的公告"（标题 + 链接 + 发布日期），
抓详情页 → 抽正文 → 判效力档 → 调 `law_text.ingest_law_text()` 入库（带来源 URL 溯源）。

**不重复做**（各有其规范所有者，别再写第二份）：
- 翻页发现与去重 → `src/core/update/announce.py`（本模块接收它发现的条目）；
- 条款切分 / 分型 / 建边 / 单事务原子入库 → `src/core/ingestion/law_text.py`；
- 分类号补全 → CCS 那条线。

**效力档的判定只在这一处**（`classify_status`）：
- 标题含「征求意见 / 草案 / 公开征求」⇒ `reference`（**参考资料 / 仅参考**）。
  ⚠ 2026-09-24 业主要求原文："**征求意见稿也要入库**，只是效力层级是参考资料，不是强制执行的那种"。
  所以它是**要入库的**，只是效力档落在"仅参考"那一档（`doc_meta.legal_status` 的枚举里
  因此多了 `reference` 一个值 —— 见 `sqlite_db._ensure_legal_status_reference` 的幂等迁移）。
  ⇒ 展示、导出、引用都必须说清"仅参考、不是现行依据"。
- 标题含「废止 / 失效 / 作废」⇒ `withdrawn`。
- 其余（令 / 公告 / 通知 / 办法 / 规定 …）⇒ `effective`。
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit

from src.core.ingestion.law_text import ingest_law_text
from src.core.update.channels.base import upd_log

#: 征求意见稿（**仅参考**，见模块 docstring 与 §10.189 切片③）
_DRAFT_RE = re.compile(r"征求意见|草案|公开征求")
#: 废止类
_WITHDRAWN_RE = re.compile(r"废止|失效|作废")

#: 详情页正文容器（政府站常见写法；按优先级找）。只需匹配**开标签**，内容用配对括号切。
_CONTENT_OPEN = (
    re.compile(r'<div[^>]+(?:id|class)="[^"]*(?:TRS_Editor|zoom|article-content|content-body|'
               r'view|detail)[^"]*"[^>]*>', re.S | re.I),
    re.compile(r"<article[^>]*>", re.S | re.I),
)
_DIV_TAG_RE = re.compile(r"</?div\b", re.I)
_SCRIPT_RE = re.compile(r"<(script|style|noscript)\b.*?</\1>", re.S | re.I)
_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)
_BLOCK_END_RE = re.compile(r"(?i)</(p|div|h[1-6]|li|tr|section|article)>|<br\s*/?>")
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t\u3000]+")
_MULTI_NL_RE = re.compile(r"\n{3,}")
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)


def _inner_html(html: str, open_match: re.Match) -> str:
    """取开标签之后**配对**的那一段（`<div>` 会嵌套，非贪婪正则会切到别的地方去）。"""
    start = open_match.end()
    if open_match.group(0).lower().startswith("<article"):
        end = html.lower().find("</article>", start)
        return html[start:end if end >= 0 else len(html)]
    depth = 1
    for m in _DIV_TAG_RE.finditer(html, start):
        if m.group(0).startswith("</"):
            depth -= 1
            if depth == 0:
                return html[start:m.start()]
        else:
            depth += 1
    return html[start:]


def classify_status(title: str) -> str:
    """标题 → 效力档：`reference`（参考资料/仅参考）/ `withdrawn` / `effective`。

    ⚠ 顺序有讲究：先判"征求意见稿"——因为「关于征求《XX办法（修订征求意见稿）》意见的通知」
    这类标题里同时会出现"办法"（像生效件）与"征求意见稿"，必须先认后者。
    """
    t = title or ""
    if _DRAFT_RE.search(t):
        return "reference"
    if _WITHDRAWN_RE.search(t):
        return "withdrawn"
    return "effective"


def classify_hierarchy(title: str) -> str:
    """标题 → 法规树那一档（尽力而为，认不出落"其他"；不猜"法律/行政法规"那种高位阶）。

    ⚠ 返回值必须是**库内既有词汇**（`doc_catalog._HIER_TO_TIER` 那一套），否则法规树会把它
    兜到"未定级"——部令就该写 `部门规章`（先前写的是 "规章"，映射表里没有这个词）。
    """
    t = title or ""
    if _DRAFT_RE.search(t):
        # 草案**没有生效位阶**：单列一档，别冒充它将来可能的位阶
        # （冒充了就成了"把征求意见稿当规章用"，正是业主要避免的那种误导）。
        return "征求意见稿"
    if re.search(r"人民政府令|地方政府规章", t):
        return "地方政府规章"
    if re.search(r"部令|总局令|委员会令|第[一二三四五六七八九十百\d]+号令", t):
        return "部门规章"
    if re.search(r"办法|规定|细则|规程", t):
        return "规范性文件"
    # 真机补（2026-09-24）：部委公告里还有一大批「通报 / 指导意见 / 实施意见 / 决定 / 方案 /
    # 规划 / 纲要 / 目标任务」——它们**都是部门规范性文件/政策文件**，落到"其他"会在法规树里
    # 显示成"未定级"（真机实测 84 篇挤在那儿）。归 `规范性文件` 比"未定级"更准。
    if re.search(r"公告|通知|通告|批复|函|通报|意见|决定|方案|规划|纲要|要点|任务", t):
        return "规范性文件"
    return "其他"


def extract_body_text(html: str) -> str:
    """详情页 HTML → 正文纯文本（去脚本/样式/注释，优先内容容器，其次全页文本）。"""
    if not html:
        return ""
    h = _COMMENT_RE.sub("", _SCRIPT_RE.sub("", html))
    body = ""
    for pat in _CONTENT_OPEN:
        m = pat.search(h)
        if m is None:
            continue
        inner = _inner_html(h, m)
        # ⚠ 阈值别定高：短的公告整篇正文可能只有几十字（实测两条"第X条"合起来才 ~60 字），
        #   定高了会把真容器判掉、退回"整页文本"（导航/页脚就跟着进来了）。
        if len(_TAG_RE.sub("", inner).strip()) > 20:
            body = inner
            break
    if body == "":
        # 兜底：去掉头尾导航/页脚后取正文（政府站把内容放在 <body> 里，导航占比不大）
        body = h
    body = _BLOCK_END_RE.sub("\n", body)
    text = _TAG_RE.sub("", body)
    text = text.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    text = _WS_RE.sub(" ", text)
    lines = [ln.strip() for ln in text.split("\n")]
    return _MULTI_NL_RE.sub("\n\n", "\n".join(ln for ln in lines if ln != "")).strip()


def page_title(html: str) -> str:
    """详情页 `<title>`（抓不到返回空串）——用于和列表页标题交叉核对。"""
    m = _TITLE_RE.search(html or "")
    return re.sub(r"\s+", " ", _TAG_RE.sub("", m.group(1))).strip() if m else ""


# ---------------------------------------------------------------- 入库范围（该不该进库）
#: **不入库**的类别（业主要的是"法规/标准/征求意见稿"这类能当依据或参考的东西）。
#: 前三个是业主 2026-09-24 **亲自点名**的（部门决算/公示/挂牌督办）；后面几个是我按同一口径
#: 补的**同类**（都是"跟法规标准无关的行政事务"）——补的理由是：真机跑下来 536 条待入库里
#: 有一批是委员人选征集、督察整改报告这类，进库只会把效力报告和检索搅浑。
#: ⚠ 清单再宽就会踩回**他正在抱怨的那个毛病**（该入库的被过滤掉）⇒ 只收"整类都不是法规标准"的，
#:   凡是拿不准的一律**留**（第 3 步的默认是 normative）。
_NON_NORMATIVE = ("决算", "预算", "公示", "挂牌督办", "督察", "整改", "征集", "人选",
                  "年度报告", "工作报告", "报表", "表彰", "招聘", "招标", "中标")
#: **强规范性线索**：命中就**无条件保留**（压过上面的排除词）。
#: 例：「关于公开征求《XX办法》意见的公示」含"公示"，但它正是业主说"应该入库"的征求意见稿；
#:    「XX标准报批前公示」含"公示"，而它正是标准正文的来源。
_STRONG_CUES = ("征求", "草案", "标准", "规范", "规程", "办法", "规定", "条例", "细则",
                "通则", "导则", "目录", "令", "法典", "法律", "行政法规")


def classify_scope(title: str) -> str:
    """标题 → `normative`（要入库）/ `non_normative`（与法规标准无关的行政事务，不入库）。

    ⚠ 判序**不可颠倒**：① 强规范性线索 → 留；② 排除词 → 不入；③ 其余 → **留**（默认留）。
    "默认留"是刻意的：这个函数的作用是"别把该入库的放过"，误留的代价（库里多几篇通知）
    远小于误杀的代价（业主又要问一次"怎么又没入库"）。
    """
    t = title or ""
    if any(c in t for c in _STRONG_CUES):
        return "normative"
    if any(w in t for w in _NON_NORMATIVE):
        return "non_normative"
    return "normative"


def _observed_rows(limit: int | None = None, source_id: str | None = None) -> list[dict]:
    """`announcement_observed`（已发现的公告）按发布日期 DESC（新的在前）取行。"""
    sql = ("SELECT o.observed_id, o.source_id, o.source_name, o.title, o.url, o.published_date"
           " FROM announcement_observed o")
    args: list[Any] = []
    if source_id:
        sql += " WHERE o.source_id=?"
        args.append(source_id)
    sql += (" ORDER BY CASE WHEN o.published_date IS NULL THEN 1 ELSE 0 END,"
            " o.published_date DESC, o.first_seen DESC, o.observed_id DESC")
    if limit is not None:
        sql += " LIMIT ?"
        args.append(max(1, int(limit)))
    from src.core.storage.sqlite_db import get_db_connection
    return [dict(r) for r in get_db_connection().execute(sql, args).fetchall()]


def _library_keys() -> tuple[set[str], set[str]]:
    """库里已经有的**来源 URL** 与**标准号（存储形）**两把钥匙。

    为什么两把都要：`ingest_law_text` 有两条"不动库"的返回 —— `duplicate`（正文哈希相同）
    与 `standard_exists`（标准号相同但正文不同）。只按 URL 判"入没入库"的话，
    `standard_exists` 那些行**永远留在待入库里**（每次都被重新抓一遍、永远不落库），
    而调用方会把它当成"入库成功"—— 实测就是这么把 372 篇报成 478 篇的（§10.193）。
    ⚠ 标题那一把要按 `ingest_law_text` 的**存储形**折过（`store_standard_no`：全角 `／`/`－` 折半角），
    与真正决定"插不插"的那层**同口径**；否则「…办法／规定…」与「…办法/规定…」
    会被判成两条、无限重试（那把尺子差一点点，代价就是永远抓不完）。
    """
    from src.core.storage.sqlite_db import get_db_connection
    rows = get_db_connection().execute(
        "SELECT source_url, standard_no FROM doc_meta").fetchall()
    urls = {r[0] for r in rows if r[0]}
    nos = {r[1] for r in rows if r[1]}
    return urls, nos


def _is_in_library(row: dict, urls: set[str], nos: set[str]) -> bool:
    from src.core.text_utils import store_standard_no
    return row["url"] in urls or store_standard_no(row.get("title") or "") in nos


def pending_rows(limit: int | None = None, source_id: str | None = None,
                 include_non_normative: bool = False) -> list[dict]:
    """已发现但**正文还没进库**的公告。

    "进没进库"的判据：`doc_meta.source_url`（本 URL 已入）**或** `doc_meta.standard_no`
    （同标题的文档已在库里 —— 那时 `ingest_law_text` 会回 `standard_exists`、根本不会插新的）。
    **不另立一份标记表**：两份真值必然漂移，判据要与真正决定"插不插"的那层同口径。
    """
    urls, nos = _library_keys()
    out = []
    for row in _observed_rows(source_id=source_id):
        if _is_in_library(row, urls, nos):
            continue
        if not include_non_normative and classify_scope(row.get("title") or "") != "normative":
            continue
        out.append(row)
        if limit is not None and len(out) >= limit:
            break
    return out


def ingest_summary(source_id: str | None = None) -> dict:
    """入库进度总览（给界面显示"还有多少条没进库"，**不抓网页**）。

    分档计数按 `classify_status` 的**标题判定**给（真正入库时要抓正文，这里只报计划）。
    """
    rows = _observed_rows(source_id=source_id)
    urls, nos = _library_keys()
    pending = {"effective": 0, "reference": 0, "withdrawn": 0}
    skipped_non_normative = 0
    for row in rows:
        if _is_in_library(row, urls, nos):
            continue
        if classify_scope(row.get("title") or "") != "normative":
            skipped_non_normative += 1
            continue
        pending[classify_status(row.get("title") or "")] += 1
    return {
        "total": len(rows),
        "ingested": len(rows) - sum(pending.values()) - skipped_non_normative,
        "pending": sum(pending.values()),
        "pending_by_status": pending,
        "skipped_non_normative": skipped_non_normative,
    }


def triage_pending(source_id: str | None = None, limit: int = 200) -> dict:
    """给"规则判不收、但要不要真清"的那批**分档**（2026-09-24 B2）。

    ⚠ **只读**：不删库、不改库、不抓正文，只回一份清/灰/留的清单。
    真正删除是业主的决定——本函数只提供判据与理由（`web_ingest.classify_scope` 的命中词
    + Jev 的 choice/confidence），**替不了他拍板**。

    - `clear`：Jev 判 admin 且 `confidence ≥ 0.90`（确证是行政事务）；
    - `review`：0.70~0.90 灰区 ⇒ **交人看，不动**；
    - `keep`：其余（含规范、变更信号、置信度不足的 admin）⇒ 留着。

    Jev 不可用 ⇒ 全部落 `keep`（按规则原样处理，绝不因外部服务挂了就误清）。
    """
    from src.core.update import jev_ingest

    n = max(1, min(int(limit or 200), 500))
    urls, nos = _library_keys()          # ⚠ 算一次就够：每行重算会在大库上白扫两次全表
    rows = [r for r in _observed_rows(source_id=source_id)
            if not _is_in_library(r, urls, nos)
            and classify_scope(r.get("title") or "") != "normative"][:n]
    verdicts = jev_ingest.judge_many([r.get("title") or "" for r in rows])
    out: list[dict] = []
    counts = {jev_ingest.CLEAR: 0, jev_ingest.REVIEW: 0, jev_ingest.KEEP: 0}
    for row in rows:
        title = row.get("title") or ""
        v = verdicts.get(title)
        verdict = (v or {}).get("verdict") or jev_ingest.KEEP
        counts[verdict] += 1
        out.append({"title": title, "url": row.get("url"),
                    "published_date": row.get("published_date"),
                    "verdict": verdict,
                    "choice": (v or {}).get("choice"),
                    "confidence": (v or {}).get("confidence"),
                    "change_signal": (v or {}).get("change")})
    return {"total": len(rows), "counts": counts, "items": out}


#: 单次批量入库的**时间预算**（秒）：到点停下、把"还没做完"如实报回去，绝不把请求挂死。
#: （前端可以再点一次；每次调用都报 `pending_left`，所以进度是看得见的。）
INGEST_BUDGET_S = 45.0
#: 单次批量条数上限（防一次点下去抓几百页）。
INGEST_BATCH_MAX = 20


def ingest_pending(limit: int = 10, source_id: str | None = None, *, transport: Any = None,
                   budget_s: float = INGEST_BUDGET_S, force: bool = False,
                   trace_id: str = "-") -> dict:
    """把已发现的公告**批量入正文库**（业主报的"应该入库的没入库"就靠它收口）。

    - 只抓**还没入库**的（判据 = `doc_meta.source_url` 或同标题的 `standard_no`），新的在前；
    - `force=True` 连"业主点名的非规范性类别"也入（逃生口，防我给的范围判错时卡死他）；
    - 单次受 `budget_s` 与 `limit`（≤ `INGEST_BATCH_MAX`）双重封顶：到点就停，
      `stopped_early=True` + `pending_left` 告诉还剩多少 —— **不假装做完了**；
    - 每条的结果原样带上（`status` / `reason` / `legal_status`），**失败与跳过都不静默**；
      同一次调用里**同一个 URL 只抓一次**（跨源重复的条目只处理第一条）。
    """
    import time as _time

    from src.core.update import announce  # 延迟导入：避免与 announce 层循环依赖

    n = max(1, min(int(limit or 10), INGEST_BATCH_MAX))
    rows = pending_rows(limit=None, source_id=source_id, include_non_normative=force)
    tp = transport if transport is not None else announce.default_transport()
    started = _time.monotonic()
    items: list[dict] = []
    counts = {"ingested": 0, "skipped": 0, "failed": 0}
    by_status = {"effective": 0, "reference": 0, "withdrawn": 0}
    stopped_early = False
    seen_urls: set[str] = set()
    for row in rows:
        if len(items) >= n:
            stopped_early = True       # 是 limit 挡下的（下面把 stopped_early 归因说清）
            break
        if _time.monotonic() - started > budget_s:
            stopped_early = True
            break
        if row["url"] in seen_urls:
            # 同一次调用里同一个 URL 只抓一次（同一条公告可能挂在两个源下）
            items.append({"url": row["url"], "title": row.get("title"), "status": "skipped",
                          "reason": "duplicate_url_in_batch"})
            counts["skipped"] += 1
            continue
        seen_urls.add(row["url"])
        # 范围判定再来一次（`force=True` 时不挡）—— 与 `pending_rows` 同一判据，不写第二份
        if not force and classify_scope(row.get("title") or "") != "normative":
            items.append({"url": row["url"], "title": row.get("title"), "status": "skipped",
                          "reason": "not_normative"})
            counts["skipped"] += 1
            continue
        res = ingest_announcement(row.get("title") or "", row["url"],
                                  published_date=row.get("published_date"),
                                  source_name=row.get("source_name") or "",
                                  transport=tp, trace_id=trace_id)
        items.append({k: res.get(k) for k in ("url", "title", "status", "reason",
                                              "legal_status", "chars")})
        # `status` 只有 ingested / skipped / failed 三种（`ingest_announcement` 的返回形状）
        key = res.get("status")
        if key in counts:
            counts[key] += 1
        st = res.get("legal_status")
        if key == "ingested" and st in by_status:
            by_status[st] += 1
    left = len(pending_rows(source_id=source_id, include_non_normative=force))
    upd_log(trace_id, "web_ingest", "INFO", "batch_ingest_done",
            tried=len(items), **counts, pending_left=left, stopped_early=stopped_early)
    # ⚠ `stopped_early` 的**归因**要说清：这批是"抓满了 limit"还是"时间到了"。
    #    前者不是坏事（再点一次就继续），后者说明该缩批次；两者都不许说成"做完了"。
    return {"tried": len(items), **counts, "by_status": by_status,
            "pending_left": left, "stopped_early": stopped_early,
            "stop_reason": ("limit" if stopped_early and len(items) >= n
                            else "budget" if stopped_early else None),
            "items": items}


def ingest_announcement(title: str, url: str, *, published_date: str | None = None,
                        source_name: str = "", transport: Any = None,
                        trace_id: str = "-") -> dict:
    """抓一条公告的详情页 → 抽正文 → 入库。返回**如实**的结果字典（不抛、不静默）。

    返回形状：`{status, url, title, legal_status, reason?, chars?, ingest?}`
    - `status="ingested"` 正常入库（`ingest` 是 `ingest_law_text` 的原始返回）；
    - `status="skipped"` + `reason`：`empty_body`（正文太短，取不到内容）；
    - `status="failed"` + `reason`：`http_404` / `fetch_failed` / `law_text_error: …`。
    """
    from src.core.update import announce  # 延迟导入：避免与 announce 层循环依赖

    out: dict[str, Any] = {"url": url, "title": title, "legal_status": classify_status(title)}
    tp = transport if transport is not None else announce.default_transport()
    try:
        status, body = tp.fetch(url, timeout=announce.PAGE_TIMEOUT_S)
    except Exception as exc:  # noqa: BLE001 — 单条失败不拖垮批量
        out.update({"status": "failed", "reason": f"fetch_failed: {str(exc)[:120]}"})
        return out
    if status != 200 or not isinstance(body, str):
        out.update({"status": "failed", "reason": f"http_{status}"})
        return out

    text = extract_body_text(body)
    out["chars"] = len(text)
    if len(text) < 40:
        out.update({"status": "skipped", "reason": "empty_body"})
        return out

    # ⚠ `standard_no` 传**存储形**（`store_standard_no`：全角 `／`/`－` 折半角）：
    #    `ingest_law_text` 的查重按存储形比对（§11.0 R6c-3d），而**落库也是这个值** ——
    #    传原始标题的话，"查重折过、落库没折"两边不同口径 ⇒ 同一条公告的不同写法
    #    （`办法／规定` vs `办法/规定`）会被插成**两篇**。
    from src.core.text_utils import store_standard_no

    stored_no = store_standard_no(title)
    res = ingest_law_text(text, stored_no, title,
                          legal_hierarchy=classify_hierarchy(title),
                          effective_from=published_date,
                          doc_type="法律法规",
                          source_marker=f"web://{urlsplit(url).netloc}",
                          source_url=url,
                          legal_status=out["legal_status"],
                          fallback_single_clause=True)
    out["ingest"] = res
    # ⚠ **如实区分三种"没插新文档"**（2026-09-24 真机跑出来的缺陷，见 §10.193）：
    #    `ingest_law_text` 只在真插了新文档时返回 `inserted`/`ok` 之类；
    #    `duplicate`（正文哈希相同）与 `standard_exists`（标准号相同、正文不同）**一个新行都没插**。
    #    先前这里把所有非 error 都写成 `ingested` ⇒ 真机 372 篇被报成 478 篇
    #    （差额 = 反复重抓那些**根本插不进去**的行）。
    kind = res.get("status")
    if kind == "error":
        out.update({"status": "failed", "reason": f"law_text_error: {res.get('message', '')[:100]}"})
    elif kind in ("duplicate", "standard_exists"):
        out.update({"status": "skipped", "reason": "already_in_library", "ingest_kind": kind})
    else:
        out["status"] = "ingested"
    upd_log(trace_id, "web_ingest", "INFO", "announcement_ingest",
            url=url, legal_status=out["legal_status"], chars=out["chars"],
            result=res.get("status"), status=out["status"])
    return out
