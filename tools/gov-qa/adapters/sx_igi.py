"""适配器：**山西省·政民互动信箱（IGI 平台，多 siteId）**——2026-10-09 新增。

## 为什么会有这个适配器
`adapters/sx_szxx.py`（siteId=110，省长信箱）只落了 **400** 条，
而上游 **1872**；更关键的是：**山西省门户的 IGI 从来没有被枚举过**。
2026-10-09 用 `recon/igi-siteid-scan.py` 扫 siteId=1..300（空 appId）实测命中
**30+ 个 siteId**，其中大块如 siteId=32（教育厅 8836）、41（8429）、92（商务厅 7309）、
45（卫健委 6991）、36（省发改委 4653）—— 旧的「1..60 窗口」与「从未扫山西」双重遗漏。

## 两个实测要点（写下来免得重踩）
1. **`appId` 是过滤条件，不是站点标识**：山西 siteId=36 带 `appId=584617` 只得 826，
   空 `appId` 得 **4653**。⇒ 枚举与采集一律用**空 appId**，否则漏掉未挂到已知 appId 的记录。
2. **地域字段是门户默认值**：山西各 siteId 的 `PROVINCE/CITY/AREA` 实测**逐条恒定**为
   `山西省/太原市/小店区`（50/50 相同），或全空 ⇒ **不是逐信地域**，是门户自身位置。
   若原样落盘会把 4 万+ 条灌进「山西省/太原市/小店区」这一个格子，**污染三级归属统计**。
   ⇒ 本适配器统一**剥离**该默认值（`_PORTAL_DEFAULT`），归省改由来源前缀 `sx-` 承担。

## siteId=110 不在本适配器内
siteId=110 已由 `sx-szxx` 落了 400 条（source=`sx-szxx`）。若这里再采会因 source 不同
而**产生重复 id**。⇒ 110 交给 `sx-szxx` 自己续采（`harvest.py --site sx-szxx --limit N`）。
"""
from __future__ import annotations

import re

from adapters._igi_common import existing_ids, harvest_igi

SITE = {
    "key": "sx-igi",
    "name": "山西省·政民互动信箱（IGI）",
    "kind": "api",
    "level": "province",
    "entry": "http://www.shanxi.gov.cn/zmhd/",
    "status": "ok",
    "note": "IGI 多 siteId（空 appId 取全量）；地域字段为门户默认值已剥离；须带 Referer",
}

BASE = "http://www.shanxi.gov.cn/IGI"
REFERER = "http://www.shanxi.gov.cn/zmhd/"
APP_ID = ""                       # ★ 必须空：带 appId 会过滤掉大部分记录
GROUP_ID = None

#: siteId → 枚举当日 totalResults（`recon/igi-siteid-shanxi.json`，2026-10-09，扫 1..300 空 appId）。
#: **46 个 siteId / 84,381 条**（该文件是权威清单；数字随上游增长，采集以接口返回为准）。
#: 本表 = 46 个里**剔除 siteId=110**（1872，由 `sx-szxx` 负责，避免 source 不同产生重复 id）。
#: 降序排列：长任务先跑大块（`igi-chunked.py` 逐 siteId 落盘，中断只损失当前一块）。
SITE_IDS = [
    "24",   # 14662
    "32",   # 山西省教育厅 8836
    "41",   # 省教育厅/人社厅等 8429
    "92",   # 山西省商务厅 7309
    "45",   # 山西省卫健委 6991
    "36",   # 山西省发改委 4653
    "22",   # 4120
    "8",    # 4107
    "19",   # 3940
    "17",   # 2672
    "35",   # 山西省药品监督管理局 2327
    "21",   # 1759
    "31",   # 山西省司法厅 1609
    "34",   # 1519
    "11",   # 1405
    "38",   # 1031
    "57",   # 729
    "93",   # 662
    "14",   # 589
    "23",   # 586
    "90",   # 572
    "16",   # 569
    "82",   # 488
    "7",    # 378
    "60",   # 299
    "18",   # 285
    "29",   # 258
    "13",   # 256
    "52",   # 235
    "70",   # 201
    "25",   # 183
    "59",   # 155
    "28",   # 142
    "6",    # 135
    "15",   # 112
    "83",   # 94
    "68",   # 56
    "44",   # 55
    "73",   # 44
    "66",   # 24
    "5",    # 17
    "65",   # 7
    "100",  # 4
    "106",  # 4
    "126",  # 1
]

#: 供 `recon/igi-chunked.py` 读取：额外并进 `skip_ids` 的兄弟源。
#: `sx-szxx` 是省长信箱（siteId=110），与本模块同门户、可能暴露同一批信件 ⇒ 去重时并入。
#: ⚠ 2026-10-09 前该并集**硬编码在 igi-chunked.py 里**，会让宁夏/广西等模块误并山西 id，已改。
EXTRA_SEEN_KEYS = ("sx-szxx",)

#: 上游给的门户默认地域（对全部记录恒定，非逐信地域）⇒ 一律剔除。
_PORTAL_DEFAULT = ("山西省", "太原市", "小店区")

#: 占位记录：个别 siteId 用「X月没有政务建议咨询类信息」当答复（question == answer）。
#: 实测 sx-igi-28（省国资委）18 条**全部**是这种，**不是真问答** ⇒ 落盘只会虚增语料。
_PLACEHOLDER_RE = re.compile(r"没有.{0,12}信息|暂无|无相关")


def postprocess(rows: list[dict]) -> list[dict]:
    """① 丢弃「答复==问题」的占位记录；② 剔除门户默认地域（避免污染三级归属统计）。"""
    out: list[dict] = []
    for r in rows:
        q = (r.get("question") or "").strip()
        a = (r.get("answer") or "").strip()
        if a and a == q and _PLACEHOLDER_RE.search(a):
            continue                                     # 占位记录，不是真问答
        e = r.get("extra") or {}
        if (e.get("province"), e.get("city"), e.get("area")) == _PORTAL_DEFAULT:
            e["province"] = e["city"] = e["area"] = None
            e["region"] = None
            e.pop("pForumNames", None)
            e["geo_note"] = "上游地域字段为门户默认值，已剥离"
        r["extra"] = e
        out.append(r)
    return out


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """遍历山西各 siteId 取已答复信件（`limit` 为跨 site 累计的**本轮新增**上限）。

    ⚠ 山西全量约 4.8 万条（枚举值）⇒ 用 `harvest.py` 一次跑完不现实；
    长任务请用分片增量驱动 `recon/sx-igi-chunked.py`（逐 siteId 落盘）。
    """
    out: list[dict] = []
    seen = existing_ids(SITE["key"]) | existing_ids("sx-szxx")
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
        out.extend(strip_portal_geo(rows))
    return out
