"""闸门 5：数值片段不得冒充条款头（2026-09-15，收敛循环第 9 轮根因）。

收敛循环第 9 轮触发类 `spurious-clause-number`（18 部），逐部取证后发现
真实机理比类名更宽：**「数值 + 单位」的句子片段被切成条款**——
  '1.5cm/m。'                        (GB/T1019-2008)
  '1.293 kg/m³。'                    (GB/T 10606-2023)
  '1.00mL，用40%乙醇溶液稀释至刻度。' (GB/T 11856-2008 / 11858-2008)
  '2.0mmol/L氯化镁、0.2mmol/LdNTPs…' (GB/T 10029-2010)
  '1.0m/s<v≤2.0 m/s时不应小于 0.50 m/s2…' (GB/T 10058-2023)
  '1.5m×全幅，应在距匹端至少2m处裁取。' (GB/T 12705.1-2024)
  '1.0 mm 模数直齿轮的 R34、R44 及 R50 级公差值曲线图' (GB/T 10095.2-2023)

既有闸门 3 只认「单位**紧跟中文**」（'1.5m时'），故上列全部漏网。
"""
from src.core.ingestion.pipeline import _plausible_clause_head


class TestValueFragmentRejected:
    def _rej(self, rest):
        assert not _plausible_clause_head("1.5", rest), rest

    def test_unit_slash_unit(self):
        self._rej("cm/m。")

    def test_unit_with_cjk_punct(self):
        self._rej("mL，用40%乙醇溶液稀释至刻度。")

    def test_compound_unit_slash(self):
        self._rej("kg/m³。")

    def test_inequality_expression(self):
        self._rej("m/s<v≤2.0 m/s时不应小于 0.50 m/s2，")

    def test_unit_times_cjk(self):
        self._rej("m×全幅，应在距匹端至少2m处裁取。")

    def test_unit_space_cjk(self):
        self._rej("mm 模数直齿轮的 R34、R44 及 R50 级公差值曲线图")

    def test_conc_mmol(self):
        self._rej("mmol/L氯化镁、0.2mmol/LdNTPs、")

    def test_value_only_line(self):
        assert not _plausible_clause_head("1.5", "mm²")


class TestReverseControls:
    """反向对照：合法条款头不得被误拒。"""

    def test_english_abbrev_title_kept(self):
        # '3.4 ppm parts per million' 是合法术语条（GB/T 12918-2023 实测）
        assert _plausible_clause_head("3.4", "ppm parts per million")

    def test_latin_started_title_kept(self):
        assert _plausible_clause_head("4.1", "pH的测定")
        assert _plausible_clause_head("4.2", "PVC 树脂应符合 GB/T 5761 的要求")
        assert _plausible_clause_head("4.2", "MFR 的测定")

    def test_type_label_kept(self):
        # 大写单字母是"型号标签"而非单位（故单位表不收大写单字母）
        assert _plausible_clause_head("1.1", "A 型结构")

    def test_cjk_title_kept(self):
        assert _plausible_clause_head("3.1", "术语和定义")
        assert _plausible_clause_head("5.1", "试验样机")

    def test_tabular_rest_still_rejected(self):
        assert not _plausible_clause_head("4.2", "1.5 3.0")
