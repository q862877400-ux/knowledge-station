"""全量扫已 OCR 的 markdown：**有多少含条款号结构**（**修正版**）。

## ⚠ 更正我自己上一版的度量错误（2026-10-07，留痕）
上一版报「含形如 5.1.3 的条款号 **0/756**」—— **那是我量错了**，不是数据的性质：
 · 正则 `^\\s*(\\d+(\\.\\d+){1,3})\\s` **漏了 `re.M`** ⇒ `^` 只匹配整串开头，不匹配每一行；
 · 而 GB 标准的条款号**恰恰是行首数字**（`1.2.1 在我国现有的…`）或**标题**（`## 1.1 主题内容`）。
 ⇒ 实测真实文件（GB 16297-1996）确认条款号**都在**。

## 本版度量（分别量三种形态，避免再量错对象）
 · `## N` / `## N.N`：**markdown 标题形态**的章/节号；
 · 行首 `N.N.N 文字`：**正文形态**的条款号（带 `re.M`）；
 · 「第X条」：**法律法规式**编号 —— GB 标准本来就不用它，量它只为说明"这不是法规"。

只读源目录。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\21-scan-clauses-fixed.py
"""
from __future__ import annotations

import json
import re
import statistics as st
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "scan-clauses-fixed.json"
SRC = Path("D:/AI/work space/标准/🇨🇳《国家标准》(35000+ 141G)/GB")

HEAD_NUM = re.compile(r"^#{1,6}\s*(\d+(?:\.\d+){0,3})\s", re.M)   # ## 1 / ## 1.1
LINE_NUM = re.compile(r"^\s*(\d+(?:\.\d+){1,3})\s+\S", re.M)      # 1.2.1 正文…
LEGAL = re.compile(r"第[一二三四五六七八九十百零\d]{1,4}条")
MD_TABLE = re.compile(r"^\s*\|.*\|\s*$", re.M)


def main() -> int:
    if not SRC.exists():
        print(f"⛔ 源目录不在：{SRC}")
        return 1
    mds = list(SRC.rglob("markdown.md"))
    print(f"[scan] 已出的 markdown = {len(mds)} 个\n", flush=True)

    stats = Counter()
    chars, n_head, n_line, per_sub, per_sub_ok = [], [], [], Counter(), Counter()
    samples = []
    for p in mds:
        t = p.read_text(encoding="utf-8", errors="ignore")
        sub = p.parts[len(SRC.parts)]
        per_sub[sub] += 1
        if not t.strip():
            stats["empty"] += 1
            continue
        chars.append(len(t))
        heads = HEAD_NUM.findall(t)
        lines = LINE_NUM.findall(t)
        has_legal = bool(LEGAL.search(t))
        has_md_table = bool(MD_TABLE.search(t))
        has_html = "<table" in t.lower()
        n_head.append(len(heads))
        n_line.append(len(lines))
        stats["head_num_docs"] += 1 if heads else 0
        stats["line_num_docs"] += 1 if lines else 0
        stats["legal_docs"] += 1 if has_legal else 0
        stats["md_table_docs"] += 1 if has_md_table else 0
        stats["html_table_docs"] += 1 if has_html else 0
        # "有条款结构"= 标题号或正文号任一
        structured = bool(heads) or bool(lines)
        stats["structured_docs"] += 1 if structured else 0
        if structured:
            per_sub_ok[sub] += 1
        samples.append({"doc": p.parent.name[:56], "chars": len(t), "heads": len(heads),
                        "line_nums": len(lines), "legal": has_legal, "md_table": has_md_table,
                        "html_table": has_html, "structured": structured})

    n = max(1, len(mds))
    print(f"[scan] **有条款结构**（标题号或正文号）: {stats['structured_docs']}/{len(mds)} "
          f"({stats['structured_docs']/n:.0%})")
    print(f"[scan]   含标题号 `## N / ## N.N` : {stats['head_num_docs']}/{len(mds)} "
          f"({stats['head_num_docs']/n:.0%})  中位条数 {int(st.median(n_head)) if n_head else 0}")
    print(f"[scan]   含正文号 `N.N.N 文字`    : {stats['line_num_docs']}/{len(mds)} "
          f"({stats['line_num_docs']/n:.0%})  中位条数 {int(st.median(n_line)) if n_line else 0}")
    print(f"[scan]   含「第X条」(**法规式，国标本就不用**): {stats['legal_docs']}/{len(mds)}")
    print(f"[scan]   含 markdown 表格: {stats['md_table_docs']}/{len(mds)} "
          f"({stats['md_table_docs']/n:.0%})  含 html 表格: {stats['html_table_docs']}/{len(mds)} "
          f"({stats['html_table_docs']/n:.0%})")
    print(f"[scan] 字符数 中位 {int(st.median(chars))} / 最小 {min(chars)} / 最大 {max(chars)}")

    print("\n[scan] 按子目录（已出 / 其中有条款结构）：")
    for k in sorted(per_sub):
        print(f"    {k:26s} {per_sub[k]:5d}  有结构 {per_sub_ok.get(k, 0):5d} "
              f"({per_sub_ok.get(k, 0)/max(1, per_sub[k]):.0%})")

    no_struct = [s for s in samples if not s["structured"]]
    print(f"\n[scan] 没有条款结构的 {len(no_struct)} 本，抽 8 本看是什么：")
    for s in sorted(no_struct, key=lambda x: -x["chars"])[:8]:
        print(f"    {s['chars']:7d} 字  表{s['md_table']}  {s['doc']}")

    OUT.write_text(json.dumps({
        "why": "全量扫已 OCR 的 markdown 的条款结构（**修正版**）",
        "correction": ("上一版报『含形如 5.1.3 的条款号 0/756』是**我的度量错误**："
                       "正则漏 `re.M`，`^` 只匹配整串开头。实测 GB 16297-1996 确认条款号都在"
                       "（形态为 `## 1.1 主题内容` 与 `1.2.1 在我国…`）。本版分三种形态分别量。"),
        "source": str(SRC), "markdown_total": len(mds), "stats": dict(stats),
        "chars": {"median": int(st.median(chars)), "min": min(chars), "max": max(chars)},
        "per_subdir": {k: {"markdown": per_sub[k], "structured": per_sub_ok.get(k, 0)}
                       for k in sorted(per_sub)},
        "no_structure_sample": sorted(no_struct, key=lambda x: -x["chars"])[:20],
        "boundary": ["按字符串形态统计，不等于切分正确；只读源目录。"],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
