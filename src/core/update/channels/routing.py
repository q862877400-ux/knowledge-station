"""渠道适配器索引：新增渠道在此注册，inspector 按标准号特征路由。

渠道分层（2026-08 四队实测，见 docs/LAW_SOURCE_PLAN.md 附 B）：
- mem_gov：AQ 行业标准状态（应急部公告）+ 全文（标准文本 PDF）
- std_samr_hb：行业标准目录状态（std.samr /hb/search/hbPage JSON）
- hbba：行业标准平台（POST /stdQueryList）
- dbba：地方标准平台（POST /stdQueryList）
- ndls：国家数字标准馆（跨门类状态+废止日期+代替链）
- mohurd：工程建设标准（住建部公告）
- ttzb：团体标准（ttbz 详情 JSON-LD）
- mee：生态环境 HJ（状态弱信号 + 全文下载链接逆向）
"""
from __future__ import annotations

import re

# 标准号 → 首选权威渠道（其余走 CHAIN 兜底 official_gb→web→govcn）
# 状态权威优先 ndls（跨门类，能判 现行/废止/废止日期/代替关系；AQ 3028→作废 2024-07-01 已验证）；
# mem_gov/mohurd 作为 公告+全文 辅助（页面 CMS/JS 结构，图文状态不全，不占状态首选）。
_PREFIX_ROUTE: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^(?:AQ/T?\b|AQ)"), "ndls"),                     # 应急管理行业标准→ndls（状态权威）
    (re.compile(r"^T/\b"), "ttbz"),                               # 团体标准→ttbz（专门渠道）
    (re.compile(r"^GB\s?(?:50|55)\d{3}\b"), "ndls"),              # 工程建设标准→ndls（状态权威）
    (re.compile(r"^GB\s?\d{4,5}\b"), "ndls"),                     # 其他国标→ndls（跨门类状态）
    (re.compile(r"^HJ\b", re.I), "mee"),                          # 生态环境标准→mee（含全文逆向）
    (re.compile(r"^DB\d"), "dbba"),                               # 地方标准→dbba
    (re.compile(r"^(?:MT|YB|JB|HG|QB|NY|SL|SN|JB|SH|JGT?|CJJ|CJ)\b", re.I), "hbba"),  # 行业标准→hbba
]

# 兜底：无特征命中时按此顺序（泛查链）
_FALLBACK = ("official_gb", "web", "govcn")


def select_chain(standard_no: str) -> tuple[str, ...]:
    """按标准号特征返回降级链（首选权威渠道在前，其余兜底在后）。"""
    no = (standard_no or "").strip()
    first = None
    for pat, ch in _PREFIX_ROUTE:
        if pat.match(no):
            first = ch
            break
    if first is None:
        return _FALLBACK
    chain = [first]
    for c in _FALLBACK:
        if c != first:
            chain.append(c)
    return tuple(chain)
