"""确定性检查：同一套设置跑两次，结果必须逐字一样。

外部评估给的硬要求之一（"同一套设置跑两次结果要一样（不一样说明环境有问题，不是正常波动）"）。
本脚本对抽样的若干条问法**各跑两遍**，比较：
  · 六路各自的候选列表（含顺序）
  · 融合后的结果顺序（`perform_hybrid_search`，rerank=False）

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\determinism.py [--n 12]
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

V2 = HERE / "benchmark-v2.jsonl"
OUT = HERE / "determinism.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=12)
    args = ap.parse_args()

    from src.core.retrieval import hybrid_engine as he
    from src.core.retrieval.hybrid_engine import perform_hybrid_search, extract_modality_from_query

    items = [json.loads(l) for l in V2.read_text(encoding="utf-8").splitlines() if l.strip()]
    step = max(1, len(items) // args.n)
    picked = items[::step][:args.n]

    conn = F.ro_conn(F.DB)
    he._conn = lambda: conn

    def snapshot(q: str) -> dict:
        mf = extract_modality_from_query(q)
        return {
            "exact": F.channel_exact(conn, q),
            "fts20": F.channel_fts(conn, q, 20),
            "fts1000": F.channel_fts(conn, q, 1000),
            "vec20": F.channel_vec(conn, q, 20),
            "vec1000": F.channel_vec(conn, q, 1000),
            "modality": F.channel_modality(conn, mf),
            "fused": [r.clause_revision_id for r in perform_hybrid_search(
                q, top_k=100, rerank=False, boost_bookmarks=False,
                modality_filter=mf)],
        }

    bad = []
    for it in picked:
        a, b = snapshot(it["query"]), snapshot(it["query"])
        diff = [k for k in a if a[k] != b[k]]
        if diff:
            bad.append({"i": it["i"], "query": it["query"], "diff": diff,
                        "sizes": {k: (len(a[k]), len(b[k])) for k in diff},
                        "head_a": {k: a[k][:5] for k in diff},
                        "head_b": {k: b[k][:5] for k in diff}})
        print(f"[det] i={it['i']} {'一致' if not diff else '⚠ 不一致: ' + ','.join(diff)}", flush=True)

    result = {
        "meta": {"n_picked": len(picked), "source": str(V2),
                 "what": "六路候选列表 + 融合顺序，各跑两遍逐字比较"},
        "n_identical": len(picked) - len(bad),
        "n_different": len(bad),
        "samples": bad[:5],
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
