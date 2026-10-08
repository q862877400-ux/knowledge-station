"""适配器：**山西省·省长信箱**——IGI 平台（与宁夏/贵州/吉林同族）。

## 站点事实（2026-10-08 实测，证据 recon/province-platform-hunt.txt 【山西】）
 · 门户 `www.shanxi.gov.cn` 的「政民互动」→「省长信箱」`/zmhd/szxx/`；
 · 接口与 `_igi_common.py` **完全同构**，零改造复用基座：
   · base `http://www.shanxi.gov.cn/IGI`
   · siteId=110, appId=1742326
   · **须带 Referer** `http://www.shanxi.gov.cn/zmhd/`
 · 实测列表 `pageInfo.totalResults=1872`，明细 `datas.REPLYS[].REPLYHTMLCONTENT` = 官方答复
   （样例：咨询直博生工龄认定 → 省人社厅答复）。
 · ⚠ 本批 `PROVINCE/CITY/AREA` **为空** ⇒ 归省只能靠 `coverage-matrix.py` 的
   `PROVINCE_PREFIX`（已加 `sx-` 族）。
 · 另有一块 `siteId=36, appId=584617`（尚未落适配器，留待后续）。
"""
from __future__ import annotations

from adapters._igi_common import harvest_igi

SITE = {
    "key": "sx-szxx",
    "name": "山西省·省长信箱",
    "kind": "api",
    "level": "province",
    "entry": "http://www.shanxi.gov.cn/zmhd/szxx/",
    "status": "ok",
    "note": "IGI 平台（siteId=110, appId=1742326）；须带 Referer；归属字段为空靠来源前缀",
}

BASE = "http://www.shanxi.gov.cn/IGI"
SITE_ID = "110"
APP_ID = "1742326"
GROUP_ID = None
REFERER = "http://www.shanxi.gov.cn/zmhd/"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """按 IGI 基座采山西省长信箱的已答复信件。"""
    return harvest_igi(fetch, SITE=SITE, base=BASE, site_id=SITE_ID, app_id=APP_ID,
                       group_id=GROUP_ID, referer=REFERER, limit=limit)
