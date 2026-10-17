# -*- coding: utf-8 -*-
"""便携化审计·精修版：把「代码里的写死」与「文档里的历史记录」分开。

## 为什么要分

业主目标：**不产生对当前环境有依赖的东西**。

- **代码里的绝对路径** = **真依赖**（换机就坏）⇒ 必须改
- **文档里的绝对路径** = **历史记录**（记的是"当时在哪个路径下发生的"）⇒ 不是依赖，
  改了反而丢证据

⇒ 本脚本只对**代码**下判据，并把代码里命中的位置逐条列出来给人看。
"""
import re
import subprocess
from collections import Counter
from pathlib import Path

REPO = Path(".").resolve()

#: 代码扩展名（真依赖只可能在这些里）
CODE_EXT = {".py", ".ts", ".tsx", ".js", ".mjs", ".cjs", ".ps1", ".psm1", ".sh",
            ".json", ".yml", ".yaml", ".toml", ".cfg", ".ini", ".sql"}
#: 文档扩展名（历史记录）
DOC_EXT = {".md", ".txt"}

PAT = {
    "旧工作区": re.compile(r"[Dd]:[\\/]AI[\\/]work space", re.I),
    "新工作区": re.compile(r"[Dd]:[\\/]Agent-Studio", re.I),
    "用户名 Zegel": re.compile(r"Zegel", re.I),
    "本机 uv python": re.compile(r"AppData[\\/]Roaming[\\/]uv", re.I),
    "用户 AppData": re.compile(r"[Cc]:[\\/]Users[\\/]Zegel[\\/]AppData", re.I),
}

files = subprocess.run(["git", "ls-files"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace").stdout.splitlines()

code_hits: dict[str, list[tuple[str, str]]] = {}
doc_count: Counter = Counter()

#: ⚠ **排除本脚本自己** —— 它里面就写着那些模式串（`D:\AI\work space` 等），
#: 不排除就会**匹配到自己**（实测读数因此 +1：138 → 139）。
_SELF = "scripts/audit-hardcoded-paths.py"

for rel in files:
    if rel == _SELF:
        continue
    p = REPO / rel
    if not p.is_file():
        continue
    ext = p.suffix.lower()
    if ext not in CODE_EXT and ext not in DOC_EXT:
        continue
    try:
        txt = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        continue
    for name, pat in PAT.items():
        found = pat.findall(txt)
        if not found:
            continue
        if ext in DOC_EXT:
            doc_count[name] += len(found)
        else:
            for _ in found:
                code_hits.setdefault(name, []).append((rel, ""))

print("=== ★ 代码里的写死（真依赖，必须改）===")
if not code_hits:
    print("    （无）")
for name in PAT:
    lst = code_hits.get(name, [])
    if not lst:
        continue
    print(f"\n  --- {name}: {len(lst)} 处")
    c = Counter(r for r, _ in lst)
    for f, n in c.most_common(30):
        print(f"      {n:>3}x  {f}")

print()
print("=== 文档里的引用（历史记录，不是依赖）===")
for name in PAT:
    n = doc_count.get(name, 0)
    if n:
        print(f"    {name}: {n} 处")
print()
print("  ⇒ 文档里的**不改**（改了丢证据）。")
