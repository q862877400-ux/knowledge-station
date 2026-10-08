"""适配器：**黑龙江省人民政府门户 · 政民互动（留言选登）**。

## 站点形态（2026-10-08 实探，证据 recon/hlj-list.html / hlj-detail.html）
 · 入口 `/hlj/c115707/wycx.shtml`（留言选登）。列表静态页只渲染 11 条，
   **翻页走 JS 接口**（`/hlj/xhtml/js/wycx.js` 的 `table_ajax()`）：
   `GET /common/search/<channelId>?_isAgg=false&_isJson=true&_pageSize=100
        &_template=index&_rangeTimeGte=&_channelName=&page=<页码>`
   其中 `channelId=bec7146b06964311a4fb4b77e1eea17d`（取自列表页 `<meta name="channelId">`）。
   → JSON `{data:{total, results:[{title, url, …}]}}`（实测 **total=4082**，`_pageSize` 最大 100 有效）。
 · 明细 `https://www.hlj.gov.cn<url>`（如 `/hlj/c115707/202609/c00_31980015.shtml`，静态）
   为一张表：`留言内容` 行=问题、`受理回复` 段的 `回复内容` 行=答复原文，
   并带 `回复单位` / `回复时间` / `回复编号`（列表页的答复是**截断**的，必须以明细页为准）。
   解析用标签锚点（`<font>留言内容</font>` / `<font>回复内容</font>` 后的 `class="cont"` 单元格），
   实测命中；**不要用「问/答」单字锚点**（导航里无，但该站用「留言内容/回复内容」全称）。

## 说明
答复是**承办单位办理答复**（如「哈尔滨市公安局交通管理支队」「哈尔滨市阿城区人民政府」），
带单位与时间 ⇒ 可当考卷口径。`answer` 取 `回复内容` 原文，不清洗。
"""
from __future__ import annotations

import re
import time

SITE = {
    "key": "hlj-hdjl",
    "name": "黑龙江省人民政府·政民互动（留言选登）",
    "kind": "api",
    "level": "province",
    "entry": "https://www.hlj.gov.cn/hlj/c115707/wycx.shtml",
    "status": "ok",
    "note": "列表 /common/search/<channelId> 接口(total≈4082, pageSize≤100) + 静态明细(留言内容/回复内容)",
}

BASE = "https://www.hlj.gov.cn"
CHANNEL_ID = "bec7146b06964311a4fb4b77e1eea17d"
LIST_API = BASE + "/common/search/" + CHANNEL_ID
LIST_PARAMS = {"_isAgg": "false", "_isJson": "true", "_pageSize": "100",
               "_template": "index", "_rangeTimeGte": "", "_channelName": ""}
PAUSE = 1.5

TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<script.*?</script>|<style.*?</style>", re.S | re.I)
Q_RE = re.compile(r'<font>留言内容</font>\s*</td>\s*<td[^>]*class="cont"[^>]*>(.*?)</td>', re.S)
A_RE = re.compile(r'<font>回复内容</font>\s*</td>\s*<td[^>]*class="cont"[^>]*>(.*?)</td>', re.S)
DEPT_RE = re.compile(r'回复单位</td>\s*<td[^>]*><span></span>(.*?)</td>', re.S)
ANS_RE = re.compile(r'>回复时间</td>\s*<td[^>]*><span>(.*?)</span>', re.S)
ASK_RE = re.compile(r'>留言时间</td>\s*<td[^>]*><span>(.*?)</span>', re.S)
ID_RE = re.compile(r'<td[^>]*>ID</td>\s*<td[^>]*><span>(.*?)</span>', re.S)
TITLE_RE = re.compile(r'<td class="biaoti" width="10%">标题</td>\s*<td[^>]*><span><p>(.*?)</p>',
                      re.S)


def _text(html: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", SCRIPT_RE.sub(" ", html))).strip()


def _parse_detail(html: str) -> dict | None:
    q = Q_RE.search(html)
    a = A_RE.search(html)
    if not q or not a:
        return None
    question = _text(q.group(1))
    answer = _text(a.group(1))
    if len(question) < 4 or len(answer) < 10:
        return None
    d = DEPT_RE.search(html)
    at = ANS_RE.search(html)
    ak = ASK_RE.search(html)
    tm = TITLE_RE.search(html)
    return {"question": question, "answer": answer,
            "title": _text(tm.group(1)) if tm else None,
            "dept": _text(d.group(1)) if d else None,
            "answered_at": at.group(1).strip() if at else None,
            "asked_at": ak.group(1).strip() if ak else None}


def harvest(fetch, *, limit: int | None = None, max_pages: int = 60) -> list[dict]:
    """按 page 翻列表接口，再逐条取明细页解析（按明细 url 去重）。"""
    out: list[dict] = []
    seen: set[str] = set()
    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            break
        params = dict(LIST_PARAMS)
        params["page"] = str(page)
        r = fetch(LIST_API, params=params)
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        try:
            data = r.json().get("data") or {}
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页 JSON 异常 {type(e).__name__}（停）")
            break
        results = data.get("results") or []
        if not results:
            break
        fresh = [it for it in results if (it.get("url") or "") not in seen]
        print(f"    [{SITE['key']}] 第 {page} 页：条目 {len(results)}，新增 {len(fresh)}"
              f"（total={data.get('total')}）")
        if not fresh:
            break
        for it in fresh:
            if limit and len(out) >= limit:
                return out[:limit]
            path = it.get("url") or ""
            if not path:
                continue
            seen.add(path)
            url = path if path.startswith("http") else BASE + path
            time.sleep(PAUSE)
            d = fetch(url)
            if getattr(d, "status_code", 0) != 200:
                continue
            rec = None
            try:
                rec = _parse_detail(d.text or "")
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{SITE['key']}] 解析失败 {path[-18:]} {type(e).__name__}")
            if not rec:
                continue
            uid = path.rsplit("/", 1)[-1].replace(".shtml", "")
            out.append({
                "source": SITE["key"],
                "id": uid,
                "url": url,
                "question": rec["question"],
                "answer": rec["answer"],
                "asked_at": rec.get("asked_at"),
                "answered_at": rec.get("answered_at"),
                "dept": rec.get("dept"),
                "channel": "政民互动·留言选登",
                "extra": {"title": rec.get("title") or it.get("title"),
                          "list_api": LIST_API,
                          "answer_kind": "承办单位办理答复"},
            })
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条（按明细 url 去重）")
    return out
