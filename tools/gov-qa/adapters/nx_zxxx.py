"""适配器：**宁夏回族自治区·主席信箱**——IGI 平台（与贵州/吉林同族）。

## 站点事实（2026-10-08 实测，证据 recon/province-platform-hunt.txt 【宁夏】）
 · 门户 `www.nx.gov.cn` 的「互动交流」→「主席信箱」`/hdjl/zxxx/`；
 · 接口与 `_igi_common.py` **完全同构**（`/IGI/nbhd/openGovmsgbox.do`），
   **零改造复用基座**，只需 (base, siteId, appId, Referer)：
   · base `https://www.nx.gov.cn/IGI`
   · siteId=115, appId=4
   · **须带 Referer** `https://www.nx.gov.cn/hdjl/`
 · 实测列表 `pageInfo.totalResults=667`，明细 `datas.REPLYS[].REPLYHTMLCONTENT` = 官方答复。
 · ★★ **列表带 PROVINCE/CITY/AREA 三级归属**（如「宁夏回族自治区 / 吴忠市 / 青铜峡市」）
   —— 这是本模块**唯一**能扩「县」的通道。
   ⚠ 新落 IGI 适配器**务必同步** `recon/coverage-matrix.py` 的 `PROVINCE_PREFIX`
   （否则旧信的地域字段为空时会掉进「未归属」）。
 · 注：参数名在宁夏写作 `appID`（大写 D），实测**大小写不敏感**，基座模板的 `appId` 同样可用。
"""
from __future__ import annotations

from adapters._igi_common import harvest_igi

SITE = {
    "key": "nx-zxxx",
    "name": "宁夏回族自治区·主席信箱",
    "kind": "api",
    "level": "province",
    "entry": "https://www.nx.gov.cn/hdjl/zxxx/",
    "status": "ok",
    "note": "IGI 平台（siteId=115, appId=4）；带省/市/区三级归属；须带 Referer",
}

BASE = "https://www.nx.gov.cn/IGI"
SITE_ID = "115"
APP_ID = "4"
GROUP_ID = None
REFERER = "https://www.nx.gov.cn/hdjl/"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """按 IGI 基座采宁夏主席信箱的已答复信件（含答复正文与三级归属）。"""
    return harvest_igi(fetch, SITE=SITE, base=BASE, site_id=SITE_ID, app_id=APP_ID,
                       group_id=GROUP_ID, referer=REFERER, limit=limit)
