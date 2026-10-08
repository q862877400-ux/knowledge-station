"""适配器：**苏州市·政民互动·部门信箱（consultfront bmxxCommonlist）**。

## 站点事实（2026-10-09 实测，证据 recon/city-js-probe9~16.txt）
 · 门户 `www.suzhou.gov.cn` 互动交流 → 部门信箱，前端 Vue（main.js）调
   `GET/POST /consultfront/common/bmxxCommonlist`。
 · 列表接口：`/consultfront/common/bmxxCommonlist`
     params: `currpage`(页码,1 基) `pagesize`(页大小) `check=do` `deptcode`(空=全部) `keywords`
   → JSON：`{"totalcount":4153,"infolist":[{…}],"retCode":"0"}`
   条目字段：`gid` 主键、`consult_title` 标题、`consult_revert_content` **答复全文**、
     `name` 答复单位、`consult_date` 提交日、`consult_revert_date` 答复时间、
     `consult_state` 状态、`consult_type` 类型（咨询/投诉…）。
   ★ **列表即含答复全文**（无需明细）⇒ 采集快。
 · ⚠ 翻页参数名是 **`currpage`**、页大小是 **`pagesize`**——
   `pageNum`/`page`/`pageIndex`/`currentPage`/`pageNo`/`start`/`offset` 全被忽略
   （恒返回第 1 页，实测）。此参数名由反查 main.js 得到：
   `Ms(RB,{currpage:u.value,check:"do",pagesize:r.value,deptcode:s.value,keywords:o.value})`。
 · 明细端点（可选，补问题正文）：`GET /consultfront/common/getBmxxDetail?id=<gid>`
   → `{"detail":{"consult_content":问题正文,"consult_revert_content":答复,…}}`。
   本适配器默认**只用列表**（列表已含完整答复，快）；问题用标题。
 · 样例：gid `30494270FA3696D3`「2003-2024年苏州市水资源公报」→ 苏州市水务局答复。
"""
from __future__ import annotations

import time

SITE = {
    "key": "js-suzhou",
    "name": "苏州市·政民互动·部门信箱",
    "kind": "api",
    "level": "city",
    "entry": "https://www.suzhou.gov.cn/szsrmzf/xhtml/hd/",
    "status": "ok",
    "note": "GET /consultfront/common/bmxxCommonlist?currpage&pagesize；**列表自带答复全文**；totalcount≈4153",
}

BASE = "https://www.suzhou.gov.cn"
LIST_URL = BASE + "/consultfront/common/bmxxCommonlist"
REFERER = SITE["entry"]
PAUSE = 1.5
PAGE_SIZE = 20


def _dt(v) -> str | None:
    v = (v or "").strip() if isinstance(v, str) else v
    return v or None


def harvest(fetch, *, limit: int | None = None, max_pages: int = 400) -> list[dict]:
    """翻页取苏州部门信箱（列表自带答复全文）。"""
    out: list[dict] = []
    seen: set[str] = set()
    total = None
    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            break
        try:
            r = fetch(LIST_URL, params={
                "currpage": page, "check": "do", "pagesize": PAGE_SIZE,
                "deptcode": "", "keywords": "",
            }, headers={"Referer": REFERER})
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
        rows = d.get("infolist") or []
        if total is None:
            total = d.get("totalcount")
            print(f"    [{SITE['key']}] 信件总数 totalcount={total}")
        if not rows:
            break
        for it in rows:
            if limit and len(out) >= limit:
                return out
            sid = str(it.get("gid") or "").strip()
            if not sid or sid in seen:
                continue
            seen.add(sid)
            answer = (it.get("consult_revert_content") or "").strip()
            if len(answer) < 10:            # 未答复，跳过
                continue
            title = (it.get("consult_title") or it.get("completetitle") or "").strip()
            out.append({
                "source": SITE["key"],
                "id": sid,
                "url": SITE["entry"],
                "question": title,
                "answer": answer,
                "asked_at": _dt(it.get("consult_date")),
                "answered_at": _dt(it.get("consult_revert_date")),
                "dept": (it.get("name") or "").strip() or None,
                "channel": "政民互动·部门信箱",
                "extra": {
                    "title": title,
                    "type": it.get("consult_type"),
                    "state": it.get("consult_state"),
                    "gid": sid,
                    "platform": "苏州 consultfront bmxxCommonlist（列表自带答复）",
                },
            })
        if total and page * PAGE_SIZE >= int(total):
            break
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
