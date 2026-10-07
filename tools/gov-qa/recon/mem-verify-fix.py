"""核对修好后的 mem 抽取质量（不写盘，直接打印）。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
sys.path.insert(0, str(HERE.parent))

from adapters import load  # noqa: E402


def main() -> int:
    import httpx

    with httpx.Client(timeout=40, follow_redirects=True, trust_env=False,
                      headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}) as cli:
        class W:
            def __call__(self, url, **kw):
                return cli.get(url, **kw)

            def post(self, url, **kw):
                return cli.post(url, **kw)

        rows = load("mem").harvest(W(), limit=3)
    out = HERE / "mem-fixed-sample.txt"
    with out.open("w", encoding="utf-8") as f:
        f.write(f"共 {len(rows)} 条\n\n")
        for r in rows:
            f.write(f"id={r['id']}\ndept={r['dept']} asked={r['asked_at']} answered={r['answered_at']}\n")
            f.write(f"问: {(r['question'] or '')[:150]}\n")
            f.write(f"答: {(r['answer'] or '')[:300]}\n\n")
    print("written", out, "rows", len(rows))
    return 0


if __name__ == "__main__":
    main()
