# -*- coding: utf-8 -*-
"""结论**草稿**（Phase D-5a，§10.96）：系统基于**已批准材料**起草一段结论，**未经用户批准**。

## 这是什么、不是什么
- **是**：把"用户手写结论"这一步变成"系统起一稿、用户改/批准"（业主的原始要求是
  "经用户评审后再确认参考资料可用…再产出报告/PPT"，缺的正是"写"这一步）。
- **不是**：不是依据、不是自动成文、不落盘、不进报告。本模块只**返回文本**；
  是否采用由**用户**逐次显式决定（`unapproved_draft` 标记由端点回给调用方）。

## 形态：复用**已审计**的取证链提示词，**不**新写提示词（这一点是本步的核心取舍）

`ks_answer.build_messages(query, [], query_mode, materials_text)` 已经做过我们想做的事：

1. system prompt 末尾追加 `MATERIAL_SYSTEM_ADDENDUM`（材料只作参考、按承重能力分组、
   引用用 `[[m:i]]`）；
2. user prompt 把材料**另起一节**摆出来（不与法条混排），编号由
   `authority.render_evidence()` 分配（与报告的依据一节**同一套编号**）。

⇒ 本模块只做四件事，其余全部复用既有所有者：
① 取材料（`assemble_evidence`，评审硬门在 `mr.search_materials()` 那层）；
② **没有可承重材料就一次 LLM 都不调**（不许靠常识硬写）；
③ 调一次 LLM，用 `parse_llm_answer()` 解析成 `{derivation, conclusion}`；
④ 用**同一个** `assembled` 调 `research_report.check_conclusion_citations()` 做引用校验
（"引用了不存在的编号 / 引用了仅线索或不可用的材料"两句话**只有这一处**在写）。

⚠ 因此本模块**不引入新的引用判据**：编号体系、校验器、警告措辞全是既有所有者。
⚠ 也**没有**把法条证据（`[[c:i]]`）带进来（默认形态）：报告的校验器核不了法条引用，
混在一起会让"那些引用本次无法核验"这句话变得说不清（见 `docs/AUTO-DRAFT-PLAN.md` §4.4）。

## 三条纪律
1. **草稿不是依据**：调用方（面板/模型）必须显示 `status == "unapproved_draft"`；
   报告的依据一节永远由 `authority.render_evidence` 渲染，草稿进不了那一节。
2. **未批准材料进不了提示词**：`assemble_evidence` 的输入来自 `mr.search_materials()`——评审硬门。
3. **不许静默降级**：LLM 不可用 ⇒ 抛（端点回 `llm_unavailable`）；空输出 ⇒ 空草稿 + 警告；
   引用不成立 ⇒ **原样保留**草稿 + 警告逐条列出（不静默删改模型写的东西）。
"""
from __future__ import annotations

from typing import Any

from src.core.exceptions import KnowledgeStationError
from src.core.materials import authority

from src.core.exports.research_report import check_conclusion_citations

#: 端点必须把它回给调用方——**这是契约的一部分**，不是装饰。
DRAFT_STATUS = "unapproved_draft"

DRAFT_DISCLAIMER = ("本段由系统基于**已批准材料**起草，**未经用户批准**，不得作为依据；"
                    "引用编号与报告的校验器是同一套，可用它复核。")


def draft_conclusion(project_id: str, *, query: str, limit: int = 8) -> dict[str, Any]:
    """起草一段结论（**草稿**）。返回结构见下面的 `out`。

    `query` 必填且非空（草稿必须知道"要回答什么"才能去检索材料）。
    项目**不存在** ⇒ `ValueError`（端点翻成 404，与 `/report/research` 同款）；
    LLM 不可用 ⇒ `KnowledgeStationError(code="llm_unavailable")`。
    """
    assembled = authority.assemble_evidence(project_id, query, limit=limit)
    counts = dict(assembled["counts"])
    notes = list(assembled["notes"])
    if not assembled.get("project_found", True):
        # 与报告同款：**项目不存在** ≠ "项目里没有命中"（两件不同的事）
        raise ValueError(f"项目不存在: {project_id}")

    usable = authority.usable_hits(assembled)
    out: dict[str, Any] = {
        "status": DRAFT_STATUS,
        "disclaimer": DRAFT_DISCLAIMER,
        "draft_md": "",
        "derivation_md": "",
        "citations": {"material_refs": [], "unknown": [],
                      "not_load_bearing": [], "unchecked_law_refs": []},
        "warnings": [],
        "counts": counts,
        "notes": notes,
        "usable_indices": [h["index"] for h in usable],
        "llm_called": False,
    }
    if not usable:
        # ⚠ **一次 LLM 都不调**：没有能承重的材料，任何"结论"都只能靠常识或想象——
        # 那正是本项目最不该产出的东西。如实说"没起草"。
        out["warnings"].append(
            "本项目的**已批准**材料里没有可承重的命中（准则/可作依据/多源互证的辅证至少要有"
            "一条），因此**没有起草**——结论不应建立在材料之外。")
        return out

    # ---- 提示词：复用取证链的构造器（材料另起一节；编号与报告同一套）----
    from src.core.llm import ks_answer as ka
    materials_text = authority.render_evidence(assembled)
    messages = ka.build_messages(query, [], "default", materials_text)

    out["llm_called"] = True
    try:
        raw_text = ka._collect_stream(ka._stream_llm(messages))
    except Exception as e:  # noqa: BLE001 —— LLMError 与其它异常都翻成可操作错误码
        raise KnowledgeStationError(
            f"起草结论失败：调模型出错（{type(e).__name__}: {e}）。"
            "若未配置 Key，请先在设置里配置；草稿功能**不会**自动降级成「凭常识作答」",
            code="llm_unavailable") from e

    parsed = ka.parse_llm_answer(raw_text or "", 0, counts.get("total", 0))
    draft = str(parsed.get("conclusion") or "").strip()
    out["derivation_md"] = str(parsed.get("derivation") or "").strip()
    out["draft_md"] = draft
    out["warnings"].extend(parsed.get("warnings") or [])
    if not draft:
        # 空输出**不是**成功：如实说，别让调用方以为"模型给了个空结论"
        out["warnings"].append(
            "模型没有产出结论段（原文见 `derivation_md`，可能被兜底解析或整体为空）——"
            "请人工判断，**不要**把空草稿当成结论。")

    # ---- 引用校验：与报告**同一个判据 + 同一套措辞**（同一个 assembled ⇒ 编号一致）----
    citations, cite_warnings = check_conclusion_citations(draft, assembled)
    out["citations"] = citations
    out["warnings"].extend(cite_warnings)
    return out
