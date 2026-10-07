"""适配器：**吉林省卫生健康委员会 · 厅长信箱**——IGI 平台（同一省内的另一个厅局）。

## 怎么发现的（2026-10-07，`recon/igi-other-depts.py`）
IGI 是厂商产品，**同一省的其他厅局站也挂了同款信箱**：
`wsjkw.jl.gov.cn` 首页/互动页里出现 `openGovmsgbox` / `listGovmsgboxs`，
参数为 `siteId=117, appId=96, groupId=178`——**siteId/appId 与省生态环境厅相同，groupId 不同**
（group 区分同一站点下的不同信箱）。

## 地址
 · 站点用**省级海云主机**：`https://haiyun.jl.gov.cn/IGI`（本站 `/IGI` 是 404，实测）；
 · 须带 `Referer`（该厅互动页），否则 403。
"""
from __future__ import annotations

from adapters._igi_common import harvest_igi

SITE = {
    "key": "jl-wjw",
    "name": "吉林省卫生健康委·厅长信箱",
    "kind": "api",
    "level": "province",
    "entry": "https://wsjkw.jl.gov.cn/hdjl/",
    "status": "ok",
    "note": "IGI 平台（海云主机 siteId=117, appId=96, groupId=178）；带省/市/区三级归属",
}

BASE = "https://haiyun.jl.gov.cn/IGI"
SITE_ID = "117"
APP_ID = "96"
GROUP_ID = "178"
REFERER = "https://wsjkw.jl.gov.cn/hdjl/"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """按 IGI 基座采吉林省卫健委厅长信箱的已答复信件。"""
    return harvest_igi(fetch, SITE=SITE, base=BASE, site_id=SITE_ID, app_id=APP_ID,
                       group_id=GROUP_ID, referer=REFERER, limit=limit)
