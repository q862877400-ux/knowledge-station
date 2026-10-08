"""河北 阶段三：抓 JS 找接口路径。"""
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
PAUSE = 1.5

JS = [
    ("heb-wsxf-wyxx.js", "https://wsxf.hebxfj.gov.cn/mail/js/wyxx.js"),
    ("heb-wsxf-djjg.js", "https://wsxf.hebxfj.gov.cn/mail/js/djjg-data.js"),
    ("heb-wsxf-common.js", "https://wsxf.hebxfj.gov.cn/mail/js/common.js"),
    ("heb-12345-index.js", "https://hb12345.szj.hebei.gov.cn/ticket/zwpage/assets/index-DvGATIgw.js"),
]


def main() -> int:
    with httpx.Client(timeout=60, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False) as cli:
        for name, url in JS:
            try:
                r = cli.get(url)
            except Exception as e:  # noqa: BLE001
                print(f"[{name}] {url} -> {type(e).__name__}: {e}")
                continue
            body = r.text or ""
            (HERE / name).write_text(body, encoding="utf-8", errors="replace")
            print(f"[{name}] -> {r.status_code} {len(body)}B")
            # 找接口路径
            paths = set(re.findall(r'["\'`](/[a-zA-Z0-9_\-/]{3,80})["\'`]', body))
            apis = sorted(p for p in paths
                          if any(k in p.lower() for k in
                                 ("api", "ticket", "list", "query", "search", "letter",
                                  "mail", "ask", "wenda", "query", "detail", "page", "wsxf")))
            for p in apis[:60]:
                print(f"    PATH {p}")
            time.sleep(PAUSE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
