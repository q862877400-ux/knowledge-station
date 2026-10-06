"""E1 步骤 3：为实验臂算向量，写进副本的 `clause_vec_ctx`（**断点续跑**）。

要点：
 · 只读 `retrieval_text_ctx`（实验臂文本），写 `clause_vec_ctx`；
 · 写入用 **float32 blob**（2048 字节），不是 JSON 文本 —— 实测 sqlite-vec 两种都收，
   但 blob 少一层 JSON 解析，全库 52 万条时差别可观；
 · 每 50 批 commit 一次；中断后重跑自动跳过已算的；
 · 全程只碰**副本** `exp.db`，真库一个字节都不动。

用法：
    .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-1-contextual\\03-embed.py            # 全量
    .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-1-contextual\\03-embed.py --limit 200 # 冒烟
"""
from __future__ import annotations

import argparse
import array
import sqlite3
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
EXP = HERE / "exp.db"
BATCH = 64
COMMIT_EVERY = 50          # 批


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--batch", type=int, default=BATCH)
    args = ap.parse_args()

    from src.core.retrieval import embedder
    from src.core.storage.sqlite_db import load_vec_extension

    conn = sqlite3.connect(str(EXP))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    if not load_vec_extension(conn):
        print("⛔ sqlite-vec 加载失败")
        return 1
    conn.execute("CREATE VIRTUAL TABLE IF NOT EXISTS clause_vec_ctx USING vec0("
                 "clause_revision_id TEXT PRIMARY KEY, embedding FLOAT[512])")
    conn.commit()

    have = {r[0] for r in conn.execute("SELECT clause_revision_id FROM clause_vec_ctx")}
    print(f"[embed] 已有 {len(have)} 条", flush=True)
    rows = conn.execute(
        "SELECT clause_revision_id, retrieval_text FROM retrieval_text_ctx"
        " ORDER BY rowid").fetchall()
    todo = [(r[0], r[1]) for r in rows if r[0] not in have]
    if args.limit:
        todo = todo[:args.limit]
    print(f"[embed] 待算 {len(todo)} 条（batch={args.batch}）", flush=True)
    if not todo:
        print("[embed] 没有待算的")
        return 0

    # 预热（首次装载模型）
    t0 = time.perf_counter()
    embedder.embed_batch([todo[0][1]])
    print(f"[embed] 预热 {time.perf_counter()-t0:.1f}s，dim={len(embedder.embed_query('测'))}", flush=True)

    t_start = time.perf_counter()
    done = 0
    batches_since_commit = 0
    for i in range(0, len(todo), args.batch):
        chunk = todo[i:i + args.batch]
        embs = embedder.embed_batch([t for _, t in chunk])
        payload = [(cid, array.array("f", e).tobytes()) for (cid, _), e in zip(chunk, embs)]
        conn.executemany(
            "INSERT OR REPLACE INTO clause_vec_ctx (clause_revision_id, embedding)"
            " VALUES (?, ?)", payload)
        done += len(chunk)
        batches_since_commit += 1
        if batches_since_commit >= COMMIT_EVERY:
            conn.commit()
            batches_since_commit = 0
        if (i // args.batch) % 100 == 0:
            el = time.perf_counter() - t_start
            rate = done / el if el else 0
            print(f"[embed] {done}/{len(todo)}  {el:.0f}s  {rate*1000:.1f} 条/s"
                  f"  预计剩余 {max(0,(len(todo)-done)/rate/60):.0f} 分钟", flush=True)
    conn.commit()
    el = time.perf_counter() - t_start
    print(f"[embed] 完成 {done} 条，用时 {el/60:.1f} 分钟（{done/el:.1f} 条/s）", flush=True)
    n = conn.execute("SELECT COUNT(*) FROM clause_vec_ctx").fetchone()[0]
    print(f"[embed] clause_vec_ctx 现有 {n} 行", flush=True)
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
