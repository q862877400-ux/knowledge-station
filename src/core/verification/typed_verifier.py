"""分型核验器（T06，依据主计划 v4.3 第 8.4 节）。

三型核验 + 条款号闭包：
  - 通用：条款号闭包（回答引用的条款号必须 ⊆ 证据集）
  - data 型：数值闭包（数值+单位必须原样出现；被改写 → number_tampered）
  - rule 型：模态强度（输出模态 < 原模态 → modality_weakened 拦截；> → strengthened 警告；
            缺失 → modality_missing）
  - legal 型：法理要素（例外丢失 → exception_missing；主体缺失 → subject_missing）
"""
from __future__ import annotations

import re
from typing import List

from src.core.domain.models import (
    MODALITY_STRENGTH, ModalityViolation, VerificationResult,
)

_NUM_UNIT = re.compile(
    r"(\d+(?:\.\d+)?)\s*(m²|m³|m\^?2|m\^?3|mm|cm|m|MPa|kPa|Pa|kV|V|kW|W|h|min|s|℃|°C|%|kg|t|kN|N|L|dB|lx|Hz|MHz)")

# 单位/符号规范化映射（阶段2.1：数值核验语义等价，响应外部评审 P1）
_UNIT_CANON = {
    "°C": "℃", "m²": "m2", "m^2": "m2", "m³": "m3", "m^3": "m3",
    "min": "min", "MPa": "MPa",
}

#: PDF 提取伪影归一（2026-09-06 真机回归）：宽字距数字被提取器切开
# （GB 30871-2022 §9.1 实测 "4 0 t ≤ m ≤ 1 0 0 t"）——数字之间的空格剥离，
# 否则 _NUM_UNIT 只匹配到最后一个数字（"0t"），与 LLM 正确输出 "40t" 对不上
# → number_tampered 误报。只合并 digit-digit 间空格；对称作用于证据与输出，
# 真篡改仍被抓（门禁宁误报不漏报的原则不受影响）。
_DIGIT_GAP_RE = re.compile(r"(?<=\d)\s+(?=\d)")


def _canon_pairs(text: str) -> set[tuple[float, str]]:
    """提取 (浮点值, 规范化单位) 集合。2.00h 与 2.0h 归一为同一元素。

    设计原则：浮点严格相等、不加百分比容差——工程数值 13m 与 13.2m 语义不同，
    门禁宁可偶发误报不可漏报（评审建议的 ±2% 容差会放过真篡改，不采纳）。
    """
    pairs = set()
    for val, unit in _NUM_UNIT.findall(_DIGIT_GAP_RE.sub("", text)):
        pairs.add((float(val), _UNIT_CANON.get(unit, unit)))
    return pairs

# 条款号引用（收紧形态，避免数值误判）：
#   第5.2.1条 / 第5.2.1 ｜ [引用:标准号-5.2.1] 徽标 ｜ 第四百九十六条（中文法条）
_CITED_NUM = re.compile(
    r"第(\d+(?:\.\d+){1,4})\s*条?"
    r"|\[引用:[^\]\[]*?-(\d+(?:\.\d+){1,4})\]"
    r"|(第[一二三四五六七八九十百千]+条)")

# 输出中的模态词定位（复用 knowledge.classifier 的复合词防护）
from src.core.knowledge.classifier import extract_modality  # noqa: E402

#: 对比/否定提及标记（2026-09-06 真机回归「吊装作业怎么分级」第二轮）：条款号
#: 出现在"与…无关/不涉及/区别于"等语境时，LLM 只是拿它做**区分**而非转述其
#: 规范要求——窗口无模态词不应计 modality_missing（GB 30871 §9.1 吊装答案
#: 引用 §5.1.1 动火分级仅作排除说明被误拦的教训）。若 LLM 真转述了要求，
#: 拼接窗口含模态词仍走正常校验，逃逸面极小。
_MENTION_ONLY_RE = re.compile(
    r"无关|不涉及|不属于|区别于|不同于|并非|不属于.*范围|不适用")


def _clause_mention_window(text: str, clause_number: str) -> str:
    """取输出中该条款号**所有**出现位置之后的窗口文本并集（phase5 修复）。

    phase3 遗留误报：长条款被多次引用时只取首个窗口，首个窗口可能无模态词
    （实测 4.10 条 f 项"不应擅自离开"在第二窗口），导致 modality_missing 误报。
    修复：遍历全部出现位置拼接窗口（各 240 字符），并去重保留顺序。
    """
    esc = re.escape(clause_number)
    parts = []
    seen = set()
    for m in re.finditer(esc, text):
        win = text[m.start():m.start() + 240]
        if win in seen:
            continue
        seen.add(win)
        parts.append(win)
    return "\n".join(parts)


_PURE_LAW_NUM = re.compile(r"^第[一二三四五六七八九十百千]+条$")


def _norm_cite(num: str) -> str:
    """引用归一：'第5.2.1条'→'5.2.1'；纯中文法条'第四百九十六条'保持原样。"""
    s = num
    if s.startswith("第") and not _PURE_LAW_NUM.match(s):
        s = s[1:]
    if s.endswith("条") and not s.startswith("第"):
        s = s[:-1]
    return s


def verify_llm_output(llm_output: str, evidence_clauses: List[dict]) -> VerificationResult:
    """evidence_clauses: [{clause_revision_id, clause_number, standard_no,
    knowledge_type, modality, content_text, exception, subject}]"""
    unsupported: List[str] = []
    tampered: List[dict] = []
    modality_violations: List[ModalityViolation] = []
    legal_violations: List[dict] = []

    evidence_numbers = {c["clause_number"] for c in evidence_clauses}

    # 1. 条款号闭包（通用）
    for groups in dict.fromkeys(_CITED_NUM.findall(llm_output)):
        raw = next((g for g in groups if g), "")
        num = _norm_cite(raw)
        if num and num not in evidence_numbers:
            unsupported.append(num)

    # 2. 分型核验
    for c in evidence_clauses:
        ktype = c.get("knowledge_type", "rule")
        window = _clause_mention_window(llm_output, c["clause_number"]) or llm_output

        if ktype == "data":
            content = c.get("content_text") or ""
            evidence_pairs = _canon_pairs(content)
            output_pairs = _canon_pairs(llm_output)
            reported: set[tuple[float, str]] = set()
            for val, unit in evidence_pairs:
                if (val, unit) in reported:
                    continue
                reported.add((val, unit))
                if (val, unit) in output_pairs:
                    continue  # 数值+单位 语义等价出现（含 2.00h↔2.0h、℃↔°C）
                for out_val, out_unit in output_pairs:
                    if out_unit != unit or out_val == val:
                        continue
                    # 输出数值若也来自证据原文（选择性引用），不算篡改
                    if (out_val, out_unit) in evidence_pairs:
                        continue
                    tampered.append({
                        "clause_id": c["clause_revision_id"],
                        "original": f"{val}{unit}",
                        "output": f"{out_val}{out_unit}",
                        "violation": "number_tampered"})
                    break

        elif ktype == "rule":
            src_mod = c.get("modality")
            src_strength = MODALITY_STRENGTH.get(src_mod, -1)
            if src_mod and src_strength >= 0:
                out_mod, _ = extract_modality(window)
                if not out_mod:
                    if _MENTION_ONLY_RE.search(window):
                        pass  # 对比/否定提及（"与…无关"）非转述要求 → 不计 missing
                    else:
                        modality_violations.append(ModalityViolation(
                            clause_revision_id=c["clause_revision_id"],
                            source_modality=src_mod, output_modality="",
                            source_strength=src_strength, output_strength=-1,
                            violation_type="modality_missing"))
                else:
                    out_strength = MODALITY_STRENGTH.get(out_mod, -1)
                    if out_strength < src_strength:
                        vtype = "modality_weakened"
                    elif out_strength > src_strength:
                        vtype = "modality_strengthened"
                    else:
                        vtype = None
                    if vtype:
                        modality_violations.append(ModalityViolation(
                            clause_revision_id=c["clause_revision_id"],
                            source_modality=src_mod, output_modality=out_mod,
                            source_strength=src_strength, output_strength=out_strength,
                            violation_type=vtype))

        elif ktype == "legal":
            exc = c.get("exception")
            if exc and not re.search(r"除.{0,60}外|另有规定|但", llm_output):
                legal_violations.append({
                    "clause_id": c["clause_revision_id"],
                    "violation": "exception_missing",
                    "original_exception": exc})
            subj = c.get("subject")
            if subj and subj not in llm_output:
                legal_violations.append({
                    "clause_id": c["clause_revision_id"],
                    "violation": "subject_missing",
                    "original_subject": subj})

    # strengthened 属警告不拦截
    blocking = [v for v in modality_violations
                if v.violation_type != "modality_strengthened"]
    is_valid = (not unsupported and not tampered
                and not blocking and not legal_violations)
    return VerificationResult(
        is_valid=is_valid,
        unsupported_clauses=unsupported,
        unverified_numbers=tampered,
        modality_violations=modality_violations,
        legal_element_violations=legal_violations)
