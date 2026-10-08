"""适配器：**南充市·政民互动·市长信箱（IGI 平台）**。

## 站点事实（2026-10-09 实测，证据 recon/city-sc-probe21/22.txt）
 · 南充门户 `www.nanchong.gov.cn` 的 IGI 接口与 `_igi_common.py` **完全同构**，
   **零改造复用基座**：
     GET https://www.nanchong.gov.cn/IGI/nbhd/openGovmsgbox.do
         ?method=listGovmsgboxs&siteId=4&order=1&appId=1&pageIndex=1&pageSize=20
     明细 GET …?method=viewGovmsgbox&siteId=4&metadataId=<id>
       → datas.REPLYS[].REPLYHTMLCONTENT = 官方答复原文。
 · siteId/appId 来自 `/images/zmhd.js` 的 `countGovmsgboxs` 调用（`siteId:4, appId:1`）。
 · ⚠ **须带 Referer** `https://www.nanchong.gov.cn/hdjl/`。
 · 列表 `datas.pageInfo.totalResults` 为总数（siteId=4 实测 ≈2324）。
 · ★ 列表带 PROVINCE/CITY/AREA 三级归属。
"""
from __future__ import annotations

from adapters._igi_common import harvest_igi

SITE = {
    "key": "sc-nanchong",
    "name": "南充市·政民互动·市长信箱（IGI）",
    "kind": "api",
    "level": "city",
    "entry": "https://www.nanchong.gov.cn/hdjl/",
    "status": "ok",
    "note": "IGI 平台（www.nanchong.gov.cn/IGI）siteId=4/appId=1；须 Referer；带省/市/区三级归属；total≈2324",
}

BASE = "https://www.nanchong.gov.cn/IGI"
REFERER = "https://www.nanchong.gov.cn/hdjl/"
APP_ID = "1"
GROUP_ID = None

# 实测命中的 siteId（2026-10-09）；数字为枚举当日 totalResults，采集时以接口为准。
SITE_IDS = ["4"]


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """遍历南充 IGI 各 siteId，取已答复信件（含答复原文与三级归属）。"""
    out: list[dict] = []
    for sid in SITE_IDS:
        if limit and len(out) >= limit:
            break
        sub_site = dict(SITE)
        sub_site["key"] = f"{SITE['key']}-{sid}"
        rows = harvest_igi(fetch, SITE=sub_site, base=BASE, site_id=sid, app_id=APP_ID,
                           group_id=GROUP_ID, referer=REFERER,
                           limit=(limit - len(out)) if limit else None, max_pages=200)
        for r in rows:                      # 基座默认口径按「厅长信箱」，本市站改为政民互动
            r["channel"] = "政民互动·市长信箱"
            r["extra"]["answer_kind"] = "办理答复（市长信箱）"
        out.extend(rows)
    return out
