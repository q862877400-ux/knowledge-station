"""适配器：**西宁市·政民互动信箱（IGI 平台，siteId=43/4）**——2026-10-09 第 8 轮新增。

## 怎么找到的
第 5 轮 `recon/igi-portal-sweep.py city`（省会 + 计划单列市门户各打一发列表请求）命中西宁
（verdict=IGI）；第 8 轮 `recon/igi-siteid-scan.py xining` 扫 siteId=1..300（**空 appId**）实测：
**2 个 siteId / 5,826 条**（`recon/igi-siteid-xining.json`；43→5,264、4→562）。

## 为什么价值最高（本轮首选）
青海省在本模块此前的**全部**存量只有 **353 条**（`qh-*`）⇒ 本适配器把该省语料放大 **≈16 倍**，
且是**唯一**能给青海**区县级**归属的通道。
> 注：青海**省**门户 `www.qinghai.gov.cn` 本机不可达（第 5 轮普查 `BLOCK / ConnectTimeout`），
> 但**西宁市**门户的 IGI 端点正常 ⇒ 弱省的解法是「绕过省门户、打市级门户」。

## 关键事实（2026-10-09 第 8 轮实测）
1. **可采**：列表 `HTTP 200 total=5,264`（siteId=43），行是大写键
   （`METADATAID/TITLE/ISREPLY/PROVINCE/CITY/AREA`）；
   明细 `HTTP 200`、`REPLYS=1`、答复正文 **4,146 字**（`datas.REPLYS[].REPLYHTMLCONTENT`）。
2. ★ **地域是真的且多变（含区县级）⇒ 保留、不剥离**：抽 siteId=43 列表首 5 行得
   `PROVINCE=青海省` 恒定、但 `AREA` **不止一种**（`大通回族土族自治县` / `市辖区` …）
   ⇒ 与广西 / 宁夏 / 湖北 / 南宁同类（真实地域），与山西 / 内蒙古 / 包头 / 沈阳 / 南京相反。
   ⚠ 这是**5 行抽样**，不是全量；`AREA` 的多样性由后续窗口继续观察。
3. 端点 `https://www.xining.gov.cn/IGI`（**https 可达**）；须带
   `Referer: https://www.xining.gov.cn/`。
4. **行数组键是 `datas.data`**（不是 `list`）—— 与南宁/包头不同，探针/抽样脚本必须带回退。
"""
from __future__ import annotations

from adapters._igi_common import existing_ids, harvest_igi

SITE = {
    "key": "xining-igi",
    "name": "西宁市·政民互动信箱（IGI）",
    "kind": "api",
    "level": "city",
    "entry": "https://www.xining.gov.cn/IGI/nbhd/openGovmsgbox.do",
    "status": "ok",
    "note": "IGI siteId=43/4（空 appId 取全量，约 5,826 条）；**带真实省/市/区县归属**；"
            "须带 Referer；https 可达；青海此前仅 353 条 ⇒ 约 16 倍",
}

BASE = "https://www.xining.gov.cn/IGI"
REFERER = "https://www.xining.gov.cn/"
APP_ID = ""                       # ★ 必须空：带 appId 会过滤掉大部分记录
GROUP_ID = None

#: 2 个 siteId（`recon/igi-siteid-xining.json`，2026-10-09 扫 1..300 空 appId），
#: 按 totalResults **降序**，合计 **5,826** 条（枚举上界；实际可采 = 已答复部分）。
SITE_IDS = ("43 4").split()


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """取西宁市已答复信件（`limit` 为本轮新增上限）。

    ⚠ 全量约 5,826 条（枚举值）⇒ 用 `harvest.py` 一次跑完不现实；
    长任务请用分片增量驱动 `recon/igi-chunked.py xining_igi`（逐页窗口落盘）。
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
