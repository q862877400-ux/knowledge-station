"""适配器：**国家林业和草原局·互动留言**（JEECMS 站内 JSON 接口，答复内联）。

## 站点事实（2026-10-09 实测，证据 recon/nat-forestry-*）
 · 入口 `http://www.forestry.gov.cn/hdly.jhtml`（互动留言）。
   列表页是空壳，内联 JS（页尾 `getLetterPage()`）调站内接口拉取（免登录）。
 · 列表（**GET，答复内联**）：
   `GET http://www.forestry.gov.cn/letter/page?title=&page=N&size=20&orderBy=3`
   → `{code:200,data:{content:[{id,title,content,replyContent,createTime,replyTime,…}],
        totalElements:673,totalPages:34}}`
   `content`=问题原文，`replyContent`=答复原文。
   ⚠ 该站是 **JEECMS**（`/r/cms/www/default/js/app.js` 定义 `api.GET`，`base=localStorage.base||''`），
     同族站的接口规律一致：`base + '/<模块>/page'`。列表接口返回**全字段**（含 ip/cookieIdentity 等），
     只取需要的，别原样落库。
 · 明细页（人看）：`http://www.forestry.gov.cn/lyDetail.htm?<id>`。
 · 实测答复点名《…》（例：《中华人民共和国野生动物保护法》《…决定》）⇒ 优质考卷料。
"""
from __future__ import annotations

import time

SITE = {
    "key": "nat-forestry",
    "name": "国家林业和草原局·互动留言",
    "kind": "api",
    "level": "national",
    "entry": "http://www.forestry.gov.cn/hdly.jhtml",
    "status": "ok",
    "note": "JEECMS 站内接口 /letter/page（GET，答复内联 replyContent，totalElements=673）",
}

BASE = "http://www.forestry.gov.cn"
LIST_API = BASE + "/letter/page"
DETAIL_PAGE = BASE + "/lyDetail.htm?"
REFERER = BASE + "/hdly.jhtml"
PAGE_SIZE = 20
PAUSE = 1.5

_HEADERS = {
    "Content-Type": "application/json",
    "Referer": REFERER,
    "Accept": "application/json, text/javascript, */*; q=0.01",
}


def harvest(fetch, *, limit: int | None = None, page_size: int = PAGE_SIZE) -> list[dict]:
    """取国家林草局互动留言（问题 + 答复原文）。"""
    out: list[dict] = []
    page = 1
    total_pages = None
    while True:
        if limit and len(out) >= limit:
            break
        r = fetch(LIST_API, params={"title": "", "page": page, "size": page_size, "orderBy": 3},
                  headers=_HEADERS)
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 第 {page} 页 HTTP {getattr(r, 'status_code', '?')}（停）")
            break
        try:
            j = r.json()
        except Exception as e:                                                  # noqa: BLE001
            print(f"    [{SITE['key']}] 第 {page} 页非 JSON（{type(e).__name__}，停）")
            break
        if j.get("code") != 200:
            print(f"    [{SITE['key']}] 第 {page} 页 code={j.get('code')}（停）")
            break
        data = j.get("data") or {}
        items = data.get("content") or []
        if total_pages is None:
            total_pages = data.get("totalPages") or 0
            print(f"    [{SITE['key']}] totalElements={data.get('totalElements')} totalPages={total_pages}")
        if not items:
            break
        for it in items:
            if limit and len(out) >= limit:
                break
            answer = (it.get("replyContent") or "").strip()
            if len(answer) < 10:
                continue
            out.append({
                "source": SITE["key"],
                "id": str(it.get("id") or it.get("letterNo") or ""),
                "url": DETAIL_PAGE + str(it.get("id") or ""),
                "question": (it.get("content") or it.get("title") or "").strip(),
                "answer": answer,
                "asked_at": it.get("createTime"),
                "answered_at": it.get("replyTime"),
                "dept": "国家林业和草原局",
                "channel": "互动留言",
                "extra": {
                    "title": it.get("title"),
                    "letter_no": it.get("letterNo"),
                    "province": it.get("province"),
                    "platform": "forestry-jeecms",
                },
            })
        if total_pages and page >= total_pages:
            break
        page += 1
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
