#!/usr/bin/env python3
"""全仓 markdown 链接检查器。

为什么单独写：门禁扫不到全部文档，因此"无断链"这个结论 MUST 独立验证，
不能只凭门禁绿来断言（宪法原则 III：假绿判 failed）。

用法：
    python scripts/docs/check-links.py            # 只报告
    python scripts/docs/check-links.py --list     # 连通过的一起列
    python scripts/docs/check-links.py --json     # 机器可读

退出码：0 = 无断链；1 = 有断链；2 = 用法错误。

解析规则（按解析顺序）：
    1. 相对本文件所在目录解析（标准 markdown 约定）
    2. 若失败，再相对仓库根解析（本仓历史上两种写法混用）
    3. 跳过 http(s):// 、mailto: 、纯锚点 (#...) 三类
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote

REPO = Path(__file__).resolve().parents[2]

# [文字](目标) —— 不匹配图片 ![..](..)，图片另按同一逻辑处理（也要检查）
LINK_RE = re.compile(r"!?\[[^\]]*\]\(\s*([^)\s]+?)(?:\s+\"[^\"]*\")?\s*\)")
# 反引号里写成路径的（如 `docs/X.md`）也顺带查——它们常被当作引用用
CODE_PATH_RE = re.compile(r"`([A-Za-z0-9_./-]+\.md)`")

# 行内代码段：单反引号 `x` 与双反引号 ``x`` 都要剥掉。
# 剥的理由：`` ``[English](foo.md)` | 中文`` `` 这种是**讲约定的举例**，不是可点的引用；
# 不剥会把举例报成断链（实测 dshdocs-F.md 的两处就是这么来的）。
INLINE_CODE_RE = re.compile(r"``.+?``|`[^`]*`")

SKIP_PREFIXES = ("http://", "https://", "mailto:", "tel:", "ftp://", "data:")


# 遍历时直接剪掉的目录名。必须在 walk 阶段剪，不能等 rglob 走完再过滤：
# node_modules 与 .venv 里有数万个文件，rglob 会把它们全走一遍（实测卡住 >120 秒）。
#
# var/ 也剪掉：整目录被 gitignore，是**本机产物**不是项目文件。
# 实测不加它会扫到 3590 个 md（含下载的课程材料与 OCR 输出），把真问题淹掉。
PRUNE_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".mypy_cache",
              ".pytest_cache", ".dsh", ".zcode", "dist", "build", "var"}

# 明显不是链接的目标：正则示例、占位符、省略号。**分开计数，不静默丢**。
NON_LINK_RE = re.compile(r"[<>{}\[\]^$*?+\\|]|…|^\.\.\.$|^#")


def is_probably_not_a_link(target: str) -> bool:
    """判断一个"链接目标"其实是正文里的示例/正则/占位符。

    这些不报为断链，但会单独计数（`skipped_lookalikes`），
    以免"过滤掉"变成"藏起来"。
    """
    if NON_LINK_RE.search(target):
        return True
    # 带空格的裸词（如 `foo bar`）通常是正文里的示例
    if " " in target and not target.startswith(("http", "/", ".")):
        return True
    return False


def iter_markdown() -> list[Path]:
    """仓库里所有受检查的 markdown 文件（遍历时剪枝，不进入依赖与缓存目录）。"""
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(REPO):
        dirnames[:] = [d for d in dirnames if d not in PRUNE_DIRS]
        for name in filenames:
            if name.endswith(".md"):
                out.append(Path(dirpath) / name)
    return sorted(out)


def resolve(target: str, source: Path) -> tuple[bool, str]:
    """返回 (是否存在, 是按哪种基准找到的)。"""
    target = target.split("#", 1)[0].strip()  # 去掉锚点
    if not target:
        return True, "anchor-only"
    target = unquote(target)
    cand = source.parent / target
    if cand.exists():
        return True, "relative"
    cand2 = REPO / target.lstrip("/")
    if cand2.exists():
        return True, "repo-root"
    return False, "missing"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true", help="连通过的一起列")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--include-code-paths", action="store_true",
                    help="也检查反引号里的 *.md 路径（默认关：那些常是举例而非引用）")
    args = ap.parse_args()

    files = iter_markdown()
    broken: list[dict] = []
    lookalikes: list[dict] = []
    total_links = 0
    by_basis = {"relative": 0, "repo-root": 0, "anchor-only": 0}

    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            broken.append({"file": str(f.relative_to(REPO)), "line": 0,
                           "target": f"<读取失败: {exc}>", "kind": "read-error"})
            continue
        for i, line in enumerate(text.splitlines(), 1):
            # 先剥掉行内代码段，再找链接：代码段里的 [x](y) 是举例，不是引用
            stripped = INLINE_CODE_RE.sub(" ", line)
            targets = [m.group(1) for m in LINK_RE.finditer(stripped)]
            if args.include_code_paths:
                targets += [m.group(1) for m in CODE_PATH_RE.finditer(line)]
            for t in targets:
                if t.startswith(SKIP_PREFIXES):
                    continue
                if is_probably_not_a_link(t):
                    lookalikes.append({"file": f.relative_to(REPO).as_posix(),
                                       "line": i, "target": t})
                    continue
                total_links += 1
                ok, how = resolve(t, f)
                if ok:
                    by_basis[how] = by_basis.get(how, 0) + 1
                else:
                    broken.append({"file": f.relative_to(REPO).as_posix(),
                                   "line": i, "target": t, "kind": "broken"})

    if args.json:
        print(json.dumps({"scanned_files": len(files), "total_links": total_links,
                          "broken_count": len(broken), "broken": broken,
                          "skipped_lookalikes": len(lookalikes),
                          "resolution_basis": by_basis}, ensure_ascii=False, indent=1))
    else:
        print(f"扫描 {len(files)} 个 markdown 文件，检查 {total_links} 条链接")
        print(f"  解析基准分布：相对本文件 {by_basis.get('relative',0)} / "
              f"相对仓库根 {by_basis.get('repo-root',0)} / 纯锚点 {by_basis.get('anchor-only',0)}")
        print(f"  另跳过 {len(lookalikes)} 条疑似示例（正则/占位符/省略号），未计入断链")
        if broken:
            print(f"\n断链 {len(broken)} 处：")
            for b in broken:
                print(f"  {b['file']}:{b['line']}  ->  {b['target']}")
        else:
            print("\n断链 0 处。")
        if args.list:
            print("\n（--list 未实现逐条通过项，避免输出过长）")

    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
