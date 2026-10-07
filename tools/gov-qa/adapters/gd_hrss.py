"""适配器：**广东省人力资源和社会保障厅**（hdjlpt 同款平台）。

2026-10-07 实测年窗 total=510 —— 广东已验证厅局里量最大的一个。
引擎见 `_gd_hdjlpt_common.py`。
"""
from __future__ import annotations

from adapters._gd_hdjlpt_common import harvest_gd

SITE = {
    "key": "gd-hr",
    "name": "广东省人力资源和社会保障厅",
    "kind": "api",
    "level": "province",
    "entry": "https://hrss.gd.gov.cn/hdjlpt?via=pc",
    "status": "ok",
    "note": "hdjlpt letter/pubList；年窗 510 条（广东已验证厅局中量最大）",
}

BASE = "https://hrss.gd.gov.cn"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """按统一记录格式返回该厅留言选登（问题+答复全文）。"""
    return harvest_gd(fetch, SITE=SITE, BASE=BASE, limit=limit)
