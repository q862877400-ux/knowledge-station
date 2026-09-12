# -*- coding: utf-8 -*-
"""读某对比目录 manifest 的 doc_id，并列出条款（若带参数 out_dir）。"""
import re
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
out_dir = sys.argv[1]
doc = None
for line in (Path(out_dir) / "manifest.json").read_bytes().decode("utf-8", errors="replace").splitlines():
    m = re.search(r'"doc_id": "([^"]+)"', line)
    if m:
        doc = m.group(1)
        break
print("doc_id=", doc)
con = sqlite3.connect(r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db")
con.row_factory = sqlite3.Row
rows = con.execute("SELECT clause_number, content_text FROM clause_revision WHERE doc_id=? ORDER BY rowid", (doc,)).fetchall()
print("条款数:", len(rows))
for r in rows[:20]:
    print("[%s] %s" % (r["clause_number"], (r["content_text"] or "").replace("\n", " ")[:64]))
con.close()
