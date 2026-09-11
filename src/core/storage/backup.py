"""快照备份与回滚（Task 13.5 / R46·R51，v5 P1 数据保护）。

- create_snapshot(type)：sqlite 在线备份（VACUUM INTO）到 %APPDATA%/KnowledgeStation/backups/，
  记录 snapshot_meta（db_checksum/file_count/clause_count）；
- 滚动保留：自动快照保留最近 7 份，手动快照永不清理；
- restore_snapshot(id)：返回目标备份路径（替换执行由 supervisor/上层做：停写→替换 db→重连）。
"""
from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

from ulid import ULID

from src.core.config import get_settings
from src.core.storage.sqlite_db import get_db_connection, write_transaction

AUTO_KEEP = 7


def _backups_dir() -> Path:
    d = get_settings().data_dir / "backups"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _checksum(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def create_snapshot(snapshot_type: str = "auto") -> dict:
    conn = get_db_connection()
    snap_id = f"snap_{ULID()}"
    target = _backups_dir() / f"{snap_id}.db"
    conn.execute("VACUUM INTO ?", (str(target),))
    checksum = _checksum(target)
    file_count = conn.execute("SELECT COUNT(*) FROM doc_meta").fetchone()[0]
    clause_count = conn.execute("SELECT COUNT(*) FROM clause_revision").fetchone()[0]
    with write_transaction() as txn:
        txn.execute(
            "INSERT INTO snapshot_meta (snapshot_id, snapshot_type, db_checksum,"
            " file_count, clause_count) VALUES (?,?,?,?,?)",
            (snap_id, snapshot_type, checksum, file_count, clause_count))
    if snapshot_type == "auto":
        _rollout_auto()
    return {"snapshot_id": snap_id, "type": snapshot_type,
            "db_checksum": checksum, "file_count": file_count,
            "clause_count": clause_count, "path": str(target)}


def _rollout_auto() -> None:
    """滚动淘汰：自动快照保留最近 AUTO_KEEP 份。"""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT snapshot_id FROM snapshot_meta WHERE snapshot_type='auto'"
        " ORDER BY created_at DESC").fetchall()
    for r in rows[AUTO_KEEP:]:
        conn.execute("DELETE FROM snapshot_meta WHERE snapshot_id=?", (r["snapshot_id"],))
        ( _backups_dir() / f"{r['snapshot_id']}.db").unlink(missing_ok=True)
    conn.commit()


def list_snapshots(limit: int = 20) -> list[dict]:
    conn = get_db_connection()
    return [dict(r) for r in conn.execute(
        "SELECT snapshot_id, snapshot_type, db_checksum, file_count, clause_count, created_at"
        " FROM snapshot_meta ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()]


def restore_snapshot(snapshot_id: str) -> dict:
    """返回备份文件路径（替换 db 由上层执行：停写→替换→重连，走 supervisor）。"""
    from src.core.exceptions import KnowledgeStationError
    conn = get_db_connection()
    row = conn.execute(
        "SELECT snapshot_type, db_checksum FROM snapshot_meta WHERE snapshot_id=?",
        (snapshot_id,)).fetchone()
    if row is None:
        raise KnowledgeStationError(f"快照不存在: {snapshot_id}", code="snapshot_not_found")
    path = _backups_dir() / f"{snapshot_id}.db"
    if not path.exists():
        raise KnowledgeStationError(f"快照文件缺失: {path}", code="snapshot_file_missing")
    # 校验和验证（红线 v2 #2：快照完整性）
    actual = _checksum(path)
    if actual != row["db_checksum"]:
        raise KnowledgeStationError("快照校验和不匹配（文件损坏），拒绝回滚",
                                    code="snapshot_checksum_mismatch")
    return {"snapshot_id": snapshot_id, "backup_path": str(path),
            "restore_note": "替换执行由 supervisor/上层完成：停写 → 替换 knowledge.db → 重连"}
