"""E4 · 步骤 0：**量真实吞吐**（决定全量重算值不值得做）。

外部评估点名 Qwen3-Embedding-0.6B，并说"重算 52 万条估计十几分钟到几小时，**我没有实测数据**"。
本脚本把那句话变成实测数字：下载 → GPU 加载 → 在**真库抽样条文**上量条/秒 → 折算全量成本。

⚠ 只读真库；只写 HF 缓存与 `var/tmp/`；**不建任何索引、不碰生产向量**。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-4-embedding-shadow\\00-measure-throughput.py
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
OUT = HERE / "throughput.json"
MODEL_ID = "Qwen/Qwen3-Embedding-0.6B"
N_SAMPLE = 512
BATCHES = (16, 32, 64)
N_TOTAL = 521_978


def main() -> int:
    import torch
    import transformers
    from huggingface_hub import snapshot_download

    print(f"[t0] torch {torch.__version__} | cuda={torch.cuda.is_available()} | "
          f"transformers {transformers.__version__}", flush=True)
    if not torch.cuda.is_available():
        print("⛔ CUDA 不可用")
        return 1
    print(f"[t0] GPU = {torch.cuda.get_device_name(0)} | "
          f"显存 {torch.cuda.get_device_properties(0).total_memory/1e9:.1f} GB", flush=True)

    t = time.perf_counter()
    path = snapshot_download(MODEL_ID, allow_patterns=["*.json", "*.safetensors", "*.txt"])
    print(f"[t0] 模型就绪（{time.perf_counter()-t:.0f}s）：{path}", flush=True)
    size = sum(f.stat().st_size for f in Path(path).rglob("*") if f.is_file())
    print(f"[t0] 本地体积 {size/1e9:.2f} GB", flush=True)

    from transformers import AutoModel, AutoTokenizer
    t = time.perf_counter()
    tok = AutoTokenizer.from_pretrained(MODEL_ID, padding_side="left")
    model = AutoModel.from_pretrained(MODEL_ID, dtype=torch.float16).to("cuda").eval()
    print(f"[t0] 加载 {time.perf_counter()-t:.0f}s | 参数量 "
          f"{sum(p.numel() for p in model.parameters())/1e6:.1f} M", flush=True)

    db = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"
    conn = sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)
    rows = conn.execute(
        "SELECT standard_name, hierarchy_path, clause_number, body"
        " FROM retrieval_text_ctx LIMIT ?", (N_SAMPLE,)).fetchall() if _has_table(conn) else None
    if rows is None:
        rows = conn.execute("SELECT '', '', '', content_text FROM clause_revision"
                            " WHERE trim(coalesce(content_text,''))<>'' LIMIT ?", (N_SAMPLE,)).fetchall()
    conn.close()
    # 实验臂的输入形态与 E1 的 V0 正文口径一致：正文前 512 字
    texts = [(r[3] or "")[:512] for r in rows]
    print(f"[t0] 抽样 {len(texts)} 条真实条文（中位长度 {sorted(len(t) for t in texts)[len(texts)//2]} 字）",
          flush=True)

    result = {"model": MODEL_ID, "n_sample": len(texts), "n_total_needed": N_TOTAL,
              "gpu": torch.cuda.get_device_name(0), "dtype": "float16", "batches": {}}

    def encode(batch):
        enc = tok(batch, padding=True, truncation=True, max_length=512, return_tensors="pt").to("cuda")
        with torch.no_grad():
            out = model(**enc)
        emb = out.last_hidden_state[:, -1]                 # Qwen3-Embedding：取最后一个 token
        return torch.nn.functional.normalize(emb, p=2, dim=1)

    with torch.no_grad():                                   # 预热
        encode(texts[:8])
    torch.cuda.synchronize()

    best = None
    for bs in BATCHES:
        t = time.perf_counter()
        for i in range(0, len(texts), bs):
            encode(texts[i:i + bs])
        torch.cuda.synchronize()
        el = time.perf_counter() - t
        rate = len(texts) / el
        est_h = N_TOTAL / rate / 3600
        result["batches"][str(bs)] = {"batch": bs, "elapsed_s": round(el, 2),
                                      "texts_per_s": round(rate, 1),
                                      "est_full_hours": round(est_h, 2),
                                      "est_full_min": round(est_h * 60, 1)}
        print(f"[t0] batch={bs:3d}  {rate:8.1f} 条/s  ⇒ 全库 {N_TOTAL} 条约 "
              f"{est_h*60:.1f} 分钟", flush=True)
        if best is None or rate > best[1]:
            best = (bs, rate)
    # 用同一个模型再量一次"现役 fastembed"的对照（CPU）
    try:
        from src.core.retrieval import embedder
        t = time.perf_counter()
        embedder.embed_batch(texts[:128])
        el = time.perf_counter() - t
        result["incumbent_fastembed_cpu"] = {"texts_per_s": round(128 / el, 1),
                                             "est_full_hours": round(N_TOTAL / (128 / el) / 3600, 2)}
        print(f"[t0] 现役 fastembed(CPU) 对照：{128/el:.1f} 条/s ⇒ 全库约 "
              f"{N_TOTAL/(128/el)/3600:.1f} 小时", flush=True)
    except Exception as e:                                   # noqa: BLE001 - 对照项，失败不影响主结论
        result["incumbent_fastembed_cpu"] = f"未测成：{type(e).__name__}: {e}"

    result["best"] = {"batch": best[0], "texts_per_s": round(best[1], 1),
                      "est_full_min": round(N_TOTAL / best[1] / 60, 1)}
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1))
    print(f"\n已写 {OUT}")
    return 0


def _has_table(conn) -> bool:
    return bool(conn.execute("SELECT 1 FROM sqlite_master WHERE type='table'"
                             " AND name='retrieval_text_ctx'").fetchone())


if __name__ == "__main__":
    sys.exit(main())
