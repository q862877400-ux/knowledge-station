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
    """熔断是否开着（连续失败超阈值且还在冷却期内）。"""
    now = time.monotonic() if now is None else now
    if _fail_streak < JEV_BREAKER_FAILS:
        return False
    return (now - _opened_at) < JEV_BREAKER_COOLDOWN_S


def _note_ok() -> None:
    global _fail_streak
    _fail_streak = 0


def _note_fail() -> None:
    global _fail_streak, _opened_at
    _fail_streak += 1
    if _fail_streak == JEV_BREAKER_FAILS:
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
            raise JevUnavailable(f"jev HTTP {r.status_code}: {r.text[:120]}")
        body = r.json()
        answers = body.get("answers")
        if not isinstance(answers, dict) or not answers:
            raise JevUnavailable("jev 响应缺 answers")
    except JevUnavailable:
        _note_fail()
        raise
    except Exception as exc:  # noqa: BLE001 — 任何网络/解析异常一律降级，不外泄
        _note_fail()
        raise JevUnavailable(f"jev 调用失败: {type(exc).__name__}") from exc
    _note_ok()
    if audit:
        try:
            record_egress(service=service, endpoint=JEV_ENDPOINT,
                          payload={"model": JEV_MODEL, "state": state,
                                   "questions": questions},
                          response_meta={"model": body.get("model"),
                                         "elapsed_ms": int((time.monotonic() - t0) * 1000),
                                         "usage": body.get("usage") or {}},
                          query=json.dumps(state, ensure_ascii=False, default=str)[:500],
                          prompt_preview="Jev 系统一请求（state+questions）")
        except Exception:  # noqa: BLE001 — 审计写失败不反噬主链路
            logger.warning("jev: egress 审计写入失败（不影响判断结果）", exc_info=True)
    return body


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
