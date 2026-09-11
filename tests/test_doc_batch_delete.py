# -*- coding: utf-8 -*-
"""批量删除文档测试（2026-08-31，随 POST /api/v1/documents/batch-delete 端点新增）。

覆盖：显式级联 9 张表（clause 级 span/patch/obligation/edge/fts/vec/revision +
doc 级 geometry/change_event/watch_list）+ doc_meta；missing 上报；confirm 防呆；
参数校验；event_log 审计。测试 id 全部 bd_ 前缀（会话级共享库防跨文件冲突）。
"""
from __future__ import annotations

import json
from array import array

H = lambda token: {"Authorization": f"Bearer {token}"}  # noqa: E731


def _seed_doc(db, doc_id: str, clauses: list[str]) -> None:
    """最小可用文档：doc_meta + geometry + watch_list + 条款（span/patch/obligation/fts/vec）。"""
    db.execute(
        "INSERT INTO doc_meta (doc_id, standard_no, standard_name, short_code,"
        " current_revision_id, domain_tags, file_path, file_hash)"
        " VALUES (?, ?, ?, ?, ?, '[]', 'x.pdf', ?)",
        (doc_id, f"BD/STD-{doc_id[-1]}", f"测试文档{doc_id}", doc_id, f"bd_rev_{doc_id}",
         f"hash_{doc_id}"))
    db.execute(
        "INSERT INTO doc_page_geometry (doc_id, page_number, width, height) VALUES (?, 1, 595, 842)",
        (doc_id,))
    db.execute("INSERT INTO watch_list (watch_id, doc_id) VALUES (?, ?)",
               (f"bd_watch_{doc_id}", doc_id))
    db.execute(
        "INSERT INTO user_doc_bookmark (doc_bookmark_id, doc_id) VALUES (?, ?)",
        (f"bd_dmb_{doc_id}", doc_id))
    for i, crid in enumerate(clauses, 1):
        db.execute(
            "INSERT INTO clause_revision (clause_revision_id, doc_revision_id, doc_id,"
            " clause_key, clause_number, content_text, page_start, page_end)"
            " VALUES (?, ?, ?, ?, ?, '测试条款内容', 1, 1)",
            (crid, f"bd_rev_{doc_id}", doc_id, f"{doc_id}#{i}", f"{i}.0"))
        db.execute(
            "INSERT INTO source_span (span_id, clause_revision_id, page_number, bbox_json)"
            " VALUES (?, ?, 1, '[0,0,1,1]')", (f"bd_span_{crid}", crid))
        db.execute(
            "INSERT INTO clause_patch (patch_id, clause_revision_id, field_name,"
            " patched_value, patch_reason) VALUES (?, ?, 'content_text', 'x', '测试')",
            (f"bd_patch_{crid}", crid))
        db.execute(
            "INSERT INTO legal_obligation (obligation_id, clause_revision_id, obligation_text)"
            " VALUES (?, ?, '应做某事')", (f"bd_obl_{crid}", crid))
        db.execute(
            "INSERT INTO clause_fts (clause_revision_id, clause_number, standard_no,"
            " title, content_segmented) VALUES (?, ?, 'bd_std', 't', 'ce shi')",
            (crid, f"{i}.0"))
        db.execute("INSERT INTO clause_vec (clause_revision_id, embedding) VALUES (?, ?)",
                   (crid, array("f", [0.01] * 512).tobytes()))
    db.commit()


def _seed_edge(db, src: str, dst: str) -> None:
    db.execute(
        "INSERT INTO evidence_edge (edge_id, source_clause_id, target_clause_id, edge_type)"
        " VALUES (?, ?, ?, 'ref')", (f"bd_edge_{src}_{dst}", src, dst))
    db.commit()


def _seed_change_event(db, doc_id: str) -> None:
    db.execute(
        "INSERT OR IGNORE INTO update_check_batch (batch_id, trigger_type, status)"
        " VALUES ('bd_batch', 'manual', 'done')")
    db.execute(
        "INSERT INTO update_change_event (change_id, batch_id, doc_id, standard_no,"
        " change_type, source_channel) VALUES (?, 'bd_batch', ?, 'bd_std', 'no_change', 'manual')",
        (f"bd_chg_{doc_id}", doc_id))
    db.commit()


def test_batch_delete_cascades_all_tables(client):
    c, token = client
    from src.core.storage.sqlite_db import get_db_connection
    db = get_db_connection()
    _seed_doc(db, "bd_doc_a", ["bd_cl_a1", "bd_cl_a2"])
    _seed_doc(db, "bd_doc_b", ["bd_cl_b1"])
    _seed_doc(db, "bd_doc_c", ["bd_cl_c1"])
    _seed_edge(db, "bd_cl_a1", "bd_cl_c1")   # 跨文档边：删 A 时边消失，C 条款保留
    _seed_change_event(db, "bd_doc_a")
    _seed_change_event(db, "bd_doc_b")

    r = c.post("/api/v1/documents/batch-delete", headers=H(token),
               json={"doc_ids": ["bd_doc_a", "bd_doc_b", "bd_doc_gone"], "confirm": True})
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["deleted_docs"] == 2
    assert data["deleted_clauses"] == 3
    assert data["missing"] == ["bd_doc_gone"]

    def one(sql, *params):
        return db.execute(sql, params).fetchone()[0]

    # doc 级
    assert one("SELECT COUNT(*) FROM doc_meta WHERE doc_id IN ('bd_doc_a','bd_doc_b')") == 0
    assert one("SELECT COUNT(*) FROM doc_page_geometry WHERE doc_id IN ('bd_doc_a','bd_doc_b')") == 0
    assert one("SELECT COUNT(*) FROM update_change_event WHERE doc_id IN ('bd_doc_a','bd_doc_b')") == 0
    assert one("SELECT COUNT(*) FROM watch_list WHERE doc_id IN ('bd_doc_a','bd_doc_b')") == 0
    assert one("SELECT COUNT(*) FROM user_doc_bookmark WHERE doc_id IN ('bd_doc_a','bd_doc_b')") == 0
    # clause 级（含 FTS/vec 虚表——无 FK 必须显式删）
    kept = ("bd_cl_a1","bd_cl_a2","bd_cl_b1")
    ph = ",".join("?" * len(kept))
    for table in ("clause_revision", "source_span", "clause_patch",
                  "legal_obligation", "clause_fts", "clause_vec"):
        assert one(f"SELECT COUNT(*) FROM {table} WHERE clause_revision_id IN ({ph})", *kept) == 0, table
    assert one(f"SELECT COUNT(*) FROM evidence_edge WHERE source_clause_id IN ({ph})"
               f" OR target_clause_id IN ({ph})", *kept, *kept) == 0
    # 未删文档 C 完好：doc + 条款 + fts + vec 都在
    assert one("SELECT COUNT(*) FROM doc_meta WHERE doc_id='bd_doc_c'") == 1
    assert one("SELECT COUNT(*) FROM clause_revision WHERE doc_id='bd_doc_c'") == 1
    assert one("SELECT COUNT(*) FROM clause_fts WHERE clause_revision_id='bd_cl_c1'") == 1
    assert one("SELECT COUNT(*) FROM clause_vec WHERE clause_revision_id='bd_cl_c1'") == 1
    # 审计：event_log 有 document.batch_delete 事件，metadata 带计数
    ev = db.execute("SELECT event_type, metadata FROM event_log WHERE event_type='document.batch_delete'"
                    " ORDER BY created_at DESC LIMIT 1").fetchone()
    assert ev is not None
    meta = json.loads(ev[1])
    assert meta["deleted_docs"] == 2 and meta["deleted_clauses"] == 3


def test_batch_delete_requires_confirm(client):
    c, token = client
    r1 = c.post("/api/v1/documents/batch-delete", headers=H(token),
                json={"doc_ids": ["bd_doc_x"]})
    assert r1.status_code == 422
    assert r1.json()["error"] == "DOC-3002"
    r2 = c.post("/api/v1/documents/batch-delete", headers=H(token),
                json={"doc_ids": ["bd_doc_x"], "confirm": False})
    assert r2.status_code == 422


def test_batch_delete_validates_input(client):
    c, token = client
    assert c.post("/api/v1/documents/batch-delete", headers=H(token),
                  json={"doc_ids": [], "confirm": True}).status_code == 422
    assert c.post("/api/v1/documents/batch-delete", headers=H(token),
                  json={"doc_ids": "bd_doc_x", "confirm": True}).status_code == 422
    assert c.post("/api/v1/documents/batch-delete", headers=H(token),
                  json={"doc_ids": [f"bd_o{i}" for i in range(501)], "confirm": True}
                  ).status_code == 422


def test_batch_delete_missing_only_leaves_db_untouched(client):
    c, token = client
    from src.core.storage.sqlite_db import get_db_connection
    db = get_db_connection()
    n_before = db.execute("SELECT COUNT(*) FROM doc_meta").fetchone()[0]
    r = c.post("/api/v1/documents/batch-delete", headers=H(token),
               json={"doc_ids": ["bd_nope1", "bd_nope2"], "confirm": True})
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["deleted_docs"] == 0
    assert data["missing"] == ["bd_nope1", "bd_nope2"]
    n_after = db.execute("SELECT COUNT(*) FROM doc_meta").fetchone()[0]
    assert n_after == n_before
