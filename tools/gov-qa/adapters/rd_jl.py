"""适配器：**吉林省人大·法规草案意见征集**（人大系统·法规草案征求意见）。

由 `rd_common.harvest_rd` 驱动；本模块只声明 SITE。
⚠ 体裁是「草案全文 + 征求意见公告」，**不是问答** ⇒ 记录带
   `extra.content_kind = "立法征求意见"` 以与问答语料区分。
"""
from __future__ import annotations

from adapters.rd_common import SITES, harvest_rd

SITE = {
    "key": "rd-jl",
    "name": "吉林省人大·法规草案意见征集",
    "kind": "html",
    "level": "province",
    "entry": "https://www.jlrd.gov.cn/gzjl/fgcayjzj/",
    "status": "ok",
    "note": "人大·法规草案征求意见（列表+详情，正文为草案全文）",
}


def harvest(fetch, *, limit: int | None = None, max_pages: int = 30) -> list[dict]:
    return harvest_rd(fetch, site_key=SITE["key"], limit=limit, max_pages=max_pages)
