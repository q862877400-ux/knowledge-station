"""适配器：**武汉市人民政府·市长信箱/12345（IGI 平台，多 site）**。

## 站点事实（2026-10-08 实测，证据 recon/gs-hb-hunt.txt 【湖北】）
 · 武汉市门户 `www.wuhan.gov.cn` 与湖北同族：根路径被**瑞数动态防护**拦（412），
   **IGI 接口路径被 WAF 放行**：
     GET https://www.wuhan.gov.cn/IGI/nbhd/openGovmsgbox.do
         ?method=listGovmsgboxs&siteId=<N>&pageIndex=1&pageSize=20   -> 200 JSON
 · 与 `_igi_common.py` **完全同构**（零改造复用基座）；appId 留空；**无需 Referer**。
 · 枚举 siteId=1..160 命中 30+ 个 site，**合计 6000+ 条**（见 recon/gs-hb-igi-sites.txt）。
   最大：siteId=10 武汉住房公积金管理中心（3228 条，162 页）、siteId=43 区住更局（1391 条）。
 · 明细 `method=viewGovmsgbox&siteId=<N>&metadataId=<id>` 的
   `datas.REPLYS[].REPLYHTMLCONTENT` = 官方答复原文（常引条例文号），质量高。
 · ★ 列表带 PROVINCE/CITY/AREA 三级归属。
"""
from __future__ import annotations

from adapters._igi_common import harvest_igi

SITE = {
    "key": "hb-wuhan",
    "name": "武汉市人民政府·市长信箱/12345",
    "kind": "api",
    "level": "city",
    "entry": "https://www.wuhan.gov.cn/",
    "status": "ok",
    "note": "IGI 平台（www.wuhan.gov.cn/IGI），多 siteId；带省/市/区三级归属；无需 Referer",
}

BASE = "https://www.wuhan.gov.cn/IGI"
REFERER = "https://www.wuhan.gov.cn/"
APP_ID = ""
GROUP_ID = None

# 枚举实测命中（2026-10-08，siteId=1..160，共 30+ site）。条数随时间增长。
# ⚠ 已剔除第三方测试实例（89，dept=第三方测试）。
SITE_IDS = [
    "6", "7", "8", "9", "10", "12", "15", "17", "21", "23",
    "25", "26", "27", "28", "30", "31", "32", "33", "43", "45",
    "49", "50", "51", "52", "54", "56", "57", "58", "59", "65",
    "98",
]


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """遍历武汉市门户 IGI 各 siteId，取已答复信件（含答复原文与三级归属）。

    `limit` 为**总条数**上限（跨 site 累计）。
    """
    out: list[dict] = []
    for sid in SITE_IDS:
        if limit and len(out) >= limit:
            break
        sub_site = dict(SITE)
        sub_site["key"] = f"{SITE['key']}-{sid}"
        rows = harvest_igi(fetch, SITE=sub_site, base=BASE, site_id=sid, app_id=APP_ID,
                           group_id=GROUP_ID, referer=REFERER,
                           limit=(limit - len(out)) if limit else None, max_pages=200)
        out.extend(rows)
    return out
