"""适配器：**青海省·互动交流·群众诉求回应**（静态列表 + 静态明细）。

## 站点事实（2026-10-08 实测，证据 recon/xj-xz-sd-gx-qh-hunt.txt 【青海】）
 · 门户 `www.qinghai.gov.cn` 的「互动交流 → 群众诉求回应」`/zmhd/wsxf/index.html`
   （另有「便民问答」`/msfw/bmwd/` 同款 CMS）；
 · ⚠ **旧结论「青海 ConnectTimeout」是 https 失败所致**：`https://www.qinghai.gov.cn`
   连接超时（40s），而 **http 明文 200 可达**。
 · CMS 是 **enorth webpublisher**，翻页走**静态分页文件**（`/zmhd/system/count/.../c<chnid>_<9位>.shtml`）：
   · 第 1 页 `/zmhd/wsxf/index.html`；
   · 第 N 页（N≥2）`/zmhd/system/count/0005002/000000000000/000/000/
     c0005002000000000000_{28-N:09d}.shtml`（站内 `count_page_list_*.js` 自报 `maxpage=26` ⇒ 共 27 页；
     实测 `_000000026.shtml` = 第 2 页，与首页无交集）。
 · 列表条目在**左栏** `class="lPanel"` … `class="rPanel"` 之间（右栏是便民通告/民生保障等非问答）：
   `<p class="item"><span class="gray">[2026/09/09]&nbsp;</span><a href="…" title="问题标题">…</a></p>`
 · 明细正文结构：
   · `<h1 class="blue tc">问题标题</h1>`（= 问题）
   · `<div class="abstract tc"> 来源：… 发布时间：YYYY-MM-DD HH:MM …</div>`（= 答复单位 + 时间）
   · `<div class="details_content"> …答复正文（常点名公告/文件号）… </div>`（= 答复）
   样例：如何申请离境退税「即买即退」商店 → 答复引《国家税务总局公告 2025 年第 9 号》。
"""
from __future__ import annotations

import html as _html
import re
import time
from urllib.parse import urljoin

from adapters._igi_common import existing_ids

SITE = {
    "key": "qh-wsxf",
    "name": "青海省·互动交流·群众诉求回应",
    "kind": "static",
    "level": "province",
    "entry": "http://www.qinghai.gov.cn/zmhd/wsxf/index.html",
    "status": "ok",
    "note": "enorth CMS 静态列表（27 页）+ 静态明细；http 可达（https 超时）",
}

BASE = "http://www.qinghai.gov.cn"
LIST1 = BASE + "/zmhd/wsxf/index.html"
#: 静态分页文件前缀（第 N≥2 页 = 前缀 + f"{28-N:09d}.shtml"）
PAGEDIR = (BASE + "/zmhd/system/count/0005002/000000000000/000/000/"
           "c0005002000000000000_")
MAXPAGE = 26          # 站内 count_page_list_*.js 自报（+1 = 27 页）
PAUSE = 1.5

ITEM_RE = re.compile(r'<p class="item">(.*?)</p>', re.S)
HREF_RE = re.compile(r'<a[^>]*href="([^"]+)"[^>]*title="([^"]*)"', re.S)
DATE_RE = re.compile(r"\[(\d{4})/(\d{2})/(\d{2})\]")
H1_RE = re.compile(r'<h1 class="blue tc">(.*?)</h1>', re.S)
ABSTRACT_RE = re.compile(r'<div class="abstract tc">(.*?)</div>', re.S)
CONTENT_RE = re.compile(r'<div class="details_content">(.*?)</div>', re.S)
SRC_RE = re.compile(r"来源[：:]\s*(.*?)\s*(?:&nbsp;|作者|发布时间|编辑|$)")
PUB_RE = re.compile(r"发布时间[：:]\s*(\d{4}-\d{2}-\d{2}(?:\s+\d{1,2}:\d{2})?)")
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<script.*?</script>|<style.*?</style>", re.S | re.I)


def _text(html: str | None) -> str:
    raw = (html or "").replace("&nbsp;", " ").replace("\u00a0", " ")
    raw = _html.unescape(raw)
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", SCRIPT_RE.sub(" ", raw))).strip()


def _page_url(n: int) -> str | None:
    if n == 1:
        return LIST1
    suffix = MAXPAGE + 2 - n          # 28 - n
    if suffix < 1:
        return None
    return PAGEDIR + f"{suffix:09d}.shtml"


def _parse_detail(html: str) -> dict | None:
    cm = CONTENT_RE.search(html)
    answer = _text(cm.group(1)) if cm else ""
    if len(answer) < 10:
        return None
    qm = H1_RE.search(html)
    question = _text(qm.group(1)) if qm else ""
    am = ABSTRACT_RE.search(html)
    abstract = _text(am.group(1)) if am else ""
    src = SRC_RE.search(abstract)
    pub = PUB_RE.search(abstract)
    return {
        "question": question[:400],
        "answer": answer,
        "dept": (src.group(1).strip() if src else None) or None,
        "answered_at": pub.group(1) if pub else None,
    }


def harvest(fetch, *, limit: int | None = None, max_pages: int = 30,
            skip_ids: set[str] | None = None) -> list[dict]:
    """翻完全部静态分页，逐条取明细（按明细 URL 去重）。

    ★ 2026-10-09 补 `skip_ids`（**修「第二轮恒 0 新增」**）：
      本适配器原先**每轮都从第 1 页重跑**，而 `harvest.py` 按 id 去重 ⇒
      上游 27 页却永远停在首批 200 条（实测存量就是 200，且复跑新增 0）。
      现在开跑先读已落盘 id：命中则**不请求明细**、**不计入 `limit`**
      ⇒ `limit` 语义变为「本轮新增条数」。要重刷已落盘条目传 `skip_ids=set()`。
    """
    if skip_ids is None:
        skip_ids = existing_ids(SITE.get("key", ""))
    out: list[dict] = []
    seen: set[str] = set()
    skipped = 0
    for n in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            break
        url = _page_url(n)
        if url is None:
            break
        if n > 1:
            time.sleep(PAUSE)
        r = fetch(url)
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 第 {n} 页 HTTP {getattr(r, 'status_code', '?')}（停）")
            break
        html = r.text or ""
        # 只取左栏（群众诉求回应），避开右栏便民通告/民生保障等非问答栏目
        # ⚠ 容器 class 是 `l lPanel` / `l rPanel`（不是 `lPanel`）；写错会静默回退整页
        li = html.find("l lPanel")
        ri = html.find("l rPanel")
        left = html[li:ri] if li >= 0 and ri > li else html
        items = []
        for blk in ITEM_RE.findall(left):
            m = HREF_RE.search(blk)
            if not m:
                continue
            dm = DATE_RE.search(blk)
            date = f"{dm.group(1)}-{dm.group(2)}-{dm.group(3)}" if dm else None
            items.append((urljoin(url, m.group(1)), _text(m.group(2)), date))
        fresh = [it for it in items if it[0] not in seen]
        print(f"    [{SITE['key']}] 第 {n}/{MAXPAGE + 1} 页：条目 {len(items)}，新增 {len(fresh)}")
        if not fresh:
            continue
        for durl, title, date in fresh:
            if limit and len(out) >= limit:
                return out[:limit]
            seen.add(durl)
            uid = durl.rsplit("/", 1)[-1].replace(".shtml", "")
            if uid in skip_ids:
                skipped += 1                    # 已落盘 ⇒ 省掉一次明细请求
                continue
            time.sleep(PAUSE)
            d = fetch(durl)
            if getattr(d, "status_code", 0) != 200:
                continue
            rec = _parse_detail(d.text or "")
            if not rec:
                continue
            out.append({
                "source": SITE["key"],
                "id": uid,
                "url": durl,
                "question": rec["question"] or title,
                "answer": rec["answer"],
                "asked_at": date,
                "answered_at": rec["answered_at"] or date,
                "dept": rec["dept"],
                "channel": "互动交流·群众诉求回应",
                "extra": {"title": rec["question"] or title, "page": n,
                          "answer_kind": "办理答复（群众诉求回应，常点名公告/文件号）"},
            })
    print(f"    [{SITE['key']}] 收 {len(out)} 条"
          + (f"（跳过已落盘 {skipped} 条）" if skipped else ""))
    return out
