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
`blocked_by_waf`（403/412）· `endpoint_gone`（404/410，含"迁移了"）· `server_error`（5xx）·
`timeout` · `transport_error` · `http_<n>` · `probe_no_anchor`（200 但没有锚点 = G14 那一类）。
"""
from __future__ import annotations

import json
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


def load_targets(path: Path | None = None) -> dict[str, dict[str, Any]]:
    """读探针目标表；缺 `targets` 键 → 抛 ValueError（不静默空跑）。"""
    p = path or PROBES_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    targets = data.get("targets")
    if not isinstance(targets, dict):
        raise ValueError(f"探针目标表格式不对（缺 targets 对象）: {p}")
    return targets


def _classify(status: int, body_text: str, expect: str | None) -> tuple[str, str | None, str | None]:
    """(state, error_code, error_message)。判据集中在这一处，便于用例穷举。

    ⚠ **"HTTP 200 ≠ 有数据"在 JSON 接口上同样成立**（dry-run 实测）：
    `flk` 检索接口在请求体不对时回 **HTTP 200 + `{"msg":"系统异常","code":500}`**，
    `dbba` 在参数不对时回 **HTTP 200 + `{"total":0,"records":[]}`**。
    只看状态码会把这两种都判成"渠道健康"——所以这里**先看正文里的失败信号**，再看锚点。
    """
    if status in (403, 412):
        return "down", "blocked_by_waf", f"HTTP {status}（WAF/反爬拒绝，非站点故障）"
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
    if expect is None:
        # 只探连通性：**如实**说"没做语义判定"，不许当成通过
        return "unknown", "no_anchor_configured", "HTTP 200，但该渠道没配语义锚点（只探通了）"
    if expect in body_text:
        return "ok", None, None
    return "suspicious", "probe_no_anchor", (
        f"HTTP 200 但响应里没有预期锚点 {expect!r}（{len(body_text)} 字符）"
        "——本领域最常见的假可用（G14）")


def probe_channel(channel_id: str, target: dict[str, Any], *,
                  transport: Any = None) -> dict[str, Any]:
    """探一个渠道，返回 `{state, error_code, error, latency_ms, http, body_head, expect}`。

    ⚠ 不落库（调用方决定）；也**不抛**：探针的职责是把失败**分类**，不是把失败抛给上层
    （抛出去会让"一个渠道挂了"变成"整次体检没结果"）。
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
    state, code, msg = _classify(int(status), text, expect)
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
