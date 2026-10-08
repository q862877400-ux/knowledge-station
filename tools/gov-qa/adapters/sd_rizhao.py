"""适配器：**日照市·政民互动·市长信箱（jact 平台）**。

## 站点事实（2026-10-08 实测，证据 recon/sd-city2-hunt.txt / probe.txt）
 · 门户 `www.rizhao.gov.cn` 首页「市长信箱」→
   `http://www.rizhao.gov.cn/jact/front/mailwrite.do?sysid=383&groupid=7351&userids=G7351`。
 · **jact（万户 hanweb）**，**http**；列表 **GET 与 POST 均可用**（此处用 GET）。
 · 实测 `sysid=383` **totalRecord=1662**。明细 `mailpubdetail.do?transactId=&sysid=383`。
"""
from __future__ import annotations

from adapters._sd_jact import harvest_jact_sd

SITE = {
    "key": "sd-rizhao",
    "name": "日照市·政民互动·市长信箱（jact）",
    "kind": "api",
    "level": "city",
    "entry": "http://www.rizhao.gov.cn/jact/front/mailpublist.do?sysid=383",
    "status": "ok",
    "note": "jact 平台（http，GET/POST 均可），sysid=383，totalRecord=1662",
}

BASE = "http://www.rizhao.gov.cn"
SYSID = "383"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """采日照市 jact 市长信箱（问题 + 答复全文）。"""
    return harvest_jact_sd(fetch, SITE=SITE, base=BASE, sysid=SYSID,
                           list_method="GET", limit=limit)
