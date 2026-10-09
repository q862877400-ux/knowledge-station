"""诊断 nat-mohurd 剩余 2 条 id 碰撞 —— 看它们到底差在哪个字段。"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
p = next((ROOT / "data").glob("nat-mohurd-*.jsonl"))
rows = []
for line in open(p, encoding="utf-8", errors="replace"):
    if line.strip() and line.lstrip().startswith("{"):
        try:
            rows.append(json.loads(line))
        except Exception:
            pass

from collections import Counter
c = Counter(str(r.get("id")) for r in rows)
dups = [k for k, v in c.items() if v > 1]
print(f"文件 {p.name}：{len(rows)} 行，{len(c)} 唯一，碰撞 {len(dups)} 组")

for d in dups:
    same = [r for r in rows if str(r.get("id")) == d]
    print(f"\n--- id={d} 出现 {len(same)} 次 ---")
    for i, r in enumerate(same):
        print(f"  [{i}] q={len(r.get('question') or '')}字 a={len(r.get('answer') or '')}字 "
              f"asked={r.get('asked_at')} dept={r.get('dept')}")
        print(f"      q前40: {(r.get('question') or '')[:40]!r}")
    # 逐字段比对
    keys = set().union(*(set(r.keys()) for r in same))
    for k in sorted(keys):
        vals = {json.dumps(r.get(k), ensure_ascii=False) for r in same}
        if len(vals) > 1:
            print(f"      ★ 字段 {k} 不同：{[v[:60] for v in vals]}")
