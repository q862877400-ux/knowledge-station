"""Task 13.5 快照备份测试：创建/校验和/滚动淘汰/恢复校验。"""
from pathlib import Path

import pytest


def test_snapshot_create_and_restore(db, tmp_path):
    from src.core.storage import backup, clause_repo
    from src.core.storage.sqlite_db import write_transaction
    # 种一点数据
    with write_transaction() as conn:
        clause_repo.insert_document(conn, dict(
            doc_id="snap1", standard_no="GB SN-2022", standard_name="s", short_code="s",
            current_revision_id="r", domain_tags=[], file_path="s.pdf", file_hash="hs"))
        conn.execute(
            "INSERT INTO clause_revision (clause_revision_id, doc_revision_id, doc_id,"
            " clause_key, clause_number, content_text, page_start, page_end, content_hash)"
            " VALUES ('snapc1','r','snap1','k','1.1','内容',1,1,'h')")
    out = backup.create_snapshot("manual")
    assert out["file_count"] >= 1 and out["clause_count"] >= 1  # 共享库可能有其他测试数据
    assert Path(out["path"]).exists()
    r = backup.restore_snapshot(out["snapshot_id"])
    assert r["backup_path"] == out["path"]


def test_snapshot_rollout_auto_keep_7(db):
    from src.core.storage import backup
    ids = []
    for _ in range(10):
        ids.append(backup.create_snapshot("auto")["snapshot_id"])
    snaps = backup.list_snapshots(limit=50)
    auto = [s for s in snaps if s["snapshot_type"] == "auto"]
    assert len(auto) <= 7, "自动快照滚动保留最多 7 份"
    # 手动快照不受淘汰影响
    m = backup.create_snapshot("manual")["snapshot_id"]
    for _ in range(5):
        backup.create_snapshot("auto")
    assert any(s["snapshot_id"] == m for s in backup.list_snapshots(50)), "手动快照永不被清理"


def test_snapshot_checksum_mismatch(db):
    from src.core.storage import backup
    out = backup.create_snapshot("manual")
    # 篡改备份文件 → 校验和拒绝
    from pathlib import Path
    p = Path(out["path"])
    p.write_bytes(b"corrupted" * 10)
    from src.core.exceptions import KnowledgeStationError
    with pytest.raises(KnowledgeStationError):
        backup.restore_snapshot(out["snapshot_id"])


def test_snapshot_api(client, db):
    from src.core.storage import backup
    backup.create_snapshot("manual")
    c, token = client
    headers = {"Authorization": f"Bearer {token}"}
    assert c.get("/api/v1/snapshots", headers=headers).status_code == 200
    r = c.post("/api/v1/snapshots", headers=headers, json={"type": "manual"})
    assert r.status_code == 200
    sid = r.json()["data"]["snapshot_id"]
    assert c.post(f"/api/v1/snapshots/{sid}/restore", headers=headers).status_code == 200
    assert c.post("/api/v1/snapshots/snap_不存在/restore", headers=headers).status_code == 404
    assert c.get("/api/v1/snapshots").status_code == 401
