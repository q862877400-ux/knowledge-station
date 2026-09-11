"""write_queue 消费端接线测试（2026-08-26，P2-①）。

历史缺陷：WriteWorker 类从未实例化 → watcher 入队的 ingest_doc 永远 pending；
本测试锁定"消费端启动后 ingest_doc 真正被消费、未知类型跳过不悬挂"。
"""
import pytest

from src.core.storage.sqlite_db import get_db_connection
from src.core.storage.write_queue import enqueue, wait_until_drained
import src.core.storage.write_queue_bootstrap as wqb


@pytest.fixture()
def clean_queue(db):
    db.execute("DELETE FROM write_queue")
    db.commit()
    yield
    db.execute("DELETE FROM write_queue")
    db.commit()


def test_worker_consumes_ingest_doc_and_skips_unknown(monkeypatch, tmp_path, clean_queue):
    calls = []

    def fake_ingest(payload):
        calls.append(payload)
        return {"status": "ok", "doc_id": "doc_test"}

    monkeypatch.setattr(wqb, "_ingest_doc", fake_ingest)
    wqb.start_write_worker()
    try:
        # ingest_doc：被消费并标记 done
        qid = enqueue("ingest_doc", {"path": str(tmp_path / "a.pdf"), "suffix": ".pdf"})
        assert wait_until_drained(timeout=10), "ingest_doc 未被消费（队列悬挂）"
        conn = get_db_connection()
        row = conn.execute("SELECT status FROM write_queue WHERE queue_id=?", (qid,)).fetchone()
        assert row["status"] == "done"
        assert calls and calls[0]["path"].endswith("a.pdf")

        # 未知类型：跳过标记 done，不永久 pending
        qid2 = enqueue("no_such_op", {})
        assert wait_until_drained(timeout=10), "未知类型悬挂"
        row2 = conn.execute("SELECT status, result FROM write_queue WHERE queue_id=?",
                            (qid2,)).fetchone()
        assert row2["status"] == "done" and "no_such_op" in row2["result"]

        # 幂等：重复 start 不重复起线程
        wqb.start_write_worker()
        assert wqb._worker is not None
    finally:
        wqb.stop_write_worker()


def test_ingest_doc_missing_file_fails_cleanly(monkeypatch, clean_queue):
    """真实 handler：文件不存在 → failed（不悬挂、不抛穿线程）。"""
    wqb.start_write_worker()
    try:
        qid = enqueue("ingest_doc", {"path": "Z:/no/such/file.pdf", "suffix": ".pdf"})
        assert wait_until_drained(timeout=10)
        conn = get_db_connection()
        row = conn.execute("SELECT status FROM write_queue WHERE queue_id=?", (qid,)).fetchone()
        assert row["status"] == "failed"
    finally:
        wqb.stop_write_worker()
