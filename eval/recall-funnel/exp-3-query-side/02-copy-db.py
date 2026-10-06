"""E3 · 步骤 2：把真库**复制**一份给 E3 用（真库全程只读）。

为什么必须复制：生产检索链 `perform_hybrid_search` 通过 `_conn()` → `get_db_connection()`
开的是**读写**连接（`hybrid_engine.set_db_override()` 正是给 eval 指副本用的）。
为了做到"真库一个字节都不动"，E3 在**副本**上跑：`set_db_override(副本)`。

用 sqlite3 的 `backup()` API（不是文件复制）：拿到一致快照，不受 WAL 影响。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-3-query-side\\02-copy-db.py
"""
from __future__ import annotations

import os
import sqlite3
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"
DST = HERE / "exp.db"


def main() -> int:
    from src.core.storage.sqlite_db import load_vec_extension

    if DST.exists():
        c = sqlite3.connect(f"file:{DST.as_posix()}?mode=ro", uri=True)
        load_vec_extension(c)
        try:
            n = c.execute("SELECT COUNT(*) FROM clause_revision").fetchone()[0]
            v = c.execute("SELECT COUNT(*) FROM clause_vec").fetchone()[0]
            print(f"[copy] 副本已存在：clause_revision={n} clause_vec={v}（不重做）")
            return 0
        finally:
            c.close()

    src_mtime = DB.stat().st_mtime
    print(f"[copy] 源 {DB}\n[copy] 大小 {DB.stat().st_size/1e9:.2f} GB → {DST}")
    t0 = time.perf_counter()
    src = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    dst = sqlite3.connect(str(DST))
    with dst:
        src.backup(dst)
    dst.close()
    src.close()
    print(f"[copy] 完成，用时 {time.perf_counter()-t0:.1f}s")

    c = sqlite3.connect(f"file:{DST.as_posix()}?mode=ro", uri=True)
    load_vec_extension(c)
    n = c.execute("SELECT COUNT(*) FROM clause_revision").fetchone()[0]
    v = c.execute("SELECT COUNT(*) FROM clause_vec").fetchone()[0]
    d = c.execute("SELECT COUNT(*) FROM doc_meta").fetchone()[0]
    c.close()
    print(f"[copy] 校验：clause_revision={n} clause_vec={v} doc_meta={d}")
    print(f"[copy] 真库 mtime 是否变化：{DB.stat().st_mtime != src_mtime}"
          f"（应为 False {'✅' if DB.stat().st_mtime == src_mtime else '⛔'}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
