"""E4 第二轮 · A 臂：**提问侧成本**（单条查询延迟 / 冷启动 / 显存）。

为什么要它：E4 第一轮（`../exp-4-embedding-shadow/`）量的是**入库侧**成本（52 万条重算
39 分钟 GPU / 2.2 小时 CPU），而**"生产每来一个问题要等多久"从来没量过** ——
第一轮 README §八 自己把它列为"换生产前必须先回答的"第一条。本脚本量这一条。

三条路各量一次（口径在 `stop-loss.json` 的 `part_A_cost_and_latency` 里**跑前写死**）：
 · 现役路：`src.core.retrieval.embedder.embed_query`（fastembed `bge-small-zh-v1.5`，CPU/ONNX）
 · 实验路：`Qwen/Qwen3-Embedding-0.6B`（torch，fp16，CUDA）
 · 附加（抽样 30 条，**不在冻结口径内**，只为回答"没显卡的机器能不能跑"）：
   Qwen3 同模型 **CPU fp32**

另外**同跑内复测**现有向量路的**扫描**耗时（52 万行 brute force）当参照物 ——
本仓既有读数 606.0 ms，但"转述的数字要回原始来源核"。

样本 = 考卷 171 条**真实提问串**（`benchmark-v2.jsonl` 的 `query`），不另造串。

只读：真库不碰；`exp.db` 只读（`mode=ro`）；不写任何向量。
用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-4b-embedding-round2\\10-latency.py
"""
from __future__ import annotations

import array
import json
import sqlite3
import statistics
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
EXP = ROOT / "eval" / "recall-funnel" / "exp-4-embedding-shadow" / "exp.db"
BENCH = ROOT / "eval" / "recall-funnel" / "benchmark-v2.jsonl"
OUT = HERE / "latency.json"
MODEL_ID = "Qwen/Qwen3-Embedding-0.6B"
OUT_DIM = 512
WARMUP = 5
CPU_EXTRA_N = 30          # 附加臂只抽样，明确标注"这是抽样，不是全部"
KNN_K = 1000
KNN_REPEAT = 5


def pct(xs: list[float], q: float) -> float:
    if not xs:
        return float("nan")
    s = sorted(xs)
    i = min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))
    return s[i]


def stat(xs: list[float]) -> dict:
    return {
        "n": len(xs),
        "p50_ms": round(pct(xs, 0.50), 2),
        "p90_ms": round(pct(xs, 0.90), 2),
        "max_ms": round(max(xs), 2),
        "mean_ms": round(statistics.fmean(xs), 2),
        "first_call_ms": round(xs[0], 2),
    }


def main() -> int:
    import torch
    import torch.nn.functional as Fn
    from transformers import AutoModel, AutoTokenizer
    import src.core.retrieval.embedder as E
    from src.core.storage.sqlite_db import load_vec_extension

    queries = [json.loads(l)["query"] for l in BENCH.read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"[e4b] 考卷提问 {len(queries)} 条（真实串，不另造）", flush=True)
    result: dict = {
        "experiment": "E4 第二轮 · A 臂：提问侧成本（单条查询延迟/冷启动/显存）",
        "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu",
        "torch": torch.__version__,
        "dtype_gpu": "float16", "n_queries": len(queries),
        "sample": "eval/recall-funnel/benchmark-v2.jsonl 的 query 字段（171 条，全部）",
        "warmup_calls": WARMUP,
    }

    # ── 参照物：现有向量路「扫描」耗时（与嵌入无关，只跟表大小/维度有关）──
    conn = sqlite3.connect(f"file:{EXP.as_posix()}?mode=ro", uri=True)
    if not load_vec_extension(conn):
        print("⛔ sqlite-vec 加载失败")
        return 1
    n_vec = conn.execute("SELECT COUNT(*) FROM clause_vec").fetchone()[0]
    n_qwen = conn.execute("SELECT COUNT(*) FROM clause_vec_qwen").fetchone()[0]
    print(f"[e4b] clause_vec={n_vec} / clause_vec_qwen={n_qwen} "
          f"{'✅' if n_vec == n_qwen else '⛔ 不一致'}", flush=True)

    # ── 路 1：现役 CPU（fastembed bge-small）──
    t0 = time.perf_counter()
    E._get_model()                      # 冷启动（**会加载**；本机权重已缓存 ⇒ 不含下载）
    cold_cpu_ms = (time.perf_counter() - t0) * 1000
    for q in queries[:WARMUP]:
        E.embed_query(q)
    lat_cpu = []
    for q in queries:
        t = time.perf_counter()
        E.embed_query(q)
        lat_cpu.append((time.perf_counter() - t) * 1000)
    result["path_incumbent_cpu_bge_small"] = {
        "model": "BAAI/bge-small-zh-v1.5（fastembed/ONNX，CPU）",
        "cold_start_ms": round(cold_cpu_ms, 1),
        "cold_start_note": "本机权重已缓存 ⇒ **不含下载**；首次装机还要多一次下载",
        "warm": stat(lat_cpu),
    }
    print(f"[e4b] CPU bge-small 冷启动 {cold_cpu_ms:.0f} ms；warm p50 "
          f"{stat(lat_cpu)['p50_ms']} ms", flush=True)

    # ── 参照物：扫描（用 CPU 路的一条查询向量；扫描耗时与查询向量无关）──
    qv = E.embed_query(queries[0])
    scan = []
    for _ in range(KNN_REPEAT):
        t = time.perf_counter()
        list(conn.execute("SELECT clause_revision_id FROM clause_vec"
                          " WHERE embedding MATCH ? AND k = ? ORDER BY distance",
                          (array.array("f", qv).tobytes(), KNN_K)))
        scan.append((time.perf_counter() - t) * 1000)
    result["reference_knn_scan"] = {
        "table": "clause_vec", "rows": n_vec, "dim": 512, "k": KNN_K,
        "repeat": KNN_REPEAT, "median_ms": round(statistics.median(scan), 1),
        "all_ms": [round(x, 1) for x in scan],
        "note": "**扫描**耗时（brute force，sqlite-vec）；与嵌入模型无关，只跟表大小/维度有关。"
                "本仓既有读数 606.0 ms（52 万行）—— 本轮同跑内复测，以本值为准。",
    }
    print(f"[e4b] 参照：KNN 扫描中位 {result['reference_knn_scan']['median_ms']} ms", flush=True)

    # ── 路 2：实验 GPU（Qwen3-0.6B，fp16，CUDA）──
    torch.cuda.reset_peak_memory_stats()
    t0 = time.perf_counter()
    tok = AutoTokenizer.from_pretrained(MODEL_ID, padding_side="left")
    model = AutoModel.from_pretrained(MODEL_ID, dtype=torch.float16).to("cuda").eval()
    cold_gpu_ms = (time.perf_counter() - t0) * 1000
    n_params = sum(p.numel() for p in model.parameters())

    def qwen_vec(q: str):
        enc = tok([q], padding=True, truncation=True, max_length=512,
                  return_tensors="pt").to("cuda")
        with torch.no_grad():
            out = model(**enc)
        v = Fn.normalize(out.last_hidden_state[:, -1][:, :OUT_DIM], p=2, dim=1)
        return v[0].float().cpu().numpy().tolist()

    for q in queries[:WARMUP]:
        qwen_vec(q)
    torch.cuda.synchronize()
    lat_gpu = []
    for q in queries:
        torch.cuda.synchronize()
        t = time.perf_counter()
        qwen_vec(q)
        torch.cuda.synchronize()
        lat_gpu.append((time.perf_counter() - t) * 1000)
    result["path_experiment_gpu_qwen3"] = {
        "model": MODEL_ID, "params": n_params, "dtype": "float16", "device": "cuda",
        "cold_start_ms": round(cold_gpu_ms, 1),
        "cold_start_note": "本机权重已缓存 ⇒ **不含下载**；含 tokenizer+model 装载与 H2D 搬运",
        "peak_mem_allocated_MiB": round(torch.cuda.max_memory_allocated() / 2**20, 1),
        "peak_mem_reserved_MiB": round(torch.cuda.max_memory_reserved() / 2**20, 1),
        "warm": stat(lat_gpu),
        "timing_note": "单条计时前后各 `torch.cuda.synchronize()`（否则量到的是排队时间）",
    }
    print(f"[e4b] GPU Qwen3 冷启动 {cold_gpu_ms:.0f} ms；warm p50 {stat(lat_gpu)['p50_ms']} ms；"
          f"峰值显存 {result['path_experiment_gpu_qwen3']['peak_mem_reserved_MiB']} MiB", flush=True)

    # ── 附加（抽样，**不在冻结口径内**）：Qwen3 同模型 CPU fp32 ──
    del model
    torch.cuda.empty_cache()
    try:
        cpu_model = AutoModel.from_pretrained(MODEL_ID).eval()   # fp32
        t0 = time.perf_counter()
        for q in queries[:3]:
            enc = tok([q], padding=True, truncation=True, max_length=512, return_tensors="pt")
            with torch.no_grad():
                cpu_model(**enc)
        warm3_ms = (time.perf_counter() - t0) * 1000 / 3
        lat_cpu_qwen = []
        for q in queries[:CPU_EXTRA_N]:
            enc = tok([q], padding=True, truncation=True, max_length=512, return_tensors="pt")
            t = time.perf_counter()
            with torch.no_grad():
                cpu_model(**enc)
            lat_cpu_qwen.append((time.perf_counter() - t) * 1000)
        result["extra_qwen3_on_cpu"] = {
            "model": MODEL_ID, "dtype": "float32", "device": "cpu",
            "n": CPU_EXTRA_N,
            "note": f"**附加、抽样 {CPU_EXTRA_N} 条，不是全部**；不在 `stop-loss.json` 的冻结口径内，"
                    "只为回答『没有显卡的机器能不能跑』",
            "warm": stat(lat_cpu_qwen),
        }
        print(f"[e4b] 附加 Qwen3-CPU 抽样 {CPU_EXTRA_N} 条：p50 "
              f"{stat(lat_cpu_qwen)['p50_ms']} ms", flush=True)
        del cpu_model
    except Exception as exc:  # noqa: BLE001
        result["extra_qwen3_on_cpu"] = {"error": f"{type(exc).__name__}: {exc}"}
        print(f"[e4b] 附加 Qwen3-CPU 失败（如实记）：{type(exc).__name__}: {exc}", flush=True)

    conn.close()
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
