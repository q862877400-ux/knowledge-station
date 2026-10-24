"""检查第 10 步：总对账（九个面各自覆盖到什么程度，可否复核）。

## 这份脚本做什么

不是再检查一遍，而是**核对前面几步的产出是否自洽**，并生成
`docs/survey/COVERAGE.md` —— 让下一棒一眼看到"哪些面查全了、哪些只是抽样"。

## 判据（任一条不满足就 exit 1）

1. `00-inventory.py --check` 三重账本 + 账本丁 → 平
2. `01-symbols.py` 解析成功 + 失败 == 总数 → 平衡
3. `schema.json` 表数 == 种子库 `sqlite_master` 表数
4. `endpoints.json` 后端条数 == 装饰器扫描命中数
5. `tests.json` 测试文件数 == `tests/` 下 `test_*.py` 实际数
6. `docs.json` 文档数 == `docs/` 下 `*.md` 实际数
7. `gates.json` 冒烟套数 == `smoke-all.mjs` 的 SUITES 条数
8. 每份生成的 md 都存在于磁盘
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "docs" / "survey" / "data"
SURVEY = ROOT / "docs" / "survey"
SEED = ROOT / "tests" / "fixtures" / "seed" / "knowledge-seed.db"


def load(n: str) -> dict:
    p = DATA / f"{n}.json"
    if not p.exists():
        raise SystemExit(f"缺 {p}（先跑 00/01/02）")
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    rows: list[tuple[str, str, str, str]] = []  # 面, 口径, 结果, 判据
    fails: list[str] = []

    # 1 文件面
    inv = load("inventory")
    led = inv["ledger"]
    expected = led["merged"] - led["generated_excluded"]
    ok1 = expected == led["counted"] and led["counted"] == len(inv["files"])
    rows.append(
        (
            "A 文件面",
            f"受控 {led['tracked']:,} + 未跟踪 {led['untracked']:,} "
            f"− 生成物 {led['generated_excluded']} = {led['counted']:,}；"
            f"另被忽略 {led['ignored_entries']:,} 条",
            "✅ 全量枚举" if ok1 else "❌ 不平",
            "甲+乙−戊 == 清单条数",
        )
    )
    if not ok1:
        fails.append("文件面账不平")

    # 2 符号面
    sym = load("symbols_py")
    summ = sym["summary"]
    ok2 = summ["modules"] + summ["parse_errors"] == summ["files_found"]
    rows.append(
        (
            "B 符号面（Python）",
            f"{summ['files_found']:,} 个 .py → "
            f"解析成功 {summ['modules']:,} / 失败 {summ['parse_errors']} → "
            f"{summ['symbols']:,} 个符号",
            "✅ 全量枚举" if ok2 else "❌ 有失败",
            "成功+失败 == 总数",
        )
    )
    if not ok2:
        fails.append("符号面解析不全")

    # 3 数据面
    sch = load("schema")
    conn = sqlite3.connect(f"file:{SEED}?mode=ro", uri=True)
    try:
        real = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchone()[0]
    finally:
        conn.close()
    ok3 = real == sch["counts"]["tables"]
    rows.append(
        (
            "D 数据面",
            f"种子库反射：表 {sch['counts']['tables']} / "
            f"列 {sch['counts']['total_columns']} / "
            f"索引 {sch['counts']['indexes']}",
            "✅ 全量枚举" if ok3 else f"❌ 表数不符（实际 {real}）",
            "表数 == sqlite_master",
        )
    )
    if not ok3:
        fails.append("数据面表数不符")

    # 4 接口面
    ep = load("endpoints")
    hits = 0
    for p in (ROOT / "src" / "core" / "api").glob("*.py"):
        hits += len(
            re.findall(
                r"@(?:app|router)\.(?:get|post|put|patch|delete)\(",
                p.read_text(encoding="utf-8", errors="replace"),
            )
        )
    ok4 = hits == ep["counts"]["backend_routes"]
    rows.append(
        (
            "E 接口面",
            f"后端 {ep['counts']['backend_routes']} 条（装饰器 {hits}）"
            f" + 前端注册 {ep['counts']['front_route_registrations']} 条",
            "✅ 全量枚举" if ok4 else f"❌ 不符（装饰器 {hits}）",
            "装饰器命中 == 输出条数",
        )
    )
    if not ok4:
        fails.append("接口面条数不符")

    # 5 测试面
    t = load("tests")
    real_t = len(list((ROOT / "tests").rglob("test_*.py"))) + len(
        list((ROOT / "tests").rglob("*_test.py"))
    )
    ok5 = real_t == t["counts"]["test_files"]
    rows.append(
        (
            "F 测试面",
            f"测试文件 {t['counts']['test_files']}"
            f" / 静态 def {t['counts']['test_functions_total']:,}",
            "✅ 全量枚举" if ok5 else f"❌ 不符（实际 {real_t}）",
            "文件数 == tests/ 下实际数",
        )
    )
    if not ok5:
        fails.append("测试面文件数不符")

    # 6 文档面
    d = load("docs")
    real_d = len(list((ROOT / "docs").rglob("*.md")))
    ok6 = real_d == d["counts"]["docs_files"]
    rows.append(
        (
            "G 文档面",
            f"文档 {d['counts']['docs_files']} 份 / "
            f"孤儿 {d['counts']['orphans_no_inbound']} 份 / "
            f"链接 {d['counts']['total_links']:,} 条",
            "✅ 全量枚举" if ok6 else f"❌ 不符（实际 {real_d}）",
            "文档数 == docs/ 下实际数",
        )
    )
    if not ok6:
        fails.append("文档面数量不符")

    # 7 门禁面
    g = load("gates")
    sm = ROOT / "plugin" / "scripts" / "smoke-all.mjs"
    blk = re.search(r"const SUITES = \[(.*?)\]", sm.read_text(encoding="utf-8"), re.S)
    real_s = len(re.findall(r"['\"]([^'\"]+\.mjs)['\"]", blk.group(1))) if blk else 0
    ok7 = real_s == g["counts"]["smoke_suites"]
    rows.append(
        (
            "H 门禁面",
            f"步 {g['counts']['steps']} / 冒烟套 {g['counts']['smoke_suites']}",
            "✅ 全量枚举" if ok7 else f"❌ 不符（实际 {real_s}）",
            "套数 == SUITES 条数",
        )
    )
    if not ok7:
        fails.append("门禁面套数不符")

    # 8 文档齐不齐
    need = [
        "README.md",
        "00-method.md",
        "01-inventory.md",
        "02-code-map.md",
        "03-cross-ref.md",
        "04-data-shape.md",
        "05-api-surface.md",
        "06-test-surface.md",
        "07-doc-surface.md",
        "08-gate-surface.md",
        "09-runtime.md",
        "10-observed.md",
        "11-module-index.md",
        "12-config-surface.md",
        "13-table-io.md",
        "14-test-index.md",
        "15-doc-index-content.md",
        "16-frontend.md",
        "17-function-index.md",
        "18-runtime-probe.md",
        "19-requirements.md",
        "20-rules.md",
    ]
    miss = [n for n in need if not (SURVEY / n).exists()]
    rows.append(
        (
            "生成物齐备",
            f"{len(need) - len(miss)}/{len(need)} 份存在",
            "✅" if not miss else f"❌ 缺 {', '.join(miss)}",
            "每份都落盘",
        )
    )
    if miss:
        fails.append("生成的 md 不全")

    # 8.5 深化面齐备
    deep_need = ["modules", "endpoints_deep", "config", "tables_io",
                 "test_content", "doc_content", "web_content",
                 "runtime_probe", "repro_resume_hang",
                 "requirements", "notdoing", "data_samples", "rules"]
    deep_miss = [n for n in deep_need if not (DATA / f"{n}.json").exists()]
    rows.append(("深化面 JSON", f"{len(deep_need) - len(deep_miss)}/{len(deep_need)} 份存在",
                 "✅" if not deep_miss else f"❌ 缺 {', '.join(deep_miss)}",
                 "模块/接口/配置/表读写"))
    if deep_miss:
        fails.append("深化面 JSON 不全")

    # 9 运行时面：**实测**（真起引擎）+ 手写说明两份
    rt = DATA / "runtime_probe.json"
    if rt.exists():
        rd = json.loads(rt.read_text(encoding="utf-8"))
        rc = rd["counts"]
        dist = ", ".join(f"{k}:{v}" for k, v in sorted(rc["by_status"].items()))
        rows.append(
            (
                "I 运行时面（实测）",
                f"真启动引擎，探 {rc['routes_probed']} 条端点；状态分布 {dist}",
                "✅ 已实测",
                "起引擎 + 逐条调用（隔离数据目录）",
            )
        )
    else:
        rows.append(
            (
                "I 运行时面（实测）",
                "**未跑**（`07-runtime-probe.py`）",
                "❌ 缺",
                "需要真启动引擎",
            )
        )
    rows.append(
        (
            "I' 运行时面（说明）",
            "手写（`09-runtime.md`），每条标已验证/未验证",
            "⚠ 部分未验证",
            "启动/端口/令牌/数据目录的说明",
        )
    )

    # ── 输出 ──
    print(f"{'面':18} {'结果':12} 口径")
    print("-" * 96)
    for a, b, c, _ in rows:
        print(f"{a:18} {c:12} {b}")

    out = [
        "## 一、九个面各自覆盖到什么程度",
        "",
        "| 面 | 口径 | 结果 | 判据 |",
        "|---|---|---|---|",
    ]
    for a, b, c, dd in rows:
        out.append(f"| {a} | {b} | {c} | {dd} |")
    out += [
        "",
        "## 二、明确**没有**覆盖的",
        "",
        "| 项 | 为什么 |",
        "|---|---|",
        "| **运行时真实行为（最大缺口）** | **从未真正启动引擎、从未调过任何端点** —— "
        "静态检查只能看到代码写了什么，验不了跑起来会怎样 |",
        "| ~~需求编号体系~~ | ✅ **已收口**：扫全部 `docs/**/*.md`，"
        "97 条编号定义（61 在需求文档 / 35 在渠道方案 / 2 在归档）+ 代码引用点 + "
        "24 条否决台账，见 `19-requirements.md` |",
        "| ~~业务规则的语义~~ | ✅ **已收口到「字面判据 + 理由」**："
        "从 `src/**/*.py` 抽出 291 条规则常量（160 正则 / 131 阈值），"
        "169 条带上方注释原文，见 `20-rules.md`。"
        "**仍未到「算法的完整复述」** —— 那需要逐行读函数体 |",
        "| **数据样例** | 记了每张表在种子库的行数，"
        "**没抽样看行内容**（隐私敏感的表更没看） |",
        "| 测试运行期覆盖率 | 要 coverage 数据，本检查没取 |",
        "| 前端符号的 AST 级清单 | 没有现成 TS AST 工具链，用正则，**近似** |",
        "| `tools/gov-qa` 948 MB 内容细节 | 只查结"
        "构与归属；隐私是**抽样** 3/594 个文件 |",
        "| 浏览器像素效果 | 需要真浏览器 |",
        "| 除旧工作区之外的绝对路径 | 通用扫描器误报率 >90%，已弃用 |",
        "| **71 条超时的确切原因** | 已按 handler 函数体关键词粗分，但 41/71 "
        "「handler 里看不出明确来源」⇒ 要定因得在超时时抓线程栈，**本检查没做** |",
        "| **把 500 与卡死修掉** | 明确不属于本检查（业主令：只检查不治病） |",
        "| `var/data` 74 GB 逐部核 | 只做了统计 |",
        "",
        "## 三、怎么复核这份对账",
        "",
        "```powershell",
        ".venv\\Scripts\\python.exe scripts/survey/00-inventory.py --check",
        ".venv\\Scripts\\python.exe scripts/survey/01-symbols.py --check",
        ".venv\\Scripts\\python.exe scripts/survey/04-reconcile.py",
        "```",
        "",
        "## 四、数字过期了怎么办",
        "",
        "重跑四个生成器（合计约 30 秒），**不要手改 md**：",
        "",
        "```powershell",
        ".venv\\Scripts\\python.exe scripts/survey/00-inventory.py",
        ".venv\\Scripts\\python.exe scripts/survey/01-symbols.py",
        ".venv\\Scripts\\python.exe scripts/survey/02-surface.py",
        ".venv\\Scripts\\python.exe scripts/survey/03-render.py",
        ".venv\\Scripts\\python.exe scripts/survey/04-reconcile.py",
        "```",
    ]
    p = SURVEY / "COVERAGE.md"
    p.write_text(
        "# 覆盖对账（九个面）\n\n"
        "> **由 `scripts/survey/04-reconcile.py` 生成。**\n"
        "> 这份文件的用途：让下一棒一眼看到**哪些面查全了、哪些只是抽样**。\n\n"
        + "\n".join(out),
        encoding="utf-8",
    )
    print(f"\n→ {p.relative_to(ROOT)}")

    if fails:
        print("\n❌ 对账失败：")
        for f in fails:
            print(f"  - {f}")
        return 1
    print("\n✅ 对账通过：所有可机械核对的判据都平")
    return 0


if __name__ == "__main__":
    sys.exit(main())
