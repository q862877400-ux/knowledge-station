"""T02 存储层测试：PRAGMA、外键级联、FTS5/vec 可用、单写者队列串行化。"""
import json

import pytest


def test_pragmas(db):
    assert db.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    assert db.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    # busy_timeout=60000：update 模块长事务（VACUUM INTO/批量巡检）需要更长等待，
    # sqlite_db.py 为权威事实源——断言跟代码走（2026-08-31 修正漂移）
    assert db.execute("PRAGMA busy_timeout").fetchone()[0] == 60000


def test_foreign_key_cascade(db):
    db.execute(
        "INSERT INTO doc_meta (doc_id, standard_no, standard_name, short_code,"
        " current_revision_id, domain_tags, file_path, file_hash)"
        " VALUES ('st_d1','T1','测试标准','T1','r1','[]','a.pdf','h1')")
    db.execute(
        "INSERT INTO clause_revision (clause_revision_id, doc_revision_id, doc_id,"
        " clause_key, clause_number, content_text, page_start, page_end)"
        " VALUES ('st_c1','r1','st_d1','k1','1.1','内容',1,1)")
    db.execute(
        "INSERT INTO source_span (span_id, clause_revision_id, page_number, bbox_json)"
        " VALUES ('st_s1','st_c1',1,'[1,2,3,4]')")
    db.commit()
    db.execute("DELETE FROM doc_meta WHERE doc_id='st_d1'")
    db.commit()
    left = db.execute(
        "SELECT COUNT(*) FROM clause_revision WHERE clause_revision_id='st_c1'").fetchone()[0]
    assert left == 0, "级联删除未生效"
    assert db.execute(
        "SELECT COUNT(*) FROM source_span WHERE span_id='st_s1'").fetchone()[0] == 0


def test_fts5_and_vec_tables(db):
    db.execute(
        "INSERT INTO clause_fts (clause_revision_id, clause_number, standard_no, title,"
        " content_segmented, modality, subject, behavior_scope_segmented)"
        " VALUES ('st_c1','5.2.3','GB','独特标记词','独特标记词 防火','不应','','')")
    db.commit()
    rows = db.execute(
        "SELECT clause_revision_id FROM clause_fts WHERE clause_fts MATCH '独特标记词'").fetchall()
    assert [r[0] for r in rows] == ["st_c1"]

    from src.core.storage.sqlite_db import load_vec_extension
    assert load_vec_extension(db), "sqlite-vec 扩展加载失败"
    # vec0 虚拟表写入（json 序列化向量）
    vec = json.dumps([0.1] * 512)
    db.execute("INSERT INTO clause_vec (clause_revision_id, embedding) VALUES ('st_c1', ?)", (vec,))
    db.commit()
    rows = db.execute(
        "SELECT clause_revision_id FROM clause_vec WHERE embedding MATCH ? AND k = 1",
        (vec,)).fetchall()
    assert [r[0] for r in rows] == ["st_c1"]


def test_write_queue_serializes(db):
    import threading
    from src.core.storage import write_queue as wq

    from ulid import ULID
    run = str(ULID()).lower()[:8]
    db.commit()
    db.execute(
        "INSERT INTO doc_meta (doc_id, standard_no, standard_name, short_code,"
        " current_revision_id, domain_tags, file_path, file_hash)"
        " VALUES ('st_q1','T1','测试','T1','r1','[]','a.pdf','h1')")
    db.commit()

    from src.core.storage.sqlite_db import write_transaction

    def handler(op_type, payload):
        with write_transaction() as conn:
            conn.execute(
                "INSERT INTO clause_revision (clause_revision_id, doc_revision_id, doc_id,"
                " clause_key, clause_number, content_text, page_start, page_end)"
                " VALUES (?,?,?,?,?,?,1,1)",
                (payload["cid"], 'r1', 'st_q1', payload["cid"], payload["no"], payload["text"]))
        return {"cid": payload["cid"]}

    worker = wq.WriteWorker(handler)
    worker.start()
    try:
        for i in range(20):
            wq.enqueue("ingest", {"cid": f"wq_{run}_{i:02d}", "no": f"1.{i}", "text": f"条款{i}"})
        assert wq.wait_until_drained(timeout=15), "队列未在期限内排空"
    finally:
        worker.stop()
    assert worker.max_concurrent_writes == 1, "写操作出现并发，串行化失效"
    assert db.execute(
        "SELECT COUNT(*) FROM clause_revision WHERE clause_revision_id LIKE 'wq_%'").fetchone()[0] == 20
    assert db.execute(
        "SELECT COUNT(*) FROM write_queue WHERE status='done'").fetchone()[0] >= 20
