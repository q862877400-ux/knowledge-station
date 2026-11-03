"""适配器：**九江市·政民互动信箱（IGI 平台，siteId=72）**——2026-10-09 第 10 轮新增。

## 怎么找到的
1. 第 10 轮**地级市 IGI 横向普查**（`var/tmp/r18/city-igi-sweep2.py`，93 城）命中九江
   （`verdict=IGI`）。江西**省**门户 `www.jiangxi.gov.cn` 第 5 轮普查是 `NO`（200 但非 IGI 体），
   ⇒ 又一次印证「**省门户 NO ≠ 省内市门户没有**」（同南京/沈阳/包头）。
2. `recon/igi-siteid-scan.py jiujiang`（扫 siteId=1..300，**空 appId**）实测
   **只有 1 个 siteId**：`siteId=72 → 1,509 条`（`recon/igi-siteid-jiujiang.json`）。

## 关键事实（2026-10-09 第 10 轮实测）
1. **可采**：列表 `HTTP 200 totalResults=1,509 totalPages=76`；
   明细 `HTTP 200`、`REPLYS=1`、答复正文 **173 字**（`datas.REPLYS[].REPLYHTMLCONTENT`）。
2. ★ **地域是真实的三级链**：首页 20 行 `PROVINCE=江西省 / CITY=九江市 / AREA=经开区`，
   **非空 20/20** ⇒ **保留、不剥离**。
   ⚠ 按第 8 轮教训：抽 20 行只够判"真/假"，**非空率必须上量复核**（西宁当初 5 行判"真"、400 行实测 7%）。
3. 端点 `https://www.jiujiang.gov.cn/IGI`（**https**）；须带 `Referer: https://www.jiujiang.gov.cn/`。
4. **行数组键是 `datas.data`**（不是 `list`）。
5. ⚠ 枚举 total 是**乐观值**（第 10 轮新坑 A，见 §二十 3）。

## 为什么价值高
江西全库此前 **461 条**（`jx-*`，且第 3 轮扫过 35 个省直部门站只找到省国资委一个真问答）
⇒ 本适配器一条线就是该省存量的 **≈3 倍**，且是江西**唯一**能拿**区县级**归属的通道。
"""
from __future__ import annotations

from adapters._igi_common import existing_ids, harvest_igi

SITE = {
    "key": "jiujiang-igi",
    "name": "九江市·政民互动信箱（IGI）",
    "kind": "api",
    "level": "city",
    "entry": "https://www.jiujiang.gov.cn/IGI/nbhd/openGovmsgbox.do",
    "status": "ok",
    "note": "IGI siteId=72（空 appId，枚举 1,509 条）；**带真实省/市/区县三级归属**；"
            "须带 Referer；https 可达；江西首条 IGI 线（该省此前仅 461 条）",
}

BASE = "https://www.jiujiang.gov.cn/IGI"
REFERER = "https://www.jiujiang.gov.cn/"
APP_ID = ""                       # ★ 必须空：带 appId 会过滤掉大部分记录
GROUP_ID = None

#: 1 个 siteId（`recon/igi-siteid-jiujiang.json`，2026-10-09 扫 1..300 空 appId），
#: 枚举 **1,509** 条（上界；实际可采 = 已答复部分）。
SITE_IDS = ("72",)


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """取九江市已答复信件（`limit` 为本轮新增上限）。

    全量约 1,509 条（枚举上界）；长任务请用分片增量驱动
    `recon/igi-chunked.py jiujiang_igi`（逐页窗口落盘）。
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
