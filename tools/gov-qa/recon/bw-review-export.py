"""把部委流 30 条记录的问答导出成文本，人工判定「答复」是不是官方口吻。"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
OUT = HERE / "bw-answers-review.txt"


def main() -> int:
    rows = []
    for p in DATA.glob("people-liuyan-*.jsonl"):
        if "df" in p.name:
            continue
        rows += [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    with OUT.open("w", encoding="utf-8") as f:
        f.write(f"部委流记录 {len(rows)} 条，前 8 条全文：\n\n")
        for i, r in enumerate(rows[:8], 1):
            f.write(f"===== {i}  dept={r.get('dept')}\n")
            f.write(f"url: {r.get('url')}\n")
            f.write(f"问: {(r.get('question') or '').replace(chr(10), ' ')[:150]}\n")
            f.write(f"答: {(r.get('answer') or '').replace(chr(10), ' ')[:260]}\n\n")
    print("written", OUT)
    return 0


if __name__ == "__main__":
    main()
