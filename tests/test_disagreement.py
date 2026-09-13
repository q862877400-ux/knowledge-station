"""阶段2c 分歧检测单测（纯函数面：O2 fallback / 相似度 / 报告装配）。
不触网、不落库——云外发由编排层（后续接入点）走 egress_audit。"""
from __future__ import annotations

from src.core.quality.disagreement import (
    DISAGREE_RATIO,
    DisagreementReport,
    build_disagreement_report,
    compare_clause_texts,
    report_to_dict,
    score_distribution_collapsed,
    select_2c_input,
    text_similarity,
)


class TestO2Fallback:
    def test_collapsed_when_dominant_high(self):
        # >0.95 占 96% → 坍缩
        assert score_distribution_collapsed([0.99] * 96 + [0.5] * 4)

    def test_not_collapsed_when_mixed(self):
        # A 侧实测分布（GB/T 1032：459/3974 低分 ≈ 11.5% 低分）→ 不坍缩
        assert not score_distribution_collapsed([0.99] * 88 + [0.6] * 12)

    def test_empty_scores_is_collapsed(self):
        assert score_distribution_collapsed([])

    def test_select_2c_input_score_mode(self):
        cls = [{"clause_number": "5.1", "ocr_confidence": 0.7},
               {"clause_number": "5.2", "ocr_confidence": 0.99}]
        picked, mode = select_2c_input(cls, all_span_scores=[0.6, 0.9])
        assert mode == "score"
        assert [c["clause_number"] for c in picked] == ["5.1"]

    def test_select_2c_input_legacy_when_collapsed(self):
        cls = [{"clause_number": "5.1", "ocr_confidence": 0.7}]
        picked, mode = select_2c_input(
            cls, all_span_scores=[0.99] * 100,
            legacy_suspects=["4.2.3", "6.1"])
        assert mode == "legacy_suspects"
        assert picked[0]["input_mode"] == "legacy"


class TestSimilarity:
    def test_identical(self):
        assert text_similarity("动火作业应办理许可证", "动火作业应办理许可证") == 1.0

    def test_whitespace_insensitive(self):
        assert text_similarity("40 t ≤ m", "40t≤m") == 1.0

    def test_totally_different(self):
        assert text_similarity("AAAAAAAA", "BBBBBBBB") < 0.2

    def test_empty_both(self):
        assert text_similarity("", "") == 1.0

    def test_empty_one_side(self):
        assert text_similarity("abc", "") == 0.0

    def test_partial(self):
        sim = text_similarity("动火作业应办理动火许可证", "动火作业应当办理许可证")
        assert 0.6 < sim < 1.0


class TestCompare:
    def test_agree(self):
        assert compare_clause_texts("受限空间作业应先通风", "受限空间作业应先通风") == "agree"

    def test_disagree(self):
        # 完全不同文本 → disagree
        assert compare_clause_texts("动火作业分级管理", "固定动火区应设置标志") == "disagree"

    def test_threshold_semantics(self):
        v = compare_clause_texts("a" * 100, "a" * 60 + "b" * 40)
        # 60% 相同 → sim≈0.6 < 1-0.35=0.65 → disagree
        assert v == "disagree"


class TestReport:
    def _pair(self, num, local, cloud, conf=0.5):
        return ({"clause_number": num, "content_text": local,
                 "page_start": 3, "page_end": 3, "ocr_confidence": conf}, cloud)

    def test_assembly_counts(self):
        rep = build_disagreement_report("doc_x", "GB 1", [
            self._pair("5.1", "动火作业应办理许可证", "动火作业应办理许可证"),
            self._pair("5.2", "受限空间作业应通风", "完全无关的云识别文本内容"),
            self._pair("5.3", "高处作业应系安全带", None),
        ])
        assert rep.checked == 3
        assert rep.agree == 1
        assert rep.disagree == 1
        assert rep.cloud_unavailable == 1

    def test_report_dict_roundtrip(self):
        rep = build_disagreement_report("doc_x", "GB 1", [
            self._pair("5.1", "动火作业应办理许可证", "动火作业应办理许可证"),
        ])
        d = report_to_dict(rep)
        assert d["checked"] == 1 and d["agree"] == 1
        assert d["items"][0]["clause_number"] == "5.1"
        assert d["items"][0]["verdict"] == "agree"

    def test_disagree_item_captures_both_heads(self):
        rep = build_disagreement_report("doc_x", "GB 1", [
            self._pair("5.2", "本地识别文本ABC", "云端识别文本XYZ"),
        ])
        it = rep.items[0]
        assert it.verdict == "disagree"
        assert "本地识别文本" in it.local_head
        assert "云端识别文本" in it.cloud_head


class TestConstants:
    def test_disagree_ratio_sane(self):
        assert 0.0 < DISAGREE_RATIO < 1.0
