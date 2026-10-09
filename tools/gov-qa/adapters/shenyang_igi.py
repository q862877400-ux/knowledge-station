"""适配器：**沈阳市·政民互动信箱（IGI 平台，多 siteId）**——2026-10-09 第 8 轮新增。

## 怎么找到的
第 5 轮 `recon/igi-portal-sweep.py`（34 个城市门户各打一发列表请求）命中沈阳；
第 6 轮 `recon/igi-siteid-scan.py shenyang` 扫 siteId=1..300（**空 appId**）实测：
**53 个 siteId / 17,369 条**（`recon/igi-siteid-shenyang.json`；
123→6,279、118→4,109、88→914、44→746、86→538、98→425…）。

## 为什么有价值
辽宁在本模块此前**没有任何 IGI 线**；沈阳 = 该省第一个三级归属候选源。

## 关键事实（2026-10-09 第 8 轮实测）
1. **可采**：列表 `HTTP 200`（siteId=123 total=6,279、siteId=118 total=4,110），
   行是大写键（`METADATAID/TITLE/ISREPLY/PROVINCE/CITY/AREA`）；
   明细 `HTTP 200`，答复正文在 `datas.REPLYS[].REPLYHTMLCONTENT`
   （实测 id=69520 → 112 字、id=69538 → 325 字）。
2. ★ **地域字段是「恒定默认值」⇒ 剥离**：`recon/igi-geo-sample.py shenyang` 抽
   siteId=123 与 118 **各 100 行**，`PROVINCE/CITY/AREA` **非空 100/100 且只有 1 种**
   —— `辽宁省 / 沈阳市 / 和平区` ⇒ 与山西 / 内蒙古 / 包头同类（门户自身位置），
   原样落盘会**污染三级归属** ⇒ `postprocess` 一律清空。
   ⚠ 这条否掉了「沈阳能给区县级」的期待：它的地域**不是真实信件属地**。
3. 端点 `https://www.shenyang.gov.cn/IGI`（**https 可达**）；须带
   `Referer: https://www.shenyang.gov.cn/`。
4. **行数组键是 `datas.data`**（不是 `list`）—— 与南宁/包头不同，探针/抽样脚本必须带回退。
"""
from __future__ import annotations

from adapters._igi_common import existing_ids, harvest_igi

SITE = {
    "key": "shenyang-igi",
    "name": "沈阳市·政民互动信箱（IGI）",
    "kind": "api",
    "level": "city",
    "entry": "https://www.shenyang.gov.cn/IGI/nbhd/openGovmsgbox.do",
    "status": "ok",
    "note": "IGI 53 站 / 约 17,369 条（空 appId 取全量）；须带 Referer；https 可达；"
            "上游地域字段为门户默认值（单值恒定），已剥离",
}

BASE = "https://www.shenyang.gov.cn/IGI"
REFERER = "https://www.shenyang.gov.cn/"
APP_ID = ""                       # ★ 必须空：带 appId 会过滤掉大部分记录
GROUP_ID = None

#: 53 个 siteId（`recon/igi-siteid-shenyang.json`，2026-10-09 扫 1..300 空 appId），
#: 按 totalResults **降序**，合计 **17,369** 条（枚举上界；实际可采 = 已答复部分）。
SITE_IDS = (
    "123 118 88 44 86 98 38 136 120 90 34 121 135 113 137 126 74 124 129 73 78 "
    "71 79 89 99 85 142 41 81 130 115 139 72 141 77 84 119 112 138 45 80 96 "
    "111 91 202 143 127 32 75 100 63 93 270"
).split()


def postprocess(rows: list[dict]) -> list[dict]:
    """剥离**恒定**地域（= 门户/站点默认值）。

    与 `baotou_igi.postprocess` 同口径：本批内**非空**地域组合只有 1 种 ⇒ 视为默认值、一律清空。
    沈阳实测（siteId 123/118 各抽 100 行）非空组合只有 `辽宁省/沈阳市/和平区` ⇒ 全剥离。
    """
    combos = {
        (r.get("extra", {}).get("province"), r.get("extra", {}).get("city"),
         r.get("extra", {}).get("area"))
        for r in rows
    }
    combos.discard((None, None, None))
    constant = len(combos) == 1
    out: list[dict] = []
    for r in rows:
        e = r.get("extra") or {}
        if constant and (e.get("province") or e.get("city") or e.get("area")):
            e["province"] = e["city"] = e["area"] = None
            e["region"] = None
            e.pop("pForumNames", None)
            e["geo_note"] = "上游地域字段为该站默认值（单值恒定），已剥离"
            r["extra"] = e
        out.append(r)
    return out


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """遍历沈阳各 siteId 取已答复信件（`limit` 为跨 site 累计的**本轮新增**上限）。

    ⚠ 全量约 1.7 万条（枚举值）⇒ 长任务请用分片增量驱动
    `recon/igi-chunked.py shenyang_igi`（逐 siteId + 页窗口落盘）。
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
