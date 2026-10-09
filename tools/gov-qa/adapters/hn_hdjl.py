"""适配器：**河南省人民政府门户 · 互动交流（网上咨询）**。

## 站点形态（2026-10-08 实探，证据 recon/hn-wszx-list.html / hn-wszx-detail.html）
 ⚠ 报告原判「豫政问答 /hdjl/hdjl/ = 文章型问答」——**实测确认不可采**：
   那是**记者撰写的政策解读报道**（正文如「记者联系了河南省医疗保障局相关负责人了解详细情况」，
   来源「河南政府网」、署名记者），**没有「提问人 + 答复单位 + 提问/答复时间」结构**，
   是新闻稿不是问答记录 ⇒ **本适配器改采真问答栏目 `/hdjl/wszx/`（网上咨询）**。
 · 列表 `/hdjl/wszx/`（服务端渲染静态 HTML）：`<li class="list-li">`
   `<span class="date">YYYY-MM-DD</span><a href="https://www.henan.gov.cn/YYYY/MM-DD/ID.html">标题</a></li>`；
   **翻页是静态页**：第 1 页 `/hdjl/wszx/`，第 N(≥2) 页 `/hdjl/wszx/index_{N-1}.html`
   （`paging.js`：`reLoadUrl + 'index' + ('_'+(page-1)) + '.html'`）。
   实测 `index_26.html` 尚有 4 条、`index_27.html` 404 ⇒ **共 27 页 / 约 629 条**（页大小 24）。
 · 明细 `/YYYY/MM-DD/ID.html`（静态，无 JS）：`<div class="content">` 内两张 `table.xf-box`：
   ① `详细信息` 表：`标题` / `提交日期` / `内容`(=问题)；
   ② `受理回复` 表：`回复日期` / `回复单位` / `回复内容`(=答复原文)。

## 说明
答复是**厅局办理答复**（如河南省药品监督管理局答复并点名《药品经营和使用质量监督管理办法》
（国家市场监督管理总局令第84号）第十一条）⇒ 可当考卷口径。`answer` 取 `回复内容` 原文，不清洗。
"""
from __future__ import annotations

import re
import time

from adapters._igi_common import existing_ids

SITE = {
    "key": "hn-hdjl",
    "name": "河南省人民政府·互动交流（网上咨询）",
    "kind": "static",
    "level": "province",
    "entry": "https://www.henan.gov.cn/hdjl/wszx/",
    "status": "ok",
    "note": "静态列表 index_{N}.html 翻页(约629条) + 静态明细(内容/回复内容)；豫政问答是文章型不可采",
}

BASE = "https://www.henan.gov.cn"
LIST_URL = BASE + "/hdjl/wszx/"
PAGE_URL = BASE + "/hdjl/wszx/index_{n}.html"
PAUSE = 1.5

ITEM_RE = re.compile(
    r'<li class="list-li"><span class="date">([0-9]{4}-[0-9]{2}-[0-9]{2})</span>'
    r'<a href="(https://www\.henan\.gov\.cn/[0-9]{4}/[0-9]{2}-[0-9]{2}/[0-9]+\.html)"'
    r'[^>]*>(.*?)</a>', re.S)
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<script.*?</script>|<style.*?</style>", re.S | re.I)
FOOT_CUT = re.compile(r"(责任编辑|扫一扫|相关阅读|【关闭当前页面】)")


def _text(html: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", SCRIPT_RE.sub(" ", html))).strip()


def _cell(html: str, label: str) -> str | None:
    m = re.search(r"<th[^>]*>" + label + r"</th>\s*<td[^>]*>(.*?)</td>", html, re.S)
    return _text(m.group(1)) if m else None


def _parse_detail(html: str) -> dict | None:
    question = _cell(html, "内容")
    answer = _cell(html, "回复内容")
    if not question or not answer:
        return None
    answer = FOOT_CUT.split(answer)[0].strip()
    if len(question) < 4 or len(answer) < 10:
        return None
    return {"question": question, "answer": answer,
            "title": _cell(html, "标题"),
            "dept": _cell(html, "回复单位"),
            "asked_at": _cell(html, "提交日期"),
            "answered_at": _cell(html, "回复日期")}


def harvest(fetch, *, limit: int | None = None, max_pages: int = 40,
            skip_ids: set[str] | None = None) -> list[dict]:
    """逐页取列表（首页静态地址，其余 index_{n}.html），再逐条取明细（按明细 url 去重）。

    ★ 2026-10-09 补 `skip_ids`（**修「第二轮恒 0 新增」**）：
      本适配器原先**每轮都从第 1 页重跑**，而 `harvest.py` 按 id 去重 ⇒
      上游 27 页却永远停在前 ~21 页（实测存量 500；复跑 limit=400 得「新增 0」，
      因为 `limit` 被前 17 页的旧记录吃满、根本走不到 22 页以后）。
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
        url = LIST_URL if n == 1 else PAGE_URL.format(n=n - 1)
        r = fetch(url)
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {n} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        html = r.text or ""
        items = ITEM_RE.findall(html)
        fresh = [it for it in items if it[1] not in seen]
        print(f"    [{SITE['key']}] 第 {n} 页：条目 {len(items)}，新增 {len(fresh)}")
        if not fresh:
            break
        for _date, durl, title in fresh:
            if limit and len(out) >= limit:
                return out[:limit]
            seen.add(durl)
            uid = durl.rsplit("/", 1)[-1].replace(".html", "")
            if uid in skip_ids:
                skipped += 1                    # 已落盘 ⇒ 省掉一次明细请求
                continue
            time.sleep(PAUSE)
            d = fetch(durl)
            if getattr(d, "status_code", 0) != 200:
                continue
            rec = None
            try:
                rec = _parse_detail(d.text or "")
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{SITE['key']}] 解析失败 {durl[-16:]} {type(e).__name__}")
            if not rec:
                continue
            out.append({
                "source": SITE["key"],
                "id": uid,
                "url": durl,
                "question": rec["question"],
                "answer": rec["answer"],
                "asked_at": rec.get("asked_at") or _date,
                "answered_at": rec.get("answered_at"),
                "dept": rec.get("dept"),
                "channel": "互动交流·网上咨询",
                "extra": {"title": rec.get("title") or _text(title),
                          "list_url": LIST_URL,
                          "answer_kind": "厅局办理答复（常点名依据）"},
            })
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条（按明细 url 去重）"
          + (f"（跳过已落盘 {skipped} 条）" if skipped else ""))
    return out
