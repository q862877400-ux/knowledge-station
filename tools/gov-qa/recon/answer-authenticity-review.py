"""同类风险复查：湖南统一平台 / 广东 hdjlpt 的 answer 字段是不是真官方答复。

动机：留言板把"网友跟帖"当答复（dataType 判错）的教训 ——
**同一种错法要在其他源上主动排查一遍**，不能等它自己暴露。
方法：每个源抽 3 条，导出问答全文，人工看口吻与结构。
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
OUT = HERE / "answer-authenticity-review.txt"

#: 抽取哪些源（各 3 条）
PICK = [
    "hunan-st", "hunan-yj", "gd-st", "gd-amr", "gd-stats", "gd-hr",
    "mee", "mem",
]


def main() -> int:
    lines: list[str] = ["# answer 字段真实性复查（每源抽 3 条）\n"]
    for key in PICK:
        files = list(DATA.glob(f"{key}-*.jsonl"))
        if not files:
            lines.append(f"## {key}: 无文件\n")
            continue
        rows = [json.loads(l) for l in files[0].read_text(encoding="utf-8").splitlines() if l.strip()]
        lines.append(f"\n## {key}（{len(rows)} 条，抽 3）")
        for r in rows[:3]:
            q = (r.get("question") or "").replace("\n", " ")[:110]
            a = (r.get("answer") or "").replace("\n", " ")[:220]
            lines.append(f"  问：{q}")
            lines.append(f"  答：{a}")
            lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("written", OUT)
    return 0


if __name__ == "__main__":
    main()
