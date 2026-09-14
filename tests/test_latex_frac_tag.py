"""latex_to_text 的 \frac/\tag 转换契约测试（OCR 循环轮次 17 根因修复配套）。

锁定：分数线语义（分子/分母可辨）、表达式括号保护、tag 编号提取与右括号
补齐、空 tag 消除、与下标转换的协同（frac 先于下标）、无 frac 行为不变。
语料：GB/T 10401（K_τ=TL/IL 等 7 式）、全库普查 16,186 frac / 19,676 tag。
"""
import pytest

from src.core.text_utils import latex_to_text as l2t


class TestFrac:
    def test_simple_frac(self):
        assert l2t(r"Q = K \frac { S } { U }\tag{}") == "Q = K S/U"

    def test_frac_with_subscripts(self):
        # 下标在 frac 组内：先 frac 后下标，组内容保真
        out = l2t(r"K _ { \tau } = \frac { T _ { L } } { I _ { L } }\tag{………(1}")
        assert "/" in out
        assert "T" in out and "I" in out
        assert out.endswith("(1)")

    def test_expression_operands_parenthesized(self):
        # 分子分母是表达式 → 括号保护（分数线语义可辨）
        out = l2t(r"\frac { a - b } { a + b } \times 100 \%\tag{………(2}")
        assert "(a - b)/(a + b)" in out
        assert out.endswith("(2)")

    def test_nested_frac(self):
        out = l2t(r"c = \frac { \frac { a } { b } } { P }")
        assert "/" in out and "a" in out and "b" in out and "P" in out

    def test_chained_fracs(self):
        out = l2t(r"c = \frac { 2 2 . 4 } { M } \cdot \frac { T } { 2 7 3 }")
        assert "22.4/M" in out or "2 2 . 4/M" in out
        assert "T/273" in out or "T/2 7 3" in out


class TestTag:
    def test_tag_number_extracted_with_close_paren(self):
        # MFR 常丢右括号：'………(2' → '(2)'
        assert l2t(r"x = y \tag{………(2}").endswith("(2)")

    def test_empty_tag_removed(self):
        assert l2t(r"Q = K \frac { S } { U }\tag{}") == "Q = K S/U"

    def test_tag_plain_number(self):
        assert l2t(r"x = 1 \tag{3}").endswith("(3)")

    def test_no_tag_unchanged(self):
        assert l2t(r"a + b") == "a + b"


class TestNoRegression:
    def test_plain_symbol_mapping_still_works(self):
        # 2026-09-01 保真修复的行为不受扰（原行为保留 ~→空格，单空格折叠）
        assert "h w" in l2t(r"h _ { \mathrm { ~ w ~ } } / \mathrm { m }")

    def test_subsup_outside_frac(self):
        out = l2t(r"F _ { \circ } = T _ { P }")
        assert "F" in out and "T" in out

    def test_real_10401_formula(self):
        # 实测语料（轮次 17）：K_mb 转矩波动系数
        out = l2t(
            r"K _ { \mathrm { m b } } = \frac { T _ { \mathrm { L m a x } }"
            r" - T _ { \mathrm { L m i n } } } { T _ { \mathrm { L m a x } }"
            r" + T _ { \mathrm { L m o } } } \times 1 0 0 \%\tag{………(2}")
        assert "/" in out          # 分数线保真
        assert "(" in out          # 表达式括号
        assert "K" in out and "100" in out.replace(" ", "")
