"""适配器：**广东省教育厅**（hdjlpt 同款平台）。年窗 14 条（2026-10-07 实测）。"""
from __future__ import annotations

from adapters._gd_hdjlpt_common import harvest_gd

SITE = {
    "key": "gd-jy",
    "name": "广东省教育厅",
    "kind": "api",
    "level": "province",
    "entry": "https://eea.gd.gov.cn/hdjlpt?via=pc",
    "status": "ok",
    "note": "hdjlpt letter/pubList；年窗 14 条",
}

BASE = "https://eea.gd.gov.cn"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """按统一记录格式返回该厅留言选登（问题+答复全文）。"""
    return harvest_gd(fetch, SITE=SITE, BASE=BASE, limit=limit)
