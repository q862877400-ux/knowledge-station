"""适配器：**河北省财政厅 · 互动交流 · 群众信箱**（静态型，小体量）。

## 站点形态（2026-10-08 实测，证据 recon/heb-czt-qzxx-list.html / -detail.html）
 · 栏目 `http://czt.hebei.gov.cn/hdjl/qzxx/index.html`；
 · 每页顶部是**写信表单**、下方才是「留言回复列表」——**务必只在该标题后的
   第一个 `<ul>` 里取条目**，否则会把上方「受理情况统计」的统计表链接也算进来（踩过）。
 · 条目：`<li class="clearfix"><span class="t ..."><a href="./YYYYMM/tYYYYMMDD_ID.html"
   title="问题">…</a></span><span class="dt">日期</span></li>`。
 · 翻页：内联 JS `countPage=4`；第 1 页 `index.html`，第 N 页 `index_{N-1}.html`。
   实测 4 页共 **26** 条（8+8+8+2）。
 · 明细：`<div class="c_title">问题</div>`；`.c_subtitle` = 留言时间/答复时间/答复单位；
   `.c_content` 表内「答复结果:」后的 `<td>` = **答复**（同行「信息内容:」多为
   「内容已隐藏」，不取）。
"""
from __future__ import annotations

import re
import time

SITE = {
    "key": "heb-czt",
    "name": "河北省财政厅·群众信箱",
    "kind": "static",
    "level": "province",
    "entry": "http://czt.hebei.gov.cn/hdjl/qzxx/index.html",
    "status": "ok",
    "note": "静态列表(4 页)+静态明细；实测 26 条；须按『留言回复列表』块取条目",
}

BASE = "http://czt.hebei.gov.cn"
LIST_BASE = BASE + "/hdjl/qzxx/"
PAUSE = 1.5

COUNT_RE = re.compile(r"countPage\s*=\s*(\d+)")
ITEM_RE = re.compile(r'<li class="clearfix">(.*?)</li>', re.S)
LINK_RE = re.compile(r'<a href="([^"]+)"[^>]*title="([^"]*)"')
DATE_RE = re.compile(r'<span class="dt">\s*([0-9\-]+)\s*</span>')
TITLE_RE = re.compile(r'<div class="c_title">(.*?)</div>', re.S)
SUB_RE = re.compile(r'<div class="c_subtitle">(.*?)</div>', re.S)
ANSWER_RE = re.compile(r"答复结果[:：]\s*</td>\s*<td[^>]*>(.*?)</td>", re.S)
ASKED_RE = re.compile(r"留言时间[：:]\s*([0-9]{4}年[0-9]{2}月[0-9]{2}日|[0-9\-]{8,10})")
ANSWERED_RE = re.compile(r"答复时间[：:]\s*([0-9\-]{8,10})")
DEPT_RE = re.compile(r"答复单位[：:]\s*([^\s<]+)")
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<script.*?</script>|<style.*?</style>", re.S | re.I)


def _text(html: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", SCRIPT_RE.sub(" ", html))).strip()


def _norm_date(s: str | None) -> str | None:
    """`2026年09月29日` → `2026-09-29`；已是 `2026-10-08` 原样返回。"""
    if not s:
        return None
    m = re.match(r"(\d{4})年(\d{2})月(\d{2})日", s)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else s


def _block_items(html: str) -> list[tuple[str, str, str | None]]:
    """只在『留言回复列表』标题后的第一个 <ul> 里取 (href, title, date)。"""
    i = html.find("留言回复列表")
    seg = html[i:] if i >= 0 else html
    m = re.search(r"<ul>(.*?)</ul>", seg, re.S)
    out: list[tuple[str, str, str | None]] = []
    for blk in ITEM_RE.findall(m.group(1) if m else ""):
        lm = LINK_RE.search(blk)
        if not lm:
            continue
        dm = DATE_RE.search(blk)
        out.append((lm.group(1), lm.group(2), dm.group(1) if dm else None))
    return out


def _parse_detail(html: str, fallback_title: str | None = None) -> dict | None:
    tm = TITLE_RE.search(html)
    q = _text(tm.group(1)) if tm else (fallback_title or "")
    am = ANSWER_RE.search(html)
    a = _text(am.group(1)) if am else ""
    if len(q) < 4 or len(a) < 4:
        return None
    sm = SUB_RE.search(html)
    sub = _text(sm.group(1)) if sm else ""
    dm = DEPT_RE.search(sub)
    return {
        "question": q,
        "answer": a,
        "asked_at": _norm_date((ASKED_RE.search(sub) or [None, None])[1]),
        "answered_at": (ANSWERED_RE.search(sub) or [None, None])[1],
        "dept": dm.group(1) if dm else None,
        "title": q,
    }


def harvest(fetch, *, limit: int | None = None, max_pages: int = 20) -> list[dict]:
    """翻完所有列表页，逐条取明细（按 URL 去重）。"""
    out: list[dict] = []
    seen: set[str] = set()

    r = fetch(LIST_BASE + "index.html")
    if getattr(r, "status_code", 0) != 200:
        print(f"    [{SITE['key']}] 首页 HTTP {getattr(r, 'status_code', '?')}（停）")
        return out
    cm = COUNT_RE.search(r.text or "")
    pages = min(int(cm.group(1)) if cm else 1, max_pages)

    for p in range(1, pages + 1):
        if limit and len(out) >= limit:
            break
        if p > 1:
            time.sleep(PAUSE)
            r = fetch(LIST_BASE + f"index_{p - 1}.html")
            if getattr(r, "status_code", 0) != 200:
                print(f"    [{SITE['key']}] 列表第 {p} 页 HTTP "
                      f"{getattr(r, 'status_code', '?')}（停）")
                break
        items = _block_items(r.text or "")
        fresh = [it for it in items if it[0] not in seen]
        print(f"    [{SITE['key']}] 第 {p}/{pages} 页：条目 {len(items)}，新增 {len(fresh)}")
        for href, title, pub in fresh:
            if limit and len(out) >= limit:
                return out[:limit]
            seen.add(href)
            url = href if href.startswith("http") else LIST_BASE + href.lstrip("./")
            time.sleep(PAUSE)
            d = fetch(url)
            if getattr(d, "status_code", 0) != 200:
                continue
            rec = _parse_detail(d.text or "", title)
            if not rec:
                continue
            uid = url.rsplit("/", 1)[-1].replace(".html", "")
            out.append({
                "source": SITE["key"],
                "id": uid,
                "url": url,
                "question": rec["question"],
                "answer": rec["answer"],
                "asked_at": rec["asked_at"] or pub,
                "answered_at": rec["answered_at"],
                "dept": rec["dept"],
                "channel": "互动交流·群众信箱",
                "extra": {"title": rec["title"], "page": p,
                          "answer_kind": "办理答复（群众信箱，少点名依据）"},
            })
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
