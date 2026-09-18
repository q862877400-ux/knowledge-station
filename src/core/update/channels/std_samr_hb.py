"""std_samr_hb适配器（2026-08 实测，巡检时效）。

全国标准信息公共服务平台·行业标准目录（2026-08 实测，首选状态源）：
GET https://std.samr.gov.cn/hb/search/hbPage → JSON（非 HTML），行含
STATE(现行/即将实施/废止/被代替)、ISSUE_DATE(发布日期)、ACT_DATE(实施日期)、
STD_NATURE(强制性/推荐性)；total 约 10.8 万。一条 GET 即得状态。

实测要点（2026-08）：
- searchText 含空格/斜杠（如 "GB/T 50493-2019"）时后端退化为全库 match-all
  （total≈107960，返回置顶行）——必须传归一号 compact 形态（norm_no 去空白/斜杠
  大写，AQ 3028-2008 → AQ3028-2008）才真正过滤；库内无该号 → total=0。
  如 GB/T 50493-2019（国标，不在行业目录）→ 诚实 miss。
- AQ 3028-2008 实测：total=1，STATE=废止，ISSUE_DATE=2008-11-19，
  ACT_DATE=2009-01-01，STD_NATURE=强制性。
- 证据链（hb-data.js 前端拼法）：https://std.samr.gov.cn/hb/search/stdHBDetailed?id=<row.id>
- 本库无废止日期字段（废止标准只有 STATE=废止 + 自身实施日期），
  effective_date 取 ACT_DATE（实施日期）；废止判定交给 STATE。

mock 应答契约（离线表驱动，同 04a §0）：
``{"http":200,"body":{"total":N,"rows":[{"id","STD_CODE","STATE","G_STATE",
"ISSUE_DATE","ACT_DATE"}]}}``；未知 STATE 串不猜测 → legal_status=None 并告警。
"""
from __future__ import annotations

import time
from time import perf_counter
from typing import Any

from src.core.update.channels.base import (
    ChannelAdapter,
    ChannelResult,
    CurlCffiTransport,
    HttpxTransport,
    derive_change_type,
    looks_like_captcha,
    map_state_text,
    norm_no,
    pick_row_by_norm,
    upd_log,
)

#: 浏览器 UA（政府站观察模式放行浏览器指纹；2026-08 实测）+ 调用间礼貌限速
_BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")


class StdSamrHbAdapter(ChannelAdapter):
    """std_samr_hb：行业标准目录标准号级状态探测（确定性、离线可测、异常归一）。"""

    name = "std_samr_hb"
    SEARCH_URL = "https://std.samr.gov.cn/hb/search/hbPage"
    DETAIL_URL = "https://std.samr.gov.cn/hb/search/stdHBDetailed?id={}"
    REFERER = "https://std.samr.gov.cn/hb/hbQuery"
    PAUSE_S = 1.0

    def probe(self, standard_no: str, standard_name: str = "") -> ChannelResult:
        t0 = perf_counter()
        compact = norm_no(standard_no)
        if not compact:
            # 空/纯符号输入会触发 match-all，直接诚实 miss（不发起查询）
            return self._miss(t0, standard_no, 200, note="empty_standard_no")

        status, body = self._fetch(
            self.SEARCH_URL,
            # searchText 必须为归一号（空格/斜杠会触发全库 match-all，ANOM-同族）
            params={"searchText": compact, "op": "", "ISSUE_DATE": ""},
            headers={"User-Agent": _BROWSER_UA, "Referer": self.REFERER},
        )
        self._pace()

        # 验证码特征优先判定：半自动降级标记，绝不当 miss 处理（F-11）
        if looks_like_captcha(body):
            return self._log_probe(t0, standard_no, ChannelResult(
                channel=self.name, found=False, captcha=True,
                raw={"http": status, "body": body}))

        rows: list[Any] = []
        if isinstance(body, dict):
            rows = body.get("rows") or []
        row = self._pick_row(rows, compact)
        if row is None:
            return self._miss(t0, standard_no, status, note=f"matches={len(rows)}")

        version = (str(row.get("STD_CODE") or "").strip() or None)
        raw_state = str(row.get("STATE") or row.get("G_STATE") or "").strip()
        legal_status = map_state_text(raw_state)
        if raw_state and legal_status is None:
            # INS-B-05/D-06：非法状态串降级为告警，不猜测不写脏值
            upd_log(self.trace_id, f"channel.{self.name}", "WARN", "illegal_state_text",
                    standard_no=standard_no, state=raw_state)

        result = ChannelResult(
            channel=self.name,
            found=True,
            change_type=derive_change_type(standard_no, version, legal_status),
            legal_status=legal_status,
            latest_version=version,
            # ACT_DATE=实施日期（本库无废止日期字段）；缺省回退发布日期
            effective_date=(str(row.get("ACT_DATE") or row.get("ISSUE_DATE") or "").strip() or None),
            # §11.0 R6c-3e：ISSUE_DATE 是**发布**日期，落它自己的槽（以前只在回退时才用）
            published_date=(str(row.get("ISSUE_DATE") or "").strip() or None),
            evidence_url=(self.DETAIL_URL.format(row["id"]) if row.get("id") else self.SEARCH_URL),
            raw={"http": status, "row": row},
        )
        return self._log_probe(t0, standard_no, result)

    def _pick_row(self, rows: list[Any], compact: str) -> dict | None:
        """行挑选：精确归一号匹配优先；否则同主体（去年代）取号最大者，保证确定性。"""
        return pick_row_by_norm(rows, compact, code_key="STD_CODE")

    def _pace(self) -> None:
        """调用间限速（政府站礼貌速率）；mock transport 不睡眠保测试速度。"""
        if isinstance(self.transport, (CurlCffiTransport, HttpxTransport)):
            time.sleep(self.PAUSE_S)
