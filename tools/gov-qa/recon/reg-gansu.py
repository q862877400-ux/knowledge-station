"""登记 `gs-tianshui`（并行 agent 已写模块但未注册）。

⚠ `adapters/__init__.py` 是**多 agent 共享文件** —— 只插入，不整体覆盖。
⚠ 按**括号配平**定位 ADAPTERS 字典结尾（按正则找第一个 `}` 会插错位置，实测踩过）。
"""
import io
import re
import sys
from pathlib import Path

INIT = Path(__file__).resolve().parent.parent / "adapters" / "__init__.py"

ENTRIES = [
    ('"gs-tianshui": "adapters.gs_tianshui",',
     "天水市·政民互动（万户 leadermail，4 栏聚合列表 ≈2444 条）"),
    ('"gs-linxia": "adapters.gs_linxia",',
     "临夏州·政民互动"),
]


def main() -> int:
    s = io.open(INIT, encoding="utf-8").read()

    m = re.search(r"ADAPTERS:\s*dict\[str,\s*str\]\s*=\s*\{", s)
    if not m:
        print("找不到 ADAPTERS 字典")
        return 1
    start = m.end() - 1
    depth, pos = 0, start
    while pos < len(s):
        if s[pos] == "{":
            depth += 1
        elif s[pos] == "}":
            depth -= 1
            if depth == 0:
                break
        pos += 1
    if depth != 0:
        print("括号未配平")
        return 1

    added = []
    block = []
    for k, note in ENTRIES:
        key = k.split('"')[1]
        if f'"{key}"' in s:
            print(f"  {key} 已登记，跳过")
            continue
        if not (Path(__file__).resolve().parent.parent / "adapters" /
                (key.replace("-", "_") + ".py")).exists():
            print(f"  {key} 模块不存在，跳过")
            continue
        block.append(f"    {k:<36s} # {note}")
        added.append(key)

    if not added:
        print("无需插入")
        return 0

    block = ["    # —— 甘肃补源（2026-10-10）：省级被 WAF 拦（412），但地市级可用。"] + block + [""]
    s2 = s[:pos] + "\n".join(block) + s[pos:]
    io.open(INIT, "w", encoding="utf-8").write(s2)
    print(f"已插入 {len(added)} 条：{added}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
