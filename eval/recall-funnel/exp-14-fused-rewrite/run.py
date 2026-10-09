"""exp-14：把 exp-13 的三条**查询侧改写**接进**完整六路融合**，量 `fused@20`。

## 为什么做这个（不是新方向）
`exp-13` 只答了"改写能不能把 gold 捞进**向量路**的前 1000"；它自己在 §五 明写
**「只测向量路，不测 `fused@20`」**，并在 §四 只肯把 D1 判成"**向量路**净负"
—— 因为**产品实际给用户的是六路融合的前 20 条**。本批就是补上这一格：
**改写对"用户实际看到的 20 条"到底有没有用。**

## 唯一变量
送进**融合管线**的查询串（由 arm 决定）。索引 / 条文 / 向量表 / 生产代码**一个字不动**
—— 改写只在**本脚本里 monkeypatch** 生效（`embedder.embed_query` 与 `hybrid_engine._fts_query`）。

## 臂 → 查询串映射（**必须按通道分别施加**，否则不是"生产会怎么用"）
 * `A0_raw`              全通道原样（生产口径，基线）
 * `B1_bge_instruction`  **只**给向量通道的嵌入输入加 BGE 官方中文检索指令前缀（喂 FTS 无意义）
 * `C1_domain_prefix`    **只**给向量通道加自造领域前缀
 * `D1_prf_expand`       **向量 + FTS** 用扩展串（原样 + 语料内 PRF 扩展词）；精确/模态原样

`D1` 的扩展串**直接复用 exp-13 已冻结的 `per-query.jsonl` 里的 `d1_query`**（不重算）。

## 断点续跑（**必须**，否则会被工具 timeout 杀掉丢进度）
单次融合调用里 **sqlite-vec 的 KNN 就占 ~0.96 s**（暴力扫 663,634 行）⇒ 120 条 × 4 臂 ≈ **10 分钟**。
逐 `(i, arm)` 结果**边跑边 append + fsync** 到 `runs.jsonl`；被杀后重跑**自动跳过已完成项**。
收口：加 `--aggregate` 只做聚合（读 `runs.jsonl` → `result.json` + `per-query.jsonl`）。

## 仪器对照
`A0` 逐条 `fused.gold_rank` 必须与 `eval/recall-funnel/funnel-per-query.jsonl` 的同 `i` 记录
**0 处不同** —— 两者调的是同一条生产融合（`search_with_details(top_k=1000, rerank=False,
boost_bookmarks=False, expand_chain=False)`）。

## 只读保证
真库 `file:...?mode=ro`；不写库、不改任何源文件；脚本首尾各记一次库 mtime，不一致即报错退出。

用法：
    .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-14-fused-rewrite\\run.py            # 跑（可反复跑续跑）
    .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-14-fused-rewrite\\run.py --aggregate  # 只聚合
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval" / "recall-funnel"))
HERE = Path(__file__).resolve().parent

DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"
BENCH = ROOT / "eval" / "recall-funnel" / "benchmark-v2.jsonl"
FUNNEL_PER = ROOT / "eval" / "recall-funnel" / "funnel-per-query.jsonl"
E13_PER = ROOT / "eval" / "recall-funnel" / "exp-13-query-rewrite" / "per-query.jsonl"
RUNS = HERE / "runs.jsonl"          # 逐 (i, arm) 台账（append-only，续跑用）
OUT = HERE / "result.json"
OUT_Q = HERE / "per-query.jsonl"

ARMS = ("A0_raw", "B1_bge_instruction", "C1_domain_prefix", "D1_prf_expand")
THRESHOLDS = (20, 100, 1000)


def _load_e13():
    """复用 exp-13 的**纯函数**（不重写第二套）：arm_queries / hit_rate / median_rank /
    flip_counts / mcnemar_exact。"""
    spec = importlib.util.spec_from_file_location(
        "exp13_run", ROOT / "eval" / "recall-funnel" / "exp-13-query-rewrite" / "run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _headline(rows: list[dict]) -> list[dict]:
    return [
        r for r in rows
        if (r.get("v2") or {}).get("bucket") == "keep"
        and not ({"gold_multi_def", "gold_dup_text"} & set((r.get("v2") or {}).get("flags", [])))
    ]


def arm_vec_query(raw: str, arm: str, d1_query: str, e13) -> str:
    """★ 纯函数：该臂**送进向量通道**的查询串。"""
    if arm == "A0_raw":
        return raw
    if arm == "D1_prf_expand":
        return d1_query
    return e13.arm_queries(raw)[arm]


def arm_fts_query(raw: str, arm: str, d1_query: str) -> str:
    """★ 纯函数：该臂**送进 FTS 通道**的查询串。只有 D1 改 FTS（其余是前缀，喂 FTS 无意义）。"""
    return d1_query if arm == "D1_prf_expand" else raw


def _run(args) -> int:
    import funnel
    from src.core.retrieval import hybrid_engine as he
    from src.core.retrieval import embedder

    e13 = _load_e13()

    mtime0 = DB.stat().st_mtime
    conn = funnel.ro_conn(DB)
    he._conn = lambda: conn          # 让生产函数也在只读连接上跑（不改生产代码）

    items = _headline([json.loads(l) for l in BENCH.read_text(encoding="utf-8").splitlines()
                       if l.strip()])
    if args.limit:
        items = items[:args.limit]

    d1_map = {json.loads(l)["i"]: json.loads(l)["d1_query"]
              for l in E13_PER.read_text(encoding="utf-8").splitlines() if l.strip()}
    missing = [it["i"] for it in items if it["i"] not in d1_map]
    if missing:
        raise RuntimeError(f"exp-13 per-query.jsonl 缺这些 i：{missing[:5]}")

    done: set[tuple[int, str]] = set()
    if RUNS.exists():
        for l in RUNS.read_text(encoding="utf-8").splitlines():
            if l.strip():
                r = json.loads(l)
                done.add((r["i"], r["arm"]))

    todo = [(it, arm) for it in items for arm in ARMS if (it["i"], arm) not in done]
    print(f"[exp-14] 考卷 {len(items)} 条 × {len(ARMS)} 臂 = {len(items)*len(ARMS)} 格；"
          f"已完成 {len(done)}；本次待跑 {len(todo)}", flush=True)
    if not todo:
        print("[exp-14] 全部已完成，直接聚合", flush=True)
        return _aggregate(items, d1_map, e13)

    _orig_embed = embedder.embed_query
    _orig_fts = he._fts_query

    def _fused_ids(raw: str, arm: str, d1_query: str) -> list[str]:
        vec_q = arm_vec_query(raw, arm, d1_query, e13)
        fts_q = arm_fts_query(raw, arm, d1_query)

        def _embed(q):
            return _orig_embed(vec_q if q == raw else q)

        def _fts(q):
            return _orig_fts(fts_q if q == raw else q)

        embedder.embed_query = _embed
        he._fts_query = _fts
        try:
            found = he.search_with_details(raw, top_k=1000, rerank=False,
                                           boost_bookmarks=False, expand_chain=False)
        finally:
            embedder.embed_query = _orig_embed
            he._fts_query = _orig_fts
        return [r.clause_revision_id for r in found["results"]]

    t0 = time.perf_counter()
    with RUNS.open("a", encoding="utf-8") as fh:
        for n, (it, arm) in enumerate(todo, 1):
            raw, gold = it["query"], it["v2"]["gold_cr_id"]
            d1q = d1_map[it["i"]]
            fused = _fused_ids(raw, arm, d1q)
            rec = {"i": it["i"], "arm": arm, "query": raw, "gold_cr_id": gold,
                   "subset": (it.get("v2") or {}).get("subset", {}).get("label"),
                   "d1_query": d1q,
                   "vec_query": arm_vec_query(raw, arm, d1q, e13),
                   "fts_query": arm_fts_query(raw, arm, d1q),
                   "fused_n": len(fused),
                   "fused_rank": (fused.index(gold) + 1) if gold in fused else None}
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
            if n % 20 == 0 or n == len(todo):
                el = time.perf_counter() - t0
                print(f"[exp-14] {n}/{len(todo)} 用时 {el:.0f}s（{el/max(n,1):.2f}s/格）",
                      flush=True)

    mtime1 = DB.stat().st_mtime
    if mtime0 != mtime1:
        print(f"[exp-14] ⚠ 真库 mtime 变了：{mtime0} -> {mtime1}", flush=True)
        return 2
    return _aggregate(items, d1_map, e13)


def aggregate_runs(items: list[dict], d1_map: dict, runs_by_key: dict, e13) -> tuple[dict, list[dict]]:
    """★ 纯函数（单测直接喂合成台账）：从逐 `(i, arm)` 台账算聚合。

    `runs_by_key[(i, arm)]` = 该格记录（含 `fused_rank` / `fused_n` / `vec_query` / `fts_query`）。
    缺格即 `KeyError`（**不静默补 0** —— 缺格会让 @20 分母错）。
    """
    per_query: list[dict] = []
    arm_ranks: dict[str, list[int | None]] = {a: [] for a in ARMS}
    arm_pool: dict[str, list[int]] = {a: [] for a in ARMS}
    for it in items:
        row = {"i": it["i"], "query": it["query"], "gold_cr_id": it["v2"]["gold_cr_id"],
               "subset": (it.get("v2") or {}).get("subset", {}).get("label"),
               "d1_query": d1_map[it["i"]], "fused_rank": {}, "fused_n": {},
               "vec_query": {}, "fts_query": {}}
        for arm in ARMS:
            r = runs_by_key[(it["i"], arm)]
            row["fused_rank"][arm] = r["fused_rank"]
            row["fused_n"][arm] = r["fused_n"]
            row["vec_query"][arm] = r["vec_query"]
            row["fts_query"][arm] = r["fts_query"]
            arm_ranks[arm].append(r["fused_rank"])
            arm_pool[arm].append(r["fused_n"])
        per_query.append(row)

    labels = [r["subset"] for r in per_query]
    subset_names = sorted({x for x in labels if x})

    def by_subset(ranks, thr):
        out = {}
        for nm in subset_names:
            sub = [r for r, lb in zip(ranks, labels) if lb == nm]
            out[nm] = {"n": len(sub), "hit": e13.hit_rate(sub, thr)}
        return out

    agg: dict = {"n": len(items), "arms": {}}
    for arm in ARMS:
        r = arm_ranks[arm]
        rec = {f"fused_top{t}": e13.hit_rate(r, t) for t in THRESHOLDS}
        rec["fused_median_rank"] = e13.median_rank(r)
        rec["fused_hit_n"] = sum(1 for x in r if x is not None)
        rec["pool_median"] = sorted(arm_pool[arm])[len(arm_pool[arm]) // 2]
        rec["by_subset_top20"] = by_subset(r, 20)
        if arm != "A0_raw":
            base_hit = [x is not None and x <= 20 for x in arm_ranks["A0_raw"]]
            arm_hit = [x is not None and x <= 20 for x in r]
            b, c = e13.flip_counts(base_hit, arm_hit)
            rec["vs_A0_top20"] = {
                "delta_pt": round(rec["fused_top20"] - agg["arms"]["A0_raw"]["fused_top20"], 2),
                "flip_in": b, "flip_out": c,
                "mcnemar_p": round(e13.mcnemar_exact(b, c), 4),
            }
        agg["arms"][arm] = rec
    return agg, per_query


def _aggregate(items: list[dict], d1_map: dict, e13) -> int:
    runs: dict[tuple[int, str], dict] = {}
    for l in RUNS.read_text(encoding="utf-8").splitlines():
        if l.strip():
            r = json.loads(l)
            runs[(r["i"], r["arm"])] = r

    try:
        agg, per_query = aggregate_runs(items, d1_map, runs, e13)
    except KeyError as e:
        print(f"[exp-14] ⚠ 缺格 {e}，聚合中止", flush=True)
        return 3

    # 仪器对照：A0 逐条 fused 名次必须与 funnel-per-query.jsonl 一致
    fq = {}
    for l in FUNNEL_PER.read_text(encoding="utf-8").splitlines():
        if l.strip():
            rec = json.loads(l)
            fq[rec["i"]] = (rec.get("fused") or {}).get("gold_rank")
    mism = [(r["i"], fq.get(r["i"]), r["fused_rank"]["A0_raw"])
            for r in per_query if fq.get(r["i"]) != r["fused_rank"]["A0_raw"]]
    agg["instrument_check"] = {
        "source": "eval/recall-funnel/funnel-per-query.jsonl（fused.gold_rank）",
        "compared": len(per_query),
        "mismatch_count": len(mism),
        "mismatch_samples": mism,
        "note": "A0 逐条 fused.gold_rank 必须 0 处不同",
    }

    print("\n[exp-14] ==== 结果（fused = 生产六路融合）====")
    for arm in ARMS:
        a = agg["arms"][arm]
        extra = ""
        if arm != "A0_raw":
            v = a["vs_A0_top20"]
            extra = (f"  Δ@20={v['delta_pt']:+.2f}pt 进{v['flip_in']}/出{v['flip_out']}"
                     f" p={v['mcnemar_p']}")
        print(f"  {arm:20s} fused@20={a['fused_top20']:5.2f}%  @100={a['fused_top100']:5.2f}%  "
              f"@1000={a['fused_top1000']:5.2f}%  中位={a['fused_median_rank']}"
              f"  池中位={a['pool_median']}{extra}")
    print(f"  仪器对照：A0 与 funnel-per-query.jsonl 不同 = {len(mism)} 处 / {len(per_query)}")

    OUT.write_text(json.dumps(
        {"note": "exp-14 把 exp-13 的三条改写接进六路融合量 fused@20；口径见 run.py docstring 与 stop-loss.json",
         "agg": agg}, ensure_ascii=False, indent=1), encoding="utf-8")
    with OUT_Q.open("w", encoding="utf-8") as f:
        for r in per_query:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n[exp-14] 已写 {OUT} 与 {OUT_Q}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 条（校验用）")
    ap.add_argument("--aggregate", action="store_true", help="只聚合 runs.jsonl，不跑")
    args = ap.parse_args()
    if args.aggregate:
        e13 = _load_e13()
        items = _headline([json.loads(l) for l in BENCH.read_text(encoding="utf-8").splitlines()
                           if l.strip()])
        if args.limit:
            items = items[:args.limit]
        d1_map = {json.loads(l)["i"]: json.loads(l)["d1_query"]
                  for l in E13_PER.read_text(encoding="utf-8").splitlines() if l.strip()}
        return _aggregate(items, d1_map, e13)
    return _run(args)


if __name__ == "__main__":
    sys.exit(main())
