"""快照备份与回滚（Task 13.5 / R46·R51，v5 P1 数据保护）。

- create_snapshot(type)：sqlite 在线备份（VACUUM INTO）到 %APPDATA%/KnowledgeStation/backups/，
  记录 snapshot_meta（db_checksum/file_count/clause_count）；
- **密钥安全网（2026-09-12 整改批 1）**：快照同时把 `secrets.json` 密文原样复制为
  `<backups>/snap_<id>.secrets.json` 并记 SHA-256（**不解密、不打印值**——红线
  「Key 读取禁明文」对备份同样适用）。DPAPI 密文只有同一 Windows 用户能解开，
  备份落在同一 data_dir 下不扩大暴露面。文件缺失时 `secrets_copied=False` 如实记录
  （快照本身照常成功——密钥文件不存在不是数据库快照的失败理由）；
- 滚动保留：自动快照保留最近 7 份，手动快照永不清理（.secrets.json 副本随主文件一起淘汰）；
- restore_snapshot(id)：返回目标备份路径（替换执行由 supervisor/上层做：停写→替换 db→重连）。
"""
from __future__ import annotations

import hashlib
import os
import shutil
from datetime import datetime
from pathlib import Path

from ulid import ULID

from src.core.config import get_settings
from src.core.storage.sqlite_db import get_db_connection, write_transaction

AUTO_KEEP = 7


def _backups_dir() -> Path:
    """备份目录。

    整改批 7（问题清单 #8）：默认 `<data_dir>/backups`；环境变量 `KS_BACKUP_DIR`
    可重定向到**数据目录之外的盘/卷**（例如另一块物理盘），这样数据盘损坏时
    备份仍然幸存——这是"快照不可变"承诺的灾难面补全。环境变量只作显式覆盖
    （CI/运维/临时调试），引擎绝不写 env，与凭据覆盖链同一纪律。
    """
    override = os.environ.get("KS_BACKUP_DIR", "").strip()
    d = Path(override) if override else get_settings().data_dir / "backups"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _checksum(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _secrets_snapshot_path(snap_id: str) -> Path:
    return _backups_dir() / f"{snap_id}.secrets.json"


def _snapshot_secrets(snap_id: str) -> dict:
    """把 secrets.json 密文原样复制进备份目录；缺失时如实记录 False。

    只碰密文（shutil.copyfile），不经过 secret_store 的解密路径——备份行为本身
    不需要读值，也不该读。返回 {"secrets_copied", "secrets_checksum", "secrets_path"}。
    """
    from src.core.settings.secret_store import store_path
    out: dict = {"secrets_copied": False, "secrets_checksum": None, "secrets_path": None}
    src = store_path()
    if not src.exists():
        return out
    dst = _secrets_snapshot_path(snap_id)
    shutil.copyfile(src, dst)
    out["secrets_copied"] = True
    out["secrets_checksum"] = _checksum(dst)
    out["secrets_path"] = str(dst)
    return out


def create_snapshot(snapshot_type: str = "auto") -> dict:
    conn = get_db_connection()
    snap_id = f"snap_{ULID()}"
    target = _backups_dir() / f"{snap_id}.db"
    conn.execute("VACUUM INTO ?", (str(target),))
    checksum = _checksum(target)
    file_count = conn.execute("SELECT COUNT(*) FROM doc_meta").fetchone()[0]
    clause_count = conn.execute("SELECT COUNT(*) FROM clause_revision").fetchone()[0]
    secrets = _snapshot_secrets(snap_id)
    with write_transaction() as txn:
        txn.execute(
            "INSERT INTO snapshot_meta (snapshot_id, snapshot_type, db_checksum,"
            " file_count, clause_count) VALUES (?,?,?,?,?)",
            (snap_id, snapshot_type, checksum, file_count, clause_count))
    if snapshot_type == "auto":
        _rollout_auto()
    out = {"snapshot_id": snap_id, "type": snapshot_type,
           "db_checksum": checksum, "file_count": file_count,
           "clause_count": clause_count, "path": str(target)}
    out.update(secrets)
    return out


def _rollout_auto() -> None:
    """滚动淘汰：自动快照保留最近 AUTO_KEEP 份。"""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT snapshot_id FROM snapshot_meta WHERE snapshot_type='auto'"
        " ORDER BY created_at DESC").fetchall()
    for r in rows[AUTO_KEEP:]:
        conn.execute("DELETE FROM snapshot_meta WHERE snapshot_id=?", (r["snapshot_id"],))
        (_backups_dir() / f"{r['snapshot_id']}.db").unlink(missing_ok=True)
        # 密钥副本随主快照一起淘汰（不留孤儿密文文件）
        _secrets_snapshot_path(r["snapshot_id"]).unlink(missing_ok=True)
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
    out = {"snapshot_id": snapshot_id, "backup_path": str(path),
           "restore_note": "替换执行由 supervisor/上层完成：停写 → 替换 knowledge.db → 重连"}
    # 密钥副本核对：存在则校验完整性并报告路径（还原动作由上层/用户执行——密钥文件
    # 的替换必须停引擎后手工做，绝不能在引擎进程内热替换自己正在读的 secrets.json）
    sec_path = _secrets_snapshot_path(snapshot_id)
    if sec_path.exists():
        out["secrets_backup_path"] = str(sec_path)
        out["secrets_checksum"] = _checksum(sec_path)
    return out
