# -*- coding: utf-8 -*-
"""查某文档条款的 figure_html，看扫描件图 asset 是否注入。"""
import re
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
con = sqlite3.connect(r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db")
con.row_factory = sqlite3.Row
rows = con.execute(
    "SELECT clause_number, figure_html FROM clause_revision WHERE doc_id=? "
    "AND figure_html IS NOT NULL AND figure_html != '' ORDER BY rowid",
    (sys.argv[1],)).fetchall()
print("含 figure_html 的条款数:", len(rows))
for r in rows:
    assets = re.findall(r'data-asset="([^"]+)"', r["figure_html"] or "")
    caps = re.findall(r'alt="([^"]*)"', r["figure_html"] or "")
    print("[%s] assets=%d %s" % (r["clause_number"], len(assets),
                                 [a[:12] for a in assets[:5]]))
# 看5.4/5章等是否有图
rows2 = con.execute(
    "SELECT clause_number, figure_html FROM clause_revision WHERE doc_id=? "
    "AND (clause_number LIKE '5%' OR clause_number LIKE '6%' OR clause_number LIKE 'A%' OR clause_number LIKE '附%') "
    "ORDER BY rowid", (sys.argv[1],)).fetchall()
print("---- 5.x/A/附录 条款 figure_html 概览 ----")
for r in rows2:
    fh = r["figure_html"] or ""
    print("[%s] figlen=%d assets=%d" % (r["clause_number"], len(fh), fh.count("data-asset")))
con.close()
