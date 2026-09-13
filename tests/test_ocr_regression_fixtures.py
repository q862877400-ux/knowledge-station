"""0b · 9 历史文档 OCR 错误回归 fixture（执行计划 v3 阶段 0b，2026-09-14）。

设计依据：var/tmp/ocr-capability-baseline.md「历史错误样本库」节 + 评审 O(b) 三类断言。
断言形态（单元级，纯函数、零 DB 依赖——语料级规则防「同形态错误再发」）：
  - 正向：已知坑的修复形态必须出现（如 30871 9.1 的 ≤slant → ≤）
  - 负向：输出不得含错误形态（≤slant、A°、PUA 犬部码位）
  - 性质：PUA 归一化产物无犬部码位残留、数学符号表长键优先

覆盖的 9 个历史文档坑（fixture 按坑组织，非按文档组织——坑是回归单元）：
  GB 30871-2022  ① ≤slant 泄漏  ② 宽字距公式数字
  GB/T 34406     ③ PUA 犬部+槡√ ④ Aₑ→度符号误识(C5) ⑤ 化学基团 PUA 键线
                  ⑥ 式中说明行 hat/bar  ⑦ 水印行剥离
  GB/T 24276     ⑧ LaTeX 符号表缺漏（希腊/微等）
  GB/T 1000-2016 ⑨ CID '('→'7' 整体错位判据（防误伤正常标点）
运行时机：升档（阶段 1）前先跑本套 = 固化旧模型行为基线；升档后误红 → 白名单评审
区分「模型换代（可接受，修 fixture）」vs「真回归（必须修代码）」。
"""
from __future__ import annotations

import pytest

from src.core.text_utils import (
    clean_eq_tags,
    latex_to_text,
    normalize_pua_latin,
    strip_block_noise,
)

# 犬部 PUA 码位全集（负向断言用：任何清洗产物不得残留）
_PUA_DOG_CHARS = "犃犅犆犇犈犉犌犎犐犑犓犔犕犖犗犘犙犚犛犜犝犞犠犡犢犣犪犫犮犱犲犳犵犺犻犼犽犾犿狀狅狆狇狉狊狋狌狏狑狓狔狕"


# =====================================================================
# 坑① GB 30871-2022 9.1 —— \leqslant 剥反斜杠泄漏 '≤slant'
# =====================================================================
class TestLeqslantLeak:
    def test_positive_clean(self):
        """修复形态：泄漏形态归一到 ≤。"""
        assert latex_to_text("\\leqslant 40") == "≤ 40"

    def test_negative_leaked_form(self):
        """负向：清洗产物不得含 ≤slant / ≥slant。"""
        out = latex_to_text("\\leqslant m \\geqslant 100")
        assert "≤slant" not in out and "≥slant" not in out
        assert out == "≤ m ≥ 100"

    def test_eq_tag_path(self):
        """行内公式 <eq>…</eq> 全链路同样不泄漏（入库路径）。"""
        html = "<p>4 0 t <eq>\\leqslant</eq> m <eq>\\leqslant</eq> 1 0 0 t</p>"
        out = clean_eq_tags(html)
        assert "≤" in out and "slant" not in out


# =====================================================================
# 坑② GB 30871-2022 —— 宽字距数字被 OCR 切开 "4 0 t"
# =====================================================================
class TestWideSpacedDigits:
    def test_property_digit_glue(self):
        """性质：数字间单空格形态应被粘合（宽字距还原）。
        ≤ 是断点 token（非单字符）→ 触发 flush，符号前后保留空格是规则本意；
        断言聚焦坑本身：40t 与 100t 必须粘回。"""
        from src.core.text_utils import glue_spaced_formulas
        out = glue_spaced_formulas("4 0 t ≤ m ≤ 1 0 0 t")
        assert "40t" in out and "100t" in out
        assert "4 0" not in out and "1 0 0" not in out


# =====================================================================
# 坑③ GB/T 34406 —— PUA 犬部错位文本层（'GB/T'→'犌犅／犜'、'0'→'!'）
# =====================================================================
class TestPuaNormalize:
    def test_positive_recover(self):
        """修复形态：犬部+数字平移整体还原。"""
        s = "犌犅／犜 !"  # 'GB/T 0'
        out = normalize_pua_latin(s)
        assert out == "GB/T 0"

    def test_property_no_pua_residue(self):
        """性质：任何 PUA 输入归一化后无犬部码位残留。"""
        s = "犌犅／犜犐犱犲狀狋犻犳犻犮犪狋犻狅狀 !\"#"
        out = normalize_pua_latin(s)
        assert not any(ch in out for ch in _PUA_DOG_CHARS)
        assert out.startswith("GB/T")

    def test_positive_sqrt_body(self):
        """修复形态：根号 PUA 替身 '槡' → '√'（34406 公式区实测）。"""
        assert "√" in normalize_pua_latin("槡(1-∑)")

    def test_property_ascii_digits_restored(self):
        """性质：0x21-0x2A 平移区字符全部还原为数字（无一漏网）。"""
        shifted = "".join(chr(0x21 + i) for i in range(10))  # !\"#$%&'()*
        out = normalize_pua_latin(shifted)
        assert out == "0123456789"


# =====================================================================
# 坑④ GB/T 34406 —— Aₑ 下标被误识为度符号（C5）
# 判据（_RE_AREA_SUB）：A° 后接面积量纲（>数值）或「面积」上下文才转，
# 保守防误伤角度 A°。fixture 用真实判据形态。
# =====================================================================
class TestAreaSubscript:
    def test_positive_sub(self):
        """修复形态：面积判据（>数值）下 A° → Aₑ。"""
        from src.core.text_utils import normalize_area_subscript
        out = normalize_area_subscript("A ° > 1.25 m²")
        assert "Aₑ" in out and "A°" not in out

    def test_positive_area_context(self):
        """修复形态：'有效散热面积'上下文同样转换。"""
        from src.core.text_utils import normalize_area_subscript
        out = normalize_area_subscript("A°为有效散热面积")
        assert "Aₑ" in out

    def test_negative_angle_untouched(self):
        """负向（防误伤）：无面积判据的角度 A° 不转。"""
        from src.core.text_utils import normalize_area_subscript
        s = "旋转角为 30°，偏差 A° 不在此列"
        assert normalize_area_subscript(s) == s


# =====================================================================
# 坑⑤ GB/T 34406 §4 —— 化学基团 PUA 键线（\ue5c6CH → —CH）
# =====================================================================
class TestChemBondDash:
    def test_positive_bond(self):
        """修复形态：PUA 键 → em dash。"""
        from src.core.text_utils import pua_bond_dash_html
        out = pua_bond_dash_html("<p>利用有机质中\ue5c6CH、\ue5c6NH、\ue5c6OH等基团</p>")
        assert "中—CH、—NH、—OH等" in out

    def test_negative_no_raw_pua(self):
        """负向：键线产物不得残留 \ue5c6 原码位。"""
        from src.core.text_utils import pua_bond_dash_html
        out = pua_bond_dash_html("<p>中\ue5c6CH</p>")
        assert "\ue5c6" not in out


# =====================================================================
# 坑⑥ GB/T 34406 —— 式中说明行 ^Ci/C̄i 帽/杠（hat/bar）
# =====================================================================
class TestMeaningMarks:
    def test_positive_hat_bar(self):
        from src.core.text_utils import katex_sym_html, weave_meaning_marks
        t = ("R=√(1-∑(^Ci-Ci)2/∑(Ci-Ci)2)(1)式中:^Ci———预测值; Ci———标准值;"
             " Ci———平均值。")
        html = "<p>" + weave_meaning_marks(t) + "</p>"
        out = katex_sym_html(html)
        assert 'data-tex="\\hat{C}_{i}"' in out
        assert 'data-tex="\\bar{C}_{i}"' in out


# =====================================================================
# 坑⑦ GB/T 34406 —— 盗版水印页眉（www.bzfxw.com）与页码
# =====================================================================
class TestWatermarkStrip:
    def test_positive_wm_url_gone(self):
        out = strip_block_noise("www.bzfxw.com")
        assert "bzfxw" not in out

    def test_negative_inline_url_untouched(self):
        """负向（防误伤）：行中合法 URL 引用不剥（仅整行水印语义才剥）。"""
        s = "更多信息见 www.example.com/standard 页面"
        out = strip_block_noise(s)
        assert "www.example.com" in out

    def test_property_pageno_forms_covered(self):
        """性质：全角/罗马页码形态剥后不留。"""
        for s in ("www.bzfxw.com ３", "www.bzfxw.com Ⅰ"):
            out = strip_block_noise(s)
            assert out.strip() == ""


# =====================================================================
# 坑⑧ GB/T 24276 —— LaTeX 符号表缺漏（2026-09-01 增补组）
# =====================================================================
class TestSymbolTable2026Additions:
    @pytest.mark.parametrize("tex,uni", [
        ("\\Delta", "Δ"), ("\\delta", "δ"), ("\\bullet", "•"),
        ("\\kappa", "κ"), ("\\lambda", "λ"), ("\\mu", "µ"),
        ("\\rho", "ρ"), ("\\sigma", "σ"), ("\\tau", "τ"), ("\\omega", "ω"),
    ])
    def test_symbols_present(self, tex, uni):
        """正向：24276 实测缺漏的符号全部可转换。"""
        assert latex_to_text(tex) == uni

    def test_property_word_boundary_no_eat(self):
        """性质：词边界防前缀误吃（\\pm 不吃 \\pmb；2026-09-01 修复）。"""
        assert latex_to_text("\\pm 5\\pmb{x}") == "± 5x"

    def test_long_key_priority(self):
        """性质：长键优先（\\leqslant 先于 \\leq，否则被前缀吞掉）。"""
        assert latex_to_text("a\\leqslant b") == "a≤ b"
        assert latex_to_text("a\\leq b") == "a≤ b"


# =====================================================================
# 坑⑨ GB/T 1000-2016 —— '('→'7' 整体错位误判（2026-09-02 修复）
# 真实回归单元是分拣函数 text_layer_pua_mangled：判据二须叠加
# 「正常数字占比异常低」——正常标点文本不再被判 PUA、不再被 +15 有损还原。
# =====================================================================
class TestShiftedDigitGuard:
    _NORMAL = ("作业前应对受限空间进行安全隔离（见 4.2 表 B-2）。"
               "取样点不少于 3 处!")

    def test_negative_normal_text_not_mangled(self):
        """负向（防误伤核心）：正常文本（正常标点 + 正常数字占比）判 False。"""
        from src.core.ingestion.mineru_adapter import text_layer_pua_mangled
        blocks = [{"text": self._NORMAL}] * 5
        assert text_layer_pua_mangled(blocks) is False

    def test_positive_shifted_digits_detected(self):
        """正向：真数字平移型（!-* 密集 + 正常数字≈0）仍判 True。"""
        from src.core.ingestion.mineru_adapter import text_layer_pua_mangled
        shifted = "!\"#$%&'()*!\"#$%&'()*" * 5 + "犌犅／犜 表!"
        blocks = [{"text": shifted}]
        assert text_layer_pua_mangled(blocks) is True

    def test_property_digit_ratio_gate(self):
        """性质：判据二的数字占比门槛——含足量正常数字的文本不触发整体平移判定。"""
        from src.core.ingestion.mineru_adapter import text_layer_pua_mangled
        # 括号标点不少，但正常数字也多（真实正常文档形态）→ False
        text = ("取样 12 处（每处 3 个）* 见 4.2 表 B-2* 取 0.5 mL!"
                " 复检 2 次（间隔 30 min）")
        assert text_layer_pua_mangled([{"text": text}]) is False
