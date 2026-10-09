"""适配器：**贵州省·人民政府门户·政民互动（IGI 平台，全量 siteId）**——2026-10-09 新增。

## 为什么会有它
`adapters/gz_portal.py`（2026-10-08）只枚举了 **siteId=1..60**，命中 11 个 site / 2,597 条。
2026-10-09 用 `recon/igi-siteid-scan.py guizhou` 把窗口扩到 **1..300**（空 appId）实测：
**44 个 siteId / 30,041 条**（70 → 16421、93 → 4627、48 → 1254、84 → 1129、97 → 1093 …）
⇒ 旧窗口漏掉了 **3.3 倍**的量，且最大的 siteId=70（16,421 条）**完全在窗口外**。

## 与 gz-portal 的分工（避免 source 不同产生重复 id）
gz_portal 已负责 siteId **30/31/35/36/48/49/51/53/56/58/59**（11 个）⇒ 本适配器**剔除这 11 个**，
只跑其余 **33 个**；`harvest()` 另把 `gz-portal` 已落盘 id 并进 `skip_ids` 兜底。

## 关键事实（实测）
1. **`appId` 是过滤条件不是站点标识**：空 `appId` 才拿该 siteId 全量。
2. **地域字段是混合态，必须逐站判**（实测）：
   · siteId=48 → 50/50 恒为 `贵州省/贵阳市/观山湖区` ⇒ **假**（站点默认值）
   · siteId=70 → 42/50 空，其余为 `黔南州/都匀市`、`/三都自治县`、`/龙里县` ⇒ **真**（逐信变化）
   · siteId=93 → 34/50 空，其余 `黔南州/都匀市`、`贵阳市/花溪区` ⇒ **真**
   ⇒ 统一规则：某 siteId 内**非空**地域组合只有 1 种即视为默认值、清空；多种则保留。
3. base `http://www.guizhou.gov.cn/IGI`；须带 `Referer: http://www.guizhou.gov.cn/`。

## 与既有贵州线的关系
本模块另有 36 个 `gz-*` 省直部门适配器，走各自子域（如 `sthj.guizhou.gov.cn/IGI`）⇒ 不同 host、不同记录。
"""
from __future__ import annotations

from adapters._igi_common import existing_ids, harvest_igi

SITE = {
    "key": "gz-igi",
    "name": "贵州省·人民政府门户·政民互动（IGI 全量 siteId）",
    "kind": "api",
    "level": "province",
    "entry": "http://www.guizhou.gov.cn/IGI/nbhd/openGovmsgbox.do",
    "status": "ok",
    "note": "IGI 多 siteId（空 appId 取全量，33 站 / 约 3 万条）；须带 Referer；"
            "地域字段逐站判真伪（单值恒定即剥离）",
}

BASE = "http://www.guizhou.gov.cn/IGI"
REFERER = "http://www.guizhou.gov.cn/"
APP_ID = ""                       # ★ 必须空：带 appId 会过滤掉大部分记录
GROUP_ID = None

#: 枚举命中的 44 个 siteId 中**剔除** gz-portal 已负责的 11 个
#: （30/31/35/36/48/49/51/53/56/58/59），剩 33 个。
#: 来源 `recon/igi-siteid-guizhou.json`（2026-10-09 扫 1..300 空 appId），按 totalResults 降序。
SITE_IDS = (
    "70 93 84 97 71 101 69 68 87 91 88 65 85 73 80 67 74 76 78 96 102 "
    "111 112 95 110 104 100 107 99 81 103 108 72"
).split()

#: 供 `recon/igi-chunked.py` 读取：额外并进 `skip_ids` 的兄弟源（gz-portal 占了另外 11 个 siteId）。
EXTRA_SEEN_KEYS = ("gz-portal",)


def postprocess(rows: list[dict]) -> list[dict]:
    """剥离**恒定**地域（= 站点默认值），保留逐信变化的地域。

    判定口径：某 siteId 内**非空**地域组合只有 **1 种** ⇒ 视为默认值、清空；
    ≥2 种 ⇒ 认为是逐信真实地域、原样保留。见模块 docstring 的实测三例。
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
    """遍历贵州门户 IGI 各 siteId（33 个）取已答复信件。

    `limit` 为跨 site 累计的**本轮新增**上限。
    ⚠ 全量约 3 万条（枚举值）⇒ 长任务请用 `recon/igi-chunked.py gz_igi`（逐 siteId 落盘）。
    """
    out: list[dict] = []
    seen = existing_ids(SITE["key"]) | existing_ids("gz-portal")
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
        out.extend(postprocess(rows))          # ★ harvest.py 不调 postprocess，必须这里调
    return out
