"""附录字母号公式引导点线契约测试（2026-09-15，VLM 通道下 dot-leader 复测）。

VLM 产物实测（GB/T 15945-2008 附录B、GB/T 10029-2010 A.1、
GB/T 10002.2-2023 B.1.1、GB/T 16422.1-2019 C.2/C.3）：公式号前的引导点线
配**附录字母号**时原样落库——既有 `_RE_FORMULA_LEADER` 只认纯数字 `(\d{1,3})`。
"""
from src.core.text_utils import strip_formula_leader


class TestAppendixLetterLeader:
    def test_letter_number_normalized(self):
        out = strip_formula_leader("Z = r ……( A.1\n下一行")
        assert "(A.1)" in out, out
        assert "……" not in out, out

    def test_multiple_letter_numbers(self):
        out = strip_formula_leader("……( B.1\n……( C.2\n")
        assert "(B.1)" in out and "(C.2)" in out, out

    def test_dotted_letter_number(self):
        out = strip_formula_leader("Δ LₚA = LₚA ……(D.7\n式中：")
        assert "(D.7)" in out, out

    def test_plain_digit_still_works(self):
        out = strip_formula_leader("x = y ………( 1\n式中：")
        assert "(1)" in out, out

    def test_idempotent(self):
        t = "Z = r ……( A.1"
        once = strip_formula_leader(t)
        assert strip_formula_leader(once) == once


class TestProseEllipsisSurvives:
    """反向对照：正文省略号必须存活（只能≤2 个 '…'）。"""

    def test_two_ellipsis_kept(self):
        t = "试验结果应符合……的规定。"
        assert strip_formula_leader(t) == t

    def test_normal_text_untouched(self):
        t = "4.1 范围\n本文件规定了测试方法。"
        assert strip_formula_leader(t) == t
