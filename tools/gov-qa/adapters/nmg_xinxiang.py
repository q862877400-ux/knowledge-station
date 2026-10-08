"""适配器：**内蒙古自治区·政民互动·反馈回应**（`xinxiang` 自建接口）。

## 站点事实（2026-10-08 实测，证据 `recon/bj-nmg-hunt.txt`）
 · 门户 `www.nmg.gov.cn` 的「政民互动」→「反馈回应」
   `/zmhd/fkhy_1/index_13317.html`（列表页由 JS 拉接口渲染）。
 · 列表（**POST** JSON，实测 200）：
   `POST https://www.nmg.gov.cn/xinxiang/api/getCaseInfoList`
   `Content-Type: application/json`，body `{"title":"","first":1,"pageSize":100}`
   → `{code:200,data:{list:[{id,ticketTitle,finishTime,ticketId,status}],
        pagination:{currentPage,pageSize,total,totalPage}}}`，实测 `total=67`。
 · 明细（**GET**，实测 200）：
   `GET https://www.nmg.gov.cn/xinxiang/api/getCaseInfo?rowguid=<id>`
   → `data:{ticketTitle,ticketContent(问题),replyContent(答复),replyDept,replyTime,appealTime}`
   样例：外地户籍申请公租房 → 鄂尔多斯市杭锦旗住房和城乡建设局答复（4 条条件）。
 · ⚠ **无独立省市县归属字段**（`replyDept` 里含地区名如「鄂尔多斯市杭锦旗…局」，
   但非结构化）⇒ 归省靠 `recon/coverage-matrix.py` 的 `PROVINCE_PREFIX`
   （**需补 `nmg-` → 内蒙古自治区**）。
"""
from __future__ import annotations

import json
import time

SITE = {
    "key": "nmg-xinxiang",
    "name": "内蒙古自治区·政民互动·反馈回应",
    "kind": "api",
    "level": "province",
    "entry": "https://www.nmg.gov.cn/zmhd/fkhy_1/index_13317.html",
    "status": "ok",
    "note": "xinxiang 自建接口；列表 POST JSON getCaseInfoList，明细 GET getCaseInfo?rowguid=；"
            "答复含办理单位；无三级归属靠来源前缀",
}

LIST = "https://www.nmg.gov.cn/xinxiang/api/getCaseInfoList"
DETAIL = "https://www.nmg.gov.cn/xinxiang/api/getCaseInfo"
ENTRY = "https://www.nmg.gov.cn/zmhd/fkhy_1/index_13317.html"
REFERER = "https://www.nmg.gov.cn/zmhd/"
PAGE_SIZE = 100
PAUSE = 1.5


def _ts(s) -> str | None:
    """ISO 时间（`2026-09-23T09:52:21.000+08:00`）→ `2026-09-23 09:52:21`。"""
    if not s:
        return None
    t = str(s).replace("T", " ").split(".")[0].split("+")[0].strip()
    return t or None


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """翻页取反馈回应列表，逐条取明细拿问题/答复正文，返回统一记录。"""
    out: list[dict] = []
    total = None
    page = 1
    while True:
        if limit and len(out) >= limit:
            break
        body = json.dumps({"title": "", "first": page, "pageSize": PAGE_SIZE})
        r = fetch.post(LIST, content=body,
                       headers={"Content-Type": "application/json",
                                "Referer": REFERER})
        if getattr(r, "status_code", 0) != 200:
            print(f"    [nmg-xinxiang] 列表第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        try:
            d = r.json()
        except Exception as e:                                              # noqa: BLE001
            print(f"    [nmg-xinxiang] 第 {page} 页解析失败 {type(e).__name__}（停）")
            break
        data = d.get("data") or {}
        rows = data.get("list") or []
        pg = data.get("pagination") or {}
        if total is None:
            try:
                total = int(pg.get("total") or 0)
            except (TypeError, ValueError):
                total = 0
        if not rows:
            break
        print(f"    [nmg-xinxiang] 第 {page} 页：{len(rows)} 条（total={total}）")
        for it in rows:
            if limit and len(out) >= limit:
                break
            gid = str(it.get("ticketId") or it.get("id") or "")
            if not gid:
                continue
            title = (it.get("ticketTitle") or "").strip()
            time.sleep(PAUSE)
            question = title
            answer = ""
            dept = None
            asked_at = None
            answered_at = it.get("finishTime")
            try:
                dr = fetch(DETAIL, params={"rowguid": gid},
                           headers={"Referer": ENTRY})
                if getattr(dr, "status_code", 0) == 200:
                    dd = dr.json().get("data") or {}
                    question = (dd.get("ticketContent") or "").strip() or title
                    answer = (dd.get("replyContent") or "").strip()
                    dept = (dd.get("replyDept") or "").strip() or None
                    asked_at = _ts(dd.get("appealTime"))
                    answered_at = _ts(dd.get("replyTime")) or _ts(answered_at)
                else:
                    print(f"    [nmg-xinxiang] 明细 {gid} HTTP {dr.status_code}")
            except Exception as e:                                          # noqa: BLE001
                print(f"    [nmg-xinxiang] 明细 {gid} 异常 {type(e).__name__}")
            if len(answer) < 5:
                continue
            out.append({
                "source": SITE["key"],
                "id": gid,
                "url": f"{ENTRY}?id={gid}",
                "question": question,
                "answer": answer,
                "asked_at": asked_at,
                "answered_at": answered_at,
                "dept": dept,
                "channel": "政民互动·反馈回应",
                "extra": {
                    "title": title,
                    "status": it.get("status"),
                    "platform": "xinxiang（内蒙古自建）",
                    "answer_kind": "办理答复（含办理单位）",
                },
            })
        if total and len(out) >= total:
            break
        if len(rows) < PAGE_SIZE:
            break
        page += 1
        time.sleep(PAUSE)
    print(f"    [nmg-xinxiang] 收 {len(out)} 条")
    return out
