"""适配器：**海南省人民政府 · 政策问答**（接口型）。

## 形态判断（2026-10-08 实探，证据 recon/heb-hi-hunt.txt）
海南省政府门户是 **Hanweb/万户站群 CMS**。互动 → 政策问答
（`/hainan/zcwd/zcwd.shtml`）的列表由前端 JS 走接口拉取，接口从栏目页内联脚本抠出：

 · 列表：`POST https://www.hainan.gov.cn/u/search/ajaxlist?channel_id=<频道>`
     form：`searchWord=""`、`curPage`（**0 基页码**）、`PageSize`
     （必须带 `Referer: https://www.hainan.gov.cn/hainan/zcwd/zcwd.shtml`）
     → `{page:{allRow, totalPage, currentPage, pageSize,
              list:[{title, url, memo, published_time, ...}]}}`
 · 明细：静态页 `https://www.hainan.gov.cn<hainan/url>`，正文用自定义标签
     `<UCAPTITLE>问题</UCAPTITLE>` / `<UCAPCONTENT>答复</UCAPCONTENT>`；
     meta 辅助：`ColumnName`=**答复部门**、`PubDate`=发布日、`Description`=memo。
   ⚠ `memo` 只是**截断**的答复摘要，**必须抓明细页**取答复全文（答复常点名依据）。

本适配器即「政策问答」这一问答频道（channel_id 固定）；实测 allRow=**2243**。
"""
from __future__ import annotations

import re
import time

SITE = {
    "key": "hi-zcwd",
    "name": "海南省人民政府·政策问答",
    "kind": "api",
    "level": "province",
    "entry": "https://www.hainan.gov.cn/hainan/zcwd/zcwd.shtml",
    "status": "ok",
    "note": "万户站群 ajaxlist（channel_id=政策问答，2243 条）；明细 UCAPCONTENT 答复全文",
}

HOST = "https://www.hainan.gov.cn"
LIST_URL = HOST + "/u/search/ajaxlist"
CHANNEL_ID = "41996292c8494145865bc7aafe48a9b1"      # 「政策问答」频道
REFERER = HOST + "/hainan/zcwd/zcwd.shtml"
PAGE_SIZE = 30
PAUSE = 1.5

TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<script.*?</script>|<style.*?</style>", re.S | re.I)
QTITLE_RE = re.compile(r"<UCAPTITLE>(.*?)</UCAPTITLE>", re.S)
QCONTENT_RE = re.compile(r"<UCAPCONTENT>(.*?)</UCAPCONTENT>", re.S)
COLUMN_RE = re.compile(r'<meta\s+name="ColumnName"\s+content="([^"]*)"')
PUBDATE_RE = re.compile(r'<meta\s+name="PubDate"\s+content="([^"]*)"')


def _text(html: str | None) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", SCRIPT_RE.sub(" ", html or ""))).strip()


def _parse_detail(html: str, item: dict) -> dict | None:
    tm = QTITLE_RE.search(html)
    cm = QCONTENT_RE.search(html)
    answer = _text(cm.group(1)) if cm else ""
    if not answer:
        return None
    question = _text(tm.group(1)) if tm else (item.get("title") or "")
    if not question:
        question = item.get("title") or ""
    if len(question) < 4 or len(answer) < 10:
        return None
    col = COLUMN_RE.search(html)
    pub = PUBDATE_RE.search(html)
    return {
        "question": question[:300],
        "answer": answer,
        "dept": (col.group(1).strip() if col else None) or None,
        "asked_at": (pub.group(1).strip() if pub else None) or item.get("published_time"),
    }


def harvest(fetch, *, limit: int | None = None, max_pages: int = 200) -> list[dict]:
    """按 curPage 翻页取政策问答列表，再逐条抓明细（按 URL 去重）。"""
    out: list[dict] = []
    seen: set[str] = set()
    total_pages = None
    for page in range(max_pages):
        if limit and len(out) >= limit:
            break
        r = fetch.post(
            LIST_URL, params={"channel_id": CHANNEL_ID},
            data={"searchWord": "", "curPage": str(page), "PageSize": str(PAGE_SIZE)},
            headers={"Referer": REFERER, "X-Requested-With": "XMLHttpRequest"},
        )
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page + 1} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        try:
            page_obj = (r.json().get("page") or {})
        except Exception as e:                                          # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page + 1} 页解析失败 {type(e).__name__}（停）")
            break
        items = page_obj.get("list") or []
        if not items:
            break
        if total_pages is None:
            total_pages = page_obj.get("totalPage")
            print(f"    [{SITE['key']}] 自报 allRow={page_obj.get('allRow')} "
                  f"totalPage={total_pages}")
        fresh = 0
        for it in items:
            if limit and len(out) >= limit:
                return out[:limit]
            url = it.get("url") or ""
            if not url:
                continue
            if url.startswith("/"):
                url = HOST + url
            if url in seen:
                continue
            seen.add(url)
            time.sleep(PAUSE)
            d = fetch(url)
            if getattr(d, "status_code", 0) != 200:
                continue
            rec = _parse_detail(d.text or "", it)
            if not rec:
                continue
            uid = url.rsplit("/", 1)[-1].replace(".shtml", "")
            out.append({
                "source": SITE["key"],
                "id": uid,
                "url": url,
                "question": rec["question"],
                "answer": rec["answer"],
                "asked_at": rec["asked_at"],
                "answered_at": None,
                "dept": rec["dept"],
                "channel": "互动交流·政策问答",
                "extra": {"title": it.get("title"), "page": page + 1,
                          "memo": it.get("memo"),
                          "channel_id": CHANNEL_ID,
                          "answer_kind": "政策答复（常点名依据）"},
            })
            fresh += 1
        print(f"    [{SITE['key']}] 第 {page + 1}/{total_pages or '?'} 页："
              f"条目 {len(items)}，收 {fresh}")
        if total_pages and page + 1 >= total_pages:
            break
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
