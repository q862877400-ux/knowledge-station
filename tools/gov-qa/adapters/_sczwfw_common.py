"""四川政务服务网「政民互动」平台基座（**全省按 areaCode 过滤，绕过瑞数 WAF**）。

## 背景（2026-10-09 实测，证据 recon/city-sc-probe44.txt）
 · 成都主站 `www.chengdu.gov.cn` 全子域被**瑞数 WAF** 拦（412）。突破口是
   **四川一体化政务服务网** 的「政民互动」模块：每个地市门户 `xxs.sczwfw.gov.cn/col/colNNNNN`
   都 iframe 嵌同一个 SPA：
     `https://www.sczwfw.gov.cn/cns-bmfw-websdt/pages/website/scwebsit/pages/peogovinteract/interact.html?areaCode=<12位区划码>`
 · 该 SPA 的真实接口（从 `interact.js` / `moreconsult.js` / `boot.min.js` 反推）：
   · 列表：`POST {API}getInteractCaseInfoListByCondition`
       body `{"pageSize":N,"currentPageIndex":P,"title":"","rqstType":"10|15|20",
              "webrqsttime":"","areaCode":"<12位>","iszwfw":"1"}`
       → `{"status":{...},"custom":{"total":T,"infoList":[{"rqsttitle","handleurl",
            "webrqsttime","replytime","publictime","answerou"}]}}`
   · 详情：`POST {API}getCaseInfoDeatil` body `{"token":"","params":{"caseguid":"<uuid>"}}`
       → `{"custom":{"rqsttitle","rqstcontent","answercontent","answerou",
            "rqsttime","answertime","finishtime","serialnum","cstatus","rqstperson"}}`
 · ★★ **加密可绕**：前端默认给请求 SM2 加密、响应 AES 解密（`CnsAESUtil`：
       key=`bmfw20190227wfmb`/iv=`2019227cnswsbsdt`；`decryptNew`：key=`qnbpwgttcfv96fgw`/iv=`5141928399038306`）。
       **实测：只要不带 `encrypt` 请求头，服务端就回明文 JSON** —— 无需实现国密。
 · rqstType：`10`=咨询 / `15`=建议 / `20`=投诉。成都（510100000000）实测
   咨询 33366 + 建议 1664 + 投诉 7875 ≈ **4.3 万条**。
"""
from __future__ import annotations

import json
import re
import time

API = "https://www.sczwfw.gov.cn/cns-bmfw-websdt/rest/cnspublic/scwebsitecaseinfoaction/"
LIST_URL = API + "getInteractCaseInfoListByCondition"
DETAIL_URL = API + "getCaseInfoDeatil"
REFERER = ("https://www.sczwfw.gov.cn/cns-bmfw-websdt/pages/website/scwebsit/pages/"
           "peogovinteract/interact.html")
PAUSE = 0.8
PAGE_SIZE = 20
RQST_TYPES = [("10", "咨询"), ("15", "建议"), ("20", "投诉")]

_CGUID_RE = re.compile(r"cguid=([0-9a-fA-F\-]+)")


def _clean(s) -> str:
    if not s:
        return ""
    return str(s).replace("\r\n", "\n").replace("\r", "\n").strip()


def harvest_sczwfw(fetch, *, source: str, area_code: str, city: str,
                   limit: int | None = None, page_size: int = PAGE_SIZE,
                   max_pages: int = 3000, rqst_types=None) -> list[dict]:
    """遍历 咨询/建议/投诉 三类工单 → 逐条详情解析问答。"""
    rqst_types = rqst_types or RQST_TYPES
    out: list[dict] = []
    seen: set[str] = set()
    hdrs = {"Content-Type": "json/application", "Referer": REFERER}
    for rtype, tname in rqst_types:
        if limit and len(out) >= limit:
            break
        total_pages = None
        for page in range(1, max_pages + 1):
            if limit and len(out) >= limit:
                return out
            if total_pages is not None and page > total_pages:
                break
            body = {"pageSize": page_size, "currentPageIndex": page, "title": "",
                    "rqstType": rtype, "webrqsttime": "", "areaCode": area_code,
                    "iszwfw": "1"}
            try:
                r = fetch.post(LIST_URL, data=json.dumps(body), headers=hdrs)
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{source}] {tname} 第 {page} 页：{type(e).__name__}（停）")
                break
            if getattr(r, "status_code", 0) != 200:
                print(f"    [{source}] {tname} 第 {page} 页 HTTP "
                      f"{getattr(r, 'status_code', '?')}（停）")
                break
            try:
                j = r.json()
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{source}] {tname} 第 {page} 页非 JSON：{type(e).__name__}（停）")
                break
            cust = j.get("custom") or {}
            rows = cust.get("infoList") or []
            if total_pages is None:
                total = int(cust.get("total") or 0)
                total_pages = (total + page_size - 1) // page_size or None
                print(f"    [{source}] {city}·{tname} 共 {total} 条 / {total_pages} 页")
            if not rows:
                break
            new = 0
            for it in rows:
                if limit and len(out) >= limit:
                    return out
                hu = it.get("handleurl") or ""
                m = _CGUID_RE.search(hu)
                if not m:
                    continue
                cg = m.group(1)
                if cg in seen:
                    continue
                seen.add(cg)
                new += 1
                try:
                    vr = fetch.post(DETAIL_URL,
                                    data=json.dumps({"token": "", "params": {"caseguid": cg}}),
                                    headers=hdrs)
                    vd = (vr.json().get("custom") or {}) if getattr(vr, "status_code", 0) == 200 else {}
                except Exception as e:                                      # noqa: BLE001
                    print(f"    [{source}] 详情 {cg[:8]}：{type(e).__name__}（跳过）")
                    continue
                answer = _clean(vd.get("answercontent"))
                if len(answer) < 10:            # 未答复，跳过
                    continue
                title = _clean(vd.get("rqsttitle") or it.get("rqsttitle"))
                content = _clean(vd.get("rqstcontent"))
                question = f"{title}\n{content}" if title and content else (content or title)
                out.append({
                    "source": source,
                    "id": cg,
                    "url": hu,
                    "question": question,
                    "answer": answer,
                    "asked_at": _clean(vd.get("rqsttime") or it.get("webrqsttime")) or None,
                    "answered_at": _clean(vd.get("answertime") or vd.get("finishtime")
                                          or it.get("replytime")) or None,
                    "dept": _clean(vd.get("answerou") or it.get("answerou")) or None,
                    "channel": f"政民互动·{tname}",
                    "extra": {
                        "title": title,
                        "serial": vd.get("serialnum"),
                        "status": vd.get("cstatus"),
                        "area_code": area_code,
                        "city": city,
                        "platform": "四川政务服务网·政民互动（sczwfw.gov.cn，无 encrypt 头回明文）",
                    },
                })
                time.sleep(PAUSE)
            if new == 0:
                break
            time.sleep(PAUSE)
    print(f"    [{source}] 收 {len(out)} 条")
    return out
