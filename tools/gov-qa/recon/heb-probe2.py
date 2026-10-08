"""河北 阶段二：探信访来信查询 + 12345 SPA。"""
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

TARGETS = [
    ("heb-wsxf", "https://wsxf.hebxfj.gov.cn/mail/views/wyxx.html?id=71"),
    ("heb-12345-root", "https://hb12345.szj.hebei.gov.cn/ticket/zwpage/"),
    ("heb-12345-index", "https://hb12345.szj.hebei.gov.cn/ticket/zwpage/index.html"),
]


def main() -> int:
    with httpx.Client(timeout=40, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False) as cli:
        for name, url in TARGETS:
            try:
                r = cli.get(url)
            except Exception as e:  # noqa: BLE001
                print(f"[{name}] {url} -> {type(e).__name__}: {e}")
                continue
            body = r.text or ""
            (HERE / f"{name}.html").write_text(body, encoding="utf-8", errors="replace")
            print(f"[{name}] {url} -> {r.status_code} {len(body)}B "
                  f"ct={r.headers.get('content-type','')}")
            if r.status_code == 200:
                scripts = re.findall(r'<script[^>]+src="([^"]+)"', body)
                for s in scripts[:20]:
                    print(f"    SCRIPT {s}")
                links = re.findall(r'<a [^>]*href="([^"]+)"[^>]*>([^<]{2,40})</a>', body)
                for u, t in links[:10]:
                    print(f"    LINK {t.strip()!r:24s} {u}")
            time.sleep(PAUSE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
