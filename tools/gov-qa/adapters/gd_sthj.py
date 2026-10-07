"""适配器：**广东省生态环境厅**「互动交流平台」（hdjlpt）留言选登。

与应急管理厅同款平台、同接口（见 `_gd_hdjlpt_common.py`）；
2026-10-07 实测年窗 total=211（应急厅同年窗仅 36）——生态厅留言量大得多。
"""
from __future__ import annotations

from adapters._gd_hdjlpt_common import harvest_gd

SITE = {
    "key": "gd-st",
    "name": "广东省生态环境厅",
    "kind": "api",
    "level": "province",
    "entry": "https://gdee.gd.gov.cn/hdjlpt?via=pc",
    "status": "ok",
    "note": "hdjlpt letter/pubList（Laravel CSRF 握手）；年窗 211 条（生态留言量大）",
}

BASE = "https://gdee.gd.gov.cn"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """按统一记录格式返回该厅留言选登（问题+答复全文）。"""
    return harvest_gd(fetch, SITE=SITE, BASE=BASE, limit=limit)
