"""更新渠道适配器基座（阶段六·批次1）。

锁定接口（pipeline/02 §1 拓扑、pipeline/04a §2 验收；后续批次依赖，不得偏离）：
- ``ChannelResult``：单渠道一次探测的确定性结论（字段与默认值逐字冻结）
- ``ChannelAdapter``：transport 注入式抽象；``transport=None`` 时走默认真实传输
  （``transport.fetch(url, **kw) -> (http_status:int, body:dict|str)``）。
  默认实现优先 curl_cffi 模拟浏览器 TLS 指纹（ANOM-002：gov 三站点 JA3 级 WAF
  掐 Python 握手）；curl_cffi 不可导入时回退 httpx 并打一条 WARN。

日志规约（pipeline/05 §1）：每条探测必落一行
``[ISO] [UPD] [TRACE=<batch_id>] [SPAN=channel.<name>] [LEVEL=...] 消息 键值对...``
TRACE 由 inspector（后续批次）注入 ``adapter.trace_id``。

错误码（pipeline/05 §2，UPD-1xxx 渠道层 / 2xxx 业务层 / 3xxx 校验层）：
- UPD-1001 channel_timeout      UPD-1002 captcha_blocked（半自动标记）
- UPD-1003 rate_limited         UPD-1004 channel_unreachable
- UPD-2001 batch_already_running（inspector 批次用，本批预留）
- UPD-2002 change_not_found     UPD-2003 batch_not_found  UPD-2004 announcement_not_found
- UPD-3001 illegal_legal_status UPD-3004 illegal_change_type
- UPD-3005 illegal_batch_status UPD-3006 illegal_trigger_type
- UPD-3007 bad_change_payload
"""
from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from time import perf_counter
from typing import Any

from src.core.exceptions import KnowledgeStationError

# ---------------------------------------------------------------- 错误码常量
UPD_CHANNEL_TIMEOUT = "UPD-1001"
UPD_CAPTCHA_BLOCKED = "UPD-1002"
UPD_CHANNEL_ERROR = "UPD-1004"
UPD_BATCH_ALREADY_RUNNING = "UPD-2001"
UPD_CHANGE_NOT_FOUND = "UPD-2002"
UPD_BATCH_NOT_FOUND = "UPD-2003"
UPD_ANNOUNCEMENT_NOT_FOUND = "UPD-2004"
UPD_ANNOUNCE_SOURCE_NOT_FOUND = "UPD-2005"
UPD_ANNOUNCE_SCAN_ALREADY_RUNNING = "UPD-2006"
UPD_ILLEGAL_LEGAL_STATUS = "UPD-3001"
UPD_ILLEGAL_CHANGE_TYPE = "UPD-3004"
UPD_ILLEGAL_BATCH_STATUS = "UPD-3005"
UPD_ILLEGAL_TRIGGER = "UPD-3006"
UPD_BAD_PAYLOAD = "UPD-3007"
UPD_ILLEGAL_SOURCE_PAYLOAD = "UPD-3008"


class UpdateError(KnowledgeStationError):
    """更新模块专用异常（LlmError 同风格：message + ``UPD-xxxx`` 错误码）。"""

    def __init__(self, message: str, code: str = "UPD-5000"):
        super().__init__(message, code=code)


# ---------------------------------------------------------------- 枚举契约
#: change_type 全集（update_change_event.change_type CHECK 的渠道层子集 + not_found 由编排层归桶）
CHANGE_TYPES = ("new_version", "superseded", "withdrawn", "not_found", "no_change")
#: legal_status 合法枚举（schema CHECK 冻结）
LEGAL_STATUSES = ("effective", "upcoming", "superseded", "withdrawn")

# 中文状态串 → 枚举（官方站/网页摘要共用；未知串不猜测，返回 None 告警）
STATE_TEXT_MAP = {
    "现行": "effective",
    "即将实施": "upcoming",
    "被代替": "superseded",
    "废止": "withdrawn",
}

LOGGER = logging.getLogger("ks.upd")


def upd_log(trace_id: str, span: str, level: str, msg: str, **kv: Any) -> None:
    """按 pipeline/05 §1 规约输出一条结构化日志行（引擎日志同格式采集）。"""
    iso = datetime.now().astimezone().isoformat(timespec="seconds")
    tail = " ".join(f'{k}="{v}"' for k, v in kv.items() if v is not None)
    line = f"[{iso}] [UPD] [TRACE={trace_id}] [SPAN={span}] [LEVEL={level}] {msg}"
    if tail:
        line = f"{line} {tail}"
    fn = {"WARN": "warning"}.get(level, level.lower())
    getattr(LOGGER, fn, LOGGER.info)(line)


def norm_no(no: str | None) -> str:
    """标准号归一：去空白与斜杠、大写（GB/T 3608-2008 ≡ GBT3608-2008）。

    ⚠ **必须同时收全角斜杠 `／`（U+FF0F）**（§11.0 R6c-2a 实测）：
    真库 6417 条标准里 **5879 条（92%）写的是全角 `／`**，而站点返回的是半角 `/`。
    这一行原先只剥半角，于是同一个号两边归一出 `GBT17098-1997` 与 `GB／T17098-1997`
    —— **永不相等**，`pick_row_by_norm` 之类"按归一号挑行"的匹配全线失手。
    另附实测（同一批号两种写法各跑一遍）：**全角 0/6 命中、半角 5/6 命中**，
    且 `ndls` 对全角写法**全部抛错**（查询体里带的就是原始写法）。
    """
    return re.sub(r"[\s/／]+", "", (no or "")).upper()


def strip_year(no_norm: str) -> str:
    """去掉归一号尾部的年代（GBT3608-2008 → GBT3608），用于同主体候选比较。"""
    return re.sub(r"-?\d{4}$", "", no_norm)


def pick_row_by_norm(rows: list[Any], standard_no: str, code_key: str = "code") -> dict | None:
    """按归一号挑选匹配行（mee/hbba/official_gb 三处重复算法的统一收敛）。

    先精确匹配（行内 ``code_key`` 字段归一后 == 目标号），否则取同主体候选
    （去年代后相同）里归一最大者。各渠道字段名不同用 ``code_key`` 传入
    （official_gb/hbba='code'、mee='no'）；非 dict 行自动跳过。
    """
    target = norm_no(standard_no)

    def no_of(r: Any) -> str:
        return norm_no(str(r.get(code_key) or "")) if isinstance(r, dict) else ""

    for r in rows:
        if no_of(r) == target:
            return r
    core = strip_year(target)
    cands = [r for r in rows if no_of(r) and strip_year(no_of(r)) == core]
    if not cands:
        return None
    return max(cands, key=no_of)


def map_state_text(text: str | None) -> str | None:
    """中文状态串 → legal_status 枚举；非法串返回 None（调用方须告警不猜测）。"""
    return STATE_TEXT_MAP.get((text or "").strip())


def derive_change_type(requested_no: str, latest_version: str | None,
                       legal_status: str | None) -> str | None:
    """确定性推导渠道级 change_type（各适配器共用，保证矩阵逐位可复现）：

    废止/被代替优先于版本对比；其次版本归一号不同 → new_version；相同 → no_change；
    无版本信息且非废止/被代替 → None（交由编排层聚合判定）。
    """
    if legal_status == "withdrawn":
        return "withdrawn"
    if legal_status == "superseded":
        return "superseded"
    if not latest_version:
        return None
    if norm_no(latest_version) != norm_no(requested_no):
        return "new_version"
    return "no_change"


def looks_like_captcha(body: Any) -> bool:
    """验证码特征检测：body 显式 captcha 标记，或文本含验证码特征词。"""
    if isinstance(body, dict):
        if body.get("captcha"):
            return True
        try:
            body = json.dumps(body, ensure_ascii=False)
        except TypeError:
            body = str(body)
    if isinstance(body, str):
        low = body.lower()
        return any(marker in low for marker in ("验证码", "captcha", "checkcode"))
    return False


# ---------------------------------------------------------------- 锁定数据类
@dataclass
class ChannelResult:
    channel: str            # official_gb|web|govcn|laws_db
    found: bool = False
    captcha: bool = False   # True=需人工过点(半自动)
    change_type: str | None = None   # new_version|superseded|withdrawn|no_change|None
    legal_status: str | None = None  # effective|upcoming|superseded|withdrawn
    latest_version: str | None = None
    effective_date: str | None = None
    evidence_url: str | None = None
    raw: dict = field(default_factory=dict)


def recordable(result: ChannelResult) -> bool:
    """结果是否允许落变更表：captcha 只返回标记，绝不写库（04a INS-C-01）。"""
    return not result.captcha


# ---------------------------------------------------------------- 传输层
DEFAULT_TIMEOUT_S = 30.0  # 单号单渠道探测上界（04a INS-A-05：delay_s=31 必超时）


class CurlCffiTransport:
    """浏览器指纹默认传输（ANOM-002 canonical 修复）：curl_cffi impersonate chrome。

    openstd.samr.gov.cn / std.samr.gov.cn / flk.npc.gov.cn 按 JA3 TLS 指纹在握手期
    掐 Python 客户端（httpx 直连与走代理均 SSL UNEXPECTED_EOF）；curl_cffi 复刻
    Chrome 指纹可正常建连。fetch 契约与 HttpxTransport 一致：
    ``(status:int, body:dict|str)``，HTTP 状态不抛、异常交由 adapter._fetch 归一。

    ⚠ **重定向策略是显式参数**（2026-09-17 独立复核 HIGH）：调用方传
    ``allow_redirects=False`` 就能让这一跳**不跟随** 302——采集侧靠它堵住
    "公网 URL 302 到 169.254.169.254"的 SSRF 绕道（实测默认跟随会**真的连上去**，
    而 `is_private_url` 只在**发起前**判过一次）。
    两家 HTTP 栈的 kwarg 名不同（curl_cffi/requests 是 `allow_redirects`、httpx 是
    `follow_redirects`），**只有本模块知道这件事**，所以对外统一用 `allow_redirects`
    这个名字；默认 `True` = 既有行为不变（公告扫描依赖跟随重定向）。
    """

    def __init__(self) -> None:
        from curl_cffi import requests as cffi_requests
        self._session: Any = cffi_requests.Session(impersonate="chrome")

    def fetch(self, url: str, **kw: Any) -> tuple[int, Any]:
        timeout = kw.pop("timeout", DEFAULT_TIMEOUT_S)
        method = str(kw.pop("method", "get") or "get").lower()
        json_body = kw.pop("json", None)
        allow_redirects = bool(kw.pop("allow_redirects", True))
        if method == "post":
            resp = self._session.post(url, json=json_body, timeout=timeout,
                                      allow_redirects=allow_redirects, **kw)
        else:
            resp = self._session.get(url, timeout=timeout,
                                     allow_redirects=allow_redirects, **kw)
        try:
            body: Any = resp.json()
        except Exception:  # 非 JSON 响应 → 原文文本
            body = resp.text
        return resp.status_code, body

    def fetch_bytes(self, url: str, **kw: Any) -> tuple[int, bytes]:
        """原始字节下载（公告 PDF 存档用）：返回 (status, content)，不解析。"""
        timeout = kw.pop("timeout", DEFAULT_TIMEOUT_S)
        allow_redirects = bool(kw.pop("allow_redirects", True))
        resp = self._session.get(url, timeout=timeout,
                                 allow_redirects=allow_redirects, **kw)
        return resp.status_code, resp.content

    def fetch_page(self, url: str, **kw: Any) -> tuple[int, dict[str, str], str, bytes]:
        """取回一个**页面**，把同一个响应的四样东西一起给出：
        `(status, headers, text, raw_bytes)`。

        ## 为什么必须有它（2026-09-17 独立复核的 MEDIUM）
        `fetch()` 只回 `(status, body)` ⇒ **Content-Type 与真实字节都在那一层丢了**。
        后果是采集侧**无法判断"这是不是网页正文"**，只能拿**转换后的文本**猜：
        `application/javascript` / `text/css` / JSON 标量会被当成正文登记进材料，
        而 PNG/JPEG 的 magic 也永远认不出（非 ASCII 首字节已被 `errors='replace'`
        变成 U+FFFD）。四样一起给 ⇒ 判据可以落在**响应头**与**真实字节**上。

        ⚠ 这**不是**第二个 HTTP 客户端：与 `fetch` 同一次请求、同一个 session，
        只是把响应上本来就有的两个字段多暴露出来。重定向策略同上（`allow_redirects`）。
        """
        timeout = kw.pop("timeout", DEFAULT_TIMEOUT_S)
        allow_redirects = bool(kw.pop("allow_redirects", True))
        resp = self._session.get(url, timeout=timeout,
                                 allow_redirects=allow_redirects, **kw)
        return resp.status_code, {str(k).lower(): str(v) for k, v in resp.headers.items()}, \
            resp.text, resp.content


class HttpxTransport:
    """回退真实传输（curl_cffi 不可导入时兜底；离线单测不触达）。

    重定向策略与 `CurlCffiTransport` 同款（统一收 `allow_redirects`，这里翻译成
    httpx 的 `follow_redirects`）——见那边的说明。
    """

    def fetch(self, url: str, **kw: Any) -> tuple[int, Any]:
        import httpx
        timeout = kw.pop("timeout", DEFAULT_TIMEOUT_S)
        method = str(kw.pop("method", "get") or "get").lower()
        json_body = kw.pop("json", None)
        allow_redirects = bool(kw.pop("allow_redirects", True))
        if method == "post":
            resp = httpx.post(url, json=json_body, timeout=timeout,
                              follow_redirects=allow_redirects, **kw)
        else:
            resp = httpx.get(url, timeout=timeout,
                             follow_redirects=allow_redirects, **kw)
        try:
            body: Any = resp.json()
        except Exception:
            body = resp.text
        return resp.status_code, body

    def fetch_bytes(self, url: str, **kw: Any) -> tuple[int, bytes]:
        """原始字节下载（公告 PDF 存档用）。"""
        import httpx
        timeout = kw.pop("timeout", DEFAULT_TIMEOUT_S)
        allow_redirects = bool(kw.pop("allow_redirects", True))
        resp = httpx.get(url, timeout=timeout,
                         follow_redirects=allow_redirects, **kw)
        return resp.status_code, resp.content

    def fetch_page(self, url: str, **kw: Any) -> tuple[int, dict[str, str], str, bytes]:
        """同 `CurlCffiTransport.fetch_page`（契约一致：`(status, headers, text, raw)`）。"""
        import httpx
        timeout = kw.pop("timeout", DEFAULT_TIMEOUT_S)
        allow_redirects = bool(kw.pop("allow_redirects", True))
        resp = httpx.get(url, timeout=timeout,
                         follow_redirects=allow_redirects, **kw)
        return resp.status_code, {str(k).lower(): str(v) for k, v in resp.headers.items()}, \
            resp.text, resp.content


def httpx_usable() -> tuple[bool, str]:
    """httpx 在这台机器上**构造**得起来吗？（返回 `(可用, 原因)`）

    ## 为什么要这条自检（2026-09-18 实测，§11.0 R3d 的 G27）
    `default_transport()` 在 `curl_cffi` 不可用时**只打一条 WARN** 就回退到 httpx。
    但本机实测：`NO_PROXY` 里含 `[::1]`，**httpx 0.28.1 连 `Client()` 都构造不出来**
    （`InvalidURL: Invalid port: ':1]'`）⇒ 那种环境下**每个渠道都会失败**，
    而现场只表现为"每条都失败"——这是最难查的一类故障（症状离原因很远）。
    所以回退时先自检：**能用就 WARN，不能用就 ERROR 并点名两个栈**。
    刻意**不抛**：抛出去会让引擎起不来；巡检照常跑，只是错误原因会**当场写进日志**。
    """
    try:
        import httpx
    except ImportError as e:
        return False, f"httpx 未安装：{type(e).__name__}: {e}"
    try:
        # ⚠ 就是这一行会失败：构造 Client 时 httpx 会解析 NO_PROXY/HTTP_PROXY 环境变量。
        httpx.Client().close()
        return True, ""
    except Exception as e:  # noqa: BLE001 —— 自检要把**任何**异常翻成一句人话
        return False, f"{type(e).__name__}: {e}"


def default_transport():
    """默认 transport 工厂：curl_cffi 可导入则优先（TLS 指纹模拟），
    否则回退现有 httpx 实现（pipeline/08 ANOM-002 §修复方案1）——**并先自检 httpx 是否真能用**。"""
    try:
        return CurlCffiTransport()
    except ImportError as exc:
        ok, why = httpx_usable()
        if ok:
            upd_log("-", "transport.init", "WARN",
                    "curl_cffi_unavailable_fallback_httpx "
                    "(gov TLS-fingerprint WAF sites may stay blocked)",
                    error=f"{type(exc).__name__}: {exc}")
        else:
            upd_log("-", "transport.init", "ERROR",
                    "both_transports_unusable_httpx_construction_failed "
                    "(curl_cffi 缺失 **且** httpx 构造失败 ⇒ 所有渠道都会失败；"
                    "常见成因：NO_PROXY/HTTP_PROXY 写法让 httpx 解析不了，"
                    "例如 NO_PROXY 含 `[::1]`——改成 `::1` 即可)",
                    error=f"curl_cffi: {type(exc).__name__}: {exc} / httpx: {why}")
        return HttpxTransport()


# ---------------------------------------------------------------- 锁定抽象基类
class ChannelAdapter(ABC):
    """渠道适配器抽象：probe(standard_no) -> ChannelResult（接口冻结）。"""

    name: str = "base"
    #: TRACE=batch_id 由 inspector 注入；独立调用时段占位
    trace_id: str = "-"

    def __init__(self, transport=None):  # noqa: ANN001 — 接口签名冻结（Any transport）
        self.transport = transport if transport is not None else default_transport()

    @abstractmethod
    def probe(self, standard_no: str, standard_name: str = "") -> ChannelResult:
        """探测单个标准号的最新官方状态。实现必须：确定性、离线可测、异常归一。"""

    # -------------------------------------------------------------- 内部工具
    def _fetch(self, url: str, **kw: Any) -> tuple[int, Any]:
        """transport 归一调用：超时/异常统一翻成 UpdateError（UPD-1xxx），HTTP 状态不抛。"""
        kw.setdefault("timeout", DEFAULT_TIMEOUT_S)
        try:
            return self.transport.fetch(url, **kw)
        except TimeoutError as e:  # mock 与内置超时
            raise UpdateError(f"channel_timeout: {url}", code=UPD_CHANNEL_TIMEOUT) from e
        except Exception as e:  # httpx.TimeoutException 等：按类名识别超时
            if "timeout" in type(e).__name__.lower():
                raise UpdateError(f"channel_timeout: {url}", code=UPD_CHANNEL_TIMEOUT) from e
            raise UpdateError(f"channel_unreachable: {url} ({type(e).__name__}: {e})",
                              code=UPD_CHANNEL_ERROR) from e

    def _log_probe(self, t0: float, standard_no: str, result: ChannelResult) -> ChannelResult:
        """每次探测必落一条结构化日志（含耗时 ms，pipeline/05 §1）。"""
        duration_ms = round((perf_counter() - t0) * 1000, 1)
        span = f"channel.{self.name}"
        if result.captcha:
            upd_log(self.trace_id, span, "WARN", "captcha_required",
                    standard_no=standard_no, duration_ms=duration_ms)
        else:
            upd_log(self.trace_id, span, "INFO", "probe_done",
                    standard_no=standard_no, duration_ms=duration_ms,
                    found=int(result.found), change_type=result.change_type,
                    legal_status=result.legal_status)
        return result

    def _miss(self, t0: float, standard_no: str, http_status: int,
              note: str | None = None) -> ChannelResult:
        """统一未命中出口：HTTP 非 200 不抛错，交由降级链决策。"""
        raw: dict[str, Any] = {"http": http_status}
        if note:
            raw["note"] = note
        return self._log_probe(t0, standard_no,
                               ChannelResult(channel=self.name, found=False, raw=raw))
