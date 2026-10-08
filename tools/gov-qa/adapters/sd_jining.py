"""适配器：**济宁市·政民互动·我要写信（jact 平台）**。

## 站点事实（2026-10-08 实测，证据 recon/sd-city2-hunt.txt / probe.txt）
 · 门户 `www.jining.gov.cn` 首页「我要写信」→ `http://www.jining.gov.cn/jact/front/main.do?sysid=1`；
   「留言查询」→ `http://www.jining.gov.cn/jact/front/mailpublist.do?sysid=1`。
 · **jact（万户 hanweb）**，**http**；列表用 **GET**（POST 返回空）。
 · 实测 `sysid=1` **totalRecord=6909**。明细 `mailpubdetail.do?transactId=&sysid=1`。
"""
from __future__ import annotations

from adapters._sd_jact import harvest_jact_sd

SITE = {
    "key": "sd-jining",
    "name": "济宁市·政民互动·我要写信（jact）",
    "kind": "api",
    "level": "city",
    "entry": "http://www.jining.gov.cn/jact/front/mailpublist.do?sysid=1",
    "status": "ok",
    "note": "jact 平台（http，GET 列表），sysid=1，totalRecord=6909",
}

BASE = "http://www.jining.gov.cn"
SYSID = "1"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """采济宁市 jact 信箱（问题 + 答复全文）。"""
    return harvest_jact_sd(fetch, SITE=SITE, base=BASE, sysid=SYSID,
                           list_method="GET", limit=limit)
