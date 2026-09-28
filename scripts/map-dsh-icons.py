# -*- coding: utf-8 -*-
"""把本仓 tsx 里引用的 Icon* 逐个映射到新版 DSH ui-primitives 的真实导出。

背景：DSH 升级后 Icon*Outline16 → Icon*OutlineRegular/Medium，且可能搬到 icons 子模块。
不猜、不逐个试：直接从新版的 lib/types/icons/index.js 抽全部导出名，做对照表。
"""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = Path(r"D:\AI\work space\zcode")
DSH = Path(r"D:\AI\DSH\deepseek-harness\packages\client\ui-primitives")
ICON_INDEX = DSH / "lib" / "types" / "icons" / "index.js"
ROOT_INDEX = DSH / "lib" / "index.js"

# 1) 本仓引用了哪些图标
used: set[str] = set()
for tsx in sorted((REPO / "plugin" / "client").rglob("*.tsx")):
    used |= set(re.findall(r"\bIcon[A-Za-z0-9]+Outline\d+\b", tsx.read_text(encoding="utf-8", errors="replace")))

# 2) 新版有哪些导出
exports: set[str] = set()
if ICON_INDEX.exists():
    exports |= set(re.findall(r"export const (Icon[A-Za-z0-9]+)", ICON_INDEX.read_text(encoding="utf-8", errors="replace")))
if ROOT_INDEX.exists():
    exports |= set(re.findall(r"\b(Icon[A-Za-z0-9]+Outline(?:Regular|Medium))\b", ROOT_INDEX.read_text(encoding="utf-8", errors="replace")))

print(f"本仓引用图标 {len(used)} 个 / 新版可用导出 {len(exports)} 个\n")
print(f"{'本仓引用(旧名)':<32}{'状态':<10}新版的对应名")
print("-" * 92)
missing = []
for name in sorted(used):
    base = re.sub(r"Outline\d+$", "", name)  # IconClockOutline16 -> IconClock
    cands = [c for c in exports if base in c]
    if cands:
        cands.sort()
        mark = "有"
        print(f"{name:<32}{mark:<10}{', '.join(cands[:3])}")
    else:
        missing.append(name)
        print(f"{name:<32}{'❌ 缺失':<10}（基础名 {base} 在新版找不到）")

print()
if missing:
    print(f"⚠ {len(missing)} 个在新版**完全找不到**（不是改名、是被删或换了基础名）：")
    for m in missing:
        print("   ", m)
else:
    print("✅ 全部图标在新版都有对应（只是改了命名规则）")
