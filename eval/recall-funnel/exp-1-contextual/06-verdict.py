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

    # ── hard_fail 逐条检查 ────────────────────────────────────────────────
    hard = []
    if ab["meta"]["n_ctx"] != ab["meta"]["n_base"]:
        hard.append(f"两臂条目数不一致：{ab['meta']['n_base']} vs {ab['meta']['n_ctx']}")
    if flip["in"] == 0 and flip["out"] == 0 and abs(net_pp) < 0.01:
        hard.append("两臂逐条完全相同 ⇒ 实验臂文本很可能没生效（查 02/03）")
    if head["ctx_vec@20"] is not None and base is not None and head["ctx_vec@20"] < head["base_vec@20"]:
        hard.append(f"@20 下降：{head['base_vec@20']:.4f} → {head['ctx_vec@20']:.4f}"
                    "（止损线：不得只报涨的那一项）")

    # ── 机械判决 ──────────────────────────────────────────────────────────
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
        "verdict": "作废（仪器/归因问题）" if hard else verdict,
        "next_step_per_plan": ({
            "推广": "继续做结构化检索表示 + 重建索引；之后再处理 Top1000→Top20 的截断",
            "观察": "单次跑分不出来 ⇒ 按 README §七 跑备选臂（E1b 只加标准名 / E1c 加路径 / E1d 正文前置）",
            "放弃": "问题不只是条文上下文 ⇒ 改走「查询改写 / 别名扩展 / 大白话→标准术语」那条路",
        }[verdict] if not hard else "先查 hard_fail 那几条，别解释结果"),
        "rescued_from_104": {"n": len(ab.get("rescued_from_104", [])),
                             "ids": ab.get("rescued_from_104", [])[:30]},
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
