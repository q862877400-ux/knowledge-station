"""抓单页原始 HTML 并打印含指定关键词的 JS 片段（用于看清 IGI 列表函数真实参数）。

用法：python recon/province-platform-hunt-raw.py <out.html> <url> <关键词1> [关键词2 ...]
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")


def main() -> int:
    import httpx
    out, url = sys.argv[1], sys.argv[2]
    keys = sys.argv[3:]
    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=20, follow_redirects=True) as c:
        r = c.get(url)
    html = r.text or ""
    (HERE / out).write_text(html, encoding="utf-8")
    print(f"[raw] {url} -> {out}  status={r.status_code} len={len(html)}")
    blocks = re.findall(r"<script[^>]*>(.*?)</script>", html, re.S | re.I)
    for i, b in enumerate(blocks):
        if any(k in b for k in keys):
            print(f"\n===== script block {i} (matched) =====")
            print(b[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
