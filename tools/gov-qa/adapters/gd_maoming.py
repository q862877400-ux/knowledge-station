"""适配器：**茂名市人民政府·政民互动**（广东 hdjlpt 同款平台）。

2026-10-10 实测：`http://www.maoming.gov.cn/hdjlpt/letter/pubList` 返回非空答复正文
（年窗 total=68）。引擎见 `_gd_hdjlpt_common.py`（Laravel CSRF 握手）。
生成器 `recon/gen-gd-city-adapters.py`（勿手改本壳）。

⚠ 广东地级市**各自部署** hdjlpt，数据互不相通 ⇒ 按域名各采各的。
"""
from __future__ import annotations

from adapters._gd_hdjlpt_common import harvest_gd

SITE = {
    "key": "gd-maoming",
    "name": "茂名市人民政府·政民互动（hdjlpt）",
    "kind": "api",
    "level": "city",
    "entry": "http://www.maoming.gov.cn/hdjlpt?via=pc",
    "status": "ok",
    "note": "hdjlpt letter/pubList；实测年窗 total=68",
}

BASE = "http://www.maoming.gov.cn"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """按统一记录格式返回该市留言选登（问题+答复全文）。"""
    return harvest_gd(fetch, SITE=SITE, BASE=BASE, limit=limit)
