# -*- coding: utf-8 -*-
"""`unsupported_context` 回归测试（D 线"资格声明"，2026-09-16 新建）。

**它修的是什么**：`unsupported_clauses` 只给一串裸条款号，用户无法区分
「本轮证据内同一部标准的条款没被检索出来」（检索召回问题，可操作）与
「引用了本轮完全没讨论的标准」（提示词违规/编造）。两者后果完全不同。

**它刻意不做什么**（边界，测试同样锁住）：
  - **不改拦截**：证据外条款号照样进 `unsupported_clauses` 且 `is_valid=False`
    （SYSTEM_PROMPT 规则 2 是硬约束，这是"违反"而非"本库没收录"）；
  - **不查库**：核验器保持纯函数、零 IO。故附近找不到标准号时必须报 `unknown`，
    **不许猜**一个标准号出来。
"""
from __future__ import annotations

from src.core.verification.typed_verifier import verify_llm_output

#: ⚠ 条款引用必须写成**无空格**形态 `第5.2.1条`：既有 `_CITED_NUM` 的正则是
#: `第(\d+(?:\.\d+){1,4})\s*条?` —— 数字须**紧随**「第」，`\s*` 在数字与「条」之间。
#: 写成 `第 5.2.1 条` 匹配不到（本文件初版即因此 4 例全红；这是**测试写法**问题，
#: 不是被测代码问题——已核对 `test_t06.py` 的既有惯例确为无空格）。

EV_STD = "GB 30871-2022"


def _ev(num: str, std: str = EV_STD, ktype: str = "rule") -> dict:
    return {
        "clause_revision_id": f"clrev_{num}",
        "clause_number": num,
        "standard_no": std,
        "knowledge_type": ktype,
        "modality": "应",
        "content_text": "应按规定执行。",
        "exception": None,
        "subject": None,
    }


def test_same_standard_not_retrieved_is_actionable():
    """情形 a：引用了**同一部标准**里未被检索的条款 → 应报"检索未召回"。

    这正是"资格声明"要区分的第一种情形：可操作（去补检索），而非编造。
    """
    out = f"按 {EV_STD} 第5.2.1条执行。另外 {EV_STD} 第9.9.9条也要求。"
    r = verify_llm_output(out, [_ev("5.2.1")])
    assert "9.9.9" in r.unsupported_clauses, r.unsupported_clauses
    ctx = {c["clause_number"]: c for c in r.unsupported_context}
    assert "9.9.9" in ctx, ctx
    assert ctx["9.9.9"]["verdict"] == "same_standard_not_retrieved", ctx["9.9.9"]
    assert ctx["9.9.9"]["standard_no"] is not None
    assert "未" in ctx["9.9.9"]["reason"] or "检索" in ctx["9.9.9"]["reason"]


def test_outside_evidence_standard_is_distinguished():
    """情形 b：引用**本轮未讨论**的标准 → 应报 `outside_evidence_standard`。

    与情形 a 的处置不同（这是提示词越界/可能编造，不是召回问题）。
    """
    out = "按 GB 50016-2014 第3.1.2条执行。"
    r = verify_llm_output(out, [_ev("5.2.1")])
    assert "3.1.2" in r.unsupported_clauses
    ctx = {c["clause_number"]: c for c in r.unsupported_context}
    assert ctx["3.1.2"]["verdict"] == "outside_evidence_standard", ctx["3.1.2"]


def test_no_standard_nearby_reports_unknown_never_guesses():
    """情形 c：附近没有标准号 → 必须报 `unknown`，**不得猜**。

    这条是"不许编造"的护栏：分类器自己也不许编造标准号。
    """
    out = "依据第9.9.9条的要求。"
    r = verify_llm_output(out, [_ev("5.2.1")])
    assert "9.9.9" in r.unsupported_clauses
    ctx = {c["clause_number"]: c for c in r.unsupported_context}
    assert ctx["9.9.9"]["verdict"] == "unknown", ctx["9.9.9"]
    assert ctx["9.9.9"]["standard_no"] is None, "不得猜标准号"


def test_evidence_clause_produces_no_context_entry():
    """反向对照：证据**内**的条款号不得产生任何 context 条目（不是告警对象）。"""
    out = f"按 {EV_STD} 第5.2.3条执行。"
    r = verify_llm_output(out, [_ev("5.2.3")])
    assert r.unsupported_clauses == [], r.unsupported_clauses
    assert r.unsupported_context == [], r.unsupported_context


def test_context_length_matches_unsupported_length():
    """结构不变量：两条列表**一一对应**（消费方可以按下标配对）。"""
    out = (f"按 {EV_STD} 第1.1.1条、GB 50016-2014 第3.1.2条"
           f"以及第9.9.9条执行。")
    r = verify_llm_output(out, [_ev("5.2.1")])
    assert len(r.unsupported_context) == len(r.unsupported_clauses), (
        r.unsupported_clauses, r.unsupported_context)
    assert ([c["clause_number"] for c in r.unsupported_context]
            == list(r.unsupported_clauses))


def test_blocking_behaviour_unchanged():
    """**边界**：分类只增信息，**不放行**——证据外条款仍使 is_valid=False。

    （若这条红了，说明"资格声明"被误实现成"宽松放行"，那是方向性错误：
    `unsupported_clauses` 记的是对规则 2 的违反，不是"本库没收录"。）
    """
    out = f"按 {EV_STD} 第9.9.9条执行。"
    r = verify_llm_output(out, [_ev("5.2.1")])
    assert r.is_valid is False, "证据外条款号仍必须拦截"
    assert r.unsupported_clauses == ["9.9.9"]
