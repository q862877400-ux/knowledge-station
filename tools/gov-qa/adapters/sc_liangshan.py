"""适配器：**凉山州·12345 政务服务便民热线·信件选登（慧兰 eportal portlet）**。

## 站点事实（2026-10-09 实测，证据 recon/city-sc-probe30.txt）
 · 平台独立域：`http://12345.lsz.gov.cn`（凉山州 12345 热线，慧兰/Huilan eportal）。
 · 「信件选登」页 `/notice/xjxd/index.html` 的列表由 portlet 异步加载：
   · 列表：`GET http://12345.lsz.gov.cn/eportal/ui`
       params: `moduleId=5`、`portal.url=/portlet/workOrder!queryWorkOrderList.portlet`、
               `current`（页码,1 基）、`size`（每页）
     → JSON：`{"data":{"current":1,"total":96,"pages":10,"size":10,"records":[{…}]}}`
   · 分页参数名是 **`current`**（`pageIndex`/`pageNum`/`page` 均被忽略）。
   ★ **列表已含问答全文**，无需详情接口：
     · `bizId` 主键、`stringTitle`/`organizeTitle` 标题
     · `stringContent` **问题正文**、`transactResult`（=`commentDetail`）**答复全文**
     · `createTime` 来信、`dofinishTime` 办结
     · `undertakeOpinion`（JSON 串，含 `deptName` 承办单位）、`businessSource` 来源（voice…）
     · `stringHotspot` 关键词。
 · 样例：bizId `202609906100`「咨询独生子女补贴问题」→ 冕宁县卫健局答复。
"""
from __future__ import annotations

import html as _html
import json
import re
import time

SITE = {
    "key": "sc-liangshan",
    "name": "凉山州·12345 便民热线·信件选登",
    "kind": "api",
    "level": "city",
    "entry": "http://12345.lsz.gov.cn/notice/xjxd/index.html",
    "status": "ok",
    "note": "慧兰 eportal portlet：GET /eportal/ui?portal.url=/portlet/workOrder!queryWorkOrderList.portlet&current=&size=（列表自带问答，total≈96）",
}

BASE = "http://12345.lsz.gov.cn"
LIST_URL = BASE + "/eportal/ui"
PORTAL = "/portlet/workOrder!queryWorkOrderList.portlet"
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
    s = s.replace("\u00a0", " ").replace("\u2002", " ").replace("\u2003", " ")
    return re.sub(r"[ \t]+\n", "\n", s).strip()


def _dept(it: dict) -> str | None:
    raw = it.get("undertakeOpinion")
    if isinstance(raw, str) and raw.strip():
        try:
            arr = json.loads(raw)
            if isinstance(arr, list) and arr:
                name = (arr[0] or {}).get("deptName")
                if name:
                    return str(name).strip()
        except Exception:                                                   # noqa: BLE001
            pass
    return None


def harvest(fetch, *, limit: int | None = None, max_pages: int = 100) -> list[dict]:
    """翻页取凉山 12345 信件选登；列表自带问答，无需详情。"""
    out: list[dict] = []
    seen: set[str] = set()
    total = None
    for page in range(1, max_pages + 1):
        if limit and len(out) >= limit:
            break
        try:
            r = fetch(LIST_URL, params={
                "moduleId": 5, "portal.url": PORTAL,
                "current": page, "size": PAGE_SIZE,
            }, headers={"Referer": REFERER})
        except Exception as e:                                              # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页：{type(e).__name__}（停）")
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
        rows = d.get("records") or []
        if total is None:
            total = d.get("total")
            print(f"    [{SITE['key']}] 信件总数 total={total}")
        if not rows:
            break
        for it in rows:
            if limit and len(out) >= limit:
                return out
            sid = str(it.get("bizId") or it.get("id") or "").strip()
            if not sid or sid in seen:
                continue
            seen.add(sid)
            answer = _clean(it.get("transactResult") or it.get("commentDetail"))
            if len(answer) < 10:            # 未答复，跳过
                continue
            title = (it.get("stringTitle") or it.get("organizeTitle") or "").strip()
            content = _clean(it.get("stringContent"))
            question = title if not content else f"{title}\n{content}"
            out.append({
                "source": SITE["key"],
                "id": sid,
                "url": SITE["entry"],
                "question": question,
                "answer": answer,
                "asked_at": (it.get("createTime") or None),
                "answered_at": (it.get("dofinishTime") or None),
                "dept": _dept(it),
                "channel": "12345 便民热线·信件选登",
                "extra": {
                    "title": title,
                    "provincial_number": it.get("stringProvincialNumber"),
                    "business_source": it.get("businessSource"),
                    "hotspot": it.get("stringHotspot"),
                    "platform": "凉山州 慧兰 eportal portlet（workOrder!queryWorkOrderList）",
                },
            })
        if total and page * PAGE_SIZE >= int(total):
            break
        time.sleep(PAUSE)
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
