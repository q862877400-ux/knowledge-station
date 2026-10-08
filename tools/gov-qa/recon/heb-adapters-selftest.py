"""自测：直接 import adapters.heb_szj / heb_czt 调 harvest()（不登记 __init__.py）。

跑法（cwd=仓库根 D:\\AI\\work space\\zcode）：
  D:\\AI\\work space\\zcode\\.venv\\Scripts\\python.exe tools/gov-qa/recon/heb-adapters-selftest.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]              # 仓库根
sys.path.insert(0, str(ROOT / "tools" / "gov-qa"))
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")

import httpx  # noqa: E402
import adapters  # noqa: E402
from adapters import heb_szj, heb_czt  # noqa: E402

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")


class _Fetcher:
    def __init__(self, c):
        self._c = c

    def __call__(self, url, **kw):
        return self._c.get(url, **kw)

    def post(self, url, **kw):
        return self._c.post(url, **kw)


def _safe(s):
    enc = sys.stdout.encoding or "utf-8"
    try:
        return (s or "").encode(enc, "replace").decode(enc, "replace")
    except Exception:                                                       # noqa: BLE001
        return (s or "").encode("ascii", "replace").decode("ascii")


def main():
    with httpx.Client(timeout=40, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False) as cli:
        f = _Fetcher(cli)
        for mod, limit in ((heb_szj, 3), (heb_czt, 3)):
            k = mod.SITE["key"]
            print(f"\n##### {k} (limit={limit}) #####")
            try:
                rows = mod.harvest(f, limit=limit)
            except Exception as e:                                          # noqa: BLE001
                print("  采集异常:", type(e).__name__, e)
                continue
            print(f"  取到 {len(rows)} 条")
            for r in rows:
                print("  · id:", r["id"], "| url:", r["url"])
                print("    Q:", _safe(r["question"])[:70])
                print("    A:", _safe(r["answer"])[:120])
                print("    asked/answered:", r["asked_at"], "/", r["answered_at"],
                      "| dept:", _safe(r["dept"] or ""),
                      "| keys:", sorted(r.keys()))


if __name__ == "__main__":
    main()
