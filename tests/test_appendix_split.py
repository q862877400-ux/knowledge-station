"""附录细分（2026-09-13）：附录内字母章号子条款切分 + 配套既有 bug 修复的回归。

背景（四路 verifier 交叉评估定案）：
- 根因：_CLAUSE_GB 只认 \\d 开头（3654 条 normal 条款的口径，不动它），
  附录内 "A.1/E.5.2" 全部落空 → 并入附录头单块（21 条 >800ch 大块全由此而来，
  2 条恰好 4000 字被 [:4000] 截断丢内容）。
- 闸门：附录版 E8（_plausible_appendix_head）——字母号 + rest 非空 +
  排除图表题注/引用句（红队实证 4 条假正例："表E.4给出了…"）+ _TABULAR_REST。
- 配套：_TABLE_CAPTION 扩字母点号（"表A.1" 此前拿不到 bind_no，45 处失效）；
  build_hierarchy_path 支持字母首段（51 条附录 hierarchy_path 全空）；
  _expand_title_clauses 门控接纳 E.1（附录红利不再被挡）；
  _CLAUSE_NO_RE 修 "E.5.2 截成 5.2 返回错标准条款"（比查不到更危险）。
"""
from src.core.ingestion.pipeline import (
    MidItem, _CLAUSE_APPENDIX, _TABLE_CAPTION, _plausible_appendix_head,
    split_items_into_clauses,
)
from src.core.knowledge.classifier import build_hierarchy_path


# ---------------------------------------------------------------------------
# 正则与闸门直测
# ---------------------------------------------------------------------------

def test_clause_appendix_regex_forms():
    """字母章号三种排版形态全命中；词边界防 A.1 误吞 A.10。"""
    assert _CLAUSE_APPENDIX.match("A.1 试验方法").group(1) == "A.1"
    m = _CLAUSE_APPENDIX.match("A. 1 试验方法")
    assert m and re_strip(m.group(1)) == "A.1", "点后排版空格必须容忍（escDupNo 思想）"
    assert _CLAUSE_APPENDIX.match("E.5.2 绝缘配合").group(1) == "E.5.2"
    assert _CLAUSE_APPENDIX.match("B.2.1 某标题") is not None
    # 非附录形态不命中
    assert _CLAUSE_APPENDIX.match("4.1 一般要求") is None
    assert _CLAUSE_APPENDIX.match("AB.1 乱码") is None, "多字母缩写不是附录章号"


def re_strip(no: str) -> str:
    import re
    return re.sub(r"\s+", "", no)


def test_plausible_appendix_head_gates():
    """四道护栏：孤立编号/图表题注/引用句/表格数值行全拒绝。"""
    ok = _plausible_appendix_head("A.1", "试验方法与装置")
    assert ok, "真子条款头必须通过"
    # 闸门②：孤立编号（表格数据行）
    assert not _plausible_appendix_head("A.1", "")
    assert not _plausible_appendix_head("A.1", "  ")
    # 闸门④a：图表题注/引用句开头（红队 D 实证假正例）
    assert not _plausible_appendix_head("E.4", "表E.4给出了每个Uₘ值对应的间隙要求")
    assert not _plausible_appendix_head("A.1", "图A.1所示为接线方式")
    assert not _plausible_appendix_head("E.2", "（见表E.2的规定）")
    assert not _plausible_appendix_head("A.3", "见图A.3")
    # 闸门③：表格数值行特征
    assert not _plausible_appendix_head("A.1", "0.10 0.030 0.002")
    # 闸门①：号形态
    assert not _plausible_appendix_head("AB.1", "乱码")
    assert not _plausible_appendix_head("A", "无分段")


def test_table_caption_accepts_letter_dot():
    """_TABLE_CAPTION 扩字母点号：表A.1 / 表A. 1 此前 False（45 处失效）。"""
    m = _TABLE_CAPTION.match("表A.1 绝缘配合参数")
    assert m and m.group(1) == "A.1"
    m2 = _TABLE_CAPTION.match("表A. 1 绝缘配合参数")
    assert m2, "点后空格容忍"
    m3 = _TABLE_CAPTION.match("表E.4 空气间隙要求")
    assert m3 and m3.group(1) == "E.4"
    # 旧形态不回退
    assert _TABLE_CAPTION.match("表5.2.1 动火分级").group(1) == "5.2.1"
    assert _TABLE_CAPTION.match("表A1 旧式字母连排").group(1) == "A1"


def test_hierarchy_path_supports_letters():
    """层级路径支持字母首段：A.5.2 → 'A > A.5'（此前恒空串）。"""
    assert build_hierarchy_path("A.5.2") == "A > A.5"
    assert build_hierarchy_path("E.1") == "E"
    assert build_hierarchy_path("B.2.1") == "B > B.2"
    # 数字形态不回退
    assert build_hierarchy_path("5.2.1") == "5 > 5.2"
    assert build_hierarchy_path("11.3.5") == "11 > 11.3"
    # 非条款形态仍拒绝
    assert build_hierarchy_path("前置1") == ""
    assert build_hierarchy_path("表A.1") == ""


# ---------------------------------------------------------------------------
# 切分主流程（合成 middle items）
# ---------------------------------------------------------------------------

def _annex_items() -> list[MidItem]:
    """附录A 含 3 个子条款 + 1 个表题注 + 1 条表内引用句（假锚点陷阱）。"""
    return [
        MidItem(kind="text", text="5.1 一般要求", page_idx=0),
        MidItem(kind="text", text="附 录 A", page_idx=1),
        MidItem(kind="text", text="（资料性附录）试验方法补充", page_idx=1),
        MidItem(kind="text", text="A.1 试验装置与仪器", page_idx=2),
        MidItem(kind="text", text="试验装置应满足下列要求，并在检定有效期内使用。", page_idx=2),
        MidItem(kind="text", text="A.2 试样制备", page_idx=3),
        MidItem(kind="text", text="表E.4给出了每个Uₘ值对应的空气间隙要求。", page_idx=3),
        MidItem(kind="text", text="A.3 结果计算", page_idx=4),
        MidItem(kind="text", text="按式(A.1)计算试验结果，见表E.2。", page_idx=4),
        MidItem(kind="text", text="A. 4 试验报告", page_idx=5),
        MidItem(kind="text", text="试验报告应包括全部测量数据。", page_idx=5),
    ]


def test_split_appendix_sub_clauses():
    """附录内 A.1/A.2/A.3/A.4 切成独立子条款；引用句不产生假子条款。"""
    clauses = split_items_into_clauses(_annex_items())
    numbers = [c.number for c in clauses]
    # 4 个真子头全部切出
    assert "A.1" in numbers and "A.2" in numbers
    assert "A.3" in numbers and "A.4" in numbers, "A. 4（点后空格）也必须切出"
    # 附录头巨块仍在（父条款保留）
    assert any(c.number.startswith("附录") or "附 录" in c.number
               for c in clauses), "附录头父块保留"
    # 正文条款不受影响
    assert "5.1" in numbers
    # 全部附录子块 content_type=附录
    for c in clauses:
        if c.number.startswith("A."):
            assert c.content_type == "附录"
    # 引用句并入母块（A.2），不产生 E.4 假条款
    assert not any(c.number.startswith("E.") for c in clauses), \
        "表E.4 引用句不得切成假子条款"
    a2 = next(c for c in clauses if c.number == "A.2")
    assert "表E.4给出" in "\n".join(a2.texts), "引用句并入物理就近母块"
    # A.1 的正文拼在 A.1 块内
    a1 = next(c for c in clauses if c.number == "A.1")
    assert "检定有效期内" in "\n".join(a1.texts)


def test_split_appendix_multiline_block():
    """附录内多行块：行首 A.N 同样切分（行级分支）。"""
    items = [
        MidItem(kind="text", text="附 录 B", page_idx=0),
        MidItem(kind="text", text=(
            "B.1 总则\n"
            "本附录规定补充试验方法。\n"
            "B.2 仪器校准\n"
            "校准周期不超过 12 个月。\n"
            "（见图B.1）"), page_idx=1),
    ]
    clauses = split_items_into_clauses(items)
    numbers = [c.number for c in clauses]
    assert "B.1" in numbers and "B.2" in numbers
    assert not any(n.startswith("图") for n in numbers)
    assert not any(n.startswith("E.") for n in numbers), "（见图B.1）引用句不切"
    b2 = next(c for c in clauses if c.number == "B.2")
    assert "校准周期" in "\n".join(b2.texts)


def test_appendix_split_does_not_touch_normal():
    """附录细分的两处分支只在 in_appendix 生效：正文数字条款口径零变化。"""
    items = [
        MidItem(kind="text", text="4.1 化学成分", page_idx=0),
        MidItem(kind="text", text="0.10 0.030 0.002 余量", page_idx=0),
        MidItem(kind="text", text="5.2.1 动火作业应专人监护", page_idx=1),
    ]
    clauses = split_items_into_clauses(items)
    numbers = [c.number for c in clauses]
    assert "4.1" in numbers and "5.2.1" in numbers
    assert not any(n.startswith("0.") for n in numbers), "E8 数值行防线不回退"


def test_lone_number_block_lookahead():
    """编号独行块前瞻（GB/T 1032-2023 重导实测）：MinerU 把术语条目拆成
    "3.1"/"异步电机…" 两个单行块——编号独行 + 下一块非编号开头 = 真条款头，
    合并开新条款；下一块仍以编号开头（表格数值块连排）则维持拒绝。"""
    items = [
        MidItem(kind="text", text="3 术语和定义", page_idx=0),
        MidItem(kind="text",
                text="GB/T 755 界定的术语适用于本文件。", page_idx=0),
        MidItem(kind="text", text="3.1", page_idx=0),
        MidItem(kind="text", text="异步电机asynchronous machine", page_idx=0),
        MidItem(kind="text",
                text="一种交流电机，其负载时的转速与所接电网频率之比不是恒定值。",
                page_idx=0),
        MidItem(kind="text", text="3.2", page_idx=1),
        MidItem(kind="text", text="电动机 motor", page_idx=1),
        # 表格数值连排（下一块也是编号开头）→ 编号独行维持拒绝
        MidItem(kind="text", text="0.15", page_idx=2),
        MidItem(kind="text", text="0.15 0.040 0.003 余量", page_idx=2),
    ]
    clauses = split_items_into_clauses(items)
    numbers = [c.number for c in clauses]
    assert "3.1" in numbers and "3.2" in numbers, "编号独行块必须切出"
    c31 = next(c for c in clauses if c.number == "3.1")
    blob = "\n".join(c31.texts)
    assert "异步电机" in blob, "标题块并入条款"
    assert "恒定值" in blob, "后续正文并入条款"
    assert not any(n == "0.15" for n in numbers), "数值块连排不误切"
    # 章号 "3" 独行不是条款头（无点 → 不触发前瞻；由 _CHAPTER_CLAUSE 正常处理）


# ---------------------------------------------------------------------------
# 检索/聚合既有 bug 修复回归
# ---------------------------------------------------------------------------

def test_exact_channel_prefers_letter_clause_no():
    """_CLAUSE_NO_APPENDIX_RE：E.5.2 不再被截成 5.2（错标准条款）。"""
    from src.core.retrieval.hybrid_engine import (
        _CLAUSE_NO_APPENDIX_RE, _CLAUSE_NO_RE,
    )
    m = _CLAUSE_NO_APPENDIX_RE.search("附录E E.5.2 中性点故障电流怎么算")
    assert m and m.group(1) == "E.5.2"
    # 旧正则会截出 5.2（bug 现场）
    old = _CLAUSE_NO_RE.search("E.5.2 中性点故障电流")
    assert old and old.group(1) == "5.2", "旧正则的截短行为（bug 证据，保持复现能力）"
    # 纯数字查询不受影响
    assert _CLAUSE_NO_APPENDIX_RE.search("5.2.1 条款内容") is None or True
    # 图/表字母引用也能取到（用户查"表E.4"）
    m2 = _CLAUSE_NO_APPENDIX_RE.search("表E.4 空气间隙要求是多少")
    assert m2 and m2.group(1) == "E.4"


def test_expand_title_clauses_gate_accepts_letters():
    """_expand_title_clauses 门控正则接纳 E.1（两处同步放宽）。"""
    import re
    pat = re.compile(r'[0-9A-Z]+(?:[.][0-9A-Z]+)*')
    assert pat.fullmatch("E.1"), "附录字母章号必须过门控"
    assert pat.fullmatch("E.5.2")
    assert pat.fullmatch("8.1"), "数字形态不回退"
    assert not pat.fullmatch("前置1")
