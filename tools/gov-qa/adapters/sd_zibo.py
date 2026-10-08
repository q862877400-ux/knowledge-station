"""适配器：**淄博市·政民互动·我要咨询（jact 平台）**。

## 站点事实（2026-10-08 实测，证据 recon/sd-city-probe3.txt / probe4.txt）
 · 门户 `www.zibo.gov.cn` 政民互动 `http://www.zibo.gov.cn/col/col6/index.html`；
   「我要咨询」→ `http://www.zibo.gov.cn/jact/front/main.do?sysid=54`。
 · **jact（万户 hanweb）平台**，但：
   · **BASE 用 http**（实测 http 200；https 亦通但统一用 http）；
   · 列表用 **GET**（`dataproxy_mailpublist.do`，参数走 query string —— **POST 会返回「错误操作」**）。
 · 实测 `sysid=54` **totalRecord = 376**；`sysid=1`（部门监督投诉）totalRecord=0（无公开记录）。
 · 明细 `mailpubdetail.do?transactId=&sysid=54`，答复标签为「答复内容」。
 · 样例：SZXX20260925344「机动车限行咨询」→「淄博市对外地号牌小型客车无禁限行规定…」（淄博市公安局）。
"""
from __future__ import annotations

from adapters._sd_jact import harvest_jact_sd

SITE = {
    "key": "sd-zibo",
    "name": "淄博市·政民互动·我要咨询（jact）",
    "kind": "api",
    "level": "city",
    "entry": "http://www.zibo.gov.cn/jact/front/mailpublist.do?sysid=54",
    "status": "ok",
    "note": "jact 平台（http，GET 列表），sysid=54，totalRecord=376；答复标签「答复内容」",
}

BASE = "http://www.zibo.gov.cn"
SYSID = "54"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """采淄博市 jact 我要咨询（问题 + 答复全文）。"""
    return harvest_jact_sd(fetch, SITE=SITE, base=BASE, sysid=SYSID,
                           list_method="GET", limit=limit)
