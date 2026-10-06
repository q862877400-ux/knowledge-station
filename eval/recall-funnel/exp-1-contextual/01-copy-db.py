"""E1 步骤 1：把真库复制成实验副本（**真库全程只读，绝不覆盖它的 clause_vec**）。

用 SQLite 的在线备份 API 从只读连接复制 —— 保证副本是**一致快照**（含 WAL 里已提交的内容）。
副本建好后自检：条款数、向量表行数、向量表可读条数，三者都要与真库一致。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-1-contextual\\01-copy-db.py [--force]
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
REAL = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"
EXP = HERE / "exp.db"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="副本已存在时覆盖重建")
    args = ap.parse_args()

    if EXP.exists() and not args.force:
        print(f"[skip] 副本已存在：{EXP}（{EXP.stat().st_size/2**30:.2f} GB）；要重建加 --force")
        return 0

    mtime0 = REAL.stat().st_mtime
    src = sqlite3.connect(f"file:{REAL.as_posix()}?mode=ro", uri=True)
    if EXP.exists():
        EXP.unlink()
    dst = sqlite3.connect(str(EXP))
    t0 = time.perf_counter()
    with dst:
        src.backup(dst)
    dst.close()
    dt = time.perf_counter() - t0
    print(f"[copy] {REAL.name} → {EXP.name}  用时 {dt:.1f}s  大小 {EXP.stat().st_size/2**30:.2f} GB")

    # 自检
    from src.core.storage.sqlite_db import load_vec_extension
    c = sqlite3.connect(f"file:{EXP.as_posix()}?mode=ro", uri=True)
    load_vec_extension(c)
    n_clause = c.execute("SELECT COUNT(*) FROM clause_revision").fetchone()[0]
    n_vec = c.execute("SELECT COUNT(*) FROM clause_vec").fetchone()[0]
    n_fts = c.execute("SELECT COUNT(*) FROM clause_fts").fetchone()[0]
    n_doc = c.execute("SELECT COUNT(*) FROM doc_meta").fetchone()[0]
    print(f"[check] 副本 clause_revision={n_clause}  clause_vec={n_vec}  clause_fts={n_fts}  doc_meta={n_doc}")
    ok = (n_clause, n_vec, n_fts, n_doc) == (522021, 522021, 522021, 6797)
    print(f"[check] 与真库应有值一致：{'✅' if ok else '⛔ 不一致，停下'}")
    c.close()
    mtime1 = REAL.stat().st_mtime
    print(f"[check] 真库 mtime {'未变 ✅' if mtime0 == mtime1 else '⛔ 被改动'}")
    return 0 if ok and mtime0 == mtime1 else 1


if __name__ == "__main__":
    sys.exit(main())
