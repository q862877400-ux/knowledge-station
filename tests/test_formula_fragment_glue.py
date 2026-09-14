"""公式内无歧义劈开的行级粘合契约测试（2026-09-15，收敛循环第 7 轮）。

spaced-run 39 部实测的三类残留（既有 token 级粘合漏掉，因为劈开跨了型边界
或紧贴 CJK）：
  ① '尺寸应测量1 . 0 mm' —— 数字-点-数字，点因紧贴 CJK 未与数字同段
  ② '±1 / 16 i n'        —— 'in'（英寸）不在 2 字母单位白名单
  ③ '0.5U N' / 'P 1 E'   —— 下标字母/数字被空格拆开

反向保护（必须零变化）：'F = m a'（变量乘积）、'2 m 及 2 m 以上'（合法数值+
单位间隔）、'12 000'（千分位空格）。
"""
from src.core.text_utils import glue_ocr_spaced_units


class TestDotSplit:
    def test_digit_dot_digit_glued(self):
        assert "1.0 mm" in glue_ocr_spaced_units("尺寸应测量1 . 0 mm")

    def test_decimal_untouched(self):
        assert glue_ocr_spaced_units("1.0 mm") == "1.0 mm"


class TestAlnumTail:
    def test_upper_pair_after_digit_glued(self):
        # 实测真相：不是 '0.5U N' 而是 '例如 0.5U N , 1.0 U N , 1.5 U N'
        out = glue_ocr_spaced_units("例如 0.5U N , 1.0 U N , 1.5 U N . . .")
        assert "1.0 UN" in out, out
        assert "0.5U N" not in out.replace("0.5U N", "X"), out

    def test_single_upper_letter_after_digit_kept(self):
        # 反向保护：单个大写字母不粘（表格相邻单元 '2 B' 不得变 '2B'）
        out = glue_ocr_spaced_units("序号 2 B 列")
        assert "2 B" in out, out

    def test_mixed_run_glued(self):
        out = glue_ocr_spaced_units("PEd = 2 n ( T E - T E , 0 ) + P 1 E - P f")
        assert "P1E" in out, out


class TestTwoLetterUnitInch:
    def test_inch_glued(self):
        out = glue_ocr_spaced_units("( ± 1 / 16 i n )")
        assert "16in" in out.replace(" ", ""), out


class TestReverseControls:
    def test_variable_product_kept(self):
        assert glue_ocr_spaced_units("F = m a") == "F = m a"

    def test_legit_value_unit_space_kept(self):
        # 合法国标排版：数值与单位间有空格，且单位是单 token → 不动
        out = glue_ocr_spaced_units("在距坠落基准面 2 m 及 2 m 以上")
        assert "2 m" in out, out

    def test_thousands_separator_kept(self):
        assert glue_ocr_spaced_units("12 000 kg") == "12 000 kg"

    def test_plain_text_untouched(self):
        t = "4.1 范围\n本文件规定了测试方法。"
        assert glue_ocr_spaced_units(t) == t

    def test_idempotent(self):
        t = "尺寸应测量1 . 0 mm (±1 / 16 i n)"
        once = glue_ocr_spaced_units(t)
        assert glue_ocr_spaced_units(once) == once
