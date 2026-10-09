"""exp-15 代价侧小探针：把 `k` 从 20 放大到 1000，向量通道的 KNN 扫描慢多少？

**为什么必须单独量**：本批的 7 条臂里，只有 `fts`/`vec` 的取数变了。
run.py 的 `2.10 s/条` 是**整批**（7 臂 + 一次生产调用）的合计，**不能**当"放大池子的代价"。
生产路径的参照是 `docs/NEXT-DEV-PLAN-2026-09-28.md §四第 1 条` 的 0.6 s 与
`exp-4b` 在真库上实测的 **1074.7 ms（663,634 行）**。

只读真库（`mode=ro`）；不改任何生产代码。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-15-pool-depth-fusion\\probe-knn-cost.py
"""
from __future__ import annotations

import json
import os
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval" / "recall-funnel"))
HERE = Path(__file__).resolve().parent

DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"
BENCH = ROOT / "eval" / "recall-funnel" / "benchmark-v2.jsonl"
OUT = HERE / "knn-cost.json"
KS = (20, 100, 1000)
REPS = 3


def main() -> int:
    import funnel
    from src.core.retrieval import embedder

    conn = funnel.ro_conn(DB)
    rows = [json.loads(l) for l in BENCH.read_text(encoding="utf-8").splitlines() if l.strip()]
    items = [r for r in rows
             if (r.get("v2") or {}).get("bucket") == "keep"
             and not ({"gold_multi_def", "gold_dup_text"} & set((r.get("v2") or {}).get("flags", [])))]
    queries = [it["query"] for it in items[:10]]        # 10 条真实提问
    print(f"[probe] 库 = {DB}（mode=ro）；提问 {len(queries)} 条 × k={KS} × {REPS} 次", flush=True)

    res: dict[str, list[float]] = {str(k): [] for k in KS}
    sizes: dict[str, int] = {}
    for q in queries:
        emb = embedder.embed_query(q)
        for k in KS:
            for _ in range(REPS):
                t0 = time.perf_counter()
                got = conn.execute(
                    "SELECT clause_revision_id FROM clause_vec"
                    " WHERE embedding MATCH ? AND k = ? ORDER BY distance",
                    (json.dumps(emb), k)).fetchall()
                res[str(k)].append((time.perf_counter() - t0) * 1000)
            sizes[str(k)] = len(got)

    out = {"db_rows_clause_vec": conn.execute("SELECT COUNT(*) FROM clause_vec").fetchone()[0],
           "queries": len(queries), "reps": REPS, "knn_ms": {}, "rows_returned": sizes}
    for k in KS:
        v = sorted(res[str(k)])
        out["knn_ms"][str(k)] = {"p50": round(v[len(v) // 2], 1), "min": round(v[0], 1),
                                 "max": round(v[-1], 1), "mean": round(statistics.mean(v), 1)}
    base = out["knn_ms"]["20"]["p50"]
    out["ratio_vs_k20"] = {str(k): round(out["knn_ms"][str(k)]["p50"] / base, 3) for k in KS}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"[probe] 已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
