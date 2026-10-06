"""E3b · 跑两臂对照（**留一法**：选术语前剔除 gold 条款）。

与 E3 的差别**只有一处**：术语选择前把该条的 gold 条款从候选里剔掉（见 README 与
`../exp-3-query-side/VOID-hardfail-record.md`）。其余（通道口径、并集定义、主终点、阈值）**一字不改**。

另外量一个 E3 没量的**诊断量**：不做留一法时，被选中术语中"定义条款就是 gold"的有多少个
—— 它量化了 E3 本来会有多少泄漏。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-3b-query-side-loo\\01-run-e3b.py
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
sys.path.insert(0, str(ROOT / "eval" / "recall-funnel"))
EXP = HERE.parent / "exp-3-query-side" / "exp.db"      # 与 E3 共用同一份副本
CACHE = ROOT / "var" / "tmp" / "term-index-full.json"
OUT = HERE / "e3b-result.json"
OUT_PER = HERE / "e3b-per-query.jsonl"
K_TERMS = 5
K_BUFFER = 8          # 多取几个再过滤，等价于"先过滤索引再 top-k"


def main() -> int:
    import funnel as F
    from src.core.retrieval import embedder
    from src.core.retrieval.term_bridge import TermIndex, topk_by_cos
    from src.core.retrieval.hybrid_engine import extract_modality_from_query
    from src.core.storage.sqlite_db import load_vec_extension

    if not CACHE.exists():
        print(f"⛔ 术语索引不存在：{CACHE}")
        return 1
    index = TermIndex.load(CACHE)
    mat = index._matrix()
    print(f"[e3b] 术语索引 {len(index)} 个术语；留一法 K={K_TERMS}（缓冲 {K_BUFFER}）", flush=True)

    conn = sqlite3.connect(f"file:{EXP.as_posix()}?mode=ro", uri=True)
    if not load_vec_extension(conn):
        print("⛔ sqlite-vec 加载失败")
        return 1

    v2 = [json.loads(l) for l in (ROOT / "eval" / "recall-funnel" / "benchmark-v2.jsonl")
          .read_text(encoding="utf-8").splitlines() if l.strip()]

    rows, direct_full_n, direct_loo_n = [], 0, 0
    t0 = time.perf_counter()
    for n, it in enumerate(v2, 1):
        q = it["query"]
        gold = it["v2"]["gold_cr_id"]
        qv = embedder.embed_query(q)
        k_buf = max(1, min(len(index.entries), K_TERMS + K_BUFFER))
        idxs = topk_by_cos(qv, index.vectors, k_buf, mat)
        picks_full = [index.entries[i] for i in idxs][:K_TERMS]
        picks_loo = [index.entries[i] for i in idxs
                     if index.entries[i].clause_revision_id != gold][:K_TERMS]
        direct_full = sum(1 for e in picks_full if e.clause_revision_id == gold)
        direct_loo = sum(1 for e in picks_loo if e.clause_revision_id == gold)
        direct_full_n += direct_full
        direct_loo_n += direct_loo
        added = [e.term for e in picks_loo]
        q_exp = q + " " + " ".join(added) if added else q

        rec = {"i": it["i"],
               "headline": bool(it["v2"]["bucket"] == "keep"
                                and not ({"gold_multi_def", "gold_dup_text"} & set(it["v2"]["flags"]))),
               "kind": it["kind"], "added_terms": added,
               "direct_hit_full": direct_full, "direct_hit_loo": direct_loo}
        mf = extract_modality_from_query(q)

        for arm, qq in (("base", q), ("ctx", q_exp)):
            exact = F.channel_exact(conn, qq)
            fts1000 = F.channel_fts(conn, qq, 1000)
            fts20 = F.channel_fts(conn, qq, 20)
            modality = F.channel_modality(conn, mf)
            vec = F.channel_vec(conn, qq, 1000)
            a = {"vec_n": len(vec), "added_n": len(added)}
            for d in (20, 100, 1000):
                union_d = (set(exact[:d]) | set(fts1000[:d]) | set(modality[:d]) | set(vec[:d]))
                a[f"rank@{d}"] = F.rank_of(gold, vec[:d])
                a[f"gold_hit@{d}"] = bool(F.rank_of(gold, vec[:d]))
                a[f"union_same@{d}"] = gold in union_d
                a[f"fts@{d}"] = gold in set(fts1000[:d])
            a["union_prod"] = gold in (set(exact) | set(fts20) | set(modality) | set(vec[:20]))
            rec[arm] = a
        rows.append(rec)
        if n % 20 == 0:
            print(f"[e3b] {n}/{len(v2)}  {time.perf_counter()-t0:.0f}s", flush=True)

    def rate(sub, arm, key):
        return round(sum(1 for r in sub if r[arm][key]) / len(sub), 4) if sub else None

    head = [r for r in rows if r["headline"]]
    summary = {}
    for label, sub in (("all_171", rows), ("headline_120", head)):
        s = {"n": len(sub)}
        for arm in ("base", "ctx"):
            s[arm] = {k: rate(sub, arm, k) for k in
                      ("rank@20", "rank@100", "rank@1000", "gold_hit@20", "gold_hit@100",
                       "gold_hit@1000", "union_same@20", "union_same@100",
                       "union_same@1000", "union_prod", "fts@20", "fts@100", "fts@1000")}
        s["delta_pp"] = {k: round((s["ctx"][k] - s["base"][k]) * 100, 2) for k in s["base"]}
        s["flip_union@1000"] = {
            "in": sum(1 for r in sub if not r["base"]["union_same@1000"] and r["ctx"]["union_same@1000"]),
            "out": sum(1 for r in sub if r["base"]["union_same@1000"] and not r["ctx"]["union_same@1000"]),
        }
        summary[label] = s

    result = {
        "experiment": "E3b 查询侧术语桥扩展（留一法）",
        "why_loo": "E3 的防作弊判据写错（结构性重合当成逐条泄漏）⇒ E3 作废；本版选术语前剔除 gold 条款",
        "single_variable": "只改送进检索的查询串（原查询 vs 原查询 + 留一法术语桥 top-5 术语名）",
        "k_terms": K_TERMS, "k_buffer": K_BUFFER,
        "primary_endpoint": "六路同预算并集 @1000（全量 171 口径）",
        "baseline_selfcheck": {"funnel_all_union@1000": 0.3918, "funnel_headline_union@1000": 0.4,
                               "funnel_all_vec@1000": 0.345, "funnel_headline_vec@1000": 0.3583},
        "summary": summary,
        "leak_diagnostic": {
            "direct_hit_full_index": direct_full_n,
            "direct_hit_loo": direct_loo_n,
            "meaning": ("`direct_hit_full_index` = **不做留一法**时，被选中术语中『定义条款就是 gold』的个数"
                        "（= E3 本来会有的泄漏量）；`direct_hit_loo` **必须为 0**（硬失败条件）。"),
        },
        "elapsed_s": round(time.perf_counter() - t0, 1),
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    OUT_PER.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "summary"}, ensure_ascii=False, indent=1))
    for label, s in summary.items():
        print(f"\n[{label}] n={s['n']} union@1000 {s['base']['union_same@1000']}→{s['ctx']['union_same@1000']}"
              f"（{s['delta_pp']['union_same@1000']:+}pt，进{s['flip_union@1000']['in']}/出{s['flip_union@1000']['out']}）")
    print(f"\n已写 {OUT}\n已写 {OUT_PER}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
