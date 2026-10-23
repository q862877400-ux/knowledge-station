"""仓库统一化尺子 —— 五条指标，一条命令出全部读数，exit code 即判据。

指标与权威出处（「只接线，不发明」）：

| # | 指标 | 权威出处 | 机械执行 |
|---|---|---|---|
| ① | 命名 / 导入 / 循环依赖 | Google Python Style Guide + PEP8 | `ruff --select E,F,I,N`（**两档已校准**，见下） |
| ② | 重复代码（行块级） | pyscn Type 1–4 克隆检测 | `pyscn analyze`（**信息项**，见下） |
| ③ | 本仓文件契约（模块 docstring） | 本仓 `AGENTS.md`「代码注释」+ `docs/naming-convention.md` | 自写扫描 |
| ④ | 跨目录同名文件 | `docs/naming-convention.md` §七「一个东西只归一处」 | 自写扫描 |
| ⑤ | **跨文件同函数体** | Type-2 克隆（α-等价），出处同 ② | `scripts/uniformity-ast-dupes.py` |

**① 的两档校准（本仓实测，2026-10-23）**——中文代码库不能用一把尺子：

- `E501`（行长）：本仓 5,096 条里 **4,684 条是中文散文行**（注释/文档串），
  412 条是真代码行。中文在 88 列下只有 44 个汉字，而本仓的注释是**承载判断依据**的
  （每条都写着"为什么这么做、实测多少"）⇒ 按 88 列判会把**判断依据本身**判成违规。
  故：**代码行 88 显示列 / 散文行 120 显示列**（120 列 = 60 个汉字）。
  按 120 档后散文行只剩 **64 条**仍超 ⇒ 判据仍然有效，不是放水。
- `N802`（函数名应小写）：本仓 492 条里 **452 条是中文测试名**
  （`test_隐藏文档被排除`），19 条是 Windows API 名的 mock（必须同名才能替换），
  21 条是刻意的强调写法（`test_unapproved_material_is_BLOCKED`）。
  中文测试名是**刻意选择**（`docs/naming-convention.md`「代码跟随语言」；
  测试名要说清意图，中文比拼音清楚）⇒ N802 退出判据，只在 `--report` 里打印。
  剩余 21 条"其他"里绝大多数是**同一个刻意的强调写法**，同样不判。

⇒ ① 的判据读数 = `E501(代码行) + E501(散文行>120) + 其余全部规则`。

★★ ⑤ 是最关键的一条：② 按行块判，上千组里绝大多数是样板（探针样例、
声明式元数据、来源块），噪声大到无法逐组裁决；⑤ 按**函数体**判，
组数少一个量级，直接对准「同一个功能多个函数重复实现」。

②（行块克隆）**降级为信息项**：它在**每一次纯格式改动下都会涨**
（本仓实测：ruff format 类改动、docstring 折行都会让它变），
它衡量的不是「重复实现」。保留打印、不决定 exit code。

尺子四条自证（缺一条就不可信）：
1. 一条命令出全部读数，exit code 即判据；
2. 每条指标能指回权威源（见上表）；
3. 工具不可用时 **FAIL，不静默跳过**；
4. 读数幂等：同一棵树跑两次同一个数（`--repeat-check` 验）。

用法：
    python scripts/check-repo-uniformity.py             # 判据模式，exit 0/1
    python scripts/check-repo-uniformity.py --report    # 打印读数表
    python scripts/check-repo-uniformity.py --write-baseline   # 收口时写天花板
    python scripts/check-repo-uniformity.py --repeat-check     # 验幂等
    python scripts/check-repo-uniformity.py --selftest         # 验判据能抓负例
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "docs" / "uniformity" / "baseline.json"
# 扫描器脚本自身的位置**不随被测树变**（自测会拿临时树当 ROOT）。
DUPES_SCRIPT = Path(__file__).resolve().parent / "uniformity-ast-dupes.py"

# 扫描面：本仓自己的代码。`tools/gov-qa` 是**另一条线**的活跃工作
# （767 项未跟踪），只测量、不判红 —— 见 baseline.json 的 scope_note。
SCAN_ROOTS = ["src", "tests", "scripts"]
MEASURE_ONLY_ROOTS = ["tools/gov-qa"]
SKIP_DIRS = {"__pycache__", "node_modules", ".venv", ".git", ".mypy_cache", ".pytest_cache"}

RUFF_SELECT = "E,F,I,N"
PY_BIN = ROOT / ".venv" / "Scripts" / "python.exe"
if not PY_BIN.exists():
    PY_BIN = Path(sys.executable)


# ── 工具层 ────────────────────────────────────────────────────────────────
def _run(argv: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def _ruff_available() -> tuple[bool, str]:
    r = _run([str(PY_BIN), "-m", "ruff", "--version"])
    return r.returncode == 0, (r.stdout or r.stderr).strip()


def _pyscn_available() -> tuple[bool, str]:
    r = _run([str(PY_BIN), "-m", "pyscn", "--version"])
    return r.returncode == 0, (r.stdout or r.stderr).strip()


# ── ① 命名 / 导入 / 循环依赖 ──────────────────────────────────────────────
#: 判据用的规则集。E501 与 N802 **单独处理**（见文件头的两档校准），
#: 这里只放不受中文影响的那些。
RUFF_SELECT = "E,F,I,N"
RUFF_EXCLUDE = {"E501", "N802"}
CODE_WIDTH = 88      # 代码行显示列上限
PROSE_WIDTH = 120    # 散文行（注释/文档串）显示列上限


def _disp_width(s: str) -> int:
    """按**显示列**算宽度（中文/全角算 2 列）。

    不能用 `len()`：一个汉字在终端/编辑器里占两列，用字符数判宽会让
    中文注释一改就涨 —— 这正是本仓历史上"改宽度就涨"的假红来源。
    """
    import unicodedata
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in s)


def _prose_lines(src: str) -> set[int]:
    """源码里属于注释或字符串的行号集合（用 tokenize，不用正则猜）。"""
    import io
    import tokenize
    prose: set[int] = set()
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type == tokenize.COMMENT:
                prose.add(tok.start[0])
            elif tok.type == tokenize.STRING:
                for ln in range(tok.start[0], tok.end[0] + 1):
                    prose.add(ln)
    except (tokenize.TokenError, IndentationError):
        pass
    return prose


def _ruff_available() -> tuple[bool, str]:
    r = _run([str(PY_BIN), "-m", "ruff", "--version"])
    return r.returncode == 0, (r.stdout or r.stderr).strip()


def _pyscn_available() -> tuple[bool, str]:
    r = _run([str(PY_BIN), "-m", "pyscn", "--version"])
    return r.returncode == 0, (r.stdout or r.stderr).strip()


def _ruff_concise(roots: list[str], select: str) -> list[str]:
    ok, ver = _ruff_available()
    if not ok:
        raise RuntimeError(
            f"ruff 不可用（{ver or 'not installed'}）⇒ FAIL，不跳过。"
            f" 装法：{PY_BIN} -m pip install ruff")
    argv = [str(PY_BIN), "-m", "ruff", "check", *roots,
            "--select", select, "--output-format", "concise", "--no-cache"]
    r = _run(argv)
    if r.returncode not in (0, 1):
        raise RuntimeError(f"ruff 执行失败 exit={r.returncode}：{(r.stderr or '')[:400]}")
    return [ln for ln in (r.stdout or "").splitlines() if re.search(r"\b[A-Z]+\d{3,4}\b", ln)]


def metric_ruff(roots: list[str]) -> tuple[int, dict[str, int], list[str]]:
    """返回 (判据条数, 按规则码计数, 明细行)。

    判据条数 = 除 E501/N802 外的全部 + **代码行**超 88 列 + **散文行**超 120 列。
    """
    by_code: dict[str, int] = {}
    detail: list[str] = []
    gated = 0

    for line in _ruff_concise(roots, RUFF_SELECT):
        m = re.search(r"\b([A-Z]+\d{3,4})\b", line)
        if not m:
            continue
        code = m.group(1)
        if code in RUFF_EXCLUDE:
            continue  # 单独处理
        by_code[code] = by_code.get(code, 0) + 1
        gated += 1
        detail.append(line)

    # E501 两档
    src_cache: dict[str, tuple[list[str], set[int]]] = {}
    code_wide = prose_wide = 0
    prose_over_88 = 0
    for line in _ruff_concise(roots, "E501"):
        m = re.match(r"^(.+?):(\d+):\d+: E501", line)
        if not m:
            continue
        fp, ln = m.group(1), int(m.group(2))
        p = Path(fp) if Path(fp).is_absolute() else ROOT / fp
        if not p.exists():
            continue
        key = str(p)
        if key not in src_cache:
            try:
                src = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            src_cache[key] = (src.splitlines(), _prose_lines(src))
        lines, prose = src_cache[key]
        if ln - 1 >= len(lines):
            continue
        text = lines[ln - 1]
        width = _disp_width(text)
        if ln in prose:
            prose_over_88 += 1
            if width > PROSE_WIDTH:
                prose_wide += 1
                gated += 1
                detail.append(f"{fp}:{ln}: E501 散文行 {width} > {PROSE_WIDTH} 列")
        elif width > CODE_WIDTH:
            code_wide += 1
            gated += 1
            detail.append(f"{fp}:{ln}: E501 代码行 {width} > {CODE_WIDTH} 列")
    by_code["E501_代码行"] = code_wide
    by_code["E501_散文行_超120"] = prose_wide
    by_code["E501_散文行_88到120_已豁免"] = prose_over_88 - prose_wide

    # N802 只打印，不判
    by_code["N802_已豁免"] = len(_ruff_concise(roots, "N802"))

    return gated, dict(sorted(by_code.items(), key=lambda kv: -kv[1])), detail


# ── ② 重复代码（行块级，信息项）──────────────────────────────────────────
def metric_pyscn_clones(roots: list[str]) -> tuple[int | None, str]:
    ok, ver = _pyscn_available()
    if not ok:
        return None, f"pyscn 不可用（{ver or 'not installed'}）⇒ 信息项缺失，不算通过"
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "pyscn.json"
        r = _run([str(PY_BIN), "-m", "pyscn", "analyze", *roots,
                  "--json", "--output", str(out), "--skip-cbo"])
        if not out.exists():
            return None, f"pyscn 未产出报告（exit={r.returncode}）：{(r.stderr or '')[:300]}"
        data = json.loads(out.read_text(encoding="utf-8"))
    groups = data.get("clone", {}).get("clone_groups", [])
    return len(groups), f"pyscn {ver.splitlines()[0] if ver else ''}"


# ── ③ 模块 docstring 契约 ────────────────────────────────────────────────
def metric_module_docstrings(roots: list[str]) -> tuple[int, list[str]]:
    """缺模块 docstring 的 `.py` 文件数（`__init__.py` 与 conftest 不算）。

    权威出处：本仓 `AGENTS.md`「代码注释」+ 每个模块第一行必须说清它干什么。
    `__init__.py` 豁免：它通常只是包标记；`tests/conftest.py` 不豁免。
    """
    missing: list[str] = []
    for root in roots:
        base = ROOT / root
        if not base.exists():
            continue
        for p in base.rglob("*.py"):
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            if p.name == "__init__.py":
                continue
            try:
                mod = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError:
                missing.append(str(p.relative_to(ROOT)).replace("\\", "/") + "  [语法错]")
                continue
            if not ast.get_docstring(mod):
                missing.append(str(p.relative_to(ROOT)).replace("\\", "/"))
    return len(missing), sorted(missing)


# ── ④ 跨目录同名文件 ────────────────────────────────────────────────────
def metric_duplicate_filenames(roots: list[str]) -> tuple[int, dict[str, list[str]]]:
    """同名的 `.py` 出现在**两个以上不同目录** ⇒ 一个东西两处放。

    出处：`docs/naming-convention.md` §七「一个东西只归一处」。
    `__init__.py` 豁免（每个包都要有）。
    """
    by_name: dict[str, set[str]] = {}
    for root in roots:
        base = ROOT / root
        if not base.exists():
            continue
        for p in base.rglob("*.py"):
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            if p.name == "__init__.py":
                continue
            rel_dir = str(p.parent.relative_to(ROOT)).replace("\\", "/")
            by_name.setdefault(p.name, set()).add(rel_dir)
    dupes = {name: sorted(dirs) for name, dirs in by_name.items() if len(dirs) >= 2}
    return len(dupes), dict(sorted(dupes.items()))


# ── ⑤ 跨文件同函数体 ────────────────────────────────────────────────────
def metric_ast_dupes(roots: list[str]) -> tuple[int, list[str]]:
    """调 `scripts/uniformity-ast-dupes.py`（α-等价），返回 (组数, 警告)。"""
    script = DUPES_SCRIPT
    if not script.exists():
        raise RuntimeError(f"缺 {script} ⇒ FAIL，不跳过")
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "dupes.json"
        r = _run([str(PY_BIN), str(script), "--roots", *roots,
                  "--min-stmts", "4", "--json", str(out)])
        if r.returncode not in (0, 2):
            raise RuntimeError(f"同函数体扫描失败 exit={r.returncode}：{(r.stderr or '')[:400]}")
        if not out.exists():
            raise RuntimeError("同函数体扫描未产出报告")
        data = json.loads(out.read_text(encoding="utf-8"))
    warn = []
    if r.returncode == 2:
        warn.append("扫描里有文件语法错（见 uniformity-ast-dupes.py 的 stderr）")
    return int(data["groups"]), warn


# ── 汇总 ────────────────────────────────────────────────────────────────
def measure() -> dict:
    result: dict = {"roots": SCAN_ROOTS, "measure_only": MEASURE_ONLY_ROOTS}
    errors: list[str] = []

    try:
        total, by_code, detail = metric_ruff(SCAN_ROOTS)
        result["ruff_total"] = total
        result["ruff_by_code"] = by_code
        result["ruff_detail"] = detail
    except RuntimeError as exc:
        errors.append(str(exc))

    clones, clones_note = metric_pyscn_clones(SCAN_ROOTS)
    result["pyscn_clone_groups"] = clones
    result["pyscn_note"] = clones_note

    n_doc, doc_missing = metric_module_docstrings(SCAN_ROOTS)
    result["missing_module_docstrings"] = n_doc
    result["missing_module_docstrings_list"] = doc_missing

    n_dup, dup_detail = metric_duplicate_filenames(SCAN_ROOTS)
    result["duplicate_filenames"] = n_dup
    result["duplicate_filenames_detail"] = dup_detail

    try:
        n_ast, ast_warn = metric_ast_dupes(SCAN_ROOTS)
        result["ast_dupe_groups"] = n_ast
        if ast_warn:
            result["ast_dupe_warnings"] = ast_warn
    except RuntimeError as exc:
        errors.append(str(exc))

    # 只测量、不判红的另一条线
    try:
        mo_total, _, _ = metric_ruff(MEASURE_ONLY_ROOTS)
        result["measure_only_ruff_total"] = mo_total
    except RuntimeError:
        result["measure_only_ruff_total"] = None
    try:
        mo_ast, _ = metric_ast_dupes(MEASURE_ONLY_ROOTS)
        result["measure_only_ast_dupe_groups"] = mo_ast
    except RuntimeError:
        result["measure_only_ast_dupe_groups"] = None

    result["errors"] = errors
    return result


GATED = ["ruff_total", "missing_module_docstrings", "duplicate_filenames", "ast_dupe_groups"]
INFO_ONLY = ["pyscn_clone_groups", "measure_only_ruff_total", "measure_only_ast_dupe_groups"]


def load_baseline() -> dict:
    if not BASELINE.exists():
        raise SystemExit(f"缺基线文件 {BASELINE}。先跑 --write-baseline。")
    return json.loads(BASELINE.read_text(encoding="utf-8"))


def compare(actual: dict, baseline: dict) -> tuple[bool, list[str]]:
    """棘轮：读数 ≤ 天花板。零松弛检查单独报。"""
    bad: list[str] = []
    ceilings = baseline.get("ceilings", {})
    for key in GATED:
        if key not in actual or actual[key] is None:
            bad.append(f"{key}: 没测出来（工具缺失 ⇒ FAIL，不跳过）")
            continue
        ceil = ceilings.get(key)
        if ceil is None:
            bad.append(f"{key}: 基线里没有天花板")
            continue
        if actual[key] > ceil:
            bad.append(f"{key}: 实测 {actual[key]} > 天花板 {ceil}（回归）")
        elif actual[key] < ceil:
            bad.append(f"{key}: 实测 {actual[key]} < 天花板 {ceil}"
                       f"（**已改善但没下调基线** ⇒ 收口时必须写成实测值，零松弛）")
    return (len(bad) == 0), bad


def print_table(actual: dict, baseline: dict | None) -> None:
    ceilings = (baseline or {}).get("ceilings", {})
    print("指标                                实测      天花板   判据")
    print("-" * 68)
    labels = {
        "ruff_total": "① ruff E/F/I/N 条数",
        "pyscn_clone_groups": "② pyscn 行块克隆组数（信息项）",
        "missing_module_docstrings": "③ 缺模块 docstring 的文件数",
        "duplicate_filenames": "④ 跨目录同名 .py 数",
        "ast_dupe_groups": "⑤ 跨文件同函数体组数",
    }
    for key, label in labels.items():
        val = actual.get(key)
        ceil = ceilings.get(key)
        if key in INFO_ONLY:
            verdict = "信息项（不判红）"
        elif val is None:
            verdict = "FAIL 未测出"
        elif ceil is None:
            verdict = "—"
        elif val > ceil:
            verdict = f"FAIL 超 {val - ceil}"
        elif val < ceil:
            verdict = f"FAIL 未下调 {ceil - val}"
        else:
            verdict = "PASS 零松弛"
        print(f"{label:36} {str(val):>8} {str(ceil):>8}   {verdict}")
    for key in ("measure_only_ruff_total", "measure_only_ast_dupe_groups"):
        print(f"{key:36} {str(actual.get(key)):>8} {'—':>8}   只测量（另一条线）")


def _selftest() -> int:
    """验判据真的会拦：拿一份坏样本，确认 ③④⑤ 都能抓到。"""
    print("自测：判据必须能抓到它真正要抓的形态")
    fails = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "src"
        root.mkdir()
        # ③ 缺模块 docstring
        (root / "no_doc.py").write_text("X = 1\n", encoding="utf-8")
        # ④ 同名文件两个目录
        (root / "a").mkdir()
        (root / "b").mkdir()
        (root / "a" / "same.py").write_text('"""d"""\nY = 1\n', encoding="utf-8")
        (root / "b" / "same.py").write_text('"""d"""\nZ = 1\n', encoding="utf-8")
        # ⑤ 跨文件同函数体
        (root / "dup1.py").write_text(
            '"""d"""\ndef f(p):\n    v = p.strip()\n    if not v:\n        raise ValueError("e")\n    return v.upper()\n',
            encoding="utf-8")
        (root / "dup2.py").write_text(
            '"""d"""\ndef g(q):\n    w = q.strip()\n    if not w:\n        raise ValueError("e")\n    return w.upper()\n',
            encoding="utf-8")
        saved = globals()["ROOT"]
        try:
            globals()["ROOT"] = Path(td)
            n_doc, _ = metric_module_docstrings(["src"])
            n_dup, _ = metric_duplicate_filenames(["src"])
            n_ast, _ = metric_ast_dupes(["src"])
        finally:
            globals()["ROOT"] = saved
        if n_doc < 1:
            fails.append(f"③ 没抓到缺 docstring 的模块（实测 {n_doc}）")
        if n_dup < 1:
            fails.append(f"④ 没抓到跨目录同名（实测 {n_dup}）")
        if n_ast < 1:
            fails.append(f"⑤ 没抓到跨文件同函数体（实测 {n_ast}）")
    for f in fails:
        print("FAIL " + f)
    if not fails:
        print("PASS 自测：③④⑤ 三条判据都抓到了各自的负例")
    return 0 if not fails else 3


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true", help="只打印读数表")
    ap.add_argument("--write-baseline", action="store_true", help="把当前读数写成天花板")
    ap.add_argument("--repeat-check", action="store_true", help="连跑两次验幂等")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--json", default="", help="把读数写成 JSON")
    args = ap.parse_args()

    if args.selftest:
        return _selftest()

    actual = measure()
    if args.json:
        Path(args.json).write_text(json.dumps(actual, ensure_ascii=False, indent=2),
                                   encoding="utf-8")

    if args.repeat_check:
        again = measure()
        diffs = [k for k in GATED if actual.get(k) != again.get(k)]
        if diffs:
            print(f"FAIL 读数不幂等：{diffs}")
            for k in diffs:
                print(f"   {k}: {actual.get(k)} → {again.get(k)}")
            return 1
        print(f"PASS 幂等：两次读数一致（{ {k: actual.get(k) for k in GATED} }）")

    if args.write_baseline:
        ceilings = {k: actual[k] for k in GATED if actual.get(k) is not None}
        old = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {}
        history = old.get("_下调记录", [])
        for k, v in ceilings.items():
            prev = old.get("ceilings", {}).get(k)
            if prev is not None and v < prev:
                history.append({"at": __import__("datetime").date.today().isoformat(),
                                "key": k, "from": prev, "to": v,
                                "why": "本轮实测降低（见 docs/uniformity/report.md）"})
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(json.dumps({
            "ceilings": ceilings,
            "info_only": {k: actual.get(k) for k in INFO_ONLY},
            "ruff_by_code": actual.get("ruff_by_code"),
            "scope_note": "扫描面 = src/tests/scripts（本仓自己的代码）。"
                          "tools/gov-qa 是另一条线的活跃工作，只测量不判红。",
            "_下调记录": history,
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"天花板已写：{BASELINE}")
        print_table(actual, {"ceilings": ceilings})
        return 0

    baseline = load_baseline()
    print_table(actual, baseline)
    if actual.get("errors"):
        print("\n工具错误（每一项都是 FAIL，不是跳过）：")
        for e in actual["errors"]:
            print("  - " + e)
    ok, bad = compare(actual, baseline)
    print()
    if ok:
        print("PASS 全部指标 ≤ 天花板且零松弛")
        return 0
    print("FAIL")
    for b in bad:
        print("  - " + b)
    return 1


if __name__ == "__main__":
    sys.exit(main())
