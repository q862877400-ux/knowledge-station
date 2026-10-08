"""E4 第二轮 · B 臂的**簇级置信区间**（与 E4 第一轮同法，便于横向比较）。

为什么要有它：`stop-loss.json` 的 B 臂判据只写"≥10pt ⇒ 进生产评估"，
但 E4 第一轮报的是**簇级 95% CI + 簇级 p**（`ab-result.json` 的 +32.50pt，CI [+22.95, +42.52]）。
不同法报数就没法横向比 ⇒ 这里按同法补上（配对簇级 bootstrap）。

簇 = `gold_cr_id`（同一条条文上的多个提问算一簇，防同一答案重复计数）。
随机种子**写死**（`20261009`）⇒ 连跑两次逐字节相同。

只读；不改任何读数。
用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-4b-embedding-round2\\13-cluster-ci.py
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "prefix-cluster-ci.json"
SEED = 20261009
N_BOOT = 10000
KEY = "rank@1000"


def main() -> int:
    per = [json.loads(l) for l in (HERE / "prefix-ab-per-query.jsonl")
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
            return sum(1 for r in sub if r["prefix"][KEY]) / n - \
                sum(1 for r in sub if r["noprefix"][KEY]) / n

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
            "p_two_sided": round(2 * min(le0, ge0), 4),
            "flip_in": sum(1 for r in rows if not r["noprefix"][KEY] and r["prefix"][KEY]),
            "flip_out": sum(1 for r in rows if r["noprefix"][KEY] and not r["prefix"][KEY]),
        }

    head = [r for r in per if r["headline"]]
    result = {
        "experiment": "E4 第二轮 · B 臂 簇级置信区间（配对簇级 bootstrap）",
        "endpoint": f"Vector {KEY}",
        "cluster_unit": "gold_cr_id",
        "method": f"配对簇级 bootstrap，{N_BOOT} 次重抽，seed={SEED}（写死 ⇒ 可复跑）",
        "headline_120": blk(head),
        "all_171": blk(per),
        "compare_with_round1": {
            "round1_model_swap_headline_delta_pp": 32.5,
            "round1_ci95_pp": [22.95, 42.52],
            "note": "第一轮是**换模型**（bge→Qwen3，无前缀）；本轮是**同模型加查询指令前缀**。"
                    "两个数不许相加当'总共'——它们不是同一条链上的独立增益（第一轮的两臂都无前缀）。",
        },
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1))
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
