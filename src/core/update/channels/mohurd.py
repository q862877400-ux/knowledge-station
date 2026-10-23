"""mohurd适配器（2026-08 实测，巡检时效）。

住建部工程建设标准（2026-08 实测，静态可抓，无验证码）：
- 公告详情（GB 55037-2022 示例）：https://www.mohurd.gov.cn/gongkai/zc/wjk/art/2024/art_17339_770016.html
  ——标题/发布时间/实施日期/废止条文清单，静态。（附件走 /api-gateway 网关，先不做全文）
- 文告列表：https://www.mohurd.gov.cn/gongkai/zc/wgk/ ——条目(标题/文号/链接/日期)。

probe 策略（预算受控）：遍历文告列表最近几页 + 公告详情，正文含目标标准号（norm_no 归一）
即判定：命中"废止"语义→withdrawn、"批准/发布/实施"→effective；找不到→_miss。
"""
from __future__ import annotations

import re
from time import perf_counter
from urllib.parse import urljoin

from src.core.update.channels.base import (
    ChannelAdapter, ChannelResult, norm_no, upd_log,
)

LIST_URL = "https://www.mohurd.gov.cn/gongkai/zc/wgk/"
_MAX_PAGES = 2
_MAX_DETAILS = 8

_TITLE_EFFECTIVE = re.compile(r"(批准|发布|颁布|印发)", re.I)
_TITLE_WITHDRAWN = re.compile(r"(废止|替代|作废)", re.I)


class MohurdAdapter(ChannelAdapter):
    """mohurd：住建部工程建设标准（标准号级状态探测，确定性、离线可测、异常归一）。"""

    name = "mohurd"

    def probe(self, standard_no: str, standard_name: str = "") -> ChannelResult:
        t0 = perf_counter()
        target = norm_no(standard_no)
        if not target:
            return self._miss(t0, standard_no, 200, note="empty_standard_no")
        try:
            base_url, kind = self._search_announcement(target)
        except Exception:  # noqa: BLE001 — 网络/解析异常归一为 miss
            return self._miss(t0, standard_no, 200, note="fetch_failed")
        if base_url is None:
            return self._miss(t0, standard_no, 200, note="not_found_in_recent_announcements")

        legal_status = "withdrawn" if kind == "withdrawn" else "effective"
        change_type = "withdrawn" if kind == "withdrawn" else "no_change"
        upd_log(self.trace_id, f"channel.{self.name}", "INFO", "announcement_hit",
                standard_no=standard_no, kind=kind)
        return self._log_probe(t0, standard_no, ChannelResult(
            channel=self.name, found=True, change_type=change_type,
            legal_status=legal_status, latest_version=None,
            effective_date=None, evidence_url=base_url,
            raw={"http": 200, "kind": kind, "standard_no": standard_no}))

    def _search_announcement(self, target: str) -> tuple[str | None, str | None]:
        pages = [LIST_URL]
        for page in range(2, _MAX_PAGES + 1):
            pages.append(f"{LIST_URL.rstrip('/')}/index_{page}.shtml")
        ann_links: list[tuple[str, str]] = []
        for page_url in pages:
            html = self._fetch_text(page_url)
            if html:
                ann_links.extend(self._parse_list_links(html))
        fetched = 0
        for href, title in ann_links:
            if fetched >= _MAX_DETAILS:
                break
            detail = self._fetch_text(urljoin(LIST_URL, href))
            fetched += 1
            if detail is None:
                continue
            stripped = re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", detail))
            if target not in norm_no(detail) and target not in stripped:
                continue
            if _TITLE_WITHDRAWN.search(title):
                return urljoin(LIST_URL, href), "withdrawn"
            if _TITLE_EFFECTIVE.search(title):
                return urljoin(LIST_URL, href), "effective"
        return None, None


    @staticmethod
    def _parse_list_links(html: str) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        for m in re.finditer(r'<a[^>]*href="([^"]+\.html)"[^>]*>(.*?)</a>', html, re.S):
            href, raw = m.group(1), re.sub(r"<[^>]+>", "", m.group(2)).strip()
            if not raw or len(raw) < 4:
                continue
            if not any(k in raw for k in ("标准", "公告", "通知", "文告")):
                continue
            out.append((href, raw))
        return out

