"""E4c · 步骤 2：两臂对照（**唯一变量 = 输出维度 512 → 1024**，同一个 Qwen3-Embedding-0.6B）。

- **对照臂 `d512`**：查询取前 512 维 + L2 归一化（MRL）→ KNN `clause_vec_qwen`（E4 第一轮算好的表）
- **实验臂 `d1024`**：查询用**原生 1024 维** + L2 归一化 → KNN `clause_vec_qwen1024`（本轮算的表）

⚠ **两臂都不加查询指令前缀**（与 E4 第一轮一致）—— 指令前缀是 exp-4b 的变量，不许混进来。
⚠ 条文侧**一字不动**；两臂的候选集合必须**双向 EXCEPT = 0**（表尺寸必须一致），否则整次作废。

固定五路（exact/fts/modality）两臂完全相同（查询串没变）⇒ 并集差别只可能来自向量那一路。

**仪器对照（硬性）**：
 1. `d512` 臂必须**逐条**复现 E4 第一轮 `ctx` 臂的 `rank@1000`（`../exp-4-embedding-shadow/ab-per-query.jsonl`）；
 2. `FTS @1000` 两臂必须完全相同（升维与按字找无关）；
 3. 两张向量表的 `clause_revision_id` 集合双向 EXCEPT 必须为 0。

**代价侧读数**：对每条查询分别计时两臂的 KNN（@1000，同一 521,978 行语料）⇒ 报 p50/p90。

只读：真库不碰；`exp.db` 只读（`mode=ro`）；**不写任何向量**。
用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-4c-embedding-1024\\21-ab-1024.py
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
sys.path.insert(0, str(ROOT / "eval" / "recall-funnel"))
R1 = ROOT / "eval" / "recall-funnel" / "exp-4-embedding-shadow"
EXP = R1 / "exp.db"
OUT = HERE / "ab-1024-result.json"
OUT_PER = HERE / "ab-1024-per-query.jsonl"
MODEL_ID = "Qwen/Qwen3-Embedding-0.6B"
D512, D1024, K = 512, 1024, 1000


def main() -> int:
    import funnel as F
    import torch
    import torch.nn.functional as Fn
    from transformers import AutoModel, AutoTokenizer
    from src.core.retrieval import embedder
    from src.core.retrieval.hybrid_engine import extract_modality_from_query
    from src.core.storage.sqlite_db import load_vec_extension

    conn = sqlite3.connect(f"file:{EXP.as_posix()}?mode=ro", uri=True)
    if not load_vec_extension(conn):
        print("⛔ sqlite-vec 加载失败")
        return 1

    # ── 前置：两张表尺寸 + 双向 EXCEPT ──
    n512 = conn.execute("SELECT COUNT(*) FROM clause_vec_qwen").fetchone()[0]
    n1024 = conn.execute("SELECT COUNT(*) FROM clause_vec_qwen1024").fetchone()[0]
    only512 = conn.execute("SELECT COUNT(*) FROM clause_vec_qwen q WHERE NOT EXISTS ("
                           " SELECT 1 FROM clause_vec_qwen1024 t"
                           " WHERE t.clause_revision_id = q.clause_revision_id)").fetchone()[0]
    only1024 = conn.execute("SELECT COUNT(*) FROM clause_vec_qwen1024 t WHERE NOT EXISTS ("
                            " SELECT 1 FROM clause_vec_qwen q"
                            " WHERE q.clause_revision_id = t.clause_revision_id)").fetchone()[0]
    print(f"[e4c] clause_vec_qwen={n512} / clause_vec_qwen1024={n1024} / "
          f"仅512={only512} / 仅1024={only1024}", flush=True)
    if not (n512 == n1024 and only512 == 0 and only1024 == 0):
        print("⛔ 两臂候选集合不一致 ⇒ 整次作废（stop-loss hard_fail）")
        return 1

    tok = AutoTokenizer.from_pretrained(MODEL_ID, padding_side="left")
    model = AutoModel.from_pretrained(MODEL_ID, dtype=torch.float16).to("cuda").eval()

    def qvec(text: str, dim: int):
        enc = tok([text], padding=True, truncation=True, max_length=512,
                  return_tensors="pt").to("cuda")
        with torch.no_grad():
            out = model(**enc)
        v = Fn.normalize(out.last_hidden_state[:, -1][:, :dim], p=2, dim=1)
        return v[0].float().cpu().numpy().tolist()

    def knn(table: str, qv, k: int):
        t0 = time.perf_counter()
        ids = [r[0] for r in conn.execute(
            f"SELECT clause_revision_id FROM {table}"
            " WHERE embedding MATCH ? AND k = ? ORDER BY distance",
            (array.array("f", qv).tobytes(), k))]
        return ids, (time.perf_counter() - t0) * 1000.0

    v2 = [json.loads(l) for l in (ROOT / "eval" / "recall-funnel" / "benchmark-v2.jsonl")
          .read_text(encoding="utf-8").splitlines() if l.strip()]
    v3 = {json.loads(l)["i"]: json.loads(l)
          for l in (ROOT / "eval" / "recall-funnel" / "benchmark-v3.jsonl")
          .read_text(encoding="utf-8").splitlines() if l.strip()}
    r1 = {json.loads(l)["i"]: json.loads(l)
          for l in (R1 / "ab-per-query.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}

    rows = []
    lat = {"d512": [], "d1024": []}
    t0 = time.perf_counter()
    for n, it in enumerate(v2, 1):
        q = it["query"]
        gold = it["v2"]["gold_cr_id"]
        mf = extract_modality_from_query(q)
        exact = F.channel_exact(conn, q)
        fts1000 = F.channel_fts(conn, q, K)
        fts20 = F.channel_fts(conn, q, 20)
        modality = F.channel_modality(conn, mf)

        vec512, ms512 = knn("clause_vec_qwen", qvec(q, D512), K)
        vec1024, ms1024 = knn("clause_vec_qwen1024", qvec(q, D1024), K)
        lat["d512"].append(ms512); lat["d1024"].append(ms1024)

        rec = {"i": it["i"],
               "headline": bool(it["v2"]["bucket"] == "keep"
                                and not ({"gold_multi_def", "gold_dup_text"} & set(it["v2"]["flags"]))),
               "kind": it["kind"], "tier": v3[it["i"]]["v3"]["req_tier"]}
        for arm, vec in (("d512", vec512), ("d1024", vec1024)):
            a = {"vec_n": len(vec)}
            for d in (20, 100, 1000):
                union_d = set(exact[:d]) | set(fts1000[:d]) | set(modality[:d]) | set(vec[:d])
                a[f"rank@{d}"] = F.rank_of(gold, vec[:d])
                a[f"union_same@{d}"] = gold in union_d
                a[f"fts@{d}"] = gold in set(fts1000[:d])
            a["union_prod"] = gold in (set(exact) | set(fts20) | set(modality) | set(vec[:20]))
            rec[arm] = a
        rows.append(rec)
        if n % 20 == 0:
            print(f"[e4c] {n}/{len(v2)}  {time.perf_counter()-t0:.0f}s", flush=True)

    def rate(sub, arm, key):
        return round(sum(1 for r in sub if r[arm][key]) / len(sub), 4) if sub else None

    def blk(sub):
        s = {"n": len(sub), "n_clusters": len({v3[r["i"]]["v2"]["gold_cr_id"] for r in sub})}
        for arm in ("d512", "d1024"):
            s[arm] = {k: rate(sub, arm, k) for k in
                      ("rank@20", "rank@100", "rank@1000", "union_same@20", "union_same@100",
                       "union_same@1000", "union_prod", "fts@1000")}
        s["delta_pp"] = {k: round((s["d1024"][k] - s["d512"][k]) * 100, 2) for k in s["d512"]}
        s["flip_rank@1000"] = {
            "in": sum(1 for r in sub if not r["d512"]["rank@1000"] and r["d1024"]["rank@1000"]),
            "out": sum(1 for r in sub if r["d512"]["rank@1000"] and not r["d1024"]["rank@1000"]),
        }
        return s

    def pct(xs, p):
        xs = sorted(xs)
        return round(xs[min(len(xs) - 1, int(p * len(xs)))], 1)

    head = [r for r in rows if r["headline"]]
    summary = {"all_171": blk(rows), "headline_120": blk(head)}

    mism = [r["i"] for r in rows
            if r["i"] in r1 and r["d512"]["rank@1000"] != r1[r["i"]]["ctx"]["rank@1000"]]
    fts_mism = sum(1 for r in rows if r["d512"]["fts@1000"] != r["d1024"]["fts@1000"])

    result = {
        "experiment": "E4c：Qwen3-Embedding-0.6B 升维（512 → 1024 维，同模型、无前缀）",
        "single_variable": "输出维度（512 截断+重归一化 vs 原生 1024）；条文文本与模型一字不动",
        "primary_endpoint": "Vector @1000（主结果 120 条口径）",
        "summary": summary,
        "instrument_control": {
            "round1_selfcheck_mismatch_items": len(mism),
            "round1_selfcheck_mismatch_i": mism[:20],
            "meaning_1": "d512 臂必须逐条复现 E4 第一轮 ctx 臂的 rank@1000；非 0 ⇒ 先查仪器，"
                         "**不许**把它读成『升维有效/无效』",
            "fts_mismatch_items": fts_mism,
            "meaning_2": "FTS 两臂必须完全相同（升维不进 FTS）；非 0 ⇒ 泄漏了",
            "vec_set_bidirectional_except": {"only_512": only512, "only_1024": only1024},
        },
        "cost_knn_scan_ms": {
            "d512": {"p50": pct(lat["d512"], 0.50), "p90": pct(lat["d512"], 0.90),
                     "mean": round(sum(lat["d512"]) / len(lat["d512"]), 1)},
            "d1024": {"p50": pct(lat["d1024"], 0.50), "p90": pct(lat["d1024"], 0.90),
                      "mean": round(sum(lat["d1024"]) / len(lat["d1024"]), 1)},
            "corpus_rows": n512,
            "meaning": "同一 521,978 行语料上 KNN @1000 的实测延迟 ⇒ 升维的代价侧读数",
        },
        "baseline_selfcheck": {"round1_ctx_headline_vec@1000": 0.6833,
                               "round1_ctx_all_vec@1000": 0.6667},
        "elapsed_s": round(time.perf_counter() - t0, 1),
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    OUT_PER.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1))
    print(f"\n已写 {OUT}\n已写 {OUT_PER}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
