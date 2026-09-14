r"""PUA 分隔符还原契约测试（2026-09-15 全库文本审计根因修复）。

背景：部分国标 PDF 文字层把**分隔符**画成私用区字形，提取后成不可见垃圾。
全库仅两个码点（27 处 / 5 部文档）：
- U+E011：日期/人名分隔位——'2009\ue01103\ue01116发布'、
  'Kennard\ue011Stone算法'
- U+E788：数值前空格位——'内径为\ue78876+2/0mm'
还原：数字↔数字 → '-'；其余 → 空格。其余私用区码点不动（未实测者不猜）。
"""
import pytest

from src.core.text_utils import normalize_pua_separators as norm


class TestSeparatorRestore:
    def test_date_separator_becomes_hyphen(self):
        assert norm("2009\ue01103\ue01116发布") == "2009-03-16发布"

    def test_name_separator_becomes_space(self):
        assert norm("运用Kennard\ue011Stone算法按7∶3") == "运用Kennard Stone算法按7∶3"

    def test_value_prefix_separator_becomes_space(self):
        assert norm("内径为\ue78876+2/0mm或\ue788152+2/0mm") == "内径为 76+2/0mm或 152+2/0mm"

    def test_consecutive_codepoints_all_handled(self):
        # 相邻 PUA 不得漏判（逐字符判定，不受前一个匹配消费影响）
        assert norm("1\ue0112\ue0113") == "1-2-3"


class TestNoRegression:
    def test_plain_text_unchanged(self):
        assert norm("正常文本无PUA") == "正常文本无PUA"
        assert norm("GB/T 10002.1-2023 给水用硬聚氯乙烯（PVC-U）管材") == \
            "GB/T 10002.1-2023 给水用硬聚氯乙烯（PVC-U）管材"

    def test_empty(self):
        assert norm("") == ""
        assert norm(None) == ""

    def test_other_pua_untouched(self):
        # 未实测的私用区码点不猜（犬部形近区由 normalize_pua_latin 负责）
        assert norm("犌犅") == "犌犅"
        assert norm("a\ue999b") == "a\ue999b"

    def test_idempotent(self):
        once = norm("2009\ue01103\ue01116发布")
        assert norm(once) == once
