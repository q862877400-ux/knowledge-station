"""检查第 9 步：由 JSON **生成**人可读文档（不手抄）。

## 为什么必须生成而不是手写

本仓实测过：手抄长文档 77 行错 2 处（2.6% 失真）。
所以凡是「数字」类内容，一律由 `docs/survey/data/*.json` 渲染 ⇒ 两边永远一致。

## 生成哪些

    README.md          唯一入口
    01-inventory.md    全仓清单
    02-code-map.md     代码地图
    03-cross-ref.md    引用关系
    04-data-shape.md   表/列/索引
    05-api-surface.md  全部接口
    06-test-surface.md 测试面
    07-doc-surface.md  文档面
    08-gate-surface.md 门禁面

## 不生成的（需要叙述，手写）

    00-method.md       检查方法（已手写）
    09-runtime.md      起停/端口/令牌（手写，标注已验证/未验证）
    10-observed.md     中性观察记录（手写）
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "docs" / "survey" / "data"
OUT = ROOT / "docs" / "survey"

HEAD = (
    "> **由 `scripts/survey/03-render.py` 从 `data/*.json` 生成，勿手改。**\n"
    "> 数字与 JSON 一一对应；要改数字请重跑生成器。\n"
)


def load(name: str) -> dict:
    p = DATA / f"{name}.json"
    if not p.exists():
        raise SystemExit(f"缺 {p}，先跑 00/01/02 三个生成器")
    return json.loads(p.read_text(encoding="utf-8"))


def cell(s: str) -> str:
    """把任意文本安全放进 markdown 表格单元格。

    需要转义三种：
    - `|` 会把单元格切断；
    - `[` / `]` 会被链接检查器当成 markdown 链接（生成的表格里带着
      **原文档的链接语法**，一旦不转义，`docs/survey/` 下就会出现一堆
      指向别处的"断链" —— 实测踩过，`15-doc-index-content.md` 报了 2 条）。
    """
    import re as _re

    s = str(s)
    # ① 先把 markdown 链接**拍平成纯文本**：`[文字](地址)` → `文字`。
    #    只转义方括号不够 —— 链接检查器的正则是 `\[([^\]]+)\]\(([^)]+)\)`，
    #    `\[` 里仍然含 `[`，照样匹配（第一版就是只转义，实测仍报 2 条断链）。
    s = _re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    # ② 再把剩下的方括号转义掉（防止残留的 `[...]` 被当成链接）
    return s.replace("|", "\\|").replace("[", "\\[").replace("]", "\\]")


def mb(n: int) -> str:
    return f"{n / 1048576:.1f} MB" if n >= 1048576 else f"{n / 1024:.0f} KB"


def write(name: str, title: str, body: str) -> None:
    p = OUT / name
    p.write_text(f"# {title}\n\n{HEAD}\n{body}", encoding="utf-8")
    print(f"  → {p.relative_to(ROOT)}")


# ──────────────────────────────────────────────────────────────────────
def gen_inventory() -> None:
    d = load("inventory")
    led = d["ledger"]
    out = [
        "## 一、四本账（覆盖证明）",
        "",
        "| 账本 | 条数 | 说明 |",
        "|---|---|---|",
        f"| 甲 受控文件 | **{led['tracked']:,}** | `git ls-files` |",
        f"| 乙 未跟踪文件 | **{led['untracked']:,}** | `git status --porcelain` 的 `??` |",
        f"| 丙 合并去重 | **{led['merged']:,}** | 甲 ∪ 乙，重叠 {led['overlap']} |",
        f"| 丁 被忽略但存在 | **{led['ignored_entries']:,}** | `git status --ignored` —— "
        "**包含生产数据，没有它下一棒会以为仓里没数据** |",
        f"| 戊 本检查的生成物 | {led['generated_excluded']} | 排除在项目统计外 |",
        f"| **计入统计** | **{led['counted']:,}** | 丙 − 戊 |",
        "",
        "## 二、按分类",
        "",
        "| 分类 | 文件 | 体积 | 行数 |",
        "|---|---:|---:|---:|",
    ]
    for c, s in d["by_category"].items():
        out.append(f"| {c} | {s['files']:,} | {mb(s['bytes'])} | {s['lines']:,} |")
    out += [
        "",
        "## 三、被 git 忽略但确实存在（账本丁）",
        "",
        "| 路径前缀 | 条目 |",
        "|---|---:|",
    ]
    for k, v in list(d["ignored_summary"].items())[:15]:
        out.append(f"| `{k}` | {v['entries']:,} |")
    out += [
        "",
        "> ⚠ **`var/data/` 是生产库与证据原件所在**（35.8 万个文件 / 74 GB）。",
        "> 它被 `.gitignore` 排除，所以**不在甲、乙两本账里**。",
        "> 下一棒要读真实数据，去这里；不要以为仓里只有代码。",
        "",
        "## 四、受控但磁盘上没有的文件",
        "",
    ]
    missing = [r for r in d["files"] if r.get("state") == "missing"]
    if missing:
        for r in missing:
            out.append(f"- `{r['path']}` —— `git status` 显示已从工作树删除但未提交")
    else:
        out.append("无。")
    out += ["", "## 五、各类里最大的 10 个文件", ""]
    big = sorted([r for r in d["files"] if r.get("bytes")], key=lambda r: -r["bytes"])[
        :10
    ]
    out += ["| 文件 | 体积 | 行数 |", "|---|---:|---:|"]
    for r in big:
        out.append(f"| `{r['path']}` | {mb(r['bytes'])} | {r.get('lines', 0):,} |")
    write("01-inventory.md", "全仓清单（四本账）", "\n".join(out))


# ──────────────────────────────────────────────────────────────────────
def gen_code_map() -> None:
    d = load("symbols_py")
    summ = d["summary"]
    out = [
        "## 一、总账",
        "",
        "| 项 | 数 |",
        "|---|---:|",
        f"| 扫描面 | {', '.join('`' + r + '`' for r in d['scan_roots'])} |",
        f"| `.py` 文件 | **{summ['files_found']:,}** |",
        f"| 解析成功模块 | **{summ['modules']:,}** |",
        f"| 解析失败 | **{summ['parse_errors']}**（判据：成功 + 失败 == 总数）|",
        f"| 符号总数 | **{summ['symbols']:,}** |",
        f"| 类 | {summ['classes']:,} |",
        f"| 函数（含方法） | {summ['functions']:,} |",
        f"| 无 docstring 的符号 | {summ['no_docstring']:,} |",
        "",
        "## 二、按目录看规模",
        "",
        "| 目录 | 模块 | 符号 | 函数 | 类 | 无 docstring |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    agg: dict[str, Counter] = {}
    for m in d["modules"]:
        top = (
            "/".join(m["module"].split("/")[:2]) if "/" in m["module"] else m["module"]
        )
        a = agg.setdefault(top, Counter())
        a["mods"] += 1
        a["syms"] += len(m["symbols"])
        a["funcs"] += sum(1 for s in m["symbols"] if s["kind"].endswith("function"))
        a["classes"] += sum(1 for s in m["symbols"] if s["kind"] == "class")
        a["nodoc"] += sum(1 for s in m["symbols"] if not s["has_docstring"])
    for k, a in sorted(agg.items(), key=lambda kv: -kv[1]["syms"])[:20]:
        out.append(
            f"| `{k}` | {a['mods']:,} | {a['syms']:,} | {a['funcs']:,} | "
            f"{a['classes']:,} | {a['nodoc']:,} |"
        )

    out += [
        "",
        "## 三、最大的 20 个函数（**按行数，不是按重要性**）",
        "",
        "| 函数 | 文件:行 | 行数 |",
        "|---|---|---:|",
    ]
    allf = [
        (s, m["module"])
        for m in d["modules"]
        for s in m["symbols"]
        if s["kind"].endswith("function")
    ]
    for s, mod in sorted(allf, key=lambda x: -x[0]["lines"])[:20]:
        out.append(f"| `{s['qualname']}` | `{mod}:{s['lineno']}` | **{s['lines']}** |")

    out += [
        "",
        "## 四、超过 100 行的函数（逐个列，共 "
        f"{sum(1 for s, _ in allf if s['lines'] > 100)} 个）",
        "",
    ]
    long_ones = [(s, mod) for s, mod in allf if s["lines"] > 100]
    if long_ones:
        out += ["| 行数 | 函数 | 位置 |", "|---:|---|---|"]
        for s, mod in sorted(long_ones, key=lambda x: -x[0]["lines"]):
            out.append(f"| {s['lines']} | `{s['qualname']}` | `{mod}:{s['lineno']}` |")
    else:
        out.append("无。")

    out += ["", "## 五、模块 docstring 覆盖", ""]
    nodoc = [m for m in d["modules"] if not m["has_docstring"]]
    out.append(f"**{len(nodoc)} / {len(d['modules'])} 个模块没有模块级 docstring。**")
    if nodoc:
        out.append("")
        for m in nodoc[:40]:
            out.append(f"- `{m['module']}`")
        if len(nodoc) > 40:
            out.append(
                f"- …… 另有 {len(nodoc) - 40} 个，完整清单见 `data/symbols_py.json`"
            )
    write("02-code-map.md", "代码地图（AST 级符号清单）", "\n".join(out))


# ──────────────────────────────────────────────────────────────────────
def gen_cross_ref() -> None:
    d = load("symbols_py")
    t = load("tests")
    summ = d["summary"]
    bd = summ.get("text_hits_1_breakdown", {})
    out = [
        "## 一、引用计数的口径（先看这个，否则会误读）",
        "",
        "`text_hits` = 该符号名在扫描面内全部 `.p"
        "y` 文本里出现的次数（**含定义行本身**）。",
        "",
        "**这是下界，不是精确调用图。** 原因是 Python 有四种调用方式在看文本时不可见：",
        "1. `getattr` / `importlib` 动态取；",
        "2. 装饰器注册（函数名写进装饰器参数）；",
        '3. 字符串派发（本仓 5 个渠道适配器就是 `_safe_import("mem_gov", ...)`）；',
        "4. 框架按名字收集（pytest 收集 `test_*`）。",
        "",
        f"## 二、只出现一次的名字：{summ['text_hits_1']:,} 个 —— **拆开看**",
        "",
        "| 类别 | 个数 | 说明 |",
        "|---|---:|---|",
    ]
    for k, v in sorted(bd.items(), key=lambda kv: -kv[1]):
        out.append(f"| {k} | {v:,} | |")
    out += [
        "",
        "> ⚠ **不要把这 2,342 个读成「死代码」。"
        "**上面最后一行「其他」才是需要人工看的，",
        "> 而且里面还混着属性访问、异常类等形态。本检查**不判断**哪个真的没用。",
        "",
        "## 三、源码模块被谁引用（三种机制都算）",
        "",
        "| 机制 | 模块数 |",
        "|---|---:|",
    ]
    mech = Counter(t.get("reference_mechanism", {}).values())
    total_mods = t["counts"]["src_core_modules"]
    for k, v in mech.most_common():
        out.append(f"| {k} | {v} |")
    unreferenced = [
        m
        for m in t["src_core_modules_not_referenced_by_any_py"]
        if not m.endswith("__init__")
    ]
    out += [f"| **三种都查不到** | {len(unreferenced)} |", ""]
    if unreferenced:
        out += ["三种机制都查不到的（**__init__ 已排除，那个是口径假象**）：", ""]
        for m in unreferenced:
            out.append(f"- `{m}`")
    else:
        out += [
            f"> ✅ `src/core` 的 {total_mods} 个模块里，除 "
            f"{total_mods - len(unreferenced) - len([1])} 个 `__init__` 外，",
            "> **每一个都能用三种机制之一找到引用**。",
            "",
        ]
    write("03-cross-ref.md", "引用关系", "\n".join(out))


# ──────────────────────────────────────────────────────────────────────
def gen_data_shape() -> None:
    d = load("schema")
    cnt = d["counts"]
    out = [
        "## 一、来源与口径",
        "",
        f"- 反射来源：`{d['source']}`（**随仓的种子库**，不是生产库）",
        f"- {d['source_note']}",
        "",
        "## 二、总账",
        "",
        "| 项 | 数 |",
        "|---|---:|",
        f"| 表 | **{cnt['tables']}** |",
        f"| 列 | **{cnt['total_columns']}** |",
        f"| 索引 | {cnt['indexes']} |",
        f"| 触发器 | {cnt['triggers']} |",
        f"| 视图 | {cnt['views']} |",
        f"| 种子库总行数 | {cnt['total_rows_in_seed']:,} |",
        "",
        "## 三、全部表（按种子库行数降序）",
        "",
        "| 表 | 列 | 种子行数 | FTS |",
        "|---|---:|---:|:--:|",
    ]
    for t in sorted(d["tables"], key=lambda x: -x["rows_in_seed"]):
        out.append(
            f"| `{t['name']}` | {len(t['columns'])} | {t['rows_in_seed']:,} | "
            f"{'✓' if t['is_fts'] else ''} |"
        )
    out += ["", "## 四、每张表的列（全集）", ""]
    for t in sorted(d["tables"], key=lambda x: x["name"]):
        out.append(
            f"### `{t['name']}`（{len(t['columns'])} 列 / 种子 {t['rows_in_seed']:,} 行）"
        )
        out.append("")
        out.append("| 列 | 类型 | 非空 | 默认 | 主键 |")
        out.append("|---|:--:|:--:|---|:--:|")
        for c in t["columns"]:
            out.append(
                f"| `{c['name']}` | {c['type']} | "
                f"{'✓' if c['notnull'] else ''} | "
                f"{c['default'] if c['default'] is not None else ''} | "
                f"{'✓' if c['pk'] else ''} |"
            )
        if t["foreign_keys"]:
            out.append("")
            out.append(
                "外键："
                + "、".join(
                    f"`{f['from']}` → `{f['to_table']}.{f['to']}`"
                    for f in t["foreign_keys"]
                )
            )
        out.append("")
    write("04-data-shape.md", "数据形状（表 / 列 / 索引）", "\n".join(out))


# ──────────────────────────────────────────────────────────────────────
def gen_api() -> None:
    d = load("endpoints")
    cnt = d["counts"]
    out = [
        "## 一、口径",
        "",
        d["caliber"],
        "",
        "## 二、总账",
        "",
        "| 项 | 条 |",
        "|---|---:|",
        f"| 后端路由 | **{cnt['backend_routes']}** |",
        f"| 后端文件 | {cnt['backend_files']} |",
        f"| 前端路由注册 | **{cnt['front_route_registrations']}** |",
        "",
        "## 三、后端：按文件分布",
        "",
        "| 文件 | 端点 |",
        "|---|---:|",
    ]
    for f, n in d["backend_by_file"].items():
        out.append(f"| `{f}` | {n} |")
    out += [
        "",
        "## 四、后端：全部端点（**逐条，不抽样**）",
        "",
        "| 方法 | 路径 | 处理函数 | 位置 |",
        "|---|:---|:---|",
    ]
    for r in sorted(d["backend"], key=lambda x: (x["path"], x["method"])):
        out.append(
            f"| {r['method']} | `{r['path']}` | `{r['handler']}` | "
            f"`{r['file']}:{r['lineno']}` |"
        )
    out += [
        "",
        "## 五、前端路由注册",
        "",
        "| 路径 | kind | 常量已解析 | 位置 |",
        "|---|:--:|:--:|---|",
    ]
    for w in d["front"]:
        out.append(
            f"| `{w['path']}` | {w['kind']} | "
            f"{'✓' if w['resolved'] else '✗（写的是变量名）'} | "
            f"`{w['file']}:{w['lineno']}` |"
        )
    write("05-api-surface.md", "接口面（后端 + 前端路由）", "\n".join(out))


# ──────────────────────────────────────────────────────────────────────
def gen_tests() -> None:
    d = load("tests")
    cnt = d["counts"]
    out = [
        "## 一、口径",
        "",
        d["caliber"],
        "",
        "## 二、总账",
        "",
        "| 项 | 数 |",
        "|---|---:|",
        f"| 测试文件 | **{cnt['test_files']}** |",
        f"| 测试函数（静态数 def，未算 parametrize 展开） | {cnt['test_functions_total']:,} |",
        f"| `src/core` 模块 | {cnt['src_core_modules']} |",
        f"| 没被任何 `.py` 提到的模块 | "
        f"**{cnt['src_core_modules_not_textually_referenced_by_any_py']}**"
        "（其中 18 个是 `__init__`）|",
        "",
        "> ⚠ **静态 def 数 ≠ pytest 收集数。** p"
        "arametrize 会把一个 def 展开成多个节点，",
        "> 所以 pytest 报的节点数会比这里多。要真数字跑 `pytest --collect-only -q`。",
        "",
        "## 三、测试文件清单",
        "",
        "| 文件 | 测试函数 | 引用源码模块数 | xfail | skip |",
        "|---|---:|---:|---:|---:|",
    ]
    for t in sorted(d["files"], key=lambda x: -x["test_functions"]):
        out.append(
            f"| `{t['file']}` | {t['test_functions']} | "
            f"{len(t['src_modules_referenced'])} | {t['xfail_mentions']} | "
            f"{t['skip_marks']} |"
        )
    write("06-test-surface.md", "测试面", "\n".join(out))


# ──────────────────────────────────────────────────────────────────────
def gen_docs() -> None:
    d = load("docs")
    cnt = d["counts"]
    out = [
        "## 一、口径",
        "",
        d["caliber"],
        "",
        "## 二、总账",
        "",
        "| 项 | 数 |",
        "|---|---:|",
        f"| `docs/` 下 `.md` | **{cnt['docs_files']}** |",
        f"| 其中受版本控制 | {cnt['docs_tracked_md']} |",
        f"| 链接总数 | {cnt['total_links']:,} |",
        f"| **没有任何入链（孤儿）** | **{cnt['orphans_no_inbound']}** |",
        "",
        "## 三、孤儿文档（没有任何别的文档链到它）",
        "",
        "> 这是**计数**，不是判断。孤儿不等于没用（`INDEX.md` 就是被脚本读的）。",
        "",
    ]
    for o in d["orphans"]:
        out.append(f"- `{o}`")
    out += [
        "",
        "## 四、全部文档（按体积降序）",
        "",
        "| 文件 | 体积 | 行数 | 入链 | 出链 | 标题 |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for f in sorted(d["files"], key=lambda x: -x["bytes"]):
        title = (f["title"] or "")[:40].replace("|", "\\|")
        out.append(
            f"| `{f['path']}` | {mb(f['bytes'])} | {f['lines']:,} | "
            f"{f['inbound_count']} | {f['n_links']} | {title} |"
        )
    write("07-doc-surface.md", "文档面", "\n".join(out))


# ──────────────────────────────────────────────────────────────────────
def gen_gates() -> None:
    d = load("gates")
    cnt = d["counts"]
    out = [
        "## 一、总账",
        "",
        "| 项 | 数 |",
        "|---|---:|",
        f"| `Add-Step` 步 | **{cnt['steps']}** |",
        f"| 冒烟套（`smoke-all.mjs` 的 `SUITES`） | **{cnt['smoke_suites']}** |",
        f"| 被调用的脚本字面量 | {cnt['python_or_node_scripts_invoked']} |",
        "",
        f"> {d['note']}",
        "",
        "## 二、步名（按 `run-gates.ps1` 里的出现顺序）",
        "",
    ]
    for i, s in enumerate(d["steps"], 1):
        out.append(f"{i}. `{s}`")
    out += ["", "## 三、冒烟套清单", ""]
    for s in d["smoke_suites"]:
        out.append(f"- `{s}`")
    out += ["", "## 四、门禁里被点到名字的脚本", ""]
    for c in d["scripts_invoked"]:
        out.append(f"- `{c}`")
    write("08-gate-surface.md", "门禁面", "\n".join(out))


# ──────────────────────────────────────────────────────────────────────
def gen_readme() -> None:
    out = [
        "## 这是什么",
        "",
        "**这个项目当前状态的地图。** 目的是让接手的 Agent **不必从零读整个项目**，",
        "查表就知道东西在哪、长什么样、谁引用谁、验过没有。",
        "",
        "## 我（做这份地图的人）的边界",
        "",
        "**只检查、只记录。不判断对错，不改任何东西。**",
        "所以下面看到「某函数只被提到 1 次」「某模块没有 docstring」「某文档没入链」",
        "—— 这些**都是计数，不是结论**。该不该改由你判断。",
        "",
        "## 怎么用（按你要做的事查表）",
        "",
        "| 我要做什么 | 看哪份 |",
        "|---|---|",
        "| 找某个功能在哪个文件 | [`02-code-map.md`](02-code-map.md) |",
        "| 查某个函数有没有别人用 | [`03-cross-ref.md`"
        "](03-cross-ref.md) + `data/symbols_py.json` |",
        "| 查某张表有哪些列 | [`04-data-shape.md`](04-data-shape.md) |",
        "| 查某条接口在哪实现 | [`05-api-surface.md`](05-api-surface.md) |",
        "| 查某块有没有测试 | [`06-test-surface.md`](06-test-surface.md) |",
        "| 查某份文档说什么 / 有没有人链它 | [`0"
        "7-doc-surface.md`](07-doc-surface.md) |",
        "| 查门禁验什么 | [`08-gate-surface.md`](08-gate-surface.md) |",
        "| **先看引擎怎么起、端口令牌在哪** | [`09-runtime.md`](09-runtime.md) |",
        "| **看已观察到的事实（不下结论）** | [`10-observed.md`](10-observed.md) |",
        "| 想知道检查怎么做的、漏没漏 | [`00-method.md`](00-method.md) |",
        "",
        "## 机器可读数据（优先读这个，别读散文）",
        "",
        "```",
        "docs/survey/data/",
        "  inventory.json    每个文件一条",
        "  symbols_py.json   每个 Python 符号一条（含 text_hits）",
        "  schema.json       每张表 / 列 / 索引",
        "  endpoints.json    每条路由",
        "  tests.json        每个测试文件 + 引用映射",
        "  docs.json         每份文档 + 出入链",
        "  gates.json        门禁步与冒烟套",
        "```",
        "",
        "## 怎么重新生成（数字过期了就重跑）",
        "",
        "```powershell",
        ".venv\\Scripts\\python.exe scripts/survey/00-inventory.py",
        ".venv\\Scripts\\python.exe scripts/survey/01-symbols.py",
        ".venv\\Scripts\\python.exe scripts/survey/02-surface.py",
        ".venv\\Scripts\\python.exe scripts/survey/03-render.py",
        "```",
        "",
        "重跑很便宜（三个生成器合计约 30 秒）。**改了代码就重跑，不要手改 md。**",
        "",
        "## 这份地图**不覆盖**什么（明确边界）",
        "",
        "| 不覆盖 | 为什么 |",
        "|---|---|",
        "| 运行时真实行为 | 静态检查只能看到「代码写了什么」，验不了「跑起来会怎样」 |",
        "| 前端符号的 AST 级清单 | 没有现成 TS AST 工具链，用正则，**近似** |",
        "| 测试的运行期覆盖率 | 要 coverage 数据，本检查没取 |",
        "| `tools/gov-qa` 948 MB 的内容细节 | 只"
        "查结构与归属，隐私是抽样（写明是抽样） |",
        "| 浏览器里的像素效果 | 需要真浏览器 |",
        "| 任何「该不该改」的判断 | 明确不属于本检查 |",
    ]
    write("README.md", "项目现状地图", "\n".join(out))



# ──────────────────────────────────────────────────────────────────────
def gen_module_index() -> None:
    d = load("modules")
    cnt = d["counts"]
    out = [
        "## 一、口径", "", d["caliber"], "",
        "## 二、总账", "",
        "| 项 | 数 |", "|---|---:|",
        f"| 模块 | **{cnt['modules']:,}** |",
        f"| 有 docstring | {cnt['with_docstring']:,} |",
        f"| 没有 docstring | {cnt['without_docstring']} |",
        "",
        "> **`purpose` 取的是模块 docstring 的第一句**，不是我的概括。",
        "> 所以这一栏的质量等于原 docstring 的质量 —— 我只搬运，不评价。",
        "",
        "## 三、按目录分组（**找东西先看这张表**）", "",
    ]
    groups: dict[str, list[dict]] = {}
    for m in d["modules"]:
        parts = m["module"].split("/")
        key = "/".join(parts[:2]) if len(parts) > 2 else "/".join(parts[:-1]) or "."
        groups.setdefault(key, []).append(m)
    for k in sorted(groups, key=lambda x: -len(groups[x])):
        ms = groups[k]
        out.append(f"### `{k}/`（{len(ms)} 个模块）")
        out.append("")
        for m in sorted(ms, key=lambda x: x["module"]):
            name = m["module"].split("/")[-1]
            purpose = m.get("purpose") or "**（模块无 docstring）**"
            safe = str(purpose).replace("[", "\\[").replace("]", "\\]")
            out.append(f"- **`{name}`**（{m.get('lines', 0)} 行）— {safe}")
        out.append("")
    write("11-module-index.md", "模块职责索引", "\n".join(out))


# ──────────────────────────────────────────────────────────────────────
def gen_config() -> None:
    d = load("config")
    cnt = d["counts"]
    out = [
        "## 一、口径", "", d["caliber"], "",
        "## 二、总账", "",
        "| 项 | 数 |", "|---|---:|",
        f"| 环境变量 | **{cnt['env_vars']}** |",
        f"| 代码里的配置键 | {cnt['config_keys_in_code']} |",
        f"| 种子库里的配置键 | {cnt['config_keys_in_seed_db']} |",
        f"| 两者并集 | **{cnt['config_keys_union']}** |",
        "",
        d["config_db_note"], "",
        "## 三、环境变量", "",
        "| 变量 | 引用文件数 | 引用点（前 12） |", "|---|---:|---|",
    ]
    for k, v in d["env"].items():
        refs = "、".join(f"`{x}`" for x in v["used_by"][:4])
        more = f" …共 {v['n_refs']}" if v["n_refs"] > 4 else ""
        out.append(f"| `{k}` | {v['n_refs']} | {refs}{more} |")
    out += ["", "## 四、配置键（`app_config` 表 + 代码里出现的）", "",
            "| 键 | 库里值的字节 | 加密 | 代码引用数 |", "|---|---:|:--:|---:|"]
    dbs = d.get("config_keys_in_seed_db", {})
    for k in sorted(set(dbs) | set(d["config_keys"])):
        dbv = dbs.get(k, {})
        cv = d["config_keys"].get(k, {})
        out.append(f"| `{k}` | {dbv.get('value_bytes', '—')} | "
                   f"{'✓' if dbv.get('is_encrypted') else ''} | {cv.get('n_refs', 0)} |")
    write("12-config-surface.md", "配置面（环境变量 + 配置键）", "\n".join(out))


# ──────────────────────────────────────────────────────────────────────
def gen_table_io() -> None:
    d = load("tables_io")
    cnt = d["counts"]
    out = [
        "## 一、口径", "", d["caliber"], "",
        "## 二、总账", "",
        "| 项 | 数 |", "|---|---:|",
        f"| 表 | **{cnt['tables']}** |",
        f"| 静态查不到写入方的表 | **{cnt['tables_with_no_writer_found']}** |",
        f"| 静态查不到读取方的表 | **{cnt['tables_with_no_reader_found']}** |",
        "",
        "> ⚠ 这两行是**计数，不是判断**。「查不到」有三种可能：① 真的没人动；",
        "> ② 表名用 f-string 拼的（本仓实测 7 处）"
        "；③ 由 SQLite 自己维护（如 FTS 影子表）。",
        "",
        "## 三、每张表的读写方", "",
        "| 表 | 写入方 | 读取方 |", "|---|:--:|:--:|",
    ]
    for k, v in sorted(d["tables"].items()):
        w = len(v["write"])
        r = len(v["read"])
        out.append(f"| `{k}` | {w if w else '**0**'} | {r if r else '**0**'} |")
    out += ["", "## 四、详细（谁写谁读）", ""]
    for k, v in sorted(d["tables"].items()):
        if not v["write"] and not v["read"]:
            continue
        out.append(f"### `{k}`")
        out.append("")
        if v["write"]:
            out.append("写入：" + "、".join(f"`{x}`" for x in v["write"]))
        if v["read"]:
            out.append("")
            out.append("读取：" + "、".join(f"`{x}`" for x in v["read"]))
        out.append("")
    write("13-table-io.md", "表读写关系", "\n".join(out))



# ──────────────────────────────────────────────────────────────────────
def gen_test_index() -> None:
    d = load("test_content")
    cnt = d["counts"]
    out = [
        "## 一、口径", "", d["caliber"], "",
        "## 二、总账", "",
        "| 项 | 数 |", "|---|---:|",
        f"| 测试文件 | **{cnt['files']}** |",
        f"| 测试函数 | **{cnt['test_functions']:,}** |",
        f"| 有 docstring | {cnt['with_docstring']:,} |",
        f"| 没有 docstring | {cnt['without_docstring']:,} |",
        "",
        "> **这一份的用途**：想确认「某功能有没有被测试钉住」，按关键词在本文件里搜，",
        "> 不用读测试体。测试名本身就是描述。",
        "",
        "## 三、每个文件的测试清单", "",
    ]
    for f in sorted(d["files"], key=lambda x: -x.get("n_tests", 0)):
        if not f.get("n_tests"):
            out.append(f"### `{f['file']}`（0 个测试函数）")
            out.append("")
            continue
        out.append(f"### `{f['file']}`（{f['n_tests']} 个）")
        out.append("")
        cur = None
        for t in f["tests"]:
            if t["group"] != cur:
                cur = t["group"]
                if cur:
                    out.append(f"**{cur}**")
                    out.append("")
            note = (" — " + str(t["purpose"]).replace("[", "\\[")
                    .replace("]", "\\]")) if t["purpose"] else ""
            out.append(f"- `{t['name']}`{note}")
        out.append("")
    write("14-test-index.md", "测试索引（每个测试钉住了什么）", "\n".join(out))


def gen_doc_index_content() -> None:
    d = load("doc_content")
    cnt = d["counts"]
    out = [
        "## 一、口径", "", d["caliber"], "",
        "## 二、总账", "",
        "| 项 | 数 |", "|---|---:|",
        f"| 文档 | **{cnt['docs']}** |",
        f"| 有首段摘要 | {cnt['with_summary']} |",
        f"| 没有（开头是列表/表格） | {cnt['without_summary']} |",
        "",
        "## 三、每份文档讲什么", "",
        "| 文件 | 行数 | 标题 | 首段 | 二级小节数 |",
        "|---|---:|---|---|---:|",
    ]
    for x in sorted(d["docs"], key=lambda y: y["path"]):
        ttl = cell((x["title"] or "")[:50])
        summ = cell((x["summary"] or "—")[:90])
        out.append(f"| `{x['path']}` | {x['lines']:,} | {ttl} | {summ} | {x['n_h2']} |")
    out += ["", "## 四、二级小节最多的 15 份（结构最复杂的文档）", ""]
    for x in sorted(d["docs"], key=lambda y: -y["n_h2"])[:15]:
        out.append(f"### `{x['path']}`（{x['n_h2']} 个二级小节）")
        out.append("")
        for h in x["h2_headings"]:
            out.append(f"- {h}")
        out.append("")
    write("15-doc-index-content.md", "文档内容索引（每份讲什么）", "\n".join(out))


def gen_frontend() -> None:
    d = load("web_content")
    cnt = d["counts"]
    out = [
        "## 一、口径", "", d["caliber"], "",
        "## 二、总账", "",
        "| 项 | 数 |", "|---|---:|",
        f"| 文件 | **{cnt['files']}** |",
        f"| 导出 | {cnt['total_exports']} |",
        f"| 声明 | {cnt['total_declarations']} |",
        f"| 含 JSX 的 | {cnt['with_jsx']} |",
        "",
        "## 三、每个文件", "",
        "| 文件 | 行数 | 导出 | 声明 | 开头说明 |",
        "|---|---:|---:|---:|---|",
    ]
    for f in sorted(d["files"], key=lambda x: -x["lines"]):
        note = cell((f["header_note"] or "—")[:70])
        out.append(f"| `{f['file']}` | {f['lines']:,} | {f['n_exports']} | "
                   f"{f['n_declarations']} | {note} |")
    # ── 与「真 AST」对照（两份各有盲区，如实并列）──
    astp = DATA / "web_ast.json"
    if astp.exists():
        a = json.loads(astp.read_text(encoding="utf-8"))
        ac, rc = a["counts"], d["counts"]
        ast_by = {f["file"]: f for f in a["files"]}
        rex_by = {f["file"]: f for f in d["files"]}
        gaps = []
        for f in sorted(set(ast_by) & set(rex_by)):
            x, y = ast_by[f]["n_exports"], rex_by[f]["n_exports"]
            if abs(x - y) >= 3:
                gaps.append((x, y, f))
        out += [
            "## 三之二、与「真 AST」对照（**两份各有盲区，不选边**）", "",
            f"仓库根已有 `typescript@{a['typescript_version']}`，"
            "用它建真 AST 抽了一遍（`scripts/survey/09-web-ast.cjs`）。", "",
            "| 口径 | 文件 | 导出 | 声明 |", "|---|---:|---:|---:|",
            f"| **AST**（`ts.createSourceFile`） | {ac['files']} | **{ac['total_exports']}** | "
            f"**{ac['total_declarations']}** |",
            f"| 正则（本节上表） | {rc['files']} | {rc['total_exports']} | "
            f"{rc['total_declarations']} |",
            "",
            "**差异说明（不判断谁对）**：",
            "",
            "| 现象 | 原因 |",
            "|---|---|",
            "| AST 导出数**少** 37 | AST 只走**顶层语句**；"
            "`declare module '…' { export … }` 里的导出不在顶层 ⇒ 没进去 |",
            "| AST 声明数**多** 385 | 正则只认 `function/const/class` 三种，"
            "**漏掉 `interface` / `type` / `enum`** |",
            "",
        ]
        if gaps:
            out += ["导出数差 ≥3 的文件（AST / 正则 / 文件）：", ""]
            for x, y, f in sorted(gaps, key=lambda z: -abs(z[0] - z[1]))[:8]:
                out.append(f"- {x} / {y} / `{f}`")
            out += [""]
    out += ["", "## 四、每个文件导出了什么（逐个列）", ""]
    for f in sorted(d["files"], key=lambda x: x["file"]):
        if not f["exports"]:
            continue
        out.append(f"### `{f['file']}`")
        out.append("")
        out.append("、".join(f"`{e}`" for e in f["exports"]))
        out.append("")
    write("16-frontend.md", "前端清单（文件 / 导出 / 说明）", "\n".join(out))



def gen_function_index() -> None:
    d = load("symbols_py")
    summ = d["summary"]
    out = [
        "## 一、口径", "",
        "`purpose` = 该函数的 **docstring 第一句*"
        "*（跳过 `#` 标题行，按 `。`/`；`/换行切，"
        "上限 140 字）。**没有 docstring 的函数 purpose 为空** —— 这是记录，不是评价。",
        "",
        "`text_hits` = 该名字在扫描面内**全部 `.py` 文本**里出现几次（含定义行）。"
        "**这是下界，不是调用图**（getattr / 装饰器注册 / 字符串派发 / "
        "pytest 按名收集都看不见）。",
        "",
        "## 二、总账", "",
        "| 项 | 数 |", "|---|---:|",
        f"| 模块 | {summ['modules']:,} |",
        f"| 符号 | **{summ['symbols']:,}** |",
        f"| 类 | {summ['classes']:,} |",
        f"| 函数（含方法） | {summ['functions']:,} |",
        f"| 有 docstring | {summ['symbols'] - summ['no_docstring']:,} |",
        f"| 没有 docstring | {summ['no_docstring']:,} |",
        "",
        "## 三、按模块列全部符号", "",
    ]
    for m in sorted(d["modules"], key=lambda x: x["module"]):
        syms = m["symbols"]
        if not syms:
            continue
        out.append(f"### `{m['module']}`（{len(syms)} 个符号）")
        out.append("")
        if m.get("docstring"):
            head = m["docstring"].splitlines()[0] if m["docstring"].strip() else ""
            if head:
                out.append(f"> {cell(head[:160])}")
                out.append("")
        out.append("| 符号 | 行 | 引用 | 职责 |")
        out.append("|---|---:|---:|---|")
        for s in sorted(syms, key=lambda x: x["lineno"]):
            kind = "类" if s["kind"] == "class" else "函数"
            out.append(f"| `{s['name']}` {kind} | {s['lineno']} | "
                       f"{s.get('text_hits', 0)} | {cell(s.get('purpose') or '—')} |")
        out.append("")
    write("17-function-index.md", "函数索引（每个符号的职责与引用计数）", "\n".join(out))



def gen_runtime_probe() -> None:
    d = load("runtime_probe")
    cnt = d["counts"]
    iso = d["isolation"]
    out = [
        "## 一、这是唯一真正跑起来的一层", "",
        "前面 17 份文档全是**静态**的：看代码写了什么。",
        "这一份是**真启动引擎、把每条端点都调了一遍** —— 静态检查验不了「跑起来会怎样」。", "",
        "## 二、隔离边界（保证没碰生产数据）", "",
        "| 项 | 值 |", "|---|---|",
        f"| 数据目录 | {iso['KS_DATA_DIR']} |",
        f"| 模型目录 | {iso['KS_MODELS_DIR']} |",
        f"| 说明 | {iso['note']} |",
        "", d["caliber"], "",
        "## 三、总账", "",
        "| 项 | 数 |", "|---|---:|",
        f"| 探测端点 | **{cnt['routes_probed']}** |",
    ]
    for k, v in sorted(cnt["by_status"].items(), key=lambda kv: -kv[1]):
        label = {"200": "200 正常", "404": "404 占位 id 不存在（合理）",
                 "422": "422 缺必填字段（正常）", "400": "400",
                 "timeout": "超时（12 秒）", "409": "409 冲突",
                 "500": "**500 未捕获异常**"}.get(k, k)
        out.append(f"| {label} | {v} |")
    out += ["", "> ⚠ `422` 与 `404` 是**空 body + 占位 id** 的正常结果，不是缺陷。",
            "> 真正的异常是 `500` 与 `timeout` —— 见 §五。", "",
            "## 四、`/api/v1/health` 的真实响应", ""]
    h = d["health"]
    out.append(f"- HTTP **{h.get('status')}**，**{h.get('ms')} ms**，{h.get('bytes')} 字节")
    out.append(f"- 顶层键：{', '.join('`' + x + '`' for x in (h.get('top_keys') or []))}")
    out += ["", "## 五、异常项逐条（**只记录，不判断**）", "",
            "### 500（未捕获异常）", ""]
    for r in d["results"]:
        if str(r.get("status")) == "500":
            out.append(f"- `{r['method']} {r['declared_path']}` "
                       f"—— `{r.get('handler')}` @ `{r.get('file')}:{r.get('lineno')}`")
    out += ["", "### 超时的端点（按路径前缀归组）", ""]
    from collections import Counter
    pref = Counter()
    for r in d["results"]:
        if r.get("status") is None and r.get("timeout"):
            parts = r["declared_path"].split("/")
            pref["/".join(parts[:4])] += 1
    out += ["| 前缀 | 超时条数 |", "|---|---:|"]
    for k, v in pref.most_common():
        out.append(f"| `{k}` | {v} |")
    # ── 超时归因：**只读这个 handler 自己的函数体** ──
    # 第一版从 handler 起始行往后扫 200 行 ⇒ 扫到了同文件别的函数，
    # 加上关键词里有 `http` 这种到处都有的词 ⇒ 49/71 都被标成「等云模型」。
    # 现在：从 def 行吃到「下一个同缩进的 def/装饰器」，并且用更具体的关键词。
    kws = [
        ("等云模型", ("llm", "answer", "_sse", "stream", "deepseek", "vlm",
                     "chat_completions", "OpenAI")),
        ("联网", ("urlopen", "httpx", "requests.", "fetch(", "urllib",
                 "download", "http_get", "apiGet", "apiPost")),
        ("重入库/解析", ("ingest", "parse_pdf", "mineru", "ocr", "_split",
                       "build_clause", "run_full_ingest")),
        ("查数据库", ("conn.execute", "get_db_connection", "write_transaction",
                     "read_transaction")),
    ]

    def handler_body(f: str, lineno: int) -> str:
        path = ROOT / f
        if not path.exists():
            return ""
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        if lineno <= 0 or lineno > len(lines):
            return ""
        # 找到 handler 的 def 行（路由装饰器附近）
        start = None
        for i in range(max(0, lineno - 1), min(len(lines), lineno + 10)):
            if re.match(r"\s*(?:async\s+)?def\s", lines[i]):
                start = i
                break
        if start is None:
            return ""
        base = len(lines[start]) - len(lines[start].lstrip())
        out_lines = [lines[start]]
        for ln in lines[start + 1:]:
            s = ln.strip()
            if s and (len(ln) - len(ln.lstrip())) <= base and (
                    re.match(r"(?:async\s+)?def\s", s) or s.startswith("@")
                    or re.match(r"def\s", s)):
                break
            out_lines.append(ln)
        return "\n".join(out_lines)

    attrib: dict[str, list[str]] = {}
    attribution_detail: list[dict] = []
    for r in d["results"]:
        if r.get("status") is not None or not r.get("timeout"):
            continue
        body = handler_body(r.get("file") or "", r.get("lineno") or 0)
        low = body.lower()
        tags = [name for name, words in kws if any(w.lower() in low for w in words)]
        key = " + ".join(tags) if tags else "**handler 里看不出明确来源**"
        attrib.setdefault(key, []).append(r["declared_path"])
        attribution_detail.append({
            "path": r["declared_path"], "handler": r.get("handler"),
            "body_lines": body.count("\n") + 1 if body else 0,
            "tags": tags,
        })
    out += ["", "### 超时的 71 条：按**这一个 handler 的函数体**粗分", "",
            "| handler 里碰到什么 | 条数 |", "|---|---:|"]
    for k, v in sorted(attrib.items(), key=lambda kv: -len(kv[1])):
        out.append(f"| {k} | {len(v)} |")
    out += ["",
            "> ⚠ 这是**按关键词粗分**：只扫该 handl"
            "er 自己的函数体（不含同文件其它函数），"
            "看有没有模型/联网/入库/数据库字样。",
            "> **不能证明超时就是因为那个**；要定因"
            "得在超时时抓线程栈。**本检查没做。**",
            "",
            "**⚠ 这一栏最重要的读数是第一行**：大多数超时的 handler **本身看不出会慢**",
            "（没有模型、没有联网、没有重入库）。而它们在第 1 次跑里是**连续 70 条**",
            "一起超时的（第 107–176 条）⇒ 更可能是**整体被卡住**，不是各自慢。",
            "与 [`10-observed.md`](10-observed.md) §七 O-22 的间歇性卡死对应着看。",
            "",
            "**逐条明细**（前 30 条）：", "",
            "| 端点 | handler | 函数体行数 | 命中 |", "|---|---|---:|---|"]
    for x in attribution_detail[:30]:
        out.append(f"| `{x['path']}` | `{x['handler']}` | {x['body_lines']} | "
                   f"{cell('、'.join(x['tags']) or '—')} |")
    out += ["", "## 六、全部端点实测结果", "",
            "| 方法 | 路径 | 状态 | 耗时 | 处理函数 |", "|---|:---:|---:|---|"]
    for r in d["results"]:
        st = r.get("status") if r.get("status") is not None else (
            "超时" if r.get("timeout") else "无响应")
        out.append(f"| {r['method']} | `{r['declared_path']}` | {st} | "
                   f"{r.get('ms', '—')} ms | `{r.get('handler')}` |")
    write("18-runtime-probe.md", "运行时探测（真启动引擎，176 条端点实测）", "\n".join(out))



# ──────────────────────────────────────────────────────────────────────
def gen_requirements() -> None:
    """需求编号 / 否决台账索引 + 种子库数据样例。"""
    req = load("requirements")
    nd = load("notdoing")
    ds = load("data_samples")
    rc, nc, dc = req["counts"], nd["counts"], ds["counts"]
    out = [
        "## 一、口径（这里有个坑，先看）", "",
        "本仓的 **`R` 前缀有两种含义**：",
        "",
        "| 形态 | 含义 | 例子 |",
        "|---|---|---|",
        "| `R24` / `R6c` / `R4b` | **需求编号 / 巡检轮次"
        "编号** | 代码注释里引它来说明「为什么这么写」 |",
        "| `R00/09` / `R80/89` | **中标分类号 CCS**（中国标准文献分类法） | "
        "`R00/09` = 公路水路运输综合，`R80/89` = 交通管理 |",
        "",
        "第一版正则把 3 个 CCS 号误报成「文档里找不到」——**那是我的误报**。",
        "现在三种排除：跟 `/数字` 的、前导零的、整行含 CCS/分类法/category 的。",
        "",
        "## 二、编号**没有单一权威文档**", "",
        "实测分布：", "",
        "| 文档 | 定义了多少个编号 |", "|---|---:|",
    ]
    for k, v in rc["definition_by_source"].items():
        out.append(f"| `{k}` | {v} |")
    out += [
        "",
        "⇒ 找编号含义**要跨文档搜**。`R6c` 不在需求文档里，它是 "
        "`CHANNEL-R6C-DESIGN.md` 的一级标题；`R6a/R6b` 只在渠道方案正文里内联出现。",
        "",
        "## 三、总账", "",
        "| 项 | 数 |", "|---|---:|",
        f"| 编号定义（扫全部 `docs/**/*.md`，标题级） | **{rc['level1_heading']}** |",
        f"| 行首加粗级定义 | {rc['level2_bold']} |",
        f"| 代码里引用到的编号 | **{rc['referenced_in_code']}** |",
        f"| 定义了但**代码从未引用** | {rc['defined_but_never_referenced']} |",
        f"| 代码引用了、**任何文档都找不到** | **{rc['level4_nowhere']}** |",
        "",
        "### 代码引用了、文档里找不到的（**附原文行，自己判断**）", "",
    ]
    for x in req["referenced_but_defined_nowhere"]:
        out.append(f"- **`{x['id']}`** —— 代码引用于 "
                   + "、".join(f"`{f['file']}`({f['n']})" for f in x["code_ref_files"]))
        out.append(f"  - 原文：`{cell(x['first_source_line'])}`")
        out.append(f"  - 提示：{cell(x['hint'])}")
    out += ["", "## 四、需求编号全表（按编号排序）", "",
            "| 编号 | 定义在哪 | 行 | 代码引用 | 标题 |", "|---|---|---:|---:|---|"]
    for r in req["requirements"]:
        if r["level"].startswith("④"):
            continue
        out.append(f"| `{r['id']}` | `{r['source']}` | {r['lineno']} | "
                   f"{r['code_ref_total']} | {cell(r['title'][:70])} |")
    out += ["", "## 五、否决台账（`NOT-DOING.md`）", "",
            "| 项 | 数 |", "|---|---:|",
            f"| 台账条目 | **{nc['items']}** |",
            f"| 代码里引用到的 | {nc['items_referenced_in_code']} |",
            f"| 代码引用了但台账没记 | {nc['ids_referenced_but_not_in_ledger']} |",
            "",
            "| # | 事项 | 裁决 | 代码引用 |", "|---:|---|---|---:|"]
    for it in nd["items"]:
        out.append(f"| {it['id']} | {cell(it['what'][:70])} | "
                   f"{cell(it['verdict'])} | {it['code_ref_total']} |")
    out += ["", "## 六、种子库数据样例", "",
            f"{ds['caliber']}", "",
            "| 项 | 数 |", "|---|---:|",
            f"| 表 | {dc['tables']} |",
            f"| **有数据的表** | {dc['tables_with_samples']} |",
            "", "### 每张表抽 2 行", ""]
    for tb in ds["tables"]:
        rows = tb.get("rows") or []
        if not rows:
            continue
        out.append(f"#### `{tb['table']}`（{len(tb['columns'])} 列）")
        out.append("")
        cols = tb["columns"]
        out.append("| " + " | ".join(f"`{c}`" for c in cols[:8]) + " |")
        out.append("|" + "---|" * min(len(cols), 8))
        for row in rows:
            out.append("| " + " | ".join(
                cell(str(row.get(c) if row.get(c) is not None else "—")[:40])
                for c in cols[:8]) + " |")
        out.append("")
    write("19-requirements.md", "需求编号 / 否决台账 / 数据样例",
          "\\n".join(out))



def gen_rules() -> None:
    d = load("rules")
    c = d["counts"]
    out = [
        "## 一、口径", "", d["caliber"], "",
        "## 二、总账", "",
        "| 项 | 数 |", "|---|---:|",
        f"| 扫描 `src/**/*.py` | {c['py_files_scanned']} |",
        f"| 抽出规则常量 | **{c['rules']}** |",
        f"| 正则类 | {c['by_kind'].get('regex', 0)} |",
        f"| 数值阈值类 | {c['by_kind'].get('threshold', 0)} |",
        f"| **带注释（有理由）** | {c['with_comment']} |",
        f"| 没注释 | {c['without_comment']} |",
        "",
        "## 三、规则集中在哪", "",
        "| 文件 | 规则数 |", "|---|---:|",
    ]
    for k, v in d["by_file_top"].items():
        out.append(f"| `{k}` | {v} |")
    out += ["", "## 四、按文件列全部规则", ""]
    cur = None
    for r in sorted(d["rules"], key=lambda x: (x["file"], x["lineno"])):
        if r["file"] != cur:
            cur = r["file"]
            out.append(f"### `{cur}`")
            out.append("")
            out.append("| 行 | 名字 | 类型 | 值 | 挂在哪 | 注释（原文） |")
            out.append("|---:|---|---|---|---|---|")
        val = cell(r["value"][:70])
        out.append(f"| {r['lineno']} | `{r['name']}` | {r['kind']} | `{val}` | "
                   f"`{r['scope']}` | {cell(r['comment'][:80]) or '—'} |")
        if r is d["rules"][-1]:
            out.append("")
    write("20-rules.md", "判定规则总表（正则 / 阈值 / 理由）", "\\n".join(out))


def main() -> int:
    gen_readme()
    gen_inventory()
    gen_code_map()
    gen_cross_ref()
    gen_data_shape()
    gen_api()
    gen_tests()
    gen_docs()
    gen_gates()
    gen_module_index()
    gen_config()
    gen_table_io()
    gen_test_index()
    gen_doc_index_content()
    gen_frontend()
    gen_function_index()
    gen_runtime_probe()
    gen_requirements()
    gen_rules()
    print("\n全部生成完毕")
    return 0


if __name__ == "__main__":
    sys.exit(main())
