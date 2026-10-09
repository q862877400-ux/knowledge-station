"""适配器：**儋州市·政民互动信箱（IGI 平台，20 个 siteId）**——2026-10-09 第 11 轮新增。

## 怎么找到的
第 10 轮**地级市 IGI 横向普查**（`igi-portal-sweep-city2.json`，93 城）命中 14 个门户，
儋州是其中**海南唯一命中**（三亚 NO）。第 10 轮只登记未枚举；第 11 轮枚举 + 实测后接入。

## 关键事实（2026-10-09 第 11 轮实测）
1. **枚举**（`recon/igi-siteid-danzhou.json`，扫 1..150、空 appId）：
   **20 个 siteId / 27,694 条**（64→22,001、66→2,892、8→1,111、7→312、24→258…）。
   ⚠ 枚举 total 是**上界**（第 10 轮新坑 A）。
2. **可采**（`var/tmp/r11/probe-city.py` 只读实测 siteId=64 与 8）：
   列表 `HTTP 200`、首页 20 行 **`ISREPLY` 全 1**；明细 `HTTP 200`、`REPLYS=1`。
3. ★ **地域字段是「恒定默认值」⇒ 剥离**：siteId=64 与 8 各抽 20 行，非空地域组合**只有 1 种**
   —— `海南省 / 海口市 / 市辖区`（**一个儋州门户却报海口市** ⇒ 平台默认值）⇒ `postprocess` 一律清空。
4. **与 `hi-zcwd`（海南政策问答，2,240 条 id）首页 20 条记录 id 重叠 0/20** ⇒ 不是同一批信件。
   ⚠ 海南**无既有 IGI 线**，无同省 IGI 可比 ⇒ 只能证明「与政策问答不重叠」，不能证明「与其他源不重叠」。
5. 端点 `https://www.danzhou.gov.cn/IGI`（**https**）；须带 `Referer: https://www.danzhou.gov.cn/`。
6. 行数组键是 `datas.data`；行是大写键（`METADATAID/TITLE/ISREPLY/PROVINCE/CITY/AREA`）。

## 价值
海南全库此前仅 `hi-zcwd` 一条线 ⇒ 本条是**海南第一条 IGI 线**，枚举上界 27,694 条。
⚠ 答复偏短（siteId=64 首条仅 29 字）⇒ 下游按长度过滤即可，不影响落盘。
"""
from __future__ import annotations

from adapters._igi_common import existing_ids, harvest_igi

SITE = {
    "key": "danzhou-igi",
    "name": "儋州市·政民互动信箱（IGI）",
    "kind": "api",
    "level": "city",
    "entry": "https://www.danzhou.gov.cn/IGI/nbhd/openGovmsgbox.do",
    "status": "ok",
    "note": "IGI 20 个 siteId（空 appId，枚举上界 27,694 条）；海南首条 IGI 线；"
            "上游地域字段为门户默认值（海口市），已剥离；须带 Referer；https 可达",
}

BASE = "https://www.danzhou.gov.cn/IGI"
REFERER = "https://www.danzhou.gov.cn/"
APP_ID = ""                       # ★ 必须空：带 appId 会过滤掉大部分记录
GROUP_ID = None

#: 20 个 siteId（`recon/igi-siteid-danzhou.json`，2026-10-09 扫 1..150 空 appId），
#: 按 totalResults **降序**，枚举上界合计 **27,694** 条。降序 = 长任务先跑大块。
SITE_IDS = (
    "64 66 8 7 24 41 78 42 57 60 52 51 "
    "49 63 65 106 54 72 80 92"
).split()


def postprocess(rows: list[dict]) -> list[dict]:
    """剥离**恒定**地域（= 门户默认值）。

    判定口径与 `baotou_igi.postprocess` 相同：某批内**非空**地域组合只有 1 种 ⇒ 视为默认值、一律清空。
    儋州实测 siteId=64/8 各抽 20 行：非空组合只有 `海南省/海口市/市辖区` ⇒ 全剥离。
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
    """遍历儋州各 siteId 取已答复信件（`limit` 为跨 site 累计的**本轮新增**上限）。

    ⚠ 枚举上界 27,694 条 ⇒ 长任务请用分片增量驱动
    `recon/igi-chunked.py danzhou_igi --sites-json igi-siteid-danzhou.json --page-chunk 20`。
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
