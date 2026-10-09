"""适配器：**长治市·政民互动信箱（IGI 平台，15 个 siteId）**——2026-10-09 第 11 轮新增。

## 怎么找到的
第 10 轮**地级市 IGI 横向普查**（`igi-portal-sweep-city2.json`，93 城）命中 14 个门户，长治其一。
第 11 轮枚举 + 实测后接入。

## 关键事实（2026-10-09 第 11 轮实测）
1. **枚举**（`recon/igi-siteid-changzhi.json`，扫 1..150、空 appId）：**15 个 siteId / 6,657 条**
   （4→1,784、44→679、21→588、75→511…）。⚠ 枚举 total 是**上界**（第 10 轮新坑 A）。
2. **可采**（`var/tmp/r11/probe-city.py` 只读实测 siteId=4）：列表 `HTTP 200 totalResults=1,784`、
   首页 20 行 **`ISREPLY` 全 1**；明细 `HTTP 200`、`REPLYS=1`、答复正文 **328 字**。
3. ★ **地域是「恒定默认值」⇒ 剥离**：siteId=4 抽 20 行非空组合只有 1 种 `山西省/长治市/市辖区`。
4. ★ **与 `sx-igi`（山西省门户）不是同一台部署**：枚举对照 15 站里仅 6 个 siteId 重合、**0 个 total 相同**、
   **9 个 siteId 独有**；抽 20 条 id 与 `sx-*` 的 21,683 个 id 比对 ⇒ **重叠 0/20**。⇒ 不声明 `EXTRA_SEEN_KEYS`。
5. 端点 `https://www.changzhi.gov.cn/IGI`（**https**）；须带 `Referer: https://www.changzhi.gov.cn/`。
6. 行数组键 `datas.data`；行是大写键。
"""
from __future__ import annotations

from adapters._igi_common import existing_ids, harvest_igi

SITE = {
    "key": "changzhi-igi",
    "name": "长治市·政民互动信箱（IGI）",
    "kind": "api",
    "level": "city",
    "entry": "https://www.changzhi.gov.cn/IGI/nbhd/openGovmsgbox.do",
    "status": "ok",
    "note": "IGI 15 个 siteId（空 appId，枚举上界 6,657 条）；与 sx-igi 不同部署"
            "（9 个 siteId 独有 / 记录 id 重叠 0/20）；地域为门户默认值已剥离；须带 Referer；https 可达",
}

BASE = "https://www.changzhi.gov.cn/IGI"
REFERER = "https://www.changzhi.gov.cn/"
APP_ID = ""
GROUP_ID = None

#: 15 个 siteId（`recon/igi-siteid-changzhi.json`，2026-10-09 扫 1..150 空 appId），按 total 降序，上界合计 6,657。
SITE_IDS = (
    "4 44 21 75 42 50 53 18 46 24 126 72 "
    "47 129 60"
).split()


def postprocess(rows: list[dict]) -> list[dict]:
    """剥离**恒定**地域（= 门户默认值）。判定口径同 `baotou_igi.postprocess`。"""
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
    """遍历长治各 siteId 取已答复信件。长任务用 `recon/igi-chunked.py changzhi_igi --sites-json ...`。"""
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
