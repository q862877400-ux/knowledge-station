"""诊断：为什么国标 OCR 入库后**切出的条款太少**。

现象：GB 175-2023 与 GB 1886.104-2024 入库 status=ok，但两本合计只新增 **7 条**。
本脚本对比三件事，定位切分到底漏在哪：
 ① 该本 markdown 里**实际有多少可切分的位置**（`## N`、`## N.N`、行首 `N.N.N`）；
 ② `split_gb_text()` 实际切出多少；
 ③ `split_law_text()` 实际切出多少；
 ④（GB 1886.235/256/350 报"未识别到条文"）它们各自切出多少。

只读副本库与源目录；**不写任何东西**。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\25-diagnose-split.py
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
OUT = HERE / "diagnose-split.json"
TRIAL = ROOT / "var" / "tmp" / "ingest-trial" / "data"
sys.path.insert(0, str(ROOT))
os.environ["KS_DATA_DIR"] = str(TRIAL)
os.environ.setdefault("KS_MODELS_DIR", str(Path(os.environ["APPDATA"]) / "KnowledgeStation" / "models"))

GB_ROOT = Path("D:/AI/work space/标准/🇨🇳《国家标准》(35000+ 141G)/GB")
SUFFIX = ".mineru-4.0.10-vlm"
DB = TRIAL / "database" / "knowledge.db"

HEAD_NUM = re.compile(r"^#{1,6}\s*(\d+(?:\.\d+){0,3})\s", re.M)      # ## 1 / ## 1.1
HEAD_NUM_DOTTED = re.compile(r"^#{1,6}\s*(\d+\.\d+(?:\.\d+){0,3})\s", re.M)   # ## 1.1（带点）
LINE_NUM = re.compile(r"^\s*(\d+(?:\.\d+){1,3})\s+\S", re.M)          # 1.2.1 正文
ALL_NUM_LINES = re.compile(r"^\s*#{0,6}\s*(\d+(?:\.\d+){0,3})\s+\S", re.M)    # 任意行首数字


def main() -> int:
    from src.core.ingestion.law_text import split_gb_text, split_law_text

    c = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    rows = c.execute(
        "SELECT doc_id, standard_no, standard_name FROM doc_meta"
        " WHERE file_path LIKE 'mineru-ocr://%'").fetchall()
    print(f"[diag] 副本里本次入的 OCR 国标：{len(rows)} 本")
    for did, no, nm in rows:
        tcs = c.execute("SELECT COUNT(*) FROM clause_revision WHERE doc_id=?", (did,)).fetchone()[0]
        print(f"    {no:20s} {nm[:34]:34s} 库中条数 = {tcs}")
        for cid, cn, ct in c.execute(
                "SELECT clause_revision_id, clause_number, substr(content_text,1,70)"
                " FROM clause_revision WHERE doc_id=? LIMIT 6", (did,)):
            print(f"         [{cn}] {ct.replace(chr(10),' ')[:70]}")

    # 逐本对比：markdown 的可切分位置 vs 两个切分函数
    print("\n[diag] 切分函数对比（用源 markdown 直接跑）")
    dirs = [d for d in GB_ROOT.rglob("*") if d.is_dir() and d.name.endswith(SUFFIX)
            and (d / "markdown.md").exists()]
    probe = []
    for d in dirs[:12]:
        t = (d / "markdown.md").read_text(encoding="utf-8", errors="ignore")
        n_head_any = len(HEAD_NUM.findall(t))
        n_head_dotted = len(HEAD_NUM_DOTTED.findall(t))
        n_line = len(LINE_NUM.findall(t))
        n_all = len(ALL_NUM_LINES.findall(t))
        gb = split_gb_text(t)
        law = split_law_text(t)
        probe.append({"dir": d.name[:56], "head_any": n_head_any, "head_dotted": n_head_dotted,
                      "line_num": n_line, "all_num_lines": n_all,
                      "split_gb": len(gb), "split_law": len(law)})
        print(f"    {d.name[:44]:44s} 可切位点 {n_all:4d} (标题带点 {n_head_dotted:3d})  "
              f"⇒ split_gb {len(gb):4d}  split_law {len(law):3d}")

    OUT.write_text(json.dumps({
        "why": "诊断国标 OCR 入库后条款数过少的原因",
        "docs_in_trial": [{"doc_id": a, "standard_no": b, "name": c} for a, b, c in rows],
        "probe": probe,
        "boundary": ["只读；切分函数用源 markdown 直接调用，未写库。"],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    c.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
