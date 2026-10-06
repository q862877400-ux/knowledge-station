"""E1 步骤 6：按**预登记的阈值**机械出判决（FR-014）。

**为什么要单独一个脚本**：止损线是跑之前写死的（`stop-loss.json`），
判决就必须由它**机械算出来**，而不是跑完之后人看着数字"感觉一下"。
本脚本只做三件事：读 `stop-loss.json`、读 `ab-result.json`、输出 `verdict.json`。

判决规则（与 stop-loss.json 一一对应）：
 · **推广**：净提升 ≥ +12pt **且** 翻进来的 ≥ 3 × 翻出去的
 · **观察**：净提升 +5 ~ +12pt
 · **放弃**：净提升 < +5pt
另按 hard_fail_conditions 逐条检查（任一命中 ⇒ 结论标为"作废/不可归因"）。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-1-contextual\\06-verdict.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SL = HERE / "stop-loss.json"
AB = HERE / "ab-result.json"
OUT = HERE / "verdict.json"

PRIMARY = "vec@1000"


def main() -> int:
    if not AB.exists():
        print(f"⛔ 还没有 {AB.name} —— 先把向量算完、跑 04-ab-eval.py")
        return 1
    sl = json.loads(SL.read_text(encoding="utf-8"))
    ab = json.loads(AB.read_text(encoding="utf-8"))
    head = ab["headline_120"]

    base = head["base_vec@1000"]
    ctx = head["ctx_vec@1000"]
    net_pp = round((ctx - base) * 100, 2)
    flip = head["vec@1000_flip"]

    # ── 仪器类 hard_fail（**只放"仪器坏了 / 结论不可归因"**）────────────────
    # ⚠ 2026-10-06 更正：初版把"@20 下降"也塞进这里，于是判成"作废（仪器/归因问题）"——
    #   **那是错的**：@20 下降是**真实的负结果**，不是仪器故障。两者混在一起会把结论说反。
    #   "合并成一句"正是本仓纪律禁止的事，故拆成两个字段。
    hard = []
    if ab["meta"]["n_ctx"] != ab["meta"]["n_base"]:
        hard.append(f"两臂条目数不一致：{ab['meta']['n_base']} vs {ab['meta']['n_ctx']}")
    if flip["in"] == 0 and flip["out"] == 0 and abs(net_pp) < 0.01:
        hard.append("两臂逐条完全相同 ⇒ 实验臂文本很可能没生效（查 02/03）")

    # ── 负结果（**要报，但不是"作废"**）────────────────────────────────────
    negatives = []
    for depth in (20, 100):
        b, c = head.get(f"base_vec@{depth}"), head.get(f"ctx_vec@{depth}")
        if b is not None and c is not None and c < b:
            negatives.append(f"Vector@{depth} 下降：{b:.4f} → {c:.4f}"
                             f"（{round((c-b)*100,2)}pt）")
    if head["base_union@1000"] is not None and head["ctx_union@1000"] is not None \
            and head["ctx_union@1000"] < head["base_union@1000"]:
        negatives.append(f"六路并集@1000 下降：{head['base_union@1000']:.4f} →"
                         f" {head['ctx_union@1000']:.4f}")

    if hard:
        verdict = "作废（仪器问题，不许解释结果）"
    else:
        if net_pp >= 12 and flip["in"] >= 3 * max(flip["out"], 1):
            verdict = "推广"
        elif net_pp >= 5:
            verdict = "观察"
        else:
            verdict = "放弃"

    out = {
        "experiment": sl["experiment"],
        "primary_endpoint": sl["primary_endpoint"],
        "baseline_from_stop_loss": sl["baseline"],
        "measured": {
            "headline_n": head["n"],
            "base_vec@20": head["base_vec@20"], "ctx_vec@20": head["ctx_vec@20"],
            "base_vec@100": head["base_vec@100"], "ctx_vec@100": head["ctx_vec@100"],
            "base_vec@1000": base, "ctx_vec@1000": ctx,
            "base_union@1000": head["base_union@1000"], "ctx_union@1000": head["ctx_union@1000"],
            "net_gain_pp_vec@1000": net_pp,
            "flip_vec@1000": flip,
            "flip_union@1000": head["union@1000_flip"],
        },
        "decision_rule_applied": {
            "thresholds": sl["decision_rule"],
            "matched": verdict,
        },
        "hard_fail_triggered": hard,
        "negative_findings": negatives,
        "verdict": verdict,
        "next_step_per_plan": ({
            "推广": "继续做结构化检索表示 + 重建索引；之后再处理 Top1000→Top20 的截断",
            "观察": "单次跑分不出来 ⇒ 按 README §七 跑备选臂（E1b 只加标准名 / E1c 加路径 / E1d 正文前置）",
            "放弃": "问题不只是条文上下文 ⇒ 改走「查询改写 / 别名扩展 / 大白话→标准术语」那条路",
        }.get(verdict, "先查 hard_fail 那几条，别解释结果")),
        "rescued_from_104": {"n": len(ab.get("rescued_from_104", [])),
                             "ids": ab.get("rescued_from_104", [])[:30]},
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
