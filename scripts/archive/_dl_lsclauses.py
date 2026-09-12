# -*- coding: utf-8 -*-
"""列出某文档全部条款号 + 前80字，诊断条款缺失。"""
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
con = sqlite3.connect(r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db")
con.row_factory = sqlite3.Row
rows = con.execute(
    "SELECT clause_number, content_text FROM clause_revision WHERE doc_id=? "
    "ORDER BY rowid", (sys.argv[1],)).fetchall()
print("条款数:", len(rows))
for r in rows:
    print("[%s] %s" % (r["clause_number"], (r["content_text"] or "").replace("\n", " ")[:70]))
con.close()
