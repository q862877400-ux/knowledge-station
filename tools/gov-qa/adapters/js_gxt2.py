"""适配器：**江苏省工业和信息化厅**「咨询建言 / 统一咨询投诉」（江苏 jact 平台）。

引擎与接口细节见 `adapters/_jact_common.py`。
· host = `gxt.jiangsu.gov.cn`，sysid = `50`；实测 **totalRecord = 140**；
· 明细页含 问题 + 答复（常点名依据条款/标准号），A 类考卷料。
（证据 recon/js-jact-hunt.txt）
"""
from __future__ import annotations

from adapters._jact_common import harvest_jact

SITE = {
    "key": "js-gxt2",
    "name": "江苏省工业和信息化厅",
    "kind": "api",
    "level": "province",
    "entry": "https://gxt.jiangsu.gov.cn/jact/front/mailpublist.do?sysid=50",
    "status": "ok",
    "note": "江苏 jact 平台；host=gxt.jiangsu.gov.cn sysid=50；实测 totalRecord=140",
}

HOST = "gxt.jiangsu.gov.cn"
SYSID = "50"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """按统一记录格式返回该厅留言选登（问题+答复全文）。"""
    return harvest_jact(fetch, SITE=SITE, host=HOST, sysid=SYSID, limit=limit)
