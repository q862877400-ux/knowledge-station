"""门禁棘轮的**口径**：只统计**受版本控制**的用例（`run-gates.ps1` 调它）。

## 为什么需要它（2026-09-26 复核 MED-1，定时炸弹）

棘轮记的是"总账"（`passed+skipped+failed+errors`）。原先它记的是**实测总数**，
而实测总数里可能含**未跟踪文件**里的用例 —— 本仓实测就有：`tests/test_jev_cn_baseline.py`
**不被 git 跟踪**（`git ls-files` 为空），却贡献 **5 条**。

⇒ 后果有两层，都是恶性的：
1. 记进基线 ⇒ 那份文件一被删（`git clean`、提取树里天然没有、别人清理），
   总账掉 5、**棘轮假红**，且红在一个**不归本仓控制**的文件上；
2. 反过来，只要有人**手工把基线调低**去躲这个假红（我 2026-09-25 就是这么干的），
   紧接着新增用例就会造出**余量** ⇒ **余量内的用例可以被静默删掉而棘轮不红**。
   复核把它量化了：**余量从 0 涨到 6**，那 6 条正是"保护提问证据不被销毁"的测试。

**修法**：口径搬进代码 —— **比较与记账两侧都只统计 tracked 用例**。于是
"有那份文件"与"没那份文件"得到**同一个数**，余量回到 0，删任何一条都红。

## 判据（本脚本自己要被验）

`tests/test_gates_tracked_total.py` 用**临时 git 仓库**造 tracked / untracked 两种文件，
断言只减掉 untracked 的那些、且不改动 tracked 的那些；并有一条**反向**断言
（不做这个扣减时，untracked 的用例会被算进去）。

用法：
    python scripts/gates-tracked-total.py --junit <junit.xml> --repo <仓库根>
输出（JSON，一行）：
    {"collected": N, "mapped": M, "unmapped": U, "untracked": X,
     "tracked_total": N-X, "untracked_files": {...}}
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def _candidate_files(repo: Path, dotted: str) -> list[Path]:
    """点分名 → 候选文件路径，**由长到短**（junit 把类名塞进 classname）。

    `tests.test_x.TestY` ⇒ 先试 `tests/test_x/TestY.py`、再退 `tests/test_x.py`。
    """
    parts = [p for p in dotted.split(".") if p]
    return [repo.joinpath(*parts[:i]).with_suffix(".py")
            for i in range(len(parts), 0, -1)]


def _tracked_set(repo: Path) -> set[str]:
    """`git ls-files` 的**仓库相对路径**集合（正斜杠、小写盘符无关，统一成 posix）。"""
    out = subprocess.run(["git", "-C", str(repo), "ls-files"],
                         capture_output=True, text=True, check=True).stdout
    return {ln.strip().replace("\\", "/") for ln in out.splitlines() if ln.strip()}


def compute(junit: Path, repo: Path) -> dict:
    tree = ET.parse(junit)
    casenames: list[str] = []
    for tc in tree.getroot().iter("testcase"):
        dotted = (tc.get("classname") or "").strip()
        name = (tc.get("name") or "").strip()
        # 收集期跳过的键是 `::<模块>` 形态（classname 为空、name 是模块名）
        casenames.append(dotted if dotted else name)

    tracked = _tracked_set(repo)
    files_cache: dict[str, str | None] = {}
    untracked: dict[str, int] = {}
    unmapped = 0

    for dotted in casenames:
        if dotted not in files_cache:
            hit = None
            for cand in _candidate_files(repo, dotted):
                if cand.is_file():
                    hit = cand.relative_to(repo).as_posix()
                    break
            files_cache[dotted] = hit
        rel = files_cache[dotted]
        if rel is None:
            unmapped += 1
        elif rel not in tracked:
            untracked[rel] = untracked.get(rel, 0) + 1

    collected = len(casenames)
    excluded = sum(untracked.values())
    return {
        "collected": collected,
        "mapped": collected - unmapped,
        "unmapped": unmapped,          # 认不出文件 ⇒ **不扣**（保守）
        "untracked": excluded,
        "tracked_total": collected - excluded,
        "untracked_files": untracked,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--junit", required=True)
    ap.add_argument("--repo", required=True)
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError):       # pragma: no cover
        pass
    info = compute(Path(args.junit), Path(args.repo))
    print(json.dumps(info, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
