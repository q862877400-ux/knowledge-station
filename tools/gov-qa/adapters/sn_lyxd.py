"""适配器：**陕西省·我向省长说句话·留言选登**（静态列表 + 静态明细）。

## 站点形态（2026-10-08 实探，证据 recon/tj-sn-cq-hunt.txt / recon/sn-list.html）
 · 栏目「互动 → 我向省长说句话 → 留言选登」`https://www.shaanxi.gov.cn/hd/wxszsjh/lyxd/`；
 · 列表条目（10 条/页，服务端渲染）：
   ```
   <li class="clearfix cur">
     <p class="w740 f-ib lf h40"><a class="f-otw" href="./202609/t20260924_3698666.html">标题</a></p>
     <span class="w140 lf">渭南市政府</span>          ← 回复单位
     <span class="w120s f-tac lf">2026-09-22</span>   ← 处理时间
     <span class="w100 f-tac lf">已办结</span>        ← 状态
   </li>
   ```
 · 翻页：`createPage(29, 0, "index", "html")` ⇒ 共 29 页，第 N 页 `index_{N-1}.html`
   （实测 `index_1.html` = 第 2 页，与第 1 页无交集）。
 · 明细：正文由**两个 `<div class="question-box">`** 组成——
   ① `提问`（`<span class="ask">提问</span>` + 来信时间）→ `<div class="quest-cont">` 内为问题；
   ② `回答`（`<span class="ask answer">回答</span>` + 回复单位 + 回复时间）→ 内容为答复。
   ⇒ 按 `question-box` 切块，块内含 `class="ask answer"` 的即答复块。
"""
from __future__ import annotations

import re
import time
from urllib.parse import urljoin

SITE = {
    "key": "sn-lyxd",
    "name": "陕西省·我向省长说句话·留言选登",
    "kind": "static",
    "level": "province",
    "entry": "https://www.shaanxi.gov.cn/hd/wxszsjh/lyxd/",
    "status": "ok",
    "note": "静态列表 10 条/页（createPage 29 页）+ 静态明细；提问/回答两块结构",
}

BASE = "https://www.shaanxi.gov.cn"
LIST_BASE = BASE + "/hd/wxszsjh/lyxd/"
PAUSE = 1.5

LI_RE = re.compile(r'<li class="clearfix[^"]*">(.*?)</li>', re.S)
LINK_RE = re.compile(r'<a class="f-otw"\s+href="([^"]+)"[^>]*>\s*(.*?)\s*</a>', re.S)
DEPT_RE = re.compile(r'<span class="w140 lf">\s*(.*?)\s*</span>', re.S)
DATE_RE = re.compile(r'<span class="w120s f-tac lf">\s*(.*?)\s*</span>', re.S)
STATUS_RE = re.compile(r'<span class="w100 f-tac lf">\s*(.*?)\s*</span>', re.S)
COUNT_RE = re.compile(r"createPage\((\d+),\s*\d+,")
TITLE_RE = re.compile(r'<div class="titContent[^"]*">(.*?)</div>', re.S)
BOX_RE = re.compile(r'<div class="question-box">')
VIEW_RE = re.compile(r'<div class="view TRS_UEDITOR[^"]*">(.*?)</div>', re.S)
ASKED_RE = re.compile(r"来信时间[：:]\s*<span>\s*([^<]+?)\s*</span>")
DEPT_D_RE = re.compile(r"回复单位[：:]\s*<span>\s*([^<]+?)\s*</span>")
ANSAT_RE = re.compile(r"回复时间[：:]\s*<span>\s*([^<]+?)\s*</span>")
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<script.*?</script>|<style.*?</style>", re.S | re.I)


def _text(html: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", SCRIPT_RE.sub(" ", html))).strip()


def _view(block: str) -> str:
    m = VIEW_RE.search(block)
    return _text(m.group(1)) if m else ""


def _parse_detail(html: str) -> dict | None:
    parts = BOX_RE.split(html)
    if len(parts) < 2:
        return None
    #: 逐块判定：带 `class="ask answer"` 的是答复块，其余第一个是提问块。
    qblk = ablk = None
    for blk in parts[1:]:
        if 'class="ask answer"' in blk:
            if ablk is None:
                ablk = blk
        elif qblk is None:
            qblk = blk
    if qblk is None or ablk is None:
        return None
    question = _view(qblk)
    answer = _view(ablk)
    if len(question) < 4 or len(answer) < 10:
        return None
    tm = TITLE_RE.search(html)
    am = ASKED_RE.search(qblk)
    dm = DEPT_D_RE.search(ablk)
    rm = ANSAT_RE.search(ablk)
    return {"question": question[:300], "answer": answer,
            "asked_at": am.group(1) if am else None,
            "answered_at": rm.group(1) if rm else None,
            "dept": dm.group(1) if dm else None,
            "title": _text(tm.group(1)) if tm else ""}


def harvest(fetch, *, limit: int | None = None, max_pages: int = 40) -> list[dict]:
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
        html = r.text or ""
        items = []
        for blk in LI_RE.findall(html):
            m = LINK_RE.search(blk)
            if not m:
                continue
            dm = DATE_RE.search(blk)
            sm = DEPT_RE.search(blk)
            st = STATUS_RE.search(blk)
            items.append((urljoin(LIST_BASE, m.group(1)), _text(m.group(2)),
                          _text(dm.group(1)) if dm else None,
                          _text(sm.group(1)) if sm else None,
                          _text(st.group(1)) if st else None))
        fresh = [it for it in items if it[0] not in seen]
        print(f"    [{SITE['key']}] 第 {p}/{pages} 页：条目 {len(items)}，新增 {len(fresh)}")
        if not fresh:
            continue
        for url, title, ansdate, dept, status in fresh:
            if limit and len(out) >= limit:
                return out[:limit]
            seen.add(url)
            time.sleep(PAUSE)
            d = fetch(url)
            if getattr(d, "status_code", 0) != 200:
                continue
            rec = _parse_detail(d.text or "")
            if not rec:
                continue
            uid = url.rsplit("/", 1)[-1].replace(".html", "")
            out.append({
                "source": SITE["key"],
                "id": uid,
                "url": url,
                "question": rec["question"] or title,
                "answer": rec["answer"],
                "asked_at": rec["asked_at"],
                "answered_at": rec["answered_at"] or ansdate,
                "dept": rec["dept"] or dept,
                "channel": "互动·我向省长说句话·留言选登",
                "extra": {"title": rec["title"] or title, "page": p,
                          "status": status,
                          "answer_kind": "办理答复（留言选登，少点名依据）"},
            })
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
