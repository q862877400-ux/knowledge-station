"""国家标准全文公开系统适配器（openstd.samr.gov.cn，F-02 主渠道）。

验证码半自动降级（F-11）：命中验证码特征 → ``ChannelResult(captcha=True)``，
只返回标记不写库、不计 gray/failed，批次转 paused 等人工过点（pipeline/05 §3）。

mock 应答契约（离线表驱动，04a §0）：
``{"http":200,"body":{"rows":[{"code","name","state","url","date"}]}}``
- ``code``：含年代的官方标准号；``state``：现行/即将实施/被代替/废止；
- ``date``：施行日期（YYYY-MM-DD）；未知 state 串不猜测 → legal_status=None 并告警。
"""
from __future__ import annotations

import re
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
    pick_row_by_norm,
    query_no,
    upd_log,
)

#: 浏览器 UA + Referer（openstd 政府站观察模式放行浏览器指纹；2026-08 实测）
_BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")


class OfficialGbAdapter(ChannelAdapter):
    """主渠道：命中即止（降级链 official_gb→web→govcn 由 inspector 编排）。"""

    name = "official_gb"
    # ANOM-003 修正：真实列表接口为 /bzgk/std/std_list（/bzgk/gb/std_list 会重定向），
    # 查询参数为 p.p2=<标准号>；返回服务端渲染 HTML 表格（非 JSON rows）。
    SEARCH_URL = "https://openstd.samr.gov.cn/bzgk/std/std_list"
    #: 调用间礼貌限速（防风控；mock transport 不睡眠保测试速度）
    PAUSE_S = 1.0

    def probe(self, standard_no: str, standard_name: str = "") -> ChannelResult:
        t0 = perf_counter()
        # ⚠ 查询用 `query_no`（全角斜杠换半角，§11.0 R6c-2b 实测）：真库 92% 的号写全角 `／`，
        #   原样送进查询串在 A/B 里 **0/6 命中**，换成半角 **5/6 命中**。
        q = query_no(standard_no)
        status, body = self._fetch(
            self.SEARCH_URL,
            # searchText 仅供测试 mock 路由复用（真实站点忽略未知参数）；p.p2 为真实查询键
            params={"searchText": q, "p.p1": "0", "p.p90": "circulation_date",
                    "p.p91": "desc", "p.p2": q},
            headers={"User-Agent": _BROWSER_UA, "Referer": self.SEARCH_URL})
        self._pace()

        # 验证码特征优先判定：半自动降级标记，绝不当 miss 处理（F-11）
        if looks_like_captcha(body):
            return self._log_probe(t0, standard_no, ChannelResult(
                channel=self.name, found=False, captcha=True,
                raw={"http": status, "body": body}))

        rows: list[Any] = []
        if isinstance(body, str) and body.lstrip().startswith(("<", "<!")):
            # 真实 openstd 返回服务端渲染 HTML 结果表（ANOM-003 修正）：
            # <tr><td>序号</td><td><a onclick="showInfo('ID')">GB 30871-2022</a></td>...
            # <td class="mytxt"><a ...>名称</a></td><td>强标|推荐</td>
            # <td><span class="text-success">现行</span></td><td>2022-03-15</td><td>2022-10-01</td>
            for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", body, re.S):
                m_code = re.search(r"<td[^>]*>\s*<a[^>]*>([^<]*GB[^<]*)</a>", tr, re.S)
                if not m_code:
                    continue
                m_name = re.search(r'<td class="mytxt"[^>]*>.*?<a[^>]*>([^<]*)</a>', tr, re.S)
                m_state = re.search(r"<span[^>]*>\s*(现行|即将实施|被代替|废止)\s*</span>", tr)
                dates = re.findall(r"<td[^>]*>\s*(\d{4}-\d{2}-\d{2})\s*</td>", tr)
                m_info = re.search(r"showInfo\('([^']+)'\)", tr)
                rows.append({
                    "code": re.sub(r"\s+", " ", m_code.group(1)).strip(),
                    "name": re.sub(r"\s+", " ", m_name.group(1)).strip() if m_name else "",
                    "state": m_state.group(1).strip() if m_state else "",
                    "date": dates[0] if dates else None,
                    "url": f"showInfo:{m_info.group(1)}" if m_info else None,
                })
        elif isinstance(body, dict):
            # mock 契约（tests/fixtures/update_channels.json）保持兼容
            rows = body.get("rows") or []
        row = self._pick_row(rows, standard_no)
        if row is None:
            return self._miss(t0, standard_no, status, note=f"matches={len(rows)}")

        version = (str(row.get("code") or "").strip() or None)
        raw_state = str(row.get("state") or "").strip()
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
            effective_date=(str(row["date"]).strip() or None) if row.get("date") else None,
            evidence_url=row.get("url") or None,
            raw={"http": status, "row": row},
        )
        return self._log_probe(t0, standard_no, result)

    def _pick_row(self, rows: list[Any], standard_no: str) -> dict | None:
        """行挑选：精确归一号匹配优先；否则同主体（去年代）取号最大者，保证确定性。"""
        return pick_row_by_norm(rows, standard_no, code_key="code")

    def _pace(self) -> None:
        """调用间限速（政府站礼貌速率）；mock transport 不睡眠保测试速度。"""
        if isinstance(self.transport, (CurlCffiTransport, HttpxTransport)):
            time.sleep(self.PAUSE_S)
