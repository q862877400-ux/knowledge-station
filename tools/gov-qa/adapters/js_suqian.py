"""适配器：**宿迁市·政民互动·留言查询/部门信箱（ajaxlist，列表自带答复）**。

## 站点事实（2026-10-09 实测，证据 recon/city-js-probe3.txt）
 · 门户 `www.suqian.gov.cn` 互动交流 → 留言查询
   `https://www.suqian.gov.cn/cnsq/xinxiang/bmxxi_frame.shtml`，
   页面 JS 调 `POST /u/consult/ajaxlist`。
 · 接口：`POST https://www.suqian.gov.cn/u/consult/ajaxlist`（form 表单）→ JSON：
     `{"code":"0","data":{"list":[[信箱名, id1, id2, 提交时间戳, 标题, 编号, 问题正文,
        答复时间戳|None, 答复正文, 答复时间字符串], …],
       "allRow":1373,"totalPage":138,"pageSize":10,…}}`
   ★ **列表即含问题 + 答复全文**（无需再请求明细）⇒ 采集极快。
 · ★★ 字段语义（2026-10-09 实测复核）：`it[1]` = **部门信箱 id**（全站只有 **41 个唯一值**，
   1373 行里大量重复）；`it[2]` = **信件 guid**（1373 唯一）；`it[5]` = 信件编号（1372 唯一）。
   **id 必须取 `it[2]`** —— 旧版用 `it[1] or it[2]` 去重，按部门折叠，1373 条只剩 41 条（3%）。
 · ⚠ `pageSize` 被服务端忽略（恒 10）；翻页参数名是 **`currentPage`**（页码，1 基）——
   `pageIndex`/`page`/`pageNo`/`pageNum` 都被忽略（恒返回第 1 页，实测）。
 · 样例：编号 202610044587「统计年鉴」→ 市统计局答复（电话告知）；公安局部门信箱同款。
"""
from __future__ import annotations

import time

SITE = {
    "key": "js-suqian",
    "name": "宿迁市·政民互动·留言查询（部门信箱）",
    "kind": "api",
    "level": "city",
    "entry": "https://www.suqian.gov.cn/cnsq/xinxiang/bmxxi_frame.shtml",
    "status": "ok",
    "note": "POST /u/consult/ajaxlist；**列表自带问题+答复全文**；allRow≈1373；pageSize 恒 10",
}

BASE = "https://www.suqian.gov.cn"
LIST_URL = BASE + "/u/consult/ajaxlist"
REFERER = SITE["entry"]
PAUSE = 1.2
PAGE_SIZE = 10


def _ts(ms) -> str | None:
    try:
        v = int(ms)
    except (TypeError, ValueError):
        return None
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(v / 1000)) if v > 0 else None


def harvest(fetch, *, limit: int | None = None, max_pages: int = 300) -> list[dict]:
    """翻页取宿迁留言（列表自带问题 + 答复全文）。"""
    out: list[dict] = []
    seen: set[str] = set()
    total = None
    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            break
        try:
            r = fetch.post(LIST_URL, data={"currentPage": page, "pageSize": PAGE_SIZE},
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
        rows = d.get("list") or []
        if total is None:
            total = d.get("allRow")
            print(f"    [{SITE['key']}] 留言总数 allRow={total}")
        if not rows:
            break
        for it in rows:
            if limit and len(out) >= limit:
                return out
            if not isinstance(it, (list, tuple)) or len(it) < 9:
                continue
            box, id1, id2, sub_ts, title, num, content, ans_ts, answer = (
                it[0], it[1], it[2], it[3], it[4], it[5], it[6], it[7], it[8])
            answered = it[9] if len(it) > 9 else None
            # ★ id 用 it[2]（信件 guid，1373 唯一）；**不是** it[1]！
            #   实测 it[1] 只有 41 个唯一值（=41 个部门信箱的 id），
            #   旧版误用 `id1 or id2 or num` ⇒ 按部门去重、1373 条只剩 41 条。
            sid = str(id2 or num or "").strip()
            if not sid or sid in seen:
                continue
            seen.add(sid)
            answer = (answer or "").strip()
            if len(answer) < 10:            # 未答复，跳过
                continue
            title = (title or "").strip()
            content = (content or "").strip()
            question = title if not content else f"{title}\n{content}"
            out.append({
                "source": SITE["key"],
                "id": sid,
                "url": SITE["entry"],
                "question": question,
                "answer": answer,
                "asked_at": _ts(sub_ts),
                "answered_at": answered or _ts(ans_ts),
                "dept": (box or "").strip() or None,
                "channel": "政民互动·部门信箱",
                "extra": {
                    "title": title,
                    "mail_number": num,
                    "box_name": box,
                    "platform": "宿迁 ajaxlist（列表自带答复）",
                },
            })
        if total and page * PAGE_SIZE >= int(total):
            break
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
