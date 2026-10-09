"""把 rd-* 4 个人大适配器登记进 adapters/__init__.py 的 ADAPTERS 字典。

只插入、不改动其它内容 —— 该文件是**多 agent 共享文件**，不能整体覆盖。
"""
import io
import re
import sys
from pathlib import Path

INIT = Path(__file__).resolve().parent.parent / "adapters" / "__init__.py"

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
    s = io.open(INIT, encoding="utf-8").read()
    if '"rd-hn"' in s:
        print("已登记过，跳过")
        return 0

    # 找 ADAPTERS = { ... } 的结尾 —— 用「最后一个顶格 }」定位
    m = re.search(r"\n(\})\n", s)
    if not m:
        print("找不到 ADAPTERS 字典结尾")
        return 1
    pos = m.start(1)

    block = ["    # —— 人大系统（2026-10-10，M4）：法规草案征求意见。",
             "    #    ⚠ 体裁是「草案全文 + 征求意见公告」，**不是问答** ⇒",
             "    #      记录带 extra.content_kind=\"立法征求意见\" 以与问答语料区分。",
             "    #    基座 adapters/rd_common.py（正则配置驱动，新增省份只需加一条配置）。"]
    for key, note in ENTRIES:
        block.append(f"    {key:<34s} # {note}")
    block.append("")

    s2 = s[:pos] + "\n".join(block) + s[pos:]
    io.open(INIT, "w", encoding="utf-8").write(s2)
    print(f"已插入 {len(ENTRIES)} 条登记")
    return 0


if __name__ == "__main__":
    sys.exit(main())
