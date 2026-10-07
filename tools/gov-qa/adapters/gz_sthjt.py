"""适配器：**贵州省生态环境厅 · 厅长信箱（信件公示）**——IGI 平台，带省/市/区三级归属。

## 站点形态（2026-10-07 实探，证据 recon/gz-xjgs.txt）
 · 页面 `https://sthj.guizhou.gov.cn/hdjl/tzxx/xjgs/` 的 JS 直接写出接口参数：
   ```
   pageIndex = 1; obj.pageSize = 20; obj.appId = 590; obj.siteId = 501471; obj.order = 1;
   ajax({ url: '/IGI/nbhd/openGovmsgbox.do?method=listGovmsgboxs', data: options })
   ```
   —— 与吉林是**同一套厂商平台**（见 `_igi_common.py`），故直接复用公共基座。
 · 实测：`https://sthj.guizhou.gov.cn/IGI/...&siteId=501471&appId=590` 返回 200，
   记录含 `PROVINCE=贵州省 / CITY=毕节市 / AREA=织金县`（**三级**）。
 · ⚠ 须带 `Referer`（该厅信件公示页），否则 403。
"""
from __future__ import annotations

from adapters._igi_common import harvest_igi

SITE = {
    "key": "gz-st",
    "name": "贵州省生态环境厅·厅长信箱",
    "kind": "api",
    "level": "province",
    "entry": "https://sthj.guizhou.gov.cn/hdjl/tzxx/xjgs/",
    "status": "ok",
    "note": "IGI 平台（siteId=501471, appId=590，无需 groupId）；带省/市/区三级归属；须带 Referer",
}

BASE = "https://sthj.guizhou.gov.cn/IGI"
SITE_ID = "501471"
APP_ID = "590"
REFERER = "https://sthj.guizhou.gov.cn/hdjl/tzxx/xjgs/"
DETAIL_PAGE = "https://sthj.guizhou.gov.cn/hdjl/tzxx/xjgs/view.html?ID="


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """按 IGI 公共基座采贵州厅长信箱的已答复信件（含答复正文与三级归属）。"""
    return harvest_igi(fetch, SITE=SITE, base=BASE, site_id=SITE_ID, app_id=APP_ID,
                       group_id=None, referer=REFERER, limit=limit)
