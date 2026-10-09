"""适配器：**宝鸡市·政民互动信箱（IGI 平台，49 个 siteId）**——2026-10-09 第 11 轮新增。

## 怎么找到的
第 10 轮**地级市 IGI 横向普查**（`igi-portal-sweep-city2.json`，93 城）命中 14 个门户，
宝鸡是陕西两个命中之一（另一为咸阳）。第 10 轮只登记未枚举；第 11 轮枚举 + 实测后接入。

## 关键事实（2026-10-09 第 11 轮实测）
1. **枚举**（`recon/igi-siteid-baoji.json`，扫 1..150、空 appId）：
   **49 个 siteId / 12,561 条**（12→1,943、17→1,560、9→1,246、94→878、10→621…）。
   ⚠ 枚举 total 是**上界**（第 10 轮新坑 A）。
2. **可采**（`var/tmp/r11/probe-city.py` 只读实测 siteId=12）：
   列表 `HTTP 200 totalResults=1,943`、首页 20 行 **`ISREPLY` 全 1**；
   明细 `HTTP 200`、`REPLYS=1`、答复正文 **378 字**。
3. ★ **地域字段是「恒定默认值」⇒ 剥离**：siteId=12 抽 20 行，非空地域组合**只有 1 种**
   —— `陕西省 / 宝鸡市 / 市辖区` ⇒ `postprocess` 一律清空。
4. ★ **与 `sn-igi`（陕西·我向省长说句话）不是同一批数据**：
   抽 siteId=12 的 20 条 id 与 `sn-*` 的 4,268 个 id 比对 ⇒ **重叠 0/20**。
   （`sn-igi` 基座是 `www.shaanxi.gov.cn/IGI` 单站；宝鸡是 `www.baoji.gov.cn/IGI` 独立部署。）
   ⇒ **不声明 `EXTRA_SEEN_KEYS`**。⚠ 20 条是抽样、不是全量。
5. 端点 `https://www.baoji.gov.cn/IGI`（**https**）；须带 `Referer: https://www.baoji.gov.cn/`。
6. 行数组键是 `datas.data`；行是大写键。

## 价值
陕西已有 `sn-igi`（省门户，4,084 条）⇒ 本条是**第二台独立部署**，枚举上界 12,561 条（≈ +3 倍）。
"""
from __future__ import annotations

from adapters._igi_common import existing_ids, harvest_igi

SITE = {
    "key": "baoji-igi",
    "name": "宝鸡市·政民互动信箱（IGI）",
    "kind": "api",
    "level": "city",
    "entry": "https://www.baoji.gov.cn/IGI/nbhd/openGovmsgbox.do",
    "status": "ok",
    "note": "IGI 49 个 siteId（空 appId，枚举上界 12,561 条）；与 sn-igi 不同部署（记录 id 重叠 0/20）；"
            "上游地域字段为门户默认值（宝鸡市/市辖区），已剥离；须带 Referer；https 可达",
}

BASE = "https://www.baoji.gov.cn/IGI"
REFERER = "https://www.baoji.gov.cn/"
APP_ID = ""                       # ★ 必须空：带 appId 会过滤掉大部分记录
GROUP_ID = None

#: 49 个 siteId（`recon/igi-siteid-baoji.json`，2026-10-09 扫 1..150 空 appId），
#: 按 totalResults **降序**，枚举上界合计 **12,561** 条。降序 = 长任务先跑大块。
SITE_IDS = (
    "12 17 9 94 10 101 16 72 80 90 78 99 "
    "95 15 67 7 13 96 66 14 69 71 81 92 "
    "76 86 63 4 88 77 82 102 18 98 62 65 "
    "91 89 93 73 74 83 85 8 87 84 64 68 "
    "11"
).split()


def postprocess(rows: list[dict]) -> list[dict]:
    """剥离**恒定**地域（= 门户默认值）。判定口径同 `baotou_igi.postprocess`。

    宝鸡实测 siteId=12 抽 20 行：非空组合只有 `陕西省/宝鸡市/市辖区` ⇒ 全剥离。
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
    """遍历宝鸡各 siteId 取已答复信件（`limit` 为跨 site 累计的**本轮新增**上限）。

    ⚠ 枚举上界 12,561 条 ⇒ 长任务请用分片增量驱动
    `recon/igi-chunked.py baoji_igi --sites-json igi-siteid-baoji.json --page-chunk 20`。
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
