"""适配器：**吉林省自然资源厅·厅长信箱**——IGI 平台（吉林省级统一部署的一个厅局）。

⚠ **本文件由 `recon/gen-jl-igi-adapters.py` 生成**，请勿手改；
要调整参数请改生成器的 TARGETS 再跑一次。

参数（`recon/jl-groupid-roster.txt` 扫 groupId 所得）：
 · 全省共用 host `https://haiyun.jl.gov.cn/IGI`（**吉林不是每厅局一个域名**）
 · siteId=117, appId=96 全省固定，**只有 groupId=171 区分厅局**
 · 须带 `Referer`（但**不必匹配本厅站点**，见 `recon/jl-groupid-scan-evidence.txt`）
 · 上游 `PUBLISHURL` 为 null ⇒ `entry` 指向平台主机，记录 id 仍准
"""
from __future__ import annotations

from adapters._igi_common import harvest_igi

SITE = {
    "key": "jl-zrzy",
    "name": "吉林省自然资源厅·厅长信箱",
    "kind": "api",
    "level": "province",
    "entry": "https://haiyun.jl.gov.cn/IGI",
    "status": "ok",
    "note": "IGI 平台（siteId=117, appId=96, groupId=171）；带省/市/区三级归属",
}

BASE = "https://haiyun.jl.gov.cn/IGI"
SITE_ID = "117"
APP_ID = "96"
GROUP_ID = "171"
REFERER = "https://hrss.jl.gov.cn/"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """按 IGI 基座采该厅局长信箱的已答复信件（含答复正文与三级归属）。"""
    return harvest_igi(fetch, SITE=SITE, base=BASE, site_id=SITE_ID, app_id=APP_ID,
                       group_id=GROUP_ID, referer=REFERER, limit=limit)
