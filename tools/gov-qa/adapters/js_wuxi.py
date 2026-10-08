"""适配器：**无锡市·政民互动·市长信箱/12345 信件查询（mailbox letter/search）**。

## 站点事实（2026-10-09 实测，证据 recon/city-js-probe9~12.txt）
 · 门户 `www.wuxi.gov.cn` 互动交流 → 信件查询
   `https://www.wuxi.gov.cn/hdjl/index.html`，页面调
   `GET /mailbox/letter/search`。
 · 接口：`GET https://www.wuxi.gov.cn/mailbox/letter/search?page=N&size=S` → JSON：
     `{"totalElements":8613,"totalPages":…,"page":N,"size":S,"data":[{…}]}`
   条目字段（关键）：
     `title` 标题、`content` 问题正文、`resultAnswer` **答复全文**（verbatim）、
     `depName` 答复单位、`beginTime` 提交日、`endTime` 答复日、`searchID` 编号、
     `answerID` uuid、`typeIDName` 类型（咨询/投诉/建议…）、`doState`（2=已办结）。
   ★ **列表即含问题 + 答复全文**（无需明细）⇒ 采集快。
 · ⚠ 翻页参数名是 **`page`**（1 基），页大小是 **`size`**——
   `pageNum`/`currentPage`/`pageNo`/`pageIndex`/`start` 都被忽略（恒返回第 1 页，实测）。
 · 样例：编号 `WX2026092500059`「找一份跆拳道教练的工作」→ 惠山区前洲街道答复（213 字）。
"""
from __future__ import annotations

import time

SITE = {
    "key": "js-wuxi",
    "name": "无锡市·政民互动·市长信箱（信件查询）",
    "kind": "api",
    "level": "city",
    "entry": "https://www.wuxi.gov.cn/hdjl/index.html",
    "status": "ok",
    "note": "GET /mailbox/letter/search?page&size；**列表自带问题+答复全文**；totalElements≈8613",
}

BASE = "https://www.wuxi.gov.cn"
LIST_URL = BASE + "/mailbox/letter/search"
REFERER = SITE["entry"]
PAUSE = 1.5
PAGE_SIZE = 20


def _day(v) -> str | None:
    v = (v or "").strip() if isinstance(v, str) else v
    return v or None


def harvest(fetch, *, limit: int | None = None, max_pages: int = 500) -> list[dict]:
    """翻页取无锡市长信箱信件（列表自带问题 + 答复全文）。"""
    out: list[dict] = []
    seen: set[str] = set()
    total = None
    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            break
        try:
            r = fetch(LIST_URL, params={"page": page, "size": PAGE_SIZE},
                      headers={"Referer": REFERER})
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页：{type(e).__name__} {e}（停）")
            break
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        try:
            d = (r.json() or {}).get("data") or {}
        except Exception:                                                   # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页非 JSON（停）")
            break
        rows = d.get("data") or []
        if total is None:
            total = d.get("totalElements")
            print(f"    [{SITE['key']}] 信件总数 totalElements={total}")
        if not rows:
            break
        for it in rows:
            if limit and len(out) >= limit:
                return out
            sid = str(it.get("searchID") or it.get("answerID") or "").strip()
            if not sid or sid in seen:
                continue
            seen.add(sid)
            answer = (it.get("resultAnswer") or "").strip()
            if len(answer) < 10:            # 未答复，跳过
                continue
            title = (it.get("title") or "").strip()
            content = (it.get("content") or "").strip()
            question = title if not content else f"{title}\n{content}"
            out.append({
                "source": SITE["key"],
                "id": sid,
                "url": SITE["entry"],
                "question": question,
                "answer": answer,
                "asked_at": _day(it.get("beginTime")),
                "answered_at": _day(it.get("endTime")),
                "dept": (it.get("depName") or "").strip() or None,
                "channel": "政民互动·市长信箱",
                "extra": {
                    "title": title,
                    "type": it.get("typeIDName"),
                    "search_id": it.get("searchID"),
                    "answer_id": it.get("answerID"),
                    "do_state": it.get("doState"),
                    "platform": "无锡 mailbox letter/search（列表自带答复）",
                },
            })
        if total and page * PAGE_SIZE >= int(total):
            break
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
