"""适配器：**天津市·政民互动·留言选登**（静态列表 + 静态明细）。

## 站点形态（2026-10-08 实探，证据 recon/tj-sn-cq-hunt.txt / recon/tj-list.html）
 · 栏目「政民互动 → 留言选登」`https://www.tj.gov.cn/zmhd/wmfkxd/index.html`；
 · 列表条目**不是 `href`**，而是 `onclick`：
   ```
   <a href="javascript:void(0)"
      onclick="jumpToDetail('https://www.tj.gov.cn/zmhd/wmfkxd/202610/t20261008_7389167.html')"
      title='栖仙温泉公寓预计10月份进行管道置换接通燃气'>…</a>
   <span class="list-item-date">2026-10-08</span>
   ```
   ⇒ 明细 URL 只能从 `onclick` 里取（**照旧印象写 `href=` 正则会 0 命中**）。
 · 翻页：CMS 分页脚本 `countPage: parseInt('25}'), PAGE_NAME: 'index', PAGE_EXT: 'html'`
   ⇒ 第 1 页 `index.html`，第 N 页 `index_{N-1}.html`（实测 `index_1.html` = 第 2 页，
   与第 1 页无交集）。共 25 页 × 20 条/页。
 · 明细正文：`<div class="trs_editor_view …">` 内**两个 `<p>`**——
   第 1 段 `…网民“X”留言：{问题}`，第 2 段 `{回复单位}回复：{答复}`。
   ⇒ 用「留言：」「回复：」两个标记切段取问答。
"""
from __future__ import annotations

import re
import time

SITE = {
    "key": "tj-hdjl",
    "name": "天津市·政民互动·留言选登",
    "kind": "static",
    "level": "province",
    "entry": "https://www.tj.gov.cn/zmhd/wmfkxd/index.html",
    "status": "ok",
    "note": "静态列表（onclick jumpToDetail）+ 静态明细；分页 index_N.html（25 页）；问/答在正文两段",
}

BASE = "https://www.tj.gov.cn"
LIST_BASE = BASE + "/zmhd/wmfkxd/"
PAUSE = 1.5

ITEM_RE = re.compile(r'<div class="list-item clear">(.*?)</div>', re.S)
LINK_RE = re.compile(r"onclick=\"jumpToDetail\('([^']+)'\)\"\s*title='([^']*)'")
DATE_RE = re.compile(r'<span class="list-item-date">\s*([0-9]{4}-[0-9]{2}-[0-9]{2})\s*</span>')
COUNT_RE = re.compile(r"countPage:\s*parseInt\('(\d+)")
TITLE_RE = re.compile(r'<div class="qt-title">(.*?)</div>', re.S)
PUB_RE = re.compile(r"发布时间[：:]\s*([0-9]{4}-[0-9]{2}-[0-9]{2}(?:\s+[0-9:]{4,5})?)")
BODY_RE = re.compile(r'<div class="trs_editor_view[^"]*">(.*?)</div>', re.S)
P_RE = re.compile(r"<p[^>]*>(.*?)</p>", re.S)
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<script.*?</script>|<style.*?</style>", re.S | re.I)


def _text(html: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", SCRIPT_RE.sub(" ", html))).strip()


def _parse_detail(html: str, fallback_title: str | None = None) -> dict | None:
    """从明细页取 问题 / 答复 / 回复单位 / 发布时间。"""
    body = BODY_RE.search(html)
    paras = [_text(p) for p in P_RE.findall(body.group(1) if body else html)]
    q = a = dept = None
    for t in paras:
        if "回复：" in t and a is None:
            pre, ans = t.split("回复：", 1)
            a = ans.strip()
            if "留言：" in pre:                      # 问答挤在同一段（少见）
                q = pre.split("留言：", 1)[1].strip()
            else:
                dept = pre.strip() or None
        elif q is None and "留言：" in t:
            q = t.split("留言：", 1)[1].strip()
    if not q or not a:
        return None
    if len(q) < 4 or len(a) < 10:
        return None
    tm = TITLE_RE.search(html)
    title = _text(tm.group(1)) if tm else (fallback_title or "")
    pub = PUB_RE.search(_text(html))
    return {"question": q[:300], "answer": a,
            "asked_at": pub.group(1) if pub else None,
            "dept": dept, "title": title}


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
        for blk in ITEM_RE.findall(html):
            m = LINK_RE.search(blk)
            if not m:
                continue
            dm = DATE_RE.search(blk)
            items.append((m.group(1), m.group(2), dm.group(1) if dm else None))
        fresh = [it for it in items if it[0] not in seen]
        print(f"    [{SITE['key']}] 第 {p}/{pages} 页：条目 {len(items)}，新增 {len(fresh)}")
        if not fresh:
            continue
        for url, title, pub in fresh:
            if limit and len(out) >= limit:
                return out[:limit]
            seen.add(url)
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
                "answered_at": None,
                "dept": rec["dept"],
                "channel": "政民互动·留言选登",
                "extra": {"title": rec["title"], "page": p,
                          "answer_kind": "办理答复（政民零距离，少点名依据）"},
            })
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
