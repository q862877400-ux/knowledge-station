"""适配器：**攀枝花市·政民互动（四川政务服务网平台，areaCode=510400000000）**。

## 站点事实
四川政务服务网「政民互动」按 `areaCode` 过滤，**攀枝花市**（`areaCode=510400000000`）
净增量约 **1292 条**（与本地门户源不重叠）。基座、列表/详情接口、
「不带 encrypt 头即回明文」的绕行细节见 `adapters/_sczwfw_common.py`。

## 为什么 key 带 `-zwfw` 后缀
本省门户（`sc-panzhihua`）与省平台（本适配器）是**两套源**、id 空间不同，
用 `sc-panzhihua-zwfw` 避免与本地源冲突。
"""
from __future__ import annotations

from adapters._sczwfw_common import harvest_sczwfw

SITE = {
    "key": "sc-panzhihua-zwfw",
    "name": "攀枝花市·政民互动（四川政务服务网）",
    "kind": "api",
    "level": "city",
    "entry": "https://www.sczwfw.gov.cn/cns-bmfw-websdt/pages/website/scwebsit/pages/peogovinteract/interact.html?areaCode=510400000000",
    "status": "ok",
    "note": "四川政务服务网政民互动 areaCode=510400000000，净增量约 1292 条（咨询10/建议15/投诉20）",
}

AREA_CODE = "510400000000"
CITY = "攀枝花市"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    return harvest_sczwfw(fetch, source=SITE["key"], area_code=AREA_CODE, city=CITY, limit=limit)
