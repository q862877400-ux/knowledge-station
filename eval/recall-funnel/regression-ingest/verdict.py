"""入库回归检查 · **判决器**：把"入库前"与"入库后"两个汇总按**预先写死的判据**机械判决。

## 判据在哪
`eval/recall-funnel/regression-ingest/STOP-LOSS-入库回归.json`（**开跑前**落的）。摘要：
 · **通过**：union@1000 两个口径都不下降，或下降落在噪声内；
 · **硬失败**：任一主口径**下降超过 6 个百分点** ⇒ 入库损害了已有能力，当缺陷处理；
 · **灰区**：下降 0~6pt ⇒ 记"有退化迹象"，报数字与区间，**不擅自改库**。
 · 并写明三条不许做的：不许因为"入库是好事"放宽判据；不许只看平均不看每一路；
   不许拿"gold 是反推的不权威"当挡箭牌。

## 本脚本做什么
 ① 读两份 `funnel-summary-{before,after}.json`，把同一指标并排；
 ② 逐条读两份 `funnel-per-query-{before,after}.jsonl`，按 `i` 配对，数**翻转**（变好/变差）；
 ③ 按上面阈值**机械输出判决**，不做解释性调和。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\regression-ingest\\verdict.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "VERDICT-入库回归.json"
HARD_FAIL_PT = 6.0          # ← 与 STOP-LOSS 一致，不许在这里改
DEPTHS = ("@20", "@100", "@1000")


def load(name: str) -> dict:
    p = HERE / f"funnel-summary-{name}.json"
    if not p.exists():
        raise SystemExit(f"⛔ 缺 {p.name}；先把两跑跑完并各跑一次 run-summarize-on.py")
    return json.loads(p.read_text(encoding="utf-8"))


def per_query(name: str) -> dict[int, dict]:
    p = HERE / f"funnel-per-query-{name}.jsonl"
    out = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            out[r["i"]] = r
    return out


def main() -> int:
    b, a = load("before"), load("after")
    pb, pa = per_query("before"), per_query("after")
    print(f"[v] 逐条配对：before {len(pb)} 条 / after {len(pa)} 条 / 共同 {len(set(pb) & set(pa))} 条")

    report: dict = {"why": "入库回归判决（判据见 STOP-LOSS-入库回归.json）",
                    "hard_fail_pt": HARD_FAIL_PT, "scopes": {}, "verdict": None, "reasons": []}

    for scope in ("headline", "all_171"):
        sb, sa = b[scope], a[scope]
        rows = {}
        print(f"\n=== {scope}（n={sb.get('n')}）===")
        print(f"    {'指标':28s} {'入库前':>9s} {'入库后':>9s} {'差(pt)':>9s}")
        for key in ("union_same_budget", "union_prod_caps", "fused"):
            vb, va = sb.get(key), sa.get(key)
            if not isinstance(vb, dict) or not isinstance(va, dict):
                continue
            depth_keys = [d for d in DEPTHS if d in vb] or [k for k in vb if k.startswith("@")]
            if key == "union_prod_caps":
                depth_keys = ["hit"] if "hit" in vb else []
            for d in depth_keys:
                x, y = vb.get(d), va.get(d)
                if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                    diff = round((y - x) * 100, 2)
                    rows[f"{key}{d}"] = {"before": x, "after": y, "diff_pt": diff}
                    print(f"    {key+d:28s} {x:9.4f} {y:9.4f} {diff:+9.2f}")
        report["scopes"][scope] = rows

    # 翻转（配对）
    flips = {"变好": [], "变差": [], "不变": 0}
    for i in sorted(set(pb) & set(pa)):
        rb, ra = pb[i], pa[i]
        for key, path in (("fused@20", ("fused", "hit@20")),
                          ("union@1000", ("union", "same_budget", "@1000")),
                          ("union@20", ("union", "same_budget", "@20"))):
            xb = rb
            for k in path:
                xb = (xb or {}).get(k)
            xa = ra
            for k in path:
                xa = (xa or {}).get(k)
            if xb is None or xa is None:
                continue
            tag = f"{key}"
            if xa and not xb:
                flips["变好"].append({"i": i, "metric": tag, "query": rb["query"][:60]})
            elif xb and not xa:
                flips["变差"].append({"i": i, "metric": tag, "query": rb["query"][:60]})
            else:
                flips["不变"] += 1
    report["flips"] = {k: (v if isinstance(v, int) else v[:20]) for k, v in flips.items()}
    print(f"\n=== 配对翻转 ===")
    print(f"    变好 {len(flips['变好'])} 条 ｜ **变差 {len(flips['变差'])} 条** ｜ 不变 {flips['不变']}")
    for x in flips["变差"][:6]:
        print(f"      ↓ [{x['metric']}] {x['query']}")

    # ★ 机械判决（只看 headline 的 union@1000 与 fused@20，与 STOP-LOSS 一致）
    hl = report["scopes"].get("headline", {})
    fails, warns = [], []
    for metric in ("union_same_budget@1000", "fused@20"):
        r = hl.get(metric)
        if not r:
            continue
        if r["diff_pt"] < -HARD_FAIL_PT:
            fails.append(f"{metric} 下降 {r['diff_pt']:.2f} pt（超过 {HARD_FAIL_PT} pt 硬失败线）")
        elif r["diff_pt"] < 0:
            warns.append(f"{metric} 下降 {r['diff_pt']:.2f} pt（灰区，未过硬失败线）")
    if fails:
        report["verdict"] = "⛔ 硬失败"
        report["reasons"] = fails + warns
    elif warns:
        report["verdict"] = "🟡 灰区：有退化迹象"
        report["reasons"] = warns
    else:
        report["verdict"] = "✅ 通过"
        report["reasons"] = ["两个主口径均未下降"]

    print(f"\n{'='*60}")
    print(f"[v] **判决 = {report['verdict']}**")
    for r in report["reasons"]:
        print(f"      · {r}")
    if report["verdict"].startswith("⛔"):
        print("      ⇒ 入库损害了已有能力，**当缺陷处理**，不许解释成正常波动。")
    elif report["verdict"].startswith("🟡"):
        print("      ⇒ 报数字与区间，**不擅自改库**，留给业主定。")
    print(f"{'='*60}")

    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
