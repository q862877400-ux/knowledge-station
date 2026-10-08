"""适配器：**扬州市·政民互动·信件选登（jpaas-jact）**。

## 站点事实（2026-10-09 实测，证据 recon/city-js-probe3.txt）
 · 门户 `www.yangzhou.gov.cn` 互动交流「信件选登」→
   `https://www.yangzhou.gov.cn/jyszzxhf/index.html`，页面内嵌接口
   `//www.yangzhou.gov.cn/api-gateway/jpaas-jact-web-server/front/mail-search.do?platformIid=Thls5eZbG3vAwgjtKY52k`。
 · 与**泰州同构**：真实数据接口是 `front/find-mail-pub-list`（不是 `mail-search.do`），
   明细是 HTML `front/mail-pub-detail?iid=`（不是 JSON `find-transact-detail`）。
 · 实测 `count≈7837`；答复标签 `答复内容/答复部门/答复日期`（由公共引擎别名归一）。
"""
from __future__ import annotations

from adapters._jpaas_jact_html_common import harvest_jpaas_html

SITE = {
    "key": "js-yangzhou",
    "name": "扬州市·政民互动·信件选登（jpaas-jact）",
    "kind": "api",
    "level": "city",
    "entry": "https://www.yangzhou.gov.cn/jyszzxhf/index.html",
    "status": "ok",
    "note": "jpaas-jact：列表 JSON（count≈7837）+ 明细 HTML（mail-pub-detail?iid=）；"
            "platformIid=Thls5eZbG3vAwgjtKY52k",
}

BASE = "https://www.yangzhou.gov.cn"
PLATFORM_KEY = "platformIid"
PLATFORM_VALUE = "Thls5eZbG3vAwgjtKY52k"
REFERER = SITE["entry"]


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """采扬州市「信件选登」（问题 + 答复原文）。"""
    return harvest_jpaas_html(fetch, SITE=SITE, base=BASE, platform_key=PLATFORM_KEY,
                              platform_value=PLATFORM_VALUE, referer=REFERER, limit=limit)
