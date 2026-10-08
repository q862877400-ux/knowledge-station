"""适配器：**湖北省人民政府·政民互动（IGI 平台，多 site）**。

## 站点事实（2026-10-08 实测，证据 recon/gs-hb-hunt.txt 【湖北】）
 · 湖北省门户 `www.hubei.gov.cn` 根路径被**瑞数动态防护**拦（412），
   **但 IGI 接口路径被 WAF 放行**：
     GET https://www.hubei.gov.cn/IGI/nbhd/openGovmsgbox.do
         ?method=listGovmsgboxs&siteId=<N>&pageIndex=1&pageSize=20   -> 200 JSON
 · 与 `_igi_common.py` **完全同构**（零改造复用基座），参数名 siteId/pageIndex/pageSize
   一致；appId 留空即可；**不需要 Referer**（实测无 Referer 也 200）。
 · 空 siteId 且空 regions 时报 `{"statusCode":301,"message":"siteId与regions不能同时为空"}`。
 · 枚举 siteId=1..160 命中若干 site（见 recon/gs-hb-igi-sites.txt），明细
   `method=viewGovmsgbox&siteId=<N>&metadataId=<id>` 的
   `datas.REPLYS[].REPLYHTMLCONTENT` = 官方答复原文，`REPLYDEPTEXTNAME` = 答复部门。
 · ★ 列表带 PROVINCE/CITY/AREA 三级归属（如「湖北省/武汉市/市辖区」）。
"""
from __future__ import annotations

from adapters._igi_common import harvest_igi

SITE = {
    "key": "hb-hdjl",
    "name": "湖北省人民政府·政民互动",
    "kind": "api",
    "level": "province",
    "entry": "https://www.hubei.gov.cn/hdjl/",
    "status": "ok",
    "note": "IGI 平台（www.hubei.gov.cn/IGI），多 siteId；带省/市/区三级归属；无需 Referer",
}

BASE = "https://www.hubei.gov.cn/IGI"
REFERER = "https://www.hubei.gov.cn/"
APP_ID = ""
GROUP_ID = None

# 枚举实测命中的 siteId（1..160，2026-10-08）；条数为枚举当日 totalResults。
# 数字会随时间增长，采集时以接口返回为准。
# ⚠ 已剔除第三方厂商的测试实例（4/28/50/112，dept=拓思达/佳软，内容是「测试」）。
SITE_IDS = [
    "10",   # 造价站
    "16",   # 湖北省建设信息中心
    "19",   # 湖北省统计局
    "25",   # 湖北省疾病预防控制中心
    "26",   # 行政审批处
    "48",   # 湖北省生态环境厅
    "57",   # 湖北省水利厅
    "58",   # 办公室
    "63",   # 神农架文旅局
    "71",   # 潜江市园林街道办事处
    "88",   # 省交易采购中心
]


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """遍历湖北省门户 IGI 各 siteId，取已答复信件（含答复原文与三级归属）。

    `limit` 为**总条数**上限（跨 site 累计）。`fetch` 见 harvest.py 的 _Fetcher 协议。
    """
    out: list[dict] = []
    for sid in SITE_IDS:
        if limit and len(out) >= limit:
            break
        sub_site = dict(SITE)
        # 每个 siteId 用独立 source 后缀便于区分归属与去重，仍统一前缀 hb-hdjl。
        sub_site["key"] = f"{SITE['key']}-{sid}"
        rows = harvest_igi(fetch, SITE=sub_site, base=BASE, site_id=sid, app_id=APP_ID,
                           group_id=GROUP_ID, referer=REFERER,
                           limit=(limit - len(out)) if limit else None, max_pages=200)
        out.extend(rows)
    return out
