"""抽验脚本（worker-national 自用）：直接调用 adapters.nat_* 的 harvest，打印前几条。

用法：
    .venv/Scripts/python.exe tools/gov-qa/recon/nat-smoke.py <module> <limit>
例：
    .venv/Scripts/python.exe tools/gov-qa/recon/nat-smoke.py nat_mot 5
"""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOVQA = HERE.parent
sys.path.insert(0, str(GOVQA))
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")

import httpx  # noqa: E402

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")


class F:
    def __init__(self, c):
        self._c = c

    def __call__(self, url, **kw):
        return self._c.get(url, **kw)

    def post(self, url, **kw):
        return self._c.post(url, **kw)


def main() -> int:
    key = sys.argv[1]
    lim = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    mod = importlib.import_module(f"adapters.{key}")
    with httpx.Client(timeout=40, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False) as cli:
        rows = mod.harvest(F(cli), limit=lim)
    print("GOT", len(rows))
    for r in rows[:5]:
        print("-", (r.get("question") or "")[:70])
        print("  A:", (r.get("answer") or "")[:120])
        print("  dept:", r.get("dept"), "| asked:", r.get("asked_at"),
              "| answered:", r.get("answered_at"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
