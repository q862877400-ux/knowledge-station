"""E1 步骤 4a：**对照臂自检** —— 在副本上量一次，看能不能复现已知基线。

为什么必须先做这一步：`ab-result.json` 里的"实验臂涨了多少"是**相对**对照臂算的。
如果对照臂在副本上跑出来的数**不是**基线那三个数，那么后面任何差异都说不清是"换文本的效果"
还是"我的测量管线跟原管线不一样"。

期望（主结果 120 条口径，来自 `funnel-summary.json` 的 `headline`）：
    Vector @20 = 10.00% / @100 = 17.50% / @1000 = 35.83%

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-1-contextual\\04a-control-check.py
"""
from __future__ import annotations

import array
import json
import sqlite3
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
EXP = HERE / "exp.db"
DEPTHS = (20, 100, 1000)
EXPECT = {"@20": 0.10, "@100": 0.175, "@1000": 0.3583}
EX = {"gold_multi_def", "gold_dup_text"}


def main() -> int:
    from src.core.retrieval import embedder
    from src.core.storage.sqlite_db import load_vec_extension

    conn = sqlite3.connect(f"file:{EXP.as_posix()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    load_vec_extension(conn)

    v2 = [json.loads(l) for l in (HERE.parent / "benchmark-v2.jsonl").read_text(encoding="utf-8").splitlines()
          if l.strip()]
    head = [it for it in v2 if it["v2"]["bucket"] == "keep" and not (EX & set(it["v2"]["flags"]))]
    print(f"[ctrl] 全量 {len(v2)} 条；主结果 {len(head)} 条（期望 120）")

    t0 = time.perf_counter()
    hits = {d: 0 for d in DEPTHS}
    for j, it in enumerate(head, 1):
        gold = it["v2"]["gold_cr_id"]
        qv = embedder.embed_query(it["query"])
        rows = conn.execute(
            "SELECT clause_revision_id FROM clause_vec"
            " WHERE embedding MATCH ? AND k = ? ORDER BY distance",
            (array.array("f", qv).tobytes(), max(DEPTHS))).fetchall()
        ids = [r[0] for r in rows]
        for d in DEPTHS:
            if gold in ids[:d]:
                hits[d] += 1
        if j % 40 == 0:
            print(f"[ctrl] {j}/{len(head)}  {time.perf_counter()-t0:.0f}s", flush=True)

    got = {f"@{d}": round(hits[d] / len(head), 4) for d in DEPTHS}
    print("\n[ctrl] 副本对照臂 vs 基线：")
    ok = True
    for k in ("@20", "@100", "@1000"):
        same = abs(got[k] - EXPECT[k]) < 0.005
        ok &= same
        print(f"   {k:6s} 副本 {got[k]:.4f}（{hits[int(k[1:])]} 条）  基线 {EXPECT[k]:.4f}  {'✅' if same else '⛔'}")
    out = HERE / "control-check.json"
    out.write_text(json.dumps({
        "why": "对照臂必须能复现基线，否则实验臂的差异说不清来源",
        "n": len(head), "got": got, "expected": EXPECT,
        "counts": {f"@{d}": hits[d] for d in DEPTHS},
        "verdict": "对照臂复现基线" if ok else "⛔ 未复现 ⇒ 先查测量管线，别急着解释实验臂",
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"⇒ {'✅ 对照臂复现基线' if ok else '⛔ 未复现，实验臂的差异暂时不可解释'}")
    print(f"已写 {out}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
