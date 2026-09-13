"""阶段2c：低置信条款云二次识别·分歧检测（disagreement-detection ONLY）。

执行计划 v3 阶段 2c 契约（评审 O2/O4 裁决后收敛）：
- 输入：clause_ocr_confidence < 阈值（默认 0.85）的深度通道条款
- 动作：把该条款对应 PDF 页区间送 MinerU 官方云（VLM 同能力）二次识别
- 输出：**分歧报告**（本地识别 vs 云识别的文本差异），绝不自动采纳
  （任何替换须人工裁决——证据文本不可变红线）
- 审计：每次云外发走 egress_audit.record_egress（D2 红线，不可豁免）
- O2 fallback：score 分布坍缩（>0.95 占比超 95%）时输入集退化为
  旧度量 suspects 清单（启发式口径），保证 2c 通道始终有可用输入

本模块是纯检测面：diff 计算用文本级相似度（difflib），阈值集中
grading.THRESHOLDS 一致纪律。
"""
from __future__ import annotations

import difflib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

#: 分歧判定阈值（相对差异比例）：> 此值 = 分歧（进报告）
DISAGREE_RATIO = 0.35
#: O2 fallback 触发线：高分 span 占比超过此值 = 分布坍缩
SCORE_COLLAPSE_HIGH_SHARE = 0.95


@dataclass
class DisagreementItem:
    clause_number: str
    page_start: int
    page_end: int
    local_head: str          # 本地识别（前 120 字）
    cloud_head: str          # 云识别（前 120 字）
    similarity: float        # difflib 相似度 [0,1]
    local_conf: float        # 本地 span min score
    verdict: str = "disagree"  # agree | disagree | cloud_unavailable


@dataclass
class DisagreementReport:
    doc_id: str
    standard_no: str
    checked: int = 0
    agree: int = 0
    disagree: int = 0
    cloud_unavailable: int = 0
    input_mode: str = "score"     # score | legacy_suspects（O2 fallback）
    items: list[DisagreementItem] = field(default_factory=list)


def score_distribution_collapsed(scores: list[float]) -> bool:
    """O2 fallback 判据：>0.95 的 span 占比 ≥ 95% = 坍缩（信号地基失效）。"""
    if not scores:
        return True  # 无信号 = 退化场景，fallback 生效
    hi = sum(1 for s in scores if s > 0.95)
    return hi / len(scores) >= SCORE_COLLAPSE_HIGH_SHARE


def text_similarity(a: str, b: str) -> float:
    """文本级相似度（difflib.SequenceMatcher，清洗空白后比较）。"""
    import re
    na = re.sub(r"\s+", "", a or "")
    nb = re.sub(r"\s+", "", b or "")
    if not na and not nb:
        return 1.0
    if not na or not nb:
        return 0.0
    return difflib.SequenceMatcher(None, na, nb).ratio()


def compare_clause_texts(local: str, cloud: str,
                         threshold: float = DISAGREE_RATIO) -> str:
    """单条款分歧判定：similarity < 1-threshold → disagree。"""
    sim = text_similarity(local, cloud)
    return "agree" if sim >= 1 - threshold else "disagree"


def select_2c_input(clauses: list[dict[str, Any]],
                    conf_key: str = "ocr_confidence",
                    conf_threshold: float = 0.85,
                    all_span_scores: list[float] | None = None,
                    legacy_suspects: list[str] | None = None) -> tuple[list[dict], str]:
    """2c 输入面选择（O2 fallback 内建）。

    clauses: [{clause_number, ocr_confidence(或 conf_key), page_start, page_end, ...}]
    返回 (选中条款, input_mode)。score 模式：conf < 阈值的条款；
    坍缩（或无分数）→ legacy_suspects 模式（旧启发式 suspects 清单）。
    """
    if all_span_scores is not None and score_distribution_collapsed(all_span_scores):
        logger.info("[2c] O2 fallback：score 分布坍缩 → 输入切换旧度量 suspects")
        return ([{"clause_number": n, "input_mode": "legacy"}
                 for n in (legacy_suspects or [])], "legacy_suspects")
    picked = [c for c in clauses
              if (c.get(conf_key) or 1.0) < conf_threshold]
    return picked, "score"


def build_disagreement_report(doc_id: str, standard_no: str,
                              pairs: list[tuple[dict, str | None]]) -> DisagreementReport:
    """对比本地/云文本，出分歧报告（纯函数，不触网）。

    pairs: [(条款dict, 云识别文本|None)]——云文本由调用方先行取回
    （本模块不直接调云，见 run_2c_for_doc 的编排说明）。
    """
    rep = DisagreementReport(doc_id=doc_id, standard_no=standard_no)
    for cl, cloud_text in pairs:
        rep.checked += 1
        if cloud_text is None:
            rep.cloud_unavailable += 1
            rep.items.append(DisagreementItem(
                clause_number=cl.get("clause_number", "?"),
                page_start=int(cl.get("page_start") or 0),
                page_end=int(cl.get("page_end") or 0),
                local_head=(cl.get("content_text") or "")[:120],
                cloud_head="", similarity=0.0,
                local_conf=float(cl.get("ocr_confidence") or 1.0),
                verdict="cloud_unavailable"))
            continue
        sim = text_similarity(cl.get("content_text") or "", cloud_text)
        v = "agree" if sim >= 1 - DISAGREE_RATIO else "disagree"
        if v == "agree":
            rep.agree += 1
        else:
            rep.disagree += 1
        rep.items.append(DisagreementItem(
            clause_number=cl.get("clause_number", "?"),
            page_start=int(cl.get("page_start") or 0),
            page_end=int(cl.get("page_end") or 0),
            local_head=(cl.get("content_text") or "")[:120],
            cloud_head=cloud_text[:120], similarity=round(sim, 4),
            local_conf=float(cl.get("ocr_confidence") or 1.0),
            verdict=v))
    return rep


def report_to_dict(rep: DisagreementReport) -> dict[str, Any]:
    """报告 → 可 JSON 化 dict（人工裁决面板消费）。"""
    return {
        "doc_id": rep.doc_id, "standard_no": rep.standard_no,
        "checked": rep.checked, "agree": rep.agree,
        "disagree": rep.disagree, "cloud_unavailable": rep.cloud_unavailable,
        "input_mode": rep.input_mode,
        "items": [{
            "clause_number": it.clause_number,
            "pages": [it.page_start, it.page_end],
            "similarity": it.similarity, "verdict": it.verdict,
            "local_conf": it.local_conf,
            "local_head": it.local_head, "cloud_head": it.cloud_head,
        } for it in rep.items],
    }
