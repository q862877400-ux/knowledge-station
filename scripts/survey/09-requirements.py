"""检查第 9 步（派生层）：需求编号索引 / 否决台账索引 / 种子库数据样例。

## 为什么必须有这一层

代码注释里到处引 `R24`、`R30`、`NOT-DOING #16`，但地图里**查不到它们指什么**。
`REQUIREMENTS-v4.3.md`（208 KB）与 `NOT-DOING.md` 也没通读 —— 这就是本检查
最后一块结构性空白。

本脚本把它们**机械提取**成索引，并做**双向交叉引用**：
- 正向：每个编号 → 标题 / 原文首段 / 定义在哪一行
- 反向：每个编号 → 代码里哪儿引用了它（文件 + 次数）

## 三件事

1. `requirements.json` —— 需求编号索引（`### R<n> 标题`）+ 代码引用点
2. `notdoing.json` —— 否决台账索引（表格行）+ 代码引用点
3. `data_samples.json` —— 种子库每张表抽 2 行（值截断 80 字）

**只记录，不判断。**
"""
from __future__ import annotations

import re
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import dump  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "docs" / "survey" / "data"
SEED = ROOT / "tests" / "fixtures" / "seed" / "knowledge-seed.db"

#: 需求编号**没有单一权威文档**（实测：`REQUIREMENTS-v4.3.md` 里是 `### R24`，
#: 而 `R6c` 是 `CHANNEL-R6C-DESIGN.md` 的 `# R6c 设计：…` 一级标题，
#: `R6a/R6b` 只在 `CHANNEL-COVERAGE-PLAN.md` 的正文里内联出现）。
#: ⇒ 扫**全部 `docs/**/*.md`**，按三级认定义，并记下每条来自哪一级。
DOCS_ROOTS = ("docs",)

NOTDOING_DOC = ROOT / "docs" / "NOT-DOING.md"

#: 需求标题：`### R24 标题` / `### R4a 标题`
#: 一级定义：任意层级标题 `# / ## / ### / ####  R24 标题`
REQ_HEAD_RE = re.compile(r"^#{1,4}\s+(R\d+[a-z]?)\b\s*[:：]?\s*(.*)$")
#: 二级定义：行首加粗 `**R6c** …`
REQ_BOLD_RE = re.compile(r"^\s*[-*]?\s*\*\*(R\d+[a-z]?)\*\*\s*[:：]?\s*(.*)$")
#: 渠道方案里的表格行：`| **R6c** | **标题**… |`
REQ_TABLE_RE = re.compile(r"^\|\s*\*\*(R\d+[a-z]?)\*\*\s*\|\s*(.+?)\s*\|")
#: 否决台账的一行：`| 16 | **事项** | 裁决 | 日期 | 归属 |`
ND_ROW_RE = re.compile(r"^\|\s*(\d+)\s*\|\s*(.+?)\s*\|")
#: 代码里引用需求编号：`R24`（前后不能是字母数字）
#: ⚠ **`R` 前缀在本仓有两种含义**（实测踩到，2026-10-24）：
#:   ① **需求编号**：`R24` / `R6c` / `R4b`（1–2 位数字 + 可选小写后缀）
#:   ② **中标分类号 CCS**：`R00/09`（公路水路运输综合）、`R80/89`（交通管理）——
#:      代码里以 `("R00/09", "公路、水路运输综合")` 这种形态出现。
#: 第一版正则 `R\d{1,3}` 把三个 CCS 号当成需求编号报成「文档里找不到」，
#: 那三条（`R00` / `R80` / `R85`）**是我的误报**，不是文档缺失。
#: ⇒ 三条排除规则：① 后面跟 `/数字` 的是 CCS 区间；② 前导零（`R00`）是 CCS；
#:   ③ 整行含 `CCS` / `分类法` / `category` 的跳过。
REQ_REF_RE = re.compile(r"(?<![A-Za-z0-9_])R(\d{1,3}[a-z]?)(?![A-Za-z0-9_])(?!\s*/\s*\d)")
CCS_LINE_RE = re.compile(r"CCS|分类法|category", re.I)
#: 代码里引用否决台账：`NOT-DOING #16`
ND_REF_RE = re.compile(r"NOT-DOING\s*#\s*(\d+)")



def iter_py():
    for root in ("src", "tests", "scripts", "plugin/src", "plugin/client"):
        d = ROOT / root
        if not d.exists():
            continue
        for p in list(d.rglob("*.py")) + list(d.rglob("*.js")) + list(d.rglob("*.ts")):
            if "__pycache__" in p.parts or "node_modules" in p.parts:
                continue
            yield p


# ══════════════════════════════════════════════════════════════════════
# A. 需求编号索引
# ══════════════════════════════════════════════════════════════════════
def first_body_para(lines: list[str], start: int, limit: int = 260) -> str:
    """取标题之后的第一个正文段（跳过空行、表格、代码块、引用）。"""
    buf: list[str] = []
    in_code = False
    for ln in lines[start + 1:start + 40]:
        s = ln.strip()
        if s.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if not s:
            if buf:
                break
            continue
        if s.startswith(("|", "#", ">", "-", "*", "!", "<!--")):
            if buf:
                break
            continue
        buf.append(s)
        if sum(len(x) for x in buf) > limit:
            break
    return " ".join(buf)[:limit]


def collect_definitions() -> tuple[dict[str, dict], dict[str, dict]]:
    """扫全部 docs，返回 (定义表, 仅正文提及表)。

    三级认定，**先到先得**（标题优先于加粗）：
      ① 标题行 `# R24 标题`
      ② 行首加粗 `**R6c** …`
      ③ 都没有 ⇒ 记入「仅正文提及」，附第一处出现位置
    """
    strong: dict[str, dict] = {}
    weak: dict[str, dict] = {}
    for root in DOCS_ROOTS:
        d = ROOT / root
        if not d.exists():
            continue
        for p in sorted(d.rglob("*.md")):
            rel = str(p.relative_to(ROOT)).replace("\\", "/")
            if rel == "docs/survey/09-requirements.md":
                continue
            try:
                lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for i, ln in enumerate(lines):
                m = REQ_HEAD_RE.match(ln)
                if m:
                    rid = m.group(1)
                    if rid not in strong:
                        strong[rid] = {
                            "id": rid, "title": m.group(2).strip().replace("**", "")[:120],
                            "source": rel, "lineno": i + 1, "level": "①标题",
                            "summary": first_body_para(lines, i),
                        }
                    continue
                m = REQ_BOLD_RE.match(ln)
                if m:
                    rid = m.group(1)
                    if rid not in strong and rid not in weak:
                        weak[rid] = {
                            "id": rid, "title": m.group(2).strip().replace("**", "")[:120],
                            "source": rel, "lineno": i + 1, "level": "②行首加粗",
                            "summary": "",
                        }
    # ③ 仅正文提及：只对**代码引用过**的编号补（避免把 R1 这种普通词全扫一遍）
    return strong, weak


def step_requirements() -> None:
    print("\n[A] 需求编号索引（扫全部 docs，三级认定）")
    strong, weak = collect_definitions()
    src_dist: dict[str, int] = {}
    for r in list(strong.values()) + list(weak.values()):
        src_dist[r["source"]] = src_dist.get(r["source"], 0) + 1
    print(f"     ① 标题定义 {len(strong)} 条 / ② 行首加粗 {len(weak)} 条")

    # 代码引用
    all_refs: dict[str, int] = {}
    ref_files: dict[str, list[dict]] = {}
    #: 每个编号在代码里**第一次出现的那一行原文** —— 匹配不到的编号，
    #: 靠这行让读者自己判断它是需求编号还是别的编号体系（实测 `R80`/`R85`
    #: 就是中标分类号 CCS，不是需求编号；我不去猜，把原文交出去）。
    first_line: dict[str, str] = {}
    for p in iter_py():
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        # ⚠ **排除检查器自己**：`scripts/survey/` 下的注释里会提到编号
        #   （比如我写「R80/R85 是 CCS 不是需求编号」），
        #   不排除就会把自己写的说明当成「代码引用了这个编号」。实测踩到。
        if rel.startswith("scripts/survey/"):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for ln in text.splitlines():
            if CCS_LINE_RE.search(ln):
                continue                       # CCS 分类号行，跳过
            for m in REQ_REF_RE.finditer(ln):
                rid = "R" + m.group(1)
                if rid[1] == "0" and len(rid) == 3 and rid[2].isdigit():
                    continue                   # R00 这类前导零 = CCS
                all_refs[rid] = all_refs.get(rid, 0) + 1
                first_line.setdefault(rid, f"{rel}: {ln.strip()[:140]}")
                slot = next((x for x in ref_files.setdefault(rid, [])
                             if x["file"] == rel), None)
                if slot:
                    slot["n"] += 1
                else:
                    ref_files[rid].append({"file": rel, "n": 1})

    # ③ 仅正文提及：对「代码引用了但没①②定义」的编号，在 docs 里找第一处出现
    mention_only: dict[str, dict] = {}
    for rid in all_refs:
        if rid in strong or rid in weak:
            continue
        found = None
        for root in DOCS_ROOTS:
            d = ROOT / root
            if not d.exists():
                continue
            for p in sorted(d.rglob("*.md")):
                rel = str(p.relative_to(ROOT)).replace("\\", "/")
                if rel.startswith("docs/survey/"):
                    continue
                try:
                    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
                except OSError:
                    continue
                for i, ln in enumerate(lines):
                    if re.search(rf"(?<![A-Za-z0-9_]){rid}(?![A-Za-z0-9_])", ln):
                        found = {"id": rid, "source": rel, "lineno": i + 1,
                                 "level": "③仅正文提及", "title": ln.strip()[:100]}
                        break
                if found:
                    break
            if found:
                break
        mention_only[rid] = found or {"id": rid, "level": "④任何文档都没有",
                                      "source": "", "lineno": 0, "title": ""}

    reqs = [dict(r) for r in strong.values()]
    for r in weak.values():
        reqs.append(dict(r))
    for r in reqs:
        r["code_refs"] = sorted(ref_files.get(r["id"], []), key=lambda x: -x["n"])
        r["code_ref_total"] = sum(x["n"] for x in r["code_refs"])
    for rid, r in mention_only.items():
        if r["level"] == "④任何文档都没有":
            reqs.append({**r, "code_refs": sorted(ref_files.get(rid, []),
                                                  key=lambda x: -x["n"]),
                         "code_ref_total": all_refs.get(rid, 0)})
    reqs.sort(key=lambda x: (x["id"][0], len(x["id"]), x["id"]))
    never = [r for r in reqs if not r["code_ref_total"]
             and r["level"] in ("①标题", "②行首加粗")]

    dump("requirements", {
        "generated_by": "scripts/survey/09-requirements.py::step_requirements",
        "sources": DOCS_ROOTS,
        "caliber": (
            "需求编号**没有单一权威文档**（实测）：`REQUIREMENTS-v4.3.md` 用 `### R24`；"
            "`R6c` 是 `CHANNEL-R6C-DESIGN.md` 的 `# R6c 设计：…` 一级标题；"
            "`R6a/R6b` 只在 `CHANNEL-COVERAGE-PLAN.md` 正文内联出现。"
            "⇒ 扫**全部 `docs/**/*.md`**，三级认定：①标题 ②行首加粗 ③仅正文提及；"
            "④任何文档都没有。`code_refs` = `src/ tests/ scripts/ plugin/src/ "
            "plugin/client/` 里 `R<n>` 的文本出现，按文件计数。"
        ),
        "counts": {
            "level1_heading": len(strong),
            "level2_bold": len(weak),
            "level3_mention_only": sum(1 for r in mention_only.values()
                                       if r["level"] == "③仅正文提及"),
            "level4_nowhere": sum(1 for r in mention_only.values()
                                  if r["level"] == "④任何文档都没有"),
            "referenced_in_code": len(all_refs),
            "defined_but_never_referenced": len(never),
            "definition_by_source": dict(sorted(src_dist.items(),
                                               key=lambda kv: -kv[1])[:12]),
        },
        "referenced_but_defined_nowhere": [
            {"id": k,
             "code_ref_files": sorted(ref_files.get(k, []), key=lambda x: -x["n"])[:4],
             "first_source_line": first_line.get(k, ""),
             # 不给结论，只给一个「看原文时的提示」
             "hint": ("原文里有 `\"path\"` / CCS / 分类 等字样 ⇒ 可能不是需求编号"
                      if any(w in first_line.get(k, "")
                             for w in ('"path"', "CCS", "分类", "category"))
                      else "原文看不出归属，需人工判断")}
            for k, v in mention_only.items() if v["level"] == "④任何文档都没有"],
        "requirements": reqs,
    })
    print(f"     ③ 仅正文提及 {sum(1 for r in mention_only.values() if r['level'].startswith('③'))} 个")
    print(f"     ④ 任何文档都没有 {sum(1 for r in mention_only.values() if r['level'].startswith('④'))} 个")
    print(f"     代码引用 {len(all_refs)} 个编号；定义了但代码从未引用 {len(never)} 条")
    for r in mention_only.values():
        if r["level"] == "④任何文档都没有":
            print(f"       ✘ {r['id']}（代码引用 "
                  f"{all_refs.get(r['id'], 0)} 处，文档里找不到）")
            print(f"          原文：{first_line.get(r['id'], '')}")


# ══════════════════════════════════════════════════════════════════════
# B. 否决台账索引
# ══════════════════════════════════════════════════════════════════════
def step_notdoing() -> None:
    print("\n[B] 否决台账索引")
    if not NOTDOING_DOC.exists():
        print(f"  ✘ 缺 {NOTDOING_DOC}")
        return
    lines = NOTDOING_DOC.read_text(encoding="utf-8", errors="replace").splitlines()
    items: list[dict] = []
    for i, ln in enumerate(lines):
        m = ND_ROW_RE.match(ln)
        if not m:
            continue
        num = int(m.group(1))
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) < 3:
            continue
        items.append({
            "id": num,
            "what": re.sub(r"\*\*", "", cells[1])[:160],
            "verdict": re.sub(r"[*⛔⏸⚰🔄]", "", cells[2]).strip()[:40],
            "lineno": i + 1,
            "n_cells": len(cells),
        })
    defined = {x["id"] for x in items}

    refs: dict[int, list[dict]] = {}
    for p in iter_py():
        rel = str(p.relative_to(ROOT)).replace("\\", "/")
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for m in ND_REF_RE.finditer(text):
            n = int(m.group(1))
            slot = next((x for x in refs.setdefault(n, []) if x["file"] == rel), None)
            if slot:
                slot["n"] += 1
            else:
                refs[n].append({"file": rel, "n": 1})
    for it in items:
        it["code_refs"] = sorted(refs.get(it["id"], []), key=lambda x: -x["n"])
        it["code_ref_total"] = sum(x["n"] for x in it["code_refs"])

    undefined = sorted(n for n in refs if n not in defined)
    dump("notdoing", {
        "generated_by": "scripts/survey/09-requirements.py::step_notdoing",
        "source": "docs/NOT-DOING.md",
        "caliber": (
            "否决台账 = `NOT-DOING.md` 里的表格行 `| 编号 | 事项 | 裁决 | … |`；"
            "`verdict` 只取第三列前 40 字并去掉符号。"
            "`code_refs` = 代码里 `NOT-DOING #<n>` 的文本出现。"
        ),
        "counts": {
            "items": len(items),
            "items_referenced_in_code": sum(1 for x in items if x["code_ref_total"]),
            "ids_referenced_but_not_in_ledger": len(undefined),
        },
        "ids_referenced_but_not_in_ledger": undefined,
        "items": items,
    })
    print(f"     台账 {len(items)} 条；代码里被引用 "
          f"{sum(1 for x in items if x['code_ref_total'])} 条")
    if undefined:
        print(f"     ⚠ 代码引用了但台账没记：{undefined[:10]}")


# ══════════════════════════════════════════════════════════════════════
# C. 种子库数据样例
# ══════════════════════════════════════════════════════════════════════
#: 这些列名一旦命中，值**不进 JSON**（只记长度）。
#: 理由：**记录 ≠ 抄录**。种子库是标准语料，但个别表可能有查询原文/用户输入。
SENSITIVE_HINTS = ("token", "secret", "password", "key", "phone", "mobile",
                   "id_card", "email", "address", "name")


def step_data_samples() -> None:
    print("\n[C] 种子库数据样例")
    if not SEED.exists():
        print(f"  ✘ 缺 {SEED}")
        return
    conn = sqlite3.connect(f"file:{SEED}?mode=ro", uri=True)
    try:
        tables = [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        samples = []
        for t in tables:
            try:
                cols = [r[1] for r in conn.execute(f'PRAGMA table_info("{t}")')]
                rows = conn.execute(f'SELECT * FROM "{t}" LIMIT 2').fetchall()
            except sqlite3.Error as exc:
                samples.append({"table": t, "error": f"{type(exc).__name__}: {exc}"[:120]})
                continue
            rec = {"table": t, "columns": cols, "n_sample": len(rows), "rows": []}
            for row in rows:
                out = {}
                for col, val in zip(cols, row):
                    low = (col or "").lower()
                    if val is None:
                        out[col] = None
                    elif any(h in low for h in SENSITIVE_HINTS):
                        # **只记长度与类型，不记值**
                        s = str(val)
                        out[col] = f"<{type(val).__name__} len={len(s)} 未记录>"
                    else:
                        s = str(val)
                        out[col] = s[:80] + ("…" if len(s) > 80 else "")
                rec["rows"].append(out)
            samples.append(rec)
        dump("data_samples", {
            "generated_by": "scripts/survey/09-requirements.py::step_data_samples",
            "source": "tests/fixtures/seed/knowledge-seed.db（随仓种子库）",
            "caliber": (
                "每张表抽 **2 行**；每个值截断 80 字。"
                f"列名命中 {SENSITIVE_HINTS} 之一的，**只记类型与长度、不记值** "
                "（记录 ≠ 抄录）。"
            ),
            "counts": {"tables": len(tables),
                       "tables_with_samples": sum(1 for s in samples if s.get("rows"))},
            "tables": samples,
        })
        print(f"     样例 {sum(1 for s in samples if s.get('rows'))} 张表有数据 / "
              f"共 {len(tables)} 张")
    finally:
        conn.close()


def main() -> int:
    step_requirements()
    step_notdoing()
    step_data_samples()
    print("\n全部落盘")
    return 0


if __name__ == "__main__":
    sys.exit(main())
