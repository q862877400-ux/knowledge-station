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
    # ⚠ **本脚本可重复运行，但文件里却有冻结记录** —— 这是我的设计缺陷：
    #   第二遍跑会把原始冻结值**刷成当前值**，于是"比对"永远通过（自己骗自己）。
    #   实测 2026-10-07 踩到。修法：**记录已存在就不覆盖**，改写一份带时间戳的复核件，
    #   并把两边的差异打出来 —— 那才是"复核"，不是"重刷"。
    import time as _t
    if OUT.exists():
        old = json.loads(OUT.read_text(encoding="utf-8"))
        alt = OUT.parent / f"FREEZE-recheck-{_t.strftime('%Y%m%d-%H%M%S')}.json"
        print(f"⚠ {OUT.name} 已在（冻结于 {old.get('frozen_at', '未知')}）—— **不覆盖**。")
        print(f"  本次只做复核，写 {alt.name}")
        _write(alt, old)
        return 0
    print("首次冻结（记录不存在）")
    _write(OUT, None)
    return 0


def _write(out: Path, old: dict | None) -> int:
    rec = {"why": "P2 实验 #1 开跑前的冻结记录（上限 20 → 100）",
           "frozen_at": __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
           "files": {}}
    changed = []
    for rel in FILES:
        p = ROOT / rel
        if not p.exists():
            rec["files"][rel] = "**不存在**"
            continue
        h = sha(p)
        rec["files"][rel] = {"sha256": h, "bytes": p.stat().st_size}
        mark = ""
        if old and isinstance(old["files"].get(rel), dict):
            o = old["files"][rel]["sha256"]
            if o != h:
                mark = f"   ⛔ **与冻结值不同**（冻结 {o[:16]}）"
                changed.append(rel)
            else:
                mark = "   ✅ 与冻结值一致"
        print(f"  {rel}\n      sha256 = {h}{mark}")
    try:
        rec["git_head"] = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                         capture_output=True, text=True).stdout.strip()
        rec["git_status_short"] = subprocess.run(["git", "status", "--short"], cwd=ROOT,
                                                 capture_output=True, text=True).stdout.strip()
    except Exception as e:                                                  # noqa: BLE001
        rec["git_error"] = f"{type(e).__name__}: {e}"
    print(f"\n  git HEAD = {rec.get('git_head')}")
    print(f"  git status = {rec.get('git_status_short') or '(干净)'}")
    if changed:
        rec["changed_vs_frozen"] = changed
        print(f"\n  ⛔ **有 {len(changed)} 个文件与冻结值不同**：{changed}")
        print("     ⇒ 开跑前先查清楚是谁改的、该不该改。")
    out.write_text(json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
