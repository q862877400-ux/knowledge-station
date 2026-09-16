# -*- coding: utf-8 -*-
"""校验刚生成的知识库备份（只读）。"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
p = sorted(Path("var/ocr-loop/backups").glob("knowledge-*.db"))[-1]
c = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
print("file =", p.name, round(p.stat().st_size / 1048576, 1), "MB")
print("quick_check =", c.execute("pragma quick_check").fetchone()[0])
tabs = [r[0] for r in c.execute(
    "select name from sqlite_master where type='table' order by name")]
print("tables =", len(tabs))
for t in ("doc_meta", "clause_revision", "clauses"):
    if t in tabs:
        n = c.execute(f"select count(*) from {t}").fetchone()[0]
        print(f"  {t}: {n}")
print("all =", tabs)
c.close()
