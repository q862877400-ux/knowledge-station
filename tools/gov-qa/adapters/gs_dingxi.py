"""适配器：**定西市·政民互动（万户 hanweb jact 平台，多 sysid）**。

## 站点事实（2026-10-08 实测，worker-gansu）
 · 定西门户 `www.dingxi.gov.cn` 部署了与江苏同款的 jact 应用（路径 `/jact/front/`），
   **复用 `_jact_common.harvest_jact`**，两处差异：
   1. **scheme 是 http**（非 https）→ 传 `scheme="http"`；
   2. **明细页标签在 `<th>`、值在 `<td>`，且用词不同**（留言标题/留言内容/留言时间/
      办理状态/答复内容/受理部门/答复时间）→ 传 `include_th=True` + 扩展 `label_aliases`。
      （若沿用江苏口径只取 `<td>`，标签全丢 ⇒ 整站收 0 条。）
 · 同一 host 下有两个 sysid（两套信箱，实测互不重叠）：
   · sysid=`91` → totalRecord=215（「市长信箱」SJXX…）
   · sysid=`3`  → totalRecord=543（「市长信箱」SZXX…）
   合计 758。
 · 列表 POST `http://www.dingxi.gov.cn/jact/front/dataproxy_mailpublist.do`
   （body 同引擎）；详情 GET `…/jact/front/mailpubdetail.do?transactId=<id>&sysid=<n>`。
"""
from __future__ import annotations

from adapters._jact_common import LABEL_ALIASES, harvest_jact

#: 定西明细页用词 → 引擎规范键（在江苏别名基础上**追加**，不改江苏口径）。
DINGXI_ALIASES = {
    "留言标题": "标题",
    "留言内容": "内容",
    "留言时间": "提交时间",
    "办理状态": "处理状态",
    "受理部门": "答复单位",
    # 「答复内容」「答复时间」已在 LABEL_ALIASES 中，无需重复。
}

SITE = {
    "key": "gs-dingxi",
    "name": "定西市·政民互动（市长信箱）",
    "kind": "api",
    "level": "city",
    "entry": "http://www.dingxi.gov.cn/jact/front/mailpublist.do?sysid=3",
    "status": "ok",
    "note": "万户 jact 平台；host=www.dingxi.gov.cn（http）；标签在 th；两 sysid=91(215)/3(543)，合计 758",
}

HOST = "www.dingxi.gov.cn"
SCHEME = "http"
SYSIDS = ["91", "3"]


def harvest(fetch, *, limit: int | None = None) -> list[dict]:
    """遍历定西两个 sysid，取已答复留言（问题 + 答复全文）。

    `limit` 为**总条数**上限（跨 sysid 累计）。
    """
    out: list[dict] = []
    for sysid in SYSIDS:
        if limit and len(out) >= limit:
            break
        sub_site = dict(SITE)
        # 每个 sysid 用独立 source 后缀便于区分归属与去重，仍统一前缀 gs-dingxi。
        sub_site["key"] = f"{SITE['key']}-{sysid}"
        rows = harvest_jact(fetch, SITE=sub_site, host=HOST, sysid=sysid,
                            limit=(limit - len(out)) if limit else None,
                            scheme=SCHEME, include_th=True,
                            label_aliases={**LABEL_ALIASES, **DINGXI_ALIASES})
        out.extend(rows)
    return out
