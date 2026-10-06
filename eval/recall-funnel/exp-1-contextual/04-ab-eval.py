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
    if n_ctx != n_base:
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
        for arm, table in (("base", "clause_vec"), ("ctx", "clause_vec_ctx")):
            full = knn(db, table, qv, max(DEPTHS))
            cands[arm] = full
            rec[arm] = {"n": len(full)}
            for d in DEPTHS:
                rec[arm][f"rank@{d}"] = rank_of(gold, full[:d])
        # 同预算并集 @1000：把 C 换成该臂，B/D 等其余通道不变（从 funnel 的副本实现取）
        fts = F.channel_fts(db, it["query"], 1000)
        mod = F.channel_modality(db, it.get("v2", {}).get("modality") or None)
        rec["union_prod"] = {  # 生产上限口径：B 只 20 条
            "base": gold in set(F.channel_fts(db, it["query"], 20)) | set(cands["base"][:20]),
            "ctx": gold in set(F.channel_fts(db, it["query"], 20)) | set(cands["ctx"][:20]),
        }
        rec["union_same_budget@1000"] = {
            "base": gold in set(fts) | set(cands["base"]),
            "ctx": gold in set(fts) | set(cands["ctx"]),
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
