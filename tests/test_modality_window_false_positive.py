"""核验器模态窗口误报 —— 判据（2026-10-19）。

## 这份文件解决什么问题（真机实测，不是假想）

2026-10-19 用免费 router 跑真实 `ks_answer('动火作业怎么分级')`，核验器报 3 条模态违规：

    {'source_modality': '可', 'output_modality': '应', 'violation_type': 'modality_strengthened'}
    {'source_modality': '可', 'output_modality': '应', 'violation_type': 'modality_strengthened'}
    {'source_modality': '不应', 'output_modality': '应', 'violation_type': 'modality_weakened'}

而模型原文写的是：

    凡生产装置或系统全部停车……经所在单位安全管理部门批准，动火作业**可按**二级动火作业管理 [[c:4]]

**它写的就是「可」**。核验器却判它写成了「应」。

## 根因

`_clause_mention_window` 取该条款号出现位置之后 240 字，`extract_modality(window)`
取窗口里**第一个**模态词。同一窗口里还有别的模态词时（本例有「应升级管理」
「应划定固定火区」），取到的那个跟本条款无关。

## 判据设计

1. **误报必须消失**：模型正确复述「可」时，不能报 strengthened。
2. **真问题必须还在**：模型真把「不应」写成「应」时，必须照旧拦截。
3. **原有行为不回归**：`test_t06.py` 里那几条（weakened / strengthened / missing）全绿。

第 2 条是这份文件存在的理由 —— 只修误报不修真问题等于把红线放松。
"""
import pytest

#: 一条「可」型条款，以及一段**包含多个其它模态词**的真实上下文。
#: 这正是误报的触发条件：本条款是「可」，但同窗口里有「应」。
EV_KEKE = [
    {
        "clause_revision_id": "c1",
        "clause_number": "5.1.2",
        "standard_no": "GB 30871-2014",
        "knowledge_type": "rule",
        "modality": "可",
        "content_text": (
            "5.1.2 二级动火作业：除特殊动火作业和一级动火作业以外的动火作业。"
            "凡生产装置或系统全部停车，装置经清洗、置换、分析合格并采取安全隔离措施后，"
            "可根据其火灾、爆炸危险性大小，经所在单位安全管理部门批准，"
            "动火作业可按二级动火作业管理。"
        ),
        "exception": None,
        "subject": None,
        "page_start": 6,
    },
    {
        "clause_revision_id": "c2",
        "clause_number": "5.1.1",
        "standard_no": "GB 30871-2014",
        "knowledge_type": "rule",
        "modality": "应",
        "content_text": "遇节日、假日或其他特殊情况，动火作业应升级管理。企业应划定固定动火区及禁火区。",
        "exception": None,
        "subject": None,
        "page_start": 6,
    },
]

#: 一条「不应」型条款，用于验证真问题仍然被抓。
EV_BUNENG = [
    {
        "clause_revision_id": "c3",
        "clause_number": "5.3",
        "standard_no": "GB 30871-2014",
        "knowledge_type": "rule",
        "modality": "不应",
        "content_text": (
            "5.3 特殊动火作业要求\n"
            "a）在生产不稳定的情况下不应进行带压不置换动火作业；\n"
            "b) 应预先制定作业方案，落实安全防火措施；\n"
            "c) 应在正压条件下进行作业。"
        ),
        "exception": None,
        "subject": None,
        "page_start": 6,
    },
]


def test_correct_keke_not_reported_as_strengthened():
    """模型正确复述「可」时，不许报 strengthened（2026-10-19 真机误报）。"""
    from src.core.verification.typed_verifier import verify_llm_output

    out = (
        "按 GB 30871-2014，固定动火区外的动火作业一般分为二级动火、一级动火、特殊动火三个级别，"
        "遇节日、假日或其他特殊情况，动火作业应升级管理 [[c:1]]。"
        "凡生产装置或系统全部停车，装置经清洗、置换、分析合格并采取安全隔离措施后，"
        "可根据其火灾、爆炸危险性大小，经所在单位安全管理部门批准，"
        "动火作业可按二级动火作业管理 [[c:0]]。"
    )
    r = verify_llm_output(out, EV_KEKE)
    strengthened = [v for v in r.modality_violations
                    if v.violation_type == "modality_strengthened"]
    assert not strengthened, (
        "模型写的是「可按二级动火作业管理」，核验器却判它加强成「应」——"
        f"这是窗口取词取错了：{[ (v.source_modality, v.output_modality) for v in strengthened ]}"
    )


def test_real_weakened_still_intercepted():
    """真问题必须还在：把「不应」写成「应」时，仍要拦截。"""
    from src.core.verification.typed_verifier import verify_llm_output

    out = "根据第5.3条，在生产不稳定的情况下应进行带压不置换动火作业。"
    r = verify_llm_output(out, EV_BUNENG)
    assert not r.is_valid, "把「不应」写成「应」是真违规，不许放过"
    assert any(v.violation_type == "modality_weakened" for v in r.modality_violations), (
        f"应报 modality_weakened，实际: {[(v.violation_type, v.source_modality, v.output_modality) for v in r.modality_violations]}"
    )


def test_correct_buneng_passes():
    """模型正确保留「不应」时，不许误报。"""
    from src.core.verification.typed_verifier import verify_llm_output

    out = "根据第5.3条，在生产不稳定的情况下不应进行带压不置换动火作业；应在正压条件下进行作业。"
    r = verify_llm_output(out, EV_BUNENG)
    assert r.is_valid, (
        f"正确保留否定被误拦: "
        f"{[(v.violation_type, v.source_modality, v.output_modality) for v in r.modality_violations]}"
    )
