"""适配器：**济南市·互动交流·回应关切（jpaas-jact 网关，JSON 接口）**。

## 站点事实（2026-10-08 实测，证据 recon/sd-city-probe4.txt + 逐接口实测）
 · 门户 `www.jinan.gov.cn` 互动交流「回应关切」→
   `http://www.jinan.gov.cn/api-gateway/jpaas-jact-web-server/front/mail-pub-list.do?...`
 · 该页是**空壳**，列表由 layui 经 `.../default-template/page.js` 拉取（接口见 `_sd_jact_gw.py`）。
 · platformUid=`HTMi0SM6aXpdnEJDZH931`，submitTargetIds=47 个部门 id。
 · ⚠ **不传 govOpen**：`govOpen=1` 只回 250 条，留空回 **6654** 条（实测）。
 · 实测 count=6654；样例「关于2026年无线电能力验证举办」→「济南市工业和信息化局」答复。
"""
from __future__ import annotations

from adapters._sd_jact_gw import harvest_jact_gateway

SITE = {
    "key": "sd-jinan",
    "name": "济南市·互动交流·回应关切（jact网关）",
    "kind": "api",
    "level": "city",
    "entry": "http://www.jinan.gov.cn/col/col26/index.html",
    "status": "ok",
    "note": "jpaas-jact 网关（http），find-mail-pub-list，count=6654（勿传 govOpen=1）",
}

BASE = "http://www.jinan.gov.cn/api-gateway/jpaas-jact-web-server/front"
PLATFORM_UID = "HTMi0SM6aXpdnEJDZH931"
SUBMIT_TARGET_IDS = (
    "0114,0171,0115,0116,0117,0118,0119,0120,0121,0123,0124,0126,0127,0128,0130,0132,"
    "0134,0135,0140,0141,0144,0146,0148,0151,0156,0133,0159,0160,0163,0161,0137,0166,"
    "0138,0149,0513,2203,2414,2422,0515,2479,2583,0145,622fntKBvD,sk7AtT5lCN,0147,"
    "1BF7PVWSQb,0152,0324,1921"
)


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """采济南「回应关切」（问题 + 答复全文）。"""
    return harvest_jact_gateway(fetch, SITE=SITE, base=BASE, platform_uid=PLATFORM_UID,
                                submit_target_ids=SUBMIT_TARGET_IDS, gov_open="",
                                limit=limit)
