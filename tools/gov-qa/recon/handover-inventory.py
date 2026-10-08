"""交接盘点：注册适配器清单 + 各来源条数 + 关键产物路径，输出给交接文档用。"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
MOD = HERE.parent
DATA = MOD / "data"


def main() -> int:
    init = (MOD / "adapters" / "__init__.py").read_text(encoding="utf-8")
    keys = re.findall(r'^\s*"([A-Za-z0-9\-]+)":\s*"adapters\.', init, re.M)
    print(f"注册适配器 {len(keys)} 个：")
    print("  " + ", ".join(keys))

    files = sorted(DATA.glob("*.jsonl"))
    rows = []
    total = 0
    for f in files:
        n = len([l for l in f.read_text(encoding="utf-8").splitlines() if l.strip()])
        total += n
        rows.append((f.stem, n))
    print(f"\ndata/ 文件 {len(files)} 个，记录 {total} 条")
    print("最大的 10 个来源：")
    for name, n in sorted(rows, key=lambda x: -x[1])[:10]:
        print(f"  {n:6d}  {name}")

    lr = MOD / "locate-rate.json"
    if lr.exists():
        j = json.loads(lr.read_text(encoding="utf-8"))
        a = sum(v.get("可当考卷(A_点名且在我们库)", 0) for v in j["sources"].values())
        b = sum(v.get("补料清单(B_点名但不在库)", 0) for v in j["sources"].values())
        c = sum(v.get("无依据(C_没点名)", 0) for v in j["sources"].values())
        print(f"\nlocate-rate：可当考卷 A={a}，补料 B={b}，无依据 C={c}（库内文档 {j['n_lib_names']} 份）")
    return 0


if __name__ == "__main__":
    main()
