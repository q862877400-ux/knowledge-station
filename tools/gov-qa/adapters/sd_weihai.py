"""适配器：**威海市·政民互动·市长信箱（jact 平台）**。

## 站点事实（2026-10-08 实测，证据 recon/sd-city2-hunt.txt / probe.txt）
 · 门户 `www.weihai.gov.cn` 政民互动「市长信箱」→
   `https://www.weihai.gov.cn/jact/front/mailpublist.do?sysid=61`（首页亦 http 可达）。
 · **jact（万户 hanweb）**，**http**；列表用 **GET**（POST 返回空）。
 · 实测 `sysid=61` **totalRecord=936**。明细 `mailpubdetail.do?transactId=&sysid=61`。
"""
from __future__ import annotations

from adapters._sd_jact import harvest_jact_sd

SITE = {
    "key": "sd-weihai",
    "name": "威海市·政民互动·市长信箱（jact）",
    "kind": "api",
    "level": "city",
    "entry": "http://www.weihai.gov.cn/jact/front/mailpublist.do?sysid=61",
    "status": "ok",
    "note": "jact 平台（http，GET 列表），sysid=61，totalRecord=936",
}

BASE = "http://www.weihai.gov.cn"
SYSID = "61"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """采威海市 jact 市长信箱（问题 + 答复全文）。"""
    return harvest_jact_sd(fetch, SITE=SITE, base=BASE, sysid=SYSID,
                           list_method="GET", limit=limit)
