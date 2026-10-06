"""入库试跑 · 步骤 1：**建一份真库的副本**（用 SQLite 官方 backup API，保证一致性）。

## 安全设计（业主 2026-10-07 同意试跑）
 · 真库路径：`%APPDATA%\\KnowledgeStation\\database\\knowledge.db`（**只读打开**）；
 · 副本路径：`var/tmp/ingest-trial/data/database/knowledge.db`；
 · 之后所有入库/检索都在 `KS_DATA_DIR=var/tmp/ingest-trial/data` 下跑 ⇒ **引擎指着副本**，
   真库一个字节不会被写。
 · 用 `sqlite3.Connection.backup()` 而不是文件拷贝 ⇒ 正确合并 WAL，拿到一致快照。

模型缓存另用 `KS_MODELS_DIR` 指向真库那份（避免重新下载 ~91MB 的 BGE）。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\23-setup-trial-copy.py
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = HERE / "trial-copy-setup.json"
REAL = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"
TRIAL = ROOT / "var" / "tmp" / "ingest-trial" / "data"
COPY = TRIAL / "database" / "knowledge.db"


def main() -> int:
    if not REAL.exists():
        print(f"⛔ 真库不在：{REAL}")
        return 1
    COPY.parent.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()
    src = sqlite3.connect(f"file:{REAL.as_posix()}?mode=ro", uri=True)
    if COPY.exists():
        COPY.unlink()
    dst = sqlite3.connect(str(COPY))
    src.backup(dst)                       # 一致快照，正确合并 WAL
    dst.close()
    src.close()
    dt = time.perf_counter() - t0

    print(f"[copy] 真库 {REAL.stat().st_size/1e9:.2f} GB → 副本 {COPY}  用时 {dt:.1f}s")

    # 复核：两边的计数必须一致
    def counts(p: Path) -> dict:
        c = sqlite3.connect(f"file:{p.as_posix()}?mode=ro", uri=True)
        r = {t: c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
             for t in ("doc_meta", "clause_revision")}
        try:
            c.execute("SELECT 1 FROM clause_vec LIMIT 1")
            r["clause_vec(需扩展)"] = "需 load_vec_extension"
        except sqlite3.Error:
            pass
        c.close()
        return r

    real_c, copy_c = counts(REAL), counts(COPY)
    print(f"[copy] 真库 {real_c}")
    print(f"[copy] 副本 {copy_c}")
    same = real_c == copy_c
    print(f"[copy] 计数一致：{'✅' if same else '⛔'}")

    OUT.write_text(json.dumps({
        "why": "入库试跑前建真库副本；之后一切操作在 KS_DATA_DIR 指向的副本上进行",
        "real_db": str(REAL), "trial_dir": str(TRIAL), "copy_db": str(COPY),
        "real_size_gb": round(REAL.stat().st_size / 1e9, 3),
        "copy_size_gb": round(COPY.stat().st_size / 1e9, 3),
        "seconds": round(dt, 1),
        "counts_real": real_c, "counts_copy": copy_c, "counts_match": same,
        "env_to_use": {"KS_DATA_DIR": str(TRIAL),
                       "KS_MODELS_DIR": str(Path(os.environ["APPDATA"]) / "KnowledgeStation" / "models")},
        "boundary": ["真库以 mode=ro 打开；副本用 sqlite3 backup API 生成。"],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main())
