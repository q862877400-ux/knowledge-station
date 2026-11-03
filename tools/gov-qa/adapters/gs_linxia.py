"""适配器：**临夏回族自治州·政民互动（书记选登 / 州长选登，jpaas-jact 平台）**。

## 站点事实（2026-10-08 实测，worker-gansu）
 · 临夏州门户 `www.linxia.gov.cn` 的「政民互动 → 书记选登(`/lxz/zmhd/xjxd/`) /
   州长选登(`/lxz/zmhd/zzxjxd/`)」由外部 JS（`ajaxfun`）调 **jpaas-jact 网关**：
     GET https://www.linxia.gov.cn/api-gateway/jpaas-jact-web-server/front/find-mail-pub-list
         ?platformUid=<colid>&type=2&pageSize=1000&orderType=2   → JSON
     详情 `…/interface/transact/find-transact-detail?transactId=<iid>` → JSON
     （与甘肃白银、山东多市同构，复用 `_jpaas_jact_common.py`。）
 · 两个栏目的 `platformUid`（colid，取自各栏目页内联 JS 的 `ajaxfun('<colid>',…)`）：
   · 书记选登 `61cd90cc51d7455b930baf42d28012c5`（实测 count=46）
   · 州长选登 `ef3fd664fe5b47bb9626f5f21caebd0e`（实测 count=39）
 · 站点 JS 一次性 `pageSize=1000` 拉全量（count 远小于 1000），故每栏目一页即可。
"""
from __future__ import annotations

from adapters._jpaas_jact_common import harvest_jpaas

SITE = {
    "key": "gs-linxia",
    "name": "临夏州·政民互动（书记选登·州长选登）",
    "kind": "api",
    "level": "city",
    "entry": "http://www.linxia.gov.cn/lxz/zmhd/xjxd/",
    "status": "ok",
    "note": "jpaas-jact 网关；两栏目 platformUid（书记 46 / 州长 39）；站点 JS 用 pageSize=1000 一次拉全",
}

BASE = "https://www.linxia.gov.cn"
# ⚠ 详情接口要求 **https 同源 Referer**：用 http Referer 会返回空 data（实测踩过）
REFERER = "https://www.linxia.gov.cn/"
LIST_EXTRA = {"type": "2", "orderType": "2"}
PAGE_SIZE = 1000

#: (栏目名, platformUid) —— colid 取自各栏目页内联 JS。
COLUMNS = [
    ("书记选登", "61cd90cc51d7455b930baf42d28012c5"),
    ("州长选登", "ef3fd664fe5b47bb9626f5f21caebd0e"),
]


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """取临夏书记/州长选登的已答复留言（问题 + 答复原文）。`limit` 为总条数上限。"""
    out: list[dict] = []
    for name, colid in COLUMNS:
        if limit and len(out) >= limit:
            break
        sub_site = dict(SITE)
        # 每栏目用独立 source 后缀便于区分归属，仍统一前缀 gs-linxia。
        sub_site["key"] = f"{SITE['key']}-{name}"
        rows = harvest_jpaas(fetch, SITE=sub_site, base=BASE, platform_key="platformUid",
                             platform_value=colid, referer=REFERER, page_size=PAGE_SIZE,
                             limit=(limit - len(out)) if limit else None,
                             list_extra=LIST_EXTRA)
        out.extend(rows)
    return out
