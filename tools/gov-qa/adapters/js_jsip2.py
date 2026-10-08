"""适配器：**江苏省知识产权局**「咨询建言 / 统一咨询投诉」（江苏 jact 平台）。

引擎与接口细节见 `adapters/_jact_common.py`。
· host = `jsip.jiangsu.gov.cn`，sysid = `85`；实测 **totalRecord = 71**；
· 明细页含 问题 + 答复（常点名依据条款/标准号），A 类考卷料。
（证据 recon/js-jact-hunt.txt）
"""
from __future__ import annotations

from adapters._jact_common import harvest_jact

SITE = {
    "key": "js-jsip2",
    "name": "江苏省知识产权局",
    "kind": "api",
    "level": "province",
    "entry": "https://jsip.jiangsu.gov.cn/jact/front/mailpublist.do?sysid=85",
    "status": "ok",
    "note": "江苏 jact 平台；host=jsip.jiangsu.gov.cn sysid=85；实测 totalRecord=71",
}

HOST = "jsip.jiangsu.gov.cn"
SYSID = "85"


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """按统一记录格式返回该厅留言选登（问题+答复全文）。"""
    return harvest_jact(fetch, SITE=SITE, host=HOST, sysid=SYSID, limit=limit)
