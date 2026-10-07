"""入库回归检查 · 汇总器驱动器：**把 `summarize.py` 指向指定的逐条文件**。

## 为什么要这个
`funnel.py` 的 `main()` **只写逐条结果**（`funnel-per-query.jsonl`），
**不写汇总** —— 汇总由另一个脚本 `summarize.py` 从逐条文件算出。
而 `summarize.py` 的输入/输出是**模块级常量**、没有命令行参数。
⇒ 与 `run-funnel-on.py` 同一招：当模块导入，**只覆盖 `PER` 与 `OUT`**，再调 `main()`。
   `summarize.py` 一行不改。

## 用法
  .venv\\Scripts\\python.exe eval\\recall-funnel\\regression-ingest\\run-summarize-on.py --prefix before
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
    ap.add_argument("--prefix", required=True)
    args = ap.parse_args()

    per = HERE / f"funnel-per-query-{args.prefix}.jsonl"
    out = HERE / f"funnel-summary-{args.prefix}.json"
    if not per.exists():
        print(f"⛔ 逐条文件不在：{per}")
        return 1

    sm = importlib.import_module("summarize")
    sm.PER = per
    sm.OUT = out
    print(f"[sum] 输入 = {per.name}（{sum(1 for _ in per.open(encoding='utf-8'))} 行）", flush=True)
    rc = sm.main()
    if out.exists():
        d = json.loads(out.read_text(encoding="utf-8"))
        print(f"[sum] 已写 {out.name}  顶层键 = {list(d.keys())}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
