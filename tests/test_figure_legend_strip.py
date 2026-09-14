"""图例段切除契约测试（2026-09-15，收敛循环第 6 轮根因）。

实测缺陷（GB/T 10002.2-2023 B.2.1.1/B.2.1.2，全库 33 部命中 figure-neighborhood）：
MinerU 把 **条款正文 + 图例 + 图注** 压进同一个文本块，图例（「标引序号说明」及
条目）随之混入条款正文。既有 `_is_figure_legend` 漏判两条：
① 图例头不在块首；② 条目是符号（dₙ₁/Z）而非数字，数字型 `_RE_LEGEND_ITEM`
数不到。故须在文本清洗层按行切段，而不是只靠"不吸收图例块"。
"""
from src.core.ingestion.pipeline import strip_figure_legend_segment


class TestLegendSegmentStripped:
    def test_real_artifact_shape(self):
        t = ("B.2.1.2 异径接头\n"
             "异径长接头的计算值和推荐偏差见表 B.4，异径短接头的的计算值和推荐偏差"
             "见表 B.5。\n"
             "标引序号说明：\n"
             "dₙ₁ 、 dₙ₂ ——与异径长接头连接管材的公称外径；\n"
             "Z ——安装长度。")
        out = strip_figure_legend_segment(t)
        assert "标引序号说明" not in out, out
        assert "——" not in out, out
        assert "B.2.1.2 异径接头" in out
        assert "见表 B.5。" in out

    def test_caption_terminates_segment(self):
        t = ("B.2.1.1 弯头\n见表 B.3。\n标引序号说明：\n"
             "1——弯头；\n2——三通。\n图 B.2 示意图\n其余正文保留。")
        out = strip_figure_legend_segment(t)
        assert "标引序号说明" not in out, out
        assert "图 B.2 示意图" in out, out
        assert "其余正文保留。" in out, out

    def test_two_segments_in_one_block(self):
        # B.2.1.2 实测：图注在图例**前**，其后又有一段图例 → 需迭代切除
        t = ("B.2.1.2 异径接头\n见表 B.5。\n图 B.4 示意图\n"
             "标引序号说明：\ndₙ₁ ——外径；\n"
             "图 B.5 另一图\n标引序号说明：\nZ ——安装长度。")
        out = strip_figure_legend_segment(t)
        assert "标引序号说明" not in out, out
        assert "B.2.1.2 异径接头" in out and "见表 B.5。" in out
        assert "图 B.4 示意图" in out

    def test_idempotent(self):
        t = "A\n标引序号说明：\n1——a；\n2——b。"
        once = strip_figure_legend_segment(t)
        assert strip_figure_legend_segment(once) == once


class TestLegendReverseControls:
    """反向对照：不得误切没有图例实体的正文。"""

    def test_head_without_entries_kept(self):
        # 只有"标引序号说明"字样、后面没有 `——` 条目 → 原样保留
        t = "5.1 试验方法\n标引序号说明见附录 A，按图 3 执行。"
        assert strip_figure_legend_segment(t) == t

    def test_dash_line_without_head_kept(self):
        t = "5.2 连接\nA——B 表示两端对应连接，见表 A.1。"
        assert strip_figure_legend_segment(t) == t

    def test_plain_text_untouched(self):
        t = "4.1 范围\n本文件规定了测试方法。"
        assert strip_figure_legend_segment(t) == t

    def test_empty(self):
        assert strip_figure_legend_segment("") == ""
