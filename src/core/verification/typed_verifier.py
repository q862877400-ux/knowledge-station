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
from typing import List, Literal, Optional

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


def _clause_mention_window(text: str, clause_number: str,
                           evidence_clauses: Optional[List[dict]] = None) -> str:
    """取输出中**该条款**被提到之处之后的窗口文本并集。

    两种引用形态都要认（2026-10-19 修复）：

    **形态 A：字面条款号**（老形态）
        「根据第5.2.1条，动火作业应有专人监护」——条款号字面出现在输出里。

    **形态 B：`[[c:i]]` 序号标记**（`FORENSIC_SYSTEM_PROMPT` 规则 1 规定的形态）
        「……动火作业应升级管理[[c:1]]」——**条款号字面根本不在输出里**，
        只有一个指向 `evidence[i]` 的序号。

    ⚠ **形态 B 曾经让本函数彻底失效**（2026-10-19 真机实测）：取证提示词要求模型
    一律用 `[[c:i]]`，于是 `clause_number` 在输出里出现 0 次 ⇒ 窗口恒为空串 ⇒
    调用处 `or llm_output` 回退**整篇答案** ⇒ `extract_modality(整篇)` 取到的是
    全文第一个模态词，与正在核验的那条条款毫无关系。

    实测后果：模型正确写出「动火作业**可按**二级动火作业管理 [[c:4]]」，
    核验器却因为全文第一个模态词是「应」而报 `modality_strengthened`（误报）。

    修法：把 `[[c:i]]` 解析成 `evidence[i].clause_number`，与字面形态一并处理。
    解析不到的序号（越界）**不猜**——它由 `unsupported_clauses` 那条判据单独负责。

    @param text - 模型输出全文。
    @param clause_number - 正在核验的证据条款号（如 `5.1.2`）。
    @param evidence_clauses - 本轮证据（用于把 `[[c:i]]` 序号映射回条款号）。
        缺省时只认字面形态（保持对旧调用方兼容）。
    @returns 该条款所有提及处之后的窗口文本（各 240 字符），去重保序；无提及返回空串。
    """
    starts: List[int] = []

    # 形态 A：字面条款号
    for m in re.finditer(re.escape(clause_number), text):
        starts.append(m.start())

    # 形态 B：[[c:i]] / [[m:i]] 序号标记
    if evidence_clauses:
        # 该条款在本轮证据里的下标（同一条款可能被检索到多次，全部收下）
        wanted = [i for i, c in enumerate(evidence_clauses)
                  if str(c.get("clause_number") or "") == str(clause_number)]
        if wanted:
            wanted_set = set(wanted)
            for m in _CITE_MARK.finditer(text):
                idx = int(m.group(1))
                if idx in wanted_set:
                    starts.append(m.start())

    if not starts:
        return ""

    parts = []
    seen = set()
    for pos in sorted(set(starts)):
        win = text[pos:pos + 240]
        if win in seen:
            continue
        seen.add(win)
        parts.append(win)
    return "\n".join(parts)


#: `[[c:i]]`（法条证据）/ `[[m:i]]`（参考资料）两种序号标记。
#: 与 `ks_answer.FORENSIC_SYSTEM_PROMPT` 规则 1 的产出格式一一对应。
_CITE_MARK = re.compile(r"\[\[(?:c|m):(\d+)\]\]")



_PURE_LAW_NUM = re.compile(r"^第[一二三四五六七八九十百千]+条$")

#: 输出中标准号的出现形态（用于把"孤立条款号"归因到某部标准）。
#: 覆盖 `GB 30871-2022` / `GB/T 12345.6-2020` / `GB／T`（全角斜杠）。
_STD_MENTION = re.compile(
    r"(?:GB|DB|JGJ|JG|CJJ|CJ|HG|SH|SY|NB|DL|YB|TB|JT|MT|AQ|TSG)"
    r"\s*[/／]?\s*[A-Z]?\s*\d{3,5}(?:\.\d+)?\s*[—\-–]\s*\d{2,4}", re.I)


def _describe_unsupported(num: str, llm_output: str,
                          evidence_clauses: List[dict]) -> dict:
    """把一条"证据外条款号"升级为**可操作**的说明（不改拦截，只补证据）。

    为什么需要（pk-eli-mcp 的启示：**先声明"有没有资格判断"，再判断**）：
    旧输出只有一串裸条款号，用户无法区分三种**后果完全不同**的情形：
      a) 模型引用了本轮证据**同一部标准**里的条款，但该条**没被检索出来**
         → 可操作：补检索该条；这是检索召回问题，不是编造；
      b) 模型引用了**本轮完全没讨论的**标准号
         → 提示词违规（规则 2），也可能是编造；
      c) 条款号本身形状可疑（如 `9.9.9` 这类越界层级）
         → 更可能是编造。

    判据故意保守：只用**文本内证据**（该条款号附近是否出现标准号、以及该标准号
    是否在本轮证据里），**不查库**（核验器保持纯函数、毫秒级、无 IO）。
    在型号附近找不到标准号时明确记为 `unknown`，而不是猜一个。

    @param num - 归一后的条款号（如 `5.2.1` 或 `第四百九十六条`）。
    @param llm_output - 模型输出全文（用于取条款号附近的上下文）。
    @param evidence_clauses - 本轮证据条款。
    @returns 形如 `{clause_number, standard_no, verdict, reason}` 的说明。
    """
    ev_stds = [str(c.get("standard_no") or "") for c in evidence_clauses]
    # 取该条款号**最后一次**出现附近的文本窗（引用通常就近给出标准号）。
    ctx_window = ""
    try:
        mentions = list(re.finditer(re.escape(num), llm_output))
        if mentions:
            m = mentions[-1]
            ctx_window = llm_output[max(0, m.start() - 160): m.start() + 160]
    except re.error:
        ctx_window = ""

    near_stds = _STD_MENTION.findall(ctx_window) if ctx_window else []
    near_std = near_stds[0] if near_stds else None

    if near_std is None:
        return {
            "clause_number": num, "standard_no": None, "verdict": "unknown",
            "reason": "条款号附近未见标准号，无法判断属于哪部标准；"
                      "它不在本轮证据集内，故不作为依据。",
        }
    in_evidence = any(near_std.replace(" ", "") in s.replace(" ", "")
                      or s.replace(" ", "") in near_std.replace(" ", "")
                      for s in ev_stds if s)
    if in_evidence:
        return {
            "clause_number": num, "standard_no": near_std,
            "verdict": "same_standard_not_retrieved",
            "reason": f"该条款号属于本轮证据内的标准 {near_std}，但这一条**未被检索出来**"
                      f"——属检索召回问题（可扩大检索范围/补该条），不是模型编造。"
                      f"本次仍不作为依据（规则：只引证据内条款）。",
        }
    return {
        "clause_number": num, "standard_no": near_std,
        "verdict": "outside_evidence_standard",
        "reason": f"该条款号指向标准 {near_std}，而本轮证据里没有这部标准"
                  f"——模型引用了讨论范围之外的条款（违反规则 2），"
                  f"也可能是编造；不作为依据。若确需该标准，请先入库再问。",
    }


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
    #
    # ⚠ 语义边界（2026-09-16 补记，务必区分）：
    #   `unsupported_clauses` 记的是**"模型引用了证据集之外的条款号"** —— 这是
    #   **提示词级硬约束的违反**（SYSTEM_PROMPT 规则 2：严禁提及证据外条款号），
    #   故它**就该拦**，与"本库有没有收录该标准"无关。
    #   它**不等于**"该条款号不存在"或"本库未收录该标准"——把两者混为一谈会产出
    #   无法执行的告警（用户既不知道是哪部标准的哪一条，也无法判断该去补什么）。
    #   故新增 `unsupported_context` 把每条升级为可操作信息（见下）。
    unsupported_context: List[dict] = []
    for groups in dict.fromkeys(_CITED_NUM.findall(llm_output)):
        raw = next((g for g in groups if g), "")
        num = _norm_cite(raw)
        if not num or num in evidence_numbers:
            continue
        unsupported.append(num)
        unsupported_context.append(_describe_unsupported(num, llm_output, evidence_clauses))

    # 2. 分型核验
    for c in evidence_clauses:
        ktype = c.get("knowledge_type", "rule")
        window = _clause_mention_window(llm_output, c["clause_number"],
                                        evidence_clauses) or llm_output

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
            src_mod = c.get("modality") or ""
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
                        vtype: Optional[Literal[
                            'modality_weakened', 'modality_strengthened']] = "modality_weakened"
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
        unsupported_context=unsupported_context,
        unverified_numbers=tampered,
        modality_violations=modality_violations,
        legal_element_violations=legal_violations)
