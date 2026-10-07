"""全量入库前置清点：**要入多少、大概多久、有没有遗漏**。

业主 2026-10-07 指示："OCR 好了，你把所有强制性国标和法律法规切分入库"。

本脚本只读，回答：
 ① **强制性国标**：GB 目录下 PDF 总数 / 已有 MinerU 产物的 / 其中已有 `middle_json.json` 的；
 ② **法律法规**：`标准\\法律法规` 下 md 总数 / 其中真正含条文的（排除 `README`/`_index`）；
 ③ **已有多少重合**：这些标准号/法规名**真库里是不是已经有了**（避免重复入库）；
 ④ **量级估算**：预计新增条款数与预计耗时（按现役 CPU 嵌入 65 条/s）。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\33-precount-ingest.py
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = HERE / "precount-ingest.json"
sys.path.insert(0, str(ROOT))
GB_ROOT = Path("D:/AI/work space/标准/🇨🇳《国家标准》(35000+ 141G)/GB")
LAW_ROOT = Path("D:/AI/work space/标准/法律法规")
DB = Path(os.environ["APPDATA"]) / "KnowledgeStation" / "database" / "knowledge.db"
SUFFIX = ".mineru-4.0.10-vlm"
STD_RE = re.compile(r"^(GB(?:/T|/Z)?\s*\d+(?:\.\d+)?\s*-\s*\d{4})")


def main() -> int:
    c = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    have_no = {r[0] for r in c.execute("SELECT standard_no FROM doc_meta")}
    have_name = {r[0] for r in c.execute("SELECT standard_name FROM doc_meta")}

    # ---- ① 强制性国标 ----
    pdfs = [p for p in GB_ROOT.rglob("*") if p.suffix.lower() == ".pdf"]
    dirs = [d for d in GB_ROOT.rglob("*") if d.is_dir() and d.name.endswith(SUFFIX)]
    with_mj = [d for d in dirs if (d / "middle_json.json").exists()]
    matched, no_match, already = [], [], []
    for d in with_mj:
        stem = d.name[: -len(SUFFIX)]
        m = STD_RE.match(stem)
        if not m:
            no_match.append(stem[:60])
            continue
        # 该 pdf 是否存在（run_full_ingest 需要 pdf_path 取 hash 与页几何）
        pdf = next((p for p in pdfs if p.stem == stem), None)
        if pdf is None:
            no_match.append(stem[:60] + "  (缺 PDF)")
            continue
        no = re.sub(r"\s+", " ", m.group(1)).strip()
        item = {"std_no": no, "name": stem[m.end():].strip() or no, "pdf": str(pdf),
                "product_dir": str(d)}
        (already if no in have_no else matched).append(item)
    print("=== ① 强制性国标 ===")
    print(f"    GB 目录 PDF 总数        = {len(pdfs)}")
    print(f"    MinerU 产物目录          = {len(dirs)}")
    print(f"    其中有 middle_json.json  = {len(with_mj)}")
    print(f"    标准号能认出 + PDF 在    = {len(matched) + len(already)}")
    print(f"    **待入库（库里还没有）** = {len(matched)}")
    print(f"    库里已有同标准号（跳过） = {len(already)}")
    print(f"    认不出标准号或无 PDF     = {len(no_match)}  {no_match[:4]}")

    # ---- ② 法律法规 ----
    mds = sorted(LAW_ROOT.rglob("*.md"))
    laws, skipped = [], []
    for p in mds:
        if p.stem in ("README", "_index") or p.name.startswith("_"):
            skipped.append(p.name)
            continue
        name = re.sub(r"\(\d{4}-\d{2}-\d{2}\)$", "", p.stem)
        if name in have_name:
            continue
        laws.append({"name": name, "path": str(p)})
    print("\n=== ② 法律法规 ===")
    print(f"    md 总数                  = {len(mds)}")
    print(f"    排除（README/_index）     = {len(skipped)}")
    print(f"    **待入库（库里还没有）** = {len(laws)}")

    # ---- ④ 量级 ----
    avg_gb, avg_law = 58, 100          # GB 实测中位 58（1014 本回归）；法规实测 ~95-126
    est_clauses = len(matched) * avg_gb + len(laws) * avg_law
    est_min = est_clauses / 65 / 60    # 现役 CPU 嵌入 ~65 条/s
    print("\n=== ④ 量级估算 ===")
    print(f"    预计新增条款 ≈ {est_clauses:,} 条"
          f"（GB {len(matched)}×{avg_gb} + 法规 {len(laws)}×{avg_law}）")
    print(f"    其中**嵌入**是主要耗时：按现役 CPU 65 条/s ⇒ 约 {est_min:.0f} 分钟")
    print(f"    （解析/切分另有开销；PDF 需读入算 hash，{len(matched)} 本）")

    OUT.write_text(json.dumps({
        "why": "全量入库前置清点",
        "gb": {"pdf_total": len(pdfs), "mineru_dirs": len(dirs), "with_middle_json": len(with_mj),
               "to_ingest": len(matched), "already_in_library": len(already),
               "unmatched": no_match[:20]},
        "law": {"md_total": len(mds), "skipped": len(skipped), "to_ingest": len(laws)},
        "estimate": {"clauses": est_clauses, "embed_minutes_cpu": round(est_min, 1)},
        "to_ingest_gb_sample": matched[:5], "to_ingest_law_sample": laws[:5],
        "already_sample": [a["std_no"] for a in already[:10]],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
