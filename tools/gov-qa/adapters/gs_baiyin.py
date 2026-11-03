"""适配器：**白银市·政民互动（jpaas-jact 平台）**。

## 站点事实（2026-10-08 实测，worker-gansu）
 · 白银门户 `www.baiyin.gov.cn` 的「市长信箱 / 我对书记说 / 县长信箱…」聚合在
   **jpaas-jact-web-server**，引擎见 `_jpaas_jact_common.py`（与甘肃临夏、山东多市同构）。
 · 列表 `find-mail-pub-list?platformIid=<pid>&pageNum=<p>&pageSize=<n>`：
   `platformIid`=**全平台聚合**（实测 count=1889）；`platformUid` 是子平台（仅 273）。
 · 详情走 JSON 接口 `find-transact-detail?transactId=<iid>`：问题在
   `transactData[fieldName=content]`，答复取 `transactOpinion[]` 最后一个非占位项。
 · ⚠ 详情 `transactData` 含 `mphone`/`cardNo` 等隐私字段 —— 引擎只取 title/content。
"""
from __future__ import annotations

from adapters._jpaas_jact_common import harvest_jpaas

SITE = {
    "key": "gs-baiyin",
    "name": "白银市·政民互动（市长信箱）",
    "kind": "api",
    "level": "city",
    "entry": "https://www.baiyin.gov.cn/zmhd/",
    "status": "ok",
    "note": "jpaas-jact 平台（platformIid 聚合，count=1889）；pageNum/pageSize 分页；JSON 详情",
}

BASE = "https://www.baiyin.gov.cn"
PLATFORM_IID = "dc0a47c54dce496a9cc6321fac5a973a"
REFERER = "https://www.baiyin.gov.cn/"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """翻页取白银政民互动已答复留言（问题 + 答复原文）。"""
    return harvest_jpaas(fetch, SITE=SITE, base=BASE, platform_key="platformIid",
                         platform_value=PLATFORM_IID, referer=REFERER, limit=limit)
