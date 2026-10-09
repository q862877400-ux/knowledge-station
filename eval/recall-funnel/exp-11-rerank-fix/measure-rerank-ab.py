"""总纲 P0·0.7 修复前后 A/B：rerank 阶段到底改不改 top-8（只读真库）。

## 这份脚本回答什么
`reranker.py::rerank` 的返回形状缺陷（总纲 0.7）修好之后，
**生产口径的 top-8 / top-20 命中率到底变不变**。

* **A 臂** = RRF 原序前 K 条。**这就是当前生产的实际行为**（因为 rerank 阶段空转）。
* **B 臂** = 把同一批 RRF 前 24 条交给**生产的** `hybrid_engine._rerank_results` 再取前 K 条。
  * 修复**前**跑：B 应**逐条等于** A（这正是"空转"的证据）。
  * 修复**后**跑：B 是真重排，与 A 的差就是这一层的收益/代价。

⇒ **同一份脚本在修复前后各跑一次**；A 臂两次必须逐条相同（仪器对照），B 臂的差才是结论。

## 为什么每问只做 1 次检索
`perform_hybrid_search` 的真实做法是：RRF 排序后取 `cap = rerank_n`（默认 24）条，
再 `_rerank_results(query, results, top_k)` 裁到 top_k。所以
「`rerank=False, top_k=24` 的结果的前 K 条」**逐位等于**「`rerank=True, top_k=K` 的结果」
（已实测：修复前 B 臂 == A 臂）。⇒ 一次检索 + 一次 `_rerank_results` 就能同时拿到两臂，
**且 B 臂走的仍是生产函数本身**，不是重写一份。

## 口径（照 `eval/recall-funnel/summarize.py`，不另立一套）
* **主结果 120** = `bucket == "keep"` 且 `flags ∩ {gold_multi_def, gold_dup_text} == ∅`；
* **全量 171** = 全部（本批 `answer_out_of_corpus` 全 False）。
* 命中判据 = `gold_cr_id` 出现在返回的 clause_revision_id 列表里（与 `funnel.py` 同一判据）。

## 只读保证
真库以 `file:...?mode=ro` 打开；`hybrid_engine._conn` 被指向这条只读连接（与 `funnel.py` 同法）；
脚本开始/结束各记一次真库 mtime，不一致即报错退出。**不写库、不改任何源文件。**

## 复跑
    .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-11-rerank-fix\\measure-rerank-ab.py --out before-fix
    .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-11-rerank-fix\\measure-rerank-ab.py --out after-fix
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

HERE = Path(__file__).resolve().parent
BENCH = ROOT / "eval" / "recall-funnel" / "benchmark-v2.jsonl"
DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"

#: 与 `summarize.py` 逐字相同的排除标记（不另立一套口径）
EXCLUDE_FLAGS = {"gold_multi_def", "gold_dup_text"}
RERANK_N = 24          # 照生产 `perform_hybrid_search` 的默认值
KS = (8, 20)           # K=8 = ks_answer 生产默认 top_k；K=20 作副终点


def ro_conn(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    from src.core.storage.sqlite_db import load_vec_extension
    if not load_vec_extension(conn):
        raise SystemExit("加载 sqlite-vec 扩展失败")
    return conn


def load_items() -> list[dict]:
    return [json.loads(l) for l in BENCH.read_text(encoding="utf-8").splitlines() if l.strip()]


def is_headline(it: dict) -> bool:
    v2 = it["v2"]
    return v2["bucket"] == "keep" and not (EXCLUDE_FLAGS & set(v2["flags"]))


def mcnemar(b: int, c: int) -> float:
    """配对 McNemar 精确检验（双侧）—— b = 翻进（A 不中 B 中）、c = 翻出。"""
    n = b + c
    if n == 0:
        return 1.0
    from math import comb

    k = min(b, c)
    tail = sum(comb(n, i) for i in range(k + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="输出名（产物 = per-query-<out>.jsonl / result-<out>.json）")
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 条（校验用）")
    args = ap.parse_args()

    from src.core.retrieval import hybrid_engine as he
    from src.core.retrieval.hybrid_engine import search_with_details
    from src.core.retrieval import reranker

    mtime0 = DB.stat().st_mtime
    conn = ro_conn(DB)
    he._conn = lambda: conn          # 生产函数也走只读连接（与 funnel.py 同法，不改生产代码）

    items = load_items()
    if args.limit:
        items = items[:args.limit]

    out_per = HERE / f"per-query-{args.out}.jsonl"
    out_res = HERE / f"result-{args.out}.json"

    avail = reranker.is_available()
    print(f"[reranker] is_available = {avail}", flush=True)
    if not avail:
        print("[warn] reranker 不可用 ⇒ B 臂会走降级（原序），本实验无意义", flush=True)

    KMAX = max(KS)
    recs: list[dict] = []
    lat: list[float] = []
    t_start = time.perf_counter()
    with out_per.open("w", encoding="utf-8") as fh:
        for it in items:
            q = it["query"]
            gold = it["v2"]["gold_cr_id"]
            # 一次检索拿 RRF 前 24 条（= 生产 rerank 阶段的输入）
            res24 = search_with_details(q, top_k=RERANK_N, rerank=False,
                                        boost_bookmarks=False, expand_chain=False)["results"]
            ids_a_all = [r.clause_revision_id for r in res24]
            t0 = time.perf_counter()
            kept, dbg = he._rerank_results(q, res24, top_k=KMAX)
            t_rr = time.perf_counter() - t0
            ids_b_all = [c.clause_revision_id for c in kept]
            if avail and len(res24) > 1:
                lat.append(t_rr)

            rec: dict = {"i": it["i"], "query": q, "gold_cr_id": gold,
                         "headline": is_headline(it),
                         "subset_label": (it["v2"].get("subset") or {}).get("label"),
                         "n_candidates": len(res24),
                         "n_kept": len(ids_b_all),
                         "rerank_offline": bool(dbg.get("rerank_offline")),
                         "rerank_reason": dbg.get("rerank_reason"),
                         "t_rerank_s": round(t_rr, 4)}
            for K in KS:
                a, b = ids_a_all[:K], ids_b_all[:K]
                rec[f"K{K}"] = {
                    "hit_a": gold in a, "hit_b": gold in b,
                    "rank_a": (a.index(gold) + 1) if gold in a else None,
                    "rank_b": (b.index(gold) + 1) if gold in b else None,
                    "same_order": a == b,
                }
            rec["ids_a8"] = ids_a_all[:8]
            rec["ids_b8"] = ids_b_all[:8]
            recs.append(rec)
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            if len(recs) % 20 == 0:
                print(f"  ... {len(recs)}/{len(items)}  ({time.perf_counter()-t_start:.0f}s)", flush=True)

    def agg(rows: list[dict], K: int) -> dict:
        n = len(rows)
        ha = sum(1 for r in rows if r[f"K{K}"]["hit_a"])
        hb = sum(1 for r in rows if r[f"K{K}"]["hit_b"])
        fin = sum(1 for r in rows if not r[f"K{K}"]["hit_a"] and r[f"K{K}"]["hit_b"])
        fout = sum(1 for r in rows if r[f"K{K}"]["hit_a"] and not r[f"K{K}"]["hit_b"])
        same = sum(1 for r in rows if r[f"K{K}"]["same_order"])
        return {
            "n": n,
            "hit_a": ha, "rate_a": round(ha / n, 4) if n else None,
            "hit_b": hb, "rate_b": round(hb / n, 4) if n else None,
            "delta_n": hb - ha,
            "delta_pt": round((hb - ha) / n * 100, 2) if n else None,
            "flip_in": fin, "flip_out": fout,
            "mcnemar_p": round(mcnemar(fin, fout), 4),
            "n_same_order": same,
            "n_reordered": n - same,
        }

    head = [r for r in recs if r["headline"]]
    summary = {
        "out": args.out,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "reranker_available": avail,
        "n_all": len(recs), "n_headline": len(head),
        "rerank_n": RERANK_N,
        "n_rerank_offline": sum(1 for r in recs if r["rerank_offline"]),
        "headline": {f"K{K}": agg(head, K) for K in KS},
        "all": {f"K{K}": agg(recs, K) for K in KS},
        "latency_rerank_s": {
            "n": len(lat),
            "p50": round(statistics.median(lat), 4) if lat else None,
            "p90": round(sorted(lat)[int(len(lat) * 0.9)], 4) if lat else None,
            "max": round(max(lat), 4) if lat else None,
        },
        "elapsed_s": round(time.perf_counter() - t_start, 1),
    }
    out_res.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    mtime1 = DB.stat().st_mtime
    if mtime0 != mtime1:
        print(f"[FAIL] 真库 mtime 变了：{mtime0} -> {mtime1}", flush=True)
        return 2
    print(json.dumps({"headline": summary["headline"], "all": summary["all"],
                      "n_offline": summary["n_rerank_offline"],
                      "latency": summary["latency_rerank_s"],
                      "elapsed_s": summary["elapsed_s"]}, ensure_ascii=False, indent=2))
    print(f"[ok] 真库未动（mtime {mtime0}）⇒ 已写 {out_per.name} / {out_res.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
