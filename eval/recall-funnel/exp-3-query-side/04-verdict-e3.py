"""E3 · 步骤 4：**机械判决**（结论由预登记阈值算出，不许跑完看着数字"感觉一下"）。

三件事：
 1. **仪器自检**：对照臂必须复现 `funnel-summary.json` 的基线数字；不复现 ⇒ 先查仪器，不许解释结果。
 2. **硬失败检查**：术语索引 ∩ 考卷 gold 必须为 0；注入词不得疑似泄漏；两臂条目集合一致。
 3. **机械判决**：按 `stop-loss.json` 的阈值（推广 ≥+9pt / 观察 +6~9pt / 放弃 <+6pt），
    并给**簇级 bootstrap** 的置信区间与 p 值（配对比较看簇，不看单点百分点）。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-3-query-side\\04-verdict-e3.py
"""
from __future__ import annotations

import json
import math
import random
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SL = HERE / "stop-loss.json"
RES = HERE / "e3-result.json"
PER = HERE / "e3-per-query.jsonl"
OUT = HERE / "verdict.json"
N_BOOT = 10000
SEED = 20261007

#: 对照臂必须复现的基线（funnel-summary.json / ab-result.json）
BASELINE = {"all_171": {"union_same@1000": 0.3918, "rank@1000": 0.345},
            "headline_120": {"union_same@1000": 0.4, "rank@1000": 0.3583}}


def binom_two_sided(k: int, n: int) -> float:
    if n == 0:
        return 1.0
    pmf = lambda i: math.comb(n, i) * 0.5 ** n       # noqa: E731
    obs = pmf(k)
    return min(1.0, sum(pmf(i) for i in range(n + 1) if pmf(i) <= obs + 1e-12))


def min_detectable(n: int) -> int | None:
    for net in range(0, n + 1):
        for k in (n // 2 - net // 2, n // 2 + (net + 1) // 2):
            if 0 <= k <= n and abs(2 * k - n) == net and binom_two_sided(k, n) < 0.05:
                return net
    return None


def main() -> int:
    if not RES.exists():
        print(f"⛔ 还没有 {RES.name} —— 先跑 03-run-e3.py")
        return 1
    sl = json.loads(SL.read_text(encoding="utf-8"))
    res = json.loads(RES.read_text(encoding="utf-8"))
    rows = [json.loads(l) for l in PER.read_text(encoding="utf-8").splitlines() if l.strip()]
    v3 = {json.loads(l)["i"]: json.loads(l)
          for l in (ROOT / "eval" / "recall-funnel" / "benchmark-v3.jsonl")
          .read_text(encoding="utf-8").splitlines() if l.strip()}

    # ── ① 仪器自检 ────────────────────────────────────────────────────────
    selfcheck = {}
    bad_instrument = []
    for label, want in BASELINE.items():
        got = {k: res["summary"][label]["base"][k] for k in want}
        ok = all(abs(got[k] - want[k]) < 0.002 for k in want)
        selfcheck[label] = {"want": want, "got": got, "ok": ok}
        if not ok:
            bad_instrument.append(f"对照臂未复现基线（{label}）：{got} vs {want}")
    print("[自检] 对照臂 vs 基线：", json.dumps(selfcheck, ensure_ascii=False))

    # ── ② 硬失败检查 ──────────────────────────────────────────────────────
    hard = list(bad_instrument)
    ac = res["anti_cheat"]
    if ac["index_cap_benchmark_gold"] != 0:
        hard.append(f"术语索引与考卷 gold 有交集：{ac['index_cap_benchmark_gold']} 条")
    if ac["injected_term_in_gold_events"] > 0:
        # 只要 hit 事件在**全库里很罕见**却频繁命中 gold，才算泄漏疑点；
        # 这里保守地全部列出，由阈值判断（share_lib 极低且命中多次）
        rare = [e for e in ac["injected_term_in_gold_samples"] if e["share_lib"] < 0.001]
        if len(rare) >= 3:
            hard.append(f"疑似间接泄漏：{len(rare)} 个注入词几乎只出现在 gold 里（全库占比 <0.1%）")

    # ── ③ 主终点 + 簇级 bootstrap ─────────────────────────────────────────
    KEY = "union_same@1000"
    for label, sub in (("all_171", [r for r in rows]),
                       ("headline_120", [r for r in rows if r["headline"]])):
        if not sub:
            continue
        groups: dict[str, list[dict]] = {}
        for r in sub:
            groups.setdefault(v3[r["i"]]["v2"]["gold_cr_id"], []).append(r)
        cl = list(groups.values())
        k = len(cl)
        gb = [sum(1 for r in g if r["base"][KEY]) for g in cl]
        gc = [sum(1 for r in g if r["ctx"][KEY]) for g in cl]
        gn = [len(g) for g in cl]
        n = len(sub)
        item_b, item_c = sum(gb) / n, sum(gc) / n
        rnd = random.Random(SEED)
        diffs = []
        for _ in range(N_BOOT):
            idx = [rnd.randrange(k) for _ in range(k)]
            tb = sum(gb[i] for i in idx); tc = sum(gc[i] for i in idx); tn = sum(gn[i] for i in idx)
            diffs.append((tc - tb) / tn)
        diffs.sort()
        lo, hi = diffs[int(N_BOOT * 0.025)], diffs[int(N_BOOT * 0.975)]
        le = sum(1 for d in diffs if d <= 0); ge = sum(1 for d in diffs if d >= 0)
        p = min(1.0, 2 * min(le, ge) / N_BOOT)
        fl_in = sum(1 for r in sub if not r["base"][KEY] and r["ctx"][KEY])
        fl_out = sum(1 for r in sub if r["base"][KEY] and not r["ctx"][KEY])
        res["summary"][label]["primary_cluster"] = {
            "key": KEY, "n_items": n, "n_clusters": k,
            "base": round(item_b, 4), "ctx": round(item_c, 4),
            "delta_pp": round((item_c - item_b) * 100, 2),
            "ci95_pp": [round(lo * 100, 2), round(hi * 100, 2)],
            "boot_p_two_sided": round(p, 4),
            "flip_in": fl_in, "flip_out": fl_out,
        }

    # ── 判决（按 stop-loss 的阈值，机械算） ────────────────────────────────
    prim = res["summary"]["all_171"]["primary_cluster"]
    net = prim["delta_pp"]
    fl_in, fl_out = prim["flip_in"], prim["flip_out"]
    if hard:
        verdict = "作废（仪器/作弊问题，不许解释结果）"
    elif net >= 9 and fl_in >= 3 * max(fl_out, 1):
        verdict = "推广"
    elif net >= 6:
        verdict = "观察"
    else:
        verdict = "放弃（query-side 这条闸门不通过）"

    rng = sl["decision_rule"]
    out = {
        "experiment": sl["experiment"],
        "primary_endpoint": sl["primary_endpoint"],
        "instrument_selfcheck": selfcheck,
        "hard_fail_triggered": hard,
        "primary_result_all171": prim,
        "decision_rule_applied": {"thresholds": rng, "matched": verdict},
        "verdict": verdict,
        "next_step": {
            "推广": "query-side 这条闸门通过 ⇒ 把它接进生产评估；**不需要**动 52 万条向量",
            "观察": "刚过显著线、不到 80% 把握度 ⇒ 按需补第二刀（Qwen3-14B 改写）再判",
            "放弃（query-side 这条闸门不通过）": "**此时才轮到第 2 项（Qwen3-Embedding-0.6B shadow test）**",
        }.get(verdict, "先查 hard_fail / 仪器自检那几条，别解释数字"),
        "how_to_read": [
            "配对比较看**分歧对**与**簇级**置信区间，不看单点百分点。",
            "涨跌两侧都报（含副终点 FTS/向量/生产上限口径）。",
            "分档按 benchmark-v3 汇报，但每格簇数很小 ⇒ 单格差异不当结论。",
        ],
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
