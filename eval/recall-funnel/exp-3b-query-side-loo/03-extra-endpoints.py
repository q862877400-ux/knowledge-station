"""E3b · 附加：给**所有终点**算簇级 bootstrap 置信区间（不只主终点）。

为什么要单列：主终点（并集@1000）+3.51pt 不显著、判决"放弃"；
但副终点 **FTS@1000 +14.62pt**（13.45% → 28.07%）看起来很大。
按仓规**不许因为副终点好看就改主终点**，但**必须把副终点也按同一把尺子量**，
否则报告就是挑着说。本脚本只补置信区间，**不改判决**（判决见 verdict.json）。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-3b-query-side-loo\\03-extra-endpoints.py
"""
from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PER = HERE / "e3b-per-query.jsonl"
OUT = HERE / "e3b-extra-endpoints.json"
N_BOOT = 10000
SEED = 20261007
KEYS = ("union_same@20", "union_same@100", "union_same@1000", "union_prod",
        "fts@20", "fts@100", "fts@1000", "rank@20", "rank@100", "rank@1000")


def binom_two_sided(k: int, n: int) -> float:
    if n == 0:
        return 1.0
    pmf = lambda i: math.comb(n, i) * 0.5 ** n       # noqa: E731
    obs = pmf(k)
    return min(1.0, sum(pmf(i) for i in range(n + 1) if pmf(i) <= obs + 1e-12))


def main() -> int:
    rows = [json.loads(l) for l in PER.read_text(encoding="utf-8").splitlines() if l.strip()]
    v3 = {json.loads(l)["i"]: json.loads(l)
          for l in (ROOT / "eval" / "recall-funnel" / "benchmark-v3.jsonl")
          .read_text(encoding="utf-8").splitlines() if l.strip()}
    rnd = random.Random(SEED)
    out = {"_note": "只补置信区间；**判决不因此改变**（主终点仍是冻结的 union_same@1000 / all_171）",
           "n_bootstrap": N_BOOT, "seed": SEED, "subsets": {}}

    for label, sub in (("all_171", rows), ("headline_120", [r for r in rows if r["headline"]])):
        groups: dict[str, list[dict]] = {}
        for r in sub:
            groups.setdefault(v3[r["i"]]["v2"]["gold_cr_id"], []).append(r)
        cl = list(groups.values())
        k = len(cl)
        res = {}
        for key in KEYS:
            gb = [sum(1 for r in g if r["base"][key]) for g in cl]
            gc = [sum(1 for r in g if r["ctx"][key]) for g in cl]
            gn = [len(g) for g in cl]
            n = len(sub)
            item_b, item_c = sum(gb) / n, sum(gc) / n
            diffs = []
            for _ in range(N_BOOT):
                idx = [rnd.randrange(k) for _ in range(k)]
                tb = sum(gb[i] for i in idx); tc = sum(gc[i] for i in idx); tn = sum(gn[i] for i in idx)
                diffs.append((tc - tb) / tn)
            diffs.sort()
            lo, hi = diffs[int(N_BOOT * 0.025)], diffs[int(N_BOOT * 0.975)]
            le = sum(1 for d in diffs if d <= 0); ge = sum(1 for d in diffs if d >= 0)
            p = min(1.0, 2 * min(le, ge) / N_BOOT)
            fin = sum(1 for r in sub if not r["base"][key] and r["ctx"][key])
            fout = sum(1 for r in sub if r["base"][key] and not r["ctx"][key])
            n_disc = fin + fout
            res[key] = {
                "n_items": n, "n_clusters": k,
                "base": round(item_b, 4), "ctx": round(item_c, 4),
                "delta_pp": round((item_c - item_b) * 100, 2),
                "ci95_pp": [round(lo * 100, 2), round(hi * 100, 2)],
                "boot_p_two_sided": round(p, 4),
                "flip_in": fin, "flip_out": fout,
                "mcnemar_exact_p": round(binom_two_sided(fin, n_disc), 4) if n_disc else None,
                "significant_at_0.05": p < 0.05,
            }
        out["subsets"][label] = res

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for label, res in out["subsets"].items():
        print(f"=== {label} ===")
        for key, v in res.items():
            star = "★显著" if v["significant_at_0.05"] else ""
            print(f"  {key:16s} {v['base']:.4f}→{v['ctx']:.4f} ({v['delta_pp']:+6.2f}pt)"
                  f"  CI95[{v['ci95_pp'][0]:+6.2f},{v['ci95_pp'][1]:+6.2f}] p={v['boot_p_two_sided']:.4f}"
                  f" 进{v['flip_in']}/出{v['flip_out']} {star}")
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
