"""目录页摄入修复（2026-09-15）：`toc-ingested-as-clauses` 头部类根因回归。

**缺陷证据**（全新语料 231 部实测，8 部命中，占该轮命中 80%）：
目录页正文被判成条款摄入，并**打乱号序**：

    GB/T 17889.5-2025  号序 ['前置1','7.1','1','2',…]（'7.1' 那条含 40 行目录）
    GB/T 24842-2018    号序 ['前置1','10.5','1',…]（25 行）
    GB/T 25483-2010    号序 ['前置1','5.3.2','1',…]（73 行）
    GB/T 28853-2012    更碎：'9.1 包装……13'/'9.2 运输……14' 被切成 5 个独立条款

**根因**：`split_items_into_clauses` 的 `in_toc` 退出判据写的是"出现第一个章/
条款头即退出"，而**目录条目本身长得就像条款头**——'7.1 一般要求 …… 16' 匹配
`_CLAUSE_GB`，于是进入目录态后**第一行就退出**，其后 39 行目录全被当正文摄入。

**修法**：目录条目的确定签名 = **点线引导 + 页码尾**（'……16'）。目录态内只要
该块是目录条目就继续吃；遇到不带页码尾的块才退出。
判据 `_is_toc_entry` 与 `audit_text.dot-leader` 同源口径（`…{2,}` = '……'）。

**反向对照**（必须存活）：正常条款'3.1 驾驶自动化分级原则'、章头'1 范围'、
带数字尾的正文行都**不带点线**，不得被判为目录条目——否则会吃掉正文。
"""
from src.core.ingestion.pipeline import (
    MidItem, _TOC_ENTRY, _is_toc_entry, split_items_into_clauses,
)


def _t(text: str, page: int = 0) -> MidItem:
    return MidItem(kind="text", text=text, page_idx=page)


# ---------------------------------------------------------------------------
# 判据直测
# ---------------------------------------------------------------------------
def test_toc_entry_predicate_positives():
    """目录条目四种实测形态全命中（含并块）。"""
    assert _is_toc_entry("7.1 一般要求 …… 16")
    assert _is_toc_entry("9.1 包装……13")
    assert _is_toc_entry("6.10 轴承温度的测定……………………………3")
    # 并块：MinerU 常把多条目录并进一个块（实测 GB/T 41780.2-2024）
    assert _is_toc_entry("国家标准化管理委员会\n11 数据共享要求……7\n12 数据删除要求……8")


def test_toc_entry_predicate_reverse_controls():
    """**反向对照**：不带点线页码尾的正文/章头/表格数值行一律不认。

    这是关键护栏——判据放宽会把正文吃掉。原判据的第二个分支
    `^\\S+\\s+\\S{2,}\\s*\\d$` 就因为不要求点线而把
    '3.1 驾驶自动化分级原则\\n3' 这类正常条款报成目录（20/23 条误报）。
    """
    for keep in ["3.1 驾驶自动化分级原则",
                 "3.1 驾驶自动化分级原则\n3",
                 "1 范围",
                 "4.1 结构型式应符合图1的规定。",
                 "2013-02-15 实施",
                 "1.05 MPa FRPT10-35-2.5-PE GB"]:
        assert not _is_toc_entry(keep), keep


def test_toc_entry_regex_requires_page_tail():
    assert _TOC_ENTRY.search("条目 …… 16")
    assert not _TOC_ENTRY.search("条目 …… ")
    assert not _TOC_ENTRY.search("正文以数字结尾 16")


# ---------------------------------------------------------------------------
# 切分行为回归（缺陷现场重放）
# ---------------------------------------------------------------------------
TOC_PAGE = [
    "目 次",
    "前言 ……………………………………………………… Ⅲ",
    "1 范围 ……………………………………………………… 1",
    "7.1 一般要求 …… 16",
    "7.2 特殊要求 …… 17",
    "8 检验规则 …… 20",
    "9 包装、运输、贮存 …… 13",
]


def test_toc_page_not_ingested_as_clauses():
    """**缺陷现场重放**：目录页整页不得产出任何条款。

    旧行为：'7.1 一般要求 …… 16' 触发退出目录态 → 其后目录行被摄入成
    条款（实测号序 ['前置1','7.1','1','2',…]）。
    """
    items = [_t(t) for t in TOC_PAGE] + [
        _t("1 范围", 2),
        _t("本标准规定了恒温槽的要求。", 2),
    ]
    clauses = split_items_into_clauses(items)
    texts = "\n".join(" ".join(c.texts) for c in clauses)
    assert "……" not in texts, f"目录条目仍被摄入：{texts[:160]}"
    for ln in ("7.1 一般要求", "7.2 特殊要求", "8 检验规则", "9 包装"):
        assert ln not in texts, f"目录行被当条款摄入：{ln}"
    # 正文必须照常保留（number 只存编号，标题在 texts 里）
    numbers = [str(c.number or "") for c in clauses]
    assert "1" in numbers, f"正文第一章被误吃：{numbers}"
    assert "本标准规定了恒温槽的要求。" in texts


def test_toc_single_entry_blocks_not_ingested():
    """逐行成块的目录条目（GB/T 28853-2012 形态）不得成为条款。"""
    items = [_t("目 次")] + [
        _t("9.1 包装……13"),
        _t("9.2 运输……14"),
        _t("9.3 贮存……14"),
        _t("10.1 技术文件……14"),
    ] + [_t("1 范围", 3), _t("本标准适用于高温恒温循环装置。", 3)]
    clauses = split_items_into_clauses(items)
    numbers = [str(c.number or "") for c in clauses]
    texts = "\n".join(" ".join(c.texts) for c in clauses)
    assert "9.1" not in numbers, f"目录条目被切成条款：{numbers}"
    assert "10.1" not in numbers
    assert "1" in numbers, f"正文被误吃：{numbers}"
    assert "本标准适用于高温恒温循环装置。" in texts
