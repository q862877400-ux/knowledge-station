"""检查第 3–7 步：数据形状 / 接口面 / 测试面 / 文档面 / 门禁面。

五个面各写一份 JSON。**只记录，不判断。**

## 每一步的覆盖判据（写进输出，可复核）

| 面 | 判据 |
|---|---|
| 数据形状 | 反射种子库，表数 == `sqlite_master` 里的表数；每表列出全部列 |
| 接口面 | 装饰器命中数 == 输出条数（逐条列，不抽样） |
| 测试面 | 测试文件数 == `tests/` 下 `.py` 数；每文件映射到它引用的源码模块 |
| 文档面 | 文档数 == `git ls-files '*.md'` + 未跟踪 `.md` |
| 门禁面 | `Add-Step` 命中数 == 解析出的步数 |
"""

from __future__ import annotations

import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "docs" / "survey" / "data"
SEED_DB = ROOT / "tests" / "fixtures" / "seed" / "knowledge-seed.db"


def dump(name: str, payload: dict) -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    p = DATA / f"{name}.json"
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  → {p.relative_to(ROOT)}")


# ══════════════════════════════════════════════════════════════════════
# 第 3 步：数据形状（反射随仓的种子库）
# ══════════════════════════════════════════════════════════════════════
def step3_schema() -> None:
    print("\n[3] 数据形状")
    if not SEED_DB.exists():
        print(f"  ✘ 种子库不存在：{SEED_DB}")
        return
    conn = sqlite3.connect(f"file:{SEED_DB}?mode=ro", uri=True)
    try:
        objs = conn.execute(
            "SELECT type, name, tbl_name, sql FROM sqlite_master "
            "WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
        ).fetchall()
        tables, indexes, triggers, views = [], [], [], []
        for typ, name, tbl, sql in objs:
            if typ == "table":
                cols = conn.execute(f'PRAGMA table_info("{name}")').fetchall()
                fk = conn.execute(f'PRAGMA foreign_key_list("{name}")').fetchall()
                n = conn.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
                tables.append(
                    {
                        "name": name,
                        "rows_in_seed": n,
                        "columns": [
                            {
                                "name": c[1],
                                "type": c[2],
                                "notnull": bool(c[3]),
                                "default": c[4],
                                "pk": bool(c[5]),
                            }
                            for c in cols
                        ],
                        "foreign_keys": [
                            {"from": f[3], "to_table": f[2], "to": f[4]} for f in fk
                        ],
                        "is_fts": "USING fts" in (sql or "").lower(),
                        "sql_head": (sql or "").split("\n")[0][:120],
                    }
                )
            elif typ == "index":
                indexes.append({"name": name, "table": tbl})
            elif typ == "trigger":
                triggers.append({"name": name, "table": tbl})
            elif typ == "view":
                views.append({"name": name})
        dump(
            "schema",
            {
                "generated_by": "scripts/survey/02-surface.py::step3_schema",
                "source": str(SEED_DB.relative_to(ROOT)),
                "source_note": (
                    "口径说明：本仓的 schema 定义在 `sche"
                    "ma.sql`（冻结），但**行数与真实形态**"
                    "以随仓的种子库为准 —— 种子库是生产库的真子集（含全部表结构）。"
                    "用种子库反射而不是读 `.sql`，是因为 `.sql` 可能与实际库漂移。"
                ),
                "counts": {
                    "tables": len(tables),
                    "indexes": len(indexes),
                    "triggers": len(triggers),
                    "views": len(views),
                    "total_columns": sum(len(t["columns"]) for t in tables),
                    "total_rows_in_seed": sum(t["rows_in_seed"] for t in tables),
                },
                "tables": tables,
                "indexes": indexes,
                "triggers": triggers,
                "views": views,
            },
        )
        print(
            f"     表 {len(tables)} / 列 {sum(len(t['columns']) for t in tables)} / "
            f"索引 {len(indexes)} / 触发器 {len(triggers)} / 视图 {len(views)}"
        )
        for t in sorted(tables, key=lambda x: -x["rows_in_seed"])[:8]:
            print(
                f"     {t['name']:28} {t['rows_in_seed']:>8,} 行 "
                f"{len(t['columns']):>3} 列{'  [FTS]' if t['is_fts'] else ''}"
            )
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════
# 第 4 步：接口面（后端路由 + 前端路由注册）
# ══════════════════════════════════════════════════════════════════════
ROUTE_RE = re.compile(
    r'@(?:app|router)\.(get|post|put|patch|delete)\(\s*["\']([^"\']+)["\']'
)
WEB_REGISTER_RE = re.compile(r"webServer\.register\(\{", re.S)
CONST_RE = re.compile(r"export\s+const\s+(\w+)\s*=\s*['\"]([^'\"]+)['\"]")


def step4_endpoints() -> None:
    print("\n[4] 接口面")
    routes: list[dict] = []
    for p in sorted((ROOT / "src" / "core" / "api").glob("*.py")):
        text = p.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        for i, ln in enumerate(lines, 1):
            m = ROUTE_RE.search(ln)
            if not m:
                continue
            # 往下找 def 名
            handler = ""
            for j in range(i, min(i + 8, len(lines))):
                hm = re.match(r"\s*(?:async\s+)?def\s+(\w+)", lines[j])
                if hm:
                    handler = hm.group(1)
                    break
            routes.append(
                {
                    "method": m.group(1).upper(),
                    "path": m.group(2),
                    "file": str(p.relative_to(ROOT)).replace("\\", "/"),
                    "lineno": i,
                    "handler": handler,
                }
            )

    web = []
    for sub in ("src", "client"):
        pc = ROOT / "plugin" / sub
        if not pc.exists():
            continue
        for p in (
            sorted(pc.glob("*.js")) + sorted(pc.glob("*.ts")) + sorted(pc.glob("*.tsx"))
        ):
            text = p.read_text(encoding="utf-8", errors="replace")
            consts = dict(CONST_RE.findall(text))
            for m in WEB_REGISTER_RE.finditer(text):
                window = text[m.end() : m.end() + 500]
                pm = re.search(r"path:\s*[\"']([^\"']+)[\"']", window) or re.search(
                    r"path:\s*(\w+)", window
                )
                km = re.search(r"kind:\s*[\"']([^\"']+)[\"']", window)
                if not pm:
                    continue
                raw = pm.group(1)
                resolved = consts.get(raw, "")
                web.append(
                    {
                        "path": resolved or raw,
                        "path_raw": raw,
                        "resolved": bool(resolved),
                        "kind": km.group(1) if km else "",
                        "file": str(p.relative_to(ROOT)).replace("\\", "/"),
                        "lineno": text[: m.start()].count("\n") + 1,
                    }
                )

    by_file: dict[str, int] = {}
    for r in routes:
        by_file[r["file"]] = by_file.get(r["file"], 0) + 1
    dump(
        "endpoints",
        {
            "generated_by": "scripts/survey/02-surface.py::step4_endpoints",
            "caliber": (
                '后端 = `src/core/api/*.py` 里的 `@app.verb("path")` 装饰器，'
                "**逐条列出，不抽样**。前端 = `plugin/client/*.ts(x)` 里 "
                "`register({...path...})` 的路由注册。"
            ),
            "counts": {
                "backend_routes": len(routes),
                "backend_files": len(by_file),
                "front_route_registrations": len(web),
            },
            "backend_by_file": dict(sorted(by_file.items(), key=lambda kv: -kv[1])),
            "backend": routes,
            "front": web,
        },
    )
    print(f"     后端 {len(routes)} 条 / {len(by_file)} 个文件；前端注册 {len(web)} 条")
    for f, n in sorted(by_file.items(), key=lambda kv: -kv[1]):
        print(f"     {n:>4}  {f}")


# ══════════════════════════════════════════════════════════════════════
# 第 5 步：测试面（每个测试文件 → 它引用哪些源码模块）
# ══════════════════════════════════════════════════════════════════════
SRC_REF_RE = re.compile(r"src\.core\.[a-z_]+\.[a-z_]+|src\.core\.[a-z_]+")


def step5_tests() -> None:
    print("\n[5] 测试面")
    tdir = ROOT / "tests"
    files = sorted(tdir.rglob("test_*.py")) + sorted(tdir.rglob("*_test.py"))
    tests = []
    for p in files:
        text = p.read_text(encoding="utf-8", errors="replace")
        n_test = len(re.findall(r"^\s*(?:async\s+)?def\s+test_", text, re.M))
        refs = sorted(set(SRC_REF_RE.findall(text)))
        xfail = text.count("xfail")
        skip = len(re.findall(r"pytest\.mark\.skip|@pytest\.mark\.skipif", text))
        tests.append(
            {
                "file": str(p.relative_to(ROOT)).replace("\\", "/"),
                "bytes": p.stat().st_size,
                "test_functions": n_test,
                "src_modules_referenced": refs,
                "xfail_mentions": xfail,
                "skip_marks": skip,
            }
        )

    # 反向：每个源码模块被几个测试文件引用
    inverse: dict[str, list[str]] = {}
    for t in tests:
        for m in t["src_modules_referenced"]:
            inverse.setdefault(m, []).append(t["file"])

    # 找出「一个测试都没引用」的 src/core 模块（**这是计数，不是判断**）
    src_mods = []
    for p in sorted((ROOT / "src" / "core").rglob("*.py")):
        if "__pycache__" in p.parts:
            continue
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        dotted = rel[:-3].replace("/", ".")
        src_mods.append(dotted)
    uncovered_by_tests = [m for m in src_mods if m not in inverse]

    # 第二个口径：**有没有被任何 .py 文本提到**（含 src/scripts，不只测试）。
    # 为什么需要两个口径：`routes_update.py` 在测试里可能不被点名，
    # 但它被 `server.py` import ⇒ 只按测试口径会把它列成"没人用"，那是误读。
    import re as _re

    blob_parts: list[str] = []
    for root in ("src", "tests", "scripts", "tools/gov-qa", "eval"):
        d = ROOT / root
        if not d.exists():
            continue
        for q in d.rglob("*.py"):
            if "__pycache__" in q.parts:
                continue
            try:
                blob_parts.append(q.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                continue
    blob = "\n".join(blob_parts)
    # 三种引用方式都要认（实测本仓三种都在用）：
    #   ① 完整点号路径被写出来（`src.core.api.server`）
    #   ② 名字出现在 import 语句里（含 `from X import a, b` 的多名字写法）
    #   ③ **名字作为字符串出现** —— 本仓 5 个渠道适配器是靠
    #      `_safe_import("mem_gov", "MemGovAdapter")` 这种字符串动态导入挂上的，
    #      纯 import 语法扫描**永远看不到**它们。
    quoted_short: set[str] = set(_re.findall(r"[\"']([a-z_][a-z0-9_]*)['\"]", blob))
    import_line_names: set[str] = set()
    for ln in blob.splitlines():
        s = ln.strip()
        if s.startswith(("from ", "import ")):
            for tok in _re.findall(r"[A-Za-z_][A-Za-z0-9_]*", s):
                import_line_names.add(tok)

    uncovered_any = []
    how_used: dict[str, str] = {}
    for m in src_mods:
        short = m.rsplit(".", 1)[-1]
        if m in blob:
            how_used[m] = "①点号路径"
        elif short in import_line_names:
            how_used[m] = "②import 语句"
        elif short in quoted_short:
            how_used[m] = "③字符串动态导入"
        else:
            uncovered_any.append(m)

    dump(
        "tests",
        {
            "generated_by": "scripts/survey/02-surface.py::step5_tests",
            "caliber": (
                "测试文件数 == tests/ 下 test_*.py + *_test.py 的实际数量。"
                "「引用了哪些源码模块」靠文件内出现的 `src.core.x.y` 字符串判定 —— "
                "**是文本引用，不是运行期覆盖**。运行期"
                "真覆盖要 coverage 数据，本检查没取。"
                "`src_modules_referenced` 为空的测试文件不"
                "代表它没用源码（可能靠 fixture 间接用）。"
            ),
            "counts": {
                "test_files": len(tests),
                "test_functions_total": sum(t["test_functions"] for t in tests),
                "files_with_zero_test_functions": sum(
                    1 for t in tests if t["test_functions"] == 0
                ),
                "src_core_modules": len(src_mods),
                "src_core_modules_not_textually_referenced_by_tests": len(
                    uncovered_by_tests
                ),
                "src_core_modules_not_textually_referenced_by_any_py": len(
                    uncovered_any
                ),
            },
            "caliber_on_unreferenced": (
                "**三种引用机制都算「被用到」**：①完整点号路径 ②import 语句里的名字 "
                '③**名字作为字符串出现**（本仓 5 个渠道适配器靠 `_safe_import("mem_gov", ...)` '
                "字符串动态导入挂上，纯 import 语法永远看不到）。"
                "`reference_mechanism` 字段记下每个模块是靠哪一条被认出来的。"
                "两个口径都要看："
                "① `..._by_tests` = 测试文件文本里没出现它的点号路径；"
                "② `..._by_any_py` = src/scripts/tests/"
                "gov-qa/eval 全部 .py 里既没有点号路径、"
                "也没有 `from/import <末段名>`。"
                "**只有②接近「没人用」；①会把被 serve"
                "r.py import 的 routes_*.py 误列。** "
                "两者都**不等于**「死代码」——动态 impo"
                "rt、字符串派发、插件注册都可能用到它。"
            ),
            "reference_mechanism": how_used,
            "src_core_modules_not_referenced_by_tests": uncovered_by_tests,
            "src_core_modules_not_referenced_by_any_py": uncovered_any,
            "inverse_reference": {k: v for k, v in sorted(inverse.items())},
            "files": tests,
        },
    )
    print(
        f"     测试文件 {len(tests)} / 测试函数 {sum(t['test_functions'] for t in tests)}"
    )
    print(f"     src/core 模块 {len(src_mods)} 个")
    print(f"       测试文件里没点名的：{len(uncovered_by_tests)}")
    print(f"       任何 .py 里都没被 import/提到：{len(uncovered_any)}")
    for m in uncovered_any[:12]:
        print(f"       {m}")


# ══════════════════════════════════════════════════════════════════════
# 第 6 步：文档面（出链 / 入链 / 孤儿）
# ══════════════════════════════════════════════════════════════════════
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def step6_docs() -> None:
    print("\n[6] 文档面")
    docs = []
    for p in sorted((ROOT / "docs").rglob("*.md")):
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        text = p.read_text(encoding="utf-8", errors="replace")
        title = ""
        for ln in text.splitlines():
            if ln.startswith("# "):
                title = ln[2:].strip()
                break
        links = []
        for m in LINK_RE.finditer(text):
            tgt = m.group(2).split("#")[0].strip()
            if tgt and not tgt.startswith(("http://", "https://", "mailto:")):
                links.append(tgt)
        docs.append(
            {
                "path": rel,
                "bytes": p.stat().st_size,
                "lines": text.count("\n") + (0 if text.endswith("\n") else 1),
                "title": title,
                "out_links": sorted(set(links)),
                "n_links": len(links),
            }
        )

    # 反向索引（按文件名或相对路径匹配）
    inbound: dict[str, list[str]] = {d["path"]: [] for d in docs}
    by_name: dict[str, list[str]] = {}
    for d in docs:
        by_name.setdefault(Path(d["path"]).name, []).append(d["path"])
    for d in docs:
        base = Path(d["path"]).parent
        for tgt in d["out_links"]:
            cand = (base / tgt).as_posix()
            hit = None
            if cand in inbound:
                hit = [cand]
            else:
                hit = by_name.get(Path(tgt).name)
            if hit:
                for h in hit:
                    if d["path"] not in inbound[h]:
                        inbound[h].append(d["path"])

    orphans = [k for k, v in inbound.items() if not v]
    for d in docs:
        d["inbound"] = inbound.get(d["path"], [])
        d["inbound_count"] = len(d["inbound"])

    tracked_md = subprocess.run(
        ["git", "ls-files", "*.md"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.split()
    all_md = [f for f in tracked_md if f.startswith("docs/")]

    dump(
        "docs",
        {
            "generated_by": "scripts/survey/02-surface.py::step6_docs",
            "caliber": (
                "扫描 `docs/**/*.md`（含 archive）。链接用 markdown `[t](p)` 正则抽取；"
                "入链按「相对路径命中」或「文件名唯一命中」判定 —— "
                "**文件名不唯一时可能记到多个目标，这是近似，不是精确图**。"
            ),
            "counts": {
                "docs_files": len(docs),
                "docs_tracked_md": len(all_md),
                "orphans_no_inbound": len(orphans),
                "total_links": sum(d["n_links"] for d in docs),
            },
            "orphans": sorted(orphans),
            "files": docs,
        },
    )
    print(f"     文档 {len(docs)} 份（受控 .md 在 docs/ 下 {len(all_md)} 份）")
    print(f"     **没有任何入链的（孤儿）**：{len(orphans)} 份")
    for o in sorted(orphans)[:12]:
        print(f"       {o}")


# ══════════════════════════════════════════════════════════════════════
# 第 7 步：门禁面
# ══════════════════════════════════════════════════════════════════════
STEP_RE = re.compile(r"""Add-Step\s+(?:"([^"]+)"|'([^']+)')""")
SUITES_BLOCK_RE = re.compile(r"const SUITES = \[(.*?)\]", re.S)
SUITE_RE = re.compile(r"""['"]([^'"]+\.mjs)['"]""")


def step7_gates() -> None:
    print("\n[7] 门禁面")
    rg = ROOT / "scripts" / "run-gates.ps1"
    text = rg.read_text(encoding="utf-8", errors="replace")
    steps = [a or b for a, b in STEP_RE.findall(text)]
    # 门禁里跑的命令（粗抽：python -m / pwsh -File / node）
    cmds = sorted(set(re.findall(r"([\w][\w./\\-]*\.py)", text)))
    cmds += sorted(set(re.findall(r"([\w][\w./\\-]*\.mjs)", text)))
    cmds += sorted(set(re.findall(r"([\w][\w./\\-]*\.ps1)", text)))
    cmds = [c for c in cmds if not c.startswith(".")]

    sm = ROOT / "plugin" / "scripts" / "smoke-all.mjs"
    suites: list[str] = []
    if sm.exists():
        stext = sm.read_text(encoding="utf-8", errors="replace")
        blk = SUITES_BLOCK_RE.search(stext)
        if blk:
            suites = sorted(set(SUITE_RE.findall(blk.group(1))))

    dump(
        "gates",
        {
            "generated_by": "scripts/survey/02-surface.py::step7_gates",
            "source": "scripts/run-gates.ps1 + plugin/scripts/smoke-all.mjs",
            "counts": {
                "steps": len(steps),
                "smoke_suites": len(suites),
                "python_or_node_scripts_invoked": len(cmds),
            },
            "steps": steps,
            "scripts_invoked": cmds,
            "smoke_suites": suites,
            "note": (
                "`steps` 含 `selftest` 分支（门禁自测"
                "用的假步），所以并不全是真实验证步。"
                "**这是解析结果，不是设计意图** —— 每一"
                "步具体跑什么要读 run-gates.ps1 原文。"
            ),
        },
    )
    print(
        f"     Add-Step {len(steps)} 个；冒烟套 {len(suites)} 个；"
        f"被调脚本 {len(cmds)} 个"
    )


def main() -> int:
    step3_schema()
    step4_endpoints()
    step5_tests()
    step6_docs()
    step7_gates()
    print("\n全部落盘")
    return 0


if __name__ == "__main__":
    sys.exit(main())
