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
    MidItem, _INDEX_HEAD, _TOC_ENTRY, _is_toc_entry, split_items_into_clauses,
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


# ---------------------------------------------------------------------------
# 第二签名：无点线目录块（2026-09-15 批次2 · 500 部新语料）
# ---------------------------------------------------------------------------
# **缺陷证据**（GB/T 29798-2013 实测）：目录被压成单行时**点线会被吞掉**，只余
# "条款号 + 页码"：
#     '10.2.3 重连接 80\n10.2.4 订阅响应 SubscribeResponse 80\n10.2.5 心跳 81\n…'
# 该块 `_is_toc_entry` 判 False → 目录态当行退出 → **其后的点线目录块**
# （'14.5 出错信息的扩展性 …… 108' 起 10 行）也一并倒进正文，产出号序断裂：
#     ['前置1','10.2.3','14.5','1','2','3',…]
# ——'14.5' 抢占正文 14.5 的座位（该条款内容实为目录尾部，正文缺此条）。
# **修法**：`_RE_TOC_CL_NO_DOTS` 认「≥2 行 条款号 + 标题 + 页码尾」为目录条目。
_TOC_NO_DOTS = ("10.2.3 重连接 80\n10.2.4 订阅响应 SubscribeResponse 80\n"
                "10.2.5 心跳 81\n10.2.6 书签 82")


def test_toc_no_dots_block_is_toc_entry():
    """无点线目录块命中第二签名（实测原文）。"""
    assert _is_toc_entry(_TOC_NO_DOTS)


def test_toc_no_dots_reverse_controls():
    """**反向对照**：正文多行块不得被第二签名吃掉。

    分水岭是**行尾裸页码**——正文块行尾不会带页码；且要求 ≥2 行，
    防正文里单行"见 4.2 条 5"这类误判。
    """
    for keep in ["3.1 原则\n3.2 方法",
                 "3.1 原则\n3.2 方法\n3.3 要求",           # 多行正文，行尾无数字
                 "4.2 应符合表 5 的规定。",                  # 单行
                 "5.1 试验方法\n见 4.2 条 5",                 # 单行带数字尾
                 "本标准规定了恒温槽的要求。\n温度范围 5 ℃ 至 40 ℃"]:
        assert not _is_toc_entry(keep), keep


def test_toc_no_dots_then_dots_block_not_ingested():
    """**缺陷现场重放**：无点线目录块 + 其后的点线目录块都不得成为条款。"""
    items = ([_t("目 次"), _t(_TOC_NO_DOTS)]
             + [_t("14.5 出错信息的扩展性 …… 108"),
                _t("14.6 主要出错消息 …… 109"),
                _t("附录 A（规范性附录） 标记约定 …… 128")]
             + [_t("前言"), _t("本标准按照 GB/T 1.1—2009 给出的规则起草。"),
                _t("1 范围", 2), _t("本标准规定了资源管理的要求。", 2)])
    clauses = split_items_into_clauses(items)
    numbers = [str(c.number or "") for c in clauses]
    texts = "\n".join(" ".join(c.texts) for c in clauses)
    for bad in ("10.2.3", "14.5", "14.6"):
        assert bad not in numbers, f"目录条目被摄入成条款：{bad} → {numbers}"
    assert "……" not in texts, f"目录尾部仍被摄入：{texts[:160]}"
    # 正文必须照常保留
    assert "1" in numbers, f"正文被误吃：{numbers}"
    assert "本标准规定了资源管理的要求。" in texts


# ---------------------------------------------------------------------------
# 文末「索引」小节（2026-09-15 批次3 · 55 部全新语料实测 1 部）
# ---------------------------------------------------------------------------
# **缺陷证据**（GB/T 5845.2-2008 城市公共交通标志 第2部分）：
# 中文索引写成 `中文名称 …… 序号\nIC 卡充值站 …… 27\n…`——**点线 + 序号列**，
# 页码位置被序号冒充，故 `_is_toc_entry` 认它（带点线页码尾），但此时**不在目录态**
# （`in_toc` 只在文首「目次」置位），于是索引两页全被**并进前一条款**：
# 正文 5.5 本只有一行，却吃下 126 行。
# **修法**：`_INDEX_HEAD` 认"整块恰为「索引」"为索引起始，其后所有块都不入条款。
_INDEX_ROWS = ("中文名称 …… 序号\nIC 卡充值站 …… 27\n保管好自己物品 …… 28\n"
               "病残专座 …… 16\n出口 …… 03")


def test_index_head_predicate():
    """只有"整块恰为索引"才算索引起始（含空格变体）。"""
    for yes in ("索引", "索 引", "索  引", "\n索引\n"):
        assert _INDEX_HEAD.match(yes), yes
    # **反向对照**：正文里含"索引"的句子不得被当索引起始
    # （否则会把该块及其后全部内容误判掉，比原缺陷更严重）
    for no in ("5.6 索引号的编制应符合规定。",
               "见索引。",
               "本部分索引如下：",
               "索引号 3.2.1",
               "附录 A（资料性附录） 索引编制规则"):
        assert not _INDEX_HEAD.match(no), no


def test_index_section_not_absorbed_into_clause():
    """**缺陷现场重放**：索引小节不得并入前一条款，正文必须保留。"""
    items = [
        _t("5.5 本部分表示方向的图形符号，可根据实际需要转换成镜像图形符号使用。"),
        _t("索引"),
        _t(_INDEX_ROWS, 19),
        _t("请勿开窗 …… 40\n请勿吸烟 …… 33", 20),
    ]
    clauses = split_items_into_clauses(items)
    numbers = [str(c.number or "") for c in clauses]
    texts = "\n".join("\n".join(c.texts or []) for c in clauses)
    # 正文 5.5 必须保留，且**只含它自己那一行**
    assert "5.5" in numbers, f"正文 5.5 被误吃：{numbers}"
    c55 = next(c for c in clauses if str(c.number) == "5.5")
    assert len(c55.rows) == 1, f"5.5 仍吃下了索引行（rows={len(c55.rows)}）"
    assert "图形符号使用" in texts
    # 索引内容不得出现在任何条款里
    for bad in ("IC 卡充值站", "病残专座", "请勿吸烟"):
        assert bad not in texts, f"索引条目被摄入条款：{bad}"
    # 索引标题本身也不得成为条款
    assert "索引" not in numbers, f"索引标题成了条款：{numbers}"


def test_index_section_does_not_eat_preceding_clauses():
    """反向对照：索引**之前**的条款必须完好（索引态不得提前置位）。"""
    items = [
        _t("1 范围"),
        _t("本部分规定了城市公共交通标志的图形符号。"),
        _t("2 规范性引用文件"),
        _t("下列文件中的内容通过文中的规范性引用而构成本部分必不可少的条款。"),
        _t("索引"),                     # 索引起点
        _t(_INDEX_ROWS, 19),
    ]
    clauses = split_items_into_clauses(items)
    numbers = [str(c.number or "") for c in clauses]
    texts = "\n".join("\n".join(c.texts or []) for c in clauses)
    assert "1" in numbers and "2" in numbers, f"索引前的条款被误吃：{numbers}"
    assert "本部分规定了城市公共交通标志的图形符号。" in texts
    assert "下列文件中的内容通过文中的规范性引用" in texts
    assert "IC 卡充值站" not in texts
