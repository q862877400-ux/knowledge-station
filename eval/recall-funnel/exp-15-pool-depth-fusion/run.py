"""exp-15：深读候选的「池深 × 融合方式」二维对照 —— 深读候选到底能不能进前 20？

## 这一批测什么（口径见同目录 stop-loss.json，**跑前落盘**）

exp-6 只放大每路取数上限（20→100）⇒ `fused@20` 只有 +1.67pt；
exp-7 只在【生产上限 20】下改融合公式 ⇒ +0.83pt、p=1.0。
**两者的交互从来没量过** —— 本批固定其他一切，只改「每路取多少条」×「怎么融合」。

| 臂 | 每路取数 | 融合 |
|---|---|---|
| `A0_prod` | fts 20 / vec 20（exact/modality 全量） | 加权 RRF `Σ w/(60+r+1)` = **生产现状** |
| `P100_rrf60` | 100 | 加权 RRF k=60（≈ exp-6 处理臂） |
| `P1000_rrf60` | 1000 | 加权 RRF k=60 |
| `P1000_rrf200` | 1000 | 加权 RRF k=200（衰减变平） |
| `P1000_rrf1000` | 1000 | 加权 RRF k=1000 |
| `P1000_rrm60` | 1000 | **RRM** `max w/(60+r+1)`（只取最强的一路名次） |
| `P1000_doc3` | 1000 → 每篇文档最多 3 条、取 20 | 加权 RRF k=60（治「同文档挤占」） |

外加 **oracle 上界**（gold 落在「每路前 d 条的并集」里的比例）—— 那是上界，**不是一个能实现的系统**。

## 不许创造第二套写法（本批复用了什么）
* 通道副本 `channel_exact/fts/vec/modality`、只读连接 `ro_conn` ⇒ 复用 `eval/recall-funnel/funnel.py`
  （它已被 exp-7 的 120/120 口径复核证明与生产单通道一致）；
* 融合 `fuse()`、排序+时效过滤 `order()`、`rank_of` / `mcnemar_exact` / `boot_ci`
  ⇒ 复用 `eval/recall-funnel/exp-7-rrm/run.py`（**只把模块级 `K` 参数化**，不改它的公式）；
* 考卷切片 `_headline` ⇒ 与 exp-14 同一判据。

## 仪器对照（硬性，对不上整批作废）
`A0_prod` 的前 20 名必须与生产 `search_with_details(top_k=20, rerank=False,
channels=[exact,fts,vec,modality], boost_bookmarks=False)` **逐条一致 120/120**。

## 断点续跑
单次向量 KNN（k=1000，暴力扫真库 66 万行）约 1 s ⇒ 120 条约 3~5 分钟。
逐条 **append + fsync** 落 `runs.jsonl`（单位 = 一条提问，一条记录含全部臂）；被杀后重跑自动跳过。

## ★ 台账字段（第 15 轮复核 P1-1 的根因，别再改回去）
`arms[臂]` 必须**分别**存三个深度的名次：`rank20` / `rank100` / `rank1000` ——
每个都是在**对应深度的名单**里取 `rank_of(gold, …)`。
初版只存了一个 `rank`（= top-20 名单里的名次）⇒ 三个阈值共用同一个名次
⇒ `@100`/`@1000` **恒等于** `@20`，而 `stop-loss.json` 明列 `fused@100` 为副终点 ⇒ **读数不真**。

`aggregate_runs()` 通过 `arm_rank()` **兼容旧台账**：旧台账另有一个 `hit@100` 布尔字段
（只能还原 @100 的**命中率**、还原不出名次），且**没有** @1000 字段
⇒ 本轮不上报 `fused_top1000`（置 `null`），由 `ledger_depths()` 判定。

## 只读保证
真库 `file:...?mode=ro`；不写库、不改任何源文件；脚本首尾各记一次库 mtime，不一致即报错退出。

用法：
    .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-15-pool-depth-fusion\\run.py
    .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-15-pool-depth-fusion\\run.py --aggregate
    .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-15-pool-depth-fusion\\run.py --limit 5
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
RUNS = HERE / "runs.jsonl"          # 逐条提问台账（append-only，续跑用）
OUT = HERE / "result.json"
OUT_Q = HERE / "per-query.jsonl"

LIVE = ("exact", "fts", "vec", "modality")

#: 臂表。`fusion` 是 `exp7.fuse()` 的臂名（"A" = 加权 RRF，"Dp" = 加权 RRM）；
#: `k` 写进 `exp7.K`；`doc_div`/`budget` 只在 `P1000_doc3` 上有。
ARMS: dict[str, dict] = {
    "A0_prod":       {"depth": 20,   "fusion": "A",  "k": 60},
    "P100_rrf60":    {"depth": 100,  "fusion": "A",  "k": 60},
    "P1000_rrf60":   {"depth": 1000, "fusion": "A",  "k": 60},
    "P1000_rrf200":  {"depth": 1000, "fusion": "A",  "k": 200},
    "P1000_rrf1000": {"depth": 1000, "fusion": "A",  "k": 1000},
    "P1000_rrm60":   {"depth": 1000, "fusion": "Dp", "k": 60},
    "P1000_doc3":    {"depth": 1000, "fusion": "A",  "k": 60, "doc_div": 3, "budget": 20},
}
ORACLE_DEPTHS = (20, 100, 1000)


def _load(mod_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(mod_name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _headline(rows: list[dict]) -> list[dict]:
    """headline 120 条切片 —— 与 exp-14 / exp-8 同一判据（不重写第二套）。"""
    return [
        r for r in rows
        if (r.get("v2") or {}).get("bucket") == "keep"
        and not ({"gold_multi_def", "gold_dup_text"} & set((r.get("v2") or {}).get("flags", [])))
    ]


# ── ★ 纯函数（单测直接喂合成数据）──────────────────────────────────────────────
def take_doc_diverse(lst: list[str], doc_of: dict[str, str],
                     per_doc: int, budget: int) -> list[str]:
    """按「每篇文档最多 `per_doc` 条」去重后取前 `budget` 条。

    `doc_of` 缺该 id 的文档时**跳过**（与生产 `fetch_full_clause` 取不到就跳过同向）。
    """
    kept: list[str] = []
    cnt: dict[str, int] = {}
    for cid in lst:
        doc = doc_of.get(cid)
        if doc is None:
            continue
        if cnt.get(doc, 0) >= per_doc:
            continue
        cnt[doc] = cnt.get(doc, 0) + 1
        kept.append(cid)
        if len(kept) >= budget:
            break
    return kept


def build_rankings(deep: dict[str, list[str]], arm: str, doc_of: dict[str, str]) -> dict[str, list[str]]:
    """★ 纯函数：该臂送进融合的**每路候选列表**。

    `exact` / `modality` 照生产**不限量**（生产问答路径不传过滤，触发时取全量）；
    只有 `fts` / `vec` 受本批的「池深」变量影响 —— 这样臂与臂之间只差一个变量。
    """
    spec = ARMS[arm]
    depth = spec["depth"]
    out: dict[str, list[str]] = {
        "exact": list(deep["exact"]),
        "modality": list(deep["modality"]),
    }
    if spec.get("doc_div"):
        out["fts"] = take_doc_diverse(deep["fts"], doc_of, spec["doc_div"], spec["budget"])
        out["vec"] = take_doc_diverse(deep["vec"], doc_of, spec["doc_div"], spec["budget"])
    else:
        out["fts"] = list(deep["fts"][:depth])
        out["vec"] = list(deep["vec"][:depth])
    return out


def oracle_pool(deep: dict[str, list[str]], d: int) -> set[str]:
    """★ 纯函数：oracle 池 = exact ∪ modality ∪ fts[:d] ∪ vec[:d]（上界，不是可实现系统）。"""
    pool: set[str] = set(deep["exact"]) | set(deep["modality"])
    pool |= set(deep["fts"][:d])
    pool |= set(deep["vec"][:d])
    return pool


def _hit_rate(ranks: list[int | None], thr: int) -> float:
    return round(sum(1 for x in ranks if x is not None and x <= thr) / len(ranks) * 100, 2)


def _median_rank(ranks: list[int | None]) -> int | None:
    vals = sorted(x for x in ranks if x is not None)
    return vals[len(vals) // 2] if vals else None


def arm_rank(arm_rec: dict, depth: int) -> int | None:
    """★ 纯函数：该臂在 `depth` 深度上的 gold 名次（`None` = 未命中 / 该深度无数据）。

    台账有两种形状：
      * **新**（本文件当前写法）：`rank20` / `rank100` / `rank1000`；
      * **旧**（第 15 轮初版 —— 复核 **P1-1** 打回的那版）：只有
        `rank`（top-20 名单里的名次）与 `hit@100`（布尔：是否进了前 100）。
    ⇒ 旧台账：@20 读 `rank`；@100 只能还原「命中与否」（用 `1` 占位，**还原不出名次**，
      但 `_hit_rate(…, 100)` 只用到"是否 ≤100"这一点，所以够用）；@1000 无字段 ⇒ `None`。
    """
    key = f"rank{depth}"
    if key in arm_rec:
        return arm_rec[key]
    if depth == 20 and "rank" in arm_rec:
        return arm_rec["rank"]
    if depth == 100 and "hit@100" in arm_rec:
        return 1 if arm_rec["hit@100"] else None
    return None


def ledger_depths(runs_by_key: dict[int, dict]) -> list[int]:
    """★ 纯函数：台账里**真的存了**哪些深度 —— 决定哪些阈值可以上报（别把没测的当 0%）。"""
    have: set[int] = set()
    for r in runs_by_key.values():
        for a in ARMS:
            rec = r["arms"][a]
            if "rank20" in rec or "rank" in rec:
                have.add(20)
            if "rank100" in rec or "hit@100" in rec:
                have.add(100)
            if "rank1000" in rec:
                have.add(1000)
    return sorted(have)


def aggregate_runs(items: list[dict], runs_by_key: dict[int, dict], exp7) -> tuple[dict, list[dict]]:
    """★ 纯函数（单测直接喂合成台账）：从逐条台账算聚合。

    `runs_by_key[i]` = 该条记录（含 `arms` / `oracle`）。缺条即 `KeyError`
    （**不静默补 0** —— 缺条会让 @20 的分母错）。

    ⚠ **每个阈值的名次必须来自对应深度的名单**（第 15 轮复核 **P1-1** 打回）：
    初版把三个阈值都套在「top-20 名单里的名次」上 ⇒ `@100/@1000` 恒等于 `@20`、读数不真。
    取数统一走 `arm_rank()`（兼容新/旧两种台账形状）。

    ⚠ `fused_hit_n` / `fused_median_rank` **定义在 @20 上**（与冻结版逐位一致）：
    前者 = @20 命中条数、后者 = @20 命中条的名次中位。**别改成 rank1000** —— 那是静默换定义。
    """
    depths = ledger_depths(runs_by_key)
    arm_r20: dict[str, list[int | None]] = {a: [] for a in ARMS}
    arm_r100: dict[str, list[int | None]] = {a: [] for a in ARMS}
    arm_r1000: dict[str, list[int | None]] = {a: [] for a in ARMS}
    arm_pools: dict[str, list[int]] = {a: [] for a in ARMS}
    oracle_hit: dict[str, list[bool]] = {f"@{d}": [] for d in ORACLE_DEPTHS}
    per_query: list[dict] = []
    for it in items:
        r = runs_by_key[it["i"]]
        row = {"i": it["i"], "query": it["query"], "gold_cr_id": it["v2"]["gold_cr_id"],
               "subset": (it.get("v2") or {}).get("subset", {}).get("label"),
               "modality_filter": r["modality_filter"],
               "deep_n": r["deep_n"], "gold_rank_in_deep": r["gold_rank_in_deep"],
               "oracle": r["oracle"], "arms": r["arms"], "check_identical": r["check_identical"]}
        for a in ARMS:
            arm_r20[a].append(arm_rank(r["arms"][a], 20))
            arm_r100[a].append(arm_rank(r["arms"][a], 100))
            arm_r1000[a].append(arm_rank(r["arms"][a], 1000))
            arm_pools[a].append(r["arms"][a]["pool"])
        for d in ORACLE_DEPTHS:
            oracle_hit[f"@{d}"].append(bool(r["oracle"][f"@{d}"]))
        per_query.append(row)

    labels = [r["subset"] for r in per_query]
    subset_names = sorted({x for x in labels if x})

    def by_subset(ranks: list[int | None], thr: int) -> dict:
        out = {}
        for nm in subset_names:
            sub = [r for r, lb in zip(ranks, labels) if lb == nm]
            out[nm] = {"n": len(sub), "hit": _hit_rate(sub, thr)}
        return out

    agg: dict = {
        "n": len(items),
        "arms": {},
        "ledger_depths": depths,
        "depth_note": "台账里真的存了名次的深度；没存的一律上报 null（**不许把没测的当 0%**）。"
                      "本轮台账（初版）只存了 @20 名次与 @100 布尔命中 ⇒ @1000 未测。",
        "oracle": {f"@{d}": round(sum(1 for x in oracle_hit[f"@{d}"] if x) / len(items) * 100, 2)
                   for d in ORACLE_DEPTHS},
        "oracle_note": "oracle = gold 落在『exact ∪ modality ∪ fts[:d] ∪ vec[:d]』里的比例；**上界，不是可实现系统**",
        "instrument_check": {
            "source": "生产 search_with_details(top_k=20, rerank=False, channels=四路, boost_bookmarks=False)",
            "compared": len(per_query),
            "identical_count": sum(1 for r in per_query if r["check_identical"]),
            "note": "A0_prod 前 20 名必须 120/120 逐条一致；对不上整批作废",
        },
    }
    for a in ARMS:
        rec = {
            "fused_top20": _hit_rate(arm_r20[a], 20),
            # ⚠ 第 15 轮复核 P1-1：@100 必须用**前 100 名单**里的名次算，不许套 top-20 名次
            "fused_top100": _hit_rate(arm_r100[a], 100) if 100 in depths else None,
            "fused_top1000": _hit_rate(arm_r1000[a], 1000) if 1000 in depths else None,
            # ↓ 这两个**定义在 @20 上**（与冻结版逐位一致）：别改成 rank1000（那是静默换定义）
            "fused_hit_n": sum(1 for x in arm_r20[a] if x is not None),
            "fused_median_rank": _median_rank(arm_r20[a]),
            "pool_median": sorted(arm_pools[a])[len(arm_pools[a]) // 2],
            "by_subset_top20": by_subset(arm_r20[a], 20),
        }
        if a != "A0_prod":
            base_hit = [x is not None and x <= 20 for x in arm_r20["A0_prod"]]
            arm_hit = [x is not None and x <= 20 for x in arm_r20[a]]
            b = sum(1 for x, y in zip(base_hit, arm_hit) if (not x) and y)
            c = sum(1 for x, y in zip(base_hit, arm_hit) if x and (not y))
            rec["vs_A0_top20"] = {
                "delta_pt": round(rec["fused_top20"] - agg["arms"]["A0_prod"]["fused_top20"], 2),
                "flip_in": b, "flip_out": c,
                "mcnemar_p": round(exp7.mcnemar_exact(b, c), 4),
            }
        agg["arms"][a] = rec
    return agg, per_query


# ── 跑 ────────────────────────────────────────────────────────────────────────
def _run(args) -> int:
    import funnel
    exp7 = _load("exp7_run", ROOT / "eval" / "recall-funnel" / "exp-7-rrm" / "run.py")
    from src.core.retrieval import hybrid_engine as he
    from src.core.retrieval.hybrid_engine import search_with_details, extract_modality_from_query

    mtime0 = DB.stat().st_mtime
    conn = funnel.ro_conn(DB)
    he._conn = lambda: conn          # 让生产函数也在只读连接上跑（不改生产代码）
    print(f"[exp-15] 库 = {DB}（mode=ro）", flush=True)

    items = _headline([json.loads(l) for l in BENCH.read_text(encoding="utf-8").splitlines()
                       if l.strip()])
    if args.limit:
        items = items[:args.limit]

    from src.core.text_utils import standard_key
    std_of_key = {standard_key(r[0]): r[0] for r in conn.execute("SELECT standard_no FROM doc_meta")}
    gold_cr: dict[int, str] = {}
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

    #: cid → doc_id（`take_doc_diverse` 用）；cid → legal_status（`order` 用，与 exp-7 同源）
    doc_of = {r[0]: r[1] for r in conn.execute("SELECT clause_revision_id, doc_id FROM clause_revision")}
    status = {r[0]: r[1] for r in conn.execute(
        "SELECT cr.clause_revision_id, dm.legal_status FROM clause_revision cr"
        " JOIN doc_meta dm ON dm.doc_id=cr.doc_id")}
    print(f"[exp-15] 预载 doc_of {len(doc_of)} / status {len(status)}；考卷 {len(items)} 条", flush=True)

    done: set[int] = set()
    if RUNS.exists():
        for l in RUNS.read_text(encoding="utf-8").splitlines():
            if l.strip():
                done.add(json.loads(l)["i"])
    todo = [it for it in items if it["i"] not in done]
    print(f"[exp-15] 已完成 {len(done)}，本次待跑 {len(todo)}", flush=True)
    if not todo:
        print("[exp-15] 全部已完成，直接聚合", flush=True)
        return _aggregate(items, exp7)

    t0 = time.perf_counter()
    with RUNS.open("a", encoding="utf-8") as fh:
        for n, it in enumerate(todo, 1):
            ts = time.perf_counter()
            q = it["query"]
            gold = gold_cr[it["i"]]
            mfilter = extract_modality_from_query(q)
            deep = {
                "exact": funnel.channel_exact(conn, q),
                "fts": funnel.channel_fts(conn, q, 1000),
                "vec": funnel.channel_vec(conn, q, 1000),
                "modality": funnel.channel_modality(conn, mfilter),
            }
            rec: dict = {
                "i": it["i"], "query": q, "gold_cr_id": gold, "modality_filter": mfilter,
                "deep_n": {c: len(deep[c]) for c in LIVE},
                "gold_rank_in_deep": {c: exp7.rank_of(gold, deep[c]) for c in LIVE},
                "oracle": {f"@{d}": gold in oracle_pool(deep, d) for d in ORACLE_DEPTHS},
                "arms": {},
            }
            rec["oracle"]["pool@1000"] = len(oracle_pool(deep, 1000))
            for a, spec in ARMS.items():
                rk = build_rankings(deep, a, doc_of)
                exp7.K = spec["k"]
                sc = exp7.fuse(rk, spec["fusion"])
                # ⚠ **必须分别取三个深度的名次**（第 15 轮复核 **P1-1** 打回）：
                #   初版只存了「top-20 名单里的名次」⇒ `rank ∈ {1..20, None}` ⇒
                #   `_hit_rate(rank, 100)` 与 `(rank, 1000)` 都恒等于 `@20`，**@100/@1000 是 @20 的复制**。
                rec["arms"][a] = {
                    "pool": len(sc),
                    "rank20": exp7.rank_of(gold, exp7.order(sc, status, 20)),
                    "rank100": exp7.rank_of(gold, exp7.order(sc, status, 100)),
                    "rank1000": exp7.rank_of(gold, exp7.order(sc, status, 1000)),
                    "ch_n": {c: len(rk[c]) for c in LIVE},
                }
            # ★ 仪器对照：A0_prod 前 20 必须与生产逐条一致
            prod = search_with_details(q, top_k=20, rerank=False, channels=list(LIVE),
                                       boost_bookmarks=False)
            prod_ids = [r["clause_revision_id"] if isinstance(r, dict) else r.clause_revision_id
                        for r in (prod.get("results") or [])]
            exp7.K = 60
            a0 = exp7.order(exp7.fuse(build_rankings(deep, "A0_prod", doc_of), "A"), status, 20)
            rec["check_identical"] = prod_ids == a0
            rec["check_prod_n"] = len(prod_ids)
            rec["elapsed_s"] = round(time.perf_counter() - ts, 2)
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
            if n % 10 == 0 or n == len(todo):
                el = time.perf_counter() - t0
                ok = sum(1 for l in RUNS.read_text(encoding="utf-8").splitlines()
                         if l.strip() and json.loads(l).get("check_identical"))
                print(f"[exp-15] {n}/{len(todo)} 用时 {el:.0f}s（{el/max(n,1):.2f}s/条）"
                      f"  口径复核一致 {ok}/{len(done)+n}", flush=True)

    mtime1 = DB.stat().st_mtime
    if mtime0 != mtime1:
        print(f"[exp-15] ⚠ 真库 mtime 变了：{mtime0} -> {mtime1}", flush=True)
        return 2
    return _aggregate(items, exp7)


def _aggregate(items: list[dict], exp7) -> int:
    runs: dict[int, dict] = {}
    for l in RUNS.read_text(encoding="utf-8").splitlines():
        if l.strip():
            r = json.loads(l)
            runs[r["i"]] = r
    try:
        agg, per_query = aggregate_runs(items, runs, exp7)
    except KeyError as e:
        print(f"[exp-15] ⚠ 缺条 {e}，聚合中止", flush=True)
        return 3

    ic = agg["instrument_check"]
    print("\n[exp-15] ==== 结果（headline 120，fused = 融合后名次）====")
    print(f"  台账里存了名次的深度 = {agg['ledger_depths']}（没存的上报「未测」，不报 0%）")
    for a in ARMS:
        r = agg["arms"][a]
        extra = ""
        if a != "A0_prod":
            v = r["vs_A0_top20"]
            extra = (f"  Δ@20={v['delta_pt']:+.2f}pt 进{v['flip_in']}/出{v['flip_out']}"
                     f" p={v['mcnemar_p']}")
        t100 = " 未测" if r["fused_top100"] is None else f"{r['fused_top100']:5.2f}%"
        t1000 = " 未测" if r["fused_top1000"] is None else f"{r['fused_top1000']:5.2f}%"
        print(f"  {a:15s} @20={r['fused_top20']:5.2f}%  @100={t100}  @1000={t1000}  "
              f"池中位={r['pool_median']}  @20命中数={r['fused_hit_n']}{extra}")
    print(f"  oracle 上界（非可实现）：" +
          "  ".join(f"@{d}={agg['oracle'][f'@{d}']:.2f}%" for d in ORACLE_DEPTHS))
    print(f"  仪器对照：A0_prod 与生产逐条一致 {ic['identical_count']}/{ic['compared']}")

    OUT.write_text(json.dumps(
        {"note": "exp-15 池深 × 融合方式二维对照；口径见 run.py docstring 与 stop-loss.json",
         "agg": agg}, ensure_ascii=False, indent=1), encoding="utf-8")
    with OUT_Q.open("w", encoding="utf-8") as f:
        for r in per_query:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\n[exp-15] 已写 {OUT} 与 {OUT_Q}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 条（校验用）")
    ap.add_argument("--aggregate", action="store_true", help="只聚合 runs.jsonl，不跑")
    args = ap.parse_args()
    exp7 = _load("exp7_run", ROOT / "eval" / "recall-funnel" / "exp-7-rrm" / "run.py")
    if args.aggregate:
        items = _headline([json.loads(l) for l in BENCH.read_text(encoding="utf-8").splitlines()
                           if l.strip()])
        if args.limit:
            items = items[:args.limit]
        return _aggregate(items, exp7)
    return _run(args)


if __name__ == "__main__":
    sys.exit(main())
