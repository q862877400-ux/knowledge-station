"""适配器：**广东省应急管理厅**「互动交流平台」（hdjlpt）留言选登。

引擎与接口细节见 `_gd_hdjlpt_common.py`（两厅已验证：应急 site_id=122、
生态 gdee 年窗 211 条；`site_id` 参数被服务端忽略 ⇒ 按厅域名各采各的）。
答复点名 `AQ 3067-2026`、应急管理部 19 号令等依据条款 —— 高档考卷料。
"""
from __future__ import annotations

from adapters._gd_hdjlpt_common import harvest_gd

SITE = {
    "key": "gd-yj",
    "name": "广东省应急管理厅",
    "kind": "api",
    "level": "province",
    "entry": "https://yjgl.gd.gov.cn/hdjlpt?via=pc",
    "status": "ok",
    "note": "hdjlpt letter/pubList（Laravel CSRF 握手）；全历史 179 条（2020-2026 五个非空年窗）",
}

BASE = "https://yjgl.gd.gov.cn"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """按统一记录格式返回该厅留言选登（问题+答复全文）。"""
    return harvest_gd(fetch, SITE=SITE, BASE=BASE, limit=limit)
