"""入库回归检查 · 跑分器驱动器：**把现成的 `funnel.py` 指向任意一个库**，跑完把结果写到指定前缀。

## 为什么这么写（而不是改 funnel.py）
`funnel.py` 的 `DB` 是写死的常量，且 `main()` 会把结果写到固定的
`funnel-summary.json / funnel-per-query.jsonl / failure-samples.jsonl`。
直接跑第二次会**覆盖第一次的结果**。
⇒ 本驱动器把它当模块导入，**只覆盖模块级的 `DB` 与三个输出路径**，再调 `main()`；
   **`funnel.py` 一行不改**（仓规：复现要复用同一套跑分器，不许另写）。

## 用法
  .venv\\Scripts\\python.exe eval\\recall-funnel\\regression-ingest\\run-funnel-on.py \\
      --db "<库路径>" --prefix before
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "eval" / "recall-funnel"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True, help="要跑的库（只读打开）")
    ap.add_argument("--prefix", required=True, help="输出前缀，如 before / after")
    args = ap.parse_args()

    db = Path(args.db)
    if not db.exists():
        print(f"⛔ 库不存在：{db}")
        return 1

    funnel = importlib.import_module("funnel")
    # 覆盖模块级常量（main() 在调用时读它们）
    funnel.DB = db
    funnel.OUT_PER = HERE / f"funnel-per-query-{args.prefix}.jsonl"
    funnel.OUT_SUM = HERE / f"funnel-summary-{args.prefix}.json"
    funnel.OUT_FAIL = HERE / f"failure-samples-{args.prefix}.jsonl"
    print(f"[run] 库 = {db}  ({db.stat().st_size/1e9:.2f} GB)", flush=True)
    print(f"[run] 输出前缀 = {args.prefix}", flush=True)

    sys.argv = ["funnel.py"]          # 不给额外参数：跑全量 171 条
    rc = funnel.main()

    if funnel.OUT_SUM.exists():
        s = json.loads(funnel.OUT_SUM.read_text(encoding="utf-8"))
        print(f"[run] 汇总已写 {funnel.OUT_SUM.name}")
        # 只打印关键几行，避免刷屏
        for k in ("n_queries", "headline", "union", "by_channel"):
            if k in s:
                print(f"      {k} = {json.dumps(s[k], ensure_ascii=False)[:400]}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
