"""检查第 6 步（内容层）：测试说了什么 / 文档说了什么 / 前端有什么。

前面几步到「有什么、在哪、谁引谁」。「彻底摸透」还要一层：
**每个测试断言什么、每份文档讲什么、每个前端组件干什么。**

## 为什么这一步值得单独做

- **测试函数名就是本仓的覆盖说明书**：本仓测试名是中文描述
  （`test_跨标准误命中必须返回_None_而不是别的标准`），
  把「文件名 → 它的测试名清单」列出来，等于给了下一棒一张
  「哪个功能已经被钉住」的索引，不用读测试体。
- **文档首段就是它的用途**：244 份文档，只有标题不够。
- **前端 33 个文件**：前面只抓到路由注册，组件职责没进地图。

**只记录，不判断。**
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import dump, first_sentence  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "docs" / "survey" / "data"





# ══════════════════════════════════════════════════════════════════════
# A. 测试说了什么
# ══════════════════════════════════════════════════════════════════════
def step_test_content() -> None:
    print("\n[A] 测试内容（每个测试函数的名字 + 它的一句话）")
    files = []
    for p in sorted((ROOT / "tests").rglob("test_*.py")):
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError as exc:
            files.append({"file": rel, "parse_error": str(exc)[:120], "tests": []})
            continue
        tests = []
        # 走到类里（本仓用 class 分组）
        def walk(nodes, prefix=""):
            for n in nodes:
                if isinstance(n, ast.ClassDef):
                    walk(n.body, (prefix + n.name + "::") if prefix == "" else prefix + n.name + "::")
                elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if n.name.startswith("test"):
                        tests.append({
                            "name": n.name,
                            "group": prefix.rstrip(":"),
                            "purpose": first_sentence(ast.get_docstring(n) or ""),
                            "lineno": n.lineno,
                        })
        walk(tree.body)
        files.append({"file": rel, "tests": tests,
                      "n_tests": len(tests),
                      "n_named_descriptively": sum(1 for t in tests if len(t["name"]) > 20)})
    total = sum(f.get("n_tests", 0) for f in files)
    with_doc = sum(1 for f in files for t in f["tests"] if t["purpose"])
    dump("test_content", {
        "generated_by": "scripts/survey/06-content.py::step_test_content",
        "caliber": ("`tests` = 每个 `def test*` 的名字、所在类、行号，"
                    "以及它的 **docstring 第一句**（很多测试没 docstring，那就空着）。"
                    "**名字本身就是本仓的覆盖说明书**（测试名写成中文描述）。"),
        "counts": {"files": len(files), "test_functions": total,
                   "with_docstring": with_doc,
                   "without_docstring": total - with_doc},
        "files": files,
    })
    print(f"     {len(files)} 个文件 / {total} 个测试函数；"
          f"有 docstring 的 {with_doc} / 没有 {total - with_doc}")


# ══════════════════════════════════════════════════════════════════════
# B. 文档说了什么
# ══════════════════════════════════════════════════════════════════════
def step_doc_content() -> None:
    print("\n[B] 文档内容（每份的标题 + 首段 + 小节标题）")
    docs = []
    for p in sorted((ROOT / "docs").rglob("*.md")):
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        text = p.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        title = ""
        summary = ""
        headings: list[str] = []
        in_code = False
        for ln in lines:
            s = ln.strip()
            if s.startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                continue
            if s.startswith("# "):
                if not title:
                    title = s[2:].strip()
                continue
            if s.startswith("## "):
                headings.append(s[3:].strip()[:60])
                continue
            if not summary and s and not s.startswith(("#", ">", "|", "-", "*", "!", "<")):
                summary = s[:160]
        docs.append({
            "path": rel,
            "title": title,
            "summary": summary,
            "h2_headings": headings[:25],
            "n_h2": len(headings),
            "lines": len(lines),
        })
    no_summary = [d for d in docs if not d["summary"]]
    dump("doc_content", {
        "generated_by": "scripts/survey/06-content.py::step_doc_content",
        "caliber": ("`summary` = 第一个 `# 标题` 之后、第一个非空且**不是** 引用/表格/列表/"
                    "代码/图片 的行，上限 160 字。`h2_he"
                    "adings` 是全部二级标题（前 25 个）。"
                    "**`summary` 为空说明该文档开头就是列表或表格**（比如索引类），"
                    "不是它没内容。"),
        "counts": {"docs": len(docs), "with_summary": len(docs) - len(no_summary),
                   "without_summary": len(no_summary)},
        "docs": docs,
    })
    print(f"     {len(docs)} 份；有首段摘要 {len(docs) - len(no_summary)} / "
          f"没有 {len(no_summary)}")


# ══════════════════════════════════════════════════════════════════════
# C. 前端有什么
# ══════════════════════════════════════════════════════════════════════
EXPORT_PAT = re.compile(
    r"export\s+(?:default\s+)?(?:async\s+)?"
    r"(?:function|const|class|interface|type|enum)\s+([A-Za-z_$][\w$]*)")
DECL_PAT = re.compile(r"^(?:export\s+)?(?:function|const|class)\s+([A-Za-z_$][\w$]*)", re.M)


def step_web_content() -> None:
    print("\n[C] 前端内容（每个文件的导出与声明）")
    files = []
    pc = ROOT / "plugin" / "client"
    for p in sorted(pc.glob("*")) if pc.exists() else []:
        if p.suffix not in (".ts", ".tsx", ".js", ".jsx"):
            continue
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        text = p.read_text(encoding="utf-8", errors="replace")
        exports = sorted(set(EXPORT_PAT.findall(text)))
        decls = sorted(set(DECL_PAT.findall(text)))
        # 顶层注释即用途
        head = ""
        for ln in text.splitlines()[:40]:
            s = ln.strip()
            if s.startswith(("/*", "*", "//")):
                s2 = s.lstrip("/* ").lstrip("// ").strip()
                if s2 and not s2.startswith("---") and len(s2) > 6:
                    head = s2[:120]
                    break
        files.append({
            "file": rel,
            "lines": text.count("\n") + 1,
            "exports": exports[:60],
            "n_exports": len(exports),
            "declarations": decls[:60],
            "n_declarations": len(decls),
            "header_note": head,
            "has_jsx": "<" in text and ("</" in text or "/>" in text),
        })
    # 也把 plugin/src 的宿主侧带上
    for p in sorted((ROOT / "plugin" / "src").glob("*.js")):
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        text = p.read_text(encoding="utf-8", errors="replace")
        exports = sorted(set(EXPORT_PAT.findall(text)))
        decls = sorted(set(DECL_PAT.findall(text)))
        files.append({
            "file": rel, "lines": text.count("\n") + 1,
            "exports": exports[:60], "n_exports": len(exports),
            "declarations": decls[:60], "n_declarations": len(decls),
            "header_note": "", "has_jsx": False,
        })
    dump("web_content", {
        "generated_by": "scripts/survey/06-content.py::step_web_content",
        "caliber": ("`exports` / `declarations` 用**正则**抽取（没有 TS AST 工具链），"
                    "**这是近似，不是完整符号表**。`header_note` 取文件开头 40 行内"
                    "第一条注释的首句。"),
        "counts": {"files": len(files),
                   "total_exports": sum(f["n_exports"] for f in files),
                   "total_declarations": sum(f["n_declarations"] for f in files),
                   "with_jsx": sum(1 for f in files if f["has_jsx"])},
        "files": files,
    })
    print(f"     {len(files)} 个文件 / 导出 {sum(f['n_exports'] for f in files)} / "
          f"声明 {sum(f['n_declarations'] for f in files)}")


def main() -> int:
    step_test_content()
    step_doc_content()
    step_web_content()
    print("\n全部落盘")
    return 0


if __name__ == "__main__":
    sys.exit(main())
