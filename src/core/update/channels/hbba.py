"""hbba适配器（2026-08 实测，巡检时效）。

行业标准信息服务平台（2026-08 实测，裸 nginx 零反爬）：
POST https://hbba.sacinfo.org.cn/stdQueryList
（application/x-www-form-urlencoded，表单 key=<标准号>）→ JSON：
``{"total": N, "records": [{"pk", "code", "chName", "status", "issueDate",
"actDate", "fzDate", "reviseStdCodes", ...}]}``

实测要点（2026-08）：
- 请求体字段：current(页码)/size(页大小)/key(标准号关键字)/ministry/industry/
  pubdate/date/status（后四者留空，stdList 页 queryParams 原样）。
- 日期为 epoch 毫秒（北京时间 UTC+8）：issueDate 批准日期 / actDate 实施日期 /
  fzDate 废止日期（仅废止行有值；AQ 3028-2008 实测 fzDate=2024-07-01，status=废止）。
- status 词汇：现行 / 即将实施 / 废止 / 有更新版（旧版被新版代替时，旧版行
  status="有更新版"，reviseStdCodes 为其所取代的更早版本号）。
- 状态判定：废止→withdrawn（effective_date 取 fzDate 废止日期）、
  有更新版→superseded、现行→effective、即将实施→upcoming；非废止取 actDate。
- 证据链：详情页 https://hbba.sacinfo.org.cn/stdDetail/<pk>。

mock 应答契约（离线表驱动，同 04a §0）：
``{"http":200,"body":{"total":N,"records":[{"code","status","issueDate",
"actDate","fzDate","pk"}]}}``；未知 status 串不猜测 → legal_status=None 并告警。
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from time import perf_counter
from typing import Any
from urllib.parse import quote

from src.core.update.channels.base import (
    ChannelAdapter,
    ChannelResult,
    derive_change_type,
    looks_like_captcha,
    map_state_text,
    pick_row_by_norm,
    query_no,
    upd_log,
)

#: sacinfo 平台独有状态串 → 枚举（base 未覆盖项；有更新版=被新版代替）
_SACINFO_STATE_MAP = {"有更新版": "superseded"}

#: 平台日期按北京时间（UTC+8）发布，转换固定时区保证跨机确定性
_CST = timezone(timedelta(hours=8))


def _epoch_ms_to_date(value: Any) -> str | None:
    """epoch 毫秒 → YYYY-MM-DD（CST）；空值/非数值 → None（确定性）。"""
    try:
        ms = float(value)
    except (TypeError, ValueError):
        return None
    if not ms:
        return None
    return datetime.fromtimestamp(ms / 1000.0, tz=_CST).strftime("%Y-%m-%d")


def _sacinfo_state(raw: str | None) -> str | None:
    """sacinfo 状态串 → legal_status 枚举；未知串返回 None（调用方须告警）。"""
    if not raw:
        return None
    raw = raw.strip()
    return _SACINFO_STATE_MAP.get(raw) or map_state_text(raw)


class _SacinfoQueryAdapter(ChannelAdapter):
    """sacinfo 行业/地方标准查询平台共享实现（hbba/dbba 同构）。

    子类只需覆盖 ``name`` 与 ``host``。POST /stdQueryList 表单查询，
    按标准号匹配 records，fzDate/status 驱动状态判定（见模块 docstring）。
    """

    #: 平台域名，子类覆盖（hbba.sacinfo.org.cn / dbba.sacinfo.org.cn）
    host: str = "hbba.sacinfo.org.cn"

    def probe(self, standard_no: str, standard_name: str = "") -> ChannelResult:
        t0 = perf_counter()
        key = query_no(standard_no).strip()   # 全角斜杠换半角（§11.0 R6c-2b）
        if not key:
            return self._miss(t0, standard_no, 200, note="empty_standard_no")

        status, body = self._fetch(
            f"https://{self.host}/stdQueryList",
            method="post",
            # 与 stdList 页 queryParams 同形（current/size 页码，key=标准号）
            data={"current": "1", "size": "20", "key": key,
                  "ministry": "", "industry": "", "pubdate": "", "date": "", "status": ""},
            headers={"Referer": f"https://{self.host}/stdList?key={quote(key)}",
                     "X-Requested-With": "XMLHttpRequest"},
        )

        # 验证码特征优先判定：半自动降级标记，绝不当 miss 处理（F-11）
        if looks_like_captcha(body):
            return self._log_probe(t0, standard_no, ChannelResult(
                channel=self.name, found=False, captcha=True,
                raw={"http": status, "body": body}))

        records: list[Any] = []
        if isinstance(body, dict):
            records = body.get("records") or []
        row = self._pick_row(records, standard_no)
        if row is None:
            return self._miss(t0, standard_no, status, note=f"matches={len(records)}")

        version = (str(row.get("code") or "").strip() or None)
        raw_state = str(row.get("status") or "").strip()
        legal_status = _sacinfo_state(raw_state)
        if raw_state and legal_status is None:
            # INS-B-05/D-06：非法状态串降级为告警，不猜测不写脏值
            upd_log(self.trace_id, f"channel.{self.name}", "WARN", "illegal_state_text",
                    standard_no=standard_no, state=raw_state)

        # effective_date：废止行取 fzDate（废止日期），否则取 actDate（实施日期）
        effective_date = None
        if legal_status == "withdrawn":
            effective_date = _epoch_ms_to_date(row.get("fzDate"))
        if effective_date is None:
            effective_date = _epoch_ms_to_date(row.get("actDate"))

        result = ChannelResult(
            channel=self.name,
            found=True,
            change_type=derive_change_type(standard_no, version, legal_status),
            legal_status=legal_status,
            latest_version=version,
            effective_date=effective_date,
            # §11.0 R6c-3e：`issueDate`（批准/发布日期）本来就在响应行里、也被整行放进 raw，
            # 但代码从没把它**命名**解析出来（复核 b35 逐条核代码时点到的）——现在落它自己的槽。
            published_date=_epoch_ms_to_date(row.get("issueDate")),
            evidence_url=(f"https://{self.host}/stdDetail/{row['pk']}" if row.get("pk")
                          else f"https://{self.host}/stdList?key={quote(key)}"),
            raw={"http": status, "row": row},
        )
        return self._log_probe(t0, standard_no, result)

    def _pick_row(self, records: list[Any], standard_no: str) -> dict | None:
        """行挑选：精确归一号匹配优先；否则同主体（去年代）取号最大者，保证确定性。"""
        return pick_row_by_norm(records, standard_no, code_key="code")


class HbbaAdapter(_SacinfoQueryAdapter):
    """hbba：行业标准信息服务平台（标准号级状态探测，确定性、离线可测、异常归一）。"""

    name = "hbba"
    host = "hbba.sacinfo.org.cn"
