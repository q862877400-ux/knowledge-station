"""适配器：**贵州省疾病预防控制局·厅长信箱**——IGI 平台（贵州省级统一部署的一个厅局）。

⚠ **本文件由 `recon/gen-gz-igi-adapters.py` 生成**，请勿手改；
要调整参数请改生成器里的 TARGETS 再跑一次。

参数（自动搜寻验证所得，见 `recon/igi-hunt.txt`）：
 · host `https://jkj.guizhou.gov.cn` → 接口基址 `https://jkj.guizhou.gov.cn/IGI`
 · siteId=503467, appId=1636
 · 须带 `Referer`（该厅站点），否则 403。
## 备注
IGI 省级统一部署（2026-10-08 自动搜寻验证，recon/gz-igi-hunt-3.txt）

"""
from __future__ import annotations

from adapters._igi_common import harvest_igi

SITE = {
    "key": "gz-jkj",
    "name": "贵州省疾病预防控制局·厅长信箱",
    "kind": "api",
    "level": "province",
    "entry": "https://jkj.guizhou.gov.cn/",
    "status": "ok",
    "note": "IGI 平台（siteId=503467, appId=1636）；带省/市/区三级归属",
}

BASE = "https://jkj.guizhou.gov.cn/IGI"
SITE_ID = "503467"
APP_ID = "1636"
GROUP_ID = None
REFERER = "https://jkj.guizhou.gov.cn/"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。"""
    return harvest_igi(fetch, SITE=SITE, base=BASE, site_id=SITE_ID, app_id=APP_ID,
                       group_id=GROUP_ID, referer=REFERER, limit=limit)
