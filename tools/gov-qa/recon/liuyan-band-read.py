"""把 fid 分层扫描结果写成可读清单（供人工核对层级归属）。"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BAND = HERE / "liuyan-fid-band-scan.json"
OUT = HERE / "liuyan-band-read.txt"


def main() -> int:
    rows = json.loads(BAND.read_text(encoding="utf-8"))
    with OUT.open("w", encoding="utf-8") as f:
        f.write("fid | 条数 | 归属链 | 承办单位\n")
        for r in rows:
            p = " > ".join(str(x) for x in (r.get("p") or [])) or "-"
            f.write(f"{r['fid']} | {r.get('n', r.get('status'))} | {p} | "
                    f"{r.get('forum') or '-'}\n")
    print("written", OUT)
    return 0


if __name__ == "__main__":
    main()
