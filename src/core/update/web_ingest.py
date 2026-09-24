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
    if re.search(r"公告|通知|通告|批复|函", t):
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

    res = ingest_law_text(text, title, title,
                          legal_hierarchy=classify_hierarchy(title),
                          effective_from=published_date,
                          doc_type="法律法规",
                          source_marker=f"web://{urlsplit(url).netloc}",
                          source_url=url,
                          legal_status=out["legal_status"],
                          fallback_single_clause=True)
    out["ingest"] = res
    if res.get("status") == "error":
        out.update({"status": "failed", "reason": f"law_text_error: {res.get('message', '')[:100]}"})
    else:
        out["status"] = "ingested"
    upd_log(trace_id, "web_ingest", "INFO", "announcement_ingest",
            url=url, legal_status=out["legal_status"], chars=out["chars"],
            result=res.get("status"))
    return out
