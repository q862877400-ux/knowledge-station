# -*- coding: utf-8 -*-
"""重导 GB/T 1031-2009（fitz 文本层）验证表格数值误切修复。"""
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.core.ingestion.pipeline import run_full_ingest

def main():
    pdf = r"D:\AI\work space\标准\🇨🇳《国家标准》(35000+ 141G)\GBT\GBT 00001 - GBT 10000\GB／T 1031-2009 产品几何技术规范（GPS） 表面结构 轮廓法 表面粗糙度参数及其数值.pdf"
    res = run_full_ingest(Path(pdf), "GB/T 1031-2009",
                          "产品几何技术规范（GPS） 表面结构 轮廓法 表面粗糙度参数及其数值",
                          reingest=True, force_deep=False)
    print("ingest:", {k: res.get(k) for k in ("status", "doc_id", "total_clauses")})
    if res.get("doc_id"):
        con = sqlite3.connect(r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db")
        con.row_factory = sqlite3.Row
        rows = con.execute("SELECT clause_number FROM clause_revision WHERE doc_id=? ORDER BY rowid", (res["doc_id"],)).fetchall()
        nums = [r["clause_number"] for r in rows]
        false_nums = [n for n in nums if n in ("12.5", "6.3", "1.6", "3.2")]
        print("条款数:", len(nums))
        print("表格值误切残留([12.5/6.3/1.6/3.2]):", false_nums if false_nums else "无(已修)")
        print("条款号前12:", nums[:12])
        con.close()

if __name__ == "__main__":
    main()
