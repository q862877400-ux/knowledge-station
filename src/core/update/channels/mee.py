"""mee 适配器（2026-08 实测，巡检时效）。

生态环境部 HJ 标准（datacenter.mee.gov.cn 数据中心「国家环境保护标准」报告，
2026-08 实测）：
- 查询：POST http://datacenter.mee.gov.cn/websjzx/report!list.action?xmlname=1520238134405
  表单 doctitle=<标准号或标准名称>（可选 bzys=标准要素 id）→ 服务端渲染报告页 HTML（UTF-8）。
- 报告页表格（#GridView1）列 colid：1 标准号 / 2 标准名称 / 5 标准实施时间 /
  6 摘要 / 7 文件下载（display:none）。

PDF 全文下载链接逆向（本适配器核心，2026-08 Network 实测）：
- 报告页「文件下载」列（colid=7，隐藏）**直接内嵌全文 PDF 的完整 URL**，例如
  http://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/shjbh/xgbzh/201705/W020170511332490849000.pdf
- 页面 JS 仅把该隐藏单元格渲染成可点击的下载链接——无 token、无附加接口、无签名拼接。
- 程序化复刻：解析 colid=7 单元格文本 → http→https 归一 → urljoin 兜底相对路径。
- 实测 GET https://www.mee.gov.cn/ywgz/fgbz/bz/bzwb/shjbh/xgbzh/201705/W020170511332490849000.pdf
  → 200 application/pdf，351,611 字节（%PDF-1.7），正文为 HJ 819-2017
  《排污单位自行监测技术指南 总则》共 14 页（含 发布 2017-04-25 / 实施 2017-06-01）。

状态弱信号：报告页无 现行/废止 列，只有实施时间 → legal_status=None、change_type=None
交聚合层判定；实施时间 + 全文 PDF 链接作为「标准存在」证据（raw.note 记录）。

输入归一：doctitle 匹配大小写不敏感但空格敏感（实测 "HJ819-2017" 查不到而 "HJ 819-2017"
命中）；首查 0 行时用「字母前缀 + 空格 + 余部」候选重试一次（≤2 次请求/号）。
"""
from __future__ import annotations

import html
import re
from time import perf_counter
from typing import Any
from urllib.parse import urljoin

from src.core.update.channels.base import (
    ChannelAdapter,
    ChannelResult,
    looks_like_captcha,
    pick_row_by_norm,
    upd_log,
)

QUERY_URL = ("http://datacenter.mee.gov.cn/websjzx/report!list.action"
             "?xmlname=1520238134405")
REFERER = "https://www.mee.gov.cn/ywgz/fgbz/bz/"
PDF_BASE = "https://www.mee.gov.cn/"

# 报告页表格列号（MEE 站点改版即失效，集中命名便于维护）
COL_NO = 1
COL_NAME = 2
COL_EFF = 5
COL_ABSTRACT = 6
COL_PDF = 7

_ROW_RE = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.S)
_DATE_RE = re.compile(r"20\d{2}-\d{2}-\d{2}")
_STATE_NOTE = ("mee: 无状态列，仅实施时间弱信号；legal_status/change_type 交聚合层判定")


def _cell_text(tr: str, colid: int) -> str | None:
    """取表格行内指定 colid 单元格的可见文本（剥标签、unescape、去空白）。"""
    m = re.search(r'<td\b[^>]*colid="%d"[^>]*>(.*?)</td[^>]*>' % colid, tr, re.S)
    if not m:
        return None
    text = html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()
    return text or None


def build_pdf_url(cell_text: str | None) -> str | None:
    """逆向 PDF 全文 URL：colid=7 隐藏列内嵌完整下载地址（实测无 token/附加接口）。

    - 单元格内若含 <a href=...> 优先取 href（javascript: 壳除外），否则取可见文本；
    - http→https 归一；相对路径用 mee.gov.cn 根 urljoin 兜底。
    """
    raw = (cell_text or "").strip()
    if not raw:
        return None
    href = re.search(r'href="([^"]+)"', raw)
    if href and not href.group(1).lstrip().lower().startswith("javascript"):
        url = href.group(1).strip()
    else:
        url = re.sub(r"<[^>]+>", "", raw).strip()
    if not url:
        return None
    if url.lower().startswith("http://"):
        url = "https://" + url[len("http://"):]
    if not url.lower().startswith("https://"):
        url = urljoin(PDF_BASE, url)
    return url


def spaced_candidate(standard_no: str) -> str | None:
    """压缩输入 → 官方空格形态候选（引擎空格敏感）：HJ819-2017 → HJ 819-2017。

    已含空格输入返回 None（不触发重试）：前缀后须紧跟数字才判定为压缩形态。
    """
    m = re.match(r"^([A-Za-z]+(?:/[A-Za-z]*)?)(\d\S*)$", (standard_no or "").strip())
    if not m:
        return None
    cand = m.group(1) + " " + m.group(2)
    return cand if cand != (standard_no or "").strip() else None


def parse_report_page(page_html: str) -> list[dict]:
    """解析报告页 HTML → 记录行列表（标准号/名称/实施时间/摘要/pdf_url）。"""
    rows: list[dict[str, Any]] = []
    for tr in _ROW_RE.findall(page_html):
        if "<th" in tr:
            continue
        no = _cell_text(tr, COL_NO)
        eff_raw = _cell_text(tr, COL_EFF)
        date_m = _DATE_RE.search(eff_raw or "")
        row = {
            "no": no,
            "name": _cell_text(tr, COL_NAME),
            "effective_date": date_m.group(0) if date_m else None,
            "abstract": _cell_text(tr, COL_ABSTRACT),
            "pdf_url": build_pdf_url(_cell_text(tr, COL_PDF)),
        }
        if row["no"] or row["effective_date"] or row["pdf_url"]:
            rows.append(row)
    return rows


class MeeAdapter(ChannelAdapter):
    """mee：标准号级状态探测（确定性、离线可测、异常归一）。"""

    name = "mee"

    def probe(self, standard_no: str, standard_name: str = "") -> ChannelResult:
        t0 = perf_counter()
        status, body = self._fetch(
            QUERY_URL, method="post", data={"doctitle": standard_no},
            headers={"Referer": REFERER})

        if looks_like_captcha(body):
            return self._log_probe(t0, standard_no, ChannelResult(
                channel=self.name, found=False, captcha=True,
                raw={"http": status, "body": body}))

        if not isinstance(body, str):
            return self._miss(t0, standard_no, status, note="unexpected_body_type")

        rows = parse_report_page(body)
        if not rows:
            cand = spaced_candidate(standard_no)
            if cand and cand != (standard_no or "").strip():
                status, body2 = self._fetch(
                    QUERY_URL, method="post", data={"doctitle": cand},
                    headers={"Referer": REFERER})
                if isinstance(body2, str):
                    rows = parse_report_page(body2)

        row = self._pick_row(rows, standard_no)
        if row is None:
            return self._miss(t0, standard_no, status, note="no_matching_row")

        upd_log(self.trace_id, f"channel.{self.name}", "INFO", "weak_status_only",
                standard_no=standard_no, effective_date=row.get("effective_date"),
                pdf=bool(row.get("pdf_url")))
        result = ChannelResult(
            channel=self.name,
            found=True,
            change_type=None,
            legal_status=None,
            latest_version=row.get("no"),
            effective_date=row.get("effective_date"),
            evidence_url=row.get("pdf_url"),
            raw={"http": status, "row": row, "note": _STATE_NOTE},
        )
        return self._log_probe(t0, standard_no, result)

    def _pick_row(self, rows: list[dict], standard_no: str) -> dict | None:
        """行挑选：精确归一号匹配优先；否则同主体（去年代）取号最大者，保证确定性。"""
        return pick_row_by_norm(rows, standard_no, code_key="no")
