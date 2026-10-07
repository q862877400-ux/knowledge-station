"""湖南全省统一互动平台（hd.hunan.gov.cn）· 共用采集基座。

## 接口（2026-10-07 从湖南省生态环境厅 `hdjl_index.js` 挖出并实测）
```
GET https://hd.hunan.gov.cn/communication/api-mailbox/frontMail/mailList2ie
    ?data={"pageNum":N,"pageSize":M,"sortMap":{"createTime":"desc"},
           "params":{"deptId":"<32位hex>","phone":"","searchCode":"",
                     "status":"","siteNo":"","siteUrl":""}}
→ {"status":"success","data":{"total":…,"pageTotal":…,"rows":[…]}}
```
**rows 自带答复全文**（`replyContent`，HTML）——列表接口即全量，不必抓明细页。

## 这是"一片"而不是"一个站"
湖南**所有**厅局都走这个平台，差别只有 `deptId`（在各厅官网互动页的
`hdjl_index.js` 里，`var deptId = "…"`）。新部门 = 复制一个薄适配器、
填它的 deptId，见 `hunan_sthjt.py` / `hunan_yjt.py`。

## 记录映射
 · `answer`：`replyContent` 的**去标签文本**（与 mem_gov 同口径：保留文字原样、
   不摘要、不动《》点名的依据；HTML 原样本身在平台接口里随时可重取）。
 · `channel`：`objectiveType`（咨询/投诉/感谢…）—— 该站没有传统栏目树。
 · 只收 `isPublish == 1` 且 `replyContent` 非空的行（未公开/未答复的跳过）。
"""
from __future__ import annotations

import json
import re
import time

API = "https://hd.hunan.gov.cn/communication/api-mailbox/frontMail/mailList2ie"
REFERER = "https://hd.hunan.gov.cn/"
PAGE_SIZE = 50
PAUSE = 1.5                     # 单线程、页间间隔，礼貌抓取

TAG_RE = re.compile(r"<[^>]+>")
#: 统一字段之外的原始键进 extra（fromName 是打码的提问者，一并保留）
KNOWN = ("id", "title", "replyContent", "createTime", "replyTime", "deptName",
         "objectiveType", "isPublish", "status", "serialNumber")


def _text(html: str) -> str:
    t = TAG_RE.sub(" ", html or "")
    return re.sub(r"\s+", " ", t).strip()


def harvest_hunan(fetch, *, SITE: dict, DEPT_ID: str, limit: int | None = None,
                  page_size: int = PAGE_SIZE, pause: float = PAUSE) -> list[dict]:
    """按统一记录格式返回该部门在湖南统一互动平台上的全部公开答复。"""
    out: list[dict] = []
    page, total = 1, None
    while True:
        data = {"pageNum": page, "pageSize": page_size,
                "sortMap": {"createTime": "desc"},
                "params": {"deptId": DEPT_ID, "phone": "", "searchCode": "",
                           "status": "", "siteNo": "", "siteUrl": ""}}
        r = fetch(API, params={"data": json.dumps(data, ensure_ascii=False)},
                  headers={"Referer": REFERER})
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        try:
            j = r.json()
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 第 {page} 页不是 JSON（{type(e).__name__}，停）")
            break
        if j.get("status") != "success":
            print(f"    [{SITE['key']}] 第 {page} 页 status={j.get('status')}（停）")
            break
        d = j.get("data") or {}
        rows = d.get("rows") or []
        if total is None:
            total = d.get("total")
            print(f"    [{SITE['key']}] platform total={total} "
                  f"pageTotal={d.get('pageTotal')}")
        if not rows:
            break
        for it in rows:
            if it.get("isPublish") != 1:
                continue
            answer = _text(it.get("replyContent") or "")
            if not answer:
                continue
            out.append({
                "source": SITE["key"],
                "id": str(it.get("id") or it.get("serialNumber") or ""),
                "url": None,            # 平台明细页是站内 iframe，无独立公开 URL
                "question": it.get("title"),
                "answer": answer,
                "asked_at": it.get("createTime"),
                "answered_at": it.get("replyTime"),
                "dept": it.get("deptName"),
                "channel": it.get("objectiveType"),
                "extra": {k: v for k, v in it.items() if k not in KNOWN},
            })
        if limit and len(out) >= limit:
            return out[:limit]
        if total and page * page_size >= total:
            break
        page += 1
        time.sleep(pause)
    return out
