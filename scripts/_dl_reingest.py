# -*- coding: utf-8 -*-
"""重导 GB/T 1000-2016，验证文本层保真后 content_text 恢复数字。"""
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.ingestion.pipeline import run_full_ingest  # noqa: E402

def main():
    pdf = r"D:\AI\work space\标准\🇨🇳《国家标准》(35000+ 141G)\GBT\GBT 00001 - GBT 10000\GB／T 1000-2016 高压线路针式瓷绝缘子尺寸与特性.pdf"
    import sys as _s
    force = _s.argv[1] != "deep" if len(_s.argv) > 1 else False  # 默认文本层快路径
    res = run_full_ingest(Path(pdf), "GB/T 1000-2016",
                          "高压线路针式瓷绝缘子尺寸与特性", reingest=True, force_deep=force)
    print("force_deep=", force)
    print("ingest:", {k: res.get(k) for k in ("status", "doc_id", "total_clauses",
                                              "pages_parsed", "span_warning")})
    if res.get("doc_id"):
        doc = res["doc_id"]
        con = sqlite3.connect(r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db")
        con.row_factory = sqlite3.Row
        for no in ("1", "2", "3.1", "4.1"):
            r = con.execute("SELECT content_text FROM clause_revision WHERE doc_id=? AND clause_number=?",
                            (doc, no)).fetchone()
            print("==== 条款", no, "====")
            print(r["content_text"][:450] if r else "(none)")
            print()
        con.close()


if __name__ == "__main__":
    main()
