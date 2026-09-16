# -*- coding: utf-8 -*-
"""打印某轮的类全貌 + 异常文档（GAP/ERROR/身份可疑）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
rnd = sys.argv[1] if len(sys.argv) > 1 else "4"
rd = Path(__file__).resolve().parent / "evolve" / "rounds" / f"round-{int(rnd):03d}"
m = json.loads((rd / "metrics.json").read_text(encoding="utf-8"))
print(f"轮 #{m['round']} · 评估 {m['docs_evaluated']} 部 · 类命中总计 {m['score']}")
print(f"verdicts: {m['verdicts']}")
print(f"\n{'类':<30}{'部数':>6}  {'条款数':>7}")
for c, v in m["classes"].items():
    mark = "  ★达线" if v["docs"] >= 3 else ""
    print(f"  {c:<28}{v['docs']:>6}{mark}")
print(f"\n达线类（≥3 部）：{m['over_line']}")
print("\n异常文档：")
for f in sorted((rd / "docs").glob("*.json")):
    r = json.loads(f.read_text(encoding="utf-8"))
    if r.get("verdict") in ("GAP", "ERROR", "IDENTITY-UNKNOWN") \
            or not r.get("artifact", {}).get("certain", True):
        print(f"  {r['std_no']:<26} {r.get('verdict'):<16} 条款 "
              f"{r.get('clauses')}/{r.get('clauses_db')} · "
              f"kind={r['artifact']['kind']} · {r['artifact']['why'][:60]}")
