"""适配器：**成都市·政民互动（四川政务服务网平台，绕过瑞数 WAF）**。

## 站点事实（2026-10-09 实测，证据 recon/city-sc-probe44.txt）
 · ★ 成都主站 `www.chengdu.gov.cn` 及其全部子域（cd12345 / 12345 / wlzl / m.chengdu.gov.cn）
   被**瑞数 WAF** 拦（全 412，带 `Set-Cookie: azSsQE5NvspcO=…`）。
 · 突破口：**四川一体化政务服务网「政民互动」**（`www.sczwfw.gov.cn/cns-bmfw-websdt/…/peogovinteract/`）
   按 `areaCode=510100000000`（成都）过滤，返回成都全市 咨询/建议/投诉 工单。
 · 接口与「加密可绕」细节见 `adapters/_sczwfw_common.py`。
 · 实测总量：咨询 33366 + 建议 1664 + 投诉 7875 ≈ **4.3 万条**。
 · 样例：`ZMHD995100002026091500143`「如何验证中级职称的真假」→ 市城市运行和政务服务办答复。
"""
from __future__ import annotations

from adapters._sczwfw_common import harvest_sczwfw

SITE = {
    "key": "sc-chengdu",
    "name": "成都市·政民互动（四川政务服务网）",
    "kind": "api",
    "level": "city",
    "entry": "https://www.sczwfw.gov.cn/cns-bmfw-websdt/pages/website/scwebsit/pages/peogovinteract/interact.html?areaCode=510100000000",
    "status": "ok",
    "note": "★ 成都主站被瑞数拦；改走四川政务服务网政民互动（areaCode=510100000000），咨询33366+建议1664+投诉7875。详情接口不带 encrypt 头回明文",
}

AREA_CODE = "510100000000"
CITY = "成都市"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    return harvest_sczwfw(fetch, source=SITE["key"], area_code=AREA_CODE, city=CITY, limit=limit)
