"""适配器：**徐州市·政民互动·来信选登（EWB 平台）**。

## 站点事实（2026-10-09 实测，证据 recon/city-js-probe2.txt / city-js-probe3.txt）
 · 门户 `www.xz.gov.cn` 政民互动 → 来信选登
   `https://www.xz.gov.cn/004/004005/selectList.html`。
 · EWB（Epoint Web Builder，`/js/webBuilderCommon.js` 定义
   `siteInfo={siteGuid:"7eb5f7f1-9041-43ad-8e13-8fcb82ea831a",projectName:"/EWB-FRONT"}`）。
 · 列表：`POST /EWB-FRONT/rest/letterlistaction/getLetterInfoListXZ`
     form 单字段 `params=<JSON>`，`{siteGuid, searchTitle:"", pageIndex:<偏移>, pageSize:10}`
     → `{"RowCount":1430,"Table":[{ROWGUID, subject, mailtype, bm, consultflowsn,
        postdate, operatedate}, …]}`。
 · 明细：`POST /EWB-FRONT/rest/frontAppNotNeedLoginAction/getLetterDetail`
     form `params={siteGuid, infoGuid:<ROWGUID>}`
     → `custom.data={subject, content(问题), replycontent(答复), postdate, operatedate,
        rowguid, consultflowsn}`。
 · ⚠ 两个 EWB 坑：① 必须 POST + `params=JSON`（GET 405，平铺字段 400）；
   ② ★ `pageIndex` 是**起始记录偏移量**（0,10,20…），不是页码 —— 传页码会每页只滑 1 条、
   漏 89%（与河北 EWB 同坑，见 `heb_szj.py`）。
 · 样例：来信「徐州市以发展玉米产品加强农旅融合的建议」→ 市农业农村局答复。
"""
from __future__ import annotations

import json
import re
import time

SITE = {
    "key": "js-xuzhou",
    "name": "徐州市·政民互动·来信选登（EWB）",
    "kind": "api",
    "level": "city",
    "entry": "https://www.xz.gov.cn/004/004005/selectList.html",
    "status": "ok",
    "note": "EWB：POST getLetterInfoListXZ（pageIndex=记录偏移）+ getLetterDetail；RowCount≈1430",
}

BASE = "https://www.xz.gov.cn"
LIST_URL = BASE + "/EWB-FRONT/rest/letterlistaction/getLetterInfoListXZ"
DETAIL_URL = BASE + "/EWB-FRONT/rest/frontAppNotNeedLoginAction/getLetterDetail"
SITE_GUID = "7eb5f7f1-9041-43ad-8e13-8fcb82ea831a"
REFERER = SITE["entry"]
PAGE_SIZE = 10
PAUSE = 1.5
TAG_RE = re.compile(r"<[^>]+>")


def _clean(html: str | None) -> str:
    import html as _h
    if not html:
        return ""
    return _h.unescape(re.sub(r"\s+", " ", TAG_RE.sub(" ", html))).strip()


def _post(fetch, url: str, payload: dict):
    return fetch.post(url, data={"params": json.dumps(payload)},
                      headers={"Referer": REFERER})


def harvest(fetch, *, limit: int | None = None, max_pages: int = 300) -> list[dict]:
    """翻页取徐州来信选登（问题 + 答复原文）。"""
    out: list[dict] = []
    seen: set[str] = set()
    total = None
    for page in range(max_pages):
        if limit and len(out) >= limit:
            break
        if page:
            time.sleep(PAUSE)
        r = _post(fetch, LIST_URL, {"siteGuid": SITE_GUID, "searchTitle": "",
                                    "pageIndex": page * PAGE_SIZE, "pageSize": PAGE_SIZE})
        if getattr(r, "status_code", 0) != 200:
            print(f"    [{SITE['key']}] 列表第 {page} 页 HTTP "
                  f"{getattr(r, 'status_code', '?')}（停）")
            break
        try:
            j = r.json()
        except Exception:                                                   # noqa: BLE001
            print(f"    [{SITE['key']}] 列表第 {page} 页非 JSON（停）")
            break
        rows = j.get("Table") or []
        if total is None:
            total = j.get("RowCount")
            print(f"    [{SITE['key']}] 来信选登总数 RowCount={total}")
        if not rows:
            break
        for it in rows:
            if limit and len(out) >= limit:
                return out
            guid = str(it.get("ROWGUID") or "").strip()
            if not guid or guid in seen:
                continue
            seen.add(guid)
            time.sleep(PAUSE)
            try:
                dr = _post(fetch, DETAIL_URL, {"siteGuid": SITE_GUID, "infoGuid": guid})
                data = ((dr.json().get("custom") or {}).get("data") or {}) \
                    if getattr(dr, "status_code", 0) == 200 else {}
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{SITE['key']}] 明细 {guid}：{type(e).__name__}（跳过）")
                continue
            question = _clean(data.get("content")) or _clean(it.get("subject"))
            answer = _clean(data.get("replycontent"))
            if len(answer) < 10:
                continue
            out.append({
                "source": SITE["key"],
                "id": guid,
                "url": f"{BASE}/viewDetails.html?rowguid={guid}",
                "question": question,
                "answer": answer,
                "asked_at": data.get("postdate") or it.get("postdate") or None,
                "answered_at": data.get("operatedate") or it.get("operatedate") or None,
                "dept": it.get("bm") or None,
                "channel": "政民互动·来信选登",
                "extra": {
                    "title": _clean(data.get("subject") or it.get("subject")),
                    "mail_number": it.get("consultflowsn"),
                    "mail_type": it.get("mailtype"),
                    "platform": "EWB(Epoint Web Builder)",
                    "site_guid": SITE_GUID,
                },
            })
        if total and (page + 1) * PAGE_SIZE >= int(total):
            break
    print(f"    [{SITE['key']}] 收 {len(out)} 条")
    return out
