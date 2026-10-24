"""检查第 2 步：Python 符号清单 + 引用关系（AST 级，不靠正则）。

## 检查什么

每个 `.py` 里：**模块 / 类 / 函数**各一条 —— 名字、kind、起止行、参数、装饰器、
有无 docstring、是否 async、是否私有。

再算**引用关系**：每个符号在整个仓里被提到几次；每个模块被谁 import。

## 怎么保证没漏

```
判据：解析成功数 + 解析失败数 == 找到的 .py 总数
     失败清单**逐文件列出**（不许静默跳过）
```

## 只记录，不判断

- 「被引用 0 次」是**一个计数**，不写「死代码该删」；
- 「有两个同名函数」是**两行记录**，不写「应该合并」。

## 用法

    python scripts/survey/01-symbols.py
    python scripts/survey/01-symbols.py --check
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "survey" / "data" / "symbols_py.json"

#: 扫描哪些树的 .py（**逐棵列出，免得下一棒以为漏了哪块**）
SCAN_ROOTS = ["src", "tests", "scripts", "tools/gov-qa", "eval"]
SKIP_DIRS = {
    "__pycache__",
    ".venv",
    "node_modules",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    "var",
    "build",
    "dist",
}


def iter_py() -> list[Path]:
    out: list[Path] = []
    for root in SCAN_ROOTS:
        d = ROOT / root
        if not d.exists():
            continue
        for p in d.rglob("*.py"):
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            out.append(p)
    return sorted(out)


def _first_sentence(doc: str, limit: int = 140) -> str:
    """取 docstring 第一句（跳过 `#` 标题行，按 。；换行切）。"""
    if not doc:
        return ""
    lines = [ln for ln in doc.strip().splitlines()
             if ln.strip() and not ln.strip().startswith("#")]
    if not lines:
        return ""
    s = lines[0].strip()
    for sep in ("。", "；", "\n"):
        if sep in s:
            s = s.split(sep)[0]
    return (s + ("。" if s and not s.endswith("。") else ""))[:limit]


def _sig(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """拼一个人能读的签名（不求完美，求可搜索）。"""
    a = fn.args
    parts: list[str] = []
    posonly = getattr(a, "posonlyargs", [])
    for i, arg in enumerate(posonly + a.args):
        name = arg.arg
        if i < len(posonly):
            parts.append(name + (f"={ast.unparse(a.defaults[i])}" if False else ""))
        else:
            parts.append(name)
    if a.vararg:
        parts.append("*" + a.vararg.arg)
    elif a.kwonlyargs:
        parts.append("*")
    for arg, dflt in zip(a.kwonlyargs, a.kw_defaults):
        parts.append(arg.arg + (f"={ast.unparse(dflt)}" if dflt is not None else ""))
    if a.kwarg:
        parts.append("**" + a.kwarg.arg)
    return f"({', '.join(parts)})"


def _decorators(fn) -> list[str]:
    out = []
    for d in fn.decorator_list:
        try:
            out.append(ast.unparse(d))
        except Exception:
            out.append("?")
    return out


def record_function(fn, rel: str, parent: str) -> dict:
    return {
        "module": rel,
        "qualname": f"{parent}.{fn.name}" if parent else fn.name,
        "name": fn.name,
        "kind": "async_function"
        if isinstance(fn, ast.AsyncFunctionDef)
        else "function",
        "file": rel,
        "lineno": fn.lineno,
        "end_lineno": getattr(fn, "end_lineno", fn.lineno),
        "lines": getattr(fn, "end_lineno", fn.lineno) - fn.lineno + 1,
        "signature": _sig(fn),
        "decorators": _decorators(fn),
        "has_docstring": ast.get_docstring(fn) is not None,
        "purpose": _first_sentence(ast.get_docstring(fn) or ""),
        "private": fn.name.startswith("_") and not fn.name.startswith("__"),
    }


def scan_file(p: Path) -> tuple[dict | None, str | None]:
    rel = str(p.relative_to(ROOT)).replace("\\", "/")
    try:
        tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"), filename=rel)
    except SyntaxError as exc:
        return None, f"{rel}:{exc.lineno}: {exc.msg}"
    except Exception as exc:  # noqa: BLE001 — 失败要具名
        return None, f"{rel}: {type(exc).__name__}: {exc}"

    mod = {
        "module": rel,
        "docstring": (ast.get_docstring(tree) or "")[:400],
        "has_docstring": ast.get_docstring(tree) is not None,
        "imports": [],
        "stars": [],
        "symbols": [],
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for al in node.names:
                mod["imports"].append(
                    {"kind": "import", "module": al.name, "as": al.asname}
                )
        elif isinstance(node, ast.ImportFrom):
            src = "." * (node.level or 0) + (node.module or "")
            for al in node.names:
                if al.name == "*":
                    mod["stars"].append(src)
                else:
                    mod["imports"].append(
                        {
                            "kind": "from",
                            "module": src,
                            "name": al.name,
                            "as": al.asname,
                        }
                    )

    # 顶层 + 嵌套（只走一层类，不走函数内嵌定义 —— 那些是局部的）
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            mod["symbols"].append(record_function(node, rel, ""))
        elif isinstance(node, ast.ClassDef):
            mod["symbols"].append(
                {
                    "module": rel,
                    "qualname": node.name,
                    "name": node.name,
                    "kind": "class",
                    "file": rel,
                    "lineno": node.lineno,
                    "end_lineno": getattr(node, "end_lineno", node.lineno),
                    "lines": getattr(node, "end_lineno", node.lineno) - node.lineno + 1,
                    "signature": "",
                    "decorators": _decorators(node),
                    "has_docstring": ast.get_docstring(node) is not None,
                "purpose": _first_sentence(ast.get_docstring(node) or ""),
                    "private": node.name.startswith("_"),
                }
            )
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    mod["symbols"].append(record_function(sub, rel, node.name))
    return mod, None


def count_references(mods: list[dict]) -> dict[str, int]:
    """每个符号名在**扫描面内全部 .py 文本**里出现几次（含定义行本身）。

    ## 口径要说清楚：这是「文本出现次数」，不是「真的被调用」

    为什么不做精确调用图：Python 的解释性调用（`getattr`、`importlib`、
    装饰器注册、字符串派发）会让精确图**漏掉真实调用** —— 那种图看起来精确、
    实际更危险。**文本计数是下界，不是精确值**，所以字段名就叫 `text_hits`。

    ## 为什么改成「一次扫描建词频表」

    第一版是「拼一个字串 + 每个符号跑一次正则」= O(符号数 × 全文字数)。
    实测本仓扫描面约 **530 万行**、符号约 5 千个 ⇒ 卡死两分钟没出结果。
    现在改成：全文只扫一次、抽出所有标识符、用 `Counter` 计数 ⇒ O(全文 + 符号数)。
    """
    from collections import Counter

    ident = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
    counter: Counter[str] = Counter()
    for p in iter_py():
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        counter.update(ident.findall(text))

    hits: dict[str, int] = {}
    for m in mods:
        for s in m["symbols"]:
            n = s["name"]
            if n not in hits:
                hits[n] = counter.get(n, 0)
    return hits


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    files = iter_py()
    print(f"找到 .py：{len(files)} 个（扫描面：{', '.join(SCAN_ROOTS)}）")

    mods: list[dict] = []
    errors: list[str] = []
    for p in files:
        mod, err = scan_file(p)
        if err:
            errors.append(err)
        else:
            mods.append(mod)

    n_sym = sum(len(m["symbols"]) for m in mods)
    print(f"解析成功：{len(mods)} 个模块 / {n_sym} 个符号")
    print(f"解析失败：{len(errors)} 个")
    for e in errors:
        print(f"  ✘ {e}")

    ok = len(mods) + len(errors) == len(files)
    print(
        f"\n判据：成功 {len(mods)} + 失败 {len(errors)} == 总数 {len(files)} -> "
        f"{'PASS' if ok else 'FAIL'}"
    )

    if args.check:
        if not OUT.exists():
            print(f"✘ 先跑一次生成：{OUT}", file=sys.stderr)
            return 1
        data = json.loads(OUT.read_text(encoding="utf-8"))
        print(
            f"上次落盘：{data['summary']['modules']} 模块 / "
            f"{data['summary']['symbols']} 符号"
        )
        return 0 if ok else 1

    if not ok:
        print("✘ 有解析失败，先修检查器或具名登记，不落盘", file=sys.stderr)
        return 1

    refs = count_references(mods)
    for m in mods:
        for s in m["symbols"]:
            s["text_hits"] = refs.get(s["name"], 0)

    # ── 把「text_hits == 1」拆开说明。**不拆开会被下一棒误读成「死代码」** ──
    once = [s for m in mods for s in m["symbols"] if s.get("text_hits") == 1]
    buckets: dict[str, int] = {}

    def bump(k: str) -> None:
        buckets[k] = buckets.get(k, 0) + 1

    for s in once:
        n, mod = s["name"], s["module"]
        if mod.startswith("tests/") and n.startswith("test_"):
            bump("测试函数（pytest 按名字收集，正常不会出现在别处）")
        elif mod.startswith("tests/") and n.startswith("_"):
            bump("测试文件的私有辅助函数")
        elif mod.startswith("tests/"):
            bump("测试文件里的其他函数")
        elif n.startswith("__") and n.endswith("__"):
            bump("魔术方法")
        elif n.startswith("test_"):
            bump("非 tests 目录的 test_ 函数（可能被外部测试运行器收集）")
        elif n.startswith("visit_") or n.startswith("_visit"):
            bump(
                "AST 访问器方法（由 ast.NodeVisitor **动"
                "态派发**调用 ⇒ 文本里当然只出现一次）"
            )
        elif s["kind"] == "class" and n.endswith(("Error", "Exception")):
            bump("异常类（定义处各一次；有没有被 raise 要另查）")
        else:
            bump("其他（**待下一棒自己核**，本检查不判断）")

    payload = {
        "generated_by": "scripts/survey/01-symbols.py",
        "scan_roots": SCAN_ROOTS,
        "reference_caliber": (
            "text_hits = 该名字在扫描面内全部 .py 文本里出现的次数（含定义行本身）。"
            "**这是下界，不是精确调用图** —— Python 的 getattr/importlib/装饰器注册/"
            "字符串派发会让精确图漏掉真实调用。用 count 判断「有没有人提到」够用，"
            "判断「是不是死代码」不够。"
        ),
        "summary": {
            "files_found": len(files),
            "modules": len(mods),
            "parse_errors": len(errors),
            "symbols": n_sym,
            "classes": sum(
                1 for m in mods for s in m["symbols"] if s["kind"] == "class"
            ),
            "functions": sum(
                1 for m in mods for s in m["symbols"] if s["kind"].endswith("function")
            ),
            "no_docstring": sum(
                1 for m in mods for s in m["symbols"] if not s["has_docstring"]
            ),
            "text_hits_1": len(once),
            "text_hits_1_breakdown": buckets,
        },
        "text_hits_1_note": (
            "text_hits == 1 表示「这个名字在扫描面内只出现过一次，就是它的定义行」。"
            "**这不等于没被使用** —— 已实测出至少两类反例："
            "① pytest 按名字收集 test_* 函数（1,985 个，正常）；"
            "② AST 访问器 visit_* 由 NodeVisitor 动态派发（文本里当然只出现一次）。"
            "要判断真的没被用到，得按第二条口径查（动态派发、属性访问、字符串注册）。"
        ),
        "parse_errors": errors,
        "modules": mods,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已落：{OUT.relative_to(ROOT)}")
    print(
        f"  模块 {len(mods)} / 符号 {n_sym} / "
        f"类 {payload['summary']['classes']} / 函数 {payload['summary']['functions']}"
    )
    print(f"  无 docstring 的符号：{payload['summary']['no_docstring']}")
    print(f"  **只在定义行出现过一次**的名字：{payload['summary']['text_hits_1']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
