"""P2 实验 #1 判决器：**上限 20（对照）vs 上限 100（处理）**，按预登记止损线机械判决。

## 判据在哪
`eval/recall-funnel/exp-6-cap/STOP-LOSS-提高取数上限.md`（**改代码之前**落的）。摘要：
 · 主指标 `fused@20`（headline）；次指标 `fused@100` / `fused@1000` / `union.prod_caps.hit` /
   分档里 L2 的条数 / **每条耗时**；
 · **推广** `fused@20` ≥ **+6 pt**；· **观察** +2~6 pt；· **放弃** < +2 pt；
 · **⛔ 硬失败**：`fused@20` **任何下降**，或单条耗时增长 **> 3×**。

## 分档口径
**照抄 `summarize.py`**（L2 用 `union.same_budget["@20"]`，子集是 headline 120 条）——
第一版我另立口径吃过大亏，这次显式照抄。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-6-cap\\verdict.py
"""
from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
REG = ROOT / "eval" / "recall-funnel" / "regression-ingest"
OUT = Path(__file__).resolve().parent / "VERDICT-cap100.json"
PROMOTE_PT, OBSERVE_PT, SLOW_X = 6.0, 2.0, 3.0        # ← 与 STOP-LOSS 一致，不许在这里改
_EXCLUDE = {"gold_multi_def", "gold_dup_text"}


def load(prefix: str) -> dict:
    p = REG / f"funnel-summary-{prefix}.json"
    if not p.exists():
        raise SystemExit(f"⛔ 缺 {p.name}")
    return json.loads(p.read_text(encoding="utf-8"))


def per_query(prefix: str) -> dict[int, dict]:
    p = REG / f"funnel-per-query-{prefix}.jsonl"
    out = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            out[r["i"]] = r
    return out


def tier(r: dict) -> str:
    u = r["union"]["same_budget"]
    if not u.get("@1000"):
        return "L1"
    if not u.get("@20"):
        return "L2"
    if not r["fused"].get("hit@20"):
        return "L3"
    gr = r["fused"].get("gold_rank")
    return "L0" if (gr is not None and gr <= 8) else "L4"


def main() -> int:
    ctrl, trt = load("after"), load("cap100")
    pc, pt = per_query("after"), per_query("cap100")
    print(f"[v] 逐条配对：对照 {len(pc)} / 处理 {len(pt)} / 共同 {len(set(pc) & set(pt))}")

    report = {"why": "P2 实验 #1：每路取数上限 20（对照）vs 100（处理）",
              "thresholds": {"推广": PROMOTE_PT, "观察": OBSERVE_PT, "硬失败耗时": SLOW_X},
              "scopes": {}, "triage": {}, "verdict": None, "reasons": []}

    METRICS = [
        ("fused@20", ("fused", "@20"), True),
        ("fused@100", ("fused", "@100"), False),
        ("fused@1000", ("fused", "@1000"), False),
        ("union@1000", ("union", "same_budget", "@1000"), False),
        ("union@20", ("union", "same_budget", "@20"), False),
        ("union.prod_caps.hit", ("union", "prod_caps", "hit"), False),
    ]

    def dig(d, path):
        for k in path:
            if not isinstance(d, dict):
                return None
            d = d.get(k)
        return d

    for scope in ("headline", "all_171"):
        c, t = ctrl[scope], trt[scope]
        rows = {}
        print(f"\n=== {scope}（n={c.get('n')}）===")
        print(f"    {'指标':24s} {'对照(20)':>10s} {'处理(100)':>10s} {'差(pt)':>9s}")
        for label, path, is_main in METRICS:
            x, y = dig(c, path), dig(t, path)
            if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                diff = round((y - x) * 100, 2)
                rows[label] = {"control": x, "treatment": y, "diff_pt": diff}
                print(f"    {label:24s} {x:10.4f} {y:10.4f} {diff:+9.2f}"
                      f"{'  ← 主指标' if is_main else ''}")
        report["scopes"][scope] = rows

    # 分档变化（headline）
    tc = {}; tt = {}
    for i in pc:
        if pc[i].get("bucket") == "keep" and not (_EXCLUDE & set(pc[i].get("flags") or [])):
            tc[tier(pc[i])] = tc.get(tier(pc[i]), 0) + 1
    for i in pt:
        if pt[i].get("bucket") == "keep" and not (_EXCLUDE & set(pt[i].get("flags") or [])):
            tt[tier(pt[i])] = tt.get(tier(pt[i]), 0) + 1
    print(f"\n=== 分档变化（headline 120，照 summarize.py 口径）===")
    print(f"    {'档':8s} {'对照':>6s} {'处理':>6s} {'差':>6s}")
    for k in ("L0", "L1", "L2", "L3", "L4"):
        a, b = tc.get(k, 0), tt.get(k, 0)
        print(f"    {k:8s} {a:6d} {b:6d} {b-a:+6d}")
    report["triage"] = {"control": tc, "treatment": tt}

    # 耗时
    def mean_elapsed(pq: dict) -> float:
        v = [r.get("elapsed_s") for r in pq.values() if isinstance(r.get("elapsed_s"), (int, float))]
        return st.mean(v) if v else 0.0
    mc, mt = mean_elapsed(pc), mean_elapsed(pt)
    ratio = (mt / mc) if mc else float("inf")
    print(f"\n=== 耗时 ===")
    print(f"    单条平均：对照 {mc:.2f}s  处理 {mt:.2f}s  ⇒ **{ratio:.2f}×**"
          f"（硬失败线 {SLOW_X}×）")
    report["elapsed"] = {"control_s": round(mc, 2), "treatment_s": round(mt, 2),
                         "ratio": round(ratio, 2)}

    # ★ 机械判决
    main_diff = (report["scopes"].get("headline") or {}).get("fused@20", {}).get("diff_pt")
    r = []
    if ratio > SLOW_X:
        r.append(f"⛔ 单条耗时 {ratio:.2f}× > {SLOW_X}× ⇒ **硬失败**（靠慢好几倍换来的收益，产品上不成立）")
    if main_diff is None:
        r.append("⛔ 主指标取不到，无法判决")
    elif main_diff < 0:
        r.append(f"⛔ 主指标 `fused@20` **下降** {main_diff} pt ⇒ **硬失败**（成本增加却更差，直接回退）")
    elif main_diff >= PROMOTE_PT:
        r.append(f"✅ 主指标 `fused@20` 提升 **+{main_diff} pt ≥ {PROMOTE_PT}** ⇒ **推广**")
    elif main_diff >= OBSERVE_PT:
        r.append(f"🟡 主指标 `fused@20` 提升 +{main_diff} pt（{OBSERVE_PT}~{PROMOTE_PT}）⇒ **观察**")
    else:
        r.append(f"⚰ 主指标 `fused@20` 提升 +{main_diff} pt < {OBSERVE_PT} ⇒ **放弃**")
    report["verdict"] = "⛔ 硬失败" if any(x.startswith("⛔") for x in r) else r[0].split()[0]
    report["reasons"] = r

    print(f"\n{'='*60}")
    for x in r:
        print(f"[v] {x}")
    print(f"{'='*60}")

    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    print("⚠ 判决若为「推广」，才另开提交把上限正式改进生产；否则**立即还原**并用冻结哈希核对。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
