"""mem_gov适配器（2026-08 实测，巡检时效）。

应急管理部 AQ 行业标准（2026-08 实测，`Server: WAF` 头，浏览器 UA 可过，无验证码）：
- 标准公告：https://www.mem.gov.cn/fw/flfgbz/bz/bzgg/ ——标题标注「批准N项/废止N项/调整归口」，
  详情页正文含标准号级清单（如 废止3项行业标准：AQ/T 3016—2008、AQ/T 3017—2008、AQ/T 3044—2013）。
- 标准文本：https://www.mem.gov.cn/fw/flfgbz/bz/bzwb/index_N.shtml（分页）——标准号/名称/日期/PDF 直链。

probe 策略（确定性、预算受控）：遍历公告列表最近几页，逐条公告详情正文找目标标准号
（norm_no 归一匹配），命中后按公告标题语义判定：废止→withdrawn、批准/发布→effective。
找不到则诚实 _miss（note 注明「近期公告未覆盖该号」）；遍历超预算或 WAF 拦截归 _miss。
"""
from __future__ import annotations

import re
from time import perf_counter
from typing import Any
from urllib.parse import urljoin

from src.core.update.channels.base import (
    ChannelAdapter, ChannelResult, norm_no, upd_log,
)

LIST_URL = "https://www.mem.gov.cn/fw/flfgbz/bz/bzgg/"
#: 公告列表遍历页数上限（每页 ~10 条，避免无限）
_MAX_LIST_PAGES = 2
#: 单号详情抓取上限（预算受控）
_MAX_DETAILS = 8

# 公告标题语义 → 状态（正文命中标准号后据此判定）
_TITLE_EFFECTIVE = re.compile(r"(批准|发布|颁布)", re.I)
_TITLE_WITHDRAWN = re.compile(r"(废止|替代|作废)", re.I)


class MemGovAdapter(ChannelAdapter):
    """mem_gov：应急管理部 AQ 行业标准（标准号级状态探测，确定性、离线可测、异常归一）。"""

    name = "mem_gov"

    def probe(self, standard_no: str, standard_name: str = "") -> ChannelResult:
        t0 = perf_counter()
        target = norm_no(standard_no)
        if not target:
            return self._miss(t0, standard_no, 200, note="empty_standard_no")

        try:
            base_url, kind = self._search_announcement(target)
        except Exception:  # noqa: BLE001 — 网络/解析异常归一为 miss（WAF/超时等）
            return self._miss(t0, standard_no, 200, note="fetch_failed")

        if base_url is None:
            return self._miss(t0, standard_no, 200, note="not_found_in_recent_announcements")

        version = None
        legal_status = "withdrawn" if kind == "withdrawn" else "effective"
        change_type = "withdrawn" if kind == "withdrawn" else "no_change"
        upd_log(self.trace_id, f"channel.{self.name}", "INFO", "announcement_hit",
                standard_no=standard_no, kind=kind)
        result = ChannelResult(
            channel=self.name,
            found=True,
            change_type=change_type,
            legal_status=legal_status,
            latest_version=version,
            effective_date=None,
            evidence_url=base_url,
            raw={"http": 200, "kind": kind, "standard_no": standard_no},
        )
        return self._log_probe(t0, standard_no, result)

    def _search_announcement(self, target: str) -> tuple[str | None, str | None]:
        """在公告列表+详情里找目标标准号，返回 (公告URL, kind|None)。

        kind: 'withdrawn'（废止）/ 'effective'（批准/发布）。找不到返回 (None, None)。
        """
        list_html = self._fetch_text(LIST_URL)
        if list_html is None:
            return None, None
        ann_links: list[tuple[str, str]] = self._parse_list_links(list_html)
        fetched = 0
        for page in range(2, _MAX_LIST_PAGES + 1):
            # 分页：index_N.shtml（首页 = LIST_URL 自身）
            page_url = LIST_URL.rstrip("/") + f"/index_{page}.shtml"
            page_html = self._fetch_text(page_url)
            if page_html:
                ann_links.extend(self._parse_list_links(page_html))

        for href, title in ann_links:
            if fetched >= _MAX_DETAILS:
                break
            detail = self._fetch_text(urljoin(LIST_URL, href))
            fetched += 1
            if detail is None:
                continue
            if target not in norm_no(detail) and target not in re.sub(
                    r"\s+", "", re.sub(r"<[^>]+>", "", detail)):
                continue
            if _TITLE_WITHDRAWN.search(title):
                return urljoin(LIST_URL, href), "withdrawn"
            if _TITLE_EFFECTIVE.search(title):
                return urljoin(LIST_URL, href), "effective"
        return None, None


    @staticmethod
    def _parse_list_links(html: str) -> list[tuple[str, str]]:
        """解析公告列表页 -> [(href, 标题)], 仅保留含 废止/批准/发布/标准 的公告项。"""
        out: list[tuple[str, str]] = []
        for m in re.finditer(r'<a[^>]*href="([^"]+\.html)"[^>]*>(.*?)</a>', html, re.S):
            href, raw = m.group(1), re.sub(r"<[^>]+>", "", m.group(2)).strip()
            if not raw or len(raw) < 4:
                continue
            if not (("标准" in raw) or ("废止" in raw) or ("批准" in raw)
                    or ("发布" in raw) or ("公告" in raw)):
                continue
            out.append((href, raw))
        return out

