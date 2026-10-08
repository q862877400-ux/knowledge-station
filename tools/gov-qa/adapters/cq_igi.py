"""适配器：**重庆市人民政府·政民互动（IGI 平台，多 site）**。

## ★★★ 翻案记录（2026-10-08）

`recon/waf-igi-sites.json` 曾把重庆记为 `sites: {}`（**枚举结果为空**），据此判「无问答」。
**这是错的，错因是枚举范围太窄**：那次只枚举了 `siteId 1..60`，
而**重庆的 siteId 全在 150~300+ 区间**。扩大范围后大爆发。

⇒ 通用教训：**枚举 siteId 时范围必须给够（至少 1..300），
   不能因为 1..60 是空就判定该站没有 IGI 数据。**（同族站点里，siteId 段位因站而异。）

## 站点事实（实测）

- BASE `http://www.cq.gov.cn/IGI`（**必须 http**）
- Referer `http://www.cq.gov.cn/hdjl/`
- 与 `adapters/_igi_common.py` **完全同构**（`datas.data[].METADATAID/TITLE/CONTENT/
  ISREPLY/DEALDEPTNAME/REPLYS`，与湖北/武汉/张掖同族）⇒ 零改造复用基座
- 列表 20 行/页；字段含 `DEALDEPTNAME`（答复部门）、`AREA`（全市/区县）
- 明细 `method=viewGovmsgbox&siteId=<N>&metadataId=<id>` 的
  `datas.REPLYS[].REPLYHTMLCONTENT` = 答复原文

## 规模

枚举 `siteId 1..300` 命中 **75 个 site / 约 32,580 条**（`recon/cq-igi-hunt.txt`）。
这是继广东之后**第二大来源**，远超原静态线 `cq-hdjl`（约 840 条）。
（枚举 301..400 仍在后台跑，可能有更多 siteId。）

⚠ **与 `cq-hdjl`（静态线）可能重叠** —— 两者都取重庆政民互动的留言选登。
若发现 id 大面积重复，应以本适配器为准并停用 `cq-hdjl`。
"""
from __future__ import annotations

from adapters._igi_common import harvest_igi

SITE = {
    "key": "cq-igi",
    "name": "重庆市人民政府·政民互动（IGI）",
    "kind": "api",
    "level": "province",
    "entry": "http://www.cq.gov.cn/hdjl/",
    "status": "ok",
    "note": "IGI 平台（www.cq.gov.cn/IGI），75 site / 约 3.26 万条；"
            "siteId 在 150~300+ 区间（1..60 为空，勿据此判死）；BASE 用 http",
}

BASE = "http://www.cq.gov.cn/IGI"
REFERER = "http://www.cq.gov.cn/hdjl/"
APP_ID = ""
GROUP_ID = None

#: 枚举实测命中的 siteId（1..300，2026-10-08）；条数为枚举当日 totalResults。
#: 数字会随时间增长，采集时以接口返回为准；无效 siteId 由基座的 404/非 200 容错跳过。
#: 区间 1..200 命中 28 个：
SITE_IDS = [
    "156",  # 149
    "157",  # 95
    "159",  # 862
    "161",  # 91
    "162",  # 29
    "164",  # 61
    "165",  # 501
    "166",  # 374
    "167",  # 342
    "168",  # 35
    "170",  # 80
    "171",  # 1158
    "173",  # 159
    "174",  # 716
    "175",  # 161
    "176",  # 99
    "178",  # 35
    "180",  # 1755
    "182",  # 203
    "184",  # 830
    "186",  # 51
    "188",  # 17
    "190",  # 129
    "191",  # 68
    "194",  # 90
    "197",  # 24
    "199",  # 171
    "200",  # 142
    # 区间 201..300 命中 47 个：
    "202",  # 78
    "204",  # 1711
    "206",  # 1262
    "207",  # 104
    "208",  # 54
    "209",  # 225
    "210",  # 53
    "213",  # 91
    "217",  # 51
    "218",  # 56
    "221",  # 53
    "224",  # 317
    "225",  # 97
    "229",  # 2485
    "230",  # 196
    "231",  # 31
    "232",  # 55
    "233",  # 1577
    "235",  # 127
    "236",  # 27
    "237",  # 85
    "238",  # 1090
    "239",  # 1778
    "240",  # 103
    "241",  # 98
    "242",  # 326
    "243",  # 118
    "244",  # 23
    "245",  # 129
    "246",  # 69
    "247",  # 83
    "249",  # 389
    "250",  # 185
    "251",  # 3063
    "252",  # 206
    "253",  # 98
    "254",  # 2641
    "257",  # 196
    "258",  # 74
    "260",  # 130
    "263",  # 51
    "264",  # 97
    "266",  # 2642
    "268",  # 808
    "269",  # 35
    "270",  # 26
    "271",  # 960
]


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """遍历重庆市门户 IGI 各 siteId，取已答复信件（含答复原文与归属）。

    `limit` 为**总条数**上限（跨 site 累计）。`fetch` 见 harvest.py 的 _Fetcher 协议。
    """
    out: list[dict] = []
    for sid in SITE_IDS:
        if limit and len(out) >= limit:
            break
        sub_site = dict(SITE)
        # 每个 siteId 用独立 source 后缀便于区分归属与去重，仍统一前缀 cq-igi。
        sub_site["key"] = f"{SITE['key']}-{sid}"
        rows = harvest_igi(fetch, SITE=sub_site, base=BASE, site_id=sid, app_id=APP_ID,
                           group_id=GROUP_ID, referer=REFERER,
                           limit=(limit - len(out)) if limit else None, max_pages=300)
        out.extend(rows)
    return out
