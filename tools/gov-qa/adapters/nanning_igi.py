"""适配器：**南宁市·政民互动信箱（IGI 平台，siteId=8）**——2026-10-09 第 7 轮新增。

## 怎么找到的
第 5 轮的 `recon/igi-portal-sweep.py` 对 34 个城市门户各打一发列表请求，**南宁命中**；
第 6 轮 `recon/igi-siteid-scan.py nanning` 扫 siteId=1..300（空 appId）实测：
**只有 1 个 siteId（=8）/ 18,977 条**（`recon/igi-siteid-nanning.json`）。

## 为什么价值高
广西在本模块此前的**全部**存量只有 **1,869 条**（`gx-igi` 1,731 + `gx-mailbox` 138）
⇒ 本适配器一次性把该省语料放大 **≈10 倍**；且南宁市此前**零覆盖**。

## 关键事实（2026-10-09 实测，探针 `recon/igi-city-probe.py nanning`）
1. **可采**：列表接口 `HTTP 200 total=18,977`，行是**大写键**
   （`METADATAID/TITLE/ISREPLY/PROVINCE/CITY/AREA`）；明细 `HTTP 200`、
   答复正文在 `datas.REPLYS[].REPLYHTMLCONTENT`（实测 id=127667 → 370 字）。
2. ★ **地域字段是真的**：抽 120 条（页 1..6）得 **12 种** `PROVINCE/CITY/AREA` 组合，
   全部落在南宁市下辖（良庆区 29 / 市辖区 18 / 江南区 16 / 上林县 12 / 武鸣区 10 /
   马山县 8 / 邕宁区 7 / 隆安县 6 / 西乡塘区 6 / 青秀区 4 / 横州市 3 / 兴宁区 1）
   ⇒ **不剥离地域**（与山西/内蒙古相反，与广西/宁夏/湖北同类）。
3. **与既有广西线不重叠**：抽 100 条南宁 id（区间 123,209–127,667）与
   `gx-igi` + `gx-mailbox` 的 1,869 个 id 比对 ⇒ **重叠 0**。
   ⇒ **不声明 `EXTRA_SEEN_KEYS`**（那两个源在另一台部署上，id 空间不同）。
   ⚠ 这只是 100 条抽样，不是全量；下游若发现重复按 `(source,id)` 去重即可。
4. 端点 `https://www.nanning.gov.cn/IGI`（**https 可达**）；须带
   `Referer: https://www.nanning.gov.cn/`。
"""
from __future__ import annotations

from adapters._igi_common import existing_ids, harvest_igi

SITE = {
    "key": "nanning-igi",
    "name": "南宁市·政民互动信箱（IGI）",
    "kind": "api",
    "level": "city",
    "entry": "https://www.nanning.gov.cn/IGI/nbhd/openGovmsgbox.do",
    "status": "ok",
    "note": "IGI siteId=8（空 appId 取全量，约 1.9 万条）；**带真实市/区县两级归属**；须带 Referer；https 可达",
}

BASE = "https://www.nanning.gov.cn/IGI"
REFERER = "https://www.nanning.gov.cn/"
APP_ID = ""                       # ★ 必须空：带 appId 会过滤掉大部分记录
GROUP_ID = None

#: 1 个 siteId（`recon/igi-siteid-nanning.json`，2026-10-09 扫 1..300 空 appId），
#: 合计 **18,977** 条（枚举上界；实际可采量 = 已答复部分，逐站答复率见 SITE-REGISTRY）。
SITE_IDS = ("8",)


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """取南宁市已答复信件（`limit` 为本轮新增上限）。

    ⚠ 全量约 1.9 万条（枚举值）⇒ 用 `harvest.py` 一次跑完不现实；
    长任务请用分片增量驱动 `recon/igi-chunked.py nanning_igi`（逐页窗口落盘）。
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
        out.extend(rows)
    return out
