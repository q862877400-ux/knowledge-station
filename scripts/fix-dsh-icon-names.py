# -*- coding: utf-8 -*-
"""把 plugin/client/*.tsx 里的旧图标名批量替换成新版 DSH 的 OutlineRegular 名。

规则来自 scripts/map-dsh-icons.py 的实测映射（17/17 一对一、零歧义）：
    Icon<Base>Outline14|16  ->  Icon<Base>OutlineRegular
只改标识符，不碰 import 路径（顶层 index.js 直接定义，路径不变）。
替换后**逐文件回读校验**，并打印 diff 摘要。
"""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(r"D:\AI\work space\zcode")
CLIENT = REPO / "plugin" / "client"
PAT = re.compile(r"\bIcon([A-Za-z0-9]+?)Outline(?:14|16)\b")

changed_files = 0
total_subs = 0
for tsx in sorted(CLIENT.rglob("*.tsx")):
    src = tsx.read_text(encoding="utf-8", errors="replace")
    new, n = PAT.subn(lambda m: f"Icon{m.group(1)}OutlineRegular", src)
    if n and new != src:
        tsx.write_text(new, encoding="utf-8", newline="")
        changed_files += 1
        total_subs += n
        rel = tsx.relative_to(REPO)
        names = sorted(set(PAT.findall(src)))
        print(f"  {rel}  ({n} 处)")

print(f"\n替换完成：{changed_files} 个文件 / {total_subs} 处")

# 回读校验：不该再有旧名残留
left = []
for tsx in sorted(CLIENT.rglob("*.tsx")):
    txt = tsx.read_text(encoding="utf-8", errors="replace")
    for m in PAT.finditer(txt):
        left.append(f"{tsx.name}:{m.group(0)}")
print(f"残留旧名：{len(left)} 处" + ("" if not left else " ⇒ " + "; ".join(left[:5])))
sys.exit(1 if left else 0)
