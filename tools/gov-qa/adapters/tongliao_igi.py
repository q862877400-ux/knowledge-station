"""适配器：**通辽市·政民互动信箱（IGI 平台，39 个 siteId）**——2026-10-09 第 11 轮新增。

## 怎么找到的
第 10 轮**地级市 IGI 横向普查**（`igi-portal-sweep-city2.json`，93 城）命中 14 个门户，通辽其一
（内蒙古两个命中：赤峰 + 通辽）。第 11 轮枚举 + 实测后接入。

## 关键事实（2026-10-09 第 11 轮实测）
1. **枚举**（`recon/igi-siteid-tongliao.json`，扫 1..150、空 appId）：**39 个 siteId / 3,843 条**
   （15→638、12→431、13→326、9→297…）。⚠ 枚举 total 是**上界**（第 10 轮新坑 A）。
2. **可采**（`var/tmp/r11/probe-city.py` 只读实测 siteId=15）：列表 `HTTP 200 totalResults=638`、
   首页 20 行 **`ISREPLY` 全 1**；明细 `HTTP 200`、`REPLYS=1`、答复正文 **1,034 字**。
3. ★ **地域是「单值恒定」⇒ 剥离**：siteId=15 抽 20 行非空组合只有 1 种 `内蒙古自治区/通辽市/科尔沁区`
   （通辽下辖多区县，却恒为科尔沁区 ⇒ 门户默认值）。⚠ 抽 20 行只够判"恒定"，非空率须落盘后复核。
4. ★ **与 `nmg-igi`（内蒙古省门户）不是同一台部署**：枚举对照 39 站里仅 3 个 siteId 重合、**0 个 total 相同**、
   **36 个 siteId 独有**；抽 20 条 id 与 `nmg-*` 的 5,717 个 id 比对 ⇒ **重叠 0/20**。⇒ 不声明 `EXTRA_SEEN_KEYS`。
5. 端点 `https://www.tongliao.gov.cn/IGI`（**https**）；须带 `Referer: https://www.tongliao.gov.cn/`。
6. 行数组键 `datas.data`；行是大写键。
"""
from __future__ import annotations

from adapters._igi_common import existing_ids, harvest_igi

SITE = {
    "key": "tongliao-igi",
    "name": "通辽市·政民互动信箱（IGI）",
    "kind": "api",
    "level": "city",
    "entry": "https://www.tongliao.gov.cn/IGI/nbhd/openGovmsgbox.do",
    "status": "ok",
    "note": "IGI 39 个 siteId（空 appId，枚举上界 3,843 条）；与 nmg-igi 不同部署"
            "（36 个 siteId 独有 / 记录 id 重叠 0/20）；地域为门户默认值已剥离；须带 Referer；https 可达",
}

BASE = "https://www.tongliao.gov.cn/IGI"
REFERER = "https://www.tongliao.gov.cn/"
APP_ID = ""
GROUP_ID = None

#: 39 个 siteId（`recon/igi-siteid-tongliao.json`，2026-10-09 扫 1..150 空 appId），按 total 降序，上界合计 3,843。
SITE_IDS = (
    "15 12 13 9 36 34 11 14 20 45 10 17 "
    "47 21 16 30 8 32 41 44 27 31 46 37 "
    "40 22 33 42 43 28 29 24 23 38 48 35 "
    "39 49 56"
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
    """遍历通辽各 siteId 取已答复信件。长任务用 `recon/igi-chunked.py tongliao_igi --sites-json ...`。"""
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
