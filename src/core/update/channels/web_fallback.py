"""网络逐号补漏搜索适配器（web，F-02 降级链第二棒 / F-12 兜底）。

official_gb 未命中/503/超时降级后使用；通用网页搜索语义，
从标题+摘要中解析版本号、状态关键词与施行日期。

mock 应答契约（离线表驱动）：
``{"http":200,"body":{"results":[{"title","url","snippet"}]}}``
命中规则：标题归一（去空白/斜杠/年代）后包含目标标准主体——新版结果标题
含新号亦视为命中，版本差异交给 derive_change_type 判 new_version。
"""
from __future__ import annotations

import re
from time import perf_counter

from src.core.update.channels.base import (
    LEGAL_STATUSES,
    ChannelAdapter,
    ChannelResult,
    derive_change_type,
    map_state_text,
    norm_no,
    query_no,
    strip_year,
)

#: 状态关键词 → 枚举（按出现顺序取第一个命中；废止优先级天然靠排序保证）
_STATUS_HINTS = (("废止", "withdrawn"), ("被代替", "superseded"),
                 ("即将实施", "upcoming"), ("现行", "effective"))

_STD_TOKEN_RE = re.compile(r"[A-Z]{1,4}(?:/[A-Z]{1,4})?\s*\d{4,5}\s*-\s*\d{4}")
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _clean_version(raw: str) -> str:
    """版本号排版归一：贴着 - / 的空白收敛、多空白合一（比较仍走 norm_no）。"""
    v = re.sub(r"\s*-\s*", "-", raw)
    v = re.sub(r"\s*/\s*", "/", v)
    return re.sub(r"\s+", " ", v).strip()


class WebFallbackAdapter(ChannelAdapter):
    """逐号补漏：标题含完整标准号即视为命中，证据链接随结果返回。"""

    name = "web"
    SEARCH_URL = "https://www.bing.com/search"

    def probe(self, standard_no: str, standard_name: str = "") -> ChannelResult:
        t0 = perf_counter()
        # ⚠ 查询值用 `query_no`（§11.0 R6c-2b 补，独立复核 b31 点名的第二处反例）：
        #   本渠道已从降级链摘除（R5c），影响≈0，但"送出去的请求里没有全角"这条口径要一致。
        query = f"{query_no(standard_no)} {standard_name}".strip()
        status, body = self._fetch(self.SEARCH_URL, params={"q": query})

        results: list = []
        if isinstance(body, dict):
            results = body.get("results") or []
        # 命中按去年代主体匹配：新版结果标题含的是新号（GB/T 3608-2025），非请求旧号
        core = strip_year(norm_no(standard_no))
        hit = next((r for r in results
                    if isinstance(r, dict) and core
                    and core in norm_no(str(r.get("title") or ""))), None)
        if hit is None:
            return self._miss(t0, standard_no, status, note=f"matches={len(results)}")

        text = f"{hit.get('title') or ''} {hit.get('snippet') or ''}"
        version_m = _STD_TOKEN_RE.search(str(hit.get("title") or ""))
        version = _clean_version(version_m.group(0)) if version_m else None

        legal_status: str | None = None
        for keyword, enum_value in _STATUS_HINTS:
            if keyword in text:
                legal_status = enum_value
                break
        # 中文关键词之外的原始状态字段（如 mock 提供英文枚举）直接校验采用
        if legal_status is None and hit.get("status"):
            raw_status = str(hit["status"]).strip()
            legal_status = raw_status if raw_status in LEGAL_STATUSES else map_state_text(raw_status)

        date_m = _DATE_RE.search(text)
        result = ChannelResult(
            channel=self.name,
            found=True,
            change_type=derive_change_type(standard_no, version, legal_status),
            legal_status=legal_status,
            latest_version=version,
            effective_date=date_m.group(0) if date_m else None,
            evidence_url=hit.get("url") or None,
            raw={"http": status, "result": hit},
        )
        return self._log_probe(t0, standard_no, result)
