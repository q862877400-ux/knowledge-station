"""适配器：**张掖市·政民互动（IGI 平台，多 siteId）**。

## 站点事实（2026-10-08 实测，worker-gansu）
 · 张掖门户 `www.zhangye.gov.cn` 的 IGI 接口与 `_igi_common.py` **完全同构**，
   **零改造复用基座**（参数名 siteId/pageIndex/pageSize 一致；appId 留空）：
     GET http://www.zhangye.gov.cn/IGI/nbhd/openGovmsgbox.do
         ?method=listGovmsgboxs&siteId=<N>&order=1&appId=&pageIndex=1&pageSize=20
     明细 GET …?method=viewGovmsgbox&siteId=<N>&metadataId=<id>
       → datas.REPLYS[].REPLYHTMLCONTENT = 官方答复原文。
 · ⚠ **必须 http**（https 不可用）；**须带 Referer** `http://www.zhangye.gov.cn/hdjl/`。
 · 列表 `datas.pageInfo.totalResults` 为总数；`datas.data[]` 为当页记录，
   `ISREPLY==1` 为已答复（基座已过滤）。
 · 实测 8 个 siteId 全部 200，totalResults 约 6 / 1320 / 59 / 69 / 5318 / 500 / 192 / 312
   （数字随时间增长，以接口返回为准）。
 · ★ 列表带 PROVINCE/CITY/AREA 三级归属。
"""
from __future__ import annotations

from adapters._igi_common import harvest_igi

SITE = {
    "key": "gs-zhangye",
    "name": "张掖市·政民互动（IGI）",
    "kind": "api",
    "level": "city",
    "entry": "http://www.zhangye.gov.cn/hdjl/",
    "status": "ok",
    "note": "IGI 平台（www.zhangye.gov.cn/IGI），多 siteId；须 http + Referer；带省/市/区三级归属",
}

BASE = "http://www.zhangye.gov.cn/IGI"
REFERER = "http://www.zhangye.gov.cn/hdjl/"
APP_ID = ""
GROUP_ID = None

# 实测命中的 siteId（2026-10-08）；数字为枚举当日 totalResults，采集时以接口为准。
SITE_IDS = ["9", "15", "19", "20", "23", "61", "67", "77"]


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """遍历张掖 IGI 各 siteId，取已答复信件（含答复原文与三级归属）。

    `limit` 为**总条数**上限（跨 site 累计）。`fetch` 见 harvest.py 的 _Fetcher 协议。
    """
    out: list[dict] = []
    for sid in SITE_IDS:
        if limit and len(out) >= limit:
            break
        sub_site = dict(SITE)
        # 每个 siteId 用独立 source 后缀便于区分归属与去重，仍统一前缀 gs-zhangye。
        sub_site["key"] = f"{SITE['key']}-{sid}"
        rows = harvest_igi(fetch, SITE=sub_site, base=BASE, site_id=sid, app_id=APP_ID,
                           group_id=GROUP_ID, referer=REFERER,
                           limit=(limit - len(out)) if limit else None, max_pages=300)
        for r in rows:                      # 基座默认口径按「厅长信箱」，本市站改为政民互动
            r["channel"] = "政民互动·信件公示"
            r["extra"]["answer_kind"] = "办理答复（市长信箱）"
        out.extend(rows)
    return out
