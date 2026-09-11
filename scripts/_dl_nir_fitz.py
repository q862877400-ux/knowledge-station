# -*- coding: utf-8 -*-
"""查 GB/T 34406-2017 原 PDF 文本层中 Ĉ/C̄ (hat/macron) 的实际码位形态。"""
import sqlite3
import sys
import fitz

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
con = sqlite3.connect(r"C:\Users\Zegel\AppData\Roaming\KnowledgeStation\database\knowledge.db")
row = con.execute("SELECT file_path FROM doc_meta WHERE standard_no='GB/T 34406-2017'").fetchone()
con.close()
if not row:
    print("no file_path"); sys.exit(0)
pdf = row[0]
print("pdf:", pdf)
d = fitz.open(pdf)
for i in range(len(d)):
    t = d[i].get_text()
    if "近红外光谱法预测值" in t or "预测值" in t:
        for ln in t.split("\n"):
            if "预测值" in ln or "标准值" in ln or "平均值" in ln:
                print("p%d line repr: %r" % (i + 1, ln))
                for ch in ln:
                    print("   U+%04X %r" % (ord(ch), ch))
d.close()
