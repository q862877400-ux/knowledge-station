"""上海/浙江适配器实测：用 harvest.py 同款 _Fetcher 跑 harvest(limit=3) 并打印记录。

用法：python recon/sh-zj-verify.py [sh|zj|both]
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ADIR = HERE.parent / "adapters"
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, ADIR / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Fetcher:
    def __init__(self, c):
        self._c = c

    def __call__(self, url, **kw):
        return self._c.get(url, **kw)

    def post(self, url, **kw):
        return self._c.post(url, **kw)


def main() -> int:
    import httpx
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    names = {"sh": ["sh_12345"], "zj": ["zj_mhww"],
             "both": ["sh_12345", "zj_mhww"]}[which]
    with httpx.Client(timeout=40, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False) as cli:
        f = _Fetcher(cli)
        for name in names:
            mod = load(name)
            print(f"\n===== {name} ({mod.SITE['key']}) =====")
            rows = mod.harvest(f, limit=3)
            print(f"  取到 {len(rows)} 条")
            for r in rows:
                print("  ·", (r["question"] or "")[:70].replace("\n", " "))
                print("    →", (r["answer"] or "")[:90].replace("\n", " "))
                print("     dept=", r["dept"], "| asked=", r["asked_at"],
                      "| answered=", r["answered_at"], "| id=", r["id"])
            if rows:
                print("  JSON keys:", list(rows[0].keys()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
