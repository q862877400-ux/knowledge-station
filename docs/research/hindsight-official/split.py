# -*- coding: utf-8 -*-
"""把 llms-full.txt 按 '## File: xxx' 切成 39 个文件，便于逐篇读。"""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SRC = Path(r"C:\Users\Zegel\AppData\Local\Temp\hs-docs2\llms-full.txt")
OUT = Path(r"C:\Users\Zegel\AppData\Local\Temp\hs-docs2\split")
OUT.mkdir(parents=True, exist_ok=True)

text = SRC.read_text(encoding="utf-8", errors="replace")
parts = re.split(r"^## File: ", text, flags=re.M)
print(f"切出 {len(parts)-1} 篇\n")
rows = []
for p in parts[1:]:
    name, _, body = p.partition("\n")
    name = name.strip()
    safe = name.replace("/", "__")
    f = OUT / safe
    f.write_text(body, encoding="utf-8")
    rows.append((name, len(body), body.count("\n")))

for n, c, l in sorted(rows, key=lambda x: -x[1]):
    print(f"  {c:>7,} 字符 {l:>5} 行   {n}")
print(f"\n输出目录: {OUT}")
