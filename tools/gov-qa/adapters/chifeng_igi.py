"""适配器：**赤峰市·政民互动信箱（IGI 平台，53 个 siteId）**——2026-10-09 第 11 轮新增。

## 怎么找到的
第 10 轮**地级市 IGI 横向普查**（`igi-portal-sweep-city2.json`，93 城）命中 14 个门户，
赤峰是内蒙古两个命中之一（另一为通辽）。第 10 轮只登记未枚举；第 11 轮枚举 + 实测后接入。

## 关键事实（2026-10-09 第 11 轮实测）
1. **枚举**（`recon/igi-siteid-chifeng.json`，扫 1..150、空 appId）：
   **53 个 siteId / 11,485 条**（12→2,969、22→1,211、19→970、51→761、23→645…）。
   ⚠ 枚举 total 是**上界**（第 10 轮新坑 A）。
2. **可采**（`var/tmp/r11/probe-city.py` 只读实测 siteId=12）：
   列表 `HTTP 200 totalResults=2,969`、首页 20 行 **`ISREPLY` 全 1**；明细 `HTTP 200`、`REPLYS=1`。
3. ★ **地域字段全空**（siteId=12 抽 20 行 `PROVINCE/CITY/AREA` 均空）⇒ 保留 `postprocess` 兜底（无可剥离）。
4. ★★ **与 `nmg-igi`（内蒙古省门户）不是同一台部署**（两条独立证据）：
   ① 枚举对照：赤峰 53 站里只有 **9 个 siteId 与 nmg 重合，且 0 个 total 相同**，**44 个 siteId 为赤峰独有**；
   ② 抽 siteId=12 的 20 条 id 与 `nmg-*` 的 5,717 个 id 比对 ⇒ **重叠 0/20**。
   ⇒ **不声明 `EXTRA_SEEN_KEYS`**（与包头 §4 的判据同源）。⚠ 20 条是抽样、不是全量。
5. 端点 `https://www.chifeng.gov.cn/IGI`（**https**）；须带 `Referer: https://www.chifeng.gov.cn/`。
6. 行数组键是 `datas.data`；行是大写键。

## 价值
内蒙古已有 `nmg-igi`（省门户）+ `baotou-igi`（包头）⇒ 本条是**第三台独立部署**，枚举上界 11,485 条。
"""
from __future__ import annotations

from adapters._igi_common import existing_ids, harvest_igi

SITE = {
    "key": "chifeng-igi",
    "name": "赤峰市·政民互动信箱（IGI）",
    "kind": "api",
    "level": "city",
    "entry": "https://www.chifeng.gov.cn/IGI/nbhd/openGovmsgbox.do",
    "status": "ok",
    "note": "IGI 53 个 siteId（空 appId，枚举上界 11,485 条）；与 nmg-igi 不同部署"
            "（siteId 映射 44 独有 / 记录 id 重叠 0/20）；须带 Referer；https 可达",
}

BASE = "https://www.chifeng.gov.cn/IGI"
REFERER = "https://www.chifeng.gov.cn/"
APP_ID = ""                       # ★ 必须空：带 appId 会过滤掉大部分记录
GROUP_ID = None

#: 53 个 siteId（`recon/igi-siteid-chifeng.json`，2026-10-09 扫 1..150 空 appId），
#: 按 totalResults **降序**，枚举上界合计 **11,485** 条。降序 = 长任务先跑大块。
SITE_IDS = (
    "12 22 19 51 23 20 16 40 33 41 48 32 "
    "27 84 17 74 86 11 29 18 30 71 49 69 "
    "37 43 44 15 24 25 21 34 46 26 42 38 "
    "14 31 36 35 94 28 39 45 13 60 93 63 "
    "50 10 47 64 72"
).split()


def postprocess(rows: list[dict]) -> list[dict]:
    """剥离**恒定**地域（= 门户默认值）。判定口径同 `baotou_igi.postprocess`。

    赤峰实测 siteId=12 抽 20 行地域**全空** ⇒ 本函数当前不生效（兜底：若某批出现单值恒定则剥离）。
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
    """遍历赤峰各 siteId 取已答复信件（`limit` 为跨 site 累计的**本轮新增**上限）。

    ⚠ 枚举上界 11,485 条 ⇒ 长任务请用分片增量驱动
    `recon/igi-chunked.py chifeng_igi --sites-json igi-siteid-chifeng.json --page-chunk 20`。
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
