"""条款头闸门契约测试（2026-09-15，「重复条款号」根因修复配套）。

根因：OCR 折行把句子切断，续行行首恰好是被引用条款号 → 被当新条款头，
产生同号重复条款。全库实测 216 组 (doc, clause_number) 重复、17 部文档受影响。
两道判据：① rest 续行标点/连接词起头 ② 号 ≤ 最近已产出号（同文档号递增）。
配套修 _CLAUSE_GB 深度上限（5 段 → 8 段）：'8.3.1.2.3.1' 曾被截成 '8.3.1.2.3'。

实测语料（修复前 → 后）：
- GB/T 10760.2 19 组重复 → 0；GB/T 1032 13 → 0；GB/T 10357.5 5 → 0；
  GB/T 1029 4 → 0；GB/T 1094.6 4 → 0（含附录号 C.7/E.1）；GB/T 10059 2 → 0
"""
import json

from src.core.ingestion.pipeline import (
    _CLAUSE_GB, _is_continuation_head, _num_segments, load_middle_items,
    split_items_into_clauses,
)


class _Fake:
    def __init__(self, number):
        self.number = number


class TestNumSegments:
    def test_numeric(self):
        assert _num_segments("5.1.2") == (5, 1, 2)

    def test_appendix_letter(self):
        # 附录号折算为 1000+ord：A.1 < A.2 < B.1
        assert _num_segments("A.1") < _num_segments("A.2") < _num_segments("B.1")

    def test_numeric_before_appendix(self):
        assert _num_segments("5.1") < _num_segments("A.1")

    def test_unorderable(self):
        assert _num_segments("前置1") is None
        assert _num_segments("") is None


class TestContinuationShape:
    """① 形态判据：续行标点/连接词/数字起头。"""

    def test_right_paren(self):
        # GB/T 10357.5 实测：'3.18)，在距离全开位置10mm以内处关闭推拉构件。'
        assert _is_continuation_head("3.18", ")，在距离全开位置10mm以内处关闭推拉构件。", [])

    def test_tilde_range(self):
        # GB/T 10059 实测：'5.1.1~5.1.19的试验结果记入表 A.2。'
        assert _is_continuation_head("5.1.1", "~5.1.19的试验结果记入表 A.2。", [])

    def test_sentence_period(self):
        # GB/T 1094.6 实测：'12.9。如未规定频率，则制造方应选择某个合适的频率。'
        assert _is_continuation_head("12.9", "。如未规定频率，则制造方应选择某个合适的频率。", [])

    def test_connector_word(self):
        # GB/T 1032 实测：'11.6.2 或11.6.3得出的值大。'
        assert _is_continuation_head("11.6.2", "或11.6.3得出的值大。", [])

    def test_dot_leading_rest(self):
        # 旧深度截断形态：'8.3.1.2.3.1 概述' 被截后 rest = '.1 概述'
        assert _is_continuation_head("8.3.1.2.3", ".1 概述", [])

    def test_real_head_not_flagged(self):
        assert not _is_continuation_head("4.1", "基本要求", [])
        assert not _is_continuation_head("5.1", "整机可靠性", [])


class TestContinuationOrder:
    """② 序性判据：号 ≤ 最近已产出号。"""

    def test_duplicate_number_rejected(self):
        # GB/T 1094.6 实测：'4.1.4 规定的变压器绕组在短路条件下的值。'
        assert _is_continuation_head("4.1.4", "规定的变压器绕组在短路条件下的值。",
                                     [_Fake("4.1.3"), _Fake("4.1.4")])

    def test_lower_number_rejected(self):
        assert _is_continuation_head("5.1.10", "所述的方法进行试验。",
                                     [_Fake("5.1.19")])

    def test_increasing_accepted(self):
        assert not _is_continuation_head("5.2", "要求", [_Fake("5.1")])
        assert not _is_continuation_head("5.1.1", "概述", [_Fake("5.1")])

    def test_parent_then_child_accepted(self):
        assert not _is_continuation_head("8.3.1.2.3.1", "概述", [_Fake("8.3.1.2.3")])

    def test_appendix_duplicate_rejected(self):
        # GB/T 1094.6 实测：'C.7)。总的磁通变化…' / 'E.1所示等效电路…'
        assert _is_continuation_head("C.7", ")。总的磁通变化是积分值", [_Fake("C.7")])
        assert _is_continuation_head("E.1", "所示等效电路，可以推导出以下结果。",
                                     [_Fake("E.1")])

    def test_appendix_progression_accepted(self):
        assert not _is_continuation_head("C.8", "试验方法", [_Fake("C.7")])

    def test_prefix_ignored(self):
        # 前置说明不参与序性比较（R65）
        assert not _is_continuation_head("1", "范围", [_Fake("前置1")])


class TestDepthCap:
    def test_deep_number_full_capture(self):
        # 修复前 {1,4} → 只捕 '8.3.1.2.3'，rest 剩 '.1 概述'
        m = _CLAUSE_GB.match("8.3.1.2.3.1 概述")
        assert m is not None
        assert m.group(1) == "8.3.1.2.3.1"
        assert m.group(2).strip() == "概述"


def _mk(items_text: list[str], tmp_path):
    mj = {"pdf_info": [{"page_idx": 0, "page_size": [595.0, 841.0], "para_blocks": [
        {"type": "text", "bbox": [60, 700, 530, 740],
         "lines": [{"bbox": [60, 700, 530, 720], "spans": [{"type": "text", "content": t}]}]}
        for t in items_text
    ]}]}
    p = tmp_path / "gates_middle.json"
    p.write_text(json.dumps(mj, ensure_ascii=False), encoding="utf-8")
    return p


class TestIntegration:
    def test_continuation_does_not_duplicate(self, tmp_path):
        # 真条款 3.18 后跟续行 '3.18)，…' → 不得产生第二条 3.18
        p = _mk(["3.18 滑轨", "用于使推拉构件灵活运动的部件。",
                 "3.18)，在距离全开位置10mm以内处关闭推拉构件。"], tmp_path)
        items, _ = load_middle_items(p)
        nums = [c.number for c in split_items_into_clauses(items)]
        assert nums.count("3.18") == 1, f"重复条款号残留: {nums}"

    def test_deep_number_kept_distinct(self, tmp_path):
        # 8.3.1.2.3 与 8.3.1.2.3.1 是两个不同条款（修复前都落 8.3.1.2.3）
        p = _mk(["8.3.1.2.3 停机时间的修正", "8.3.1.2.3.1 概述",
                 "用直接测量电阻的方法来测量。"], tmp_path)
        items, _ = load_middle_items(p)
        nums = [c.number for c in split_items_into_clauses(items)]
        assert "8.3.1.2.3.1" in nums, f"深层号未完整捕获: {nums}"

    def test_normal_progression_unaffected(self, tmp_path):
        p = _mk(["5.1 试验样机", "试验样机应符合要求。", "5.2 试验仪器",
                 "试验仪器应经检定。"], tmp_path)
        items, _ = load_middle_items(p)
        nums = [c.number for c in split_items_into_clauses(items)]
        assert nums == ["5.1", "5.2"], nums
