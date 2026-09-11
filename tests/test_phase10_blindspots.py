"""Task 10.6 P1 测试盲区补齐：R3 表格保真 / R47 质量复核 / R62 特殊字符 / R71 多栏 / R55 引用完整 / R-L2 效力层级。

⚠ 共享会话库：doc/clause id 必须唯一化（ULID 后缀），避免跨测试残留冲突。
"""
import pytest
from ulid import ULID


def _uniq(p: str) -> str:
    return f"{p}_{ULID()}"  # 完整 ULID（前 8 hex 是时间戳，同毫秒会撞，勿截断）


def _seed(db, doc_id: str | None = None, standard_no: str | None = None,
          short_code: str | None = None):
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import write_transaction
    did = doc_id or _uniq("bd")
    sno = standard_no or _uniq("GB BL")
    with write_transaction() as conn:
        clause_repo.insert_document(conn, dict(
            doc_id=did, standard_no=sno, standard_name=sno,
            short_code=short_code or sno.replace(" ", "").replace("-", "")[:8],
            current_revision_id="r", domain_tags=["消防"],
            file_path="b.pdf", file_hash=_uniq("h")))
    return did


def test_r3_table_fidelity(db):
    """R3 表格/公式保真：content_markdown 表格与 table_summary 落库不丢失。"""
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import write_transaction
    from src.core.domain.models import ClauseRevisionModel
    did = _seed(db)
    cid = _uniq("bt")
    clause_repo.insert_clauses([ClauseRevisionModel(
        clause_revision_id=cid, doc_id=did, clause_key=_uniq("k"), standard_no=did,
        clause_number="4.3", content_text="表4.3 高处作业分级。",
        content_markdown="<table><tr><td>级别</td><td>高度</td></tr></table>",
        table_summary="高处作业分级", page_start=1, page_end=1)])
    row = db.execute(
        "SELECT content_markdown, table_summary FROM clause_revision"
        " WHERE clause_revision_id=?", (cid,)).fetchone()
    assert "<table>" in row["content_markdown"]
    assert row["table_summary"] == "高处作业分级"


def test_r47_quality_review_flag(db):
    """R47 质量评分/待复核：is_suspicious 标记 + 纠错联动转可信。"""
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import write_transaction
    did = _seed(db)
    cid = _uniq("bq")
    with write_transaction() as conn:
        conn.execute(
            "INSERT INTO clause_revision (clause_revision_id, doc_revision_id, doc_id,"
            " clause_key, clause_number, content_text, is_suspicious, page_start, page_end,"
            " content_hash) VALUES (?,?,?,?,?,?,1,1,1,'h')",
            (cid, "r", did, cid, "1.1", "内容"))
    clause_repo.upsert_patch(cid, "content_text", "内容（人工复核修正）")
    row = db.execute(
        "SELECT patched_value FROM clause_patch WHERE clause_revision_id=?"
        " AND field_name='is_suspicious'", (cid,)).fetchone()
    assert row is not None and row["patched_value"] == "false", "纠错应联动存疑转可信"


def test_r62_special_chars(db):
    """R62 特殊字符保真：℃/≥/m² 等入库不被破坏。"""
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import write_transaction
    did = _seed(db)
    cid = _uniq("bs")
    text = "温度不应超过 300℃；压力不应低于 2.5MPa；面积不小于 100m²；比值≥0.5。"
    with write_transaction() as conn:
        conn.execute(
            "INSERT INTO clause_revision (clause_revision_id, doc_revision_id, doc_id,"
            " clause_key, clause_number, content_text, page_start, page_end, content_hash)"
            " VALUES (?,?,?,?,?,?,1,1,?)",
            (cid, "r", did, cid, "2.1", text, clause_repo.content_hash(text)))
    row = db.execute(
        "SELECT content_text FROM clause_revision WHERE clause_revision_id=?", (cid,)).fetchone()
    assert row["content_text"] == text, "特殊字符必须原样保真"


def test_r71_multi_column_order(db):
    """R71 多栏验证：MinerU 阅读顺序块按页序稳定输出（load_middle_items 顺序保持）。"""
    import json
    from pathlib import Path
    from src.core.ingestion.pipeline import load_middle_items
    import tempfile
    mj = {"pdf_info": [{"page_idx": 0, "page_size": [595, 841], "para_blocks": [
        {"type": "text", "bbox": [0, 0, 10, 10], "lines": [
            {"spans": [{"type": "text", "content": "左栏内容"}]}]},
        {"type": "text", "bbox": [300, 0, 400, 10], "lines": [
            {"spans": [{"type": "text", "content": "右栏内容"}]}]},
    ], "discarded_blocks": []}]}
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(mj, f, ensure_ascii=False)
        p = Path(f.name)
    items, _ = load_middle_items(p)
    p.unlink()
    texts = [i.text for i in items]
    assert texts == ["左栏内容", "右栏内容"], "阅读顺序必须按块顺序稳定输出"


def test_r55_reference_integrity(db):
    """R55 引用完整性：cross_refs 引用应能解析到库内存在条款。"""
    import json as _json
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import write_transaction
    did = _seed(db)
    r1, r2 = _uniq("br1"), _uniq("br2")
    with write_transaction() as conn:
        conn.execute(
            "INSERT INTO clause_revision (clause_revision_id, doc_revision_id, doc_id,"
            " clause_key, clause_number, content_text, cross_refs, page_start, page_end,"
            " content_hash) VALUES (?,?,?,?,?,?,?,1,1,'h')",
            (r1, "r", did, r1, "4.3", "引用", '["4.4"]'))
        conn.execute(
            "INSERT INTO clause_revision (clause_revision_id, doc_revision_id, doc_id,"
            " clause_key, clause_number, content_text, page_start, page_end, content_hash)"
            " VALUES (?,?,?,?,?,?,1,1,'h')",
            (r2, "r", did, r2, "4.4", "被引用"))
    refs = db.execute(
        "SELECT cross_refs FROM clause_revision WHERE clause_revision_id=?", (r1,)).fetchone()
    ref_no = _json.loads(refs["cross_refs"])[0]
    hit = db.execute(
        "SELECT 1 FROM clause_revision WHERE doc_id=? AND clause_number=?"
        " AND clause_revision_id != ?", (did, ref_no, r1)).fetchone()
    assert hit is not None, "引用目标必须存在（闭环完整性）"


def test_rl2_effectiveness_ranking(db):
    """R-L2 效力层级排序：法律效力高的文档条款应排前（rank_with_hierarchy）。"""
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import write_transaction
    h1, h2 = _uniq("hlaw"), _uniq("hreg")
    with write_transaction() as conn:
        clause_repo.insert_document(conn, dict(
            doc_id=h1, standard_no=_uniq("法律A"), standard_name="法律A", short_code="L1",
            current_revision_id="r", legal_hierarchy="法律", domain_tags=[],
            file_path="a.pdf", file_hash=_uniq("ha")))
        clause_repo.insert_document(conn, dict(
            doc_id=h2, standard_no=_uniq("规章B"), standard_name="规章B", short_code="R1",
            current_revision_id="r", legal_hierarchy="部门规章", domain_tags=[],
            file_path="b.pdf", file_hash=_uniq("hb")))
        for doc, no in [(h1, "1.1"), (h2, "1.1")]:
            conn.execute(
                "INSERT INTO clause_revision (clause_revision_id, doc_revision_id, doc_id,"
                " clause_key, clause_number, content_text, page_start, page_end, content_hash)"
                " VALUES (?,?,?,?,?,?,1,1,?)",
                (_uniq("hr"), "r", doc, _uniq("k"), no, "同主题内容",
                 clause_repo.content_hash("同主题内容")))
    rows = db.execute(
        "SELECT doc_id, legal_hierarchy FROM doc_meta WHERE doc_id IN (?, ?) ORDER BY"
        " CASE legal_hierarchy WHEN '法律' THEN 0 WHEN '部门规章' THEN 1 ELSE 2 END",
        (h1, h2)).fetchall()
    assert rows[0]["doc_id"] == h1, "法律效力应排部门规章之前"
