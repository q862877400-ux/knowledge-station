"""E4 · 步骤 2：两臂对照（唯一变量 = 嵌入模型）。

- **对照臂**：查询用现役 `fastembed bge-small`（**不加任何指令前缀**）嵌入 → KNN `clause_vec`
- **实验臂**：查询用 `Qwen3-Embedding-0.6B`（**同样不加指令前缀**）嵌入 → KNN `clause_vec_qwen`

⚠ 两臂**都不加查询指令前缀** —— 这是对冻结项「查询侧不动」的解释：
   本轮只换模型，不引入"指令 vs 无指令"这第二个变量。
   Qwen3 官方推荐的 `instruct: …\\nquery: …` 前缀**本轮不试**，留作第二刀（已写进 README 边界）。

固定五路（exact/fts/modality）**两臂完全相同**（查询串没变）⇒ 并集的差别**只可能来自向量那一路**。
因此固定五路**每条只算一次**，两臂共用。

`FTS@1000 两臂必须完全相同` —— 这是**仪器对照**（按字找与嵌入模型无关）；若不同说明动了不该动的东西。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-4-embedding-shadow\\02-ab-eval.py
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
EXP = HERE / "exp.db"
MODEL_ID = "Qwen/Qwen3-Embedding-0.6B"
OUT_DIM = 512
OUT = HERE / "ab-result.json"
OUT_PER = HERE / "ab-per-query.jsonl"
BY_KIND_OUT = HERE / "ab-by-kind.json"


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
    n_q = conn.execute("SELECT COUNT(*) FROM clause_vec_qwen").fetchone()[0]
    n_b = conn.execute("SELECT COUNT(*) FROM clause_vec").fetchone()[0]
    print(f"[e4] clause_vec={n_b} / clause_vec_qwen={n_q} {'✅' if n_q == n_b else '⛔ 不一致'}", flush=True)

    tok = AutoTokenizer.from_pretrained(MODEL_ID, padding_side="left")
    model = AutoModel.from_pretrained(MODEL_ID, dtype=torch.float16).to("cuda").eval()

    def qwen_query_vec(q: str):
        enc = tok([q], padding=True, truncation=True, max_length=512, return_tensors="pt").to("cuda")
        with torch.no_grad():
            out = model(**enc)
        v = Fn.normalize(out.last_hidden_state[:, -1][:, :OUT_DIM], p=2, dim=1)
        return v[0].float().cpu().numpy().tolist()

    def knn(table: str, qv, k: int):
        return [r[0] for r in conn.execute(
            f"SELECT clause_revision_id FROM {table}"
            " WHERE embedding MATCH ? AND k = ? ORDER BY distance",
            (array.array("f", qv).tobytes(), k))]

    v2 = [json.loads(l) for l in (ROOT / "eval" / "recall-funnel" / "benchmark-v2.jsonl")
          .read_text(encoding="utf-8").splitlines() if l.strip()]
    v3 = {json.loads(l)["i"]: json.loads(l)
          for l in (ROOT / "eval" / "recall-funnel" / "benchmark-v3.jsonl")
          .read_text(encoding="utf-8").splitlines() if l.strip()}

    rows = []
    t0 = time.perf_counter()
    for n, it in enumerate(v2, 1):
        q = it["query"]
        gold = it["v2"]["gold_cr_id"]
        mf = extract_modality_from_query(q)
        # ── 固定五路：两臂共用（查询串没变）──
        exact = F.channel_exact(conn, q)
        fts1000 = F.channel_fts(conn, q, 1000)
        fts20 = F.channel_fts(conn, q, 20)
        modality = F.channel_modality(conn, mf)

        rec = {"i": it["i"],
               "headline": bool(it["v2"]["bucket"] == "keep"
                                and not ({"gold_multi_def", "gold_dup_text"} & set(it["v2"]["flags"]))),
               "kind": it["kind"], "tier": v3[it["i"]]["v3"]["req_tier"]}
        # ── 向量路：两臂各用各的模型 ──
        vecs = {"base": knn("clause_vec", embedder.embed_query(q), 1000),
                "ctx": knn("clause_vec_qwen", qwen_query_vec(q), 1000)}
        for arm in ("base", "ctx"):
            vec = vecs[arm]
            a = {"vec_n": len(vec)}
            for d in (20, 100, 1000):
                union_d = set(exact[:d]) | set(fts1000[:d]) | set(modality[:d]) | set(vec[:d])
                a[f"rank@{d}"] = F.rank_of(gold, vec[:d])
                a[f"union_same@{d}"] = gold in union_d
                a[f"fts@{d}"] = gold in set(fts1000[:d])       # 仪器对照：两臂应完全相同
            a["union_prod"] = gold in (set(exact) | set(fts20) | set(modality) | set(vec[:20]))
            rec[arm] = a
        rows.append(rec)
        if n % 20 == 0:
            print(f"[e4] {n}/{len(v2)}  {time.perf_counter()-t0:.0f}s", flush=True)

    def rate(sub, arm, key):
        return round(sum(1 for r in sub if r[arm][key]) / len(sub), 4) if sub else None

    def blk(sub):
        s = {"n": len(sub), "n_clusters": len({v3[r["i"]]["v2"]["gold_cr_id"] for r in sub})}
        for arm in ("base", "ctx"):
            s[arm] = {k: rate(sub, arm, k) for k in
                      ("rank@20", "rank@100", "rank@1000", "union_same@20", "union_same@100",
                       "union_same@1000", "union_prod", "fts@20", "fts@100", "fts@1000")}
        s["delta_pp"] = {k: round((s["ctx"][k] - s["base"][k]) * 100, 2) for k in s["base"]}
        s["flip_rank@1000"] = {
            "in": sum(1 for r in sub if not r["base"]["rank@1000"] and r["ctx"]["rank@1000"]),
            "out": sum(1 for r in sub if r["base"]["rank@1000"] and not r["ctx"]["rank@1000"]),
        }
        return s

    head = [r for r in rows if r["headline"]]
    summary = {"all_171": blk(rows), "headline_120": blk(head)}
    # FTS 仪器对照
    fts_mismatch = sum(1 for r in rows
                       if any(r["base"][f"fts@{d}"] != r["ctx"][f"fts@{d}"] for d in (20, 100, 1000)))

    result = {
        "experiment": "E4 embedding shadow test（Qwen3-Embedding-0.6B, 512d）",
        "single_variable": "嵌入模型（条文文本一字不动；查询两臂都不加指令前缀）",
        "primary_endpoint": "Vector @1000（主结果 120 条口径）",
        "summary": summary,
        "instrument_control": {
            "fts_mismatch_items": fts_mismatch,
            "meaning": "FTS 两臂必须完全相同（按字找与嵌入模型无关）；非 0 ⇒ 先查仪器",
        },
        "baseline_selfcheck": {"funnel_headline_vec@1000": 0.3583, "funnel_all_vec@1000": 0.345,
                               "funnel_headline_union@1000": 0.4, "funnel_all_union@1000": 0.3918},
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
