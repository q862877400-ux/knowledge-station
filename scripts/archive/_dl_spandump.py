# -*- coding: utf-8 -*-
"""dump fitz get_text('dict') 的 span 原始字符+字体，诊断畸形/错位字符。"""
import sys
import fitz

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
pdf = sys.argv[1]
pageno = int(sys.argv[2]) - 1 if len(sys.argv) > 2 else 3
d = fitz.open(pdf)
page = d[pageno]
data = page.get_text("dict")
d.close()
print("==== 第", pageno + 1, "页 blocks/spans 原始字符 ====")
for bi, b in enumerate(data["blocks"]):
    if b.get("type") != 0:
        continue
    for li, line in enumerate(b.get("lines", [])):
        for si, sp in enumerate(line.get("spans", [])):
            t = sp.get("text", "")
            # 只打含关键字的 span 或含非中文字符的 span
            if any(k in t for k in ("范围", "10kV", "100Hz", "千伏", "Hz", "kV", "简称", ")( ", "(")) or \
               any(ord(c) > 0x2000 for c in t):
                print("b%d l%d s%d font=%s size=%.1f unicode=%s repr=%r" % (
                    bi, li, si, sp.get("font"), sp.get("size"), sp.get("flags"), t))
