"""全量扫一遍已 OCR 的 markdown：**到底有多少含条款号结构**（决定能不能沿用现有切分）。

## 为什么必须全量扫（业主 2026-10-07）
抽样 12 本里 **0 本**含 `第X条`。但那 12 本恰好是**食品安全类**（以表格为主、本来就没有条款结构），
所以那个 0 **不能**推广 ⇒ 必须扫全部已出的 markdown，并**按子目录/按标准类型分开报**。

同时统计：
 · markdown 里**表格**是文字（可检索）还是只有图片链接（不可检索）；
 · 是否带标题层级（`#`）、是否带 `第X章/节`；
 · 字符数分布。

只读源目录。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\20-scan-all-markdown.py
"""
from __future__ import annotations

import json
import re
import statistics as st
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "scan-all-markdown.json"
SRC = Path("D:/AI/work space/标准/🇨🇳《国家标准》(35000+ 141G)/GB")
SUFFIX = ".mineru-4.0.10-vlm"

CLAUSE = re.compile(r"第[一二三四五六七八九十百零\d]{1,4}条")
CHAPTER = re.compile(r"第[一二三四五六七八九十百零\d]{1,4}章")
NUMERIC_CLAUSE = re.compile(r"^\s*(\d+(?:\.\d+){1,3})\s")          # 形如 5.1.3 的条款号
MD_TABLE = re.compile(r"^\s*\|.*\|\s*$", re.M)


def main() -> int:
    if not SRC.exists():
        print(f"⛔ 源目录不在：{SRC}")
        return 1

    mds = [p for p in SRC.rglob("markdown.md")]
    print(f"[scan] 已出的 markdown = {len(mds)} 个", flush=True)

    stats = {"total": len(mds), "with_clause": 0, "with_chapter": 0, "with_numeric_clause": 0,
             "with_md_table": 0, "with_html_table": 0, "with_image_link": 0, "empty": 0}
    chars, per_sub, per_sub_clause = [], Counter(), Counter()
    worst, best = [], []
    for p in mds:
        t = p.read_text(encoding="utf-8", errors="ignore")
        sub = p.parts[len(SRC.parts)] if len(p.parts) > len(SRC.parts) else "?"
        per_sub[sub] += 1
        if not t.strip():
            stats["empty"] += 1
            continue
        chars.append(len(t))
        has_c = bool(CLAUSE.search(t))
        has_ch = bool(CHAPTER.search(t))
        has_nc = bool(NUMERIC_CLAUSE.search(t))
        has_md = bool(MD_TABLE.search(t))
        has_html = "<table" in t.lower()
        has_img = "![](images/" in t or "](images/" in t
        stats["with_clause"] += has_c
        stats["with_chapter"] += has_ch
        stats["with_numeric_clause"] += has_nc
        stats["with_md_table"] += has_md
        stats["with_html_table"] += has_html
        stats["with_image_link"] += has_img
        if has_c:
            per_sub_clause[sub] += 1
        rec = {"doc": p.parent.name[:58], "chars": len(t), "sub": sub,
               "clause": has_c, "chapter": has_ch, "numeric_clause": has_nc,
               "md_table": has_md, "html_table": has_html, "image_link": has_img}
        (best if has_c else worst).append(rec)

    n = max(1, len(mds))
    pct = lambda k: f"{stats[k]}/{stats['total']} ({stats[k]/n:.0%})"   # noqa: E731
    print(f"\n[scan] 含『第X条』  : {pct('with_clause')}")
    print(f"[scan] 含『第X章』  : {pct('with_chapter')}")
    print(f"[scan] 含形如 5.1.3 的条款号: {pct('with_numeric_clause')}")
    print(f"[scan] 含 markdown 表格: {pct('with_md_table')}")
    print(f"[scan] 含 html 表格    : {pct('with_html_table')}")
    print(f"[scan] 含图片链接      : {pct('with_image_link')}")
    print(f"[scan] 空的 markdown   : {stats['empty']}")
    print(f"[scan] 字符数 中位 {int(st.median(chars)) if chars else None} / "
          f"最小 {min(chars) if chars else None} / 最大 {max(chars) if chars else None}")

    print("\n[scan] 按子目录（已出 / 其中含条款号）：")
    for k in sorted(per_sub):
        print(f"    {k:26s} {per_sub[k]:5d}  含条款号 {per_sub_clause.get(k, 0):5d} "
              f"({per_sub_clause.get(k, 0)/max(1, per_sub[k]):.0%})")

    print("\n[scan] 含条款号的样例（若上面比例低，看这几个说明『有结构的都存在』）：")
    for r in sorted(best, key=lambda x: -x["chars"])[:6]:
        print(f"    {r['chars']:7d} 字  {r['doc']}")

    OUT.write_text(json.dumps({
        "why": "全量扫已 OCR 的 markdown：有多少含条款号结构（决定能否沿用现有按条款切分）",
        "source": str(SRC), "stats": stats,
        "chars": {"median": int(st.median(chars)) if chars else None,
                  "min": min(chars) if chars else None, "max": max(chars) if chars else None},
        "per_subdir": {k: {"markdown": per_sub[k], "with_clause": per_sub_clause.get(k, 0)}
                       for k in sorted(per_sub)},
        "with_clause_sample": sorted(best, key=lambda x: -x["chars"])[:12],
        "without_clause_sample": sorted(worst, key=lambda x: -x["chars"])[:12],
        "boundary": ["只读源目录；统计按字符串出现判断，不等于语义正确。"],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
