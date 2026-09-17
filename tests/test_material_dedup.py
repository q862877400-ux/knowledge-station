# -*- coding: utf-8 -*-
"""近重复检测测试（`src/core/materials/dedup.py`）。

用途是**收紧**"≥2 个独立来源"这条核心纪律：一稿多发不算多源互证。
故这里既测"它抓得住什么"，也测**它的诚实边界**（改写过的独立报道必须**不**被判为重复——
否则会把真正的互证也一起掐掉，那比假互证更糟：用户会以为没有来源支持）。
"""
from __future__ import annotations

import pytest

from src.core.materials import dedup


class TestNormalize:
    def test_punctuation_and_whitespace_are_dropped(self):
        assert dedup.normalize_text("据通报，住宿标准 每晚 800 元。") == \
            dedup.normalize_text("据通报住宿标准每晚800元")

    def test_fullwidth_folds_to_halfwidth(self):
        # NFKC：全角数字/字母折叠（转载常见差异）
        assert dedup.normalize_text("ＡＢＣ１２３") == "abc123"

    def test_case_folds(self):
        assert dedup.normalize_text("GB 30871") == dedup.normalize_text("gb 30871")

    def test_empty_inputs_are_empty(self):
        assert dedup.normalize_text(None) == ""
        assert dedup.normalize_text("   ") == ""


class TestSimilarity:
    def test_identical_is_one(self):
        assert dedup.similarity("abcde" * 5, "abcde" * 5) == 1.0

    def test_punctuation_only_change_is_near_one(self):
        a = "据通报，住宿标准每晚不超过八百元，自下月起执行。"
        b = "据通报 住宿标准每晚不超过八百元 自下月起执行"
        assert dedup.similarity(a, b) == 1.0

    def test_one_word_changed_stays_a_near_duplicate(self):
        """改一两个词仍是"同一篇稿子"（**判据是阈值，不是 0.9**）。

        ⚠ 我最初把断言写成 `> 0.9`（拍脑袋的期望），实测是 **0.857** —— 期望错了，
        代码是对的。改成断言**它真正要保证的性质**：仍在阈值之上。
        """
        a = "据当地通报，住宿标准每晚不超过八百元，自下月起执行，适用于全体职工。"
        b = "据当地通报，住宿标准每晚不超过八百元，自下月起执行，适用于全体员工。"
        sim = dedup.similarity(a, b)
        assert sim >= dedup.DEFAULT_THRESHOLD, f"相似度 {sim} 掉到阈值下，转载会漏判"
        assert dedup.near_duplicate(a, b) is True

    def test_different_wording_is_low(self):
        """**改写过的独立报道必须被判为不同**（否则会掐掉真互证）。"""
        a = "据当地通报，住宿标准每晚不超过八百元，自下月起执行，适用于全体职工。"
        b = "有关部门答复称，住宿费用上限调整为八百元一晚，新标准即将生效。"
        assert dedup.similarity(a, b) < dedup.DEFAULT_THRESHOLD

    def test_unrelated_text_is_low(self):
        assert dedup.similarity("动火作业应办理审批手续", "住宿标准每晚八百元") < 0.3

    def test_short_texts_fall_back_to_equality(self):
        """短文本（< 3n）不做 n-gram：相等=1，不等=0（样本太短，Jaccard 不稳定）。"""
        assert dedup.similarity("住宿标准", "住宿标准") == 1.0
        assert dedup.similarity("住宿标准", "餐饮标准") == 0.0

    def test_one_side_empty_is_zero_except_both_empty(self):
        assert dedup.similarity("", "abcde" * 5) == 0.0
        # 两侧都为空 → 1.0（对互证而言它们同样提供不了独立信息）
        assert dedup.similarity("", "") == 1.0

    def test_empty_against_empty_normalized(self):
        # 只有标点的文本归一化后为空
        assert dedup.similarity("。。。", "") == 1.0

    def test_threshold_is_configurable(self):
        """阈值可调，且**行为随阈值单调**（用实测相似度定位，不靠我猜具体数值）。

        ⚠ 第一版我拿一对文本断言"0.5 松 / 0.999 严"，结果它对 0.5 就已经是 False
        ——我的期望又错了。改成**性质断言**：以实测相似度为界，两侧行为必须相反。
        """
        a = "据当地通报，住宿标准每晚不超过八百元，自下月起执行，适用于全体职工。"
        b = "据当地通报，住宿标准每晚不超过八百元，下月起执行，适用全体职工。"
        sim = dedup.similarity(a, b)
        assert 0.0 < sim < 1.0, f"这对应是部分相似（实测 {sim}），才适合测阈值边界"
        assert dedup.near_duplicate(a, b, threshold=min(0.99, sim + 0.01)) is False
        assert dedup.near_duplicate(a, b, threshold=max(0.01, sim - 0.01)) is True


class TestGroupByContent:
    def test_identical_texts_group_together(self):
        assert dedup.group_by_content(["同一段话" * 20, "同一段话" * 20]) == [[0, 1]]

    def test_distinct_texts_stay_separate(self):
        groups = dedup.group_by_content([
            "据当地通报，住宿标准每晚不超过八百元，自下月起执行，适用于全体职工。",
            "有关部门答复称，住宿费用上限调整为八百元一晚，新标准即将生效。",
        ])
        assert groups == [[0], [1]]

    def test_output_is_deterministic(self):
        texts = ["甲" * 30, "甲" * 30, "乙" * 30]
        assert dedup.group_by_content(texts) == dedup.group_by_content(texts)

    def test_empty_input(self):
        assert dedup.group_by_content([]) == []


class TestIndependentSourceCount:
    """**域名图**的连通分量（不是内容分组的个数——那是第一版的错）。"""

    def test_syndicated_pair_counts_as_one(self):
        same = "据通报，住宿标准每晚不超过八百元，自下月起执行。"
        n, groups = dedup.independent_source_count(
            ["a.com", "b.com"], [same, same])
        assert n == 1
        assert groups == [["a.com", "b.com"]]

    def test_two_genuinely_different_reports_count_as_two(self):
        n, _ = dedup.independent_source_count(
            ["a.com", "b.com"],
            ["据当地通报，住宿标准每晚不超过八百元，自下月起执行，适用于全体职工。",
             "有关部门答复称，住宿费用上限调整为八百元一晚，新标准即将生效。"])
        assert n == 2

    def test_same_domain_two_articles_is_ONE_source(self):
        """同一家媒体的两篇不同文章 = 一个来源（节点语义，不是内容分组数）。"""
        n, groups = dedup.independent_source_count(
            ["a.com", "a.com"],
            ["据当地通报，住宿标准每晚不超过八百元，自下月起执行，适用于全体职工。",
             "有关部门答复称，住宿费用上限调整为八百元一晚，新标准即将生效。"])
        assert n == 1
        assert groups == [["a.com"]]

    def test_syndicated_pair_plus_a_second_real_source(self):
        x = "据通报，住宿标准每晚不超过八百元，自下月起执行。"
        y = "有关部门答复称，住宿费用上限调整为八百元一晚，新标准即将生效。"
        n, groups = dedup.independent_source_count(
            ["a.com", "b.com", "c.com"], [x, x, y])
        assert n == 2
        assert groups == [["a.com", "b.com"], ["c.com"]]

    def test_unknown_identity_is_excluded(self):
        """无域名的条目**不参与**（它们本来就不能互证，判据在 authority 那一层）。"""
        n, groups = dedup.independent_source_count(
            [None, "a.com"], ["任意文本" * 10, "任意文本" * 10])
        assert n == 1
        assert groups == [["a.com"]]

    def test_all_unknown_gives_zero(self):
        assert dedup.independent_source_count([None, None], ["x" * 30, "x" * 30]) == (0, [])

    def test_transitivity_is_handled_by_components(self):
        """近似关系不传递（A≈B、B≈C 但 A≉C）——连通分量把它们并成一组（可复现的定义）。"""
        a = "前缀甲" + "共同段落" * 8
        b = "共同段落" * 8 + "后缀乙"
        # a 与 b 的相似度中等，但都各自与 c 高度相似时，三者应在同一分量里
        c = "共同段落" * 8
        n, groups = dedup.independent_source_count(
            ["a.com", "b.com", "c.com"], [a, b, c], threshold=0.4)
        assert n == 1, groups


class TestHonestLimits:
    def test_heavy_rewrite_is_not_detected(self):
        """**已知边界**：把通稿大改一遍后重发，本模块**抓不到**（判据只是"文字近似"）。

        这条不是缺陷而是**边界**——把它写出来，免得有人以为这是查重/辟谣工具。
        """
        origin = "据当地通报，住宿标准每晚不超过八百元，自下月起执行，适用于全体职工。"
        rewrite = ("记者近日从相关渠道了解到，有关住宿费用的报销上限将有所调整，"
                   "具体数额为每夜八百元，并计划于下个月开始正式施行。")
        assert dedup.similarity(origin, rewrite) < dedup.DEFAULT_THRESHOLD

    def test_threshold_is_documented(self):
        # 阈值是启发式，必须能被引用到（而不是散落在调用处的魔数）
        assert 0.0 < dedup.DEFAULT_THRESHOLD <= 1.0
        assert dedup.DEFAULT_NGRAM >= 2

    @pytest.mark.parametrize("bad", ["", None])
    def test_never_raises_on_missing_input(self, bad):
        assert isinstance(dedup.similarity(bad, bad), float)
        assert isinstance(dedup.near_duplicate(bad, bad), bool)
