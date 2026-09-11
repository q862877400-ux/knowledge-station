"""Task 11.3 自动标签测试：规则层提取 + 红线（不碰原文）断言。"""
import pytest


def test_auto_tag_standard_and_superseded():
    from src.core.knowledge.auto_tag import auto_tag
    text = ("中华人民共和国国家标准\n"
            "危险化学品企业特殊作业安全规范\n"
            "GB 30871—2022\n"
            "代替 GB 30871-2014\n"
            "自 2022 年 10 月 1 日起施行")
    t = auto_tag(text)
    assert "GB30871-2022" in (t.standard_no or "")
    assert t.year == "2022"
    assert "GB30871-2014" in (t.superseded or "")
    assert t.effective_from == "2022-10-01"
    assert "安全" in t.domain_tags


def test_auto_tag_filename_fallback():
    from src.core.knowledge.auto_tag import auto_tag
    t = auto_tag("仅一段无标准号的正文", filename="GB50016-2014建筑设计防火规范.pdf")
    assert t.year == "2014"
    assert "建筑" in t.domain_tags and "消防" in t.domain_tags


def test_apply_tags_does_not_touch_clause(db):
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import write_transaction
    from src.core.knowledge.auto_tag import auto_tag, apply_tags_to_doc_meta
    with write_transaction() as conn:
        clause_repo.insert_document(conn, dict(
            doc_id="tag1", standard_no="GB T", standard_name="t", short_code="t",
            current_revision_id="r", domain_tags=[], file_path="t.pdf", file_hash="ht"))
        conn.execute(
            "INSERT INTO clause_revision (clause_revision_id, doc_revision_id, doc_id,"
            " clause_key, clause_number, content_text, page_start, page_end, content_hash)"
            " VALUES ('tagc1','r','tag1','k','1.1','原始条文内容',1,1,'h')")
    tags = auto_tag("本规范适用于建筑消防设计，代替 GB X-2010，自 2024 年 1 月 1 日起施行")
    apply_tags_to_doc_meta("tag1", tags)
    doc = db.execute("SELECT domain_tags, effective_from FROM doc_meta WHERE doc_id='tag1'").fetchone()
    assert "建筑" in doc["domain_tags"] and doc["effective_from"] == "2024-01-01"
    # 红线：clause_revision 原文零改动
    raw = db.execute(
        "SELECT content_text FROM clause_revision WHERE clause_revision_id='tagc1'").fetchone()
    assert raw["content_text"] == "原始条文内容"
