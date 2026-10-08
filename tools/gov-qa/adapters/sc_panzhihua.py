"""适配器：**攀枝花市·12345 政务服务便民热线（webapp api-letter 接口）**。

## 站点事实（2026-10-09 实测，证据 recon/city-sc-probe1~17.txt）
 · 门户 `www.panzhihua.gov.cn`（**http 可达；https 部分 502**）→ 网络理政 →
   `12345政务服务便民热线 /hdcy/zwfwbmrx/index.shtml`。
 · ⚠ 该页「市长信箱」(`/hdcy/szxx/szxx/index.shtml`) 的 `mailbox/letterListJson` 恒返回
   `{"topics":[]}`（不公开信件）；**真正有数据的是 12345 便民热线页**用的接口。
   · ★ 列表接口（无需令牌）：`GET http://www.panzhihua.gov.cn/webapp/api-letter/search-letter`
     params: `pageIndex`（1 基）、`pageSize`
     ⚠ 分页参数名是 **`pageIndex`**，不是 `pageNum`（用 pageNum 时 `pageIndex` 恒回 1，
       永远只拿第一页 ⇒ 曾只落 20/70 条）。2026-10-09 修。
   → JSON：`{"code":0,"totalCount":70,"pageCount":24,"pageIndex":1,"pageSize":3,
      "data":[{id, letterId, letterTitle, letterContent, letterCategory,
               letterReceivedTime, letterReplyTime, replyDepartment, processingResult}]}`
   ★ **列表即含问题 + 答复全文**（`processingResult`）⇒ 采集快。
 · 该接口是爬 12345 转办件：`letterContent` 为来电反映内容，`processingResult` 为办理结果（答复）。
 · 样例：`8219c941-…`「攀枝花学院的相关问题」→ 攀枝花学院答复。
"""
from __future__ import annotations

import time

SITE = {
    "key": "sc-panzhihua",
    "name": "攀枝花市·12345 政务服务便民热线",
    "kind": "api",
    "level": "city",
    "entry": "http://www.panzhihua.gov.cn/hdcy/zwfwbmrx/index.shtml",
    "status": "ok",
    "note": "GET /webapp/api-letter/search-letter?pageNum&pageSize；**列表自带问题+答复全文**；total≈70",
}

BASE = "http://www.panzhihua.gov.cn"
LIST_URL = BASE + "/webapp/api-letter/search-letter"
REFERER = SITE["entry"]
PAUSE = 1.2
PAGE_SIZE = 20


def _day(v) -> str | None:
    v = (v or "").strip() if isinstance(v, str) else v
    return v or None


def harvest(fetch, *, limit: int | None = None, max_pages: int = 100) -> list[dict]:
    """翻页取攀枝花 12345 便民热线工单（列表自带问题 + 答复全文）。"""
    out: list[dict] = []
    seen: set[str] = set()
    total = None
    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            break
        try:
            r = fetch(LIST_URL, params={"pageIndex": page, "pageSize": PAGE_SIZE},
                      headers={"Referer": REFERER, "X-Requested-With": "XMLHttpRequest"})
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页：{type(e).__name__} {e}（停）")
            break
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        try:
            d = r.json() or {}
        except Exception:                                                   # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页非 JSON（停）")
            break
        rows = d.get("data") or []
        if total is None:
            total = d.get("totalCount")
            print(f"    [{SITE['key']}] 工单总数 totalCount={total}")
        if not rows:
            break
        for it in rows:
            if limit and len(out) >= limit:
                return out
            sid = str(it.get("letterId") or it.get("id") or "").strip()
            if not sid or sid in seen:
                continue
            seen.add(sid)
            answer = (it.get("processingResult") or "").strip()
            if len(answer) < 10:            # 未答复，跳过
                continue
            title = (it.get("letterTitle") or "").strip()
            content = (it.get("letterContent") or "").strip()
            question = title if not content else f"{title}\n{content}"
            out.append({
                "source": SITE["key"],
                "id": sid,
                "url": SITE["entry"],
                "question": question,
                "answer": answer,
                "asked_at": _day(it.get("letterReceivedTime")),
                "answered_at": _day(it.get("letterReplyTime")),
                "dept": (it.get("replyDepartment") or "").strip() or None,
                "channel": "12345政务服务便民热线",
                "extra": {
                    "title": title,
                    "category": it.get("letterCategory"),
                    "letter_id": it.get("letterId"),
                    "platform": "攀枝花 webapp api-letter（12345 转办件，列表自带答复）",
                },
            })
        if total and page * PAGE_SIZE >= int(total):
            break
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
