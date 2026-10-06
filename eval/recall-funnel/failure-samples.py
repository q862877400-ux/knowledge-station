"""失败样本留证：从"六路深读 1000 都没召回 gold"的问法里抽最多 50 条，把当时的候选原样存下。

**不改问题、不改判定** —— 只把"当时六路各返回了什么"冻结下来，供下一阶段人工/外部 AI 看。
每条保存：query / gold(标准号+条款号+原文) / 六路 Top20（带条文片段）/ 六路 Top100（只有键）
/ 当时的判定票 / 融合结果。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\failure-samples.py [--limit 50]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1]))

import funnel as F  # noqa: E402

PER = HERE / "funnel-per-query.jsonl"
BENCH_V2 = HERE / "benchmark-v2.jsonl"
OUT = HERE / "failure-samples.jsonl"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=50)
    args = ap.parse_args()

    per = [json.loads(l) for l in PER.read_text(encoding="utf-8").splitlines() if l.strip()]
    v2 = {json.loads(l)["i"]: json.loads(l)
          for l in BENCH_V2.read_text(encoding="utf-8").splitlines() if l.strip()}

    failed = sorted([r for r in per if not r["hit_in_deep_union"]], key=lambda r: r["i"])
    picked = failed[:args.limit]
    print(f"[samples] 六路深读 1000 全未命中 {len(failed)} 条；本次留证 {len(picked)} 条", flush=True)

    conn = F.ro_conn(F.DB)
    from src.core.retrieval.hybrid_engine import extract_modality_from_query

    def key_of(cid: str) -> str:
        r = conn.execute(
            "SELECT cr.clause_number, dm.standard_no FROM clause_revision cr"
            " JOIN doc_meta dm ON dm.doc_id=cr.doc_id WHERE cr.clause_revision_id=?",
            (cid,)).fetchone()
        return f"{r[1]} {r[0]}" if r else cid

    def snip(cid: str, n: int = 70) -> str:
        r = conn.execute("SELECT content_text FROM clause_revision WHERE clause_revision_id=?",
                         (cid,)).fetchone()
        return (r[0] or "").replace("\n", " ")[:n] if r else ""

    with OUT.open("w", encoding="utf-8") as fh:
        for k, r in enumerate(picked, 1):
            q = r["query"]
            mf = extract_modality_from_query(q)
            cand = {
                "exact": F.channel_exact(conn, q),
                "fts": F.channel_fts(conn, q, 1000),
                "vec": F.channel_vec(conn, q, 1000),
                "modality": F.channel_modality(conn, mf),
                "legal_element": [],
                "behavior_scope": [],
            }
            rec = {
                "i": r["i"],
                "query": q,
                "kind": r["kind"],
                "gold_std": r["gold_std"],
                "gold_clause": r["gold_clause"],
                "gold_text": v2[r["i"]].get("gold_text", ""),
                "votes": v2[r["i"]].get("votes"),
                "confidence": v2[r["i"]].get("confidence"),
                "modality_filter": mf,
                "fused": r["fused"],
                "fused_rerank8": r.get("fused_rerank8"),
                "fts_pool": r.get("fts_pool"),
                "channels": {
                    c: {
                        "n": len(cand[c]),
                        "top20": [{"key": key_of(x), "text": snip(x)} for x in cand[c][:20]],
                        "top100_keys": [key_of(x) for x in cand[c][:100]],
                    } for c in cand
                },
            }
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            if k % 10 == 0 or k == len(picked):
                print(f"[samples] {k}/{len(picked)}", flush=True)
    print(f"已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
