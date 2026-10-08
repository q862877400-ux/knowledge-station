"""适配器：**湖北省人力资源和社会保障厅·互动交流（IGI 平台，多 site）**。

## ⚠⚠ 2026-10-08 21:40 实测结论：本适配器与 hb-hdjl **同后端，数据重复**

`rst.hubei.gov.cn/IGI` 与 `www.hubei.gov.cn/IGI`（即 `hb-hdjl`）返回**同一份数据**：
- 本适配器抽验 20 条，其中 **19 条 id 已存在于 `hb-hdjl`**；
- 唯一「独有」的 id `8383` 只是因为 hb-hdjl 当时仅采了 150 条（被 limit 截断），
  全量采完后必然包含。
- 厅站新增的 siteId `4 / 28 / 50` 只各返回 1-3 条，是**厂商测试实例**（标题为
  「1」「2」「6666」之类），非真实业务数据。

⇒ **默认不要采集本适配器**（会产出重复条目、污染语料、虚增覆盖数）。
   仅当确认后端已分离时才启用。**湖北省的问答以 `hb-hdjl` 为准。**

## 站点事实（2026-10-08 实测，证据 recon/waf-igi-sites.json 【sx-hd】）
 · 厅站 `rst.hubei.gov.cn` 的互动交流留言由 **IGI 平台**驱动，与
   `adapters/_igi_common.py` 同构（参数 siteId/order/appId/pageIndex/pageSize 一致）。
 · base `http://rst.hubei.gov.cn/IGI`；order=1、appId 留空；**须带 Referer**
   `http://rst.hubei.gov.cn/hdjl/`（否则服务端 403）。
 · ⚠ **BASE 必须用 http**：实测部分湖北站 https 直接 ConnectError，http 明文 200。
 · 枚举 siteId 命中 **11 个 site / 合计 487 条**（recon 当日 totalResults，乐观估计）：
   ```
   4 → 3     10 → 6     16 → 122   19 → 4     25 → 289   26 → 23
   28 → 1    48 → 12    50 → 3     57 → 20    58 → 4
   ```
   ⚠ 同族站点（如贵州门户）经验：枚举出的 siteId 里**往往只有一部分有效**，
   其余列表接口返回 404 —— 故本适配器对 404 容错（基座遇非 200 即停该 site，不抛异常）。
 · 明细 `datas.REPLYS[].REPLYHTMLCONTENT` = 官方答复原文；带省/市/区三级归属。
"""
from __future__ import annotations

from adapters._igi_common import harvest_igi

SITE = {
    "key": "hb-rst-igi",
    "name": "湖北省人力资源和社会保障厅·互动交流（IGI）",
    "kind": "api",
    "level": "province",
    "entry": "http://rst.hubei.gov.cn/hdjl/",
    "status": "dup",
    "note": "⚠ 与 hb-hdjl 同后端（www.hubei.gov.cn/IGI），数据重复，默认不采；"
            "湖北省问答以 hb-hdjl 为准",
}

BASE = "http://rst.hubei.gov.cn/IGI"
REFERER = "http://rst.hubei.gov.cn/hdjl/"
APP_ID = ""
GROUP_ID = None

#: 枚举实测命中的 siteId（recon/waf-igi-sites.json，2026-10-08）；条数为枚举当日 totalResults。
#: 数字会随时间增长，采集时以接口返回为准；无效 siteId 由基座的 404 容错跳过。
SITE_IDS = [
    "4",
    "10",
    "16",
    "19",
    "25",
    "26",
    "28",
    "48",
    "50",
    "57",
    "58",
]


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """遍历湖北省人社厅 IGI 各 siteId，取已答复信件（含答复原文与三级归属）。

    `limit` 为**总条数**上限（跨 site 累计）。`fetch` 见 harvest.py 的 _Fetcher 协议。
    """
    out: list[dict] = []
    for sid in SITE_IDS:
        if limit and len(out) >= limit:
            break
        sub_site = dict(SITE)
        # 每个 siteId 用独立 source 后缀便于区分归属与去重，仍统一前缀 hb-rst-igi。
        sub_site["key"] = f"{SITE['key']}-{sid}"
        rows = harvest_igi(fetch, SITE=sub_site, base=BASE, site_id=sid, app_id=APP_ID,
                           group_id=GROUP_ID, referer=REFERER,
                           limit=(limit - len(out)) if limit else None, max_pages=200)
        out.extend(rows)
    return out
