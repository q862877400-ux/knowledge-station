"""检查第 10 步（规则层）：把「判定规则」抽成表。

## 补的是哪个缺口

`COVERAGE.md` 里「业务规则的语义」一直标着未做：抓到了正则和行号，
但「什么算条款头」这类规则**怎么算的**没进地图。

完全复述算法不现实（那是重写一遍代码）。本脚本做**可机械做的那部分**：

| 抽什么 | 为什么有用 |
|---|---|
| 模块级正则常量（`_RE_*` / `*_RE`） | 规则的字面判据 |
| 数值阈值常量（`_MIN_*` / `*_MAX` / `RRF_K` …） | 规则的门槛 |
| 它们**上方紧邻的注释** | 规则的**理由**（本仓注释就是说明书） |
| 所在函数（如果是函数内常量） | 规则挂在哪一步 |

⇒ 下一棒看这张表就知道「条款头判据是哪条正则、阈值是多少、当初为什么这么定」。

**只记录，不判断阈值合不合理。**
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import dump  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "docs" / "survey" / "data"

#: 正则类常量的名字形态（本仓两种写法都有）
RE_NAME = re.compile(r"^(?:_?[A-Z0-9_]*_RE|_RE_[A-Z0-9_]+|RE_[A-Z0-9_]+|"
                     r"_?[A-Z0-9_]*_RE_?[A-Z0-9_]*)$")
#: 数值阈值类常量的名字形态
THRESH_NAME = re.compile(r"^(?:_[A-Z][A-Z0-9_]*|[A-Z][A-Z0-9_]{2,})$")



def comment_above(lines: list[str], lineno: int, max_lines: int = 6) -> str:
    """取某行上方紧邻的注释块（连续 `#` 行），**保留原文**。"""
    out: list[str] = []
    i = lineno - 2
    while i >= 0 and len(out) < max_lines:
        s = lines[i].strip()
        if not s.startswith("#"):
            break
        out.append(s.lstrip("#").strip())
        i -= 1
    return " ".join(reversed([x for x in out if x]))[:300]


def main() -> int:
    rules: list[dict] = []
    files = 0
    for p in sorted((ROOT / "src").rglob("*.py")):
        if "__pycache__" in p.parts:
            continue
        files += 1
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        src = p.read_text(encoding="utf-8", errors="replace")
        lines = src.splitlines()
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue

        # 走一遍：模块级 + 函数体内的赋值
        def walk(nodes, scope: str) -> None:
            for node in nodes:
                if isinstance(node, ast.Assign):
                    for tgt in node.targets:
                        if not isinstance(tgt, ast.Name):
                            continue
                        name = tgt.id
                        is_re = bool(RE_NAME.match(name)) and isinstance(
                            node.value, (ast.Call, ast.Constant))
                        is_num = (THRESH_NAME.match(name)
                                  and isinstance(node.value, ast.Constant)
                                  and isinstance(node.value.value, (int, float)))
                        if not (is_re or is_num):
                            continue
                        val = ""
                        if is_re:
                            # 尽量取正则字面量
                            try:
                                val = ast.unparse(node.value)[:200]
                            except Exception:      # noqa: BLE001
                                val = "<unparse 失败>"
                        else:
                            val = repr(node.value.value)
                        rules.append({
                            "name": name,
                            "kind": "regex" if is_re else "threshold",
                            "value": val,
                            "file": rel,
                            "lineno": node.lineno,
                            "scope": scope or "(模块级)",
                            "comment": comment_above(lines, node.lineno),
                        })
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    walk(node.body, node.name)
                elif isinstance(node, ast.ClassDef):
                    walk(node.body, node.name)
        walk(tree.body, "")

    by_kind: dict[str, int] = {}
    by_file: dict[str, int] = {}
    for r in rules:
        by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + 1
        by_file[r["file"]] = by_file.get(r["file"], 0) + 1
    with_comment = sum(1 for r in rules if r["comment"])

    dump("rules", {
        "generated_by": "scripts/survey/10-rules.py",
        "caliber": (
            "从 `src/**/*.py` 的**赋值语句**里抽两类常量："
            "① 正则类（名字匹配 `*_RE` / `_RE_*`）；②"
            " 数值阈值类（全大写名字 + 数字字面量）。"
            "`comment` = 该行**上方紧邻的连续注释**（最多 6 行，保留原文、不概括）。"
            "`scope` = 所在函数/类；模块级记 `(模块级)`。"
            "**这是「规则的字面判据 + 当初的理由」，不是「算法的完整复述」** —— "
            "要把算法讲清得逐行读函数体。"
        ),
        "counts": {
            "py_files_scanned": files,
            "rules": len(rules),
            "by_kind": by_kind,
            "with_comment": with_comment,
            "without_comment": len(rules) - with_comment,
            "files_with_rules": len(by_file),
        },
        "by_file_top": dict(sorted(by_file.items(), key=lambda kv: -kv[1])[:20]),
        "rules": rules,
    })
    print(f"     扫 {files} 个 py；抽出 {len(rules)} 条规则常量")
    print(f"     正则 {by_kind.get('regex', 0)} / 阈值 {by_kind.get('threshold', 0)}；"
          f"带注释的 {with_comment} / 没注释的 {len(rules) - with_comment}")
    for f, n in sorted(by_file.items(), key=lambda kv: -kv[1])[:6]:
        print(f"       {n:>3}  {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
