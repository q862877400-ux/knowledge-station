"""E1 复核补算 ①：**簇级**显著性 —— 按"独立条文"重做配对检验与分辨力。

外部评估 2026-10-06 打回：我报的 9.17pt 分辨力是**按条目**算的，但主结果 120 条只落在
**64 条独立条文**上（平均 1.88 条问法/条文），同一条文的几条问法**几乎完全相关**。

本脚本做三件它要求的事（全部用已存产物，**不需要重算向量**）：
 1. **设计效应**：从簇间/簇内方差直接估，不靠猜。
 2. **簇级 bootstrap**：以「独立条文」为重抽样单位，给差值的 95% 区间与 p 值。
 3. **簇级分辨力**：这种重抽样下，@1000 要净差多少才到 0.05。

簇 = `gold_cr_id`（同一条文的多条问法算一簇）。同时给 headline_120 与 all_171 两个口径。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-1-contextual\\13-cluster-significance.py
"""
from __future__ import annotations

import json
import random
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "cluster-significance.json"
N_BOOT = 10000
SEED = 20261006


def main() -> int:
    ab = json.loads((HERE / "ab-result.json").read_text(encoding="utf-8"))
    v2 = {json.loads(l)["i"]: json.loads(l)
          for l in (HERE.parent / "benchmark-v2.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    per = ab["per_query"]

    def rows_of(pred):
        return [{"i": r["i"], "cluster": v2[r["i"]]["v2"]["gold_cr_id"],
                 "base20": bool(r["base"]["rank@20"]), "ctx20": bool(r["ctx"]["rank@20"]),
                 "base100": bool(r["base"]["rank@100"]), "ctx100": bool(r["ctx"]["rank@100"]),
                 "base1000": bool(r["base"]["rank@1000"]), "ctx1000": bool(r["ctx"]["rank@1000"])}
                for r in per if pred(r)]

    subsets = {"headline_120": rows_of(lambda r: r["headline"]), "all_171": rows_of(lambda r: True)}
    rnd = random.Random(SEED)
    report = {}

    for name, rows in subsets.items():
        groups: dict[str, list[dict]] = {}
        for r in rows:
            groups.setdefault(r["cluster"], []).append(r)
        cl = list(groups.values())
        n, k = len(rows), len(cl)
        rep = {"n_items": n, "n_clusters": k, "items_per_cluster": round(n / k, 3)}

        for cut in (20, 100, 1000):
            b, c = f"base{cut}", f"ctx{cut}"
            # 预先按簇求和 ⇒ 每次重抽样只需 O(k)
            gb = [sum(r[b] for r in g) for g in cl]
            gc = [sum(r[c] for r in g) for g in cl]
            gn = [len(g) for g in cl]
            item_b = sum(gb) / n
            item_c = sum(gc) / n
            diffs = []
            for _ in range(N_BOOT):
                idx = [rnd.randrange(k) for _ in range(k)]
                tb = sum(gb[i] for i in idx); tc = sum(gc[i] for i in idx)
                tn = sum(gn[i] for i in idx)
                diffs.append((tc - tb) / tn)
            diffs.sort()
            lo, hi = diffs[int(N_BOOT * 0.025)], diffs[int(N_BOOT * 0.975)]
            le = sum(1 for d in diffs if d <= 0)
            ge = sum(1 for d in diffs if d >= 0)
            p_two = min(1.0, 2 * min(le, ge) / N_BOOT)
            rep[f"@{cut}"] = {
                "item_base": round(item_b, 4), "item_ctx": round(item_c, 4),
                "item_diff_pp": round((item_c - item_b) * 100, 2),
                "cluster_boot_diff_pp_mean": round(st.mean(diffs) * 100, 2),
                "cluster_boot_ci95_pp": [round(lo * 100, 2), round(hi * 100, 2)],
                "cluster_boot_p_two_sided": round(p_two, 4),
                "significant_at_0.05": p_two < 0.05,
            }
            if cut == 1000:
                item_d = [r[c] - r[b] for r in rows]
                cl_means = [st.mean([r[c] - r[b] for r in g]) for g in cl]
                iv, cv = st.variance(item_d), st.variance(cl_means)
                deff = (cv / iv) * (n / k) if iv else None
                rep["design_effect"] = {
                    "deff": round(deff, 3) if deff else None,
                    "effective_n": round(n / deff, 1) if deff else None,
                    "note": "deff ≈ (簇间方差 / 条目方差) × 平均簇大小；>1 = 条目口径高估了独立信息量",
                }
                rep["cluster_power"] = {
                    "method": f"簇级 bootstrap（{N_BOOT} 次）下差值分布 ±1.96 sd 的宽度",
                    "sd_of_diff_pp": round(st.pstdev(diffs) * 100, 2),
                    "min_detectable_pp": round(1.96 * st.pstdev(diffs) * 100, 2),
                    "min_detectable_items": round(1.96 * st.pstdev(diffs) * n),
                }
        report[name] = rep

    # 独立条文数（按类型）
    from collections import Counter
    by_kind = {}
    for kind in ("定义", "要求"):
        rr = rows_of(lambda r, K=kind: r["kind"] == K and r["headline"])
        by_kind[kind] = {"n_items": len(rr), "n_clusters": len({r["cluster"] for r in rr})}

    result = {
        "why": "外部评估打回：分辨力按条目算，但 120 条只落在 64 条独立条文上 ⇒ 必须按簇重算",
        "cluster_definition": "gold_cr_id（同一条文的多条问法算一簇）",
        "n_bootstrap": N_BOOT, "seed": SEED,
        "headline_by_kind": by_kind,
        "subsets": report,
        "reading": [
            "`item_*` 是上一版口径（把条目当独立）—— 偏乐观。",
            "`cluster_boot_*` 以**独立条文**为重抽样单位 —— 这才是该报的口径。",
            "方向一致而显著性更弱 ⇒ 「没检测到效果」的结论不变，但 p 值与分辨力必须按簇口径说。",
        ],
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1))
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
