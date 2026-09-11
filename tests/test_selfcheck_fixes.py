"""第一阶段自检修复的回归测试（phase1-selfcheck.md 对应）。"""
from pathlib import Path


def test_query_modality_compound_guard():
    from src.core.retrieval.hybrid_engine import extract_modality_from_query
    assert extract_modality_from_query("应该怎么做") is None, "'应该'不应误触发模态通道"
    assert extract_modality_from_query("可能会出问题吗") is None, "'可能会'不应误触发"
    assert extract_modality_from_query("哪些情况严禁使用") == "严禁"
    assert extract_modality_from_query("这个可以做吗") == "可以"


def test_write_queue_stale_processing_recovered(db):
    from src.core.storage import write_queue as wq
    db.execute(
        "INSERT INTO write_queue (operation_type, payload, status)"
        " VALUES ('ingest','{}','processing')")
    db.commit()
    worker = wq.WriteWorker(lambda op, p: {"ok": True})
    worker.start()  # 启动时应把 processing 重置为 pending 并消费
    try:
        assert wq.wait_until_drained(timeout=10)
    finally:
        worker.stop()
    assert db.execute(
        "SELECT COUNT(*) FROM write_queue WHERE status='done'").fetchone()[0] >= 1


def test_same_standard_different_hash_blocked(db, tmp_path):
    """R43: 同标准号不同 hash 不崩溃，返回 standard_exists 供上层确认。"""
    from src.core.storage import clause_repo
    from src.core.ingestion import smoke_ingest
    import hashlib

    pdf = tmp_path / "a.pdf"
    pdf.write_bytes(b"%PDF-fake-1")
    clause_repo.insert_document(db, dict(
        doc_id="ex1", standard_no="GB TEST-2022", standard_name="t", short_code="t",
        current_revision_id="r", domain_tags=[], file_path=str(pdf),
        file_hash=hashlib.sha256(b"other").hexdigest()))

    out = smoke_ingest.ingest_pdf(pdf, "GB TEST-2022", "t")
    assert out["status"] == "standard_exists"
    assert out["existing_doc_id"] == "ex1"


def test_ingest_missing_file():
    from src.core.ingestion import smoke_ingest
    out = smoke_ingest.ingest_pdf(Path("Z:/不存在/xx.pdf"), "GB X", "x")
    assert out["status"] == "error"
    assert "不存在" in out["message"]
