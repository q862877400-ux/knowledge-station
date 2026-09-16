"""水印剥离的**上下文消歧**回归（2026-09-17 修，原为 strict xfail 缺口）。

背景：`strip_watermark_lines` 的 step ② 用一条只锚行尾的判据收口"被
`pypdf_backfill` 的 `" ".join(buf)` 拍进行尾的页眉"（形如 `'…执行。 5 GB/T 10029—2010'`），
判别特征只有"前导页码"。**而表格末格恰好也是 `<裸数字> <标准号>`**：
`20 GB/T699—2015`、`10 GB/T917—2009`、`1 JT/T132—2003`，于是被误删。

实测口径（清洗前快照，19,981 条 content_text 补丁）：该判据命中的 `页码+标准号` 尾
共 **2,910** 处，其中 **2,904** 处是**该文档自己的**标准号（确是逐页页眉，删得对），
**6** 处引用**别的**标准（疑似真表格内容，涉 3 个条款）。生产库当时**未受损**
（4 条候选都还在），但再跑一次 `--apply` 就会删掉。

修法：**喂上下文**。`strip_watermark_lines(text, *, own_standard_no=None)` ——
传了自家标准号后，"页码 + 标准号"这一族只吃**标准号相符**的页眉；
`pipeline.build_clause_models` 与 `repair_patch_watermarks.py` 都已传。
不传时保持历史行为（本文件最后一条用例钉住这一点，防止悄悄改变既有调用方输出）。
"""
import pytest

from src.core.text_utils import canon_standard_no, strip_watermark_lines

OWN = "GB/T 28788-2012"          # 下面 4 段文本所属文档**自己的**标准号

# 4 条实测输入（取自生产库；`needle` 只出现在**行尾那一格**）
CASES = [
    (
        "锅炉材料表末格",
        "5.2 材料 锅炉主要受压元件材料按表2规定执行。 表 2 锅炉主要受压元件材料 "
        "零件名称 推荐材料名称 推荐材料牌号 标准编号 筒体、管板(封头)、炉胆 承压设备用钢板 "
        "Q245R、Q345R GB/T713.2—2023 烟管、水管、牵条管 无缝钢管 20 钢级410 GB/T3087—2022 "
        "GB/T5312—2009 牵条 优质碳素结构钢 20 GB/T699—2015",
        "GB/T699—2015",
    ),
    (
        "村镇属性表末格",
        "8.14 公路沿线村镇 公路沿线村镇属性结构见表24。 表 24 字段名 类型 宽度 (单位:字节) "
        "值域或说明 村镇代码 字符型 6 GB/T10114 村镇名称 字符型 20 中文名称 路线代码 字符型 "
        "10 GB/T917—2009",
        "GB/T917—2009",
    ),
    (
        "交通标志属性表末格",
        "8.9.1 交通标志属性结构见表9。 表 9 字段名 类型 宽度 (单位:字节) 值域或说明 "
        "交通标志代码 字符型 6 JT/T132—2003 交通标志名称 字符型 20 中文名称 路线代码 "
        "字符型 10 GB/T917—2009 桩号 数值型(小数点后三位) 8 交通标志构造 字符型 1 "
        "JT/T132—2003 标志支持方式 字符型 1 JT/T132—2003",
        "JT/T132—2003",
    ),
    (
        "环境条件表末格",
        "6.1 产品应用环境条件的分类及其代码 按照环境条件标准,选择产品的应用环境条件是确定"
        "产品环境适应性的一个捷径。 表 9 产品应用环境条件类型 序号 应用环境条件类型 数字代码 "
        "国家标准 备注 1 运输 1 GB/T4798.1—2005 2 贮存 2 GB/T4798.2—2008 3 有气候防护场所"
        "固定使用 3 GB/T47 4 地面车辆使用 5 GB/T4798.5—2007",
        "GB/T4798.5—2007",
    ),
]

IDS = [c[0] for c in CASES]


# ---------------------------------------------------------------- 核心：表格末格必须存活

@pytest.mark.parametrize("label,text,needle", CASES, ids=IDS)
def test_table_last_cell_survives_with_own_standard(label, text, needle):
    """传了自家标准号 → 表格末格（别人的标准号）不再被当成页眉删掉。

    ⚠ 断言用 `endswith` 而不是 `in`：同一个标准号在表内可能**出现多次**
    （交通标志表里 JT/T132—2003 出现 3 次），只判包含会在尾格被删后仍然通过。
    """
    out = strip_watermark_lines(text, own_standard_no=OWN)
    assert out.rstrip().endswith(needle), f"{label}：表格末格被误删"


# ---------------------------------------------------------------- 反向：真页眉仍要删掉

@pytest.mark.parametrize("label,text,needle", CASES, ids=IDS)
def test_own_header_tail_is_still_removed(label, text, needle):
    """自家的行尾页眉仍必须删干净 —— 修缺口不等于把真页眉一起放过。"""
    out = strip_watermark_lines(text + f" 7 {OWN}", own_standard_no=OWN)
    assert f"7 {OWN}" not in out, f"{label}：自家页眉没删掉"
    assert out.rstrip().endswith(needle), f"{label}：删页眉时连带删掉了正文"


def test_own_header_line_is_still_removed():
    """整行即页眉（`^…$` 族）同样只按自家标准号判定。"""
    out = strip_watermark_lines("5 GB/T 28788-2012", own_standard_no=OWN)
    assert out.strip() == "", "整行页眉（自家标准号）应被删除"


def test_foreign_standard_only_line_is_kept():
    """整行只有**别的**标准号时，不再整行删除（那可能是一格独立成行的数据）。"""
    out = strip_watermark_lines("20 GB/T699—2015", own_standard_no=OWN)
    assert "GB/T699—2015" in out


def test_own_standard_fullwidth_still_matches():
    """库里的标准号可能是**全角斜杠**（实测 `GB／T 10067.6-2023`）。

    本文本侧的尾巴是半角（实测样本都是半角），而 `own_standard_no` 来自库、可能全角
    → 比较前必须抹平，否则"自家页眉"会被误判成"别人的标准号"而留下。
    """
    out = strip_watermark_lines("7 GB/T 10067.6—2023", own_standard_no="GB／T 10067.6-2023")
    assert out.strip() == "", "全角写法的 own_standard_no 应能与半角尾巴匹配"


def test_header_written_without_slash_t_is_still_removed():
    """**页眉常把 `GB/T` 印成 `GB`**（实测 226 行属此类）→ 比较键必须只认"号 + 年"。

    这条是我自己的验证脚本抓出来的：最初按**整串**比较标准号，于是
    `own='GB／T 12041.1-2010'` 与页眉 `'1 GB 12041.1—2010'` 被判为"别人的标准号"而
    **留下不删** —— 226 行真页眉因此漏删。改为只比"号 + 年"后修复。
    """
    out = strip_watermark_lines("正文结束。 1 GB 12041.1—2010",
                                own_standard_no="GB／T 12041.1-2010")
    assert "12041.1" not in out, "页眉把 GB/T 印成 GB 时仍必须删掉"
    out2 = strip_watermark_lines("5 GB 12041.1—2010",
                                 own_standard_no="GB/T 12041.1-2010")
    assert out2.strip() == "", "整行页眉同理"


def test_different_number_same_family_is_kept():
    """同一个前缀族但**号不同** → 是别人的标准，必须保住（表格里的引用）。"""
    out = strip_watermark_lines("表 2 材料 优质碳素结构钢 20 GB/T699—2015",
                                own_standard_no="GB/T 12041.1-2010")
    assert out.rstrip().endswith("GB/T699—2015")


def test_different_part_same_number_is_kept():
    """分册号不同（10029.2 vs 10029）→ 不同分册，必须保住。"""
    out = strip_watermark_lines("3 GB/T 10029.2—2010", own_standard_no="GB/T 10029-2010")
    assert out.rstrip().endswith("10029.2—2010")


def test_fullwidth_slash_inside_text_is_not_matched():
    """**已知限制（有意保留，不修）**：正文里的全角斜杠标准号不被页眉判据识别。

    判据的前缀族是 `GB|DB|JGJ|…` + 可选 ASCII `/`，从一开始就只认半角斜杠；
    实测样本里正文尾巴都是半角（全角只出现在 `doc_meta.standard_no`），
    故不为此放宽判据（放宽会扩大误删面）。本用例把限制**显式记录**，
    而不是让它以"某天有人发现漏删"的形式存在。
    """
    out = strip_watermark_lines("7 GB／T 10067.6—2023", own_standard_no="GB/T 10067.6-2023")
    assert out.strip() == "7 GB／T 10067.6—2023"


# ---------------------------------------------------------------- 不回归：合法引用必须存活

@pytest.mark.parametrize("text", [
    "本附录使用 SOAP 1.2 规范，命名空间为 http://www.w3.org/2003/05/soap-envelope",
    "按 GB/T 18654.1 的规定执行。",
    "应符合 GB/T 10029—2010",
    "见表 5 GB/T 10029—2010 的规定",
])
def test_legitimate_text_still_survives_with_own_standard(text):
    """传 own_standard_no 不得削弱原有的"合法引用必存活"保证。"""
    assert strip_watermark_lines(text, own_standard_no=OWN) == text


def test_watermark_tokens_still_removed_with_own_standard():
    """URL / 工具水印两族与 own_standard_no 无关，仍应照删。"""
    out = strip_watermark_lines("正文。\n网址 www.spc.net.cn\n结论。", own_standard_no=OWN)
    assert "www.spc.net.cn" not in out and "正文。" in out and "结论。" in out
    asp = strip_watermark_lines(
        "1 范围 5 GB/T 10029—2010 Evaluation Only. Created with Aspose.PDF. "
        "Copyright 2002-2025 Aspose Pty Ltd.", own_standard_no=OWN)
    assert "Aspose" not in asp


# ---------------------------------------------------------------- 向后兼容（关键）

@pytest.mark.parametrize("label,text,needle", CASES, ids=IDS)
def test_without_own_standard_behaviour_is_unchanged(label, text, needle):
    """**不传 own_standard_no 时保持历史行为**（表格末格仍会被删）。

    这条是**故意**钉住旧行为的：既有调用方（如仅做纯文本清洗的消费者）没有文档上下文，
    悄悄改变它们的输出会造成无痕回归。要修就得显式传 own_standard_no。
    """
    out = strip_watermark_lines(text)
    assert not out.rstrip().endswith(needle), \
        "不传 own_standard_no 时应保持历史行为（否则既有调用方输出会无痕改变）"


# ---------------------------------------------------------------- 归一函数本身

@pytest.mark.parametrize("raw,expect", [
    ("GB/T 3608-2008", "GBT3608-2008"),
    ("GB／T 3608-2008", "GBT3608-2008"),     # 全角斜杠
    ("gb/t 3608—2008", "GBT3608-2008"),      # 小写 + 长横
    ("GB/T 3608–2008", "GBT3608-2008"),      # en dash
    ("GB/T 3608－2008", "GBT3608-2008"),     # 全角连字符
    ("GB 10769—2025", "GB10769-2025"),       # 无分册字母
    ("GB/T 10067.6-2023", "GBT10067.6-2023"),  # 带分册号
    (None, ""),
])
def test_canon_standard_no(raw, expect):
    assert canon_standard_no(raw) == expect


# ---------------------------------------------------------------- 端到端接线

def _middle_with_table_cell(own: str, tmp_path, first: str | None = None):
    """一页 middle.json：正文里既有**自家页眉**（应删）又有**表格末格**（别人的标准号，应留）。"""
    import json
    from pathlib import Path

    first = first or "5.2.1 材料要求：锅炉受压元件材料见表 2。"

    def _ln(content):
        return {"bbox": [60.0, 700.0, 530.0, 720.0],
                "spans": [{"type": "text", "content": content}]}

    mj = {"pdf_info": [{
        "page_idx": 0, "page_size": [595.0, 841.0],
        "para_blocks": [{"type": "text", "bbox": [60.0, 600.0, 530.0, 720.0], "lines": [
            _ln(first),
            _ln("牵条 优质碳素结构钢 20 GB/T699—2015"),
            _ln("7 " + own),
        ]}],
        "discarded_blocks": [],
    }]}
    p = Path(tmp_path) / "m.json"
    p.write_text(json.dumps(mj, ensure_ascii=False), encoding="utf-8")
    return p


def test_ingest_wiring_passes_own_standard(tmp_path, monkeypatch):
    """**端到端接线**：`build_clause_models(doc_id, standard_no, …)` 必须把文档自己的
    标准号透传进清洗链 —— 否则单元测试全绿而真机入库照旧误判。

    做法：截获 `text_utils.clean_clause_text`（`build_clause_models` 在函数体内
    `from … import`，故打补丁生效），断言 kwarg 确实到了。
    """
    from src.core import text_utils
    from src.core.ingestion.pipeline import (
        build_clause_models, load_middle_items, split_items_into_clauses)

    own = "GB/T 12041.1-2010"
    seen = {}
    real = text_utils.clean_clause_text

    def spy(text, **kw):
        seen.update(kw)
        return real(text, **kw)

    monkeypatch.setattr(text_utils, "clean_clause_text", spy)
    items, page_sizes = load_middle_items(_middle_with_table_cell(own, tmp_path))
    clauses = split_items_into_clauses(items)
    build_clause_models("w1", own, "standard", clauses, page_sizes)

    assert seen.get("own_standard_no") == own, \
        "入库清洗链没拿到本文档自己的标准号（水印判据无法消歧）"


def test_ingest_removes_own_header_end_to_end(tmp_path):
    """自家页眉（页码 + 本文档标准号）在真链路里仍被删掉。"""
    from src.core.ingestion.pipeline import (
        build_clause_models, load_middle_items, split_items_into_clauses)

    own = "GB/T 12041.1-2010"
    items, page_sizes = load_middle_items(_middle_with_table_cell(own, tmp_path))
    clauses = split_items_into_clauses(items)
    models, _ = build_clause_models("w2", own, "standard", clauses, page_sizes)
    text = "\n".join(m.content_text for m in models)
    assert "7 " + own not in text, "端到端：自家页眉必须被删掉"


def test_ingest_inline_furniture_keeps_foreign_standard(tmp_path):
    """**行内**家具片段也已接上下文：引用**别的**标准的片段（表格末格）不再被剥掉。

    用**长正文**（>80 字）绕开切分层的 80 字家具剥离，从而只考验 `build_clause_models`
    里的逐行剥离（`_STD_CODE_FRAG`）—— 那一处签名里就有 `standard_no`，已接上下文。
    """
    from src.core.ingestion.pipeline import (
        build_clause_models, load_middle_items, split_items_into_clauses)

    own = "GB/T 12041.1-2010"
    long_first = ("5.2.1 材料要求：锅炉主要受压元件材料应按表 2 的规定执行，"
                  "允许采用性能不低于表 2 规定的其他材料，具体要求由设计文件规定。")
    items, page_sizes = load_middle_items(
        _middle_with_table_cell(own, tmp_path, first=long_first))
    clauses = split_items_into_clauses(items)
    models, _ = build_clause_models("w3", own, "standard", clauses, page_sizes)
    text = "\n".join(m.content_text for m in models)
    assert "GB/T699—2015" in text, "行内家具剥离把表格末格（别人的标准）切掉了"
    assert "7 " + own not in text, "自家页眉仍应被删掉"


def test_ingest_short_block_keeps_foreign_standard(tmp_path):
    """**短块**（≤80 字）走切分层的家具剥离 —— 传了标准号后同样不再误删。

    `run_full_ingest` 现在把 `standard_no` 传给切分层；本用例按同一条链调用
    （`split_items_into_clauses(items, standard_no=own)` → `build_clause_models`）。
    """
    from src.core.ingestion.pipeline import (
        build_clause_models, load_middle_items, split_items_into_clauses)

    own = "GB/T 12041.1-2010"
    items, page_sizes = load_middle_items(_middle_with_table_cell(own, tmp_path))
    clauses = split_items_into_clauses(items, standard_no=own)
    models, _ = build_clause_models("w4", own, "standard", clauses, page_sizes)
    text = "\n".join(m.content_text for m in models)
    assert "GB/T699—2015" in text, "短块的家具剥离把表格末格（别人的标准）切掉了"
    assert "7 " + own not in text, "自家页眉仍应被删掉"


def test_splitter_without_standard_keeps_historic_behaviour(tmp_path):
    """**向后兼容**：不传 `standard_no` 时，切分层的家具剥离仍是历史行为（一律剥掉）。

    既有调用方（预览路径、数十条既有用例）都走这条；不能因为新参数而悄悄改变它们。
    """
    from src.core.ingestion.pipeline import load_middle_items, split_items_into_clauses

    own = "GB/T 12041.1-2010"
    items, _ = load_middle_items(_middle_with_table_cell(own, tmp_path))
    texts = [t for c in split_items_into_clauses(items) for t in c.texts]
    assert not any("GB/T699—2015" in t for t in texts), \
        "不传 standard_no 时应保持历史行为（否则既有调用方输出会无痕改变）"


def test_own_key_of_rejects_placeholder():
    """`_own_key_of` 必须把"看着不像标准号"的占位符挡回 None。

    dry-run 预览在猜不出标准号时会传 `"未知标准号"`；若它变成非 None 的比较键，
    就会**永不匹配**，等于把家具剥离整体关掉（与历史行为不符）。
    """
    from src.core.ingestion.pipeline import _own_key_of
    assert _own_key_of(None) is None
    assert _own_key_of("") is None
    assert _own_key_of("未知标准号") is None
    assert _own_key_of("GB/T 12041.1-2010") == "12041.1-2010"
