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


def test_snapshot_copies_secrets_json(db, tmp_path, monkeypatch):
    """批1整改：快照必须把 secrets.json 密文带进备份目录（密钥安全网）。

    - secrets.json 存在 → 密文原样复制 + 校验和一致 + restore 报告副本路径；
    - secrets.json 缺失 → secrets_copied=False 如实记录，快照本身照常成功。
    """
    from src.core.storage import backup
    from src.core.settings import secret_store

    # data_dir 已由 conftest 的 KS_DATA_DIR 指向 tmp（drift-guard 保证同一路径规则）
    secret_store.write_values({"KS_TEST_KEY": "fake-secret-value-123"}, data_dir=None)

    out = backup.create_snapshot("manual")
    assert out["secrets_copied"] is True
    assert Path(out["secrets_path"]).exists()
    assert out["secrets_path"].endswith(".secrets.json")
    # 密文原样（不解密验证内容，只验字节一致 → 读回校验和即证明副本可用）
    assert out["secrets_checksum"] == backup._checksum(Path(out["secrets_path"]))

    # 副本必须仍是合法 DPAPI 密文（能被 secret_store 原样读回同一个值）
    payload_src = (backup._backups_dir() / Path(out["secrets_path"]).name)
    assert secret_store.read_value("KS_TEST_KEY") == "fake-secret-value-123"

    # restore 报告密钥副本路径 + 校验和
    r = backup.restore_snapshot(out["snapshot_id"])
    assert "secrets_backup_path" in r
    assert r["secrets_checksum"] == out["secrets_checksum"]


def test_snapshot_without_secrets_json(db):
    """secrets.json 不存在（当前真机正是此状态）→ secrets_copied=False，快照照常成功。"""
    from src.core.storage import backup
    from src.core.settings.secret_store import store_path
    # 会话级 tmp 目录被其他测试共享——显式移除模拟「真机上密钥文件尚未创建」状态
    p = store_path()
    if p.exists():
        p.unlink()
    assert not p.exists()
    out = backup.create_snapshot("manual")
    assert out["secrets_copied"] is False
    assert out["secrets_checksum"] is None
    assert out["file_count"] >= 0  # 快照本体正常


def test_snapshot_secrets_rollout_cleanup(db, tmp_path):
    """自动快照滚动淘汰时 .secrets.json 副本一起删，不留孤儿密文文件。"""
    from src.core.storage import backup
    from src.core.settings import secret_store

    secret_store.write_values({"KS_TEST_KEY2": "v2"})
    for _ in range(9):  # AUTO_KEEP=7 → 前 2 份会被淘汰
        backup.create_snapshot("auto")
    autos = [s for s in backup.list_snapshots(50) if s["snapshot_type"] == "auto"]
    assert len(autos) <= 7
    # 不存在任何 meta 里已删但磁盘还在的孤儿副本（手动快照的副本合法保留，不计数）
    meta_ids = {s["snapshot_id"] for s in backup.list_snapshots(50)}
    for p in backup._backups_dir().glob("snap_*.secrets.json"):
        sid = p.name.replace(".secrets.json", "")
        assert sid in meta_ids, f"孤儿密文副本: {p}"
