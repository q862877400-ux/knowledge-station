# -*- coding: utf-8 -*-
"""用 fitz 读 PDF 原始文本层，判断数字/字母是否在源头就错位/缺失。"""
import sys
import fitz

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
pdf = sys.argv[1]
pageno = int(sys.argv[2]) - 1 if len(sys.argv) > 2 else 3  # 第4页 0-based=3
d = fitz.open(pdf)
t = d[pageno].get_text()
d.close()
print("=== 第", pageno + 1, "页 原始文本层（repr 前600） ===")
print(repr(t[:600]))
