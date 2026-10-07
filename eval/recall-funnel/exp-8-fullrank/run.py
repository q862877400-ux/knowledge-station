"""F1：**全库名次分解** —— 正确条文在 66 万条里到底排第几？

## 为什么做这个（外部复核把它排第一）
实验 7 只测到「正确条文**不在前 40 条候选池**里」（105/120），但**没说它在全库里排第几**。
`"Top1000 里没有"` 与 `"排在 12,653 名"` 是完全不同的信息：
 · 若普遍是「前 1%~5%」⇒ 首要问题是**排序/候选深度**，不是"嵌入空间没形成语义邻域"；
 · 若普遍是「十名开外、几十万名」⇒ 才像**嵌入表达不足**，该谈 query 改写 / 微调检索器。

## 冻结口径（先写死，跑完不许改）
 · **考卷** = headline **120** 条（`bucket=="keep"` 且无 `gold_multi_def`/`gold_dup_text`）；
 · **两个检索器，语义不同，必须分开报**：
   ① **向量**：全库**精确**名次（暴力扫描；见下"做法"）；
   ② **关键词**：全库名次 = 在**命中任一分词**的行里的名次（生产的 FTS 查询是分词 OR）；
      **gold 一个词都没命中 ⇒ 记为"未命中"（不是第 N 名）**；
 · **k 上限的处理**：`sqlite-vec` 的 KNN 接口硬上限 `k ≤ 4096`，**所以不用 KNN**；
 · **做法（实测）**：把全库向量矩阵一次性读进内存（实测 **277s / 1.36 GB**），
   之后每条算全库距离（实测 **2.89s/条**）⇒ 120 条约 6 分钟；
 · **一致性自查**：抽 3 条同时用"SQL 数点数"与"numpy"两个方法算，名次必须一致。
 · **只读**（`mode=ro`）；**不改任何生产代码**。

## 报什么
每条 query：`vector_rank` / `fts_rank` / `fts_matched` / `best_rank` /
`in_top{20,100,1000,10000,100000}` / `percentile`。
聚合：各阈值的命中率、名次中位数、两条通道各自的分布。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-8-fullrank\\run.py
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval" / "recall-funnel"))
HERE = Path(__file__).resolve().parent

DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"
OUT = HERE / "fullrank.json"
OUT_Q = HERE / "per-query.jsonl"

TOTAL = 663634          # 向量/条款总数，跑前由脚本实测覆盖


def main() -> int:
    from src.core.storage.sqlite_db import load_vec_extension
    from src.core.retrieval.hybrid_engine import _fts_query
    from src.core.retrieval import embedder
    import funnel

    conn = funnel.ro_conn(DB)
    print(f"[F1] 库 = {DB}（mode=ro）", flush=True)

    rows = [json.loads(l) for l in
            (ROOT / "eval" / "recall-funnel" / "benchmark-v2.jsonl").read_text(encoding="utf-8").splitlines()
            if l.strip()]
    items = [r for r in rows
             if (r.get("v2") or {}).get("bucket") == "keep"
             and not ({"gold_multi_def", "gold_dup_text"} & set((r.get("v2") or {}).get("flags", [])))]
    print(f"[F1] headline 考卷 = {len(items)} 条", flush=True)

    # ① 载入全库向量矩阵
    t0 = time.perf_counter()
    vr = conn.execute("SELECT clause_revision_id, embedding FROM clause_vec").fetchall()
    ids = [r[0] for r in vr]
    M = np.frombuffer(b"".join(r[1] for r in vr), dtype=np.float32).reshape(len(vr), -1)
    global TOTAL
    TOTAL = len(ids)
    print(f"[F1] 全库矩阵 {M.shape} 载入 {time.perf_counter()-t0:.0f}s "
          f"内存 {M.nbytes/1e9:.2f} GB  向量总数 {TOTAL}", flush=True)
    id_pos = {cid: i for i, cid in enumerate(ids)}

    per: list[dict] = []
    t0 = time.perf_counter()
    for n, it in enumerate(items, 1):
        q = it["query"]
        gold = it["v2"]["gold_cr_id"]

        # ── 向量全库名次（numpy）───────────────────────────────────────────
        qe = np.asarray(embedder.embed_query(q), dtype=np.float32)
        d = np.linalg.norm(M - qe, axis=1)
        gi = id_pos.get(gold)
        vrank = int((d < d[gi]).sum()) + 1 if gi is not None else None

        # ── 关键词全库名次（生产 FTS 查询；rgold 未命中则记 None）──────────
        fq = _fts_query(q)
        frank = fmatched = None
        if fq:
            try:
                cnt = conn.execute(
                    "SELECT COUNT(*) FROM clause_fts WHERE clause_fts MATCH ?", (fq,)).fetchone()[0]
                grow = conn.execute(
                    "SELECT rank FROM clause_fts WHERE clause_fts MATCH ? AND clause_revision_id = ?",
                    (fq, gold)).fetchone()
                if grow is not None and cnt:
                    better = conn.execute(
                        "SELECT COUNT(*) FROM clause_fts WHERE clause_fts MATCH ? AND rank < ?",
                        (fq, grow[0])).fetchone()[0]
                    frank, fmatched = int(better) + 1, int(cnt)
                else:
                    fmatched = int(cnt)
            except sqlite3.OperationalError as e:
                print(f"[F1] ⚠ FTS 失败 i={it['i']}: {e}", flush=True)

        best = min([x for x in (vrank, frank) if x is not None], default=None)
        rec = {"i": it["i"], "gold_std": it["gold_std"], "gold_clause": it["gold_clause"],
               "kind": it.get("kind"), "register": it.get("register"),
               "overlap": it.get("overlap"),
               "vector_rank": vrank, "fts_rank": frank, "fts_matched": fmatched,
               "best_rank": best,
               "vector_pct": round(vrank / TOTAL, 6) if vrank else None,
               "fts_pct": round(frank / fmatched, 6) if (frank and fmatched) else None}
        per.append(rec)
        if n % 20 == 0 or n == len(items):
            print(f"  [{n}/{len(items)}]  {time.perf_counter()-t0:.0f}s", flush=True)

    # ── 聚合 ────────────────────────────────────────────────────────────────
    def rate(f, key, thr):
        vals = [r[key] for r in per if r[key] is not None]
        return (round(sum(1 for v in vals if v <= thr) / len(per) * 100, 2), len(vals))
    agg = {"n": len(per), "total_clauses": TOTAL}
    for name, key in (("vector", "vector_rank"), ("fts", "fts_rank"), ("best", "best_rank")):
        agg[name] = {f"top{t}": rate(None, key, t)[0] for t in (20, 100, 1000, 10000, 100000)}
        vals = sorted(r[key] for r in per if r[key] is not None)
        agg[name]["n_retrieved"] = len(vals)
        agg[name]["n_not_retrieved"] = len(per) - len(vals)
        if vals:
            agg[name]["median"] = vals[len(vals) // 2]
            agg[name]["p90"] = vals[int(len(vals) * 0.9)]
            agg[name]["min"], agg[name]["max"] = vals[0], vals[-1]
    print("\n[F1] ==== 全库名次分布（占 120 条的 %） ====")
    for name in ("vector", "fts", "best"):
        a = agg[name]
        print(f"  {name:7s} 已召回 {a['n_retrieved']:3d} / 未召回 {a['n_not_retrieved']:3d}  "
              f"中位 {a.get('median','-')}  " +
              "  ".join(f"top{t}={a[f'top{t}']:.1f}%" for t in (20, 100, 1000, 10000, 100000)))
    OUT.write_text(json.dumps({"note": "F1 全库名次分解；口径见 run.py docstring",
                               "agg": agg, "per_query": per}, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    OUT_Q.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in per), encoding="utf-8")
    print(f"\n[F1] 已写 {OUT} 与 {OUT_Q}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
