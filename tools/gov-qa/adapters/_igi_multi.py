"""IGI **多 siteId 适配器**的公共构造器（2026-10-09 新增）。

## 为什么要有它
`_igi_common.harvest_igi` 只负责「一个 siteId 翻页取明细」；
而 IGI 平台的门户往往有 **几十个 siteId**（山西 45、广西 207、沈阳 53…）。
`adapters/nmg_igi.py` / `gz_igi.py` 已经把「遍历 siteId + 恒定地域剥离」写了两遍；
本模块把它抽出来，新增门户只需 ~25 行（见 `nn_igi.py` 等）。

## 两个必须一起用的东西
1. `make_harvest(...)` —— 造出符合 `harvest.py` 契约的 `harvest(fetch, *, limit=None)`。
   内部**逐 site 调用 `strip_constant_geo`**，因为 **`harvest.py` 不会调用 `postprocess`**
   （只有 `recon/igi-chunked.py` 会）⇒ 转换必须写在 `harvest()` 里才两种驱动都生效。
2. `strip_constant_geo(rows)` —— **地域真伪判定**：某 siteId 内**非空**地域组合只有 1 种
   ⇒ 视为该站默认值（门户自身位置）、一律清空；≥2 种 ⇒ 认为是逐信真实地域、原样保留。

## 实测依据（2026-10-09）
| 站 | 抽样 | 判定 |
|---|---|---|
| 山西 各 siteId | 逐条恒 `山西省/太原市/小店区` | **假** ⇒ 剥离 |
| 内蒙古 66/68/88 | 逐条恒 `内蒙古自治区/呼和浩特市/市辖区` | **假** ⇒ 剥离 |
| 贵州 48 | 50/50 恒 `贵州省/贵阳市/观山湖区` | **假** ⇒ 剥离 |
| 贵州 70/93 | 非空值有 2~3 种（黔南州都匀市/三都自治县/龙里县…）| **真** ⇒ 保留 |
| 广西 206 / 湖北 / 宁夏 | 多种组合 | **真** ⇒ 保留 |
"""
from __future__ import annotations

from adapters._igi_common import existing_ids, harvest_igi

__all__ = ["strip_constant_geo", "make_harvest"]


def strip_constant_geo(rows: list[dict]) -> list[dict]:
    """剥离**恒定**地域（= 门户/站点默认值），保留逐信变化的地域。

    判定粒度是**传进来的这批 rows**（`igi-chunked.py` 与 `make_harvest` 都是**按 siteId** 调它，
    所以粒度就是「一个 siteId」——正是我们想要的）。保留 `geo_note` 说明原因，
    便于下游知道「这批地域是主动清空的，不是上游缺失」。
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


def make_harvest(SITE: dict, BASE: str, REFERER: str, SITE_IDS,
                 APP_ID: str = "", GROUP_ID: str | None = None,
                 extra_seen: tuple[str, ...] = (), max_pages: int = 300):
    """造一个遍历 `SITE_IDS` 的 `harvest(fetch, *, limit=None)`。

    `extra_seen`：额外并进 `skip_ids` 的**兄弟源**（同门户另一入口，可能暴露同一批信件）。
    `limit` 语义 = 跨 site 累计的**本轮新增**条数上限（`skip_ids` 命中则不计）。
    """

    def harvest(fetch, *, limit: int | None = None) -> list[dict]:
        out: list[dict] = []
        seen = existing_ids(SITE["key"])
        for k in extra_seen:
            seen |= existing_ids(k)
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
                               max_pages=max_pages, skip_ids=seen)
            out.extend(strip_constant_geo(rows))
        return out

    return harvest
