"""Task 11.1 docx 入库测试：降级直解路径（无 Word 环境可测）+ 条款切分 + 表格保真。"""
from pathlib import Path

import pytest


@pytest.fixture()
def docx_fixture(tmp_path):
    from docx import Document
    doc = Document()
    doc.add_heading("测试制度文档", level=1)
    doc.add_heading("第一条 总则", level=2)
    doc.add_paragraph("本制度适用于全体员工，应当遵守执行。")
    doc.add_heading("第二条 责任", level=2)
    doc.add_paragraph("各部门应当落实安全管理责任。")
    doc.add_paragraph("第三条 处罚")
    doc.add_paragraph("违反本制度的，按照公司规定予以处罚。")
    t = doc.add_table(rows=2, cols=2)
    t.cell(0, 0).text = "项目"
    t.cell(0, 1).text = "要求"
    t.cell(1, 0).text = "巡查"
    t.cell(1, 1).text = "每日一次"
    p = tmp_path / "测试制度.docx"
    doc.save(str(p))
    return p


def test_parse_docx_text(docx_fixture):
    from src.core.ingestion.docx_adapter import parse_docx_text
    clauses = parse_docx_text(docx_fixture)
    numbers = [c["number"] for c in clauses]
    assert "第一条" in numbers and "第二条" in numbers
    first = next(c for c in clauses if c["number"] == "第一条")
    assert "全体员工" in first["text"]


def test_run_docx_ingest_direct(docx_fixture, monkeypatch):
    # 显式禁 COM（本机装了 WPS/pywin32 时不再自动走 COM 转 PDF 路径），
    # 锁定被测目标 = 降级直解（docx-direct 无 bbox）
    monkeypatch.setattr("src.core.ingestion.docx_adapter.docx_to_pdf_via_com",
                        lambda *a, **k: False)
    from src.core.ingestion.docx_ingest import run_docx_ingest
    from src.core.storage.sqlite_db import get_db_connection
    out = run_docx_ingest(docx_fixture, "公司制度-测试", "测试制度",
                          doc_type="标准", domain_tags=["安全"])
    assert out["status"] == "ok"
    assert out["total_clauses"] >= 2
    assert out["mode"] == "docx-direct"
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT cr.clause_number, cr.knowledge_type, dm.doc_type"
        " FROM clause_revision cr JOIN doc_meta dm ON dm.doc_id=cr.doc_id"
        " WHERE cr.doc_id=?", (out["doc_id"],)).fetchall()
    assert any(r["clause_number"] == "第一条" for r in rows)
    # 幂等：重复入库 duplicate
    assert run_docx_ingest(docx_fixture, "公司制度-测试", "测试制度")["status"] == "duplicate"


def test_run_docx_ingest_missing():
    from src.core.ingestion.docx_ingest import run_docx_ingest
    out = run_docx_ingest(Path("Z:/不存在.docx"), "x", "x")
    assert out["status"] == "error"
