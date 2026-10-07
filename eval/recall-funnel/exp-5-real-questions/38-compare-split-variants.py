"""比三种切法，用**已知真实条数**的法律当裁判 —— 挑最准的再改生产代码。

## 三种候选
 · **A 现状**：`(?=第X条)` —— 任何位置都切（已知多切，引用也切）。
 · **B 只认行首**：`(?=^[ \\t]*(?:\\*\\*)?第X条)` + `re.M`。
 · **C 行首 或 句末标点之后**：`(?=(?:^|(?<=[。！？；\\n]))[ \\t]*(?:\\*\\*)?第X条)` + `re.M`
   —— 兼顾"被折行的条文"（B 会漏掉的那些）。

裁判 = 10 部法律的实际条数（公开事实，不是我定的）。

只读源目录。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\38-compare-split-variants.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = HERE / "compare-split-variants.json"
LAW_ROOT = Path("D:/AI/work space/标准/法律法规")

A = re.compile(r"(?=第[一二三四五六七八九十百千零]+条)")
B = re.compile(r"(?=^[ \t]*(?:\*\*)?第[一二三四五六七八九十百千零]+条)", re.M)
C = re.compile(r"(?=(?:^|(?<=[。！？；\n]))[ \t]*(?:\*\*)?第[一二三四五六七八九十百千零]+条)", re.M)

KNOWN = {"劳动法": 107, "劳动合同法": 98, "行政处罚法": 86, "社会保险法": 98,
         "特种设备安全法": 101, "职业病防治法": 90, "环境保护法": 70, "矿山安全法": 50,
         "刑法": 452, "民法典": 1260}


def main() -> int:
    rows = []
    for p in sorted(LAW_ROOT.rglob("*.md")):
        if p.name.startswith("_") or "案例/" in p.relative_to(LAW_ROOT).as_posix():
            continue
        name = re.sub(r"\(\d{4}-\d{2}-\d{2}\)$", "", p.stem)
        if name not in KNOWN or any(r["name"] == name for r in rows):
            continue
        t = p.read_text(encoding="utf-8", errors="ignore")
        t = re.sub(r"\r\n", "\n", t)
        t = re.sub(r"\*{0,2}(第[一二三四五六七八九十百千零]+条)\*{0,2}", r"\1", t)
        rows.append({"name": name, "真实": KNOWN[name],
                     "A": len(A.split(t)) - 1, "B": len(B.split(t)) - 1, "C": len(C.split(t)) - 1})

    print(f"{'法律':16s} {'真实':>6s} {'A现状':>7s} {'B行首':>7s} {'C行首或句末':>10s}")
    for r in rows:
        print(f"{r['name']:16s} {r['真实']:>6d} {r['A']:>7d} {r['B']:>7d} {r['C']:>10d}")

    def score(k: str) -> tuple[int, float]:
        d = [abs(r[k] - r["真实"]) for r in rows]
        return sum(1 for x in d if x == 0), sum(d) / len(d)

    print()
    for k, label in (("A", "A 现状"), ("B", "B 只认行首"), ("C", "C 行首或句末标点后")):
        ex, mae = score(k)
        print(f"  {label:16s} 完全一致 {ex}/{len(rows)} 部 ；平均偏差 {mae:.1f} 条")
    OUT.write_text(json.dumps({"why": "比三种切法，用已知真实条数当裁判", "rows": rows}, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
