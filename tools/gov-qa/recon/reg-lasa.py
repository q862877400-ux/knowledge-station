"""把 xz-lasa 登记进 adapters/__init__.py 的 ADAPTERS 字典。

⚠ 该文件是**多 agent 共享文件**，只做插入，不整体覆盖。
⚠ 按**括号配平**定位 ADAPTERS 字典结尾 —— 按正则找第一个 `}` 会插错位置（实测踩过）。
"""
import io
import re
import sys
from pathlib import Path

INIT = Path(__file__).resolve().parent.parent / "adapters" / "__init__.py"

KEY = "xz-lasa"
ENTRY = ('"xz-lasa": "adapters.xz_lasa",',
         "拉萨市·来信选登（POST api-mailbox/frontMail/mailList，"
         "公开列表含 objectiveType 类型标签）")


def main() -> int:
    s = io.open(INIT, encoding="utf-8").read()
    if f'"{KEY}"' in s:
        print("已登记过，跳过")
        return 0

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

    k, note = ENTRY
    block = ["    # —— 西藏（2026-10-10，补 none 单元）：省级信访需登录已判死，",
             "    #    但**拉萨市**这个接口是公开的 ⇒ 省级不行 ≠ 地市级也不行。",
             f"    {k:<34s} # {note}", ""]
    s2 = s[:pos] + "\n".join(block) + s[pos:]
    io.open(INIT, "w", encoding="utf-8").write(s2)
    print(f"已插入 {KEY}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
