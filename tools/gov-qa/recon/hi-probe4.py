"""海南 阶段四：抓政策问答明细页，确认答复全文与依据。"""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx  # noqa: E402

HERE = Path(__file__).resolve().parent
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")

DETAILS = [
    "https://www.hainan.gov.cn/hainan/c100551/202610/6dbd72d854e34bddbea62b71e1291bb3.shtml",
    "https://www.hainan.gov.cn/hainan/c100551/202610/395a9576ffef4a8aa48397bf6933a89c.shtml",
]


def main() -> int:
    with httpx.Client(timeout=40, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False) as cli:
        for i, url in enumerate(DETAILS):
            r = cli.get(url)
            body = r.text or ""
            (HERE / f"hi-zcwd-detail{i}.html").write_text(body, encoding="utf-8", errors="replace")
            print(f"[{i}] {url} -> {r.status_code} {len(body)}B")
            time.sleep(1.5)
    return 0


if __name__ == "__main__":
    sys.exit(main())
