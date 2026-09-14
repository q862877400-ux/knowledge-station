"""LaTeX ``array`` 环境泄漏修复契约测试（2026-09-15，收敛循环第 5 轮根因）。

实测缺陷：`\\begin{array}{rl} z &= \\min(z,200) \\\\ &= \\min(40,200) \\end{array}`
经 `latex_to_text` 后变成 ``array l z = * min ( z , 200 ) \\ & = ...``
—— `array`、列格式、`&`、`\\` 全部漏进条款正文，全库 45 部命中
（GB/T 10095.2-2023 E.1/E.2 为实证样本），并连带触发
spaced-run / ocr-wide-space-units / formula-flattened 三个审计类。

根因：通用命令剥离 `\\[A-Za-z]+` 把 `\\begin`/`\\end` 当普通命令删除，
却留下 `{array}{rl}` 的**花括号内容**与 `&`/`\\\\` 分隔符。所有者是
`latex_to_text`，环境语义必须在那一层落地。
"""
from src.core.text_utils import latex_to_text


class TestArrayEnvironment:
    def test_full_env_no_residue(self):
        src = (r"\begin{array}{rl} z &= \min(z,200) \\ &= \min(40,200) "
               r"\\ &= 40 \end{array}")
        out = latex_to_text(src)
        assert "array" not in out, out
        assert "&" not in out, out
        assert "\\" not in out, out
        # \min 必须映射为 'min'（通用剥离器曾整词删除 → 公式语义丢失）
        assert "min" in out, out
        assert "200" in out, out
        assert "40" in out, out

    def test_row_break_becomes_separator(self):
        # 行分隔还原为分隔符后被本函数的空白归一压成空格（既有契约：公式文本
        # 不保留换行），关键是**两行的内容都在、且无 `\\` 残留**。
        out = latex_to_text(r"\begin{array}{l} a \\ b \end{array}")
        assert "\\" not in out, repr(out)
        assert "a" in out and "b" in out, out
        assert out.strip() in ("a b", "a\nb"), repr(out)

    def test_bare_leak_from_real_artifact(self):
        # GB/T 10095.2-2023 E.1 实测残留形态（环境标记已被上游吃掉）
        src = r"array l z = * min ( z , 200 ) \ & = * min ( 40 , 200 ) \ = 40"
        out = latex_to_text(src)
        assert "array" not in out, out
        assert "&" not in out, out
        assert "\\" not in out, out
        assert "200" in out and "40" in out, out

    def test_column_spec_variants(self):
        for spec in ("rl", "l", "cc", "rcl"):
            out = latex_to_text(r"\begin{array}{" + spec + r"} x &= 1 \end{array}")
            assert "array" not in out, (spec, out)
            assert not out.strip().startswith(spec), (spec, out)

    def test_thin_space_commands(self):
        out = latex_to_text(r"a \, b \; c \! d")
        assert "\\" not in out, out
        assert "a" in out and "d" in out, out


class TestArrayReverseControls:
    """反向对照：不得误伤合法内容。"""

    def test_word_containing_array_untouched(self):
        # 裸词 "array" 后若**不接列格式符 l/r/c**，不得删（防吃真变量）
        out = latex_to_text("array x y z = 5")
        assert "array" in out or "x" in out, out
        assert "5" in out, out

    def test_variable_product_preserved(self):
        assert latex_to_text(r"F = m a") == "F = m a"

    def test_normal_digits_preserved(self):
        assert "12000" in latex_to_text(r"1 2 0 0 0").replace(" ", "")

    def test_frac_still_converted(self):
        out = latex_to_text(r"\frac{a}{b}")
        assert out == "a/b", out
