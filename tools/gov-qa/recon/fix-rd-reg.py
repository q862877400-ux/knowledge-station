"""修正 rd-* 登记位置 —— 上一次误插进了 SITE 字典，应插进 ADAPTERS 字典。

做法：按行过滤掉误插块，再用**括号配平**定位 ADAPTERS 字典的结尾，插在那里。
"""
import io
import re
import sys
from pathlib import Path

INIT = Path(__file__).resolve().parent.parent / "adapters" / "__init__.py"

BLOCK_HEAD = "# —— 人大系统（2026-10-10，M4）"
RD_KEYS = ('"rd-hn"', '"rd-sd"', '"rd-js"', '"rd-gd"')

ENTRIES = [
    ('"rd-hn": "adapters.rd_hn",',
     "河南省人大·法规草案征求意见（列表+详情，正文为草案全文）"),
    ('"rd-sd": "adapters.rd_sd",',
     "山东省人大·法规草案征求意见"),
    ('"rd-js": "adapters.rd_js",',
     "江苏省人大·法规草案征求意见（分页 index_N.shtml）"),
    ('"rd-gd": "adapters.rd_gd",',
     "广东省人大·法规草案征求意见（分页 index_N.html）"),
]


def main() -> int:
    lines = io.open(INIT, encoding="utf-8").read().splitlines(keepends=True)

    # ① 删掉误插块（从 BLOCK_HEAD 行到最后一个 rd-* 行，含紧随的空行）
    out, i, removed = [], 0, 0
    while i < len(lines):
        if BLOCK_HEAD in lines[i]:
            j = i
            while j < len(lines) and not any(k in lines[j] for k in RD_KEYS):
                j += 1
            j += 1                                   # 含 rd-gd 行
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            removed += j - i
            i = j
            continue
        out.append(lines[i])
        i += 1
    print(f"① 删除误插块 {removed} 行")

    s = "".join(out)

    # ② 用括号配平找 ADAPTERS 字典的结尾
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
    print(f"② ADAPTERS 字典结尾在第 {s[:pos].count(chr(10)) + 1} 行")

    block = ["    # —— 人大系统（2026-10-10，M4）：法规草案征求意见。",
             "    #    ⚠ 体裁是「草案全文 + 征求意见公告」，**不是问答** ⇒",
             "    #      记录带 extra.content_kind=\"立法征求意见\" 以与问答语料区分。",
             "    #    基座 adapters/rd_common.py（正则配置驱动，新增省份只需加一条配置）。"]
    for key, note in ENTRIES:
        block.append(f"    {key:<34s} # {note}")
    block.append("")

    s2 = s[:pos] + "\n".join(block) + s[pos:]
    io.open(INIT, "w", encoding="utf-8").write(s2)
    print(f"③ 已插入 {len(ENTRIES)} 条到 ADAPTERS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
