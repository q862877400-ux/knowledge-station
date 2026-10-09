"""适配器：**荆州市·政民互动信箱（IGI 平台，29 个 siteId）**——2026-10-09 第 11 轮新增。

## 怎么找到的
第 10 轮**地级市 IGI 横向普查**（`igi-portal-sweep-city2.json`，93 城）命中 14 个门户，荆州其一。
第 11 轮枚举 + 实测后接入。

## 关键事实（2026-10-09 第 11 轮实测）
1. **枚举**（`recon/igi-siteid-jingzhou.json`，扫 1..150、空 appId）：**29 个 siteId / 5,130 条**
   （15→861、32→628、35→627、13→451…）。⚠ 枚举 total 是**上界**（第 10 轮新坑 A）。
2. **可采**（`var/tmp/r11/probe-city.py` 只读实测 siteId=15）：列表 `HTTP 200 totalResults=861`、
   首页 20 行 **`ISREPLY` 全 1**；明细 `HTTP 200`、`REPLYS=1`、答复正文 33 字（偏短，下游可按长度过滤）。
3. ★ **地域是「恒定默认值」⇒ 剥离**：siteId=15 抽 20 行非空组合只有 1 种 `湖北省/荆州市/市辖区`。
4. ⚠ **与 `hb-*`（湖北既有线）有轻微重叠**：抽 20 条 id 与 `hb-*`（含 hb-hdjl/hb-wuhan，9,118 个 id）
   比对 ⇒ **重叠 1/20（5%）**。⇒ 判定为**跨源重复投递**（同一封信同时投省门户与市门户），
   **不声明 `EXTRA_SEEN_KEYS`**（重叠太小，声明了反而会误跳过荆州自有信件）；下游按 `(source,id)` 去重即可。
5. 端点 `https://www.jingzhou.gov.cn/IGI`（**https**）；须带 `Referer: https://www.jingzhou.gov.cn/`。
6. 行数组键 `datas.data`；行是大写键。
"""
from __future__ import annotations

from adapters._igi_common import existing_ids, harvest_igi

SITE = {
    "key": "jingzhou-igi",
    "name": "荆州市·政民互动信箱（IGI）",
    "kind": "api",
    "level": "city",
    "entry": "https://www.jingzhou.gov.cn/IGI/nbhd/openGovmsgbox.do",
    "status": "ok",
    "note": "IGI 29 个 siteId（空 appId，枚举上界 5,130 条）；与 hb-* 记录 id 重叠 1/20（跨源重复投递）；"
            "地域为门户默认值已剥离；须带 Referer；https 可达",
}

BASE = "https://www.jingzhou.gov.cn/IGI"
REFERER = "https://www.jingzhou.gov.cn/"
APP_ID = ""
GROUP_ID = None

#: 29 个 siteId（`recon/igi-siteid-jingzhou.json`，2026-10-09 扫 1..150 空 appId），按 total 降序，上界合计 5,130。
SITE_IDS = (
    "15 32 35 13 26 42 16 17 11 22 19 41 "
    "28 14 21 46 34 31 29 27 18 33 73 20 "
    "77 38 12 36 63"
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
    """遍历荆州各 siteId 取已答复信件。长任务用 `recon/igi-chunked.py jingzhou_igi --sites-json ...`。"""
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
