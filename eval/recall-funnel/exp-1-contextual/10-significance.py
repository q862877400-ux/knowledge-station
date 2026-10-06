"""E1 显著性复核：**这个实验到底能分辨多大的效果**？观测到的差异是不是噪声？

为什么要单独算：主结果只有 120 条、且这 120 条只落在 79 条独立条文上。
单看百分点（+0.83pt / −2.50pt）会**把噪声读成结论**——而且两个方向都会读错。

本实验是**同一批条目的配对比较** ⇒ 用 McNemar 的精确二项检验：
只统计"两种不一致对"（翻进 k_in / 翻出 k_out），做双侧精确二项检验。
并给出**最小可检测效果**（n 对不一致时，要多少净差才到 p<0.05）。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-1-contextual\\10-significance.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "significance.json"


def binom_two_sided(k: int, n: int) -> float:
    """精确二项检验（p=0.5）双侧 p 值。"""
    if n == 0:
        return 1.0
    def pmf(i):
        return math.comb(n, i) * 0.5 ** n
    obs = pmf(k)
    return min(1.0, sum(pmf(i) for i in range(n + 1) if pmf(i) <= obs + 1e-12))


def min_detectable(n: int) -> int:
    """n 对不一致时，达到双侧 p<0.05 所需的**净差**（= |2k-n| 的最小值）。"""
    for net in range(0, n + 1):
        for k in (n // 2 - net // 2, n // 2 + (net + 1) // 2):
            if 0 <= k <= n and abs(2 * k - n) == net and binom_two_sided(k, n) < 0.05:
                return net
    return n


def main() -> int:
    ab = json.loads((HERE / "ab-result.json").read_text(encoding="utf-8"))
    rows = []
    for label, blk in (("主结果 120", ab["headline_120"]), ("全量 171", ab["all_171"])):
        for d in (20, 100, 1000):
            f = blk[f"vec@{d}_flip"]
            n = f["in"] + f["out"]
            p = binom_two_sided(f["in"], n)
            md = min_detectable(n)
            rows.append({
                "subset": label, "cutoff": f"@{d}",
                "flip_in": f["in"], "flip_out": f["out"], "discordant": n,
                "net_items": f["in"] - f["out"], "net_pp": f["net_pp"],
                "exact_binom_two_sided_p": round(p, 4),
                "significant_at_0.05": p < 0.05,
                "min_detectable_net_items": md,
                "min_detectable_pp": round(md / blk["n"] * 100, 2),
            })
    result = {
        "why": "配对比较 ⇒ 用 McNemar 的精确二项检验；只看百分点会把噪声读成结论",
        "test": "exact two-sided binomial, p=0.5, on the discordant pairs",
        "rows": rows,
        "conclusion": [
            "没有任何一档达到显著（全部 p 远大于 0.05）——**两个方向都不显著**。",
            "⇒ 正确的说法是「**本次没有检测到效果**」，而**不是**「变差了」或「略微变好」。",
            "更要紧的是**这个实验的分辨力**：@1000 只有 19 对不一致，要到净差 11 条（≈9.2pt）才显著；",
            "这正是预登记把「推广」门槛定在 +12pt 的原因 —— 小改动本来就不该指望被这个样本量测出来。",
        ],
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1))
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
