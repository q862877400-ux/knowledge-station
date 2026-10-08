"""适配器：**新疆维吾尔自治区·互联网+督查·督查回声**（静态列表 + 静态明细）。

## 站点事实（2026-10-08 实测，证据 recon/xj-xz-sd-gx-qh-hunt.txt 【新疆】）
 · 信访线**未通**：门户「政民互动」把问答指向信访域名 `wsxf.xjxfj.gov.cn`，但
   `queryIndex.jsp` 是**查询表单**（要姓名+查询码+验证码），`onlineILsit.jsp`/`getLetterList.action`
   需登录（实测 `checkLogon` 返回 `logonFlag:'false'`，`getLetterList` 返回空
   `{"letterList":[],...}`）；首页只有「来信反馈」通知列表（无问答正文）。
 · ★ **门户另有公开问答**：`www.xinjiang.gov.cn/xinjiang/hlwdc/hlwdc.shtml`
   （自治区「互联网+督查」平台）的「督查回声」栏目
   `/xinjiang/dchs/common_list.shtml` —— 群众留言 + 政府办理结果公开稿。
 · 分页：`createPageHTML('page-div',23, 1,'common_list','shtml',227)` ⇒ **23 页 / 227 条**；
   页 1 = `common_list.shtml`，页 N（N≥2）= `common_list_{N}.shtml`
   （⚠ 实测 `common_list_1.shtml` **404**，页 2 从 `common_list_2.shtml` 起，别用 `_1`）。
 · 明细 `/xinjiang/dchs/YYYYMM/<32位hex>.shtml`：
   · 标题（meta `ArticleTitle` / `<title>`）=「群众反映…问题{单位}…{办理结果}」；
   · 正文在 `<div id="NewsContent"> … </div>`（无嵌套 div），含「群众反映…问题。…收到留言后，
     督促…核查办理。…」；
   · 日期 `p.yyyy`+`p.mmdd`+`p.hhmm`；来源 `p.source`（多为「自治区人民政府督查室」）。
"""
from __future__ import annotations

import html as _html
import re
import time
from urllib.parse import urljoin

SITE = {
    "key": "xj-dchs",
    "name": "新疆维吾尔自治区·互联网+督查·督查回声",
    "kind": "static",
    "level": "province",
    "entry": "https://www.xinjiang.gov.cn/xinjiang/dchs/common_list.shtml",
    "status": "ok",
    "note": "门户督查回声静态列表（23 页/227 条）+ 静态明细；信访线需登录未通",
}

BASE = "https://www.xinjiang.gov.cn"
LIST1 = BASE + "/xinjiang/dchs/common_list.shtml"
PAUSE = 1.5

LINK_RE = re.compile(r'href="(/xinjiang/dchs/\d{6}/[0-9a-f]{32}\.shtml)"[^>]*>([^<]{4,}?)</a>')
PAGES_RE = re.compile(r"createPageHTML\('[^']*',\s*(\d+),")
TITLE_META_RE = re.compile(r'name="ArticleTitle"\s+content="([^"]*)"')
TITLE_RE = re.compile(r"<title>(.*?)_")
NEWSCONTENT_RE = re.compile(r'id="NewsContent"[^>]*>(.*?)</div>', re.S)
SRC_RE = re.compile(r'<p class="source">(.*?)</p>', re.S)
YYYY_RE = re.compile(r'<p class="yyyy">(.*?)</p>', re.S)
MMDD_RE = re.compile(r'<p class="mmdd">(.*?)</p>', re.S)
HHMM_RE = re.compile(r'<p class="hhmm">(.*?)</p>', re.S)
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<script.*?</script>|<style.*?</style>", re.S | re.I)
#: 块级/换行标签 ⇒ 空白；其余（span/font 等**内联**标签）⇒ 直接删（否则「群众反映」会被
#: 逐字插空格成「群 众 反 映」——本页正文用 <span><font> 逐段包字，实测踩过）
BLOCK_RE = re.compile(r"</(?:p|div|li|tr|td|th|h[1-6]|ul|ol|table|section|article)>|<br\s*/?>",
                      re.I)


def _text(html: str | None) -> str:
    raw = (html or "").replace("&nbsp;", " ").replace("\u00a0", " ")
    raw = _html.unescape(raw)
    raw = SCRIPT_RE.sub(" ", raw)
    raw = BLOCK_RE.sub(" ", raw)
    return re.sub(r"\s+", " ", TAG_RE.sub("", raw)).strip()


def _page_url(n: int) -> str:
    return LIST1 if n == 1 else BASE + f"/xinjiang/dchs/common_list_{n}.shtml"


def _parse_detail(html: str) -> dict | None:
    cm = NEWSCONTENT_RE.search(html)
    answer = _text(cm.group(1)) if cm else ""
    if len(answer) < 15:
        return None
    tm = TITLE_META_RE.search(html) or TITLE_RE.search(html)
    question = _text(tm.group(1)) if tm else ""
    src = SRC_RE.search(html)
    y, m, d = YYYY_RE.search(html), MMDD_RE.search(html), HHMM_RE.search(html)
    date = None
    if y and m:
        date = f"{_text(y.group(1))}-{_text(m.group(1)).replace('/', '-')}"
    return {"question": question, "answer": answer,
            "dept": _text(src.group(1)) if src else None,
            "answered_at": date}


def harvest(fetch, *, limit: int | None = None, max_pages: int = 30) -> list[dict]:
    """翻完督查回声列表页，逐条取明细（按明细 URL 去重）。"""
    out: list[dict] = []
    seen: set[str] = set()

    r = fetch(LIST1)
    if getattr(r, "status_code", 0) != 200:
        print(f"    [{SITE['key']}] 首页 HTTP {getattr(r, 'status_code', '?')}（停）")
        return out
    pm = PAGES_RE.search(r.text or "")
    pages = min(int(pm.group(1)) if pm else 1, max_pages)

    for n in range(1, pages + 1):
        if limit and len(out) >= limit:
            break
        if n > 1:
            time.sleep(PAUSE)
            r = fetch(_page_url(n))
            if getattr(r, "status_code", 0) != 200:
                print(f"    [{SITE['key']}] 列表第 {n} 页 HTTP "
                      f"{getattr(r, 'status_code', '?')}（跳过）")
                continue
        html = r.text or ""
        items: dict[str, str] = {}
        for href, title in LINK_RE.findall(html):
            t = _text(title)
            if href not in items or len(t) > len(items[href]):
                items[href] = t
        fresh = [(u, t) for u, t in items.items() if u not in seen]
        print(f"    [{SITE['key']}] 第 {n}/{pages} 页：条目 {len(items)}，新增 {len(fresh)}")
        for href, title in fresh:
            if limit and len(out) >= limit:
                return out[:limit]
            seen.add(href)
            time.sleep(PAUSE)
            d = fetch(urljoin(BASE, href))
            if getattr(d, "status_code", 0) != 200:
                continue
            rec = _parse_detail(d.text or "")
            if not rec:
                continue
            uid = href.rsplit("/", 1)[-1].replace(".shtml", "")
            out.append({
                "source": SITE["key"],
                "id": uid,
                "url": urljoin(BASE, href),
                "question": rec["question"] or title,
                "answer": rec["answer"],
                "asked_at": None,
                "answered_at": rec["answered_at"],
                "dept": rec["dept"],
                "channel": "互联网+督查·督查回声",
                "extra": {"title": rec["question"] or title, "page": n,
                          "answer_kind": "办理答复（督查回声，群众留言+政府办理结果）"},
            })
    print(f"    [{SITE['key']}] 收 {len(out)} 条（站内自报 227）")
    return out
