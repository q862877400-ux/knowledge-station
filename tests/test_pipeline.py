"""T05 管线测试：切分/分型/边/坐标翻转（合成 fixture）+ 真实 middle.json 集成。"""
import json
from pathlib import Path

import pytest

from src.core.ingestion.pipeline import (
    MidItem, build_clause_models, load_middle_items, resolve_edges,
    split_items_into_clauses,
)
from src.core.knowledge.classifier import classify_clause, normalize_clause_number


def _mk_middle(tmp_path: Path) -> Path:
    """合成一份 2 页 middle.json：封面/前言 + 2 条款(跨页拼接) + 但书 + 表绑定 + 附录。"""
    mj = {
        "pdf_info": [
            {"page_idx": 0, "page_size": [595, 841],
             "para_blocks": [
                 {"type": "text", "bbox": [60, 700, 500, 740], "lines": [
                     {"spans": [{"type": "text", "content": "前  言"}]}]},
                 {"type": "text", "bbox": [60, 600, 500, 660], "lines": [
                     {"spans": [{"type": "text", "content": "本标准代替 GB 30871-2014。"}]}]},
             ],
             "discarded_blocks": [
                 {"type": "header", "bbox": [200, 20, 400, 40], "lines": [
                     {"spans": [{"type": "text", "content": "GB 30871—2022"}]}]}]},
            {"page_idx": 1, "page_size": [595, 841],
             "para_blocks": [
                 {"type": "text", "bbox": [60, 700, 530, 740], "lines": [
                     {"spans": [{"type": "text",
                                 "content": "5.2.1 动火作业应有专人监护，作业前应清除易燃物品。"}]}]},
                 {"type": "text", "bbox": [60, 650, 530, 690], "lines": [
                     {"spans": [{"type": "text",
                                 "content": "但节假日或夜间作业除外，应升级管理。"}]}]},
                 {"type": "table", "bbox": [60, 400, 530, 600], "blocks": [
                     {"type": "table_caption", "lines": [
                         {"spans": [{"type": "text", "content": "表 5.2.1 动火分级"}]}]},
                     {"type": "table_body", "lines": [
                         {"spans": [{"type": "table", "html": "<table><tr><td>级别</td></tr></table>"}]}]},
                 ]},
                 {"type": "text", "bbox": [60, 300, 530, 340], "lines": [
                     {"spans": [{"type": "text",
                                 "content": "5.2.2 动火分析合格标准：可燃气体浓度不大于 0.5%。"}]}]},
             ],
             "discarded_blocks": [
                 {"type": "page_number", "bbox": [280, 800, 320, 820], "lines": [
                     {"spans": [{"type": "text", "content": "2"}]}]}]},
        ]
    }
    p = tmp_path / "fake_middle.json"
    p.write_text(json.dumps(mj, ensure_ascii=False), encoding="utf-8")
    return p


def test_load_middle_items_drops_discarded(tmp_path):
    items, page_sizes = load_middle_items(_mk_middle(tmp_path))
    assert page_sizes[0] == (595.0, 841.0)
    texts = " ".join(i.text for i in items)
    assert "GB 30871—2022" not in texts, "页眉应被丢弃（R65/E4）"
    assert "动火作业" in texts
    kinds = [i.kind for i in items]
    assert "table" in kinds


def test_split_clauses_and_table_binding(tmp_path):
    items, page_sizes = load_middle_items(_mk_middle(tmp_path))
    clauses = split_items_into_clauses(items)
    numbers = [c.number for c in clauses]
    assert "5.2.1" in numbers and "5.2.2" in numbers
    c521 = next(c for c in clauses if c.number == "5.2.1")
    assert "但节假日" in "\n".join(c521.texts), "但书应拼接到母条款（E4 跨块合并）"
    assert c521.table_html and "<table>" in c521.table_html, "表 5.2.1 应绑定母条款（E5）"
    assert c521.table_summary == "动火分级"
    preface = [c for c in clauses if c.number.startswith("前置")]
    assert preface, "前言应成为前置说明"


def test_split_rejects_table_value_clause_heads():
    """E8 表格数值防误判（2026-08-28 生产实测）：成分表数据行不得切成 0.x/伪章号条款。

    化学分析类标准（GB/T 3260.x/3286.x/5009.x 等）的大表被 MinerU 切成文本行后，
    行首单元格值（0.10 / 0.0001 / 1103.11 / "4.2 1.5 3.0"）曾满足 _CLAUSE_GB
    门槛 → 每行一个假条款（41% 新产出文档中招）。E8 闸门：章号首段∈1..60
    且号码后不紧跟 ≥2 个独立数字（表格行特征）。
    """
    items = [
        MidItem(kind="text", text="4.1 化学成分应符合表 1 的规定", page_idx=0),
        MidItem(kind="text", text=(
            "0.10 0.030 0.002 余量\n"
            "0.15 0.040 0.003 余量\n"
            "0.0001 0.001\n"
            "4.2 1.5 3.0 0.25\n"
            "1103.11 抗拉强度\n"), page_idx=0),
        MidItem(kind="text", text="5.2.1 动火作业应专人监护", page_idx=1),
    ]
    clauses = split_items_into_clauses(items)
    numbers = [c.number for c in clauses]
    assert "4.1" in numbers and "5.2.1" in numbers
    assert not any(n.startswith("0.") or n == "1103.11" or n == "4.2"
                   for n in numbers), numbers
    # 表格行应并入母条款 4.1，内容不丢
    blob = "\n".join("\n".join(c.texts) for c in clauses)
    assert "0.030" in blob and "1103.11" in blob and "抗拉强度" in blob


def test_pua_detector_catches_cid_garbage_without_pua_glyphs():
    """E9 cid 乱码变体（2026-08-28 GB/T 20529.2-2010 实测）：文本层不含
    犌犅犜/数字错位特征，而是拉丁扩展+泰米尔+生僻字 + 超长同字符跑，
    也必须判乱码转 OCR，否则 0 条款入库。"""
    from src.core.ingestion.mineru_adapter import text_layer_pua_mangled

    garbage = "www.bzfxw.com / 㼬 ௿ / ಆ૆㠯ఠ ಆććććććććććććććććććććććććć / ಇ૆㻰㠯ᕓᑁ⩔᪳Т ಆćććććććććććććććććććććććć"
    assert text_layer_pua_mangled([{"text": garbage}] * 3), "cid 乱码必须被判中"
    # 正常中文不得误伤
    normal = "4.1 化学成分应符合表 1 的规定。表 1 中的数值……\n4.2 抗拉强度不小于 1103 N/mm²。"
    assert not text_layer_pua_mangled([{"text": normal}]), "正常文本不得误判"


def test_pua_detector_catches_ascii_mapped_garbage():
    """E9b 判据四：cid 错位第四形态——汉字被映射为 ASCII（GB/T 35210.1-2023
    用户实测报障），无怪区字符、无非 ASCII 长跑、条款号首段合法，
    仅能靠「中文标准正文无汉字」捕获。"""
    from src.core.ingestion.mineru_adapter import text_layer_pua_mangled

    garbage = (
        "34.567.589.:;) a)*<\"*!'=>yz+a>?k@>GA)!!\"!#!\"#$%,$\"#%#! www.bzfxw.com"
        "%!!$!!WXtuYZ[PM?s¯BCWXDE¨[PµF]GH(IJKnM?01+sWXµD] 2Ln 3 M C)W X t u Y Z "
        "[ P$\\ [ ] v . 0 1 b c N E n Ä O+m ? U V 1 - ] 1)-.$/#%\"!* P¯¶QRST("
        "<WXtuYZ[P$\\[]v.ghnej+UVlmpW)%%%k!lm'STUV1)%%%k\"lm' ]1)-.$/#%\"!*,!"
        "%\"*!'yzMXwÜ%+YZ[denh(\\]/^/JKn _+YZ[P M?nE`æç-Mabcdyef)fgæçnhi+RSb?"
        "M?vjn[P]?tu¯W Xkln [P]+mn<©Mn[P]+¥3MCtu[PJKo[PVp [P]qf?¡¢[P]"
    )
    assert len(garbage) >= 200
    assert text_layer_pua_mangled([{"text": garbage}]) is True
    # 正常中文条款不受影响
    normal = "4.1 化学成分应符合表 1 的规定。表 1 中的数值对热轧（锻造）钢材按 GB/T 223 的规定。"
    assert text_layer_pua_mangled([{"text": normal}]) is False


def test_delete_document_uses_bulk_fts_delete(db):
    """E10 性能根因（2026-08-28 试点实测）：clause_fts.clause_revision_id 是
    UNINDEXED 列，逐行 DELETE 每行都全表扫描 24 万行 FTS 索引——覆盖式重入库
    每本文档都要付分钟级代价（py-spy 实测单文档卡 15 分钟）。
    delete_document 必须用单条子查询批量删除（≤2 条语句），且删干净不留孤儿。"""
    from src.core.domain.models import ClauseRevisionModel
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import write_transaction

    if db.execute("SELECT 1 FROM doc_meta WHERE doc_id='e10'").fetchone():
        clause_repo.delete_document("e10")
    with write_transaction() as c:
        clause_repo.insert_document(c, dict(
            doc_id="e10", standard_no="GB E10-2025", standard_name="E10",
            short_code="e10", current_revision_id="r", domain_tags=[],
            file_path="e10.pdf", file_hash="he10"))
    clause_repo.insert_clauses([
        ClauseRevisionModel(
            clause_revision_id=f"e10c{i}", doc_id="e10", clause_key=f"e10k{i}",
            standard_no="GB E10-2025", clause_number=f"4.{i}",
            content_text=f"条款 {i} 的内容。", knowledge_type="legal",
            modality="应", modality_strength=3, page_start=1, page_end=1)
        for i in range(30)
    ])
    assert db.execute(
        "SELECT COUNT(*) FROM clause_fts WHERE clause_revision_id LIKE 'e10c%'"
    ).fetchone()[0] == 30

    stmts: list[str] = []
    db.set_trace_callback(stmts.append)
    try:
        clause_repo.delete_document("e10")
    finally:
        db.set_trace_callback(None)
    fts_deletes = [s for s in stmts if "DELETE FROM CLAUSE_FTS" in s.upper()]
    assert len(fts_deletes) <= 2, (
        f"clause_fts 删除语句 {len(fts_deletes)} 条（30 条款）——仍是逐行全表扫描")
    assert db.execute(
        "SELECT COUNT(*) FROM clause_fts WHERE clause_revision_id LIKE 'e10c%'"
    ).fetchone()[0] == 0
    assert db.execute(
        "SELECT COUNT(*) FROM clause_vec WHERE clause_revision_id LIKE 'e10c%'"
    ).fetchone()[0] == 0
    assert db.execute(
        "SELECT 1 FROM doc_meta WHERE doc_id='e10'").fetchone() is None


def test_build_models_classification_and_edges(tmp_path):
    items, page_sizes = load_middle_items(_mk_middle(tmp_path))
    clauses = split_items_into_clauses(items)
    models, raw_edges = build_clause_models("d1", "GB T-2022", "standard", clauses, page_sizes)
    by_no = {m.clause_number: m for m in models}
    m521, m522 = by_no["5.2.1"], by_no["5.2.2"]
    assert m521.knowledge_type == "rule" and m521.modality == "应"
    assert m522.knowledge_type == "data", "含数值量纲应归 data 型"
    assert m522.modality is None, "'可燃气体'的'可'不应误判为模态"
    assert m521.exception and "节假日" in m521.exception
    assert m521.hierarchy_path == "5 > 5.2"
    # 坐标契约（v5 修正）：source_span 原样直存 MinerU bbox（PDF 底部原点，y 向上；
    # 页顶文本 y 接近页高）。前端 PdfViewer 直接 convertToViewportPoint(x, y)，禁止翻转。
    span = m521.source_spans[0]
    assert span.bbox == pytest.approx([60.0, 700.0, 530.0, 740.0])  # 原样直存，未翻转
    number_to_id = {m.clause_number: m.clause_revision_id for m in models}
    edges = resolve_edges(raw_edges, number_to_id)
    assert all(e[0] in ("reference_relation", "exception_relation") for e in edges)


def test_classifier_details():
    tc = classify_clause("高层民用建筑之间的防火间距不应小于13m", doc_type="standard")
    assert tc.knowledge_type == "data" and tc.modality == "不应"
    tc2 = classify_clause("经营者不得利用格式条款排除消费者权利", doc_type="法律法规")
    assert tc2.knowledge_type == "legal" and tc2.subject == "经营者"
    tc3 = classify_clause("本规范第5.2.1条规定了动火监护要求", doc_type="standard")
    assert "5.2.1" in tc3.cross_refs
    assert normalize_clause_number("05.02.01") == "5.2.1"


@pytest.mark.skipif(
    not Path("var/mineru_cli_out/GB30871-2022识别版/auto/GB30871-2022识别版_middle.json").exists(),
    reason="真实 MinerU 产物不存在（本机运行时自动启用）")
def test_real_middle_json_integration():
    items, page_sizes = load_middle_items(
        Path("var/mineru_cli_out/GB30871-2022识别版/auto/GB30871-2022识别版_middle.json"))
    assert len(items) > 100
    clauses = split_items_into_clauses(items)
    numbers = {c.number for c in clauses}
    assert "5.2.1" in numbers and "6.2" in numbers
    c521 = next(c for c in clauses if c.number == "5.2.1")
    assert "专人监护" in c521.texts[0]


def test_interline_equation_restored(tmp_path):
    """2026-09-01 独立公式行（interline_equation）不再蒸发（GB/T 24276
    "公式没识别出来"根因）：此前 _spans_rows 只认 inline_equation，
    interline_equation 块 parts 落空 → 整条公式从条目流消失。修复后
    同走 latex_to_text → 可读 Unicode 文本行，并入所属条款。"""
    mj = {"pdf_info": [
        {"page_idx": 6, "page_size": [595.0, 841.0], "para_blocks": [
            {"type": "text", "bbox": [60, 700, 530, 740], "lines": [
                {"spans": [{"type": "text",
                            "content": "5.2.4 外壳的温升应按下式计算："}]}]},
            {"type": "interline_equation", "bbox": [251, 650, 419, 680],
             "lines": [{"spans": [{"type": "interline_equation",
                                   "content": "f { = } \\frac { h ^ { 1.35 } } "
                                              "{ A _ { \\mathrm { b } } }"}]}]},
        ]},
    ]}
    p = tmp_path / "eq_middle.json"
    p.write_text(json.dumps(mj, ensure_ascii=False), encoding="utf-8")

    items, _ = load_middle_items(p)
    eq = [i for i in items if i.kind == "text" and "f =" in (i.text or "")]
    assert eq, "独立公式行必须以文本条目入库，不得蒸发"
    t = eq[0].text
    assert "\\" not in t and "{" not in t, \
        f"LaTeX 命令/花括号应转为可读文本，实际: {t!r}"
    assert eq[0].bbox, "公式条目应带框（行框齐备，PDF 高亮不缺位）"

    clauses = split_items_into_clauses(items)
    assert [c.number for c in clauses] == ["5.2.4"], \
        "公式行不得伪造条款头（闸门兜底）"
    c524 = clauses[0]
    assert any("f =" in ln for ln in c524.texts), "公式行应并入所属条款 texts"
