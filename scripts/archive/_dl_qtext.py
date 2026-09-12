# -*- coding: utf-8 -*-
"""查目标条款 content_text，定位数字/字母是否在入库时丢失。"""
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
db = r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db"
doc = sys.argv[1] if len(sys.argv) > 1 else "doc_01M1FS1P5YZ3SR9TCWBR0T8NCY"

con = sqlite3.connect(db)
con.row_factory = sqlite3.Row
rows = con.execute(
    'SELECT clause_number, content_text FROM clause_revision '
    'WHERE doc_id=? AND clause_number IN (?,?,?,?) ORDER BY clause_number',
    (doc, "1", "2", "3.1", "4.1")).fetchall()
for r in rows:
    print("==== 条款", r["clause_number"], "====")
    print(r["content_text"][:600])
    print()
con.close()
