"""诊断：为什么 A 臂（加权求和 RRF）复现不了生产 `search_with_details(rerank=False)`。

分别检查：
 ① 集合差异还是仅次序差异；
 ② 收藏加分（生产默认 `boost_bookmarks=True`，而我重建时没加）；
 ③ 各通道候选集是否一致（funnel 副本 vs 生产单通道）。
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
from src.core.retrieval.hybrid_engine import search_with_details, perform_hybrid_search, extract_modality_from_query  # noqa: E402
from src.core.text_utils import standard_key  # noqa: E402
import funnel  # noqa: E402

DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"
BENCH = ROOT / "eval" / "recall-funnel" / "benchmark-v2.jsonl"
LIVE = ("exact", "fts", "vec", "modality")
K = 60
W = {"exact": 2.0, "fts": 1.0, "vec": 1.0, "modality": 0.8}

conn = funnel.ro_conn(DB)
he._conn = lambda: conn

# ② 收藏
try:
    from src.core.storage.user_data import bookmarked_clause_keys
    bm = bookmarked_clause_keys()
    print(f"[diag] ② 收藏数 = {len(bm)}")
except Exception as e:
    print(f"[diag] ② 收藏读取失败：{type(e).__name__}: {e}")

items = [json.loads(l) for l in BENCH.read_text(encoding="utf-8").splitlines() if l.strip()]
items = [it for it in items
         if (it.get("v2") or {}).get("bucket") == "keep"
         and not ({"gold_multi_def", "gold_dup_text"} & set((it.get("v2") or {}).get("flags", [])))]
std_of_key = {standard_key(r[0]): r[0] for r in conn.execute("SELECT standard_no FROM doc_meta")}

for it in items[:3]:
    q = it["query"]
    std_no = std_of_key[standard_key(it["gold_std"])]
    gold = conn.execute(
        "SELECT cr.clause_revision_id FROM clause_revision cr JOIN doc_meta dm ON dm.doc_id=cr.doc_id"
        " WHERE dm.standard_no=? AND cr.clause_number=?", (std_no, it["gold_clause"])).fetchone()[0]
    print(f"\n===== i={it['i']}  q={q[:48]!r} =====")

    # 生产（不带收藏加分）
    p_noboost = search_with_details(q, top_k=20, rerank=False, channels=list(LIVE),
                                    boost_bookmarks=False)
    p_boost = search_with_details(q, top_k=20, rerank=False, channels=list(LIVE))
    def ids(x):
        return [r["clause_revision_id"] if isinstance(r, dict) else r.clause_revision_id
                for r in (x.get("results") or [])]
    a_p = ids(p_noboost)
    b_p = ids(p_boost)
    print(f"  生产(不上收藏) top20 = {len(a_p)}  收藏影响: 与默认相同={a_p == b_p}")

    # 我的重建
    mfilter = extract_modality_from_query(q)
    rk = {
        "exact": funnel.channel_exact(conn, q),
        "fts": funnel.channel_fts(conn, q, 20),
        "vec": funnel.channel_vec(conn, q, 20),
        "modality": funnel.channel_modality(conn, mfilter),
    }
    for c in LIVE:
        print(f"    通道 {c:9s} 候选 {len(rk[c]):5d}  gold_rank={funnel.rank_of(gold, rk[c])}")
    sc = {}
    for c, lst in rk.items():
        for rank, cid in enumerate(lst):
            sc[cid] = sc.get(cid, 0.0) + W[c] / (K + rank + 1)
    mine = sorted(sc.keys(), key=lambda x: sc[x], reverse=True)[:20]
    print(f"  集合相同 = {set(mine) == set(a_p)}   次序相同 = {mine == a_p}")
    if set(mine) != set(a_p):
        print(f"    只在生产: {len(set(a_p)-set(mine))}  只在我: {len(set(mine)-set(a_p))}")
        # 生产侧 top 里，我这边排第几
        for cid in a_p[:5]:
            print(f"      生产#{a_p.index(cid)+1} 我这边 rank={mine.index(cid)+1 if cid in mine else '不在前20'}  score={sc.get(cid)}")
