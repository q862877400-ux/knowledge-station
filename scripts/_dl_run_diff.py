# -*- coding: utf-8 -*-
"""对 12 本运行 program_diff 自动对账，列出符号/图/表题注缺失。"""
import sqlite3
import sys
sys.path.insert(0, ".")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from scripts.program_diff import diff  # noqa: E402
from pathlib import Path

con = sqlite3.connect(r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db")
con.row_factory = sqlite3.Row
books = ["GB/T1000-2016", "GB/T9278-2008", "GB/T1.1-2020", "GB/T1.2-2020",
         "GB/T10-2013", "GB/T10000-2023", "GB/T1003-2016", "GB/T1008-2008",
         "GB/T1019-2008", "GB/T1028-2018", "GB/T1029-2021", "GB/T1031-2009"]
for std in books:
    r = None
    for cand in (std, std.replace("GB/T", "GB/T ")):
        r = con.execute("SELECT doc_id, file_path FROM doc_meta WHERE standard_no=? ORDER BY rowid DESC LIMIT 1", (cand,)).fetchone()
        if r:
            break
    if not r or not r["file_path"]:
        print(std, "-> no doc/path")
        continue
    try:
        res = diff(Path(r["file_path"]), r["doc_id"])
        print("%-16s 图缺=%s 表缺=%s 符号缺=%s" % (
            std, res["missing_figs"], res["missing_tabs"], res["missing_syms"]))
    except Exception as e:
        print(std, "-> err", str(e)[:80])
con.close()
