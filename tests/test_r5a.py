"""阶段3 R5a 测试：放宽的内部引用抽取 + 证据链扩展检索。"""
import pytest


def test_loosened_internal_refs():
    from src.core.knowledge.classifier import classify_clause
    cases = [
        ("作业要求按 5.2.1 执行。", ["5.2.1"]),          # 无前缀"按 X 执行"
        ("安全措施应符合本规范第 6.4.2 条的规定。", ["6.4.2"]),
        ("依照 12.3 条办理审批。", ["12.3"]),
        ("监护要求执行9.2.6", ["9.2.6"]),
    ]
    for text, expect in cases:
        tc = classify_clause(text, doc_type="standard")
        assert tc.cross_refs == expect, f"{text} → {tc.cross_refs}"


def test_expand_evidence_chain(db):
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import write_transaction
    from src.core.retrieval.hybrid_engine import expand_evidence_chain

    with write_transaction() as conn:
        clause_repo.insert_document(conn, dict(
            doc_id="de1", standard_no="GB E-2022", standard_name="t", short_code="e",
            current_revision_id="r", domain_tags=[], file_path="e.pdf", file_hash="he1"))
        for cid, no, text in [
            ("ec1", "5.2.1", "动火作业应有专人监护。按 5.2.2 执行监护交接。"),
            ("ec2", "5.2.2", "监护交接应记录。"),
            ("ec3", "5.9.9", "无关条款，不应被扩展。"),
        ]:
            conn.execute(
                "INSERT INTO clause_revision (clause_revision_id, doc_revision_id, doc_id,"
                " clause_key, clause_number, content_text, cross_refs, page_start, page_end)"
                " VALUES (?,?,?,?,?,?,?,?,1)",
                (cid, "r", "de1", no, no, text,
                 '["5.2.2"]' if cid == "ec1" else "[]", 1))
        # 手工建边：ec1 --reference_relation--> ec2
        clause_repo.insert_edges_in_txn(conn, [
            ("reference_relation", "ec1", "ec2", 0.9, "active")])

    expanded = expand_evidence_chain(db, ["ec1"], max_hops=1)
    assert len(expanded) == 1
    assert expanded[0]["clause"].clause_revision_id == "ec2"
    assert expanded[0]["expanded_from"] == "ec1"
    assert expanded[0]["edge_type"] == "reference_relation"


def test_search_with_details_expansion(db):
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import write_transaction
    from src.core.retrieval.hybrid_engine import search_with_details

    with write_transaction() as conn:
        clause_repo.insert_document(conn, dict(
            doc_id="de2", standard_no="GB E2-2022", standard_name="t", short_code="e2",
            current_revision_id="r", domain_tags=[], file_path="e2.pdf", file_hash="he2"))
        from src.core.storage.clause_repo import _seg
        for cid, no, text in [
            ("ex1", "6.1.1", "高处作业应系安全带。按 6.1.2 执行验收。"),
            ("ex2", "6.1.2", "验收应留存记录。"),
        ]:
            conn.execute(
                "INSERT INTO clause_revision (clause_revision_id, doc_revision_id, doc_id,"
                " clause_key, clause_number, content_text, cross_refs, page_start, page_end)"
                " VALUES (?,?,?,?,?,?,?,?,1)",
                (cid, "r", "de2", no, no, text, '["6.1.2"]' if cid == "ex1" else "[]", 1))
            conn.execute(
                "INSERT INTO clause_fts (clause_revision_id, clause_number, standard_no,"
                " title, content_segmented, modality, subject, behavior_scope_segmented)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (cid, no, "GB", "", _seg(text), "", "", ""))
        clause_repo.insert_edges_in_txn(conn, [
            ("reference_relation", "ex1", "ex2", 0.9, "active")])

    out = search_with_details("高处作业 安全带", top_k=2, channels=["fts"])
    assert any(r.clause_revision_id == "ex1" for r in out["results"])
    assert out["expanded"], "应沿证据边扩展出 6.1.2"
    assert out["expanded"][0]["clause"].clause_revision_id == "ex2"
    assert out["debug"]["expanded_count"] == len(out["expanded"])
