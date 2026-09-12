# -*- coding: utf-8 -*-
"""查 GB/T 34406-2017 图A.1(散点chart) 的题注/注入/渲染现状。"""
import sqlite3
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
con = sqlite3.connect(r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db")
con.row_factory = sqlite3.Row
doc = "doc_01M1FFN1WE0G3PYHT1MCHBCV8T"
rows = con.execute(
    "SELECT clause_number, content_text, content_markdown, figure_html FROM clause_revision "
    "WHERE doc_id=? AND (content_text LIKE '%图 A%' OR content_text LIKE '%图A%') ORDER BY rowid",
    (doc,)).fetchall()
print("含 图A 的条款数:", len(rows))
for r in rows:
    ct = r["content_text"] or ""
    fh = r["figure_html"] or ""
    print("[%s] figlen=%d assets=%d" % (r["clause_number"], len(fh), fh.count("data-asset")))
    for ln in ct.split("\n"):
        if re.search(r"图\s*A\s*\.?\s*\d", ln):
            print("   内容题注行: %r" % ln[:70])
con.close()
