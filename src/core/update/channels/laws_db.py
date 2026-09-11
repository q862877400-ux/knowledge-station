"""国家法律法规数据库适配器（laws_db，flk.npc.gov.cn，FRB F-22 真机版）。

查询：``POST /law-search/search/list``（载荷为 cn-law-hub 项目实测文档化的浏览器真实载荷，
2026-08-24 实测可用）；行内 ``sxx`` 状态码映射：3=有效→effective、2=被修改→superseded、
4=尚未生效→upcoming、1=已废止→withdrawn；未知码 → 告警不猜测（pipeline/05 §2 UPD-3xxx 哲学）。
标题含 ``<em class='highlight'>`` 高亮标记，须剥离后比对。
"""
from __future__ import annotations

import re
from time import perf_counter
from typing import Any

from src.core.update.channels.base import (
    ChannelAdapter,
    ChannelResult,
    upd_log,
)

SXX_LEGAL: dict[int, str] = {
    1: "withdrawn",   # 已废止
    2: "superseded",  # 被修改（旧版仍可查，已有新版）
    3: "effective",   # 现行有效
    4: "upcoming",    # 尚未生效
}


class LawsDbAdapter(ChannelAdapter):
    """法律法规渠道（F-22）：标题精确/模糊检索 → 状态映射 → ChannelResult。"""

    name = "laws_db"
    SEARCH_URL = "https://flk.npc.gov.cn/law-search/search/list"
    DETAIL_BASE = "https://flk.npc.gov.cn/detail?id="

    def _search(self, query: str) -> list[dict]:
        payload = {
            "searchRange": 1, "sxrq": [], "gbrq": [], "sxx": [],
            "searchType": 2, "xgzlSearch": False, "searchContent": query,
            "orderByParam": {"order": "-1", "sort": ""},
            "flfgCodeId": [], "zdjgCodeId": [], "gbrqYear": [],
            "pageNum": 1, "pageSize": 20,
        }
        status, body = self._fetch(self.SEARCH_URL, method="post", json=payload)
        if not isinstance(body, dict):
            return []
        rows = body.get("rows") or []
        return [r for r in rows if isinstance(r, dict)]

    def probe(self, standard_no: str, standard_name: str = "") -> ChannelResult:
        t0 = perf_counter()
        query = (standard_name or standard_no).strip()
        if not query:
            return self._miss(t0, standard_no, 200, note="empty_query")
        rows = self._search(query)  # UPD-1xxx 由 _search/_fetch 归一，交由降级链
        target = re.sub(r"\s+", "", query)

        def norm_title(row: dict) -> str:
            t = re.sub(r"<[^>]+>", "", row.get("title") or "")
            return re.sub(r"\s+", "", t)

        matches = [r for r in rows if target in norm_title(r) or norm_title(r) in target]
        if not matches:
            return self._miss(t0, standard_no, 200,
                              note=f"no_title_match rows={len(rows)}")
        # 确定性挑选：现行(sxx=3)优先，其次按公布日期新者优先
        best = max(matches, key=lambda r: (1 if r.get("sxx") == 3 else 0,
                                           str(r.get("gbrq") or "")))
        sxx = best.get("sxx")
        legal_status = SXX_LEGAL.get(sxx) if isinstance(sxx, int) else None
        if sxx is not None and legal_status is None:
            upd_log(self.trace_id, f"channel.{self.name}", "WARN",
                    "illegal_sxx_code", standard_no=standard_no, sxx=sxx)
        bbbs = str(best.get("bbbs") or "")
        # change_type 域约束在 schema CHECK（new_version/superseded/withdrawn/not_found/no_change）：
        # upcoming 不属枚举 → None 交聚合层（legal_status='upcoming' 按现行绿处理，04a §4）
        change_type: str | None = (
            "no_change" if legal_status == "effective"
            else (legal_status if legal_status in ("superseded", "withdrawn") else None))
        result = ChannelResult(
            channel=self.name,
            found=True,
            change_type=change_type,
            legal_status=legal_status,
            effective_date=str(best.get("sxrq") or best.get("gbrq") or "").strip() or None,
            evidence_url=f"{self.DETAIL_BASE}{bbbs}" if bbbs else None,
            raw={"sxx": sxx, "row": {k: best.get(k) for k in
                                     ("bbbs", "title", "flxz", "zdjgName", "gbrq", "sxrq", "sxx")}},
        )
        return self._log_probe(t0, standard_no, result)
