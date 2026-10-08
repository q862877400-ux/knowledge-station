"""适配器：**西藏自治区·人民政府门户 IGI 信箱（多 site）**——IGI 平台。

## ★ 为什么这条值得单独记（一次「翻案」）
2026-10-08 早前结论：西藏「留言选登」按钮指向 `xzxf.xizang.gov.cn/ocp/wsxx.html`，
**已改版为统一身份认证登录门户** ⇒ 判「未通」。

但同日全国 34 省 IGI 可达性矩阵（`recon/waf-igi-probe-stage1.json`）实测：
**西藏门户 `http://www.xizang.gov.cn/IGI/nbhd/openGovmsgbox.do` 返回 200**！
（siteId=1 无数据，但那只是没枚举到有数据的 siteId。）

⇒ **枚举 siteId=1..60 命中 8 个 site / 合计 355 条**（2026-10-08）：
```
22  →   1 条      24 → 143 条      30 →  19 条      32 → 46 条
37  →  74 条      39 →  40 条      45 →  10 条      56 → 22 条
```
明细 `datas.REPLYS[].REPLYHTMLCONTENT` = 官方答复原文；带省/市/区三级归属。

## 教训（写进结论）
**「门户无公开问答」≠「该省无公开问答」。** 门户 HTML 页面可以是登录墙，
但同域的 IGI JSON 接口可能完全开放。**遇 412/登录墙，务必单独试 `/IGI/` 路径并枚举 siteId。**
"""
from __future__ import annotations

from adapters._igi_common import existing_ids, harvest_igi

SITE = {
    "key": "xz-igi",
    "name": "西藏自治区·人民政府·政民互动（IGI）",
    "kind": "api",
    "level": "province",
    "entry": "http://www.xizang.gov.cn/IGI/nbhd/openGovmsgbox.do",
    "status": "ok",
    "note": "IGI 平台（www.xizang.gov.cn/IGI），多 siteId；带省/市/区三级归属；http 可达；"
            "★ 门户留言选登已改版为登录门户，但该 JSON 接口开放 ⇒ 「翻案」来源",
}

BASE = "http://www.xizang.gov.cn/IGI"
REFERER = "http://www.xizang.gov.cn/"
APP_ID = ""
GROUP_ID = None

#: 枚举实测命中的 siteId（1..60，2026-10-08）。条数会随时间增长，以接口返回为准。
SITE_IDS = [
    "22", "24", "30", "32", "37", "39", "45", "56",
]


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """遍历西藏门户 IGI 各 siteId，取已答复信件（含答复原文与三级归属）。

    `limit` 为**总条数**上限（跨 site 累计）。`fetch` 见 harvest.py 的 _Fetcher 协议。
    **可反复跑、逐轮推进**：每个 siteId 先读自己已落盘的 id 跳过（`limit` = 本轮新增条数）。
    """
    out: list[dict] = []
    # ⚠ 全部 siteId 共用**一个**产物文件（harvest.py 按顶层 SITE['key'] 命名），
    #   所以已有 id 取顶层 key 的集合，不能按 sub_site key 取（那样恒为空）。
    seen = existing_ids(SITE["key"])
    for sid in SITE_IDS:
        if limit and len(out) >= limit:
            break
        sub_site = dict(SITE)
        sub_site["key"] = f"{SITE['key']}-{sid}"
        rows = harvest_igi(fetch, SITE=sub_site, base=BASE, site_id=sid, app_id=APP_ID,
                           group_id=GROUP_ID, referer=REFERER,
                           limit=(limit - len(out)) if limit else None, max_pages=200,
                           skip_ids=seen)
        out.extend(rows)
    return out
