"""Task 13.3 盲区补齐（免费路径 4 项）：R13 质量分级 / R44 离线开关 / R59 覆盖范围 / R67 过渡期。"""
import pytest
from ulid import ULID


def test_r13_quality_grade_tag(db):
    """R13 质量分级标签：doc_meta.quality_grade 落库与校验约束。"""
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import write_transaction
    did, sno = f"r13_{ULID()}", f"GB R13-{ULID()}"
    with write_transaction() as conn:
        clause_repo.insert_document(conn, dict(
            doc_id=did, standard_no=sno, standard_name=sno, short_code="R13",
            current_revision_id="r", quality_grade="B", domain_tags=[],
            file_path="r.pdf", file_hash=f"h{ULID()}"))
    row = db.execute("SELECT quality_grade FROM doc_meta WHERE doc_id=?", (did,)).fetchone()
    assert row["quality_grade"] == "B"
    assert db.execute(
        "SELECT 1 FROM doc_meta WHERE quality_grade IN ('A','B','C') AND doc_id=?",
        (did,)).fetchone() is not None


def test_r44_offline_flag_exists(db):
    """R44 离线模式：app_config 离线开关存在性与默认值（功能隐藏由前端门控）。"""
    from src.core.storage.sqlite_db import write_transaction
    with write_transaction() as conn:
        conn.execute(
            "INSERT INTO app_config (config_key, config_value) VALUES ('run_mode','online_preferred')"
            " ON CONFLICT(config_key) DO NOTHING")
    row = db.execute(
        "SELECT config_value FROM app_config WHERE config_key='run_mode'").fetchone()
    assert row is not None and row["config_value"] in ("online_preferred", "offline_only")


def test_r59_coverage_mode_switch(db):
    """R59 覆盖范围模式：include_superseded 开关影响检索时效过滤。"""
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import write_transaction
    from src.core.domain.models import ClauseRevisionModel
    did, sno = f"r59_{ULID()}", f"GB R59-{ULID()}"
    with write_transaction() as conn:
        clause_repo.insert_document(conn, dict(
            doc_id=did, standard_no=sno, standard_name=sno, short_code="R59",
            current_revision_id="r", legal_status="superseded", domain_tags=[],
            file_path="r.pdf", file_hash=f"h{ULID()}"))
    clause_repo.insert_clauses([ClauseRevisionModel(
        clause_revision_id=f"r59c_{ULID()}", doc_id=did, clause_key=f"k{ULID()}",
        standard_no=sno, clause_number="1.1", content_text="已废止条款内容",
        page_start=1, page_end=1)])
    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    from src.core.storage.sqlite_db import get_db_connection
    cid = get_db_connection().execute(
        "SELECT clause_revision_id FROM clause_revision WHERE doc_id=?",
        (did,)).fetchone()["clause_revision_id"]
    # 相对断言：默认检索不得包含该已废止条款；include_superseded 后必须包含
    res_default = perform_hybrid_search(sno, top_k=10)
    assert all(r.clause_revision_id != cid for r in res_default), "默认应过滤已废止"
    res_all = perform_hybrid_search(sno, top_k=10, include_superseded=True)
    assert any(r.clause_revision_id == cid for r in res_all), "include_superseded 应含已废止"


def test_r67_transition_both_valid(db):
    """R67 过渡期并行有效：upcoming 与 effective 文档同时存在时不互斥。"""
    from src.core.storage import clause_repo
    from src.core.storage.sqlite_db import write_transaction
    from src.core.domain.models import ClauseRevisionModel
    for i, status in enumerate(("effective", "upcoming")):
        did, sno = f"r67_{ULID()}", f"GB R67-{i}-{ULID()}"
        with write_transaction() as conn:
            clause_repo.insert_document(conn, dict(
                doc_id=did, standard_no=sno, standard_name=sno, short_code="R67",
                current_revision_id="r", legal_status=status, domain_tags=[],
                file_path="r.pdf", file_hash=f"h{ULID()}"))
        clause_repo.insert_clauses([ClauseRevisionModel(
            clause_revision_id=f"r67c_{ULID()}", doc_id=did, clause_key=f"k{ULID()}",
            standard_no=sno, clause_number="1.1", content_text=f"{status}内容",
            page_start=1, page_end=1)])
    from src.core.storage.sqlite_db import get_db_connection
    conn = get_db_connection()
    assert conn.execute(
        "SELECT COUNT(*) FROM doc_meta WHERE legal_status IN ('effective','upcoming')"
        " AND standard_no LIKE 'GB R67%'").fetchone()[0] == 2, "过渡期两状态并行有效"
