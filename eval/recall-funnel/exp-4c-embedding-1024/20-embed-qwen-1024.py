"""E4c · 步骤 1：用 **Qwen3-Embedding-0.6B（1024 维，原生全维）** 重算全库条文向量（影子表）。

与 `exp-4/01-embed-qwen.py` 的**唯一差别** = 输出维度：那里截断到 512 维（MRL），这里用满原生 1024 维。
其余**逐项不动**：条文文本同款公式、同一个模型、batch 照 `19-probe` 实测、只在 exp-4 的副本上写。

 · 写进**独立表** `clause_vec_qwen1024`（float32 blob，4096 字节/条），**绝不碰生产 `clause_vec`**；
 · 真库全程**只读**（`mode=ro`）；本脚本只动 exp-4 的副本 `exp.db`；断点续跑；每 N 批提交一次。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-4c-embedding-1024\\20-embed-qwen-1024.py
"""
from __future__ import annotations

import array
import json
import sqlite3
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
EXP = ROOT / "eval" / "recall-funnel" / "exp-4-embedding-shadow" / "exp.db"
MODEL_ID = "Qwen/Qwen3-Embedding-0.6B"
OUT_DIM = 1024
COMMIT_EVERY = 100
LOG = HERE / "embed1024-progress.json"
TABLE = "clause_vec_qwen1024"


def pick_batch() -> int:
    p = HERE / "throughput-1024.json"
    if p.exists():
        try:
            return int(json.loads(p.read_text(encoding="utf-8"))["best"]["batch"])
        except Exception:
            pass
    return 16


def display_text(title, body):
    """**现役同款公式**（与 exp-4 一字不差）。"""
    return f"{title or ''}\n{(body or '')[:512]}"


def main() -> int:
    import torch
    import torch.nn.functional as Fn
    from transformers import AutoModel, AutoTokenizer
    from src.core.storage.sqlite_db import load_vec_extension

    BATCH = pick_batch()
    conn = sqlite3.connect(str(EXP))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=120000")
    if not load_vec_extension(conn):
        print("⛔ sqlite-vec 加载失败")
        return 1
    conn.execute(f"CREATE VIRTUAL TABLE IF NOT EXISTS {TABLE} USING vec0("
                 f"clause_revision_id TEXT PRIMARY KEY, embedding FLOAT[{OUT_DIM}])")
    conn.commit()

    have = {r[0] for r in conn.execute(f"SELECT clause_revision_id FROM {TABLE}")}
    rows = conn.execute(
        "SELECT clause_revision_id, title, content_text FROM clause_revision"
        " WHERE trim(coalesce(content_text,'')) <> '' ORDER BY rowid").fetchall()
    todo = [(r[0], display_text(r[1], r[2])) for r in rows if r[0] not in have]
    print(f"[e4c] 目标 {len(rows)} 条；已算 {len(have)}；待算 {len(todo)}；batch={BATCH}；维度={OUT_DIM}",
          flush=True)
    if not todo:
        print("[e4c] 没有待算的")
        return 0

    tok = AutoTokenizer.from_pretrained(MODEL_ID, padding_side="left")
    model = AutoModel.from_pretrained(MODEL_ID, dtype=torch.float16).to("cuda").eval()
    print(f"[e4c] 模型就绪；输出维度 {OUT_DIM}（原生全维，不截断）", flush=True)

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
                f"INSERT OR REPLACE INTO {TABLE} (clause_revision_id, embedding)"
                " VALUES (?, ?)", payload)
            done += len(chunk); since += 1
            if since >= COMMIT_EVERY:
                conn.commit(); since = 0
            if (i // BATCH) % 200 == 0:
                el = time.perf_counter() - t0
                rate = done / el if el else 0
                eta = (len(todo) - done) / rate / 60 if rate else 0
                print(f"[e4c] {done}/{len(todo)}  {el:.0f}s  {rate:.1f} 条/s  预计剩余 {eta:.0f} 分钟",
                      flush=True)
                LOG.write_text(json.dumps({"done": done, "total": len(todo),
                                           "rate": round(rate, 1), "eta_min": round(eta, 1),
                                           "elapsed_s": round(el, 1)}, ensure_ascii=False),
                               encoding="utf-8")
    conn.commit()
    n = conn.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0]
    nb = conn.execute("SELECT COUNT(*) FROM clause_vec_qwen").fetchone()[0]
    print(f"[e4c] 完成：{TABLE}={n} / clause_vec_qwen={nb}"
          f"（应一致 {'✅' if n == nb else '⛔ 不一致'}）；用时 {(time.perf_counter()-t0)/60:.1f} 分钟",
          flush=True)
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
