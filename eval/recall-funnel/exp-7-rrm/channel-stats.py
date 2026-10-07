"""查一件事：本次考卷上，四个通道各触发多少次、候选池多大。

## 为什么要查
实验结果是「A≡B（权重无影响）」且「@20 四臂完全相同」。
在解释之前必须先排除一个平凡原因：**加权的那两路（exact 2.0 / modality 0.8）根本没触发**，
那样"权重无影响"就只是"权重没被用到"，而不是"权重不重要"。
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval" / "recall-funnel"))

from src.core.retrieval import hybrid_engine as he  # noqa: E402
from src.core.retrieval.hybrid_engine import extract_modality_from_query  # noqa: E402
from src.core.text_utils import standard_key  # noqa: E402
import funnel  # noqa: E402

DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"
BENCH = ROOT / "eval" / "recall-funnel" / "benchmark-v2.jsonl"
OUT = ROOT / "eval" / "recall-funnel" / "exp-7-rrm" / "channel-stats.json"

conn = funnel.ro_conn(DB)
he._conn = lambda: conn

items = [json.loads(l) for l in BENCH.read_text(encoding="utf-8").splitlines() if l.strip()]
items = [it for it in items
         if (it.get("v2") or {}).get("bucket") == "keep"
         and not ({"gold_multi_def", "gold_dup_text"} & set((it.get("v2") or {}).get("flags", [])))]
std_of_key = {standard_key(r[0]): r[0] for r in conn.execute("SELECT standard_no FROM doc_meta")}
gold_cr = {}
for it in items:
    std = std_of_key[standard_key(it["gold_std"])]
    gold_cr[it["i"]] = conn.execute(
        "SELECT cr.clause_revision_id FROM clause_revision cr JOIN doc_meta dm ON dm.doc_id=cr.doc_id"
        " WHERE dm.standard_no=? AND cr.clause_number=?", (std, it["gold_clause"])).fetchone()[0]

fire = {c: 0 for c in ("exact", "fts", "vec", "modality")}
sizes = {c: [] for c in fire}
gold_in = {c: 0 for c in fire}
pool = []
for it in items:
    q = it["query"]
    g = gold_cr[it["i"]]
    mf = extract_modality_from_query(q)
    rk = {
        "exact": funnel.channel_exact(conn, q),
        "fts": funnel.channel_fts(conn, q, 20),
        "vec": funnel.channel_vec(conn, q, 20),
        "modality": funnel.channel_modality(conn, mf),
    }
    u: set[str] = set()
    for c, lst in rk.items():
        if lst:
            fire[c] += 1
            sizes[c].append(len(lst))
            if g in lst:
                gold_in[c] += 1
        u |= set(lst)
    pool.append(len(u))

n = len(items)
print(f"[ch] 考卷 {n} 条\n")
print("  通道        触发次数      平均候选数    gold 在该通道内的次数")
for c in ("exact", "fts", "vec", "modality"):
    avg = (sum(sizes[c]) / len(sizes[c])) if sizes[c] else 0.0
    print(f"  {c:10s}  {fire[c]:3d}/{n} ({fire[c]/n:5.1%})   {avg:8.1f}      {gold_in[c]:3d}/{n}")
print(f"\n  [ch] 融合候选池大小：均 {sum(pool)/len(pool):.1f}  中位 {sorted(pool)[len(pool)//2]}  "
      f"最大 {max(pool)}  最小 {min(pool)}")

OUT.write_text(json.dumps({
    "why": "查加权通道是否根本没触发（否则『权重无影响』是平凡结论）",
    "n": n,
    "fire": {c: [fire[c], round(fire[c] / n, 4)] for c in fire},
    "avg_size": {c: round(sum(sizes[c]) / len(sizes[c]), 1) if sizes[c] else 0.0 for c in fire},
    "gold_in_channel": {c: [gold_in[c], round(gold_in[c] / n, 4)] for c in fire},
    "pool": {"mean": round(sum(pool) / len(pool), 1), "median": sorted(pool)[len(pool) // 2],
             "max": max(pool), "min": min(pool)},
}, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"已写 {OUT}")
