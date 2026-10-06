"""E4 · 步骤 3：**机械判决** + 全终点簇级置信区间。

按 `stop-loss.json`（**跑之前**冻结，sha256 `d5c2a1eb…`）的三档：
 **< 8pt 放弃 / 8~10pt 灰区 / ≥10pt 进第二轮验证**（主终点 = Vector@1000，主结果 120 条口径）。

硬失败逐条机械检查（任一命中 ⇒ 作废，不许解释数字）：
 1. 实验向量与对照臂条目集合**双向 EXCEPT 任一非 0**；
 2. **真库被动过** —— 判据：真库里**不应存在** `clause_vec_qwen` 表，且 `clause_vec` 行数仍为 522,021；
 3. **FTS@1000 两臂出现非零变化**（按字找与嵌入模型无关，是仪器对照）；
 4. 两臂用了不同条文文本（文本是冻结项；由脚本口径保证，此处记录）。

⚠ 涨跌两侧都报：若新模型更差，那就是「更差」的结论。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-4-embedding-shadow\\03-verdict-e4.py
"""
from __future__ import annotations

import json
import math
import os
import random
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
RES = HERE / "ab-result.json"
PER = HERE / "ab-per-query.jsonl"
OUT = HERE / "verdict.json"
OUT_CI = HERE / "extra-endpoints.json"
EXP = HERE / "exp.db"
N_BOOT = 10000
SEED = 20261007
REAL_DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"

#: 对照臂必须复现的基线（主结果 120 / 全量 171）
BASELINE = {"headline_120": {"rank@1000": 0.3583, "union_same@1000": 0.4, "rank@100": 0.175},
            "all_171": {"rank@1000": 0.345, "union_same@1000": 0.3918}}
KEYS = ("rank@20", "rank@100", "rank@1000", "union_same@20", "union_same@100",
        "union_same@1000", "union_prod", "fts@1000")


def binom_two_sided(k: int, n: int) -> float:
    if n == 0:
        return 1.0
    pmf = lambda i: math.comb(n, i) * 0.5 ** n       # noqa: E731
    obs = pmf(k)
    return min(1.0, sum(pmf(i) for i in range(n + 1) if pmf(i) <= obs + 1e-12))


def main() -> int:
    if not RES.exists():
        print(f"⛔ 还没有 {RES.name} —— 先跑 02-ab-eval.py")
        return 1
    sl = json.loads((HERE / "stop-loss.json").read_text(encoding="utf-8"))
    res = json.loads(RES.read_text(encoding="utf-8"))
    rows = [json.loads(l) for l in PER.read_text(encoding="utf-8").splitlines() if l.strip()]
    v3 = {json.loads(l)["i"]: json.loads(l)
          for l in (ROOT / "eval" / "recall-funnel" / "benchmark-v3.jsonl")
          .read_text(encoding="utf-8").splitlines() if l.strip()}

    # ── ① 仪器自检：对照臂复现基线 ────────────────────────────────────────
    hard, selfcheck = [], {}
    for label, want in BASELINE.items():
        got = {k: res["summary"][label]["base"][k] for k in want}
        ok = all(abs(got[k] - want[k]) < 0.002 for k in want)
        selfcheck[label] = {"want": want, "got": got, "ok": ok}
        if not ok:
            hard.append(f"对照臂未复现基线（{label}）：{got} vs {want}")

    # ── ② FTS 仪器对照 ────────────────────────────────────────────────────
    fts_mm = res["instrument_control"]["fts_mismatch_items"]
    if fts_mm != 0:
        hard.append(f"FTS 两臂出现 {fts_mm} 条不一致（按字找与嵌入模型无关）⇒ 先查仪器")

    # ── ③ 真库没被动过 ────────────────────────────────────────────────────
    from src.core.storage.sqlite_db import load_vec_extension
    rc = sqlite3.connect(f"file:{REAL_DB.as_posix()}?mode=ro", uri=True)
    load_vec_extension(rc)
    real_n = rc.execute("SELECT COUNT(*) FROM clause_vec").fetchone()[0]
    has_qwen = bool(rc.execute("SELECT 1 FROM sqlite_master WHERE name='clause_vec_qwen'").fetchone())
    rc.close()
    real_ok = (real_n == 522021) and not has_qwen
    if not real_ok:
        hard.append(f"真库被动过：clause_vec={real_n}（应 522021）、存在 clause_vec_qwen={has_qwen}")

    # ── ④ 实验向量与对照臂条目集合 ────────────────────────────────────────
    c = sqlite3.connect(f"file:{EXP.as_posix()}?mode=ro", uri=True)
    load_vec_extension(c)
    only_base = c.execute("SELECT COUNT(*) FROM clause_vec v WHERE NOT EXISTS ("
                          " SELECT 1 FROM clause_vec_qwen q WHERE q.clause_revision_id=v.clause_revision_id)"
                          ).fetchone()[0]
    only_ctx = c.execute("SELECT COUNT(*) FROM clause_vec_qwen q WHERE NOT EXISTS ("
                         " SELECT 1 FROM clause_vec v WHERE v.clause_revision_id=q.clause_revision_id)"
                         ).fetchone()[0]
    c.close()
    if only_base or only_ctx:
        hard.append(f"两臂条目集合不一致：仅对照臂 {only_base} / 仅实验臂 {only_ctx}")

    # ── ⑤ 全终点簇级 bootstrap ────────────────────────────────────────────
    rnd = random.Random(SEED)
    ci_all: dict = {"n_bootstrap": N_BOOT, "seed": SEED, "subsets": {}}
    for label, sub in (("all_171", rows), ("headline_120", [r for r in rows if r["headline"]])):
        groups: dict[str, list[dict]] = {}
        for r in sub:
            groups.setdefault(v3[r["i"]]["v2"]["gold_cr_id"], []).append(r)
        cl = list(groups.values()); k = len(cl); n = len(sub)
        res_lab = {}
        for key in KEYS:
            gb = [sum(1 for r in g if r["base"][key]) for g in cl]
            gc = [sum(1 for r in g if r["ctx"][key]) for g in cl]
            gn = [len(g) for g in cl]
            ib, ic = sum(gb) / n, sum(gc) / n
            diffs = []
            for _ in range(N_BOOT):
                idx = [rnd.randrange(k) for _ in range(k)]
                tb = sum(gb[i] for i in idx); tc = sum(gc[i] for i in idx); tn = sum(gn[i] for i in idx)
                diffs.append((tc - tb) / tn)
            diffs.sort()
            lo, hi = diffs[int(N_BOOT * .025)], diffs[int(N_BOOT * .975)]
            le = sum(1 for d in diffs if d <= 0); ge = sum(1 for d in diffs if d >= 0)
            p = min(1.0, 2 * min(le, ge) / N_BOOT)
            fin = sum(1 for r in sub if not r["base"][key] and r["ctx"][key])
            fout = sum(1 for r in sub if r["base"][key] and not r["ctx"][key])
            nd = fin + fout
            res_lab[key] = {"n_items": n, "n_clusters": k, "base": round(ib, 4), "ctx": round(ic, 4),
                            "delta_pp": round((ic - ib) * 100, 2),
                            "ci95_pp": [round(lo * 100, 2), round(hi * 100, 2)],
                            "boot_p_two_sided": round(p, 4),
                            "flip_in": fin, "flip_out": fout,
                            "mcnemar_exact_p": round(binom_two_sided(fin, nd), 4) if nd else None,
                            "significant_at_0.05": p < 0.05}
        ci_all["subsets"][label] = res_lab
    OUT_CI.write_text(json.dumps(ci_all, ensure_ascii=False, indent=1), encoding="utf-8")

    # ── ⑥ 机械判决（主终点 = Vector@1000，主结果 120 条口径）──────────────
    prim = ci_all["subsets"]["headline_120"]["rank@1000"]
    net = prim["delta_pp"]
    if hard:
        verdict = "作废（仪器/越界问题，不许解释结果）"
    elif net < 8:
        verdict = "放弃（这个模型不值得）"
    elif net < 10:
        verdict = "灰区（不能据此换生产模型）"
    else:
        verdict = "进第二轮验证"

    out = {
        "experiment": sl["experiment"],
        "primary_endpoint": sl["primary_endpoint"],
        "instrument_selfcheck": selfcheck,
        "fts_instrument_control": {"mismatch_items": fts_mm, "ok": fts_mm == 0},
        "real_db_untouched": {"clause_vec": real_n, "has_clause_vec_qwen": has_qwen, "ok": real_ok},
        "arm_set_check": {"only_base": only_base, "only_ctx": only_ctx, "ok": not (only_base or only_ctx)},
        "hard_fail_triggered": hard,
        "primary_result_headline120_vector@1000": prim,
        "all_endpoints": ci_all["subsets"],
        "decision_rule_applied": {"thresholds": sl["decision_rule"], "matched": verdict},
        "verdict": verdict,
        "next_step": {
            "放弃（这个模型不值得）": "换模型这条线在 0.6B/512d 下不成立 ⇒ 回到已确证的按字找那条路，或另议候选模型",
            "灰区（不能据此换生产模型）": "刚过显著线、远低于 80% 把握度 MDE（11.68pt）⇒ 单次跑不出来，需另立一轮或换候选",
            "进第二轮验证": "仍**不是**确证有效 ⇒ 须看簇级置信区间，并另立第二轮实验（如 1024 维 / BGE-M3 / 加指令前缀）",
        }.get(verdict, "先查硬失败那几条，别解释数字"),
        "must_read": [
            "**涨跌两侧都报**：若新模型更差，那就是「更差」的结论。",
            "主终点是 Vector@1000（主结果 120）；其余终点只作参考，**不许因副终点好看改主终点**。",
            "8pt 是分辨率线、不是生产切换线；≥10pt 仍低于本仓实测的 80% 把握度 MDE（11.68pt）。",
        ],
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "all_endpoints"}, ensure_ascii=False, indent=1))
    for label, d in ci_all["subsets"].items():
        print(f"\n=== {label} ===")
        for key, v in d.items():
            print(f"  {key:16s} {v['base']:.4f}→{v['ctx']:.4f} ({v['delta_pp']:+6.2f}pt)"
                  f" CI95[{v['ci95_pp'][0]:+6.2f},{v['ci95_pp'][1]:+6.2f}] p={v['boot_p_two_sided']:.4f}"
                  f" 进{v['flip_in']}/出{v['flip_out']}"
                  f"{'  ★显著' if v['significant_at_0.05'] else ''}")
    print(f"\n已写 {OUT}\n已写 {OUT_CI}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
