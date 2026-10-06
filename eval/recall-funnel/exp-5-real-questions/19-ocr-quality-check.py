"""体检业主正在产出的 MinerU OCR 结果：**进度 + 质量**（重点看表格与数字）。

业主 2026-10-07："已经有几百份了，你看看 …\\GB"。
实测产物形态：每本一个 `<标准名>.mineru-4.0.10-vlm\\` 文件夹，内有
 `markdown.md` / `middle_json.json` / `structured_content.json` / `images\\`（含 page_N_table_M.jpg）。

本脚本只读，回答四件事：
 ① **进度**：GB 目录里 1,088 个 PDF，已有多少本出了 markdown；
 ② **正文质量**：抽样看 markdown 的字符数与结构（有没有 `第X条`）；
 ③ **★ 表格**：markdown 里表格是**变成了文字/HTML**，还是**只剩一张图片引用**（后者无法检索）；
 ④ **表格图与公式图**的数量（说明有多少内容以图片形态存在）。

只读源目录；不写任何东西。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\19-ocr-quality-check.py --n 12
"""
from __future__ import annotations

import argparse
import json
import re
import statistics as st
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "ocr-quality-check.json"
SRC = Path("D:/AI/work space/标准/🇨🇳《国家标准》(35000+ 141G)/GB")
SUFFIX = ".mineru-4.0.10-vlm"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=12, help="抽样多少本细看")
    args = ap.parse_args()

    if not SRC.exists():
        print(f"⛔ 源目录不在：{SRC}")
        return 1

    pdfs = list(SRC.rglob("*.PDF")) + list(SRC.rglob("*.pdf"))
    dirs = [d for d in SRC.rglob("*") if d.is_dir() and d.name.endswith(SUFFIX)]
    print(f"[q] GB 目录：PDF {len(pdfs)} 个；MinerU 产物目录 {len(dirs)} 个", flush=True)
    done = sum(1 for d in dirs if (d / "markdown.md").exists())
    print(f"[q] 其中含 markdown.md 的 {done} 个 ⇒ 进度约 {done/max(1,len(pdfs)):.1%}", flush=True)

    # 各子目录进度
    per = {}
    for sub in sorted(SRC.iterdir()):
        if not sub.is_dir():
            continue
        p = len(list(sub.rglob("*.PDF"))) + len(list(sub.rglob("*.pdf")))
        m = len([d for d in sub.rglob("*") if d.is_dir() and d.name.endswith(SUFFIX)
                 and (d / "markdown.md").exists()])
        per[sub.name] = {"pdf": p, "done": m}
        print(f"    {sub.name:26s} PDF {p:4d}  已出 {m:4d}  ({m/max(1,p):.0%})", flush=True)

    # 抽样细看
    import random
    rnd = random.Random(20261007)
    pool = [d for d in dirs if (d / "markdown.md").exists()]
    pick = rnd.sample(pool, min(args.n, len(pool)))
    samples, tbl_text, tbl_img = [], 0, 0
    chars, has_clause, img_refs = [], 0, 0
    for d in pick:
        md = (d / "markdown.md").read_text(encoding="utf-8", errors="ignore")
        imgs = list((d / "images").glob("*")) if (d / "images").exists() else []
        n_tbl_img = sum(1 for i in imgs if "_table_" in i.name)
        n_eq_img = sum(1 for i in imgs if "_equation_" in i.name)
        # markdown 里的表格表现
        has_md_table = bool(re.search(r"^\s*\|.*\|\s*$", md, re.M))
        has_html_table = "<table" in md.lower()
        has_img_link = bool(re.search(r"!\[\]\(images/", md))
        clauses = len(re.findall(r"第[一二三四五六七八九十百零\d]{1,4}条", md))
        chars.append(len(md))
        has_clause += 1 if clauses else 0
        img_refs += 1 if has_img_link else 0
        tbl_text += 1 if (has_md_table or has_html_table) else 0
        tbl_img += 1 if n_tbl_img else 0
        samples.append({"doc": d.name[:60], "chars": len(md), "clauses": clauses,
                        "md_table": has_md_table, "html_table": has_html_table,
                        "image_links": has_img_link, "table_images": n_tbl_img,
                        "equation_images": n_eq_img, "images_total": len(imgs),
                        "head": md[:300].replace("\n", " ")})
        print(f"    {len(md):7d} 字  第X条 {clauses:4d}  md表 {int(has_md_table)} html表 "
              f"{int(has_html_table)} 图链 {int(has_img_link)} 表图 {n_tbl_img:3d}  {d.name[:44]}",
              flush=True)

    n = len(samples)
    res = {
        "why": "体检业主正在产出的 MinerU OCR 结果：进度 + 质量（重点表格与数字）",
        "source": str(SRC),
        "progress": {"pdf_total": len(pdfs), "mineru_dirs": len(dirs), "with_markdown": done,
                     "ratio": round(done / max(1, len(pdfs)), 4), "per_subdir": per},
        "sampled": n,
        "markdown": {
            "chars_median": int(st.median(chars)) if chars else None,
            "chars_min": min(chars) if chars else None,
            "chars_max": max(chars) if chars else None,
            "docs_with_clause_numbers": has_clause,
            "docs_with_table_as_text": tbl_text,
            "docs_with_table_images": tbl_img,
            "docs_with_image_links": img_refs,
        },
        "reading": {
            "表格变成文字的比例": f"{tbl_text}/{n}" + "（这些表格内容**可被检索**）",
            "存在表格图的比例": f"{tbl_img}/{n}" + "（表格另有图片，若正文只有图链则**不可检索**）",
            "含第X条的比例": f"{has_clause}/{n}" + "（决定能不能按条款切分）",
        },
        "samples": samples,
        "boundary": ["抽样是随机的、n 小，只判方向；只读源目录，未写任何内容。"],
    }
    OUT.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print()
    print(json.dumps({k: v for k, v in res.items() if k != "samples"}, ensure_ascii=False, indent=1))
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
