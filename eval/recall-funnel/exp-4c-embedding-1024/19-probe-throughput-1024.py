"""E4c · 步骤 0：**1024 维**吞吐探针（真实条文抽样，GPU fp16）。

E4 第一轮测的是 **512 维**输出（batch16 = 224.9 条/s），当时本机还跑着别的服务。
本轮 GPU 空闲（1129/16376 MiB）⇒ **重新量一次 1024 维**，照实测挑 batch。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-4c-embedding-1024\\19-probe-throughput-1024.py
"""
from __future__ import annotations

import json
import sqlite3
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
EXP = ROOT / "eval" / "recall-funnel" / "exp-4-embedding-shadow" / "exp.db"
OUT = HERE / "throughput-1024.json"
MODEL_ID = "Qwen/Qwen3-Embedding-0.6B"
OUT_DIM = 1024
N_SAMPLE = 512
BATCHES = (16, 32, 64)


def display_text(title, body):
    return f"{title or ''}\n{(body or '')[:512]}"


def main() -> int:
    import torch
    import torch.nn.functional as Fn
    from transformers import AutoModel, AutoTokenizer
    from src.core.storage.sqlite_db import load_vec_extension

    conn = sqlite3.connect(f"file:{EXP.as_posix()}?mode=ro", uri=True)
    load_vec_extension(conn)
    rows = conn.execute(
        "SELECT title, content_text FROM clause_revision"
        " WHERE trim(coalesce(content_text,'')) <> '' ORDER BY rowid LIMIT ?",
        (N_SAMPLE,)).fetchall()
    conn.close()
    texts = [display_text(t, b) for t, b in rows]
    print(f"[e4c] 抽样 {len(texts)} 条真实条文；中位长度 "
          f"{sorted(len(t) for t in texts)[len(texts)//2]} 字", flush=True)

    tok = AutoTokenizer.from_pretrained(MODEL_ID, padding_side="left")
    model = AutoModel.from_pretrained(MODEL_ID, dtype=torch.float16).to("cuda").eval()
    out = {"model": MODEL_ID, "out_dim": OUT_DIM, "n_sample": len(texts),
           "gpu": torch.cuda.get_device_name(0), "dtype": "float16", "batches": {}}

    with torch.no_grad():
        for bs in BATCHES:
            # 热身 1 批，不计时
            enc = tok(texts[:bs], padding=True, truncation=True, max_length=512,
                      return_tensors="pt").to("cuda")
            _ = Fn.normalize(model(**enc).last_hidden_state[:, -1][:, :OUT_DIM], p=2, dim=1)
            torch.cuda.synchronize()
            t0 = time.perf_counter()
            for i in range(0, len(texts), bs):
                enc = tok(texts[i:i + bs], padding=True, truncation=True, max_length=512,
                          return_tensors="pt").to("cuda")
                e = Fn.normalize(model(**enc).last_hidden_state[:, -1][:, :OUT_DIM], p=2, dim=1)
                _ = e.float().cpu().numpy()
            torch.cuda.synchronize()
            el = time.perf_counter() - t0
            rate = len(texts) / el
            out["batches"][str(bs)] = {
                "batch": bs, "elapsed_s": round(el, 3), "texts_per_s": round(rate, 1),
                "est_full_min_521978": round(521978 / rate / 60, 1)}
            print(f"[e4c] batch={bs}: {el:.2f}s  {rate:.1f} 条/s  "
                  f"全量 521,978 预计 {521978/rate/60:.1f} 分钟", flush=True)

    best = max(out["batches"].values(), key=lambda d: d["texts_per_s"])
    out["best"] = best
    out["peak_mem_mib"] = {"allocated": round(torch.cuda.max_memory_allocated() / 2**20, 1),
                           "reserved": round(torch.cuda.max_memory_reserved() / 2**20, 1)}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[e4c] 最佳 batch={best['batch']}（{best['texts_per_s']} 条/s）⇒ 已写 {OUT}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
