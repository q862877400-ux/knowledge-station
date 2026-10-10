#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""机械扫描命名违规项（001-project-consolidation T006）。

## 为什么要有它
`docs/naming-convention.md` 是**规则**，但规则写在散文里就只是散文——
**改名的成果会随下一次新增文件慢慢漂回去**。本脚本把规则变成**可重跑的判据**：
违反规则的项会被列出来，退出码非 0。

## 它查什么（逐条对应规范的节）
| 规则 | 判据 | 依据 |
|---|---|---|
| R1 文档文件名用 `-` 不用 `_` | 文档（`*.md`）文件名含 `_` ⇒ 违规 | 规范 §二 |
| R2 目录名全小写 kebab | 目录名含 `_` 或含大写 ⇒ 违规 | 规范 §一 |
| R3 代码文件跟随语言 | **不检查**（Python 的 `snake_case` 是对的） | 规范 §一 |

⚠ **R3 是本脚本存在的意义之一**：v1 规范曾把 327 个 `snake_case.py` 判成违规，
那会断掉每一个 import。**代码文件一律不进判据**——这是刻意的，不是漏查。

## 不查什么（明确边界，防"看着绿就是合规"）
- **不查大小写是否"好看"**：规范 §三 明确标准文档保留全大写，没有可机械判定的规则。
- **不查日期后缀**：规范 §五 说"只给会被取代的真源"，那需要人的判断。
- **不查分类归属**：规范 §七 的目录职责需要理解内容。
⇒ 本脚本只机械判定**能机械判定**的两条。其余靠人，别把本脚本的绿读成"全规范合规"。

## 用法
```bash
.venv/Scripts/python.exe scripts/docs/scan-rename-targets.py            # 人读
.venv/Scripts/python.exe scripts/docs/scan-rename-targets.py --json     # 机器读
```
退出码：`0` = 零违规；`1` = 有违规（逐条列出）。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

#: 走全树会先遍历 node_modules / .venv（数万个文件）——实测卡死超 120 秒。
#: 剪枝后 0.2 秒（这条坑记在 specs/001-project-consolidation/baseline.md §五 坑 2）。
SKIP_DIRS = {
    ".git", ".venv", "node_modules", "__pycache__", ".mypy_cache",
    ".pytest_cache", "var", ".zcode", ".dsh", ".workbuddy-ai", ".codebuddy",
    ".browser4-cli", ".specify", "wenjianmulu", "recon",
}
#: 本机产物目录名（规范 §七：`var/` 类不进判据）。
#: `recon/` 也被剪：`tools/gov-qa/recon/` 由另一个自动化高频写入，
#: 它的文件名前缀是**数据分区约定**（见 tools/gov-qa/WRITE-SCOPE.md），不归本规范管。
#: `tools/gov-qa/data/` 同理——那里的"目录"其实是**中文站点名的转义残留**，
#: 由采集侧生成、由另一个自动化拥有，不是命名规范的管辖面。
SKIP_PATH_PREFIXES = (
    "tools/gov-qa/data/",
    "tools/gov-qa/assets-",
)


def tracked_files() -> list[str]:
    """只扫**受版本控制**的文件——未跟踪的本机产物不归规范管（规范 §七）。

    ⚠ **必须 `-z` + `core.quotepath=false`**：`git ls-files` 默认把非 ASCII 路径
    **转义成八进制**（`"tools/.../\\345\\271\\277..."`）⇒ `Path()` 拿到的是一个带引号的
    单段字符串，`parents` 全是垃圾 ⇒ 实测刷出几千条**假违规**。
    这条是第一次实现时的真缺陷，留痕于此。
    """
    out = subprocess.run(
        ["git", "-c", "core.quotepath=false", "ls-files", "-z"],
        cwd=str(REPO), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    return [ln for ln in out.stdout.split("\0") if ln.strip()]


def is_under_skipped_dir(rel: str) -> bool:
    if any(rel.startswith(p) for p in SKIP_PATH_PREFIXES):
        return True
    return any(part in SKIP_DIRS for part in Path(rel).parts[:-1])


def doc_filename_violation(rel: str) -> dict | None:
    """R1：文档文件名用 `-`，不用 `_`。命中返回违规项，否则 `None`。

    ⚠ **只判 `*.md`**：`snake_case.py` 是 PEP8 的正确写法（规范 §一），
    把它判违规正是 v1 规范被推翻的原因（会断掉每一个 import）。
    """
    name = Path(rel).name
    if name.lower().endswith(".md") and "_" in name:
        return {
            "kind": "doc_filename_underscore",
            "rule": "R1 / 规范 §二",
            "path": rel,
            "suggest": name.replace("_", "-"),
            "why": "文档文件名必须用连字符 `-`（下划线只允许出现在代码文件名里）",
        }
    return None


def dir_name_violation(dir_path: str) -> dict | None:
    """R2：目录名全小写 kebab-case。命中返回违规项，否则 `None`。

    ⚠ 只判**目录本身**，不判它下面的文件——调用方按目录去重（见 `scan()`）。
    """
    dname = Path(dir_path).name
    if not dname or dname in SKIP_DIRS:
        return None
    if dname != dname.lower():
        return {
            "kind": "dir_name_not_lowercase",
            "rule": "R2 / 规范 §一",
            "path": dir_path,
            "suggest": dname.lower(),
            "why": "目录名必须全小写 kebab-case",
        }
    return None


def scan() -> list[dict]:
    violations: list[dict] = []
    seen_dirs: set[str] = set()

    for rel in tracked_files():
        if is_under_skipped_dir(rel):
            continue
        p = Path(rel)

        hit = doc_filename_violation(rel)
        if hit is not None:
            violations.append(hit)

        # R2：目录名全小写 kebab（逐个祖先目录去重）
        for parent in p.parents:
            key = parent.as_posix()
            if key in (".", "") or key in seen_dirs:
                continue
            seen_dirs.add(key)
            hit = dir_name_violation(key)
            if hit is not None:
                violations.append(hit)
    return violations


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true", help="机器可读输出")
    args = ap.parse_args()

    v = scan()
    if args.json:
        print(json.dumps({"violations": v, "count": len(v)}, ensure_ascii=False, indent=1))
    else:
        print(f"扫描受版本控制的文件（已剪枝 {len(SKIP_DIRS)} 类目录 + "
              f"{len(SKIP_PATH_PREFIXES)} 类前缀）")
        print(f"违规 {len(v)} 处")
        for item in v:
            print(f"  [{item['rule']}] {item['path']}")
            print(f"      建议: {item['suggest']}")
            print(f"      原因: {item['why']}")
        if not v:
            print("  ⇒ 零违规")
    return 1 if v else 0


if __name__ == "__main__":
    raise SystemExit(main())
