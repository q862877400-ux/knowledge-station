"""Jev（TypeSafe System One）结构化判断客户端（2026-09-24，业主授权接入）。

## 它是什么、不是什么

Jev **不是**聊天模型：给它一段 state + 一组**带类型的问题**，它回**结构化答案 + 概率**，
不写字、不解释。引擎用它做那些"要读一段文字、拿一个带把握的答案"的判断。

官方三条硬约束（照做，别自己发明）：
1. **Noul 没有 confidence**（只有 Choice/Score 有）。Noul≈0.5 才是"真没把握"，
   Noul=0.12 是"笃定的否"。**要门控就得用 Choice/Score 的 confidence**。
2. **每个 Noul 必须写 `criteria`**（什么算 yes / 什么算 no）。不写＝让模型自己猜"你说的
   必遵守是什么意思"——本项目 2026-09-24 实测：不写 criteria 时"征求意见稿"被 0.12 判死。
3. **state 只放这个问题需要的东西**。官方锯齿表第 5 条：state 塞满无关细节会拉低准确率
   （本项目实测：加 600 字正文后准确率反而从 13/18 掉到 8/18）。

## 官方明示的局限（我们据以设边界）
- **英文最好、其他语言（含中文）当前较弱** ⇒ 阈值必须在我们自己的内容上量过再定，
  且 `jev_guard` 用一组中文回归样本持续盯（见 `tests/test_jev_guard.py`）。
- **不算数、不比日期**（锯齿表 #2/#3）⇒ 本模块只问语义判断；日期/计数留在调用方代码里。
- **typed output 保证接口、不保证为真** ⇒ 低置信一律交人，不自动落库。

## 凭据与出站
- Key 走 `config._read_secret()`（唯一入口：env → DPAPI 加密存储 → 旧系统层只读兼容），
  存 `KS_JEV_API_KEY`，**与 `KS_LLM_API_KEY` 并列**。客户端/host 侧永不接触。
- 每次调用经 `egress_audit.record_egress()` 落库可审计（引擎既有纪律：所有云调用必须可审计）。
- **失败一律降级、不抛给主链路**：`JevUnavailable`。调用方（Jev 护栏）拿不到判断时退回
  词表，绝不因为外部服务挂了就让合规护航整体失效。
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

import requests

from src.core.config import get_settings
from src.core.llm.egress_audit import record_egress

logger = logging.getLogger(__name__)

#: 官方端点（System One 唯一入口）
JEV_ENDPOINT = "https://api.typesafe.ai/v1/systemone"
#: **钉版本号**，不用 `jev-latest` 别名：官方明示"调过置信度阈值就别用会漂移的别名"
#: （别名会随新发布移动，阈值就名不副实了）。升级模型 = 重新量阈值 + 改这一行。
JEV_MODEL = "jev-1.13.0"

#: 单次调用超时（秒）。实测 p50 约 0.25~0.5s；留足余量但**必须有上限**——
#: 这是每条用户消息都可能走一次的路径，不能让外部服务拖住输入。
JEV_TIMEOUT_S = 2.0
#: 连续失败多少次后短路（熔断），避免"每条消息都等一次超时"。冷却 60s 后自动恢复。
JEV_BREAKER_FAILS = 3
JEV_BREAKER_COOLDOWN_S = 60.0

_fail_streak = 0
_opened_at = 0.0


class JevUnavailable(RuntimeError):
    """Jev 不可用（未配 Key / 熔断中 / 网络失败 / 响应不合契约）。

    调用方**必须**捕获并降级——它绝不该顺着冒泡到用户界面。
    """


def _read_key() -> str:
    """Jev Key：与 LLM Key 同一个唯一入口（`KS_JEV_API_KEY`）。"""
    from src.core.config import _read_secret
    return _read_secret("KS_JEV_API_KEY", (), "")


def breaker_open(now: float | None = None) -> bool:
    """熔断是否开着（**上次熔断**后还在冷却期内 ⇒ 跳过调用）。

    ⚠ 判据用 `_opened_at`（"上次熔断的时刻"）而不是 `_fail_streak >= 阈值`：
    后者会让**冷却期一过就永远失去熔断**（连续失败数不会自己降下来，而 `opened_at`
    也不再刷新 ⇒ 之后再失败多少次都开不了熔断，每条消息都去等一次超时）。
    独立复核 2026-09-24 实测：冷却 60s 后第 4 次失败，`breaker_open` 仍为 False。
    """
    now = time.monotonic() if now is None else now
    if _opened_at <= 0.0:
        return False
    return (now - _opened_at) < JEV_BREAKER_COOLDOWN_S


def _note_ok() -> None:
    global _fail_streak, _opened_at
    _fail_streak = 0
    _opened_at = 0.0            # 成功 ⇒ 熔断窗口关闭（下次失败从头计）


def _note_fail() -> None:
    global _fail_streak, _opened_at
    _fail_streak += 1
    if _fail_streak >= JEV_BREAKER_FAILS and not breaker_open():
        # 只在"当前没在熔断"时开新窗口 ⇒ 熔断期间进来的失败不会把冷却期无限往后推，
        # 而冷却一过的下一次失败会**重新计时**（这正是上一版的漏）。
        _opened_at = time.monotonic()
        logger.warning("jev: 连续失败 %d 次，熔断 %.0fs（合规护栏退回词表）",
                       _fail_streak, JEV_BREAKER_COOLDOWN_S)


def reset_breaker_for_tests() -> None:
    """测试用：清熔断状态（生产路径不调用）。"""
    global _fail_streak, _opened_at
    _fail_streak, _opened_at = 0, 0.0


def system_one(state: Any, questions: dict[str, Any], *,
               service: str = "jev", audit: bool = True) -> dict[str, Any]:
    """问一组类型化问题，返回 `{"answers": {...}, "model": ..., "usage": {...}}`。

    `questions` 必须是官方三种题型之一（`noul` / `choice` / `score`）的 dict；
    每个 noul 都应带 `criteria`。本函数**不解释、不纠正**——判据是调用方的责任。

    ⚠ **每次外发都审计**（成功/HTTP 失败/异常 alike，见 `_record_egress`）——审计本身
      **会写库**（`debug_dump`），源码里不写"只读"这类不准确的话。
    ⚠ 回包经 `_validate_body` 逐题校验：答案键必须与提问一一对应、数值必须在 0~1（排除 bool）、
      `model` 必须是我们钉的版本号（别名会漂，阈值是按该版本量的）。不合格 ⇒ `JevUnavailable`
      （调用方降级），**不把坏答案当"判定为不触发"**。
    """
    key = _read_key()
    if not key:
        raise JevUnavailable("KS_JEV_API_KEY 未配置")
    if breaker_open():
        raise JevUnavailable("jev 熔断中（连续失败），本次不调用")
    payload = {"state": state, "model": JEV_MODEL, "questions": questions}
    t0 = time.monotonic()
    try:
        r = requests.post(
            JEV_ENDPOINT,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload, timeout=JEV_TIMEOUT_S,
        )
        if r.status_code != 200:
            _record_egress(service, payload, None, f"http_{r.status_code}", t0, audit)
            raise JevUnavailable(f"jev HTTP {r.status_code}: {r.text[:120]}")
        body = r.json()
        _validate_body(body, set(questions), _score_levels(questions))
    except JevUnavailable:
        _note_fail()
        raise
    except Exception as exc:  # noqa: BLE001 — 任何网络/解析异常一律降级，不外泄
        _note_fail()
        _record_egress(service, payload, None, f"exception_{type(exc).__name__}", t0, audit)
        raise JevUnavailable(f"jev 调用失败: {type(exc).__name__}") from exc
    _note_ok()
    _record_egress(service, payload, body, "ok", t0, audit)
    return body


def _score_levels(questions: dict[str, Any]) -> dict[str, int]:
    """从提问里取出每道 Score 题的**档位数**（`criteria` 列表长度），供回包值域校验用。"""
    out: dict[str, int] = {}
    for qid, q in questions.items():
        if isinstance(q, dict) and q.get("type") == "score":
            levels = q.get("criteria")
            if isinstance(levels, list) and levels:
                out[qid] = len(levels)
    return out


def _validate_body(body: Any, question_ids: set[str], score_levels: dict[str, int] | None = None) -> None:
    """**逐题验契约**（独立复核 2026-09-24 MED-2：原先只查 `answers` 存在，于是
    `True`（Python bool 是 int 子类）、`1.1`、以及回包 `model` 漂成别名都算"合法"）。

    - 答案键必须与请求的题一一对应（少一题不许当成功——调用方会当成"全判过了"）；
    - `noul` 与 `confidence` 必须在 **0~1 闭区间**且是真 float/int（**排除 bool**）；
    - ⚠ **`score` 不是 0~1**！官方 Score 是**有序量表**，回的是档位下标（0..档数−1，可为小数）。
      我第一版把三个字段一起按 0~1 判 ⇒ **真机第一轮就把自己锁死**（4 题里带 Score 的那次
      全部被判非法，隐性的 6 条全落熔断窗内——实测 miss 6/10，2026-09-24 17:0x）。
      `score_levels` 传各题的档位数时按 `[0, 档数−1]` 判；没传就只查它是数值。
    - `model` 必须是我们钉的那个版本号：别名会随官方发布漂移，而阈值是按该版本量的。
    """
    if not isinstance(body, dict):
        raise JevUnavailable("jev 响应不是对象")
    got_model = str(body.get("model") or "")
    if got_model != JEV_MODEL:
        raise JevUnavailable(f"jev 模型不匹配：回包 {got_model!r} ≠ 钉住的 {JEV_MODEL!r}")
    answers = body.get("answers")
    if not isinstance(answers, dict) or set(answers) != question_ids:
        raise JevUnavailable(
            f"jev 答案键与提问不一致：回 {sorted(answers) if isinstance(answers, dict) else answers}"
            f" / 问 {sorted(question_ids)}")
    for qid, ans in answers.items():
        if not isinstance(ans, dict):
            raise JevUnavailable(f"jev 答案 {qid} 不是对象")
        # Score 题的档位数（从提问里取；没有就退化成"只要是数值"）
        levels = (score_levels or {}).get(qid)
        for field in ("noul", "score", "confidence"):
            if field not in ans:
                continue
            val = ans[field]
            if isinstance(val, bool) or not isinstance(val, (int, float)):
                raise JevUnavailable(f"jev 答案 {qid}.{field} 类型非法：{val!r}")
            val = float(val)
            if field == "score" and levels:
                if not 0.0 <= val <= float(levels - 1):
                    raise JevUnavailable(
                        f"jev 答案 {qid}.score 越界：{val}（量表 {levels} 档 ⇒ 合法 [0, "
                        f"{levels - 1}]）")
            elif not 0.0 <= val <= 1.0:
                raise JevUnavailable(f"jev 答案 {qid}.{field} 越界：{val!r}")


def _record_egress(service: str, payload: dict[str, Any], body: Any,
                   outcome: str, t0: float, audit: bool) -> None:
    """登记**每一次**外发——成功、HTTP 失败、异常都登记（独立复核 2026-09-24 MED-6：
    原先只有成功路径登记 ⇒ "HTTP 503 那次外发"在审计里查不到；而 `record_egress`
    **会写库**（`debug_dump` 表并清旧行），所以源码里原先"只读"的说法是错的，已删）。

    ⚠ 审计写失败**不反噬**主链路：判断结果比审计更重要（但会 warning 留痕）。
    """
    if not audit:
        return
    try:
        record_egress(service=service, endpoint=JEV_ENDPOINT, payload=payload,
                      response_meta={"outcome": outcome,
                                     "elapsed_ms": int((time.monotonic() - t0) * 1000),
                                     "model": (body or {}).get("model")
                                     if isinstance(body, dict) else None,
                                     "usage": (body or {}).get("usage")
                                     if isinstance(body, dict) else None},
                      query=json.dumps(payload.get("state"), ensure_ascii=False,
                                       default=str)[:500],
                      prompt_preview=f"Jev 系统一请求 outcome={outcome}")
    except Exception:  # noqa: BLE001 — 审计写失败不反噬主链路
        logger.warning("jev: egress 审计写入失败（不影响判断结果）", exc_info=True)


# ---------------------------------------------------------------------------
# 题型构造（薄封装：把官方字段名固定在一处，调用方不手写 dict 字面量）
# ---------------------------------------------------------------------------

def noul(instructions: str, *, yes: str, no: str) -> dict[str, Any]:
    """是非题。**`yes`/`no` 必填**（criteria）——不写 criteria 是本项目踩过的坑。"""
    return {"type": "noul", "instructions": instructions,
            "criteria": {"true": yes, "false": no}}


def choice(instructions: str, criteria: dict[str, str]) -> dict[str, Any]:
    """选项题。回 `choice` + 各选项 `probabilities` + **`confidence`**（门控要用它）。"""
    return {"type": "choice", "instructions": instructions, "criteria": criteria}


def score(instructions: str, levels: list[str]) -> dict[str, Any]:
    """量表题。`levels` 从低到高；回 `score` + 分布 + `confidence`。"""
    return {"type": "score", "instructions": instructions, "criteria": levels}
