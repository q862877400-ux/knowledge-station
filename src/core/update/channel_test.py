"""
渠道的「已知文件测试」（批C，2026-09-22 业主定案）：每条渠道配一个**已知文件**
（样本链接 + 期望标准号）；测试 = 从这条渠道把它拉下来、识别出标准号、比对期望 ——
**能拿到已知文件 = 这渠道算数**。结果留痕在 `channel_test_case`（ok/fail + 详情 + 时间）。

为什么要做：探针只答"今天能不能抓"（连通+锚点）；已知文件测试答的是更强的一句
"**真东西拿不拿得到、认不认得出**"——这是渠道的验收口径（业主原话：
"成功把某个你知道的文件从新渠道下载或者识别下来了，那就说明这个渠道是成功的"）。

实现纪律：
- 拉取走**可注入** `fetcher`（默认 urllib 标准库 GET，10 秒超时）——测试喂假 fetcher，
  不打真网络；真实路径与测试路径**同一段比对代码**（不许测试另写一份）。
- 标准号识别用本模块的 `STANDARD_NO_RE`（正则从文里找）；识别口径=找到的第一个号。
- 结果**永远落库**（成功失败都留痕——不留痕就等于没测过）。
"""
from __future__ import annotations

import re
import urllib.request
from datetime import datetime
from typing import Any, Callable

from src.core.storage.sqlite_db import get_db_connection, write_transaction

#: 标准号形状（识别口径）：常见前缀 + 数字 + 可选年号。命中第一个即认。
STANDARD_NO_RE = re.compile(
    r"(?:GB/T|GBZ/T|GBZ|GBT|GB|JGJ|JG/T|JG|CJJ|CJ|DL/T|DL|HG/T|HG|SH/T|SH|HJ|SY/T|SY|"
    r"JT/T|JT|JTG|YD|SJ|QB/T|QB|NY/T|NY|SL|TB|MT|LD|EJ|FZ/T|FZ|GA/T|GA|JJG|JJF|"
    r"DB\d*/T|DB\d*|T/CECS|CECS)[\s]*\d{1,5}(?:[.-]\d{1,4})*(?:[-—]\d{4})?")

FetchResult = tuple[int, bytes]


def default_fetcher(url: str) -> FetchResult:
    """默认拉取器：标准库 GET，10s 超时，只收 2xx。返回 (HTTP 码, 正文字节)。"""
    req = urllib.request.Request(url, headers={"User-Agent": "ks-channel-test/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310 —— url 由人填
        return int(resp.status), resp.read(262144)


def identify_standard_no(text: str) -> str | None:
    """从文本里识别标准号（第一个命中）；识别不出 = None（如实说，不硬凑）。"""
    m = STANDARD_NO_RE.search(text or "")
    return m.group(0).strip() if m else None


def _norm_no(s: str | None) -> str:
    """比对口径：去空格、破折号归一、统一大写（大小写/横竖线不该决定成败）。"""
    return re.sub(r"[\s\u2014\u2013-]+", "", (s or "")).upper()


def set_test_case(channel_id: str, sample_url: str, expect_no: str,
                  note: str | None = None) -> dict[str, Any] | None:
    """给渠道配/改「已知文件」（样本链接 + 期望标准号）。渠道不存在返回 None。"""
    conn = get_db_connection()
    if conn.execute("SELECT 1 FROM update_channel WHERE channel_id=?",
                    (channel_id,)).fetchone() is None:
        return None
    with write_transaction() as txn:
        # 复核点名修（2026-09-23）：配/改样本 = 重新起跑的声明 ⇒ **清掉旧样本的留痕**
        # （原样会把旧样本的 ok/fail 挂到新样本头上=留痕误导，真数据口径的真缺陷）。
        txn.execute(
            "INSERT INTO channel_test_case(channel_id, sample_url, expect_no, note)"
            " VALUES (?,?,?,?) ON CONFLICT(channel_id) DO UPDATE SET"
            " sample_url=excluded.sample_url, expect_no=excluded.expect_no,"
            " note=excluded.note, updated_at=datetime('now'),"
            " last_result=NULL, last_detail=NULL, last_run_at=NULL",
            (channel_id, sample_url, expect_no, note))
    return get_test_case(channel_id)


def get_test_case(channel_id: str) -> dict[str, Any] | None:
    row = get_db_connection().execute(
        "SELECT * FROM channel_test_case WHERE channel_id=?",
        (channel_id,)).fetchone()
    return dict(row) if row else None


def run_channel_test(channel_id: str,
                     fetcher: Callable[[str], FetchResult] | None = None) -> dict[str, Any]:
    """跑这条渠道的「已知文件测试」：拉样本 → 识别标准号 → 比对期望 → 落痕。

    返回 {"result": "ok"|"fail"|"no_case", "detail": 人话, ...}。**失败也落库**（留痕）。
    """
    case = get_test_case(channel_id)
    if case is None:
        return {"result": "no_case",
                "detail": "这条渠道还没配「已知文件」（样本链接 + 期望标准号）"}
    fetch = fetcher or default_fetcher
    try:
        status, body = fetch(case["sample_url"])
    except Exception as exc:  # noqa: BLE001 —— 网络万象，失败要如实落痕
        detail = f"拉取失败：{type(exc).__name__}: {exc}"
        _record(channel_id, "fail", detail)
        return {"result": "fail", "detail": detail}
    text = body.decode("utf-8", errors="replace")
    if status < 200 or status >= 300:
        detail = f"拉取失败：HTTP {status}"
        _record(channel_id, "fail", detail)
        return {"result": "fail", "detail": detail}
    got = identify_standard_no(text)
    if got is None:
        detail = "拉到了内容，但没认出任何标准号（识别口径见 STANDARD_NO_RE）"
        _record(channel_id, "fail", detail)
        return {"result": "fail", "detail": detail}
    if _norm_no(got) == _norm_no(case["expect_no"]):
        detail = f"拿到并认出了已知文件：{got}"
        _record(channel_id, "ok", detail)
        return {"result": "ok", "detail": detail, "got": got}
    detail = f"认出的是 {got}，期望是 {case['expect_no']}——对不上"
    _record(channel_id, "fail", detail)
    return {"result": "fail", "detail": detail, "got": got}


def _record(channel_id: str, result: str, detail: str) -> None:
    with write_transaction() as txn:
        txn.execute(
            "UPDATE channel_test_case SET last_result=?, last_detail=?, last_run_at=?"
            " WHERE channel_id=?",
            (result, detail, datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), channel_id))
