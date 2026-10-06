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
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
SL = HERE / "stop-loss.json"
AB = HERE / "ab-result.json"
OUT = HERE / "verdict.json"
EXP_DB = HERE / "exp.db"

PRIMARY = "vec@1000"


def set_check() -> dict | None:
    """**真集合比较**（独立复核 F5）：两臂的 `clause_revision_id` 集合是否完全一致。

    为什么不能只比数量：**数量相等但成员不同，名次照样不可比** —— 这正是
    `stop-loss.json` 第 3 条要挡的。这里用双向 `EXCEPT` 各数一次。

    ⚠ 读 `vec0` 表**必须**加载 sqlite-vec 扩展（本批已踩过三次：不加载就报 no such module: vec0）。
    """
    if not EXP_DB.exists():
        return None
    import sqlite3
    from src.core.storage.sqlite_db import load_vec_extension
    c = sqlite3.connect(f"file:{EXP_DB.as_posix()}?mode=ro", uri=True)
    try:
        if not load_vec_extension(c):
            return None
        only_base = c.execute(
            "SELECT COUNT(*) FROM clause_vec v WHERE NOT EXISTS ("
            "  SELECT 1 FROM clause_vec_ctx x WHERE x.clause_revision_id = v.clause_revision_id)"
        ).fetchone()[0]
        only_ctx = c.execute(
            "SELECT COUNT(*) FROM clause_vec_ctx x WHERE NOT EXISTS ("
            "  SELECT 1 FROM clause_vec v WHERE v.clause_revision_id = x.clause_revision_id)"
        ).fetchone()[0]
        return {"only_base": only_base, "only_ctx": only_ctx,
                "identical": only_base == 0 and only_ctx == 0,
                "rule": "双向 EXCEPT 均为 0 ⇔ 两臂候选集合完全相同"}
    finally:
        c.close()


def binom_two_sided(k: int, n: int) -> float:
    """精确二项检验（p=0.5）双侧 p 值 —— 配对比较就该用它，不该只看百分点。"""
    if n == 0:
        return 1.0
    pmf = lambda i: math.comb(n, i) * 0.5 ** n       # noqa: E731
    obs = pmf(k)
    return min(1.0, sum(pmf(i) for i in range(n + 1) if pmf(i) <= obs + 1e-12))


def min_detectable(n: int) -> int | None:
    """n 对不一致时，达到双侧 p<0.05 所需的净差条数；**做不到就返回 None**。

    ⚠ 2026-10-06 更正（独立复核 F13）：初版写 `return n` 兜底，于是 n=5 时报出
    "5 条 / 4.17pt" 这种**永远不可能达到**的值 —— n=5 时双侧最小 p = 0.0625 > 0.05，
    **没有任何一种结果能显著**。兜底必须是「不可能」，不能是一个像结论的数。
    """
    for net in range(0, n + 1):
        for k in (n // 2 - net // 2, n // 2 + (net + 1) // 2):
            if 0 <= k <= n and abs(2 * k - n) == net and binom_two_sided(k, n) < 0.05:
                return net
    return None


def main() -> int:
    if not AB.exists():
        print(f"⛔ 还没有 {AB.name} —— 先把向量算完、跑 04-ab-eval.py")
        return 1
    sl = json.loads(SL.read_text(encoding="utf-8"))
    ab = json.loads(AB.read_text(encoding="utf-8"))
    head = ab["headline_120"]

    base = head["base_vec@1000"]
    ctx = head["ctx_vec@1000"]
    flip = head["vec@1000_flip"]
    # ⚠ 净提升用**条数**算，不用四舍五入后的率相减（独立复核 F6）：
    #   用率会得 0.3667−0.3583 = 0.84，用条数得 1/120 = 0.8333 ⇒ 0.83。
    #   同一批、同一个量不该有两个值；以条数为准。
    net_items = flip["in"] - flip["out"]
    net_pp = round(net_items / head["n"] * 100, 2)

    # ── 仪器类 hard_fail（**只放"仪器坏了 / 结论不可归因"**）────────────────
    # ⚠ 2026-10-06 两次更正：
    #   ① 初版把"@20 下降"也塞进这里，于是判成"作废（仪器/归因问题）"——**那是错的**：
    #      @20 下降是**真实的负结果**，不是仪器故障。两者混在一起会把结论说反。
    #   ② 独立复核 F5：`stop-loss.json` 第 3 条要求的是"**条目集合**有任何一处不一致"，
    #      初版只查了**数量**（`n_ctx != n_base`）—— 那是弱化实现。现补**真集合比较**。
    hard = []
    if ab["meta"]["n_ctx"] != ab["meta"]["n_base"]:
        hard.append(f"两臂条目数不一致：{ab['meta']['n_base']} vs {ab['meta']['n_ctx']}")
    setchk = set_check()
    if setchk and not setchk["identical"]:
        hard.append(f"两臂条目**集合**不一致：仅对照臂有 {setchk['only_base']} 条、"
                    f"仅实验臂有 {setchk['only_ctx']} 条")
    if flip["in"] == 0 and flip["out"] == 0 and abs(net_pp) < 0.01:
        hard.append("两臂逐条完全相同 ⇒ 实验臂文本很可能没生效（查 02/03）")

    # ── 负向发现（**要报，但不是"作废"**）──────────────────────────────────
    # ⚠ 2026-10-06 第二次更正：这里原先把"@20 下降 2.5pt"直接写成"负向发现"，
    #   而没说它**是不是可分辨**。算过之后：@20 的分歧对只有 5 对（翻进 1 / 翻出 4），
    #   精确二项双侧 **p = 0.375** ⇒ **在噪声里**。把它说成"实打实变差"是**在相反方向上超出证据**。
    #   ⇒ 现在每条负向发现都**必须带显著性**；同时还报**这个样本量最小能测出多大的效果**。
    negatives = []
    for depth in (20, 100, 1000):
        b, c = head.get(f"base_vec@{depth}"), head.get(f"ctx_vec@{depth}")
        if b is None or c is None or c >= b:
            continue
        f = head[f"vec@{depth}_flip"]
        p = binom_two_sided(f["in"], f["in"] + f["out"])
        negatives.append({
            "what": f"Vector@{depth} 下降：{b:.4f} → {c:.4f}（{round((c-b)*100,2)}pt）",
            "flip_in": f["in"], "flip_out": f["out"],
            "exact_binom_two_sided_p": round(p, 4),
            "within_noise": p >= 0.05,
        })
    if head["base_union@1000"] is not None and head["ctx_union@1000"] is not None \
            and head["ctx_union@1000"] < head["base_union@1000"]:
        negatives.append({"what": f"六路并集@1000 下降：{head['base_union@1000']:.4f} →"
                                  f" {head['ctx_union@1000']:.4f}",
                          "flip_in": None, "flip_out": None,
                          "exact_binom_two_sided_p": None, "within_noise": None})

    # ── 本次实验的分辨力（**防止把"没测出来"说成"没有效果"或"变差了"**）──────
    power = {}
    for d in (20, 100, 1000):
        f = head[f"vec@{d}_flip"]
        n = f["in"] + f["out"]
        md = min_detectable(n)
        power[f"@{d}"] = {
            "discordant_pairs": n,
            "min_detectable_net_items": md,
            "min_detectable_pp": (round(md / head["n"] * 100, 2) if md is not None else None),
            "note": ("对所有不一致对数而言，这种规模**任何结果都不可能达到 p<0.05**"
                     if md is None else None),
        }

    if hard:
        verdict = "作废（仪器问题，不许解释结果）"
    else:
        if net_pp >= 12 and flip["in"] >= 3 * max(flip["out"], 1):
            verdict = "推广"
        elif net_pp >= 5:
            verdict = "观察"
        else:
            verdict = "放弃（未检测到效果）"

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
        "arm_set_check": setchk,
        "negative_findings": negatives,
        "power_of_this_run": power,
        "verdict": verdict,
        "next_step_per_plan": ({
            "推广": "继续做结构化检索表示 + 重建索引；之后再处理 Top1000→Top20 的截断",
            "观察": "单次跑分不出来 ⇒ 按 README §七 跑备选臂（E1b 只加标准名 / E1c 加路径 / E1d 正文前置）",
            "放弃（未检测到效果）":
                "本次**没有检测到效果**（不是「变差了」）⇒ 按预先分叉改走「查询改写 / 别名扩展 / 大白话→标准术语」；"
                "若要试备选臂，每次只改文本这一处、各自单独写止损线",
        }.get(verdict, "先查 hard_fail 那几条，别解释结果")),
        "how_to_read_this": [
            "配对比较 ⇒ 看**分歧对**（翻进/翻出）与精确二项 p，不看百分点。",
            "本次每一档 p 都远大于 0.05 ⇒ **两个方向都不显著**；",
            "结合 power_of_this_run：@1000 要净差 11 条（≈9.2pt）才显著 ⇒",
            "**这个样本量只能分辨大效果**，小改动本来就测不出来（这正是预登记门槛定在 +12pt 的原因）。",
        ],
        "rescued_from_104": {"n": len(ab.get("rescued_from_104", [])),
                             "ids": ab.get("rescued_from_104", [])[:30]},
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
