"""P2 实验 #1 · 冻结记录：**改代码之前**把该冻的哈希记下来。

## 为什么单独一个脚本
仓规：「每个改进实验**开跑前**定好止损线（放弃阈值 / 观察阈值 / 推广阈值）」，
且要能事后核"跑之前那棵树长什么样"。
⇒ 本脚本把**被改文件**与**考卷**的 sha256 落盘，事后可逐位核对有没有被顺手改动。

只读；不写任何东西（除了自己那份 JSON）。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-6-cap\\freeze.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "FREEZE.json"

FILES = [
    "src/core/retrieval/hybrid_engine.py",       # ← 本轮唯一被改的文件
    "eval/recall-funnel/funnel.py",              # ← 跑分器（代码不改，只覆盖常量）
    "eval/recall-funnel/summarize.py",           # ← 汇总器（同上）
    "eval/recall-funnel/benchmark-v2.jsonl",     # ← 考卷
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    rec = {"why": "P2 实验 #1 开跑前的冻结记录（上限 20 → 100）", "files": {}}
    for rel in FILES:
        p = ROOT / rel
        if not p.exists():
            rec["files"][rel] = "**不存在**"
            continue
        rec["files"][rel] = {"sha256": sha(p), "bytes": p.stat().st_size}
        print(f"  {rel}\n      sha256 = {rec['files'][rel]['sha256']}"
              f"  ({rec['files'][rel]['bytes']} 字节)")
    try:
        rec["git_head"] = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                         capture_output=True, text=True).stdout.strip()
        rec["git_status_short"] = subprocess.run(["git", "status", "--short"], cwd=ROOT,
                                                 capture_output=True, text=True).stdout.strip()
    except Exception as e:                                                  # noqa: BLE001
        rec["git_error"] = f"{type(e).__name__}: {e}"
    print(f"\n  git HEAD = {rec.get('git_head')}")
    print(f"  git status = {rec.get('git_status_short') or '(干净)'}")
    OUT.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
