"""索引页护栏契约测试（2026-09-15，GB/T 1008-2008 154 组重复号根因修复）。

背景：索引页（中文/英文索引）每行是「裸号 + 引点 + 词条」，引点被 OCR 成
000000000000000。'编号独行块前瞻' 分支（2026-09-13 为 GB/T 1032 术语条目而加）
把「裸号 + 引点块」当条款头 → 154 个索引号全部成伪条款（重复号 307 行）。
修复：该分支补两道拒——① 下一块是纯引点填充 ② 序性（索引号 ≤ 正文已产出号）。
护栏不能误伤原用例（1032 术语条目独行号递增）。
"""
import json

from src.core.ingestion.pipeline import (
    _is_continuation_head, _is_leader_run, load_middle_items_from_blocks,
    split_items_into_clauses,
)


class _Fake:
    def __init__(self, number):
        self.number = number


class TestLeaderRun:
    def test_zeros_run(self):
        assert _is_leader_run("000000000000000")

    def test_dots_run(self):
        assert _is_leader_run(".............")
        assert _is_leader_run(". . . . . . .")

    def test_short_not_leader(self):
        assert not _is_leader_run("00")
        assert not _is_leader_run("0.1")

    def test_number_with_other_digits_not_leader(self):
        # '10000000' 含非 0 数字 → 不是引点（防把大数值当引点）
        assert not _is_leader_run("10000000")

    def test_text_not_leader(self):
        assert not _is_leader_run("异步电机asynchronous machine")
        assert not _is_leader_run("")

    def test_stripped(self):
        assert _is_leader_run("   0000000000   ")


class TestOrderingOnBareNumber:
    """序性判据的**现**契约（2026-09-15 收敛循环首轮修正）。

    初版契约是「号 ≤ 最近已产出号即拒」，跨父也拒——但收敛循环首轮实测暴露它是
    **顺序依赖且不可恢复**：假头 40.5 一旦入史，其后所有真头（4.1/5.2/附录 A.1）
    全被判回退，GB/T 12706.4-2020 从 53 条塌成 3 条、正文 6489→4886 字。
    现契约收窄为两条**局部充分**判据：① 重复号；② 同父回退。
    索引行的护栏不在此处，而在前瞻分支的引点判据 —— 由
    `TestIntegration.test_index_rows_not_clauses` 端到端保证。
    """

    def test_same_parent_backward_rejected(self):
        # 同一父下回退 = 引用前面兄弟的续行（真条款号同父严格递增）
        assert _is_continuation_head("8.13", "", [_Fake("8.20")])
        assert _is_continuation_head("3.1", "", [_Fake("3.9")])

    def test_duplicate_rejected(self):
        assert _is_continuation_head("3.1", "", [_Fake("3.2"), _Fake("3.1")])

    def test_cross_parent_backward_accepted(self):
        # 跨父"回退"必须放行：那既可能是新章开始，也可能是假头之后的真头；
        # 拒它就是让一个假头毒死全文（不可恢复）。
        assert not _is_continuation_head("8.13", "", [_Fake("14.2")])
        assert not _is_continuation_head("4.1", "", [_Fake("40.5")])

    def test_body_progression_accepted(self):
        # 正文递增号（1032 术语条目形态）不受影响
        assert not _is_continuation_head("3.2", "", [_Fake("3.1")])
        assert not _is_continuation_head("10.1", "", [_Fake("9.9")])

    def test_no_history_accepted(self):
        assert not _is_continuation_head("3.1", "", [])


def _blocks(triples):
    """triples: [(页号, 文本)] → fitz 风格 blocks。"""
    out = []
    for pno, txt in triples:
        out.append({"page_number": pno, "text": txt,
                    "bbox": [60.0, 100.0, 530.0, 130.0], "source": "pymupdf"})
    return out


class TestIntegration:
    def test_index_rows_not_clauses(self):
        # 索引页形态：裸号 + 引点 + 词条（重复三次），前置一个正文条款确立序性
        rows = [(1, "14.2 夹具\n夹具应符合本文件要求。")]
        for num, term in (("8.13", "百分表"), ("9.10", "扳手"), ("8.11", "搬运机器人")):
            rows += [(17, num), (17, "000000000000000"), (17, term)]
        items, _ = load_middle_items_from_blocks(_blocks(rows))
        clauses = split_items_into_clauses(items)
        nums = [c.number for c in clauses]
        assert nums.count("8.13") == 0, f"索引号成了条款: {nums}"
        assert nums.count("9.10") == 0
        assert "14.2" in nums

    def test_bare_number_with_title_still_clause(self):
        # 前瞻分支原用例：独行号 + 纯标题 → 仍须成条款（递增号）
        rows = [(1, "3.1"), (1, "异步电机asynchronous machine"),
                (1, "一种交流电机。"), (2, "3.2"), (2, "电动机 motor"),
                (2, "将电能转化为机械能的电机。")]
        items, _ = load_middle_items_from_blocks(_blocks(rows))
        clauses = split_items_into_clauses(items)
        nums = [c.number for c in clauses]
        assert "3.1" in nums and "3.2" in nums, nums

    def test_leader_content_not_lost(self):
        # 引点块本身是噪声可丢，但词条文本不得消失（保守：并入当前条款）
        rows = [(1, "14.2 夹具\n夹具应符合本文件要求。"),
                (17, "8.13"), (17, "000000000000000"), (17, "百分表")]
        items, _ = load_middle_items_from_blocks(_blocks(rows))
        clauses = split_items_into_clauses(items)
        body = "\n".join(t for c in clauses for t in c.texts)
        assert "百分表" in body, "索引词条文本不应凭空消失"
