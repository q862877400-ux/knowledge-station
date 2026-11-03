"""适配器：**张掖市·政民互动信箱（IGI 平台，8 个 siteId）**——2026-10-09 第 10 轮新增。

## 怎么找到的（★★ 甘肃此前是"整域 412"的死省）
1. 第 10 轮做**地级市 IGI 横向普查**（`var/tmp/r18/city-igi-sweep2.py`，93 城，只读），
   张掖命中 `verdict=IGI`（响应体是 IGI 的 `datas`+`pageInfo` 信封）。
   ⇒ **`www.zhangye.gov.cn` 的 `/IGI/` 路径没被 WAF 拦**，尽管甘肃**省**门户整域 412。
2. `recon/igi-siteid-scan.py zhangye`（扫 siteId=1..300，**空 appId**）实测
   **8 个 siteId / 7,777 条**（`recon/igi-siteid-zhangye.json`）：
   23→5,318、15→1,320、61→500、77→312、67→193、20→69、19→59、9→6。

## 关键事实（2026-10-09 第 10 轮实测）
1. **可采**：列表 `HTTP 200 totalResults=5,318 totalPages=266`（siteId=23）；
   行是大写键（`METADATAID/TITLE/ISREPLY/PROVINCE/CITY/AREA`）；
   明细 `HTTP 200`、`REPLYS=1`、答复正文 **252 字**（`datas.REPLYS[].REPLYHTMLCONTENT`）。
2. ★ **地域是真实的三级链（省/市/区县）**：siteId=23 首页 20 行
   `PROVINCE=甘肃省 / CITY=张掖市 / AREA=甘州区`，**非空 20/20**。
   ⇒ **保留、不剥离**（与山西/内蒙古/包头/沈阳/南京的"恒定默认值"不同）。
   ⚠ 按第 8 轮教训：**抽 20 行只够判"真/假"，非空率必须上量复核**（西宁当初 5 行判"真"、
     400 行实测只有 7%）。落盘后请用 `recon/audit-igi-prov.py` 复核非空率。
3. 端点 `https://www.zhangye.gov.cn/IGI`（**https**）；须带 `Referer: https://www.zhangye.gov.cn/`。
4. **行数组键是 `datas.data`**（不是 `list`）。
5. ⚠ **枚举 total 是乐观值**（第 10 轮新坑 A）：贵州 `gz-igi-70` 枚举 16,421 而实测列表 227 页
   就 404（真实 ≈4,035）⇒ 本适配器的 7,777 也只是**上界**。

## 为什么价值高
甘肃全库此前 **9,677 条**（`gs-*`，且整域被 412 挡）⇒ 这是**甘肃第一条 IGI 线**，
且是唯一能给甘肃**区县级**归属的通道。
"""
from __future__ import annotations

from adapters._igi_common import existing_ids, harvest_igi

SITE = {
    "key": "zhangye-igi",
    "name": "张掖市·政民互动信箱（IGI）",
    "kind": "api",
    "level": "city",
    "entry": "https://www.zhangye.gov.cn/IGI/nbhd/openGovmsgbox.do",
    "status": "ok",
    "note": "IGI 8 个 siteId（空 appId，枚举合计 7,777 条）；**带真实省/市/区县三级归属**；"
            "须带 Referer；https 可达；甘肃首条 IGI 线（该省省门户整域 412）",
}

BASE = "https://www.zhangye.gov.cn/IGI"
REFERER = "https://www.zhangye.gov.cn/"
APP_ID = ""                       # ★ 必须空：带 appId 会过滤掉大部分记录
GROUP_ID = None

#: 8 个 siteId（`recon/igi-siteid-zhangye.json`，2026-10-09 扫 1..300 空 appId），
#: 按 totalResults **降序**，枚举合计 **7,777** 条（上界；实际可采 = 已答复部分）。
SITE_IDS = ("23 15 61 77 67 20 19 9").split()


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """取张掖市已答复信件（`limit` 为本轮新增上限）。

    ⚠ 全量约 7,777 条（枚举上界）⇒ 用 `harvest.py` 一次跑完不现实；
    长任务请用分片增量驱动 `recon/igi-chunked.py zhangye_igi`（逐页窗口落盘）。
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
