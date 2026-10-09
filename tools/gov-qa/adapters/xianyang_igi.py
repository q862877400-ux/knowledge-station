"""适配器：**咸阳市·政民互动信箱（IGI 平台，17 个 siteId）**——2026-10-09 第 11 轮新增。

## 怎么找到的
第 10 轮**地级市 IGI 横向普查**（`igi-portal-sweep-city2.json`，93 城）命中 14 个门户，咸阳其一
（陕西两个命中：咸阳 + 宝鸡）。第 11 轮枚举 + 实测后接入。

## 关键事实（2026-10-09 第 11 轮实测）
1. **枚举**（`recon/igi-siteid-xianyang.json`，扫 1..150、空 appId）：
   **17 个 siteId / 52,859 条**（127→21,321、93→11,136、91→4,501、96→2,951、95→2,195…）。
   ⚠ 枚举 total 是**上界**（第 10 轮新坑 A：贵州 gz-70 枚举 16,421 实测只有 4,035）。**本站头号大站**。
2. **可采**（`var/tmp/r11/probe-city.py` 只读实测 siteId=127）：
   列表 `HTTP 200 totalResults=21,321`、首页 20 行 **`ISREPLY` 全 1**；
   明细 `HTTP 200`、`REPLYS=1`、答复正文 **1,184 字**。
3. ★ **地域字段全空**（siteId=127 抽 20 行 `PROVINCE/CITY/AREA` 均空）⇒ 保留 `postprocess` 兜底（无可剥离）。
4. ★ **与 `sn-igi`（陕西·我向省长说句话）不是同一批数据**：
   抽 siteId=127 的 20 条 id 与 `sn-*` 的 4,268 个 id 比对 ⇒ **重叠 0/20**。⇒ 不声明 `EXTRA_SEEN_KEYS`。
   （`sn-igi` 基座 `www.shaanxi.gov.cn/IGI` 单站；咸阳 `www.xianyang.gov.cn/IGI` 独立部署。）
5. 端点 `https://www.xianyang.gov.cn/IGI`（**https**）；须带 `Referer: https://www.xianyang.gov.cn/`。
6. 行数组键 `datas.data`；行是大写键。

## 价值
陕西已有 `sn-igi`（省门户，4,084 条）⇒ 本条枚举上界 **52,859 条**，是本轮**第二大站**（仅次于儋州 27,694 的
上界虽小，但咸阳首站 21,321 单站即超过儋州全站）。
"""
from __future__ import annotations

from adapters._igi_common import existing_ids, harvest_igi

SITE = {
    "key": "xianyang-igi",
    "name": "咸阳市·政民互动信箱（IGI）",
    "kind": "api",
    "level": "city",
    "entry": "https://www.xianyang.gov.cn/IGI/nbhd/openGovmsgbox.do",
    "status": "ok",
    "note": "IGI 17 个 siteId（空 appId，枚举上界 52,859 条）；与 sn-igi 不同部署（记录 id 重叠 0/20）；"
            "须带 Referer；https 可达；本轮最大站",
}

BASE = "https://www.xianyang.gov.cn/IGI"
REFERER = "https://www.xianyang.gov.cn/"
APP_ID = ""
GROUP_ID = None

#: 17 个 siteId（`recon/igi-siteid-xianyang.json`，2026-10-09 扫 1..150 空 appId），按 total 降序，上界合计 52,859。
SITE_IDS = (
    "127 93 91 96 95 4 36 89 6 97 94 90 "
    "101 99 100 98 18"
).split()


def postprocess(rows: list[dict]) -> list[dict]:
    """剥离**恒定**地域（= 门户默认值）。判定口径同 `baotou_igi.postprocess`。

    咸阳实测 siteId=127 抽 20 行地域**全空** ⇒ 本函数当前不生效（兜底）。
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
    """遍历咸阳各 siteId 取已答复信件。长任务用 `recon/igi-chunked.py xianyang_igi --sites-json ...`。"""
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
