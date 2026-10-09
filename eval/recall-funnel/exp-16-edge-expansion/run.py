"""exp-16：**引用边扩边对检索有没有用**（在**修后**的图上测）。

## 为什么现在才做

P5（多跳）一直被一条红线挡着：「边密度 ≥0.3–0.5 才谈多跳（现 0.026）」。而那句 0.026 是
**在修前的错图上**量的（引用边全挂到各文档最后一条条款身上，见 `docs/DEVELOPMENT-HISTORY.md §10.223`）。
图已于 2026-10-09 修好并重建（密度 **0.03465**、跨文档边仍 **0**、有任一边的条款占 **4.93%**）
⇒ **现在可以实测"扩边到底有没有用"**，不用再靠密度门槛外推。

## 量什么

考卷 171 条（`benchmark-v2.jsonl`）。对每条：

1. 跑**生产同款**六路检索（`perform_hybrid_search`，`rerank=False` —— 生产里重排是关的），
   取 fused **top-20**（答案层证据上限是 8，20 是给扩边留的余量）；
2. 从这 20 条出发，沿 `evidence_edge`（`status='active'`、**只走出边**）扩 **1 跳** / **2 跳**；
3. 看 **gold 条款**在不在：① 原 top-20；② 并上 1 跳邻居；③ 再并上 2 跳邻居。

**判据**：`hit@20` 有没有提升、以及**代价**（候选池涨多少）。

## 只读

真库 `mode=ro`；不改生产代码、不写库。**不复现**任何已有实验（E4/E9/exp-13/14/15 都没碰）。
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

DB = Path(os.path.expandvars(r"%APPDATA%\KnowledgeStation\database\knowledge.db"))
BENCH = ROOT / "eval" / "recall-funnel" / "benchmark-v2.jsonl"
OUT = Path(__file__).resolve().parent / "result.json"


def gold_ids(con, rows) -> dict[int, set[str]]:
    """把考卷的 (standard_no, clause_number) 解析成 clause_revision_id。"""
    out: dict[int, set[str]] = {}
    miss = 0
    for r in rows:
        std, num = r["gold_std"], str(r["gold_clause"])
        q = """SELECT cr.clause_revision_id FROM clause_revision cr
               JOIN doc_meta dm ON dm.doc_id = cr.doc_id
               WHERE dm.standard_no = ? AND cr.clause_number = ?"""
        ids = {x[0] for x in con.execute(q, (std, num))}
        if not ids:                      # 回退：standard_no 带后缀/写法差异
            q2 = q.replace("dm.standard_no = ?", "dm.standard_no LIKE ?")
            ids = {x[0] for x in con.execute(q2, (std + "%", num))}
        if not ids:
            miss += 1
        out[r["i"]] = ids
    print("gold 解析：命中 %d / %d（未解析 %d）" % (len(rows) - miss, len(rows), miss))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--topk", type=int, default=20)
    ap.add_argument("--hops", type=int, default=2)
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 条（0=全跑）")
    args = ap.parse_args(argv)

    from src.core.retrieval.hybrid_engine import perform_hybrid_search
    from src.core.storage.sqlite_db import get_db_connection, load_vec_extension

    con = get_db_connection()
    try:
        load_vec_extension(con)
    except Exception as exc:  # noqa: BLE001
        print("（向量扩展加载失败，向量路会缺席）：", exc)

    rows = [json.loads(l) for l in BENCH.read_text(encoding="utf-8").splitlines() if l.strip()]
    if args.limit:
        rows = rows[: args.limit]
    gold = gold_ids(con, rows)

    # 三个方向（出边 / 入边 / 双向）× 三档（基线 / 1 跳 / 2 跳）
    keys = [f"{t}{h}" for t in ("out", "in", "both") for h in (0, 1, 2)]
    hit = {k: 0 for k in keys}
    pool = {k: 0 for k in keys}
    per = []
    t0 = time.time()
    for n, r in enumerate(rows, 1):
        q = r["query"]
        try:
            res = perform_hybrid_search(q, top_k=args.topk, rerank=False)
        except Exception as exc:  # noqa: BLE001
            print("  检索失败 i=%s: %s" % (r["i"], exc))
            res = []
        base = [c.clause_revision_id for c in res]
        g = gold.get(r["i"], set())

        # 逐跳扩边（三个方向各算一遍：出边 / 入边 / 双向）
        def _step(frontier, seen, sql):
            nxt: list[str] = []
            if frontier:
                for i in range(0, len(frontier), 400):
                    chunk = frontier[i:i + 400]
                    qq = sql % ",".join("?" * len(chunk))
                    for (t,) in con.execute(qq, chunk):
                        if t not in seen:
                            seen.add(t)
                            nxt.append(t)
            return nxt

        SQL_OUT = ("SELECT target_clause_id FROM evidence_edge WHERE status='active'"
                   " AND source_clause_id IN (%s)")
        SQL_IN = ("SELECT source_clause_id FROM evidence_edge WHERE status='active'"
                  " AND target_clause_id IN (%s)")
        levels: dict[str, dict[int, set[str]]] = {}
        for tag, sqls in (("out", (SQL_OUT,)), ("in", (SQL_IN,)), ("both", (SQL_OUT, SQL_IN))):
            f, s = list(base), set(base)
            lv = {0: set(s)}
            for h in range(1, args.hops + 1):
                nxt = []
                for sql in sqls:
                    nxt += _step(f, s, sql)
                f = nxt
                lv[h] = set(s)
            levels[tag] = lv

        for tag in ("out", "in", "both"):
            for h in (0, 1, 2):
                if g & levels[tag][h]:
                    hit[f"{tag}{h}"] += 1
                pool[f"{tag}{h}"] += len(levels[tag][h])
        per.append({"i": r["i"],
                    **{f"{t}{h}": bool(g & levels[t][h]) for t in ("out", "in", "both") for h in (0, 1, 2)},
                    **{f"pool_{t}{h}": len(levels[t][h]) for t in ("out", "in", "both") for h in (0, 1, 2)}})
        if n % 20 == 0:
            print("  …%d/%d  base=%d  out2=%d  in2=%d  both2=%d"
                  % (n, len(rows), hit["out0"], hit["out2"], hit["in2"], hit["both2"]), flush=True)

    N = len(rows)
    print()
    print("=== 结果（考卷 %d 条，fused top-%d，rerank=False）===" % (N, args.topk))
    for tag, label in (("out", "只走出边"), ("in", "只走入边"), ("both", "双向")):
        b = hit[f"{tag}0"]
        h1, h2 = hit[f"{tag}1"], hit[f"{tag}2"]
        print("  %-8s 基线 %d (%.1f%%) → 1跳 %d (%+.1fpt) → 2跳 %d (%+.1fpt)  池 %.1f→%.1f→%.1f"
              % (label, b, 100.0 * b / N, h1, 100.0 * (h1 - b) / N, h2, 100.0 * (h2 - b) / N,
                 pool[f"{tag}0"] / N, pool[f"{tag}1"] / N, pool[f"{tag}2"] / N))
    print("  用时 %.1f s" % (time.time() - t0))

    OUT.write_text(json.dumps({
        "bench": str(BENCH), "n": N, "topk": args.topk, "hops": args.hops,
        "hit": hit, "pool_mean": {k: pool[k] / N for k in pool},
        "per_query": per}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("  written:", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
