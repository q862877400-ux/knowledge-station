"""适配器：**台州市·民呼我为统一平台·办理公开**（`code=331000`）。

## 站点事实（2026-10-09 实测，证据 recon/city-js-zj-zjmhww-probe.txt）
浙江省互动统一收敛到**浙江省民呼我为统一平台**（`zxts.zjzwfw.gov.cn/zwmhww/`）。
列表接口的 `code` 是**精确行政区划码**（非层级聚合）：
 · `330000`=省本级、`331000`=**台州市**、非法码=0 条 ⇒ 各市互不重叠。
本适配器复用省本级 `zj_mhww` 的字体反爬解码（glyph 名即真字），仅换 `code`。

## 接口
 · 列表 `POST {BASE}/zlh/zsapi/xfpt/OTMelbwjyz/OTMjkerj`
     body `{"code":"331000","bt":"","bldw":"","pageNum":<n>,"pageSize":<m>}` → `data.totalItem`
 · 明细 `GET  {BASE}/zlh/zsapi/xfpt/OTMelbwjyz/OTMrwgaxid?storeId=<id>`
     → `dfyj`=答复原文、`nr`=问题、`dfdw`=答复单位、`fysj`/`dfsj`=反映/答复时间。

## 备注
 · 可反复跑（开跑跳过已落盘 id，`limit`=本轮新增）；`max_records` 默认 500 兜底。
 · 全量很大（台州 实测 totalItem≈2737），全采前请评估耗时。
"""
from __future__ import annotations

from adapters._zj_mhww_common import harvest_area

SITE = {
    "key": "zj-taizhou",
    "name": "台州市·民呼我为·办理公开",
    "kind": "api",
    "level": "city",
    "entry": "https://zxts.zjzwfw.gov.cn/zwmhww/#/home/index/public",
    "status": "ok",
    "note": "浙江民呼我为统一平台 code=331000；文字 woff 字体混淆按 glyph 名解码；"
            "可反复跑（limit=本轮新增）",
}

AREA = "331000"


def harvest(fetch, *, limit: int | None = None, max_records: int = 500) -> list[dict]:
    """采台州市「民呼我为·办理公开」（问题 + 答复原文，自动还原字体混淆）。"""
    return harvest_area(fetch, SITE=SITE, area=AREA, limit=limit,
                        max_records=max_records)
