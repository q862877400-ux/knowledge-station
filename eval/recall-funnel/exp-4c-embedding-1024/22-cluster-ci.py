"""E4c · 步骤 3：**簇级置信区间**（与 E4 第一轮 / E4b 第二轮同法，便于横向比较）。

簇 = `gold_cr_id`（同一条条文上的多个提问算一簇，防同一答案重复计数）。
配对簇级 bootstrap，10000 次重抽，随机种子**写死**（`20261009`）⇒ 连跑两次逐字节相同。

只读；不改任何读数。
用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-4c-embedding-1024\\22-cluster-ci.py
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "ab-1024-cluster-ci.json"
SEED = 20261009
N_BOOT = 10000
KEY = "rank@1000"


def main() -> int:
    per = [json.loads(l) for l in (HERE / "ab-1024-per-query.jsonl")
           .read_text(encoding="utf-8").splitlines() if l.strip()]
    gold = {json.loads(l)["i"]: json.loads(l)["v2"]["gold_cr_id"]
            for l in (ROOT / "eval" / "recall-funnel" / "benchmark-v2.jsonl")
            .read_text(encoding="utf-8").splitlines() if l.strip()}
    for r in per:
        r["_cluster"] = gold[r["i"]]

    def blk(rows: list[dict]) -> dict:
        by_cluster: dict[str, list[dict]] = {}
        for r in rows:
            by_cluster.setdefault(r["_cluster"], []).append(r)
        clusters = list(by_cluster)

        def delta(sub: list[dict]) -> float:
            n = len(sub)
            return sum(1 for r in sub if r["d1024"][KEY]) / n - \
                sum(1 for r in sub if r["d512"][KEY]) / n

        obs = delta(rows) * 100
        rng = random.Random(SEED)
        boots = []
        for _ in range(N_BOOT):
            pick = [clusters[rng.randrange(len(clusters))] for _ in clusters]
            sub = [r for c in pick for r in by_cluster[c]]
            boots.append(delta(sub) * 100)
        boots.sort()
        lo = boots[int(0.025 * N_BOOT)]
        hi = boots[int(0.975 * N_BOOT)]
        le0 = sum(1 for b in boots if b <= 0) / N_BOOT
        ge0 = sum(1 for b in boots if b >= 0) / N_BOOT
        return {
            "n": len(rows), "n_clusters": len(clusters),
            "delta_pp": round(obs, 2),
            "ci95_pp": [round(lo, 2), round(hi, 2)],
            # ⚠ 上界截到 1.0：观测 Δ≈0 时 le0 与 ge0 都接近 0.5 ⇒ 2*min 会 >1（本轮实测 1.079）。
            # 这是本脚本新加的一行；`exp-4b/13-cluster-ci.py` 用的是**同一公式、无截断**
            # （它那次 Δ 远离 0 ⇒ p=0.0000，没暴露）⇒ 那条潜伏缺陷**已登记、未改那个已冻结的文件**。
            "p_two_sided": round(min(1.0, 2 * min(le0, ge0)), 4),
            "flip_in": sum(1 for r in rows if not r["d512"][KEY] and r["d1024"][KEY]),
            "flip_out": sum(1 for r in rows if r["d512"][KEY] and not r["d1024"][KEY]),
        }

    head = [r for r in per if r["headline"]]
    result = {
        "experiment": "E4c 簇级置信区间（配对簇级 bootstrap；唯一变量 = 输出维度）",
        "endpoint": f"Vector {KEY}",
        "cluster_unit": "gold_cr_id",
        "method": f"配对簇级 bootstrap，{N_BOOT} 次重抽，seed={SEED}（写死 ⇒ 可复跑）",
        "headline_120": blk(head),
        "all_171": blk(per),
        "compare_with_prior_rounds": {
            "round1_model_swap_headline_delta_pp": 32.5,
            "round1_ci95_pp": [22.95, 42.52],
            "round2_prefix_headline_delta_pp": 15.84,
            "round2_ci95_pp": [9.43, 22.73],
            "note": "第一轮=换模型；第二轮=同模型加查询指令前缀；本轮=同模型升维（512→1024）。"
                    "三个数**不许相加** —— 不是同一条链上的独立增益。",
        },
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1))
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
