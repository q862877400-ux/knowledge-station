"""适配器：**内蒙古自治区·政民互动信箱（IGI 平台，多 siteId）**——2026-10-09 新增。

## 怎么找到的（这一步以前从没人做过）
`recon/igi-portal-sweep.py` 对 22 个「尚未确认有 IGI」的省门户各打一发列表请求，
**内蒙古（www.nmg.gov.cn）命中**（返回标准 IGI 体 `{statusCode,message,datas:{data,pageInfo}}`）。
随后 `recon/igi-siteid-scan.py neimenggu` 扫 siteId=1..300（空 appId）实测：
**42 个 siteId / 26,074 条**（66 → 5651、68 → 3436、88 → 3286、71 → 2068、92 → 1857、67 → 1818 …）。

## 为什么价值高
内蒙古在本模块此前的存量只有 **67 条**（`nmg-xinxiang`，走门户自建接口 `getCaseInfoList`）
⇒ 本适配器一次性把该省语料放大 **≈389 倍**，且内蒙古正是任务书点名的「全国覆盖缺口」省份之一。

## 关键事实（全部实测）
1. **`appId` 是过滤条件不是站点标识**：与山西/广西同理，空 `appId` 才拿该 siteId 全量。
2. ★ **地域字段是假的**：抽 siteId=66 / 68 / 88 各 50 条，**100% 恒为**
   `内蒙古自治区 / 呼和浩特市 / 市辖区` ⇒ 这是**门户自身位置**，不是逐信地域。
   原样落盘会把 2.6 万条全灌进同一个「区」格子、**污染三级归属统计** ⇒ **一律剥离**
   （与山西同处理；广西/宁夏/湖北才是真地域）。
3. 端点 `https://www.nmg.gov.cn/IGI`；须带 `Referer: https://www.nmg.gov.cn/zmhd/`。

## 与既有内蒙古线的关系
`nmg-xinxiang`（67 条）走的是门户**自建**接口（`getCaseInfoList`，id 为 UUID），
与 IGI 的 `METADATAID`（数字）**不是同一套 id** ⇒ 不存在 id 冲突；
但为稳妥，`harvest()` 仍把它的 id 并进 `skip_ids`（同一条信件若两路都暴露则不重复落盘）。
"""
from __future__ import annotations

from adapters._igi_common import existing_ids, harvest_igi

SITE = {
    "key": "nmg-igi",
    "name": "内蒙古自治区·政民互动信箱（IGI）",
    "kind": "api",
    "level": "province",
    "entry": "https://www.nmg.gov.cn/IGI/nbhd/openGovmsgbox.do",
    "status": "ok",
    "note": "IGI 多 siteId（空 appId 取全量，42 站 / 约 2.6 万条）；须带 Referer；"
            "上游地域字段为门户默认值，已剥离",
}

BASE = "https://www.nmg.gov.cn/IGI"
REFERER = "https://www.nmg.gov.cn/zmhd/"
APP_ID = ""                       # ★ 必须空：带 appId 会过滤掉大部分记录
GROUP_ID = None

#: 42 个 siteId（`recon/igi-siteid-neimenggu.json`，2026-10-09 扫 1..300 空 appId），
#: 按 totalResults 降序，合计 **26,074** 条。降序 = 长任务先跑大块
#: （`igi-chunked.py` 逐 siteId 落盘，中断只损失当前一块）。
SITE_IDS = (
    "66 68 88 71 92 67 55 70 101 91 85 82 90 76 83 97 61 56 102 15 75 "
    "87 96 80 77 94 95 54 89 72 53 74 86 84 98 69 73 121 99 120 32 3"
).split()

#: 供 `recon/igi-chunked.py` 读取：额外并进 `skip_ids` 的兄弟源（同省另一入口）。
EXTRA_SEEN_KEYS = ("nmg-xinxiang",)


def postprocess(rows: list[dict]) -> list[dict]:
    """剥离**恒定**地域（= 门户/站点默认值）。

    判定口径：某 siteId 内**非空**地域组合只有 **1 种** ⇒ 视为默认值、一律清空。
    内蒙古实测 66/68/88 全部 1 种（`内蒙古自治区/呼和浩特市/市辖区`）⇒ 全剥离。
    保留 `geo_note` 说明原因，便于下游知道「这批地域是主动清空的，不是上游缺失」。
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
    """遍历内蒙古各 siteId 取已答复信件（`limit` 为跨 site 累计的**本轮新增**上限）。

    ⚠ 内蒙古全量约 2.6 万条（枚举值）⇒ 用 `harvest.py` 一次跑完不现实；
    长任务请用分片增量驱动 `recon/igi-chunked.py nmg_igi`（逐 siteId 落盘）。
    """
    out: list[dict] = []
    seen = existing_ids(SITE["key"]) | existing_ids("nmg-xinxiang")
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
