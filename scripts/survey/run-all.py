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
    ("05-deep.py", "模块职责/接口明细/配置面/表读写"),
    ("06-content.py", "测试内容/文档内容/前端清单"),
    ("09-requirements.py", "需求编号/否决台账/数据样例"),

    ("10-rules.py", "判定规则（正则/阈值/理由）"),
    # ⚠ 07-runtime-probe.py **不进默认循环**：它要真启动引擎、跑 3–5 分钟。
    #   单独跑：`.venv\Scripts\python.exe scripts/survey/07-runtime-probe.py`

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

    # 前端真 AST 用 node 跑（仓根已有 typescript），不属于 python 生成器
    print("\n── 09-web-ast.cjs（前端真 AST，node）")
    nj = subprocess.run(["node", str(ROOT / "scripts" / "survey" / "09-web-ast.cjs")],
                        cwd=ROOT, capture_output=True, text=True,
                        encoding="utf-8", errors="replace")
    for ln in [x for x in (nj.stdout or "").splitlines() if x.strip()][-2:]:
        print(f"   {ln}")
    if nj.returncode != 0:
        print(f"   ⛔ exit={nj.returncode}")
        for ln in (nj.stderr or "").splitlines()[-6:]:
            print(f"   {ln}")
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
