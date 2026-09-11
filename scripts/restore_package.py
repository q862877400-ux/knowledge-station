# -*- coding: utf-8 -*-
"""数据包离线恢复 CLI（2026-08-26，P2-②：data_package.py TODO(supervisor) 接线）。

语义：**引擎停止时**执行整体替换——校验包（manifest 格式 / db 文件 / SHA-256 校验和 /
幂等台账）→ 备份当前库 → 用包内 knowledge.db 覆盖活动库 → 完整性验证。

用法：
  python scripts/restore_package.py <包目录或 manifest.json>          # dry-run
  python scripts/restore_package.py <包目录或 manifest.json> --apply  # 执行替换

设计取舍：不在引擎进程内做"停写→换库→重连"（连接/线程风险高），改为离线脚本，
与 backup.restore 的"校验和拒绝 + 替换由上层执行"约定一致。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.config import get_settings  # noqa: E402

PACKAGE_FORMAT = "knowledge-station-package-v1"
DB_NAME = "knowledge.db"
REGISTRY_KEY = "data_package.import_registry"


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _registry(conn: sqlite3.Connection) -> list[dict]:
    row = conn.execute("SELECT config_value FROM app_config WHERE config_key=?",
                       (REGISTRY_KEY,)).fetchone()
    if not row:
        return []
    try:
        return json.loads(row[0])
    except (ValueError, TypeError):
        return []


def validate(pkg_dir: Path) -> dict:
    """校验包：返回 {db_path, checksum, manifest}；失败 raise ValueError。"""
    mpath = pkg_dir / "manifest.json"
    if not mpath.exists():
        raise ValueError(f"数据包缺少 manifest.json: {pkg_dir}")
    manifest = json.loads(mpath.read_text(encoding="utf-8"))
    if manifest.get("format") != PACKAGE_FORMAT:
        raise ValueError(f"非本系统数据包格式: {manifest.get('format')!r}")
    db_path = pkg_dir / str(manifest.get("db_file") or DB_NAME)
    if not db_path.exists():
        raise ValueError(f"数据包缺少库快照文件: {db_path}")
    actual = _sha256(db_path)
    if actual != manifest.get("db_checksum"):
        raise ValueError(f"数据包校验和不匹配（损坏或被篡改），拒绝恢复: "
                         f"{actual[:16]}… != {str(manifest.get('db_checksum'))[:16]}…")
    return {"db_path": db_path, "checksum": actual, "manifest": manifest}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="数据包离线恢复（引擎停止时执行）")
    ap.add_argument("src", help="包目录或其中 manifest.json 路径")
    ap.add_argument("--apply", action="store_true", help="执行替换（默认 dry-run）")
    args = ap.parse_args(argv)

    p = Path(args.src)
    pkg = p if p.is_dir() else p.parent
    info = validate(pkg)
    db_path = info["db_path"]
    checksum = info["checksum"]
    manifest = info["manifest"]

    target = Path(get_settings().db_path)
    if not target.exists():
        raise SystemExit(f"活动库不存在: {target}（确认 KS_DATA_DIR 后重试）")

    conn = sqlite3.connect(str(target))
    try:
        reg = _registry(conn)
    finally:
        conn.close()
    for item in reg:
        if item.get("checksum") == checksum:
            print(f"⚠ 该数据包已恢复过（checksum={checksum[:16]}…，{item.get('restored_at')}）")

    print(f"包: {pkg}")
    print(f"库快照: {db_path.name} ({db_path.stat().st_size} bytes) checksum={checksum[:16]}…")
    print(f"目标: {target}")
    if not args.apply:
        print("\n[dry-run] 未执行任何写入。加 --apply 执行替换。")
        return 0

    # 备份当前库（时间戳副本，恢复点）
    backup_dir = target.parent / "restore_backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = backup_dir / f"pre_restore_{stamp}_{DB_NAME}"
    shutil.copy2(target, backup)
    print(f"已备份当前库: {backup}")

    # 覆盖替换
    shutil.copy2(db_path, target)
    print(f"已替换: {target}")

    # 完整性验证
    v = sqlite3.connect(str(target))
    try:
        ok = v.execute("PRAGMA integrity_check").fetchone()[0]
        docs = v.execute("SELECT COUNT(*) FROM doc_meta").fetchone()[0]
        clauses = v.execute("SELECT COUNT(*) FROM clause_revision").fetchone()[0]
    finally:
        v.close()
    if ok != "ok":
        print(f"✗ integrity_check 未通过: {ok}")
        return 1
    print(f"✓ 完整性 OK（doc_meta={docs}, clause_revision={clauses}）")
    # 幂等台账（写回新库）
    v = sqlite3.connect(str(target))
    try:
        v.execute("INSERT OR IGNORE INTO app_config (config_key, config_value) VALUES (?,?)",
                  (REGISTRY_KEY, "[]"))
        v.execute(
            "UPDATE app_config SET config_value=? WHERE config_key=?",
            (json.dumps([*reg, {"checksum": checksum, "restored_at": stamp}],
                        ensure_ascii=False), REGISTRY_KEY))
        v.commit()
    finally:
        v.close()
    print("恢复完成。重新启动引擎即可使用恢复后的知识库。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
