"""T06 测试：分型核验器三型拦截 + Prompt 构造 + SSE 核验事件（mock LLM）。"""
import json

import pytest


EV = [
    {"clause_revision_id": "c1", "clause_number": "5.2.1", "standard_no": "GB 30871-2022",
     "knowledge_type": "rule", "modality": "应",
     "content_text": "动火作业应有专人监护，作业前应清除易燃物品。",
     "exception": None, "subject": None, "page_start": 11},
    {"clause_revision_id": "c2", "clause_number": "5.2.2", "standard_no": "GB 30871-2022",
     "knowledge_type": "data", "modality": None,
     "content_text": "可燃气体浓度不大于 0.5%。",
     "exception": None, "subject": None, "page_start": 12},
    {"clause_revision_id": "c3", "clause_number": "第29条", "standard_no": "民法典",
     "knowledge_type": "legal", "modality": "应当",
     "content_text": "处理敏感个人信息应当取得个人的单独同意，但法律另有规定的除外。",
     "exception": "但法律另有规定的除外", "subject": "个人信息处理者", "page_start": 30},
]


def test_pass_through():
    from src.core.verification.typed_verifier import verify_llm_output
    out = ("根据 GB 30871-2022 第5.2.1条，动火作业应有专人监护 [引用:GB 30871-2022-5.2.1]。"
           "第5.2.2条：浓度不大于 0.5% [引用:GB 30871-2022-5.2.2]。")
    r = verify_llm_output(out, EV[:2])
    assert r.is_valid, f"正确复述应通过: {r.model_dump()}"


def test_modality_weakened_intercepted():
    from src.core.verification.typed_verifier import verify_llm_output
    out = "根据第5.2.1条，动火作业宜有专人监护 [引用:GB 30871-2022-5.2.1]。"
    r = verify_llm_output(out, EV[:1])
    assert not r.is_valid
    assert r.modality_violations[0].violation_type == "modality_weakened"
    assert r.modality_violations[0].source_modality == "应"
    assert r.modality_violations[0].output_modality == "宜"


def test_modality_strengthened_warns_not_blocks():
    from src.core.verification.typed_verifier import verify_llm_output
    out = "根据第5.2.1条，动火作业严禁无监护作业 [引用:GB 30871-2022-5.2.1]。"
    r = verify_llm_output(out, EV[:1])
    assert r.is_valid is True, "擅自加强义务=警告，不拦截"
    assert any(v.violation_type == "modality_strengthened" for v in r.modality_violations)


def test_number_tampered_intercepted():
    from src.core.verification.typed_verifier import verify_llm_output
    out = "第5.2.2条：可燃气体浓度不大于 1.0% [引用:GB 30871-2022-5.2.2]。"
    r = verify_llm_output(out, [EV[1]])
    assert not r.is_valid
    assert r.unverified_numbers and r.unverified_numbers[0]["violation"] == "number_tampered"


def test_number_pdf_space_artifact_not_flagged():
    """2026-09-06 真机回归（GB 30871-2022 §9.1 吊装分级实测）：PDF 宽字距数字
    被提取器切开（"4 0 t ≤ m ≤ 1 0 0 t"），数字内空格必须剥离归一——否则
    证据数值只剩 "0.0t"，LLM 正确输出 "40t" 被误报 number_tampered。
    防回退：真篡改（40t→4t）仍必须拦截。"""
    from src.core.verification.typed_verifier import verify_llm_output
    ev_text = "9.1 作业分级\n吊装作业按照吊物质量m不同分为：\na）一级吊装作业m > 1 0 0 t ;\nb）二级吊装作业：4 0 t ≤ m ≤ 1 0 0 t ;\nc) 三级吊装作业：m < 4 0 t"
    ev = [{"clause_revision_id": "c91", "clause_number": "9.1", "standard_no": "GB 30871-2022",
           "knowledge_type": "data", "modality": None, "content_text": ev_text, "page_start": 15}]
    # LLM 正确输出（规范化数字）→ 不应误报
    r = verify_llm_output("二级吊装作业：40t≤m≤100t [引用:GB 30871-2022-9.1]。", ev)
    assert r.is_valid, f"空格伪影被误报篡改: {r.unverified_numbers}"
    # 防回退：真篡改（把二级阈值改成 4t）仍必须拦截
    r2 = verify_llm_output("二级吊装作业：4t≤m≤100t [引用:GB 30871-2022-9.1]。", ev)
    assert not r2.is_valid and r2.unverified_numbers, "40t→4t 是真篡改，归一不能放过"


def test_mention_only_clause_not_modality_missing():
    """2026-09-06 真机回归第二轮（吊装答案引用 §5.1.1 仅作区分）：条款号出现在
    「与…无关」等对比/否定语境 = 提及而非转述要求 → 窗口无模态词不计
    modality_missing。防回退：真转述（同条款号 + 陈述句无模态词）仍必须拦截。"""
    from src.core.verification.typed_verifier import verify_llm_output
    ev = [{"clause_revision_id": "c511", "clause_number": "5.1.1", "standard_no": "GB 30871-2022",
           "knowledge_type": "rule", "modality": "应",
           "content_text": "固定动火区外的动火作业分为特级动火、一级动火和二级动火三个级别；遇节假日、公休日、夜间或其他特殊情况，动火作业应升级管理。",
           "page_start": 10},
          {"clause_revision_id": "c512", "clause_number": "5.1.2", "standard_no": "GB 30871-2022",
           "knowledge_type": "rule", "modality": None,
           "content_text": "特级动火作业：在火灾爆炸危险场所处于运行状态下的生产装置设备、管道、储罐、容器等部位上进行的动火作业。",
           "page_start": 10}]
    # 对比/否定提及（吊装答案排除动火分级）→ 不误拦
    out = "吊装作业按吊物质量分为三级。上述分级仅针对吊装作业本身，与动火作业分级（如第5.1.1条、第5.1.2条所述）无关。"
    r = verify_llm_output(out, ev)
    assert r.is_valid, f"对比提及被误拦: unsupported={r.unsupported_clauses} modality={r.modality_violations}"
    # 防回退：真转述（陈述句引用条款要求但丢掉模态词）仍必须拦截
    out2 = "第5.1.1条：动火作业分为三个级别。"
    r2 = verify_llm_output(out2, ev)
    assert not r2.is_valid, "真转述缺模态应仍拦"
    from src.core.verification.typed_verifier import verify_llm_output
    ev_text = "9.1 作业分级\n吊装作业按照吊物质量m不同分为：\na）一级吊装作业m > 1 0 0 t ;\nb）二级吊装作业：4 0 t ≤ m ≤ 1 0 0 t ;\nc) 三级吊装作业：m < 4 0 t"
    ev = [{"clause_revision_id": "c91", "clause_number": "9.1", "standard_no": "GB 30871-2022",
           "knowledge_type": "data", "modality": None, "content_text": ev_text, "page_start": 15}]
    # LLM 正确输出（规范化数字）→ 不应误报
    r = verify_llm_output("二级吊装作业：40t≤m≤100t [引用:GB 30871-2022-9.1]。", ev)
    assert r.is_valid, f"空格伪影被误报篡改: {r.unverified_numbers}"
    # 防回退：真篡改（把二级阈值改成 4t）仍必须拦截
    r2 = verify_llm_output("二级吊装作业：4t≤m≤100t [引用:GB 30871-2022-9.1]。", ev)
    assert not r2.is_valid and r2.unverified_numbers, "40t→4t 是真篡改，归一不能放过"


def test_number_selective_quote_not_flagged():
    """E2E 真实案例回归：证据同时含 10m/30m/60m，LLM 只引用 10m —— 不是篡改。"""
    from src.core.verification.typed_verifier import verify_llm_output
    ev = [{"clause_revision_id": "cx", "clause_number": "5.3.1", "standard_no": "GB",
           "knowledge_type": "data", "modality": None,
           "content_text": "动火点10m范围内分析；监测点30m；大型装置60m。", "page_start": 1}]
    out = "在动火点10 m范围内进行气体分析 [引用:GB-5.3.1]。"
    r = verify_llm_output(out, ev)
    assert r.is_valid, f"选择性引用不应判篡改: {r.unverified_numbers}"


def test_numeric_semantic_equivalence_passes():
    """阶段2.1 评审 P1 案例回归：语义等价的数值变体不应误拦。"""
    from src.core.verification.typed_verifier import verify_llm_output
    cases = [
        ("耐火极限不应低于 2.00h。", "耐火极限不应低于 2.0h [引用:GB-1.1]。", "1.1"),
        ("间距不应小于 13m。", "间距不应小于 13.0m [引用:GB-1.2]。", "1.2"),
        ("温度不应超过 300°C。", "温度不应超过 300℃ [引用:GB-1.3]。", "1.3"),
        ("浓度不小于 0.50MPa。", "浓度不小于 0.5MPa [引用:GB-1.4]。", "1.4"),
        ("系数取 1.5。", "系数取 1.50 [引用:GB-1.5]。", "1.5"),
    ]
    for ev_text, out, no in cases:
        ev = [{"clause_revision_id": "c", "clause_number": no, "standard_no": "GB",
               "knowledge_type": "data", "modality": None,
               "content_text": ev_text, "page_start": 1}]
        r = verify_llm_output(out, ev)
        assert r.is_valid, f"语义等价被误拦 ({ev_text}): {r.unverified_numbers}"


def test_numeric_real_tamper_still_blocked():
    """防回退：百分比容差方案会放过真篡改，浮点严格相等必须仍拦截。"""
    from src.core.verification.typed_verifier import verify_llm_output
    ev = [{"clause_revision_id": "c", "clause_number": "1.2", "standard_no": "GB",
           "knowledge_type": "data", "modality": None,
           "content_text": "间距不应小于 13m。", "page_start": 1}]
    r = verify_llm_output("间距不应小于 13.2m [引用:GB-1.2]。", ev)
    assert not r.is_valid and r.unverified_numbers, "13m→13.2m 是真篡改，必须拦截"
    r2 = verify_llm_output("耐火极限不应低于 2h [引用:GB-1.1]。",
                           [{"clause_revision_id": "c", "clause_number": "1.1",
                             "standard_no": "GB", "knowledge_type": "data",
                             "modality": None,
                             "content_text": "耐火极限不应低于 20h。", "page_start": 1}])
    assert not r2.is_valid, "2h↔20h 数量级不同，必须拦截"


def test_fabricated_clause_intercepted():
    from src.core.verification.typed_verifier import verify_llm_output
    out = "依据第9.9.9条 [引用:GB 30871-2022-9.9.9]，严禁作业。"
    r = verify_llm_output(out, EV[:1])
    assert not r.is_valid
    assert any("9.9.9" in u for u in r.unsupported_clauses)


def test_legal_exception_missing_intercepted():
    from src.core.verification.typed_verifier import verify_llm_output
    out = "第29条：处理敏感个人信息应当取得单独同意 [引用:民法典-第29条]。"
    r = verify_llm_output(out, [EV[2]])
    assert not r.is_valid
    assert any(v["violation"] == "exception_missing"
               for v in r.legal_element_violations)


def test_evidence_prompt_minimal():
    from src.core.llm.deepseek_client import build_evidence_prompt
    p = build_evidence_prompt("动火监护", EV[:2])
    assert "用户问题：动火监护" in p
    assert "5.2.1" in p and "0.5%" in p
    assert "仅基于以上证据" in p
    # 版权页等无关内容不进入 Prompt（只传证据片段）


def test_sse_verification_event_with_mock_llm(client):
    """SSE 全链路：mock 掉 LLM 流（无 Key 场景走占位答案），核验事件带真实结果。"""
    c, token = client
    with c.stream("POST", "/api/v1/chat/completions",
                  json={"query": "5.2.1 动火监护", "top_k": 1},
                  headers={"Authorization": f"Bearer {token}"}) as r:
        assert r.status_code == 200
        events, verification = [], None
        for line in r.iter_lines():
            if line.startswith("event: "):
                events.append(line[7:])
            if line.startswith("data: ") and '"is_valid"' in line:
                verification = json.loads(line[6:])
        assert events[0] == "evidence" and events[-1] == "done"
        assert verification is not None
        assert set(verification) >= {"is_valid", "unsupported_clauses",
                                     "unverified_numbers", "modality_violations",
                                     "legal_element_violations"}
