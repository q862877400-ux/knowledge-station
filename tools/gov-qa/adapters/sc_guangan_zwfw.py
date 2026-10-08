"""适配器：**广安市·政民互动（四川政务服务网平台，areaCode=511600000000）**。

## 站点事实
四川政务服务网「政民互动」按 `areaCode` 过滤，**广安市**（`areaCode=511600000000`）
净增量约 **536 条**（与本地门户源不重叠）。基座、列表/详情接口、
「不带 encrypt 头即回明文」的绕行细节见 `adapters/_sczwfw_common.py`。

## 为什么 key 带 `-zwfw` 后缀
本省门户（`sc-guangan`）与省平台（本适配器）是**两套源**、id 空间不同，
用 `sc-guangan-zwfw` 避免与本地源冲突。
"""
from __future__ import annotations

from adapters._sczwfw_common import harvest_sczwfw

SITE = {
    "key": "sc-guangan-zwfw",
    "name": "广安市·政民互动（四川政务服务网）",
    "kind": "api",
    "level": "city",
    "entry": "https://www.sczwfw.gov.cn/cns-bmfw-websdt/pages/website/scwebsit/pages/peogovinteract/interact.html?areaCode=511600000000",
    "status": "ok",
    "note": "四川政务服务网政民互动 areaCode=511600000000，净增量约 536 条（咨询10/建议15/投诉20）",
}

AREA_CODE = "511600000000"
CITY = "广安市"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    return harvest_sczwfw(fetch, source=SITE["key"], area_code=AREA_CODE, city=CITY, limit=limit)
