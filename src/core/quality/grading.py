"""质量分级与裁决——阈值与规则的**唯一所有者**（纯函数，零 IO）。

## 为什么阈值集中在这里
全仓此前**没有任何质量阈值**（既没有 quality_grade 的生产者，也没有倾斜/坍缩判据），
所以这里第一次把"什么算坏"写成可测常量。任何调参只改 `THRESHOLDS` 一处 + 同步测试 fixture。

## 裁决三态（决策 2 的分桶依据）
- `block`（❌ 不建议入库）：**只在能自证的损坏上触发**（乱码不可修复 / 严重倾斜 /
  条款坍缩 / 近乎空白 / 替换字符泛滥 / 有文本却切不出条款 / 解析失败）。
- `warn`（⚠️ 需人工确认）：扫描件无文本层、轻度倾斜、可疑条款偏多、与库内重复、
  分型置信度偏低等"可能没事但要看一眼"的情形。
- `ok`（✅ 可直接入库）：无上述证据。

**取舍（有意漏放）**：倾斜 < 1.0° 与轻度排版损坏落在 warn/ok，不 block——真实语料里
扫描件占比高，把"无法评估"判成"损坏"会阻断合法入库。因此 R27 的"100% 拦截"只对
**可合成复现的那几类形态**宣称（见 tests/test_dryrun_report.py 的 `test_blk_*` / `test_verdict_*`），不对真实语料宣称 100%。

## 分级与 R13 契约
`doc_meta.quality_grade` 的既有契约是 **A|B|C**（R13：清晰度/OCR 识别率 ≥0.95→A，
0.85~0.95→B，<0.85→C；`schema.sql` 该列无 CHECK 但测试锁定了取值）。
本模块的 `grade_document` 因此把 `D` 定义为**只存在于预览报告**的档位，
含义是"禁止默认落库"，**永不写入 doc_meta**（强制入库时降级写 C，由调用方负责）。
"""

from __future__ import annotations

import statistics
from typing import Any, Iterable

__all__ = [
    "THRESHOLDS",
    "grade_document",
    "legal_element_quality",
    "one_line_summary",
    "typing_quality",
    "verdict_document",
]

#: 全部阈值/扣分常量。**唯一所有者**（改这里就改了全局口径）。
THRESHOLDS: dict[str, float] = {
    # ---- block：正向损坏证据 ----
    "collapse_chars": 2000,           # B2 有这么多字却几乎切不出条款 = 坍缩
    "collapse_clauses": 1,
    "skew_block_deg": 3.0,            # B3 文档中位倾角
    "skew_block_ratio": 0.5,          # B3 倾斜页占比
    "sparse_chars_per_page": 20.0,    # B4 页面字符密度过低 = 近乎空白
    "sparse_min_pages": 5,
    "weird_block_ratio": 0.30,        # B5 异常字符占比
    "weird_min_chars": 500,
    "replacement_block_ratio": 0.05,  # B6 替换字符 U+FFFD 占比
    # 注：曾设计 B7「有文本却 0 条款 = 切分失败」，2026-09-11 实测**删除**——
    # 切分器对任何 ≥200 字的输入都至少产出一条「前置说明」条款（8 类形态实测
    # clauses 恒 ≥1），该条件不可达 = 死规则。真正的坍缩信号由 B2 承担
    # （≥2000 字却 ≤1 条）。
    # ---- warn ----
    "skew_warn_deg": 1.0,             # W2
    "suspect_warn_ratio": 0.05,       # W3 可疑条款占比
    "warn_min_clauses": 10,           # W3/W10 生效下限（条款太少时比例不可靠）
    "clauses_per_1000chars_warn": 1.0,  # W10 条款密度异常偏低
    "low_type_confidence": 0.85,      # W5 分型置信度
    "untyped_warn_share": 0.30,       # W5 低置信条款占比阈值
    # ---- 分级（R13 契约，硬对齐）----
    "grade_a_min": 0.95,
    "grade_b_min": 0.85,
    # ---- 条款级扣分（recognition.clause_ocr_confidence 用）----
    "clause_weird_ratio": 0.02,
    "clause_replacement_ratio": 0.01,
    "clause_min_cjk_ratio": 0.05,
    "p_clause_tiny": 0.15,
    "p_clause_weird": 0.35,
    "p_clause_replacement": 0.40,
    "p_clause_nonprint": 0.20,
    "p_clause_nocjk": 0.25,
    "p_clause_skew": 0.30,
    # ---- R27 口径：OCR 置信度 < 0.85 视为可疑 ----
    "suspect_confidence": 0.85,
}


def _why(code: str, reason: str) -> dict[str, str]:
    return {"code": code, "reason": reason}


def verdict_document(report: dict[str, Any]) -> tuple[str, list[dict[str, str]]]:
    """依据报告度量给出 (verdict, reasons)。

    `report` 至少包含：`status`、`error_code`、`recognition`、`layout`、`total_clauses`、
    `deep_fallback_skipped`、`duplicate`、`ocr_suspects`、`typing_quality`。
    缺失的度量**不会**触发 block（block 需要正向证据），也不会被当成 ok 的证据。
    """
    T = THRESHOLDS
    reasons: list[dict[str, str]] = []
    rec = report.get("recognition") or {}
    lay = report.get("layout") or {}
    chars = int(lay.get("chars") or 0)
    clauses = int(report.get("total_clauses") or 0)
    state = str(rec.get("text_layer_state") or "")
    typed = report.get("typing_quality") or {}
    dup = report.get("duplicate") or {}
    suspects = report.get("ocr_suspects") or []

    block: list[dict[str, str]] = []
    warn: list[dict[str, str]] = []

    # ---------------- block（❌）----------------
    if str(report.get("status")) == "error":
        block.append(_why("B8", f"解析失败：{report.get('error_code') or '未知'}"))
    if state == "pua_mangled":
        block.append(_why("B1", "文本层为 PUA 错位字体且归一化无法修复（切分不可信）"))
    if chars >= T["collapse_chars"] and clauses <= T["collapse_clauses"]:
        block.append(_why("B2", f"正文 {chars} 字却只切出 {clauses} 条条款（坍缩）"))
    skew = rec.get("skew_deg")
    skew_measured = bool(rec.get("skew_measured"))
    skew_pages_ratio = float(rec.get("skew_pages_ratio") or 0)
    if skew_measured and skew is not None:
        # 两条判据**互相独立**（不能写成 elif）：文档中位倾角未到 block 线、但多数页
        # 各自都严重倾斜的"混合文档"（半本正、半本歪）也要能拦下来。
        # 2026-09-11 verifier 审计 P0-1：原 `elif` 让第二条在 skew 已 ≥3° 时才求值，
        # 而那条路径已被第一条拦下，等于死分支。
        if abs(float(skew)) >= T["skew_block_deg"]:
            block.append(_why("B3", f"文档中位倾角 {skew}° ≥ {T['skew_block_deg']}°（严重倾斜）"))
        elif skew_pages_ratio >= T["skew_block_ratio"]:
            block.append(_why("B3", f"倾斜页占比 {skew_pages_ratio:.0%} ≥ {T['skew_block_ratio']:.0%}"
                                   f"（多数页各自严重倾斜）"))
    pages = int(lay.get("pages") or 0)
    # 缺失度量不得触发 block（本函数 docstring 的承诺）：`chars_per_page` 缺席时**跳过** B4，
    # 而不是把 None 当 0——那会把"没测到"误报成"近乎空白"（verifier 审计 P2-3）。
    #
    # **B4 必须排除"无文本层"**（2026-09-11 真机抓到的误伤）：扫描件的 chars_per_page 恒为 0
    # 是**构造性事实**而非质量问题——否则 31 页扫描版国标（实测 GB 30871-2022）会被判 block，
    # 与"不许误杀扫描件"的设计直接冲突。无文本层的情形由 W1 承担（warn）。
    # 合成测试此前只用 1 页图，恰好绕过 `pages >= 5` 门槛，所以这条只有真机才暴露。
    cpp = lay.get("chars_per_page")
    if (cpp is not None and state != "empty" and pages >= T["sparse_min_pages"]
            and float(cpp) < T["sparse_chars_per_page"]):
        block.append(_why("B4", f"{pages} 页平均每页仅 {float(cpp):.1f} 字（近乎空白）"))
    weird = float(rec.get("weird_ratio") or 0.0)
    if chars >= T["weird_min_chars"] and weird >= T["weird_block_ratio"]:
        block.append(_why("B5", f"异常字符占比 {weird:.1%} ≥ {T['weird_block_ratio']:.0%}"))
    repl = float(rec.get("replacement_ratio") or 0.0)
    if repl >= T["replacement_block_ratio"]:
        block.append(_why("B6", f"替换字符 U+FFFD 占比 {repl:.1%} ≥ {T['replacement_block_ratio']:.0%}"))

    # ---------------- warn（⚠️）----------------
    if state == "empty":
        extra = "，且已跳过深度通道（零外发）" if report.get("deep_fallback_skipped") else ""
        warn.append(_why("W1", f"无文本层（扫描件？）{extra}——条款级预览不可得"))
    if skew_measured and skew is not None and abs(float(skew)) >= T["skew_warn_deg"] \
            and not any(r["code"] == "B3" for r in block):
        warn.append(_why("W2", f"文档中位倾角 {skew}°（轻度倾斜，人工确认）"))
    if clauses >= T["warn_min_clauses"] and suspects:
        ratio = len(suspects) / clauses
        if ratio >= T["suspect_warn_ratio"]:
            warn.append(_why("W3", f"可疑条款 {len(suspects)}/{clauses}（{ratio:.1%}）"
                                    f"≥ {T['suspect_warn_ratio']:.0%}"))
    low = int(typed.get("low_type_confidence") or 0)
    if clauses >= T["warn_min_clauses"] and low and (low / clauses) >= T["untyped_warn_share"]:
        warn.append(_why("W5", f"分型置信度 <{T['low_type_confidence']} 的条款 {low}/{clauses}"))
    density = float(lay.get("clauses_per_1000chars") or 0.0)
    if chars >= T["collapse_chars"] and 0 < density < T["clauses_per_1000chars_warn"]:
        warn.append(_why("W10", f"条款密度 {density:.2f}/千字 偏低（切分可能丢条）"))
    if str(dup.get("kind") or "none") != "none":
        warn.append(_why("W6", f"与库内已有文档重复（{dup.get('kind')}）：{dup.get('message') or ''}"))

    if block:
        return "block", block + warn
    if warn:
        return "warn", warn
    return "ok", [_why("OK", "未发现已知损坏证据")]


def grade_document(verdict: str, doc_confidence: float) -> tuple[str, list[str]]:
    """质量分级。`block → D`（仅预览语义，**不写 doc_meta**）；否则按 R13 阈值定 A/B/C。"""
    T = THRESHOLDS
    if verdict == "block":
        return "D", ["存在损坏证据（D 仅用于预览拦截，不入库）"]
    conf = float(doc_confidence or 0.0)
    if conf >= T["grade_a_min"]:
        return "A", [f"识别置信度 {conf:.4f} ≥ {T['grade_a_min']}"]
    if conf >= T["grade_b_min"]:
        return "B", [f"识别置信度 {conf:.4f} 落在 [{T['grade_b_min']}, {T['grade_a_min']})"]
    return "C", [f"识别置信度 {conf:.4f} < {T['grade_b_min']}"]


def typing_quality(clauses: Iterable[dict[str, Any]], *, doc_type: str) -> dict[str, Any]:
    """分型预览质量评估（R27 v4.3 新增）。

    只使用分型器**已有输出**（knowledge_type / type_confidence），不重新定义分型规则。
    """
    items = list(clauses)
    dist: dict[str, int] = {}
    confs: list[float] = []
    low = 0
    for c in items:
        kt = str(c.get("knowledge_type") or "unknown")
        dist[kt] = dist.get(kt, 0) + 1
        cf = float(c.get("type_confidence") or 0.0)
        confs.append(cf)
        if cf < THRESHOLDS["low_type_confidence"]:
            low += 1
    return {
        "total": len(items),
        "distribution": dist,
        "low_type_confidence": low,
        "low_type_confidence_ratio": round(low / len(items), 4) if items else 0.0,
        "type_confidence_median": round(statistics.median(confs), 4) if confs else 0.0,
        "doc_type_used": doc_type,
    }


def legal_element_quality(clauses: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """法理要素抽取质量评估（R27 v4.3 新增）。

    **要素口径**：全部取自引擎既有的抽取器输出（`build_clause_models` 落进 ClauseRevisionModel
    的那几个字段，源自 `classify_clause` 的 `TypedClause`）——模态词/强度、义务主体（subject）、
    但书（exception）、内部引用（cross_refs）、外部法规引用（legal_refs）。**不在此另造规则**。

    （2026-09-11 更正：早先本函数只统计模态词并声称"其余要素尚无所有者"——那是错的，
    `TypedClause` 一直在产出 subject/exception/cross_refs。verifier 审计 P0-3 一并纠正。）
    """
    items = list(clauses)
    total = len(items)
    with_modality = [c for c in items if c.get("modality")]
    strengths = [int(c["modality_strength"]) for c in with_modality
                 if c.get("modality_strength") is not None]
    dist: dict[str, int] = {}
    for c in with_modality:
        m = str(c.get("modality"))
        dist[m] = dist.get(m, 0) + 1

    def _ratio(n: int) -> float:
        return round(n / total, 4) if total else 0.0

    n_subject = sum(1 for c in items if c.get("subject"))
    n_exception = sum(1 for c in items if c.get("exception"))
    n_cross = sum(1 for c in items if int(c.get("cross_refs_count") or 0) > 0)
    n_external = sum(1 for c in items if int(c.get("external_refs_count") or 0) > 0)
    return {
        "total": total,
        "with_modality": len(with_modality),
        "with_modality_ratio": _ratio(len(with_modality)),
        "modality_distribution": dist,
        "modality_strength_median": (round(statistics.median(strengths), 2) if strengths else None),
        "strong_modality_count": sum(1 for s in strengths if s >= 4),
        "with_subject": n_subject, "with_subject_ratio": _ratio(n_subject),
        "with_exception": n_exception, "with_exception_ratio": _ratio(n_exception),
        "with_cross_ref": n_cross, "with_cross_ref_ratio": _ratio(n_cross),
        "with_external_ref": n_external, "with_external_ref_ratio": _ratio(n_external),
        # 一个粗粒度"要素提取完备度"：至少抽到一种法理要素的条款占比
        "element_coverage_ratio": _ratio(sum(
            1 for c in items if c.get("modality") or c.get("subject") or c.get("exception")
            or int(c.get("cross_refs_count") or 0) > 0
            or int(c.get("external_refs_count") or 0) > 0)),
    }


def one_line_summary(report: dict[str, Any]) -> str:
    """批量分桶用的一行摘要（稳定格式，测试锁定）。"""
    lay = report.get("layout") or {}
    typed = (report.get("typing_quality") or {}).get("distribution") or {}
    dist = "/".join(f"{k}{v}" for k, v in sorted(typed.items())) or "-"
    suspects = len(report.get("ocr_suspects") or [])
    reasons = (report.get("verdict_reasons") or [{}])[0].get("code", "-")
    return (f"{report.get('grade', '?')}级 · {lay.get('pages', 0)}页 · "
            f"{report.get('total_clauses', 0)}条 · 可疑{suspects} · {dist} · {reasons}")
