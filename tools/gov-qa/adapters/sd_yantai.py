"""适配器：**烟台市·互动交流·网上民声（jpaas-jact 网关，JSON 接口）**。

## 站点事实（2026-10-08 实测，证据 recon/sd-city2-hunt.txt / probe.txt）
 · 门户 `www.yantai.gov.cn` 首页「网上民声」→
   `http://www.yantai.gov.cn/api-gateway/jpaas-jact-web-server/front/mail-pub-list.do?platformIid=TBCxiImkDT42EEoX3QnkW&type=1`
 · 与济南**同款** jpaas-jact 网关（接口同名 `find-mail-pub-list`，见 `_sd_jact_gw.py`）。
 · platformUid=`TBCxiImkDT42EEoX3QnkW`，submitTargetIds 为空（页面 hidden 值为空）。
 · ⚠ **不传 govOpen**：`govOpen=1` 回 0 条，留空回 **101152** 条（实测）。
 · 实测 count=101152；样例「司法警告，务必严惩和赔付客户」→ 芝罘区通伸街道市场监督管理所。
"""
from __future__ import annotations

from adapters._sd_jact_gw import harvest_jact_gateway

SITE = {
    "key": "sd-yantai",
    "name": "烟台市·互动交流·网上民声（jact网关）",
    "kind": "api",
    "level": "city",
    "entry": "http://www.yantai.gov.cn/col/col11783/index.html",
    "status": "ok",
    "note": "jpaas-jact 网关（http），find-mail-pub-list，count=101152（勿传 govOpen=1）",
}

BASE = "http://www.yantai.gov.cn/api-gateway/jpaas-jact-web-server/front"
PLATFORM_UID = "TBCxiImkDT42EEoX3QnkW"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """采烟台「网上民声」（问题 + 答复全文）。"""
    return harvest_jact_gateway(fetch, SITE=SITE, base=BASE, platform_uid=PLATFORM_UID,
                                submit_target_ids="", gov_open="", limit=limit)
