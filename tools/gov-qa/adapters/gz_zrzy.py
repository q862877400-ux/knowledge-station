"""适配器：**贵州省自然资源厅·厅长信箱**——IGI 平台（贵州省级统一部署的一个厅局）。

⚠ **本文件由 `recon/gen-gz-igi-adapters.py` 生成**，请勿手改；
要调整参数请改生成器里的 TARGETS 再跑一次。

参数（自动搜寻验证所得，见 `recon/igi-hunt.txt`）：
 · host `https://zrzy.guizhou.gov.cn` → 接口基址 `https://zrzy.guizhou.gov.cn/IGI`
 · siteId=502056, appId=797
 · 须带 `Referer`（该厅站点），否则 403。
## 备注
IGI 省级统一部署（2026-10-08 实探 /wzgb/gzcy/ 页面 JS，igi-dig-2.txt；站内共 3739 条）

"""
from __future__ import annotations

from adapters._igi_common import harvest_igi

SITE = {
    "key": "gz-zrzy",
    "name": "贵州省自然资源厅·厅长信箱",
    "kind": "api",
    "level": "province",
    "entry": "https://zrzy.guizhou.gov.cn/wzgb/gzcy/",
    "status": "ok",
    "note": "IGI 平台（siteId=502056, appId=797）；带省/市/区三级归属",
}

BASE = "https://zrzy.guizhou.gov.cn/IGI"
SITE_ID = "502056"
APP_ID = "797"
GROUP_ID = None
REFERER = "https://zrzy.guizhou.gov.cn/"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。"""
    return harvest_igi(fetch, SITE=SITE, base=BASE, site_id=SITE_ID, app_id=APP_ID,
                       group_id=GROUP_ID, referer=REFERER, limit=limit)
