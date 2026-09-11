"""Task 11.2 监听文件夹测试：扫描入队 / 防重 / 队列状态。"""
from pathlib import Path


def test_scan_enqueue_and_dedupe(db, tmp_path):
    from src.core.ingestion import watcher
    from src.core.storage.write_queue import wait_until_drained

    d = tmp_path / "watch"
    d.mkdir()
    (d / "a.pdf").write_bytes(b"%PDF-1")
    (d / "b.docx").write_bytes(b"PK\x03\x04")
    (d / "c.txt").write_bytes(b"ignore me")

    enqueued = watcher.scan_and_enqueue(d)
    assert len(enqueued) == 2  # 只收 pdf/docx
    assert watcher.scan_and_enqueue(d) == [], "重复扫描不重复入队"

    # 已入库文件不再入队
    conn = db
    conn.execute(
        "INSERT INTO doc_meta (doc_id, standard_no, standard_name, short_code,"
        " current_revision_id, domain_tags, file_path, file_hash)"
        " VALUES ('w1','GB W','w','w','r','[]','x.pdf','" + "h" * 64 + "')")
    conn.commit()
    (d / "a.pdf").write_bytes(b"%PDF-2")  # 换内容新 hash
    (d / "d.pdf").write_bytes(b"%PDF-3")
    e2 = watcher.scan_and_enqueue(d)
    assert len(e2) == 1 and e2[0]["path"].endswith("d.pdf")


def test_ingest_queue_status(db):
    from src.core.ingestion import watcher
    from src.core.storage import write_queue as wq
    wq.enqueue("ingest_doc", {"path": "C:/x.pdf"})
    status = watcher.ingest_queue_status()
    assert status["counts"]["queued"] >= 1
    assert any(it["path"] == "C:/x.pdf" for it in status["items"])
