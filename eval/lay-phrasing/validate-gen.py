import json
from pathlib import Path
D = Path(r"D:\AI\work space\zcode\var\tmp")
def load(p):
    rows = []
    for ln, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line: continue
        try: rows.append(json.loads(line))
        except Exception as e: print(f"  ⚠ {p.name} 第 {ln} 行解析失败: {e}")
    return rows
for name in ("gen-V1", "gen-V2"):
    rows = load(D / f"{name}.jsonl")
    lay = sum(len(r.get("lay") or []) for r in rows)
    kinds = set()
    for r in rows:
        for x in (r.get("lay") or []): kinds.add(type(x).__name__)
    empty = sum(1 for r in rows if not (r.get("lay") or []))
    print(f"{name}: {len(rows)} 条术语 / {lay} 条说法 / lay 元素类型={kinds} / 写空的 {empty} 个")
    for f in ("terms-50.txt","terms-300.txt","terms-500.txt"):
        ts = {l.strip() for l in (D/f).read_text(encoding="utf-8").splitlines() if l.strip()}
        got = {r["term"] for r in rows}
        print(f"    vs {f}: 交集 {len(got & ts)}；本文件独有 {len(got - ts)}；该清单未被覆盖 {len(ts - got)}")
