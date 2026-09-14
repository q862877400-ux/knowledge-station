r"""latex_to_text 逐字符空格归并契约测试（2026-09-15 全库公式审计根因修复）。

背景：MinerU 的 LaTeX 对宽距字符逐字符输出空格——实测
GB/T 10541 `inline_equation` 原文 '6 1 0 ~ \mathrm{g/m^{2}}'（真值 610 g/m²）、
GB/T 11115 '6 5 0 ~ \mu\mathrm{m}\pm 1 0 0 ~\mu\mathrm{m}'（真值 650 µm±100 µm）。
修复前 latex_to_text 只折叠连续空格 → '6 1 0 g / m ²' 落库。

规则与反向保护（误合并会破坏语义，必须锁死）：
- 数字段 ≥3 单数字合并；**2 个不动**（'1/2 3' 的分母后独立数字）
- 字母段 ≥3 单字母合并；**2 个不动**（'F = m a' 变量乘积不得粘成 'ma'）
- 斜杠去空格 / 微符号贴附 / 上下标贴附 / '\%' → '%'
"""
import pytest

from src.core.text_utils import latex_to_text as l2t


class TestDigitRuns:
    def test_three_single_digits_merged(self):
        assert l2t(r"6 1 0 ~ \mathrm { g / m ^ { 2 } }") == "610 g/m²"

    def test_two_digit_run_merged_with_unit_anchor(self):
        assert l2t(r"6 5 0 ~ \mu \mathrm { m }") == "650 µm"

    def test_plain_number_run(self):
        assert l2t(r"2 7 3") == "273"

    def test_two_tokens_protected(self):
        # 分数后的独立数字不得被粘进分母
        assert l2t(r"\frac { 1 } { 2 } 3") == "1/2 3"


class TestLetterRuns:
    def test_three_letter_run_merged(self):
        assert l2t(r"\pm 2 0 0 \ \mathrm { r / m i n }") == "± 200 r/min"

    def test_kpa_merged(self):
        assert l2t(r"1 0 0 \mathrm { k P a }") == "100 kPa"

    def test_variable_product_protected(self):
        # 'F = m a'（力=质量×加速度）不得粘成 'ma'
        assert l2t(r"F = m a") == "F = m a"

    def test_two_letter_unit_not_merged(self):
        # 'h w / m' → 'h w/m'（2 字母段保护；斜杠仍去空格）
        assert l2t(r"h _ { \mathrm { ~ w ~ } } / \mathrm { m }") == "h w/m"


class TestAttachments:
    def test_superscript_attaches(self):
        assert l2t(r"m ^ { 2 }") == "m²"

    def test_micro_prefix_attaches(self):
        assert l2t(r"\mu \mathrm { m } \pm 1 0 0 ~ \mu \mathrm { m }") == "µm ± 100 µm"

    def test_subscript_chain_attaches(self):
        assert l2t(r"K _ { \mathrm { m b } }") == "Kₘb"

    def test_percent_escape(self):
        assert l2t(r"\times 1 0 0 \%") == "× 100 %"


class TestNoRegression:
    def test_symbol_mapping_intact(self):
        assert l2t(r"\leqslant 40") == "≤ 40"
        assert l2t(r"a \leqslant b") == "a ≤ b"
        assert l2t(r"\pm 5\pmb{x}") == "± 5x"

    def test_frac_still_semantic(self):
        out = l2t(r"\frac { a - b } { a + b } \tag{……(2}")
        assert "(a - b)/(a + b)" in out and out.endswith("(2)")

    def test_real_10401_formula(self):
        out = l2t(
            r"K _ { \mathrm { m b } } = \frac { T _ { \mathrm { L m a x } }"
            r" - T _ { \mathrm { L m i n } } } { T _ { \mathrm { L m a x } }"
            r" + T _ { \mathrm { L m o } } } \times 1 0 0 \%\tag{………(2}")
        assert "/" in out and "100 %" in out and "(2)" in out

    def test_idempotent(self):
        once = l2t(r"6 1 0 ~ \mathrm { g / m ^ { 2 } }")
        assert l2t(once) == once
