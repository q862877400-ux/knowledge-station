# -*- coding: utf-8 -*-
"""定位 '近红外光谱法预测值' 文档，检查 content_text 中 Ĉ/C̄(hat/macron) 是否保留。"""
import sqlite3
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
con = sqlite3.connect(r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db")
con.row_factory = sqlite3.Row
rows = con.execute(
    "SELECT c.doc_id, d.standard_no, c.clause_number, c.content_text "
    "FROM clause_revision c LEFT JOIN doc_meta d ON c.doc_id=d.doc_id "
    "WHERE c.content_text LIKE ? LIMIT 6",
    ("%近红外光谱法预测值%",)).fetchall()
print("命中条款数:", len(rows))
for r in rows:
    print("STANDARD:", r["standard_no"], "| doc:", r["doc_id"], "| clause:", r["clause_number"])
    # 打印含 '预测值' 的行
    for ln in (r["content_text"] or "").split("\n"):
        if "预测值" in ln or "标准值" in ln or "平均值" in ln:
            print("   line repr:", repr(ln))
con.close()
