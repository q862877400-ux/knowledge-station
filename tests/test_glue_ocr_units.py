"""glue_ocr_spaced_units 契约测试（OCR 循环轮次 12 根因修复配套）。

锁定：OCR 逐字符拉开形态的粘合语义、分段不跨型、小数点、幂等、正常行零变化。
实测语料：GB/T 10238 油井水泥（± 2 0 0 r / * m i n）、GB/T 10058 电梯
（0 . 7 0 m / s ²0）、GB/T 10095.2 齿轮（F ᵢ d ₜ 邻域）。
"""
import pytest

from src.core.text_utils import glue_ocr_spaced_units as glue


class TestSubscriptResidue:
    """2026-09-15 残留修复：初版单字符集只有 ASCII → 下标型公式变量漏粘。
    实测 GB/T 10593.2（'S ₑ'/'C ₛ ᵢ ₜ'）、GB/T 1094.6、GB/T 10671。"""

    def test_subscript_joins_letter(self):
        assert glue("S ₑ = 1000") == "Sₑ = 1000"

    def test_multi_subscript_variable(self):
        assert glue("C ₛ ᵢ ₜ = α") == "Cₛᵢₜ = α"

    def test_product_variables(self):
        # C₁V₁ 乘积记法：下标并入、字母段连续
        assert glue("( C ₁ V ₁ - C ₀ V ₀ )") == "( C₁V₁ - C₀V₀ )"

    def test_superscript_on_unit(self):
        # 与文本层 glue 的 'm ³'→'m³' 规则对齐
        assert glue("mg / m ³ )") == "mg / m³ )"

    def test_greek_variable(self):
        assert glue("Δ t 变量") == "Δt 变量"

    def test_leading_subscript_not_merged_forward(self):
        # 段首下标遇字母 → 断段（防反序误粘）
        assert glue("ₖ 段首") == "ₖ 段首"

    def test_no_cross_type_still(self):
        # 扩展后仍不跨型（原契约不破）
        assert glue("s 7 9 mm") == "s 79 mm"


class TestGlue:
    def test_decimal_digits(self):
        # 数字段含小数点：7 8 . 2 → 78.2（文本层 glue 不吃点，OCR 版必须吃）
        assert glue("T = 7 8 . 2 + 2 0 . 0 2 B") == "T = 78.2 + 20.02 B"

    def test_two_digit_group(self):
        assert glue("7 9 m m") == "79 mm"

    def test_letter_units_min(self):
        # 字母段 ≥2 门槛：m i n → min
        assert glue("± 2 0 0 r / * m i n") == "± 200 r / * min"

    def test_letter_units_mm(self):
        # 2026-09-15 契约更新：上标并入段（'m ²'→'m²'），与文本层 glue 的
        # 'm ³'→'m³' 规则对齐——初版"上标不进段"已由残留修复取代
        assert glue("6 m m ² / s") == "6 mm² / s"

    def test_letter_units_ssu(self):
        assert glue("4 5 S S U 3 6 0 S S U") == "45 SSU 360 SSU"

    def test_type_boundary_no_cross_glue(self):
        # 型边界即词边界：数字段与字母段分别粘，不跨型粘连
        assert glue("1 5 0 r / m i n") == "150 r / min"

    def test_superscript_joins_segment(self):
        # 2026-09-15 契约更新（原 test_superscript_not_in_segment）：上标/下标
        # 并入当前段——ASCII-only 的初版漏粘下标型公式变量（10593.2/1094.6 实测）
        assert glue("6 m m ² / s") == "6 mm² / s"

    def test_normal_line_unchanged(self):
        # 正常行零变化（最关键契约——不能把好文本改坏）
        assert glue("转速为4000r/min(66.7r/s)时") == "转速为4000r/min(66.7r/s)时"
        assert glue("12 000 r/min(200r/s)") == "12 000 r/min(200r/s)"

    def test_chinese_unchanged(self):
        assert glue("采用常压稠化仪进行水泥浆的拌合") == "采用常压稠化仪进行水泥浆的拌合"

    def test_letter_pair_glues(self):
        # 字母段门槛 ≥2：两字母单位粘（mm/cm 类单位是主流实测形态）
        assert glue("A B 分级") == "AB 分级"

    def test_digit_pair_glues(self):
        # 数字段门槛 ≥2：两位数字粘
        assert glue("误差 2 5 以内") == "误差 25 以内"
    def test_idempotent(self):
        s = "± 2 0 0 r / * m i n ( ± 3 . 3 r / s );"
        once = glue(s)
        assert glue(once) == once

    def test_multiline(self):
        assert glue("a\n1 2 3 b c d") == "a\n123 bcd"

    def test_empty_and_none(self):
        assert glue("") == ""
        assert glue(None) == ""
        assert glue("无空格文本") == "无空格文本"

    def test_leading_dash_number(self):
        # GB/T 10058 实测形态邻域：'5 . 5 . 1' 型号层级（点分编号不跨段粘）
        assert glue("- 5 . 5 . 1 a )") == "- 5.5.1 a )"
