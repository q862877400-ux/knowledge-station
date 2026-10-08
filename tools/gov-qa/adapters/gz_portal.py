"""适配器：**贵州省·人民政府门户·政民互动（IGI 平台，多 site）**——IGI 中间件。

## 站点事实（2026-10-08 实测，证据 recon/waf-igi-sites.json 【guizhou】）
 · 门户 `www.guizhou.gov.cn` 的留言由 **IGI 平台**驱动，与 `_igi_common.py` 同构。
 · base `http://www.guizhou.gov.cn/IGI`；order=1、appId 留空；**须带 Referer** `http://www.guizhou.gov.cn/`。
 · 枚举 siteId=1..60 命中 **11 个 site / 合计 2,597 条**（2026-10-08）：
   ```
   30 →   3      31 →   4      35 → 185      36 →  31      48 → 1254
   49 → 147      51 → 463      53 →  30      56 →  77      58 → 263      59 → 140
   ```
   （48/51/58 抽验明细：dept 分别为「直接办理」「花溪区清溪街道办事处」「息烽县公安局」。）
 · 明细 `datas.REPLYS[].REPLYHTMLCONTENT` = 官方答复原文；带省/市/区三级归属。

## 与既有贵州线的关系
本模块此前已有 27 个 `gz-*` 省直部门适配器（走各自 `/IGI/` 子域）。
本适配器补上**省门户级**通道（另一实例），是增量。
"""
from __future__ import annotations

from adapters._igi_common import harvest_igi

SITE = {
    "key": "gz-portal",
    "name": "贵州省·人民政府门户·政民互动（IGI）",
    "kind": "api",
    "level": "province",
    "entry": "http://www.guizhou.gov.cn/IGI/nbhd/openGovmsgbox.do",
    "status": "ok",
    "note": "IGI 平台（www.guizhou.gov.cn/IGI），多 siteId；须带 Referer；带省/市/区三级归属",
}

BASE = "http://www.guizhou.gov.cn/IGI"
REFERER = "http://www.guizhou.gov.cn/"
APP_ID = ""
GROUP_ID = None

#: 枚举实测命中的 siteId（1..60，2026-10-08）。
SITE_IDS = [
    "30", "31", "35", "36", "48", "49", "51", "53", "56", "58", "59",
]


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """遍历贵州省门户 IGI 各 siteId，取已答复信件（含答复原文与三级归属）。"""
    out: list[dict] = []
    for sid in SITE_IDS:
        if limit and len(out) >= limit:
            break
        sub_site = dict(SITE)
        sub_site["key"] = f"{SITE['key']}-{sid}"
        rows = harvest_igi(fetch, SITE=sub_site, base=BASE, site_id=sid, app_id=APP_ID,
                           group_id=GROUP_ID, referer=REFERER,
                           limit=(limit - len(out)) if limit else None, max_pages=200)
        out.extend(rows)
    return out
