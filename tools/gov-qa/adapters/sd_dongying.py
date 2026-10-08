"""适配器：**东营市·政民互动·网上民生（jact 平台）**。

## 站点事实（2026-10-08 实测，证据 recon/sd-city-probe2.txt / probe3.txt）
 · 门户 `www.dongying.gov.cn` 首页「我要留言」→ `http://www.dongying.gov.cn/jact/front/main.do?sysid=129`。
 · **jact（万户 hanweb）平台**，与江苏同构，但：
   · **BASE 用 http**（https 证书不匹配，ConnectError）；
   · 列表用 **POST**（`dataproxy_mailpublist.do`，参数走表单 body）。
 · 实测 `sysid=129` **totalRecord = 20299**（全省地市里目前最大）。
 · 明细 `mailpubdetail.do?transactId=&sysid=129`，答复标签为「答复内容」，答复部门「答复部门」。
 · 样例：办件编号 BMMS20261037979「找不到我的档案了」→「已电话联系来电人…」。
"""
from __future__ import annotations

from adapters._sd_jact import harvest_jact_sd

SITE = {
    "key": "sd-dongying",
    "name": "东营市·政民互动·网上民生（jact）",
    "kind": "api",
    "level": "city",
    "entry": "http://www.dongying.gov.cn/jact/front/mailpublist.do?sysid=129",
    "status": "ok",
    "note": "jact 平台（http，POST 列表），sysid=129，totalRecord=20299；答复标签「答复内容」",
}

BASE = "http://www.dongying.gov.cn"
SYSID = "129"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """采东营市 jact 网上民生（问题 + 答复全文）。"""
    return harvest_jact_sd(fetch, SITE=SITE, base=BASE, sysid=SYSID,
                           list_method="POST", limit=limit)
