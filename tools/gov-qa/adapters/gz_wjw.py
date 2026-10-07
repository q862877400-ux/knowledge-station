"""适配器：**贵州省卫生健康委员会 · 厅长信箱**——IGI 平台（贵州省内第二个厅局）。

## 怎么发现的（2026-10-07，`recon/igi-other-depts.py`）
`wjw.guizhou.gov.cn` 页面含 `openGovmsgbox` / `listGovmsgboxs` 指纹，
参数 `siteId=500663, appId=321`（与省生态环境厅 501471/590 不同）⇒ 同一省、不同站点。

## 地址
 · 用**本站** `/IGI`：`https://wjw.guizhou.gov.cn/IGI`（实测 200）；
 · 须带 `Referer`，否则 403。
"""
from __future__ import annotations

from adapters._igi_common import harvest_igi

SITE = {
    "key": "gz-wjw",
    "name": "贵州省卫生健康委·厅长信箱",
    "kind": "api",
    "level": "province",
    "entry": "https://wjw.guizhou.gov.cn/",
    "status": "ok",
    "note": "IGI 平台（本站 /IGI，siteId=500663, appId=321）；带省/市/区三级归属",
}

BASE = "https://wjw.guizhou.gov.cn/IGI"
SITE_ID = "500663"
APP_ID = "321"
REFERER = "https://wjw.guizhou.gov.cn/"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """按 IGI 基座采贵州省卫健委厅长信箱的已答复信件。"""
    return harvest_igi(fetch, SITE=SITE, base=BASE, site_id=SITE_ID, app_id=APP_ID,
                       group_id=None, referer=REFERER, limit=limit)
