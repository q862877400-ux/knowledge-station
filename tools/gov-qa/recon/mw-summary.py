r"""按省汇总 `recon/city-middleware.json` 的中间件归类 —— 挑下一批要打的市。

## 为什么

`probe-city-middleware.py` 已经把所有零记录市门户按中间件分了组，
但只打印了**全局**汇总。要决定「下一批打哪几个市」，
需要看**每个省**内部有多少市共用同一套中间件 ——
**同省同中间件 = 一个适配器覆盖一片**。

## 用法

```bash
.venv/Scripts/python.exe tools/gov-qa/recon/mw-summary.py
.venv/Scripts/python.exe tools/gov-qa/recon/mw-summary.py --province 河南省
```

只读，不落盘。
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
MW = HERE / "city-middleware.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mw", default=str(MW))
    ap.add_argument("--province", default="")
    args = ap.parse_args()

    d = json.loads(Path(args.mw).read_text(encoding="utf-8"))

    by_prov: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for city, v in d.items():
        mw = "+".join(v.get("middleware") or []) or "（未识别）"
        by_prov[v.get("province") or "?"].append((city, mw))

    out: list[str] = []
    if args.province:
        rows = by_prov.get(args.province, [])
        out.append(f"{args.province}：{len(rows)} 个市（已探到域名）")
        for city, mw in sorted(rows, key=lambda x: (x[1], x[0])):
            out.append(f"  {city:14s} {mw}")
    else:
        out.append(f"共 {len(d)} 个市；按省汇总（**同省同中间件 = 一个适配器覆盖一片**）")
        out.append("")
        for prov, rows in sorted(by_prov.items(), key=lambda kv: -len(kv[1])):
            cnt = Counter(mw for _, mw in rows)
            top = "、".join(f"{m}×{n}" for m, n in cnt.most_common(3))
            out.append(f"  {prov:16s} {len(rows):3d} 个市  ←  {top}")

    text = "\n".join(out) + "\n"
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
