r"""公式编号引导点线清洗契约测试（2026-09-15 全库审计 dot-leader 类达线修复）。

背景：公式编号前的引导点线在文本层是 U+2026 连排（'……………( 1'），既有
_RE_FORMULA_DOTS 只认 NFKC 后 ASCII 点且未被内容清洗链调用 → 点线原样落库。
全库审计 dot-leader 类 44 部文档 167 条。

两条规则（顺序固定）：
① 点线 + 编号：**无论点数**（GB 引导线常短至 '……(7)'）→ 归一 ' (N)'，顺带补右括号
② 裸点线：≥7 ASCII 点 或 ≥4 个 '…' → 删（正文省略号 '……' 最多 2 个必须存活）
"""
import pytest

from src.core.text_utils import strip_formula_leader as S


class TestNumberedLeader:
    def test_long_u2026_leader_with_broken_number(self):
        out = S("m × 10 - ⁴ ……………( 1 / 式中：")
        assert " (1)" in out and "…" not in out

    def test_short_u2026_leader(self):
        # GB 引导线常短至 '……(7)'（2 个省略号 + 编号）——无论点数即归一
        assert S("A ₚ /A ₀ ……( 7 / 式中：") == "A ₚ /A ₀  (7)/ 式中："

    def test_ascii_dots_with_number(self):
        assert S("V1 / V2 ....(12)") == "V1 / V2  (12)"

    def test_closing_paren_already_present(self):
        assert S("x ……(3)。") == "x  (3)。"


class TestBareLeader:
    def test_ascii_dots_run_removed(self):
        assert S("W / = / P / S ..............................").strip() == "W / = / P / S"

    def test_long_u2026_run_removed(self):
        assert "…" not in S("标引…………………………………后文")


class TestProsePreserved:
    def test_two_char_ellipsis_survives(self):
        # 正文省略号 '……' 不得被当引导线删掉
        assert S("见下文……也就是说") == "见下文……也就是说"

    def test_plain_text_unchanged(self):
        assert S("公式(2)给出结果。") == "公式(2)给出结果。"

    def test_empty(self):
        assert S("") == ""
        assert S(None) == ""


class TestIdempotent:
    def test_idempotent_numbered(self):
        once = S("m × 10 - ⁴ ……………( 1 / 式中：")
        assert S(once) == once

    def test_idempotent_bare(self):
        once = S("W / V2 ....................")
        assert S(once) == once
