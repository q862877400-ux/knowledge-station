"""E4 · 步骤 1：用 **Qwen3-Embedding-0.6B（512 维）** 重算全库条文向量（影子表）。

要点（全部按 `stop-loss.json` 的冻结项）：
 · 条文文本**一字不动**，用**现役同款公式**：`title + "\\n" + content_text[:512]`
   （实测 title 仅 43/522,021 条有值 ⇒ 实际等于 content_text[:512]）；
 · 输出 **512 维**：Qwen3 原生 1024 ⇒ 取前 512 维后重新 L2 归一化（MRL），
   把"换模型"与"升维"两个变量拆开；
 · 写进**独立表** `clause_vec_qwen`（float32 blob，2048 字节/条），**绝不碰生产 `clause_vec`**；
 · 只在**副本**上写（真库只读）；断点续跑；每 N 批提交一次。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-4-embedding-shadow\\01-embed-qwen.py
"""
from __future__ import annotations

import array
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
EXP = HERE / "exp.db"
MODEL_ID = "Qwen/Qwen3-Embedding-0.6B"
OUT_DIM = 512
BATCH = 16                 # 实测最快（224.9 条/s）
COMMIT_EVERY = 100         # 批
LOG = HERE / "embed-progress.json"
DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"


def ensure_copy() -> None:
    if EXP.exists():
        return
    from src.core.storage.sqlite_db import load_vec_extension
    print(f"[e4] 复制真库（只读源）→ {EXP}", flush=True)
    t = time.perf_counter()
    src = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    dst = sqlite3.connect(str(EXP))
    with dst:
        src.backup(dst)
    dst.close(); src.close()
    c = sqlite3.connect(f"file:{EXP.as_posix()}?mode=ro", uri=True); load_vec_extension(c)
    print(f"[e4] 复制完成 {time.perf_counter()-t:.1f}s；clause_vec="
          f"{c.execute('SELECT COUNT(*) FROM clause_vec').fetchone()[0]}", flush=True)
    c.close()


def display_text(title: str | None, body: str | None) -> str:
    """**现役同款公式**（`clause_repo.insert_clauses_in_txn` 实测口径），一字不改。"""
    return f"{title or ''}\n{(body or '')[:512]}"


def main() -> int:
    import torch
    import torch.nn.functional as Fn
    from transformers import AutoModel, AutoTokenizer
    from src.core.storage.sqlite_db import load_vec_extension

    ensure_copy()
    conn = sqlite3.connect(str(EXP))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=120000")
    if not load_vec_extension(conn):
        print("⛔ sqlite-vec 加载失败")
        return 1
    conn.execute(f"CREATE VIRTUAL TABLE IF NOT EXISTS clause_vec_qwen USING vec0("
                 f"clause_revision_id TEXT PRIMARY KEY, embedding FLOAT[{OUT_DIM}])")
    conn.commit()

    have = {r[0] for r in conn.execute("SELECT clause_revision_id FROM clause_vec_qwen")}
    rows = conn.execute(
        "SELECT clause_revision_id, title, content_text FROM clause_revision"
        " WHERE trim(coalesce(content_text,'')) <> '' ORDER BY rowid").fetchall()
    todo = [(r[0], display_text(r[1], r[2])) for r in rows if r[0] not in have]
    print(f"[e4] 目标 {len(rows)} 条；已算 {len(have)}；待算 {len(todo)}", flush=True)
    if not todo:
        print("[e4] 没有待算的")
        return 0

    tok = AutoTokenizer.from_pretrained(MODEL_ID, padding_side="left")
    model = AutoModel.from_pretrained(MODEL_ID, dtype=torch.float16).to("cuda").eval()
    print(f"[e4] 模型就绪；输出维度 {OUT_DIM}（原生 1024 → 截断 + 重新归一化）", flush=True)

    t0 = time.perf_counter()
    done = 0
    since = 0
    with torch.no_grad():
        for i in range(0, len(todo), BATCH):
            chunk = todo[i:i + BATCH]
            enc = tok([t for _, t in chunk], padding=True, truncation=True,
                      max_length=512, return_tensors="pt").to("cuda")
            out = model(**enc)
            emb = Fn.normalize(out.last_hidden_state[:, -1][:, :OUT_DIM], p=2, dim=1)
            payload = [(cid, array.array("f", e.float().cpu().numpy()).tobytes())
                       for (cid, _), e in zip(chunk, emb)]
            conn.executemany(
                "INSERT OR REPLACE INTO clause_vec_qwen (clause_revision_id, embedding)"
                " VALUES (?, ?)", payload)
            done += len(chunk); since += 1
            if since >= COMMIT_EVERY:
                conn.commit(); since = 0
            if (i // BATCH) % 200 == 0:
                el = time.perf_counter() - t0
                rate = done / el if el else 0
                eta = (len(todo) - done) / rate / 60 if rate else 0
                print(f"[e4] {done}/{len(todo)}  {el:.0f}s  {rate:.1f} 条/s  预计剩余 {eta:.0f} 分钟",
                      flush=True)
                LOG.write_text(json.dumps({"done": done, "total": len(todo),
                                           "rate": round(rate, 1), "eta_min": round(eta, 1),
                                           "elapsed_s": round(el, 1)}, ensure_ascii=False),
                               encoding="utf-8")
    conn.commit()
    n = conn.execute("SELECT COUNT(*) FROM clause_vec_qwen").fetchone()[0]
    nb = conn.execute("SELECT COUNT(*) FROM clause_vec").fetchone()[0]
    print(f"[e4] 完成：clause_vec_qwen={n} / clause_vec={nb}"
          f"（应一致 {'✅' if n == nb else '⛔ 不一致'}）；用时 {(time.perf_counter()-t0)/60:.1f} 分钟",
          flush=True)
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
