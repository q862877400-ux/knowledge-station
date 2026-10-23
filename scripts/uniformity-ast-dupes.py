"""跨文件同函数体检测（α-等价）—— 统一化尺子的第 ⑤ 项。

为什么自己写：`pyscn` 的行块克隆按行块判，上千组里绝大多数是探针样例、
声明式元数据、来源块，噪声大到无法逐组裁决。按**函数体**判、先做
α-归一化（局部绑定名抹平、保留全局引用与属性名），组数少一个量级，
且直接对准「同一个功能多个函数重复实现」。

判据（与 `repo-uniformity-ratchet` skill 一致）：
- 去 docstring；把局部绑定名（形参、局部赋值、for/with/except 目标、
  推导式变量、嵌套 def/class 名、import 别名）抹成同一占位符；
- **保留**全局引用与属性名（`obj.method` 的 `method` 不改）；
- 同文件同名不算（那是重载 / 分支实现），只报**跨文件**；
- 函数体语句数 < MIN_STMTS 的不算（琐碎样板）。

用法：
    python scripts/uniformity-ast-dupes.py [--roots src tests scripts tools/gov-qa]
                                           [--min-stmts 4] [--json OUT] [--list]
    python scripts/uniformity-ast-dupes.py --selftest

退出码：0 = 扫描完成（不论组数）；2 = 有文件语法错；3 = 自测失败。
「组数是否超标」由 `scripts/check-repo-uniformity.py` 对基线判。
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

MIN_STMTS = 4
SKIP_DIRS = {"__pycache__", "node_modules", ".venv", ".git", ".mypy_cache",
             ".pytest_cache", "archive", "_trash"}
PLACEHOLDER = "_L"


def _bound_names(fn: ast.AST) -> set[str]:
    """收集该函数作用域内**自己绑定**的名字。

    只收本作用域的绑定：形参、赋值目标、for/with/except 目标、
    推导式变量、嵌套 def/class 名、import 别名。全局引用（未绑定就出现的
    `Name`）不收 —— 那些是跨模块依赖，抹掉会把「调用同一个全局」和
    「调用不同全局」判成同一件事。
    """
    names: set[str] = set()
    args = fn.args  # type: ignore[attr-defined]
    for a in list(args.posonlyargs) + list(args.args) + list(args.kwonlyargs):
        names.add(a.arg)
    if args.vararg:
        names.add(args.vararg.arg)
    if args.kwarg:
        names.add(args.kwarg.arg)

    for node in ast.walk(fn):
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            names.add(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node is not fn:
            names.add(node.name)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            names.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.asname:
                    names.add(alias.asname)
                elif alias.name != "*":
                    names.add(alias.name.split(".")[0])
    return names


class _AlphaNormalizer(ast.NodeTransformer):
    """把局部绑定名抹成同一占位符，其余原样保留。"""

    def __init__(self, local: set[str]) -> None:
        self.local = local

    def visit_Name(self, node: ast.Name) -> ast.AST:
        if node.id in self.local:
            return ast.copy_location(ast.Name(id=PLACEHOLDER, ctx=node.ctx), node)
        return node

    def visit_arg(self, node: ast.arg) -> ast.AST:
        node.arg = PLACEHOLDER
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        node.name = PLACEHOLDER
        return self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        node.name = PLACEHOLDER
        return self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
        node.name = PLACEHOLDER
        return self.generic_visit(node)


def _strip_docstring(fn: ast.AST) -> None:
    body = getattr(fn, "body", None)
    if not body:
        return
    first = body[0]
    if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)):
        del body[0]


def _body_stmt_count(fn: ast.AST) -> int:
    """数函数体里真正干活的语句数（不含 docstring）。"""
    body = list(getattr(fn, "body", []))
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        body = body[1:]
    n = 0
    stack = list(body)
    while stack:
        node = stack.pop()
        n += 1
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.stmt):
                stack.append(child)
    return n


def fingerprint(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """返回 α-归一化后的函数体指纹。"""
    local = _bound_names(fn)
    clone = ast.parse(ast.unparse(fn)).body[0]
    assert isinstance(clone, (ast.FunctionDef, ast.AsyncFunctionDef))
    _strip_docstring(clone)
    # 签名也参与指纹：参数个数/默认值不同说明不是同一个东西。
    clone.body = [ast.Expr(value=ast.Constant(value="__BODY__"))] + clone.body
    _AlphaNormalizer(local).visit(clone)
    dumped = ast.dump(clone, annotate_fields=True, include_attributes=False)
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()[:16]


def iter_py_files(roots: list[Path]):
    for root in roots:
        if not root.exists():
            continue
        if root.is_file() and root.suffix == ".py":
            yield root
            continue
        for p in root.rglob("*.py"):
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            yield p


def scan(roots: list[Path], min_stmts: int = MIN_STMTS) -> tuple[dict[str, list[dict]], list[str]]:
    """返回 (指纹 -> 出现处列表, 语法错文件列表)。"""
    groups: dict[str, list[dict]] = defaultdict(list)
    syntax_errors: list[str] = []
    seen: set[tuple[str, str]] = set()  # (file, qualname) 去重：嵌套遍历会重复访问

    for path in iter_py_files(roots):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError as exc:
            syntax_errors.append(f"{path}: {exc.msg} (line {exc.lineno})")
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            key = (str(path), f"{node.name}@{node.lineno}")
            if key in seen:
                continue
            seen.add(key)
            if _body_stmt_count(node) < min_stmts:
                continue
            try:
                fp = fingerprint(node)
            except (SyntaxError, ValueError):
                continue
            groups[fp].append({
                "file": str(path),
                "name": node.name,
                "line": node.lineno,
                "stmts": _body_stmt_count(node),
            })
    return dict(groups), syntax_errors


def cross_file_groups(groups: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """只保留**跨文件**出现的组（同文件多处不算重复实现）。"""
    out: dict[str, list[dict]] = {}
    for fp, hits in groups.items():
        files = {h["file"] for h in hits}
        if len(files) >= 2:
            out[fp] = sorted(hits, key=lambda h: (h["file"], h["line"]))
    return out


# ── 自测：用已知正反例校准判据 ──────────────────────────────────────────
_SELFTEST_SRC = {
    # 正例：改名后逐字相同 ⇒ 必须判重复
    "a.py": '''
def load_text(path):
    with open(path, encoding="utf-8") as fh:
        raw = fh.read()
    if not raw:
        raise ValueError("empty")
    return raw.strip()
''',
    "b.py": '''
def read_document(p):
    with open(p, encoding="utf-8") as handle:
        data = handle.read()
    if not data:
        raise ValueError("empty")
    return data.strip()
''',
    # 反例：已参数化好的薄转发壳 ⇒ 不该判重复
    "c.py": '''
def fetch_a(x):
    return _dispatch("a", x)


def fetch_b(x):
    return _dispatch("b", x)
''',
    # 反例：同形不同字段表的 __post_init__ ⇒ 不该判重复
    "d.py": '''
class P:
    def __post_init__(self):
        self.a = str(self.a).strip()
        self.b = str(self.b).strip()
        self.c = str(self.c).strip()
        self.d = str(self.d).strip()
''',
    "e.py": '''
class Q:
    def __post_init__(self):
        self.w = int(self.w or 0)
        self.x = int(self.x or 0)
        self.y = int(self.y or 0)
        self.z = int(self.z or 0)
''',
}


def _selftest() -> int:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        for name, src in _SELFTEST_SRC.items():
            (root / name).write_text(src, encoding="utf-8")
        groups, errs = scan([root], min_stmts=3)
        dupes = cross_file_groups(groups)
        pairs = sorted({tuple(sorted({h["file"].rsplit("\\", 1)[-1].rsplit("/", 1)[-1] for h in hs}))
                        for hs in dupes.values()})
        ok = True
        if errs:
            print(f"FAIL 自测出现语法错：{errs}")
            ok = False
        if ("a.py", "b.py") not in pairs:
            print(f"FAIL 正例未被判重复（a.py/b.py）—— 实测组：{pairs}")
            ok = False
        if ("c.py",) in pairs:
            print("FAIL 反例被误判：薄转发壳 fetch_a/fetch_b")
            ok = False
        if ("d.py", "e.py") in pairs:
            print("FAIL 反例被误判：__post_init__ 同形不同字段表")
            ok = False
        print(f"{'PASS' if ok else 'FAIL'} 自测：正例命中、两个反例未误判（实测跨文件组 {pairs}）")
        return 0 if ok else 3


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--roots", nargs="*", default=["src", "tests", "scripts", "tools/gov-qa"])
    ap.add_argument("--min-stmts", type=int, default=MIN_STMTS)
    ap.add_argument("--json", default="")
    ap.add_argument("--list", action="store_true", help="逐组打印成员")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        return _selftest()

    roots = [Path(r) for r in args.roots]
    groups, errs = scan(roots, args.min_stmts)
    dupes = cross_file_groups(groups)
    total_hits = sum(len(v) for v in dupes.values())

    print(f"跨文件同函数体：{len(dupes)} 组 / {total_hits} 处（min_stmts={args.min_stmts}）")
    by_size = sorted(dupes.items(), key=lambda kv: -max(h["stmts"] for h in kv[1]))
    for fp, hits in by_size[:15]:
        files = sorted({h["file"] for h in hits})
        print(f"  {fp}  {len(files)} 文件 / {len(hits)} 处 / 最大 {max(h['stmts'] for h in hits)} 语句")
        if args.list:
            for h in hits:
                print(f"      {h['file']}:{h['line']}  {h['name']}  ({h['stmts']} 语句)")
    if errs:
        print(f"\n语法错 {len(errs)} 个文件：", file=sys.stderr)
        for e in errs:
            print("  " + e, file=sys.stderr)

    if args.json:
        Path(args.json).write_text(json.dumps({
            "groups": len(dupes),
            "hits": total_hits,
            "min_stmts": args.min_stmts,
            "detail": {fp: hits for fp, hits in dupes.items()},
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"明细已落：{args.json}")

    return 2 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
