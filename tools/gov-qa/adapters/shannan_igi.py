"""适配器：**山南市·政民互动信箱（IGI 平台，7 个 siteId）**——2026-10-09 第 11 轮新增。

## 怎么找到的
第 10 轮**地级市 IGI 横向普查**（`igi-portal-sweep-city2.json`，93 城）命中 14 个门户，
山南是其中**西藏唯一命中**（拉萨 / 日喀则 / 林芝 / 昌都**全部 NO**）。
第 10 轮只枚举未接（"量小排后"）；第 11 轮实测可采后接入。

## 关键事实（2026-10-09 第 11 轮实测）
1. **枚举**（`recon/igi-siteid-shannan.json`，扫 1..300、空 appId）：**7 个 siteId / 191 条**
   （4→163、34→20、42→4、31/37/39/46 各 1）。
2. **可采**（`var/tmp/r11/probe-shannan.py` 只读实测）：
   列表 `HTTP 200 totalResults=163`，首页 20 行 **`ISREPLY` 全 1（答复率 100%）**；
   明细 `HTTP 200`、`REPLYS=1`、答复正文 **2,682 字**（`datas.REPLYS[].REPLYHTMLCONTENT`）。
3. ★ **地域是真实的三级链**：首页 20 行 `PROVINCE=西藏自治区 / CITY=山南市 / AREA=错那县·乃东区·加查县…`
   **非空 20/20** ⇒ **保留、不剥离**。
   ⚠ 按第 8 轮教训：**抽 20 行只够判"真/假"，非空率必须上量复核**（西宁当初 5 行判"真"、400 行实测仅 7%）。
4. **与 `xz-igi`（西藏既有线，350 条）首页 20 条 id 重叠 0/20** ⇒ 不是同一批信件，**可并存**。
5. 端点 `https://www.shannan.gov.cn/IGI`（**https**）；须带 `Referer: https://www.shannan.gov.cn/`。
6. 行数组键是 `datas.data`（与 zhangye 同）；行是大写键（`METADATAID/TITLE/ISREPLY/PROVINCE/CITY/AREA`）。

## 价值
西藏全库此前 **350 条**（`xz-igi`）⇒ 本条是**西藏第二条 IGI 线**，枚举上界 191 条 = **+55%**。
绝对量小（第 10 轮已判"量小排后"），但成本极低（7 站、约 10 页）。
"""
from __future__ import annotations

from adapters._igi_common import existing_ids, harvest_igi

SITE = {
    "key": "shannan-igi",
    "name": "山南市·政民互动信箱（IGI）",
    "kind": "api",
    "level": "city",
    "entry": "https://www.shannan.gov.cn/IGI/nbhd/openGovmsgbox.do",
    "status": "ok",
    "note": "IGI 7 个 siteId（空 appId，枚举合计 191 条）；**带真实省/市/区县三级归属**；"
            "须带 Referer；https 可达；西藏第二条 IGI 线（与 xz-igi id 重叠 0/20）",
}

BASE = "https://www.shannan.gov.cn/IGI"
REFERER = "https://www.shannan.gov.cn/"
APP_ID = ""                       # ★ 必须空：带 appId 会过滤掉大部分记录
GROUP_ID = None

#: 7 个 siteId（`recon/igi-siteid-shannan.json`，2026-10-09 扫 1..300 空 appId），
#: 按 totalResults **降序**，枚举合计 **191** 条（上界；实际可采 = 已答复部分）。
SITE_IDS = ("4 34 42 31 37 39 46").split()


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """取山南市已答复信件（`limit` 为本轮新增上限）。全量仅约 191 条 ⇒ 可一次跑完。"""
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
