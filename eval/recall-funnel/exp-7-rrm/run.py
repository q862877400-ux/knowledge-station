"""实验 7：融合算子 —— RRF（加权求和） vs RRM（取最大）。

## 这一刀测什么
RefWalk（arXiv 2605.29742）§5.5 说：**sum-based RRF「要求所有视图达成一致」，从而稀释专家信号**；
改用 **max-based RRM「保留最强的那个名次」** 更好。它是纯写代码、直对判据②、我们没试过的改动。

## 四个臂（每次只改一处，保证可归因）
  A  sum_c w_c/(60+rank_c+1)   ← 生产现状
  B  sum_c  1 /(60+rank_c+1)   ← 只去掉通道权重
  C  max_c  1 /(60+rank_c)     ← 去掉权重 + 换算子（= RefWalk 原样实现）
  D  max_c  w_c/(60+rank_c)    ← 只换算子（保留权重）

## ★ 口径复核（跑之前必须过，否则实验无效）
**A 臂必须能逐字复现生产 `search_with_details(rerank=False)` 的前 N 名。**
对不上 ⇒ 停，先查为什么，不许带着错口径往下跑。

## 口径（照 `eval/recall-funnel/exp-7-rrm/STOP-LOSS-融合算子.md.json` 冻结）
 · 生产问答路径的真实活路 = **exact / fts / vec / modality 四路**
   （`legal_element`/`behavior_scope` 在生产问答路径传空过滤 ⇒ 不检索：
    见 `eval/recall-funnel/funnel.py` 的注释「生产问答路径不传 subject_filter / behavior_scope_filter」）
 · `PROD_CAP = {exact: None, fts: 20, vec: 20, modality: None}`；`k=60`
 · **`rerank=False`**（与 `src/core/llm/ks_answer.py` 的默认一致 = 生产真实路径）
 · 时效过滤与生产一致（排除 superseded / withdrawn）；收藏加分为 0

## 只读
用 `mode=ro` 连接（**比"副本"更严**：物理上无法写）。**不改生产代码**。

用法：
  .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-7-rrm\\run.py --check      # 只做口径复核
  .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-7-rrm\\run.py             # 全量
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

DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"
BENCH_V2 = ROOT / "eval" / "recall-funnel" / "benchmark-v2.jsonl"
BENCH_V1 = ROOT / "eval" / "reverse-benchmark" / "benchmark-171.jsonl"

K = 60
#: 与 `hybrid_engine.CHANNEL_WEIGHTS` 逐字一致
W = {"exact": 2.0, "fts": 1.0, "vec": 1.0, "modality": 0.8}
PROD_CAP = {"exact": None, "fts": 20, "vec": 20, "modality": None}
#: **生产问答路径上真正会检索的四路**（另两路传空过滤）
LIVE = ("exact", "fts", "vec", "modality")
OUT = HERE / "result.json"


def ro_conn(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)


def fuse(rankings: dict[str, list[str]], arm: str) -> dict[str, float]:
    """四种融合。rankings[c] = 该通道按名次排好的 clause_revision_id 列表。"""
    sc: dict[str, float] = {}
    if arm in ("A", "B"):
        for c, lst in rankings.items():
            w = W[c] if arm == "A" else 1.0
            for rank, cid in enumerate(lst):
                sc[cid] = sc.get(cid, 0.0) + w / (K + rank + 1)
    else:  # C / D
        for c, lst in rankings.items():
            w = 1.0 if arm == "C" else W[c]
            for rank, cid in enumerate(lst):
                v = w / (K + rank)
                if v > sc.get(cid, 0.0):
                    sc[cid] = v
    return sc


def order(sc: dict[str, float], status: dict[str, str], top_n: int) -> list[str]:
    """按融合分降序，套生产同样的时效过滤，取前 top_n。

    ⚠ 生产的时效过滤在 `perform_hybrid_search` 里是
    `if not include_superseded and clause.legal_status in ("superseded","withdrawn"): continue`
    —— `legal_status` 来自 `doc_meta`（`fetch_full_clause` 的 JOIN），不是 `clause_revision`。
    """
    out: list[str] = []
    for cid in sorted(sc.keys(), key=lambda x: sc[x], reverse=True):
        st = status.get(cid)
        if st is None:
            continue
        if st in ("superseded", "withdrawn"):
            continue
        out.append(cid)
        if len(out) >= top_n:
            break
    return out


def rank_of(gold: str, lst: list[str]) -> int | None:
    try:
        return lst.index(gold) + 1
    except ValueError:
        return None


def mcnemar_exact(b: int, c: int) -> float:
    """精确 McNemar（双侧）：b/c 是不一致对的两种方向。"""
    from math import comb
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    tail = sum(comb(n, i) for i in range(0, k + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def boot_ci(clusters: list[list[int]], reps: int = 2000, seed: int = 20261007) -> tuple[float, float]:
    """cluster bootstrap（cluster = gold 文档）。clusters[i] = 该 cluster 内每条的 (a-b) 差。"""
    import random
    rnd = random.Random(seed)
    n = len(clusters)
    if n == 0:
        return (0.0, 0.0)
    diffs = []
    for _ in range(reps):
        pick = [clusters[rnd.randrange(n)] for _ in range(n)]
        flat = [x for cl in pick for x in cl]
        diffs.append(sum(flat) / len(flat) if flat else 0.0)
    diffs.sort()
    lo = diffs[int(0.025 * reps)]
    hi = diffs[int(0.975 * reps) - 1]
    return (lo * 100, hi * 100)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只做口径复核（A 臂 vs 生产）")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    from src.core.retrieval import hybrid_engine as he
    from src.core.retrieval.hybrid_engine import search_with_details, extract_modality_from_query
    from src.core.text_utils import standard_key

    # 复用 funnel.py 的通道副本（它们已被复核过与生产单通道一致）
    sys.path.insert(0, str(ROOT / "eval" / "recall-funnel"))
    import funnel  # type: ignore

    conn = funnel.ro_conn(DB)   # 复用 funnel 的只读连接（它已加载 sqlite-vec 扩展）
    he._conn = lambda: conn          # 生产函数跑在只读连接上（不改生产代码）
    print(f"[exp7] 库 = {DB}（mode=ro，物理不可写）", flush=True)

    src = BENCH_V2 if BENCH_V2.exists() else BENCH_V1
    items = [json.loads(l) for l in src.read_text(encoding="utf-8").splitlines() if l.strip()]
    items = [it for it in items
             if (it.get("v2") or {}).get("bucket") == "keep"
             and not ({"gold_multi_def", "gold_dup_text"} & set((it.get("v2") or {}).get("flags", [])))]
    if args.limit:
        items = items[:args.limit]
    print(f"[exp7] headline 考卷 = {len(items)} 条（bucket=keep 且无 gold_multi_def/gold_dup_text）", flush=True)

    std_of_key = {standard_key(r[0]): r[0] for r in conn.execute("SELECT standard_no FROM doc_meta")}
    gold_cr = {}
    for it in items:
        std_no = std_of_key[standard_key(it["gold_std"])]
        row = conn.execute(
            "SELECT cr.clause_revision_id FROM clause_revision cr"
            " JOIN doc_meta dm ON dm.doc_id=cr.doc_id"
            " WHERE dm.standard_no=? AND cr.clause_number=?",
            (std_no, it["gold_clause"])).fetchone()
        if row is None:
            raise RuntimeError(f"gold 找不到：{it['i']}")
        gold_cr[it["i"]] = row[0]

    depth = 1000
    print(f"[exp7] 候选池 = 生产上限口径 PROD_CAP={PROD_CAP}"
          f"（fts/vec 取前 20，exact/modality 不限量）", flush=True)

    #: clause_revision_id → legal_status（来自 doc_meta，与 `fetch_full_clause` 同源）
    status = {r[0]: r[1] for r in conn.execute(
        "SELECT cr.clause_revision_id, dm.legal_status FROM clause_revision cr"
        " JOIN doc_meta dm ON dm.doc_id=cr.doc_id")}
    print(f"[exp7] 预载 legal_status {len(status)} 条", flush=True)

    arms = ("A", "B", "C", "D")
    per_query: list[dict] = []
    t0 = time.perf_counter()
    for n, it in enumerate(items, 1):
        q = it["query"]
        gold = gold_cr[it["i"]]
        mfilter = extract_modality_from_query(q)
        # ⚠ **生产上限口径**（= 生产手里真正有的候选）：
        #    fts/vec 取前 `PROD_CAP` 条，exact/modality 不限量（照 `perform_hybrid_search`）。
        #    ⚠ 第一版我误用了 funnel 的「同预算口径」（每路取 1000），
        #      被口径复核抓住：A 臂与生产 0/10 一致。**预注册文件里写的本来就是 PROD_CAP。**
        rk: dict[str, list[str]] = {
            "exact": funnel.channel_exact(conn, q),
            "fts": funnel.channel_fts(conn, q, PROD_CAP["fts"]),
            "vec": funnel.channel_vec(conn, q, PROD_CAP["vec"]),
            "modality": funnel.channel_modality(conn, mfilter),
        }
        rec: dict = {"i": it["i"], "gold_std": it["gold_std"], "gold_clause": it["gold_clause"]}
        for arm in arms:
            sc = fuse(rk, arm)
            lst = order(sc, status, depth)
            rec[arm] = {f"@{d}": bool(rank_of(gold, lst) and rank_of(gold, lst) <= d)
                        for d in (8, 20, 5, 100)}
            rec[arm]["rank"] = rank_of(gold, lst)
        # ★ 口径复核：A 臂 vs 生产
        prod = search_with_details(q, top_k=20, rerank=False, channels=list(LIVE), boost_bookmarks=False)
        prod_ids = [r["clause_revision_id"] if isinstance(r, dict) else r.clause_revision_id
                    for r in (prod.get("results") or [])]
        a20 = order(fuse(rk, "A"), status, 20)
        rec["_check"] = {"prod_len": len(prod_ids), "A_len": len(a20),
                         "identical": prod_ids == a20}
        per_query.append(rec)
        if n % 20 == 0 or n == len(items):
            ok = sum(1 for r in per_query if r["_check"]["identical"])
            print(f"  [{n}/{len(items)}]  口径复核一致 {ok}/{n}  用时 {time.perf_counter()-t0:.0f}s",
                  flush=True)
        if args.check and n >= 10:
            break

    nchk = len(per_query)
    nok = sum(1 for r in per_query if r["_check"]["identical"])
    print(f"\n[exp7] ★ 口径复核：A 臂与生产 `search_with_details(rerank=False)` 前 20 名完全一致 "
          f"{nok}/{nchk} = {nok/nchk:.1%}", flush=True)
    bad = [r["i"] for r in per_query if not r["_check"]["identical"]][:10]
    if bad:
        print(f"[exp7] ⚠ 不一致的 query i = {bad}", flush=True)
    if args.check:
        return 0

    # ── 统计 ────────────────────────────────────────────────────────────────
    res: dict = {"n": len(per_query), "check_pass": f"{nok}/{nchk}", "k": K, "depth": depth,
                 "arms": {}, "fusion": {"A": "sum w/(k+r+1)", "B": "sum 1/(k+r+1)",
                                        "C": "max 1/(k+r)", "D": "max w/(k+r)"},
                 "live_channels": list(LIVE), "prod_cap": {k: v for k, v in PROD_CAP.items()},
                 "rerank": False}
    for d in (8, 20):
        for arm in arms:
            hits = [1 if r[arm][f"@{d}"] else 0 for r in per_query]
            res["arms"].setdefault(arm, {})[f"@{d}"] = round(sum(hits) / len(hits) * 100, 2)
    # 配对对比（以 A 为基准）
    res["vs_A"] = {}
    for d in (8, 20):
        a = [1 if r["A"][f"@{d}"] else 0 for r in per_query]
        for arm in ("B", "C", "D"):
            bvec = [1 if r[arm][f"@{d}"] else 0 for r in per_query]
            n01 = sum(1 for x, y in zip(a, bvec) if x == 0 and y == 1)   # A 错 arm 对
            n10 = sum(1 for x, y in zip(a, bvec) if x == 1 and y == 0)   # A 对 arm 错
            delta = (sum(bvec) - sum(a)) / len(a) * 100
            cl: dict[str, list[int]] = {}
            for r, x, y in zip(per_query, a, bvec):
                cl.setdefault(r["gold_std"], []).append(y - x)
            lo, hi = boot_ci(list(cl.values()))
            res["vs_A"][f"{arm}@{d}"] = {
                "delta_pt": round(delta, 2), "b_A错arm对": n01, "c_A对arm错": n10,
                "mcnemar_p": round(mcnemar_exact(n01, n10), 4),
                "ci95": [round(lo, 2), round(hi, 2)],
            }
    print("\n[exp7] ==== 命中率（%） ====")
    hdr = "  arm  " + "".join(f"@{d:>10}" for d in (8, 20))
    print(hdr)
    for arm in arms:
        print(f"   {arm}   " + "".join(f"{res['arms'][arm][f'@{d}']:>11.2f}" for d in (8, 20)))
    print("\n[exp7] ==== 相对 A（生产现状） ====")
    for dkey, v in sorted(res["vs_A"].items()):
        print(f"   {dkey:6s} Δ={v['delta_pt']:+6.2f}pt  b={v['b_A错arm对']:3d} c={v['c_A对arm错']:3d}"
              f"  p={v['mcnemar_p']:.4f}  CI95=[{v['ci95'][0]:+.2f},{v['ci95'][1]:+.2f}]")
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n[exp7] 已写 {OUT}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
