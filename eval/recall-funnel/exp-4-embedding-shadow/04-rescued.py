"""E4 · 附加：**救回了多少原本"六路前 1000 都没有"的题**。

这是最直观的一个数：E1/phase-0 诊断出**六路同预算并集 @1000 完全没命中**的那批题
（`funnel-per-query.jsonl` 的 `hit_in_deep_union == False`），
换模型之后有多少条被救回来、同时丢了多少条原本能找到的。

⚠ 只读产物，不重跑检索。口径写清：全量 171 条。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-4-embedding-shadow\\04-rescued.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
FUNNEL = ROOT / "eval" / "recall-funnel" / "funnel-per-query.jsonl"
PER = HERE / "ab-per-query.jsonl"
OUT = HERE / "rescued-from-104.json"


def main() -> int:
    fun = {json.loads(l)["i"]: json.loads(l)
           for l in FUNNEL.read_text(encoding="utf-8").splitlines() if l.strip()}
    rows = [json.loads(l) for l in PER.read_text(encoding="utf-8").splitlines() if l.strip()]

    # 原本"六路前 1000 都没有"的那批（phase-0 诊断口径）
    missing = [r for r in rows if not fun[r["i"]].get("hit_in_deep_union")]
    present = [r for r in rows if fun[r["i"]].get("hit_in_deep_union")]

    rescued = [r["i"] for r in missing if r["ctx"]["union_same@1000"]]
    lost = [r["i"] for r in present if not r["ctx"]["union_same@1000"]]
    also_ctx = [r["i"] for r in missing if r["base"]["union_same@1000"]]

    result = {
        "question": "换嵌入模型之后，原本『六路前 1000 都没有』的题救回了几条？",
        "scope": "全量 171 条；口径 = 六路同预算并集 @1000（与 phase-0 的 hit_in_deep_union 同定义）",
        "n_missing_before": len(missing),
        "n_present_before": len(present),
        "rescued": {"n": len(rescued), "pct_of_missing": round(len(rescued) / len(missing), 4) if missing else None,
                    "ids": rescued},
        "lost": {"n": len(lost), "ids": lost},
        "net": len(rescued) - len(lost),
        "note": (f"原 missing 集合里，对照臂（现役模型）本来就能命中的有 {len(also_ctx)} 条 —— "
                 f"说明这两套口径不完全等价，本数按同一批题对比、不混口径"),
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=1))
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
