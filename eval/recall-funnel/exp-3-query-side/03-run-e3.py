"""E3 · 步骤 3：**跑两臂对照**（唯一变量 = 送进检索的那串字）。

- 对照臂 A：原查询（一字不改）
- 实验臂 T：原查询 + 术语桥 `TermIndex.select(query, k=5)` 选出的 5 个术语名

**主终点 = 六路同预算并集 @1000（全量 171）**，且**与基线 0.3918 同口径** ——
因此直接复用 `eval/recall-funnel/funnel.py` 的通道函数与并集定义（只换查询串）。
基线自检：对照臂必须复现 `funnel-summary.json` 的 headline/all 数字，否则先查仪器。

⚠ 全部在**副本** `exp-3-query-side/exp.db` 上只读进行；真库不碰。
⚠ 防作弊：`select()` 只吃 query；另跑机械检查（注入词在 gold vs 全库的集中度、术语索引与考卷交集）。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-3-query-side\\03-run-e3.py
"""
from __future__ import annotations

import array
import json
import sqlite3
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval" / "recall-funnel"))
EXP = HERE / "exp.db"
CACHE = ROOT / "var" / "tmp" / "term-index-full.json"
OUT = HERE / "e3-result.json"
OUT_PER = HERE / "e3-per-query.jsonl"
K_TERMS = 5


def main() -> int:
    import funnel as F
    from src.core.retrieval.term_bridge import TermIndex
    from src.core.retrieval.hybrid_engine import extract_modality_from_query
    from src.core.storage.sqlite_db import load_vec_extension

    if not CACHE.exists():
        print(f"⛔ 术语索引不存在：{CACHE} —— 先跑 01-build-term-index.py")
        return 1
    index = TermIndex.load(CACHE)
    print(f"[e3] 术语索引 {len(index)} 个术语", flush=True)

    conn = sqlite3.connect(f"file:{EXP.as_posix()}?mode=ro", uri=True)
    if not load_vec_extension(conn):
        print("⛔ sqlite-vec 加载失败")
        return 1

    v2 = [json.loads(l) for l in (ROOT / "eval" / "recall-funnel" / "benchmark-v2.jsonl")
          .read_text(encoding="utf-8").splitlines() if l.strip()]

    # ── 防作弊 ①：术语索引的条款集合 ∩ 考卷 gold 条款集合 ──────────────────
    gold_ids = {r["v2"]["gold_cr_id"] for r in v2}
    idx_ids = set()
    for e in index.entries:                       # TermEntry 带 clause id（见 term_bridge）
        cid = getattr(e, "clause_revision_id", None) or getattr(e, "clause_id", None)
        if cid:
            idx_ids.add(cid)
    inter = gold_ids & idx_ids
    print(f"[e3] 防作弊①：术语索引条款 {len(idx_ids)} 个 ∩ 考卷 gold {len(gold_ids)} 个 = {len(inter)}"
          f" {'✅' if not inter else '⛔ 有交集，作废'}", flush=True)

    rows = []
    t0 = time.perf_counter()
    for n, it in enumerate(v2, 1):
        q = it["query"]
        picks = index.select(q, k=K_TERMS)
        added = [p.term for p in picks]
        q_exp = q + " " + " ".join(added) if added else q

        rec = {"i": it["i"], "headline": bool(it["v2"]["bucket"] == "keep"
                                               and not ({"gold_multi_def", "gold_dup_text"}
                                                        & set(it["v2"]["flags"]))),
               "kind": it["kind"], "added_terms": added, "query": q, "query_expanded": q_exp}
        mf = extract_modality_from_query(q)          # 模态筛只由原查询决定（不改它，避免多改一处）

        for arm, qq in (("base", q), ("ctx", q_exp)):
            # 通道定义**逐字复用 funnel.py**（与基线 0.3918 同口径）；唯一差别是查询串 qq。
            exact = F.channel_exact(conn, qq)
            fts1000 = F.channel_fts(conn, qq, 1000)
            fts20 = F.channel_fts(conn, qq, 20)
            modality = F.channel_modality(conn, mf)   # 模态筛只由**原查询**决定（不多改一处）
            vec = F.channel_vec(conn, qq, 1000)       # 向量这一路用扩展后的查询串去嵌入
            gold = it["v2"]["gold_cr_id"]

            a = {"vec_n": len(vec), "added_n": len(added)}
            for d in (20, 100, 1000):
                # 同预算口径：每路各截到 d（与 funnel 的 union.same_budget 一致）
                union_d = (set(exact[:d]) | set(fts1000[:d]) | set(modality[:d]) | set(vec[:d]))
                a[f"rank@{d}"] = F.rank_of(gold, vec[:d])
                a[f"gold_hit@{d}"] = bool(F.rank_of(gold, vec[:d]))
                a[f"union_same@{d}"] = gold in union_d
                a[f"fts@{d}"] = gold in set(fts1000[:d])
            # 生产上限口径：A/D/E 取全量、B/C/F 各 20
            a["union_prod"] = gold in (set(exact) | set(fts20) | set(modality) | set(vec[:20]))
            rec[arm] = a
        rows.append(rec)
        if n % 20 == 0:
            print(f"[e3] {n}/{len(v2)}  {time.perf_counter()-t0:.0f}s", flush=True)

    # ── 防作弊 ②：注入词在 gold 条文里 vs 在全库里的出现率 ──────────────────
    all_text_n = conn.execute("SELECT COUNT(*) FROM clause_revision").fetchone()[0]
    leak = []
    for r in rows:
        if not r["added_terms"]:
            continue
        gold_txt = next((x["gold_text"] or "" for x in v2 if x["i"] == r["i"]), "")
        for t in r["added_terms"]:
            if t and t in gold_txt:
                n_lib = conn.execute(
                    "SELECT COUNT(*) FROM clause_revision WHERE content_text LIKE ?",
                    (f"%{t}%",)).fetchone()[0]
                leak.append({"i": r["i"], "term": t,
                             "share_lib": round(n_lib / all_text_n, 4)})

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
        "experiment": "E3 查询侧术语桥扩展",
        "single_variable": "只改送进检索的查询串（原查询 vs 原查询+术语桥 top-5 术语名）",
        "k_terms": K_TERMS,
        "primary_endpoint": "六路同预算并集 @1000（全量 171 口径）",
        "baseline_selfcheck": {
            "注": "对照臂应复现 funnel-summary.json；若不复现则先查仪器、不许解释结果",
            "funnel_all_union@1000": 0.3918, "funnel_headline_union@1000": 0.4,
            "funnel_all_vec@1000": 0.345, "funnel_headline_vec@1000": 0.3583,
        },
        "summary": summary,
        "anti_cheat": {
            "index_cap_benchmark_gold": len(inter),
            "index_cap_note": "必须为 0；>0 则整次作废",
            "injected_term_in_gold_events": len(leak),
            "injected_term_in_gold_samples": leak[:20],
            "reading": ("注入词命中 gold 的天数/条数若集中（share_lib 很小却频繁命中 gold）"
                        "⇒ 疑似间接泄漏，结论作废"),
        },
        "elapsed_s": round(time.perf_counter() - t0, 1),
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    OUT_PER.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1))
    print(f"\n已写 {OUT}\n已写 {OUT_PER}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
