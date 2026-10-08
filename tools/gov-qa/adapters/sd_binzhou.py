"""适配器：**滨州市·政民互动·领导信箱（jact 平台）**。

## 站点事实（2026-10-08 实测，证据 recon/sd-city2-hunt.txt / probe.txt）
 · 门户 `www.binzhou.gov.cn` 首页「领导信箱」→
   `http://www.binzhou.gov.cn/jact/front/mailpublist.do?sysid=1206`；
   「反馈回应」→ `http://www.binzhou.gov.cn/jact/front/main.do?sysid=1007`。
 · **jact（万户 hanweb）**，**http**；列表 **GET 与 POST 均可用**（此处用 GET）。
 · 实测 `sysid=1206` **totalRecord=179**。明细 `mailpubdetail.do?transactId=&sysid=1206`。
"""
from __future__ import annotations

from adapters._sd_jact import harvest_jact_sd

SITE = {
    "key": "sd-binzhou",
    "name": "滨州市·政民互动·领导信箱（jact）",
    "kind": "api",
    "level": "city",
    "entry": "http://www.binzhou.gov.cn/jact/front/mailpublist.do?sysid=1206",
    "status": "ok",
    "note": "jact 平台（http，GET/POST 均可），sysid=1206，totalRecord=179",
}

BASE = "http://www.binzhou.gov.cn"
SYSID = "1206"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """采滨州市 jact 领导信箱（问题 + 答复全文）。"""
    return harvest_jact_sd(fetch, SITE=SITE, base=BASE, sysid=SYSID,
                           list_method="GET", limit=limit)
