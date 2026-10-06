"""事实核查：检验外部评估关于"分辨力 / 样本量"的两个说法，用我们自己的实测分布重算。

**为什么要自己算**：业主分工明确 —— 涉及事实核查的由我自己做，不转述二手结论。

要核的两条：
 ① 它说："若 MDE=8.18pt 真是按固定 α/power 定义的，那『+10pt 只有一半把握被测出』与 MDE 的定义不一致。"
    —— 方向对不对？我原来那个 8.18 到底是什么量？
 ② 它给的样本量换算："MDE 从 8.18 降到 5pt ⇒ 120×(8.18/5)² ≈ 322 rows"。
    —— 这个换算用的是**条目**口径；而我们刚确立必须用**簇**口径。两者是否一致？

做法：直接用 `cluster-significance.json` 里簇级 bootstrap 的差值 sd（= 差值的标准误 SE），
按正态近似算：显著性阈值、各真实效应下的把握度、以及达到目标把握度所需的簇数/条目数。
**不引入新的模拟，只做定义清晰的正态换算**（近似已注明）。
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "power-factcheck.json"

Z_A = 1.959963985          # 双尾 0.05
Z_B = 0.8416212336         # 80% 把握度


def phi(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def power(delta: float, se: float, alpha_z: float = Z_A) -> float:
    """真实效应 delta、差值标准误 se 时，双尾 α 检验的把握度（正态近似）。"""
    return phi(delta / se - alpha_z) + phi(-delta / se - alpha_z)


def main() -> int:
    cs = json.loads((HERE / "cluster-significance.json").read_text(encoding="utf-8"))
    h = cs["subsets"]["headline_120"]
    a = cs["subsets"]["all_171"]
    se_h = h["cluster_power"]["sd_of_diff_pp"]
    se_a = a["cluster_power"]["sd_of_diff_pp"]
    n_h, k_h = h["n_items"], h["n_clusters"]
    n_a, k_a = a["n_items"], a["n_clusters"]

    out: dict = {
        "why": "业主分工：事实核查由本仓自己做 —— 不转述外部结论",
        "input": {
            "headline_120": {"rows": n_h, "clusters": k_h, "se_of_diff_pp": se_h},
            "all_171": {"rows": n_a, "clusters": k_a, "se_of_diff_pp": se_a},
            "source": "cluster-significance.json 的簇级 bootstrap 差值 sd（10000 次）",
        },
    }

    # ① 8.18pt 是什么量？
    out["what_is_8_18"] = {
        "definition_used": "1.96 × SE（双尾 0.05 的**显著性阈值**）",
        "is_it_a_proper_MDE": False,
        "note": ("标准意义上的 MDE 通常指「给定 α 与把握度（如 80%）下可检出的最小效应」。"
                 "1.96×SE 是**显著性阈值**，恰好等于**把握度 50%** 那一点，不是 80% 把握度的 MDE。"),
        "power_at_various_effects_headline": {
            f"{d}pt": round(power(d, se_h), 4) for d in (5, 8, 8.18, 10, 12, 15)
        },
        "proper_MDE_80pct_headline_pp": round((Z_A + Z_B) * se_h, 2),
        "proper_MDE_80pct_all171_pp": round((Z_A + Z_B) * se_a, 2),
    }

    # ② 样本量换算：条目口径 vs 簇口径
    def n_for(target_pp: float, se: float, rows: int, clusters: int, by: str):
        """SE 与 1/sqrt(单位数) 成正比 ⇒ 需要多少单位。"""
        need = clusters * (se / (target_pp / (Z_A + Z_B))) ** 2
        return {"by": by, "target_MDE_80pct_pp": target_pp,
                "clusters_needed": round(need, 1),
                "rows_if_same_ratio": round(need * rows / clusters, 1)}

    out["sample_size_to_reach_MDE"] = {
        "external_claim": "120×(8.18/5)² ≈ 322 rows（**条目**口径）",
        "our_check_rows_basis": round(n_h * (se_h / (5 / (Z_A + Z_B))) ** 2, 1),
        "our_check_cluster_basis": n_for(5.0, se_h, n_h, k_h, "clusters"),
        "external_target_350_400_rows_180_200_clusters": {
            "implied_SE_at_190_clusters_pp": round(se_h * math.sqrt(k_h / 190), 2),
            "implied_MDE_80pct_at_190_clusters_pp": round(
                (Z_A + Z_B) * se_h * math.sqrt(k_h / 190), 2),
            "verdict": "**达不到 5pt**（80% 把握度下约 6.8pt）—— 它这条换算把簇口径丢了，正是它自己警告过的错",
        },
    }

    # ③ 结论
    out["conclusions"] = [
        "① 它对**表述**的纠正是对的：8.18pt 不是 80% 把握度的 MDE，而是显著性阈值（≈50% 把握度点）。",
        "   我原来那句「+10pt 只有约一半把握」**错了**：实测把握度约 "
        f"{round(power(10, se_h)*100)}%。（改正后仍不影响「本次没检测到效果」这个结论。）",
        f"   按 80% 把握度算，主结果口径的真实 MDE 是 **{round((Z_A+Z_B)*se_h,2)}pt**，不是 8.18pt。",
        "② 它给的 322 rows 换算是**条目口径**；按簇口径（我们刚确立必须这么算）到 5pt 需要 "
        f"**{n_for(5.0, se_h, n_h, k_h, 'clusters')['clusters_needed']} 个簇**（≈"
        f"{n_for(5.0, se_h, n_h, k_h, 'clusters')['rows_if_same_ratio']} 行）。",
        "③ 它给的目标「350–400 行、180–200 簇」在 80% 把握度下对应约 "
        f"{round((Z_A+Z_B)*se_h*math.sqrt(k_h/190),2)}pt —— **是进步，但够不到 5pt**。若要 5pt，得 ~349 簇。",
        "⚠ 以上全是**正态近似的换算**，不是新模拟；且 SE 来自 10000 次簇级 bootstrap（已注明）。",
    ]
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
