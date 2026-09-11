# -*- coding: utf-8 -*-
"""E5 表格绑定「物理就近优先」规则测试（2026-09-02，契约更新）。

现行规则（pipeline.py 410-414 注释，2026-09-02 定案）：表x 的归属绑定顺序为
  物理就近(current) → 引用（仅当物理无且非续表）→ 续表。
即：表格物理上紧跟哪个条款就归哪个条款（"表物理在哪页就归哪个条款"）。

历史：引用优先规则（"表x 的母条款 = 最近一个文内引用表x 的条款"，"应符合表x
的规定"为国标通行句式）曾在 2026-08-29 因"表1/表2/表3 题注号撞上新章节点
1/2/3"而引入；但 2026-09-02 实测（24276）发现引用优先把物理位于 6 章的表 1
误绑到引用它的 5.2.4 → 表显示在 5.2.4 而非物理 6 章 = 表位置错，故改为物理
就近优先。E5 回归价值（25596 人工测试）仍保留：章级条款修复后，表题注号
不得撞号挂到章级条款 1/2/3。
"""
from __future__ import annotations

from src.core.ingestion.pipeline import MidItem, split_items_into_clauses


def _t(text, caption=None, html=None, page=0):
    return MidItem(kind="table", text=caption or text or "", caption=caption,
                   html=html or f"<table>{caption or text}</table>", page_idx=page)


def _cl(clauses, no):
    return next(c for c in clauses if c.number == no)


def test_caption_number_must_not_steal_chapter_clauses():
    """回归核心（物理就近语义）：题注"表1/表2"不得撞号挂到章级条款 1/2；
    表1/表2 物理紧跟 3.4.2 条款之后 → 一律归 3.4.2，引用者 3.4.1 不收表。"""
    items = [
        MidItem(kind="text", text="1范围"),
        MidItem(kind="text", text="本标准适用于0~12月龄婴儿食用的特殊医学用途婴儿配方食品。"),
        MidItem(kind="text", text="2术语和定义"),
        MidItem(kind="text", text="2.1特殊医学用途婴儿配方食品"),
        MidItem(kind="text", text="3.4.1常见特殊医学用途婴儿配方食品应符合表1的规定。"),
        MidItem(kind="text", text="3.4.2维生素指标应符合表2的规定。"),
        _t("表1", "表1 能量和蛋白质指标", "<table>T1</table>", page=4),
        _t("表2", "表2 维生素指标", "<table>T2</table>", page=5),
    ]
    clauses = split_items_into_clauses(items)
    assert _cl(clauses, "1").table_html is None      # 章"1 范围"不得收表（题注号撞号回归）
    assert _cl(clauses, "2").table_html is None      # 章"2 术语和定义"不得收表（题注号撞号回归）
    # 物理就近：表1/表2 紧跟 3.4.2 条款之后，归属 3.4.2（与题注号/引用者无关）
    assert "T1" in _cl(clauses, "3.4.2").table_html
    assert "T2" in _cl(clauses, "3.4.2").table_html
    assert _cl(clauses, "3.4.1").table_html is None  # 引用者（"应符合表1的规定"）不收表


def test_table_follows_physical_position_over_reference():
    """物理就近优先于引用（新语义）：表5 物理落在章"4"之后（4其他 独立成章、
    无子条款）→ 归属"4"；虽 3.6 文内引用"表5"，但引用条款不因文内引用收表。"""
    items = [
        MidItem(kind="text", text="1范围"),
        MidItem(kind="text", text="本标准适用于婴儿配方食品。"),
        MidItem(kind="text", text="3.6其他指标应符合表5的规定。"),
        MidItem(kind="text", text="4其他"),
        _t("表5", "表5 其他指标", "<table>T5</table>", page=6),
    ]
    clauses = split_items_into_clauses(items)
    assert "T5" in _cl(clauses, "4").table_html
    assert _cl(clauses, "3.6").table_html is None


def test_appendix_table_binds_appendix_clause():
    """附录表（表A.1）挂附录条款；正文条款不受牵连。"""
    items = [
        MidItem(kind="text", text="1范围"),
        MidItem(kind="text", text="本标准适用于婴儿配方食品。"),
        MidItem(kind="text", text="附 录 A"),
        MidItem(kind="text", text="常见特殊医学用途婴儿配方食品见表A.1的规定。"),
        _t("表A.1", "表A.1 产品类别及技术指标", "<table>TA1</table>", page=9),
    ]
    clauses = split_items_into_clauses(items)
    assert "TA1" in _cl(clauses, "附录A").table_html
    assert _cl(clauses, "1").table_html is None


def test_word_boundary_no_false_reference():
    """引用判定词边界："表1.1"不算引用"表1"；表1 物理紧跟 1.2 条款 → 归 1.2
    （物理就近优先；词边界仅防引用误配的兜底）。"""
    items = [
        MidItem(kind="text", text="1.1样品分组"),
        MidItem(kind="text", text="样品分组应符合表1.1的规定。"),
        MidItem(kind="text", text="1.2试剂"),
        _t("表1", "表1 一般要求", "<table>T1x</table>", page=1),
    ]
    clauses = split_items_into_clauses(items)
    assert _cl(clauses, "1.1").table_html is None
    assert "T1x" in _cl(clauses, "1.2").table_html


def test_multi_table_same_clause_append():
    """同一条款多张表（正表+续表）保持追加语义，不覆盖。"""
    items = [
        MidItem(kind="text", text="1范围"),
        MidItem(kind="text", text="本标准适用于婴儿配方食品。"),
        MidItem(kind="text", text="2.1基本要求应符合表1的规定。"),
        _t("表1", "表1 基本要求", "<table>T1a</table>", page=3),
        _t("表1续", "表1 基本要求(续)", "<table>T1b</table>", page=4),
    ]
    clauses = split_items_into_clauses(items)
    html = _cl(clauses, "2.1").table_html
    assert "T1a" in html and "T1b" in html
