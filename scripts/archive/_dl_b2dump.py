# -*- coding: utf-8 -*-
"""打印第4页所有文本块/行的完整拼接文本，定位 '1 范围' 的 '1' 是否被拆到别的块/行。"""
import sys
import fitz

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
pdf = sys.argv[1]
page_no = int(sys.argv[2]) - 1 if len(sys.argv) > 2 else 3
d = fitz.open(pdf)
page = d[page_no]
data = page.get_text("dict")
d.close()
print("==== 第", page_no + 1, "页 各块完整行文本 ====")
for bi, b in enumerate(data["blocks"]):
    if b.get("type") != 0:
        continue
    for li, line in enumerate(b.get("lines", [])):
        spans = line.get("spans", [])
        txt = "".join(sp.get("text", "") for sp in spans)
        print("b%d l%d: %r" % (bi, li, txt))
