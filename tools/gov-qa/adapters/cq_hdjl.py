"""适配器：**重庆市·互动交流·留言选登**（静态列表 + 静态明细）。

## 站点形态（2026-10-08 实探，证据 recon/tj-sn-cq-hunt.txt / recon/cq-list.html）
 · 栏目「互动交流 → 留言选登」`https://www.cq.gov.cn/hdjl/cqhlwdc/lyxd1/`；
 · 列表条目（30 条/页，服务端渲染）：
   ```
   <li><a target="_blank" href="./202608/t20260826_15980785.html" title="标题">标题</a>
       <span>答复时间：2026-07-10</span></li>
   ```
 · 翻页：`createPage(28, 0, "index", "html")` ⇒ 共 28 页，第 N 页 `index_{N-1}.html`
   （实测 `index_1.html` = 第 2 页，与第 1 页无交集）。
 · 明细：一张 `class="orderDetail"` 表，键值对（`<th/td class="name">键</th/td><td class="text…">值</td>`）：
   `留言标题 / 留言时间 / 留言摘要 / 答复日期 / 答复内容 / 答复单位 / 发布单位`。
   ⇒ 问题取**留言摘要**（站上即为该字段；标题另存 `extra.title`），答复取**答复内容**。
"""
from __future__ import annotations

import re
import time
from urllib.parse import urljoin

SITE = {
    "key": "cq-hdjl",
    "name": "重庆市·互动交流·留言选登",
    "kind": "static",
    "level": "province",
    "entry": "https://www.cq.gov.cn/hdjl/cqhlwdc/lyxd1/",
    "status": "ok",
    "note": "静态列表 30 条/页（createPage 28 页）+ 静态明细；明细为键值表（留言摘要/答复内容）",
}

BASE = "https://www.cq.gov.cn"
LIST_BASE = BASE + "/hdjl/cqhlwdc/lyxd1/"
PAUSE = 1.5

LI_RE = re.compile(r"<li>(.*?)</li>", re.S)
LINK_RE = re.compile(r'<a[^>]*href="(\./\d{6}/t\d{8}_\d+\.html)"[^>]*title="([^"]*)"')
DATE_RE = re.compile(r"<span>\s*答复时间[：:]\s*([0-9]{4}-[0-9]{2}-[0-9]{2})\s*</span>")
COUNT_RE = re.compile(r"createPage\((\d+),\s*\d+,")
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<script.*?</script>|<style.*?</style>", re.S | re.I)


def _text(html: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", SCRIPT_RE.sub(" ", html))).strip()


def _cell(html: str, key: str) -> str | None:
    """取明细表里 `键 → 值` 单元格的纯文本（th/td 通用）。"""
    m = re.search(r">" + re.escape(key) + r"</t[dh]>\s*<t[dh][^>]*>(.*?)</t[dh]>", html, re.S)
    return _text(m.group(1)) if m else None


def _parse_detail(html: str) -> dict | None:
    title = _cell(html, "留言标题")
    question = _cell(html, "留言摘要") or title
    answer = _cell(html, "答复内容")
    if not question or not answer:
        return None
    if len(question) < 4 or len(answer) < 10:
        return None
    return {"question": question[:300], "answer": answer,
            "asked_at": _cell(html, "留言时间"),
            "answered_at": _cell(html, "答复日期"),
            "dept": _cell(html, "答复单位"),
            "title": title,
            "publisher": _cell(html, "发布单位")}


def harvest(fetch, *, limit: int | None = None, max_pages: int = 40) -> list[dict]:
    """翻完所有列表页，逐条取明细（按 URL 去重）。"""
    out: list[dict] = []
    seen: set[str] = set()

    r = fetch(LIST_BASE)
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
            items.append((urljoin(LIST_BASE, m.group(1)), m.group(2),
                          dm.group(1) if dm else None))
        fresh = [it for it in items if it[0] not in seen]
        print(f"    [{SITE['key']}] 第 {p}/{pages} 页：条目 {len(items)}，新增 {len(fresh)}")
        if not fresh:
            continue
        for url, title, ansdate in fresh:
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
                "question": rec["question"],
                "answer": rec["answer"],
                "asked_at": rec["asked_at"],
                "answered_at": rec["answered_at"] or ansdate,
                "dept": rec["dept"],
                "channel": "互动交流·留言选登",
                "extra": {"title": rec["title"], "publisher": rec["publisher"],
                          "page": p,
                          "answer_kind": "办理答复（民呼我为，少点名依据）"},
            })
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
