"""五类能力矩阵（§11.0 R6c）：人可读的"哪一类由谁答、它今天活着吗"。

用法：
    .venv\\Scripts\\python.exe scripts\\answers-matrix.py [--json]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # noqa: UP026

from src.core.storage import channel_repo as cr  # noqa: E402
from src.core.update import channel_answers as ca  # noqa: E402
from src.core.update import channel_probe as cp  # noqa: E402

STATE = {"ok": "🟢", "suspicious": "🟡", "down": "🔴", "unknown": "⚪"}


def main() -> int:
    table = ca.load_answers()
    rows = {r["channel_id"]: r for r in cr.list_channels()}
    targets = cp.load_targets()
    cov = ca.coverage(table)

    if "--json" in sys.argv:
        print(json.dumps({"coverage": cov,
                          "per_class": {c: ca.channels_for(c, table=table) for c in ca.CLASSES}},
                         ensure_ascii=False, indent=2))
        return 0

    print(f"五类能力表：{cov['total']} 条渠道 · 来源 {cov['by_source']} · 置信 {cov['by_confidence']}")
    print(f"每条能答几类：{cov['answers_per_channel']}")
    print()
    for cls in ca.CLASSES:
        ids = ca.channels_for(cls, table=table)
        print(f"【{cls}】{len(ids)} 条渠道能答")
        for cid in ids:
            r = rows.get(cid) or {}
            flag = STATE.get(str(r.get("state")), "?")
            probe = "有探针" if cid in targets else "无探针"
            conf = (table[cid].get("confidence") or "")[:6]
            print(f"   {flag} {cid:<52} {probe:<6} {conf:<7} {str(r.get('name'))[:26]}")
        print()
    print("⚠ 读法：🟢 只是「探针没判死」，不等于「这一类真能答」——答案质量要看 basis 与适配器解析。")
    print("⚠ `无探针` 的渠道今天**没有可达性证据**（tool 类与部分 internal），别当成可用。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
