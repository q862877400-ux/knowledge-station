# -*- coding: utf-8 -*-
"""一键重跑：把五个生成器按正确顺序跑到「一致点」。

## 为什么需要「跑到一致点」

生成器之间有先后与**自我引用**关系：

```
00-inventory  → inventory.json
01-symbols    → symbols_py.json
02-surface    → schema / endpoints / tests / docs / gates.json
03-render     → docs/survey/*.md（**这一步会新增 .md 文件**）
04-reconcile  → 核对 docs.json 里的文档数是否等于磁盘实际数
```

`03-render` 写出的 md **本身也在 `docs/` 下** ⇒ `docs.json` 里的文档数会变
⇒ 必须**再跑一次 02 让 `docs.json` 反映新数量**，然后再跑一次 03 让
`07-doc-surface.md` 的数字同步。

实测一次就够（新增文件数量是固定的 12 份）。本脚本跑两轮再核对，
**对不上就 exit 1**（而不是静默留一个过期数字）。

## 用法

    python scripts/survey/run-all.py
    python scripts/survey/run-all.py --rounds 3
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = str(ROOT / ".venv" / "Scripts" / "python.exe")
if not Path(PY).exists():
    PY = sys.executable

STEPS = [
    ("00-inventory.py", "文件清单（四本账）"),
    ("01-symbols.py", "Python 符号 + 引用"),
    ("02-surface.py", "数据/接口/测试/文档/门禁"),
    ("03-render.py", "渲染人可读文档"),
]


def run(script: str, label: str) -> bool:
    p = ROOT / "scripts" / "survey" / script
    print(f"\n── {script}（{label}）")
    r = subprocess.run(
        [PY, str(p)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    tail = [ln for ln in (r.stdout or "").splitlines() if ln.strip()][-3:]
    for ln in tail:
        print(f"   {ln}")
    if r.returncode != 0:
        print(f"   ⛔ exit={r.returncode}")
        for ln in (r.stderr or "").splitlines()[-8:]:
            print(f"   {ln}")
        return False
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=2)
    args = ap.parse_args()

    for rnd in range(1, args.rounds + 1):
        print(f"\n{'=' * 62}\n第 {rnd} 轮\n{'=' * 62}")
        for script, label in STEPS:
            if not run(script, label):
                return 1

    print(f"\n{'=' * 62}\n对账\n{'=' * 62}")
    p = ROOT / "scripts" / "survey" / "04-reconcile.py"
    r = subprocess.run([PY, str(p)], cwd=ROOT)
    if r.returncode != 0:
        print(
            "\n⛔ 对账未通过 —— 可能有生成器之间的数量互相影响，"
            "试试 --rounds 3 或检查 04-reconcile.py 的判据",
            file=sys.stderr,
        )
        return 1
    print("\n✅ 全部完成且对账通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
