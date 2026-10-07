"""适配器：**广东省林业局**（广东 hdjlpt 同款平台）。

2026-10-07 探测年窗 total=21（recon/gd-dept-domains-probed.json）。
引擎见 `_gd_hdjlpt_common.py`；生成器 `recon/gen-gd-adapters.py`（勿手改本壳）。
"""
from __future__ import annotations

from adapters._gd_hdjlpt_common import harvest_gd

SITE = {
    "key": "gd-lyj",
    "name": "广东省林业局",
    "kind": "api",
    "level": "province",
    "entry": "https://lyj.gd.gov.cn/hdjlpt?via=pc",
    "status": "ok",
    "note": "hdjlpt letter/pubList；探测年窗 total=21",
}

BASE = "https://lyj.gd.gov.cn"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """按统一记录格式返回该单位留言选登（问题+答复全文）。"""
    return harvest_gd(fetch, SITE=SITE, BASE=BASE, limit=limit)
