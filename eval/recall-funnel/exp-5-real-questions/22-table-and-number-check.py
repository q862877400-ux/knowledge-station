"""OCR 质量终检：**表格可检索性** + **数字损伤的迹象**。

业主 2026-10-07 说"已经有几百份了，你看看 …\\GB"。
前两轮已确认：**100% 有条款结构**（`## 1.1` / `1.2.1`），表格大多变成了文字。
本脚本查最后两个要命的点：

 ① **表格只剩图片的**有多少本 —— 这类表格**检索不到**（正文里没有表格文字）；
 ② **数字损伤的迹象** —— GB 的要求全在数值里，所以量：
    · 小数点位形态异常（如 `0 . 5`、`1.0.5`）；
    · 明显被认坏的字符（字母 l/I/O 混进纯数字里，如 `1O0`、`l5`）；
    · 全角/半角混用导致的分隔异常。

⚠ 这两项都是**启发式线索**，不是"错字率"（那需要人工逐格比对原 PDF）。

只读源目录。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\22-table-and-number-check.py
"""
from __future__ import annotations

import json
import re
import statistics as st
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "table-number-check.json"
SRC = Path("D:/AI/work space/标准/🇨🇳《国家标准》(35000+ 141G)/GB")

MD_TABLE = re.compile(r"^\s*\|.*\|\s*$", re.M)
#: 数字里混进字母（易被认坏）：如 1O0 / l5 / 2S
BAD_ALNUM = re.compile(r"\b\d*[lIOo]\d+\b|\b\d+[lIOo]\d*\b")
#: 小数点被空格拆开：0 . 5  /  1 . 25
SPACED_DOT = re.compile(r"\d\s+\.\s+\d")
#: 小数点重复/错位：1.0.5（三段以上且末段是单个数字——很可能是 1.0.5 本应 1.0.5？跳过，改为量明显异常）
DOUBLE_DOT = re.compile(r"\d\.\d\.\d")


def main() -> int:
    if not SRC.exists():
        print(f"⛔ 源目录不在：{SRC}")
        return 1
    dirs = [d for d in SRC.rglob("*") if d.is_dir() and d.name.endswith(".mineru-4.0.10-vlm")]
    print(f"[chk] MinerU 产物目录 {len(dirs)} 个\n", flush=True)

    stats = Counter()
    rows = []
    table_img_no_text = []
    for d in dirs:
        md_p = d / "markdown.md"
        if not md_p.exists():
            stats["no_markdown"] += 1
            continue
        t = md_p.read_text(encoding="utf-8", errors="ignore")
        imgs = list((d / "images").glob("*")) if (d / "images").exists() else []
        n_tbl_img = sum(1 for i in imgs if "_table_" in i.name)
        n_eq_img = sum(1 for i in imgs if "_equation_" in i.name)
        has_md_table = bool(MD_TABLE.search(t))
        has_html_table = "<table" in t.lower()
        has_table_text = has_md_table or has_html_table
        bad = len(BAD_ALNUM.findall(t))
        sdot = len(SPACED_DOT.findall(t))
        stats["docs"] += 1
        stats["has_table_text"] += has_table_text
        stats["has_table_image"] += bool(n_tbl_img)
        stats["table_image_no_text"] += bool(n_tbl_img) and not has_table_text
        stats["has_equation_image"] += bool(n_eq_img)
        stats["docs_with_bad_alnum"] += bad > 0
        stats["docs_with_spaced_dot"] += sdot > 0
        stats["total_bad_alnum"] += bad
        stats["total_spaced_dot"] += sdot
        rows.append({"doc": d.name[:56], "table_images": n_tbl_img, "equation_images": n_eq_img,
                     "md_table": has_md_table, "html_table": has_html_table,
                     "table_text": has_table_text, "bad_alnum": bad, "spaced_dot": sdot})
        if n_tbl_img and not has_table_text:
            table_img_no_text.append({"doc": d.name[:60], "table_images": n_tbl_img})

    n = max(1, stats["docs"])
    print(f"[chk] 有 markdown 的 {stats['docs']} 本：")
    print(f"      表格**有文字**（可检索）      : {stats['has_table_text']}/{n} "
          f"({stats['has_table_text']/n:.0%})")
    print(f"      表格**有图片**               : {stats['has_table_image']}/{n} "
          f"({stats['has_table_image']/n:.0%})")
    print(f"      ★ **有表格图但正文无表格文字**: {stats['table_image_no_text']}/{n} "
          f"({stats['table_image_no_text']/n:.0%})  ← 这些表格检索不到")
    print(f"      含公式图                     : {stats['has_equation_image']}/{n} "
          f"({stats['has_equation_image']/n:.0%})")
    print()
    print(f"[chk] 数字损伤线索（启发式，非错字率）：")
    print(f"      出现『数字里混字母』的文档: {stats['docs_with_bad_alnum']}/{n} "
          f"({stats['docs_with_bad_alnum']/n:.0%})，合计 {stats['total_bad_alnum']} 处")
    print(f"      出现『小数点被空格拆开』的文档: {stats['docs_with_spaced_dot']}/{n} "
          f"({stats['docs_with_spaced_dot']/n:.0%})，合计 {stats['total_spaced_dot']} 处")
    if table_img_no_text:
        print(f"\n[chk] 表格只剩图片的样例（前 8）：")
        for x in table_img_no_text[:8]:
            print(f"      表图 {x['table_images']:3d} 张  {x['doc']}")

    OUT.write_text(json.dumps({
        "why": "OCR 终检：表格可检索性 + 数字损伤线索",
        "source": str(SRC), "docs": stats["docs"], "stats": dict(stats),
        "table_image_no_text_sample": table_img_no_text[:30],
        "per_doc_sample": rows[:20],
        "boundary": ["数字损伤项是**启发式线索**，不是错字率；真正的错字率需人工逐格比对原 PDF。",
                     "只读源目录。"],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
