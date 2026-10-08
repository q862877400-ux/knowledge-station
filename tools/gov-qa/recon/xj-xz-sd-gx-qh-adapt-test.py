"""直测新适配器（不改 __init__.py）：gx_mailbox / sd_12345 / qh_wsxf。"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOVQA = HERE.parent
sys.path.insert(0, str(GOVQA))

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx  # noqa: E402

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")


class _Fetcher:
    def __init__(self, client):
        self._c = client

    def __call__(self, url, **kw):
        return self._c.get(url, **kw)

    def post(self, url, **kw):
        return self._c.post(url, **kw)


def run(modname, limit):
    mod = __import__(f"adapters.{modname}", fromlist=["harvest"])
    print(f"\n===== {mod.SITE['key']} / {mod.SITE['name']} =====")
    with httpx.Client(timeout=40, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False) as cli:
        t0 = time.perf_counter()
        rows = mod.harvest(_Fetcher(cli), limit=limit)
        dt = time.perf_counter() - t0
    print(f"  => 取到 {len(rows)} 条（{dt:.0f}s）")
    for r in rows[:3]:
        print("   · id=", r["id"], "| dept=", r.get("dept"), "| at=", r.get("answered_at"))
        print("     Q:", (r.get("question") or "")[:70])
        print("     A:", (r.get("answer") or "")[:90])


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    lim = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    for m in (["xj_dchs", "gx_mailbox", "sd_12345", "qh_wsxf"] if which == "all" else [which]):
        try:
            run(m, lim)
        except Exception as e:  # noqa: BLE001
            print(f"  [{m}] 失败 {type(e).__name__}: {e}")
