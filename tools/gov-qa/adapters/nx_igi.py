"""适配器：**宁夏回族自治区·政民互动信箱（IGI 平台，多 siteId）**——2026-10-09 新增。

## 为什么会有这个适配器
`adapters/nx_zxxx.py` 只接了 **siteId=115**（主席信箱，597 → 664 条），
因为 2026-10-08 那次是从门户页面里读到这一个 id。
2026-10-09 用 `recon/igi-siteid-scan.py` 扫 siteId=1..300（空 appId）实测命中
**65 个 siteId / 13,014 条**（siteId=259 → 6055、135 → 772、186 → 647、137 → 628 …）。

## 关键事实
1. **`appId` 是过滤条件，不是站点标识**（与山西/广西同理）：空 `appId` 才拿到该 siteId 全量。
2. **地域字段是真实的**：`nx-zxxx`（siteId=115）597 条里有 **80 种**
   `PROVINCE/CITY/AREA` 组合（如「宁夏回族自治区/银川市/金凤区」）
   ⇒ **宁夏是能扩「县」的通道**，故**不剥离**地域（与山西不同）。
3. base `https://www.nx.gov.cn/IGI`；须带 `Referer: https://www.nx.gov.cn/hdjl/`。

## siteId=115 不在本适配器内
siteId=115 已由 `nx-zxxx` 落了 664 条（source=`nx-zxxx`）。这里再采会因 source 不同
而**产生重复 id** ⇒ 交给 `nx-zxxx` 自己续采。

## ⚠ 一条教训（本轮踩到两次）
枚举**扫描中途的日志**只显示已命中的项 ⇒ 若据此下结论会**严重低估**
（我先按中途日志写「宁夏只有 1 个 siteId」，扫完才发现是 **65 个**）。
⇒ **枚举清单必须等扫描跑完、从 json 取。**
"""
from __future__ import annotations

from adapters._igi_common import existing_ids, harvest_igi

SITE = {
    "key": "nx-igi",
    "name": "宁夏回族自治区·政民互动信箱（IGI）",
    "kind": "api",
    "level": "province",
    "entry": "https://www.nx.gov.cn/hdjl/",
    "status": "ok",
    "note": "IGI 多 siteId（空 appId 取全量）；**带真实省/市/区三级归属**；须带 Referer",
}

BASE = "https://www.nx.gov.cn/IGI"
REFERER = "https://www.nx.gov.cn/hdjl/"
APP_ID = ""                       # ★ 必须空：带 appId 会过滤掉大部分记录
GROUP_ID = None

#: 63 个 siteId（`recon/igi-siteid-ningxia.json`，2026-10-09 扫 1..300 空 appId），
#: 按 totalResults 降序，合计 **12,347** 条。**不含 siteId=115**（由 nx-zxxx 负责）。
SITE_IDS = (
    "259 135 186 137 166 181 160 279 140 275 161 138 139 173 255 158 159 136 174 156 "
    "237 175 250 269 205 241 286 285 254 157 223 281 262 264 267 206 261 187 282 300 "
    "240 258 280 292 228 274 277 289 234 238 272 182 145 256 284 288 168 233 260 263 "
    "270 294 295"
).split()


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """遍历宁夏各 siteId 取已答复信件（`limit` 为跨 site 累计的**本轮新增**上限）。

    ⚠ 宁夏全量约 1.3 万条（枚举值）⇒ 长任务请用分片增量驱动
    `recon/igi-chunked.py nx_igi`（逐 siteId 落盘）。
    """
    out: list[dict] = []
    seen = existing_ids(SITE["key"]) | existing_ids("nx-zxxx")
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
        out.extend(rows)
    return out
