"""把 dept-hd-dig.json 里各站的互动入口列出来，供挑选下一步适配器目标。"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "dept-hd-dig.json"
OUT = HERE / "dept-hd-links.txt"


def main() -> int:
    rows = json.loads(SRC.read_text(encoding="utf-8"))
    with OUT.open("w", encoding="utf-8") as f:
        for rec in rows:
            f.write(f"\n=== {rec.get('name') or rec.get('url')} "
                    f"[{rec.get('status', rec.get('error'))}] ===\n")
            for u, t in (rec.get("hd_links") or []):
                f.write(f"  · {t} -> {u}\n")
            for s in (rec.get("sub") or []):
                f.write(f"  [子页 {s.get('text')}] {s.get('status')} len={s.get('len')} "
                        f"{s.get('url')}\n")
                for u, t in (s.get("hd_links") or [])[:6]:
                    f.write(f"      · {t} -> {u}\n")
                if s.get("api_hints"):
                    f.write(f"      api: {s['api_hints'][:4]}\n")
    print("written", OUT)
    return 0


if __name__ == "__main__":
    main()
