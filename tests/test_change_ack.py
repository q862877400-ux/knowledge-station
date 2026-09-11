"""巡检确认闭环测试（2026-08-26）：mark_ack 确认废止/被替代时同步写回 doc_meta。

历史缺陷：mark_ack 只标记 user_ack，doc_meta.legal_status 永不更新 →
已废止标准（如 AQ 3028-2008，2024-07-01 废止）继续被检索当现行引用。
"""
import json

import pytest

from src.core.update.change_repo import UPD_CHANGE_NOT_FOUND, UpdateError, mark_ack
from src.core.storage.sqlite_db import get_db_connection


def _mk_doc(conn, doc_id, legal_status="effective"):
    conn.execute(
        "INSERT INTO doc_meta (doc_id, standard_no, standard_name, short_code,"
        " current_revision_id, legal_status, file_path, file_hash, domain_tags)"
        " VALUES (?,?,?,?,?,?,?,?,?)",
        (doc_id, f"GB {doc_id}", "测试标准", f"GB{doc_id}", f"rev_{doc_id}",
         legal_status, f"C:/x/{doc_id}.pdf", "h" * 64, '["测试"]'))
    conn.commit()


def _mk_change(conn, change_id, doc_id, change_type, status):
    conn.execute(
        "INSERT OR IGNORE INTO update_check_batch (batch_id, trigger_type, status)"
        " VALUES ('batch_x', 'manual', 'done')")
    conn.execute(
        "INSERT INTO update_change_event (change_id, batch_id, doc_id, standard_no,"
        " change_type, current_legal_status, source_channel, evidence_url, user_ack)"
        " VALUES (?,?,?,?,?,?,?,?,0)",
        (change_id, "batch_x", doc_id, f"GB {doc_id}", change_type, status,
         "ndls", "https://x"))
    conn.commit()


def test_mark_ack_applies_withdrawn_to_doc_meta(db):
    """确认废止变更 → doc_meta.legal_status 同步为 withdrawn + 审计两条。"""
    _mk_doc(db, "D1")
    _mk_change(db, "chg_1", "D1", "withdrawn", "withdrawn")
    out = mark_ack("chg_1")
    assert out["applied"] == {"doc_id": "D1", "legal_status": "withdrawn"}
    row = db.execute("SELECT legal_status FROM doc_meta WHERE doc_id='D1'").fetchone()
    assert row["legal_status"] == "withdrawn"
    events = db.execute(
        "SELECT event_type FROM event_log WHERE target_id IN ('D1','chg_1')").fetchall()
    types = {e["event_type"] for e in events}
    assert "update/status_applied_to_doc" in types
    assert "update/change_ack" in types


def test_mark_ack_applies_superseded(db):
    _mk_doc(db, "D2")
    _mk_change(db, "chg_2", "D2", "superseded", "superseded")
    out = mark_ack("chg_2")
    assert out["applied"]["legal_status"] == "superseded"
    row = db.execute("SELECT legal_status FROM doc_meta WHERE doc_id='D2'").fetchone()
    assert row["legal_status"] == "superseded"


def test_mark_ack_not_applied_for_new_version(db):
    """new_version 变更只确认不落状态（引导导入新版而非改写现行状态）。"""
    _mk_doc(db, "D3")
    _mk_change(db, "chg_3", "D3", "new_version", "effective")
    out = mark_ack("chg_3")
    assert out["applied"] is None
    row = db.execute("SELECT legal_status FROM doc_meta WHERE doc_id='D3'").fetchone()
    assert row["legal_status"] == "effective"


def test_mark_ack_cancel_does_not_apply(db):
    """取消确认（ack=False）不落库。"""
    _mk_doc(db, "D4")
    _mk_change(db, "chg_4", "D4", "withdrawn", "withdrawn")
    out = mark_ack("chg_4", ack=False)
    assert out["applied"] is None
    row = db.execute("SELECT legal_status FROM doc_meta WHERE doc_id='D4'").fetchone()
    assert row["legal_status"] == "effective"


def test_mark_ack_missing_change_raises(db):
    with pytest.raises(UpdateError) as ei:
        mark_ack("no_such_change")
    assert ei.value.code == UPD_CHANGE_NOT_FOUND
