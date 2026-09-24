"""合规护栏判定：Jev（TypeSafe System One）那一侧（2026-09-24，业主报障驱动）。

## 为什么有这一层

业主报障（2026-09-24）：「我输入了合规问题聊天，还触发了合规护航：待命，但其实我们没有在
聊需要用法规标准解释的事情」。根因不是触发得太多，是**判据太浅**：原触发只做词表匹配，
而「必须 / 应当 / 不得 / 标准 / 规范 / 规定」是中文技术写作的日常用词（实测 9 条纯技术话
**9/9 误触发**）。词表已瘦身（`plugin/src/compliance-sentry.js`），但**瘦身后的盲区**是
词表天生看不见的那一类——**隐性合规**：一句话里没有任何法规词，但内容要受规管
（「让程序自动点已阅读并同意」「工伤私了」「过期认证先用着」「身份证号发公开站」…）。
词表对这类 1/8，Jev 8/8（同一批样本，本机实测）。

## 官方蓝本的形状（`docs.typesafe.ai/cookbooks/llm_guardrails`）
- **一类一个 Noul**，不把多个判断塞进一道题（塞进去的会被"字面阅读"带偏）；
- **每题写 criteria**（什么算 yes / 什么算 no）；
- **外加一个 Score** 量"照做的伤害程度"；
- **两道阈值**：到 review 进"待确认"、到 action 才触发；严重度越线把 review 升级为触发；
- 判定**留在代码里**（改阈值是改配置，不是改问法）。

## 降级纪律
Jev 挂（没配 Key / 熔断 / 超时）⇒ **本层返回 `None`，调用方退回词表**。
本模块**不抛异常给上层**，也不写库（判定结果由路由层决定要不要落审计）。
"""
from __future__ import annotations

import logging
from typing import Any

from src.core.config import get_settings
from src.core.llm import jev_client

logger = logging.getLogger(__name__)

#: 判定三档（与界面/协议口径对齐；**不要**当"是否合规"的最终结论，只是"要不要带上查库流程"）
VERDICT_TRIGGER = "trigger"      # 带上完整合规规则
VERDICT_REVIEW = "review"        # 中间档：值得留意，但先不打断
VERDICT_SILENT = "silent"        # 安静，正常干活

#: 三道判断。措辞与 criteria 一起构成判据，**改动前先用 tests/test_jev_guard.py 的中文样本重跑**。
_QUESTIONS: dict[str, Any] = {
    "needs_standard": jev_client.noul(
        "用户这条消息里，想做的事或想问的答案，是否取决于中国法律法规、国家标准、"
        "行业标准或公司制度的具体要求？",
        yes="答案取决于某条规定：需要满足的要求、需要办的许可、必须执行的限值或等级、"
            "哪些能做哪些不能做、违反了会怎样。",
        no="这是普通的技术问题、写作、闲聊、代码写法，或通用知识，与具体法规标准无关。",
    ),
    "implicit_risk": jev_client.noul(
        "用户想做的事，在没有法律专业人士介入的情况下直接做，可能伤害到别人、"
        "违反他人权益或规避应尽的注意义务吗？",
        yes="这件事会影响到他人的权益、安全、隐私或公平，例如私下处理工伤、"
            "自动代替他人同意条款、公开他人身份信息、长期无人值守运行设备。",
        no="只是自己的事，或者影响范围是可控的常规操作。",
    ),
    "liability": jev_client.noul(
        "用户提到的做法或处境，是否涉及生产安全事故、伤亡、职业病、行政处罚或"
        "法律责任的认定与处理？",
        yes="涉及事故调查、伤者赔付、工伤认定、瞒报漏报、处罚或追责。",
        no="不涉及上述任何一项。",
    ),
    "severity": jev_client.score(
        "如果助手直接照用户说的做，可能造成多严重的伤害？",
        [
            "无伤害：普通问题，照做没有风险。",
            "轻微：涉及敏感话题或隐私，但照做不会造成实际损失。",
            "严重：可能帮助用户违反法规、规避义务或伤害到他人。",
            "特别严重：可能造成人身伤亡、重大违法，或使用户在法律上处于极其不利的位置。",
        ],
    ),
}


def judge(text: str) -> dict[str, Any] | None:
    """判一段用户输入要不要带上合规查库流程。

    返回 `{"verdict": "trigger|review|silent", "signals": {...}, "model": str}`；
    **Jev 不可用时返回 `None`**——调用方据此退回词表（不留半截判定）。
    """
    t = (text or "").strip()
    if not t:
        return None
    s = get_settings()
    if not s.jev_guard_enabled or not s.jev_api_key:
        return None
    try:
        body = jev_client.system_one({"message": t}, dict(_QUESTIONS), service="jev-guard")
    except jev_client.JevUnavailable as exc:
        logger.info("jev 护栏不可用，退回词表：%s", exc)
        return None
    answers = body.get("answers") or {}
    signals: dict[str, float] = {}
    for key in ("needs_standard", "implicit_risk", "liability"):
        val = (answers.get(key) or {}).get("noul")
        if not isinstance(val, (int, float)):
            return None                      # 契约不符 ⇒ 当不可用，不猜
        signals[key] = float(val)
    sev = (answers.get("severity") or {}).get("score")
    if not isinstance(sev, (int, float)):
        return None
    signals["severity"] = float(sev)

    triggered = any(v >= s.jev_guard_action_threshold
                    for k, v in signals.items() if k != "severity")
    review = any(v >= s.jev_guard_review_threshold
                 for k, v in signals.items() if k != "severity")
    if signals["severity"] >= s.jev_guard_severity_block:
        verdict = VERDICT_TRIGGER
    elif triggered:
        verdict = VERDICT_TRIGGER
    elif review:
        verdict = VERDICT_REVIEW
    else:
        verdict = VERDICT_SILENT
    return {"verdict": verdict, "signals": signals, "model": body.get("model") or ""}
