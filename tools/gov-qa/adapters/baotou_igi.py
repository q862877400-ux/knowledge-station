"""适配器：**包头市·政民互动信箱（IGI 平台，多 siteId）**——2026-10-09 第 7 轮新增。

## 怎么找到的
第 5 轮的 `recon/igi-portal-sweep.py` 对 34 个城市门户各打一发列表请求，**包头命中**；
第 6 轮 `recon/igi-siteid-scan.py baotou` 扫 siteId=1..300（空 appId）实测：
**42 个 siteId / 7,243 条**（`recon/igi-siteid-baotou.json`；46→1068、57→751、64→703、40→475…）。

## 关键事实（2026-10-09 实测）
1. **可采**：列表 `HTTP 200`（siteId=46 → total=1,068、siteId=57 → 751），行是大写键。
2. ★ **地域字段是「恒定默认值」⇒ 剥离**：抽 siteId=46 的 100 条，
   非空地域组合**只有 1 种** —— `内蒙古自治区/包头市/市辖区`（28/100；其余 72 条为空）
   ⇒ 与 `nmg-igi` 同类（门户自身位置），原样落盘会污染三级归属 ⇒ `postprocess` 一律清空。
3. ★ **与 `nmg-igi` 不是同一批数据**（两条独立证据）：
   ① 同 siteId 的总数不同（包头 66→451 vs 内蒙古 66→5651）⇒ **两台部署**；
   ② 抽 100 条包头 id（区间 78,034–235,961）与 `nmg-igi` 的 1,200 个 id 比对 ⇒ **重叠 0**。
   ⇒ **不声明 `EXTRA_SEEN_KEYS`**。⚠ 100 条是抽样、不是全量；下游按 `(source,id)` 去重即可。
4. 端点 `https://www.baotou.gov.cn/IGI`；须带 `Referer: https://www.baotou.gov.cn/`。
"""
from __future__ import annotations

from adapters._igi_common import existing_ids, harvest_igi

SITE = {
    "key": "baotou-igi",
    "name": "包头市·政民互动信箱（IGI）",
    "kind": "api",
    "level": "city",
    "entry": "https://www.baotou.gov.cn/IGI/nbhd/openGovmsgbox.do",
    "status": "ok",
    "note": "IGI 42 站 / 约 7,243 条（空 appId 取全量）；须带 Referer；上游地域字段为门户默认值，已剥离",
}

BASE = "https://www.baotou.gov.cn/IGI"
REFERER = "https://www.baotou.gov.cn/"
APP_ID = ""                       # ★ 必须空：带 appId 会过滤掉大部分记录
GROUP_ID = None

#: 42 个 siteId（`recon/igi-siteid-baotou.json`，2026-10-09 扫 1..300 空 appId），
#: 按 totalResults 降序，合计 **7,243** 条。降序 = 长任务先跑大块。
SITE_IDS = (
    "46 57 64 40 66 15 8 21 20 45 31 61 35 39 12 62 44 14 22 49 53 "
    "18 48 17 65 26 30 42 27 38 9 51 16 43 47 11 60 67 7 19 41 59"
).split()


def postprocess(rows: list[dict]) -> list[dict]:
    """剥离**恒定**地域（= 门户/站点默认值）。

    判定口径与 `nmg_igi.postprocess` 相同：某批内**非空**地域组合只有 1 种 ⇒ 视为默认值、一律清空。
    包头实测 siteId=46 抽 100 条：非空组合只有 `内蒙古自治区/包头市/市辖区` ⇒ 全剥离。
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
    """遍历包头各 siteId 取已答复信件（`limit` 为跨 site 累计的**本轮新增**上限）。

    ⚠ 全量约 7,243 条（枚举值）⇒ 长任务请用分片增量驱动
    `recon/igi-chunked.py baotou_igi`（逐 siteId + 页窗口落盘）。
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
