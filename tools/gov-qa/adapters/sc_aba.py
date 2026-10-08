"""适配器：**阿坝州·互动交流·领导信箱（通信平台 /communication/api-mailbox）**。

## 站点事实（2026-10-09 实测，证据 recon/city-sc-probe22/23.txt）
 · 互动栏目：`/abazhou/c101014/hd_mailbox.shtml`（领导信箱）、
   `/abazhou/rexian/12345rx.shtml`（12345 热线）。
 · 前端 `/abazhou/xhtml/abzrmzf/pc2025/js/abzlxxd.js` 调 —— 与绵阳/内江同款「通信平台」，
   但**本接口不需要签名**：
   · 列表：`POST /communication/api-mailbox/frontMail/mailList`
       body(JSON): `{pageNum, pageSize, sortMap:{createTime:"desc"},
                     params:{phone:"", searchCode:"", deptId:"2d7b74f66a0c4d50b6305c4e02c29510"}}`
     → `{"status":"success","data":{"total":2719,"pageNum":1,"pageSize":20,"pageTotal":136,
        "rows":[{id, serialNumber, fromName, objectiveType, deptName, title, createTime, …}]}}`
   · 详情：`GET /communication/api-mailbox/frontMail/detail?mailId=<id>`（**无需 sign**）
     → `{"status":"success","data":{title, content, deptName, createTime, objectiveType,
        replyContents:[{allName, replyContent, …}], serialNumber}}`
   ★ 答复全文在 `replyContents[].replyContent`（HTML）；`content` 是问题正文。
 · 样例：id `5eae1d32e4044924bae56149f90c57b5`「医保退休不足年限补缴」→ 阿坝州政府办答复。
"""
from __future__ import annotations

import html as _html
import re
import time

SITE = {
    "key": "sc-aba",
    "name": "阿坝州·互动交流·领导信箱",
    "kind": "api",
    "level": "city",
    "entry": "https://www.abazhou.gov.cn/abazhou/c101014/hd_mailbox.shtml",
    "status": "ok",
    "note": "POST /communication/api-mailbox/frontMail/mailList（列表 total≈2719，无需签名）+ GET …/detail?mailId=（答复）",
}

BASE = "https://www.abazhou.gov.cn"
LIST_URL = BASE + "/communication/api-mailbox/frontMail/mailList"
DETAIL_URL = BASE + "/communication/api-mailbox/frontMail/detail"
DEPT_ID = "2d7b74f66a0c4d50b6305c4e02c29510"     # = abzlxxd.js departmentId（信访局）
REFERER = SITE["entry"]
PAUSE = 1.0
PAGE_SIZE = 20

_TAG = re.compile(r"<[^>]+>")


def _clean(s) -> str:
    if not s:
        return ""
    s = re.sub(r"(?i)<br\s*/?>", "\n", str(s))
    s = re.sub(r"(?i)</p>", "\n", s)
    s = _TAG.sub("", s)
    s = _html.unescape(s)
    return s.strip()


def harvest(fetch, *, limit: int | None = None, max_pages: int = 400) -> list[dict]:
    """翻页取阿坝领导信箱；列表不含答复，逐条取详情。"""
    out: list[dict] = []
    seen: set[str] = set()
    total = None
    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            break
        body = {"pageNum": page, "pageSize": PAGE_SIZE,
                "sortMap": {"createTime": "desc"},
                "params": {"phone": "", "searchCode": "", "deptId": DEPT_ID}}
        try:
            r = fetch.post(LIST_URL, json=body, headers={"Referer": REFERER})
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
        rows = d.get("rows") or []
        if total is None:
            total = d.get("total")
            print(f"    [{SITE['key']}] 信件总数 total={total}")
        if not rows:
            break
        for it in rows:
            if limit and len(out) >= limit:
                return out
            sid = str(it.get("id") or "").strip()
            if not sid or sid in seen:
                continue
            seen.add(sid)
            try:
                dr = fetch(DETAIL_URL, params={"mailId": sid},
                           headers={"Referer": REFERER})
                dd = (dr.json() or {}).get("data") or {}
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{SITE['key']}] 详情 {sid}：{type(e).__name__}（跳过）")
                continue
            reps = dd.get("replyContents") or []
            answer = "\n".join(_clean(x.get("replyContent")) for x in reps
                               if isinstance(x, dict) and x.get("replyContent")).strip()
            if len(answer) < 10:            # 未答复，跳过
                continue
            title = (it.get("title") or dd.get("title") or "").strip()
            content = _clean(dd.get("content"))
            question = title if not content else f"{title}\n{content}"
            dept = (it.get("deptName") or dd.get("deptName")
                    or (reps[0].get("allName") if reps else None))
            out.append({
                "source": SITE["key"],
                "id": sid,
                "url": SITE["entry"],
                "question": question,
                "answer": answer,
                "asked_at": (it.get("createTime") or dd.get("createTime") or None),
                "answered_at": None,
                "dept": (dept or "").strip() or None,
                "channel": "互动交流·领导信箱",
                "extra": {
                    "title": title,
                    "objective_type": it.get("objectiveType") or dd.get("objectiveType"),
                    "serial_number": it.get("serialNumber") or dd.get("serialNumber"),
                    "platform": "阿坝州 通信平台 api-mailbox（列表+详情，免签名）",
                },
            })
            time.sleep(PAUSE)
        if total and page * PAGE_SIZE >= int(total):
            break
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
