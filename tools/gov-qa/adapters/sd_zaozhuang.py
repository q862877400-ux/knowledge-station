"""适配器：**枣庄市·政民互动·市长信箱（IGI 平台）**。

## 站点事实（2026-10-08 实测，证据 recon/sd-city-probe2.txt / probe3.txt）
 · 门户 `www.zaozhuang.gov.cn` 政民互动 `http://www.zaozhuang.gov.cn/zmhd/`；
   页面内联 JS 直接调 IGI：`http://www.zaozhuang.gov.cn/IGI/nbhd/openGovmsgbox.do`。
 · 与 `adapters/_igi_common.py` **完全同构**，参数从页面 JS 抠出：
   · base `http://www.zaozhuang.gov.cn/IGI`
   · siteId=**124**，appId=**84**，orderBy='submitTime_desc'、resultType='json'
   · **BASE 用 http**（https 证书不匹配）。
 · 实测列表第 1 页 20 条（样例「结婚问题」ISREPLY=1）；明细
   `method=viewGovmsgbox&siteId=124&metadataId=` → `datas.REPLYS[].REPLYHTMLCONTENT`（样例答复 456 字）。
 · 注：本实例列表的 PROVINCE/CITY/AREA 为空（无三级归属）。
"""
from __future__ import annotations

from adapters._igi_common import harvest_igi

SITE = {
    "key": "sd-zaozhuang",
    "name": "枣庄市·政民互动·市长信箱（IGI）",
    "kind": "api",
    "level": "city",
    "entry": "http://www.zaozhuang.gov.cn/zmhd/",
    "status": "ok",
    "note": "IGI 平台（http），siteId=124 / appId=84；须带 Referer；三级归属为空",
}

BASE = "http://www.zaozhuang.gov.cn/IGI"
REFERER = "http://www.zaozhuang.gov.cn/zmhd/"
APP_ID = "84"
GROUP_ID = None
SITE_ID = "124"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """采枣庄市 IGI 市长信箱（含答复原文）。"""
    return harvest_igi(fetch, SITE=SITE, base=BASE, site_id=SITE_ID, app_id=APP_ID,
                       group_id=GROUP_ID, referer=REFERER, limit=limit, max_pages=300)
