"""E1 步骤 4：A/B 对照（**两个臂都在同一份副本上**，语料完全冻结）。

对照臂 = 副本里的 `clause_vec`（现役口径：`title + "\\n" + content_text[:512]`）
实验臂 = 副本里的 `clause_vec_ctx`（标准名 + 章节路径 + 条款号 + content_text[:512]）

**查询侧一字不改**（用 `benchmark-v2.jsonl` 的原始问法）。
按预登记的止损线（`stop-loss.json`）看：Vector @20/@100/@1000、同预算并集 @1000、
以及**翻进来/翻出去**的逐条清单（配对口径，比单看百分点可靠）。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-1-contextual\\04-ab-eval.py
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
sys.path.insert(0, str(HERE.parent))          # 复用 funnel.py 的通道实现
EXP = HERE / "exp.db"
DEPTHS = (20, 100, 1000)


def conn_ro(p: Path) -> sqlite3.Connection:
    c = sqlite3.connect(f"file:{p.as_posix()}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    from src.core.storage.sqlite_db import load_vec_extension
    load_vec_extension(c)
    return c


def knn(c: sqlite3.Connection, table: str, qvec: list[float], k: int) -> list[str]:
    rows = c.execute(
        f"SELECT clause_revision_id, distance FROM {table}"
        " WHERE embedding MATCH ? AND k = ? ORDER BY distance",
        (array.array("f", qvec).tobytes(), k)).fetchall()
    return [r[0] for r in rows]


def rank_of(gold: str, cand: list[str]) -> int | None:
    try:
        return cand.index(gold) + 1
    except ValueError:
        return None


def rate(hits: int, n: int) -> float | None:
    return round(hits / n, 4) if n else None


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="实验臂也用对照臂的向量跑一遍：只验并集定义能否复现 funnel 的 40.00%%")
    ap.add_argument("--expect-union", type=float, default=0.40)
    args = ap.parse_args()

    import funnel as F
    from src.core.retrieval import embedder

    v2 = [json.loads(l) for l in (HERE.parent / "benchmark-v2.jsonl").read_text(encoding="utf-8").splitlines()
          if l.strip()]
    per = {json.loads(l)["i"]: json.loads(l)
           for l in (HERE.parent / "funnel-per-query.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}

    db = conn_ro(EXP)
    n_ctx = db.execute("SELECT COUNT(*) FROM clause_vec_ctx").fetchone()[0]
    n_base = db.execute("SELECT COUNT(*) FROM clause_vec").fetchone()[0]
    print(f"[ab] 对照臂 clause_vec = {n_base} 行；实验臂 clause_vec_ctx = {n_ctx} 行")
    if args.dry_run:
        print("[ab] --dry-run：实验臂也用对照臂的向量，只为验证并集定义")
    elif n_ctx != n_base:
        print(f"⛔ 两个臂的条目数不一致（{n_base} vs {n_ctx}）⇒ 按止损线「hard_fail」作废本次")
        return 1

    EX = {"gold_multi_def", "gold_dup_text"}
    out_rows = []
    t0 = time.perf_counter()
    for j, it in enumerate(v2, 1):
        gold = it["v2"]["gold_cr_id"]
        qv = embedder.embed_query(it["query"])
        rec = {"i": it["i"], "kind": it["kind"],
               "headline": it["v2"]["bucket"] == "keep" and not (EX & set(it["v2"]["flags"]))}
        cands = {}
        for arm, table in (("base", "clause_vec"),
                           ("ctx", "clause_vec" if args.dry_run else "clause_vec_ctx")):
            full = knn(db, table, qv, max(DEPTHS))
            cands[arm] = full
            rec[arm] = {"n": len(full)}
            # 精确名次（在上限 1000 的候选表内）—— 报告不只是"过没过线"，还要看整体有没有往前挪
            rec[arm]["rank"] = rank_of(gold, full)
            for d in DEPTHS:
                rec[arm][f"rank@{d}"] = rank_of(gold, full[:d])
        # 并集：**照 funnel.py 的两个口径**，只把通道 C 换成该臂 —— 其余五路逐字不动。
        # ⚠ 初版这里只并了 B + C，漏掉 A/D/E/F，且模态筛选取了个不存在的字段（恒 None）。
        #   当前语料下那四路贡献恰好为 0（A 触发 0、D 触发了但前 1000 名无命中、E/F 恒 0），
        #   所以数字没受影响；但**定义是错的**，语料一变就会静默跑偏。已按 funnel 的口径补齐。
        from src.core.retrieval.hybrid_engine import extract_modality_from_query
        mf = extract_modality_from_query(it["query"])
        ch = {
            "exact": F.channel_exact(db, it["query"]),
            "fts20": F.channel_fts(db, it["query"], 20),
            "fts1000": F.channel_fts(db, it["query"], 1000),
            "modality": F.channel_modality(db, mf),
            "legal_element": [],
            "behavior_scope": [],
        }
        # 同预算口径 @1000：每路各取前 1000（uncapped 的路也截到 1000）
        fixed_same = set(ch["exact"][:1000]) | set(ch["fts1000"]) | \
            set(ch["modality"][:1000]) | set(ch["legal_element"][:1000]) | set(ch["behavior_scope"][:1000])
        # 生产上限口径：A/D/E 取全量、B/C/F 各 20
        fixed_prod = set(ch["exact"]) | set(ch["fts20"]) | \
            set(ch["modality"]) | set(ch["legal_element"]) | set(ch["behavior_scope"][:20])
        rec["union_prod"] = {
            "base": gold in fixed_prod | set(cands["base"][:20]),
            "ctx": gold in fixed_prod | set(cands["ctx"][:20]),
        }
        rec["union_same_budget@1000"] = {
            "base": gold in fixed_same | set(cands["base"]),
            "ctx": gold in fixed_same | set(cands["ctx"]),
        }
        out_rows.append(rec)
        if j % 20 == 0:
            print(f"[ab] {j}/{len(v2)}  {time.perf_counter()-t0:.0f}s", flush=True)

    def summarize(rows, label):
        n = len(rows)
        r = {"n": n}
        for arm in ("base", "ctx"):
            for d in DEPTHS:
                r[f"{arm}_vec@{d}"] = rate(sum(1 for x in rows if x[arm][f"rank@{d}"]), n)
            r[f"{arm}_union_prod"] = rate(sum(1 for x in rows if x["union_prod"][arm]), n)
            r[f"{arm}_union@1000"] = rate(sum(1 for x in rows if x["union_same_budget@1000"][arm]), n)
        for d in DEPTHS:
            gain = sum(1 for x in rows if not x["base"][f"rank@{d}"] and x["ctx"][f"rank@{d}"])
            lose = sum(1 for x in rows if x["base"][f"rank@{d}"] and not x["ctx"][f"rank@{d}"])
            r[f"vec@{d}_flip"] = {"in": gain, "out": lose, "net_pp": round((gain - lose) / n * 100, 2)}
        r["union@1000_flip"] = {
            "in": sum(1 for x in rows if not x["union_same_budget@1000"]["base"]
                      and x["union_same_budget@1000"]["ctx"]),
            "out": sum(1 for x in rows if x["union_same_budget@1000"]["base"]
                       and not x["union_same_budget@1000"]["ctx"]),
        }
        return r

    allr = summarize(out_rows, "all")
    head = summarize([x for x in out_rows if x["headline"]], "headline")

    if args.dry_run:
        got = head["base_union@1000"]
        ok = abs(got - args.expect_union) < 0.005
        print(f"\n[dry-run] 并集定义自检：对照臂 union_same_budget@1000 = {got:.4f}"
              f"（期望 {args.expect_union:.4f}，来自 funnel-summary.json 的 headline）"
              f" → {'✅ 一致' if ok else '⛔ 不一致'}")
        print(f"[dry-run] 两臂应完全相同：base={got:.4f} ctx={head['ctx_union@1000']:.4f}"
              f" → {'✅' if got == head['ctx_union@1000'] else '⛔'}")
        return 0 if ok else 1

    # 那 104 条"六路前 1000 名都没有"里，有多少被救回
    rescued = [x["i"] for x in out_rows
               if not per[x["i"]].get("hit_in_deep_union") and x["union_same_budget@1000"]["ctx"]]
    print(f"\n[ab] 原本「六路前 1000 名都没有」的 104 条里，实验臂救回 {len(rescued)} 条: {rescued[:20]}")

    result = {
        "meta": {
            "exp": "E1 Contextual Retrieval Representation A/B",
            "arm_control": "clause_vec（现役：title + '\\n' + content_text[:512]）",
            "arm_experiment": "clause_vec_ctx（标准名 + 章节路径 + 条款号 + content_text[:512]）",
            "query_side": "一字不改（benchmark-v2.jsonl 的 query）",
            "stop_loss": "stop-loss.json（跑之前已落盘）",
            "n_ctx": n_ctx, "n_base": n_base,
        },
        "headline_120": head,
        "all_171": allr,
        "rescued_from_104": rescued,
        "per_query": out_rows,
    }
    (HERE / "ab-result.json").write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n=== 主结果 120 条 ===")
    print(json.dumps(head, ensure_ascii=False, indent=1))
    print("\n=== 全量 171 条 ===")
    print(json.dumps(allr, ensure_ascii=False, indent=1))
    print(f"\n已写 {HERE / 'ab-result.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
