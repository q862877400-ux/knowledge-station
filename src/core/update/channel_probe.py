"""渠道健康探针（§11.0 R3）：把"这个渠道今天还活着吗"变成**可实测、可落库**的一件事。

## 为什么必须有语义探针（而不是只看 HTTP 状态码）
R1 的 G14 是实测证据：应急管理部标准页 HTTP 200 但**响应体只有 465 字节**（正文仅标题）、
`bzw.com.cn` 列表页正文写着"当前第0页，每页0条，共0条"（JS 未执行）、住建部/ccsa/cesa 是
JS 空壳、北京市地标查询后端**502 死链**。⇒ 只用状态码判活，会让**零产出在上线后才暴露**，
而业主的诉求恰恰是"前端能看到有效性、方便人工维护"。
所以判据是：**HTTP 通 + 页面里真的出现我们期望的锚点**，否则记 `suspicious`。

## 与适配器能力的分工（**两根轴，不许互相顶替**）
- 本模块（`state`）：**渠道（站点/接口）本身**是否可用、形态是否还是我们以为的那样；
- 台账的 `wiring`：**我们的适配器**能不能解析它（R1 的 G6：`web`/`govcn` 的适配器只解 mock 的 dict）。
  一个站点可以"活着"而我们的解析器是坏的；也可以"适配器对但站点今天挂了"。
  面板必须两列都显示——只显示一列就会给出错误结论。

## 失败要**分级**（面板上"不可抓"必须带原因码，人工才知道该等它修复还是该换渠道）
`blocked_by_waf`（403/412）· `rate_limited`（429，**判可疑不判死**：稍后再来即可）·
`endpoint_gone`（404/410，含"迁移了"）· `server_error`（5xx）· `timeout` · `transport_error` ·
`http_<n>` · `probe_no_anchor`（200 但没有文本锚点）· `probe_too_few_links`（200 但页面里
**没有内容链接**——R5a 实测应急部频道页 471 字节 0 链接的 JS 壳形态，R6a 又批量发现 12 条同形态）。

## 期望值可叠加（R6）
`expect`（文本锚点）与 `min_links`（HTML 链接数下限）可以**同时配**，任一不满足即不算通过：
它们回答同一问题的两个侧面——"还是那张页面吗"与"内容真的发出来了吗（还是只有壳）"。
只配 `url` 不配任何期望 = **只探连通性**，结果记 `unknown`（不许当成通过）。

## 目标表要**逐字段校验**（`load_targets` → `_validate_target`，独立复核 b28 的发现）
`probe_channel` 的"不抛异常"契约只在**经校验的目标**上成立；配置错误（target 不是对象、
`expect=123`、`method=delete`、`form` 不是对象……）必须在**读表时**就报出来。
⛔ 尤其禁止 `expect=""`：`"" in body_text` **恒真** ⇒ 连空正文都会被判 `ok`（假绿）；
要"只探连通性"就**省略** `expect`，而不是给它空串。
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from src.core.storage import channel_repo as cr

#: 探针目标表（url / method / json|form / expect / evidence）
PROBES_PATH = Path(__file__).resolve().parent / "channel_probes.json"

#: 单次探测超时（渠道台账是"体检"，不是取数：宁可快失败，也别拖住面板）
PROBE_TIMEOUT_S = 20.0

#: 响应体截断长度（落进证据里给人看；不存整页）
BODY_HEAD = 400

#: 链接计数（§11.0 R6 的 `min_links` 判据用）。大小写不敏感、容忍 `<a\n` 这种换行写法。
_LINK_RE = re.compile(r"<a[\s>]", re.I)


def _count_links(text: str) -> int:
    """数 HTML 里 `<a>` 标签的个数（R6 的"JS 空壳"判据）。

    ## 为什么要这条判据（实测，§11.0 R5a）
    应急管理部「法律法规标准」频道页 **HTTP 200、正文只有 471 字节、链接数 0**——
    它是纯 JS 壳（内容靠 XHR 填）。只看状态码、甚至只看 `<title>` 都会判成"健康"，
    而真相是**这里什么都抓不到**。R6a 批量实测又发现 12 条渠道是同一形态。
    """
    return len(_LINK_RE.findall(text or ""))


#: 允许的请求方法（其它一律读表即拒——探针只做"看一眼"，不需要更多动词）
_VALID_METHODS = ("get", "post")


def _validate_target(cid: str, target: Any) -> None:
    """校验**一条**目标（读表时一次性做掉；`probe_channel` 的"不抛"契约以此为前提）。

    ## 为什么必须在这里校验（独立复核 b28 的发现，2026-09-18）
    复核员实测：原先只校验 `min_links` ⇒ 把 target 写成**字符串**能静默过表，
    随后 `probe_channel` 抛 `AttributeError`；`expect=123` 抛 `TypeError`。
    也就是说"探针不抛异常"当时**只对恰好写对的目标成立**——配置错误会伪装成运行时崩溃。
    还有一条更隐蔽的：`expect=""` 时 `"" in body_text` **恒真** ⇒ 连空正文都判 `ok`（假绿）。
    所以这里逐字段校验，**空 `expect` 直接拒**（要"只探连通性"就**别写** expect）。
    """
    where = f"channel_id={cid}"
    if not isinstance(target, dict):
        raise ValueError(f"探针目标必须是对象（{where}）：{type(target).__name__}")
    url = target.get("url")
    if not isinstance(url, str) or not url.startswith("http"):
        raise ValueError(f"探针目标缺 http(s) url（{where}）：{url!r}")
    method = target.get("method", "get")
    if not isinstance(method, str) or method.lower() not in _VALID_METHODS:
        raise ValueError(f"method 只能是 {'/'.join(_VALID_METHODS)}（{where}）：{method!r}")
    expect = target.get("expect")
    if expect is not None and (not isinstance(expect, str) or not expect.strip()):
        raise ValueError(
            f"expect 必须是非空字符串，或**省略**它（{where}）：{expect!r}——"
            "空串会被 `'' in body` 判成恒真（假绿）；只想探连通性就别写 expect")
    v = target.get("min_links")
    if v is not None:
        if isinstance(v, bool) or not isinstance(v, int) or v < 1:
            raise ValueError(f"min_links 必须是 ≥1 的整数（{where}）：{v!r}")
    for key in ("form", "json", "headers"):
        payload = target.get(key)
        if payload is not None and not isinstance(payload, dict):
            raise ValueError(f"{key} 必须是对象（{where}）：{type(payload).__name__}")


def load_targets(path: Path | None = None) -> dict[str, dict[str, Any]]:
    """读探针目标表；缺 `targets` 键 → 抛 ValueError（不静默空跑）。

    每条目标都过 `_validate_target`：**配置错误必须在读表时响亮地报出来**，
    而不是留到探测时被吞掉或伪装成运行时崩溃（`probe_channel` 的契约是"探针不抛异常"）。
    """
    p = path or PROBES_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    targets = data.get("targets")
    if not isinstance(targets, dict):
        raise ValueError(f"探针目标表格式不对（缺 targets 对象）: {p}")
    for cid, target in targets.items():
        _validate_target(cid, target)
    return targets


def _classify(status: int, body_text: str, expect: str | None, *,
              min_links: int = 0) -> tuple[str, str | None, str | None]:
    """(state, error_code, error_message)。判据集中在这一处，便于用例穷举。

    ⚠ **"HTTP 200 ≠ 有数据"在 JSON 接口上同样成立**（dry-run 实测）：
    `flk` 检索接口在请求体不对时回 **HTTP 200 + `{"msg":"系统异常","code":500}`**，
    `dbba` 在参数不对时回 **HTTP 200 + `{"total":0,"records":[]}`**。
    只看状态码会把这两种都判成"渠道健康"——所以这里**先看正文里的失败信号**，再看锚点。

    期望值可以**叠加**（R6）：`expect`（文本锚点）与 `min_links`（HTML 链接数下限）。
    两个都配时，**任一不满足即不算通过**——因为它们在回答同一个问题的两个侧面：
    "这个页面还是我们以为的那张页面吗"（文本）与"它真的把内容发出来了还是只有壳"（链接）。
    """
    if status in (403, 412):
        return "down", "blocked_by_waf", f"HTTP {status}（WAF/反爬拒绝，非站点故障）"
    if status == 429:
        # ⚠ 429 是**限流**，不是"这条渠道死了"（R6a 实测：GitHub 上被限流的两条就是这样）。
        #   判成 down 会让业主以为要换渠道；判成 suspicious 才是"稍后再来"。
        return "suspicious", "rate_limited", "HTTP 429（限流：稍后重试即可，不代表渠道失效）"
    if status in (404, 410):
        return "down", "endpoint_gone", f"HTTP {status}（端点不存在或已迁移）"
    if status >= 500:
        return "down", "server_error", f"HTTP {status}（服务端错误）"
    if status != 200:
        return "down", f"http_{status}", f"HTTP {status}"

    # ---- 正文层的失败信号（HTTP 200 也算失败）----
    try:
        parsed = json.loads(body_text)
    except Exception:
        parsed = None
    if isinstance(parsed, dict):
        code = parsed.get("code")
        if isinstance(code, int) and code >= 400:
            return "down", "api_error", (
                f"HTTP 200 但正文报错（code={code}，msg={parsed.get('msg') or parsed.get('message')!r}）"
                "——先怀疑**我们的请求体**，其次才是渠道")
        msg = str(parsed.get("msg") or parsed.get("message") or "")
        if any(k in msg for k in ("系统异常", "不支持", "失败", "错误", "not supported")):
            return "down", "api_error", f"HTTP 200 但正文报错（{msg!r}）"

    # ---- 期望值（可叠加；全部满足才算通过）----
    failures: list[tuple[str, str]] = []
    if expect is not None and expect not in body_text:
        failures.append(("probe_no_anchor",
                         f"响应里没有预期锚点 {expect!r}（{len(body_text)} 字符）"))
    if min_links > 0:
        n = _count_links(body_text)
        if n < min_links:
            failures.append(("probe_too_few_links",
                             f"HTML 里只有 {n} 个链接（要求 ≥{min_links}）"))
    if expect is None and min_links <= 0:
        # 只探连通性：**如实**说"没做语义判定"，不许当成通过
        return "unknown", "no_anchor_configured", "HTTP 200，但该渠道没配语义期望（只探通了）"
    if not failures:
        return "ok", None, None
    first_code = failures[0][0]
    detail = "；".join(msg for _, msg in failures)
    return "suspicious", first_code, (
        f"HTTP 200 但{failure_kind(first_code)}：{detail}"
        "——本领域最常见的假可用（G14：页面在、内容没发出来）")


def failure_kind(code: str) -> str:
    """失败码 → 人话前缀（面板的失败原因列读的是它）。"""
    return {
        "probe_no_anchor": "响应里没有预期内容",
        "probe_too_few_links": "页面里没有内容链接（JS 空壳嫌疑）",
    }.get(code, "语义判定不通过")



def probe_channel(channel_id: str, target: dict[str, Any], *,
                  transport: Any = None) -> dict[str, Any]:
    """探一个渠道，返回 `{state, error_code, error, latency_ms, http, body_head, expect}`。

    ⚠ 不落库（调用方决定）；也**不抛**：探针的职责是把失败**分类**，不是把失败抛给上层
    （抛出去会让"一个渠道挂了"变成"整次体检没结果"）。
    ⚠ 这份"不抛"契约的**前提是目标表过了 `load_targets` 的校验**（独立复核 b28 的发现）：
    未经校验的裸 dict（如 target 写成字符串、`expect=123`）会在下面读字段时抛
    `AttributeError/TypeError`——所以**别绕过 `load_targets` 直接把任意 dict 喂进来**。
    """
    url = str(target.get("url") or "")
    if not url:
        return {"state": "unknown", "error_code": "no_probe_url",
                "error": "该渠道没配探针 URL", "latency_ms": None,
                "http": None, "body_head": "", "expect": None}
    expect = target.get("expect")
    if transport is None:
        from src.core.update.channels.base import default_transport
        transport = default_transport()
    kw: dict[str, Any] = {"timeout": PROBE_TIMEOUT_S}
    if target.get("headers"):
        kw["headers"] = target["headers"]
    if str(target.get("method", "get")).lower() == "post":
        # ⚠ `method="post"` 必须**显式**传给 transport（它按这个 kwarg 选 session.post）；
        #   忘了传 = 静默降级成 GET —— dry-run 实测就抓到过：flk 返回
        #   `{"msg":"Request method 'GET' not supported"}`、dbba 返回一张 HTML 首页，
        #   而两层都是 **HTTP 200** ⇒ 只看状态码会把"方法错了"当成"渠道健康"。
        kw["method"] = "post"
        if target.get("form") is not None:
            kw["data"] = target["form"]
        elif target.get("json") is not None:
            kw["json"] = target["json"]
    t0 = time.perf_counter()
    try:
        status, body = transport.fetch(url, **kw)
    except TimeoutError:
        return {"state": "down", "error_code": "timeout",
                "error": f"超时（>{PROBE_TIMEOUT_S:.0f}s）", "latency_ms": None,
                "http": None, "body_head": "", "expect": expect}
    except Exception as e:  # noqa: BLE001 —— 探针要把**任何**异常分类，而不是让它冒出去
        return {"state": "down", "error_code": "transport_error",
                "error": f"{type(e).__name__}: {e}", "latency_ms": None,
                "http": None, "body_head": "", "expect": expect}
    latency_ms = int((time.perf_counter() - t0) * 1000)
    text = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)
    state, code, msg = _classify(int(status), text, expect,
                                 min_links=int(target.get("min_links") or 0))
    return {"state": state, "error_code": code, "error": msg, "latency_ms": latency_ms,
            "http": int(status), "body_head": text[:BODY_HEAD], "expect": expect}


def probe_channels(ids: list[str] | None = None, *, transport: Any = None,
                   persist: bool = True, path: Path | None = None) -> dict[str, Any]:
    """批量探针：默认**只探配了目标的渠道**（没配的记 `unknown/no_probe_target`，不计失败）。

    Args:
        ids: 只探这些 channel_id（None = 全部有目标的）。
        persist: 是否把结果写进台账（`record_probe`）。dry-run 时置 False。
    Returns:
        `{probed, results:[{channel_id, state, error_code, error, latency_ms, http}], counts}`
    """
    targets = load_targets(path)
    known = {r["channel_id"] for r in cr.list_channels()}
    wanted = list(ids) if ids else [cid for cid in targets if cid in known]
    missing = [cid for cid in wanted if cid not in known]
    if missing:
        raise ValueError(f"channel_not_found: {missing}（先 seed_channels()）")

    results = []
    for cid in wanted:
        target = targets.get(cid) or {}
        out = probe_channel(cid, target, transport=transport)
        row: dict[str, Any] = {"channel_id": cid, "state": out["state"],
                               "error_code": out["error_code"], "error": out["error"],
                               "latency_ms": out["latency_ms"], "http": out["http"]}
        if persist and out["error_code"] != "no_probe_url":
            cr.record_probe(cid, state=out["state"], latency_ms=out["latency_ms"],
                            error=out["error"], error_code=out["error_code"])
        results.append(row)

    counts: dict[str, int] = {}
    for r in results:
        counts[r["state"]] = counts.get(r["state"], 0) + 1
    return {"probed": len(results), "results": results, "counts": counts,
            "without_target": sorted(known - set(targets))}
