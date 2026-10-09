"""适配器：**南京市·政民互动信箱（IGI 平台，多 siteId）**——2026-10-09 第 8 轮新增。

## 怎么找到的
第 5 轮 `recon/igi-portal-sweep.py`（34 个城市门户各打一发列表请求）命中南京；
第 6 轮 `recon/igi-siteid-scan.py nanjing` 扫 siteId=1..300（**空 appId**）实测：
**63 个 siteId / 4,065 条**（`recon/igi-siteid-nanjing.json`；
126→868、130→192、64→177、72→149、71→140、70→133、48→130、86→122、55→119、58→118…）。

## 为什么有价值
江苏此前**没有 IGI 线**（只有 `js-*` 厅局 jact 系）。南京 = 该省第一个 IGI 候选源。
⚠ 但**不能扩县级**（见下第 2 条）。

## 关键事实（2026-10-09 第 8 轮实测）
1. **可采**：列表 `HTTP 200`（siteId=126 total=868、siteId=130 total=192），行是大写键；
   明细 `HTTP 200`，答复正文在 `datas.REPLYS[].REPLYHTMLCONTENT`
   （实测 id=430593 → 2,315 字、id=430297 → 163 字）。
2. ★ **地域字段基本是空/恒定 ⇒ 剥离**：`recon/igi-geo-sample.py nanjing` 抽
   siteId=126 与 130 **各 100 行**：
   - siteId=126：`PROVINCE/CITY/AREA` **非空 0/100**（整段为空）；
   - siteId=130：**非空 23/100**，且只有 1 种 —— `江苏省 / 南京市 / 市辖区`。
   ⇒ 与山西 / 内蒙古 / 包头 / 沈阳同类（**门户默认值或缺失**），原样落盘会污染三级归属
   ⇒ `postprocess` 一律清空。
   ⚠ 这条否掉了「南京能给区县级」的期待。
3. 端点 `https://www.nanjing.gov.cn/IGI`（**https 可达**）；须带
   `Referer: https://www.nanjing.gov.cn/`。
4. **行数组键是 `datas.data`**（不是 `list`）—— 与南宁/包头不同，探针/抽样脚本必须带回退。
"""
from __future__ import annotations

from adapters._igi_common import existing_ids, harvest_igi

SITE = {
    "key": "nanjing-igi",
    "name": "南京市·政民互动信箱（IGI）",
    "kind": "api",
    "level": "city",
    "entry": "https://www.nanjing.gov.cn/IGI/nbhd/openGovmsgbox.do",
    "status": "ok",
    "note": "IGI 63 站 / 约 4,065 条（空 appId 取全量）；须带 Referer；https 可达；"
            "上游地域字段为空或门户默认值，已剥离",
}

BASE = "https://www.nanjing.gov.cn/IGI"
REFERER = "https://www.nanjing.gov.cn/"
APP_ID = ""                       # ★ 必须空：带 appId 会过滤掉大部分记录
GROUP_ID = None

#: 63 个 siteId（`recon/igi-siteid-nanjing.json`，2026-10-09 扫 1..300 空 appId），
#: 按 totalResults **降序**，合计 **4,065** 条（枚举上界；实际可采 = 已答复部分）。
SITE_IDS = (
    "126 130 64 72 71 70 5 48 86 55 58 36 137 85 6 111 9 67 74 16 69 8 133 77 "
    "78 136 57 81 7 123 54 134 50 56 92 132 53 75 4 60 79 10 90 59 31 47 101 "
    "52 84 12 88 82 89 141 38 127 129 44 159 96 100 13 110"
).split()


def postprocess(rows: list[dict]) -> list[dict]:
    """剥离**空/恒定**地域（= 门户默认值或缺失）。

    与 `baotou_igi.postprocess` 同口径：本批内**非空**地域组合只有 1 种（或全空）⇒ 一律清空。
    南京实测（siteId 126/130 各抽 100 行）非空组合只有 `江苏省/南京市/市辖区`（或全空）⇒ 全剥离。
    """
    combos = {
        (r.get("extra", {}).get("province"), r.get("extra", {}).get("city"),
         r.get("extra", {}).get("area"))
        for r in rows
    }
    combos.discard((None, None, None))
    constant = len(combos) <= 1
    out: list[dict] = []
    for r in rows:
        e = r.get("extra") or {}
        if constant and (e.get("province") or e.get("city") or e.get("area")):
            e["province"] = e["city"] = e["area"] = None
            e["region"] = None
            e.pop("pForumNames", None)
            e["geo_note"] = "上游地域字段为空或该站默认值（单值恒定），已剥离"
            r["extra"] = e
        out.append(r)
    return out


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """遍历南京各 siteId 取已答复信件（`limit` 为跨 site 累计的**本轮新增**上限）。

    ⚠ 全量约 4,065 条（枚举值）⇒ 长任务请用分片增量驱动
    `recon/igi-chunked.py nanjing_igi`（逐 siteId + 页窗口落盘）。
    """
    out: list[dict] = []
    seen = existing_ids(SITE["key"])
    if seen:
        print(f"    [{SITE['key']}] 已落盘 {len(seen)} 条，本轮跳过其明细")
    for sid in SITE_IDS:
        if limit and len(out) >= limit:
            break
        sub_site = dict(SITE)
        sub_site["key"] = f"{SITE['key']}-{sid}"
        rows = harvest_igi(fetch, SITE=sub_site, base=BASE, site_id=sid, app_id=APP_ID,
                           group_id=GROUP_ID, referer=REFERER,
                           limit=(limit - len(out)) if limit else None,
                           max_pages=300, skip_ids=seen)
        out.extend(postprocess(rows))
    return out
