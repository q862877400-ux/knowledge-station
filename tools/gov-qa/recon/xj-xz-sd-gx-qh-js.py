"""抓 JS 与明细样本：青海/广西/新疆/山东。"""
from __future__ import annotations

import os
import re
import sys
import time

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx  # noqa: E402

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
HERE = os.path.dirname(os.path.abspath(__file__))
PAUSE = 1.5

TARGETS = [
    ("qh-wsxf-detail.html", "http://www.qinghai.gov.cn/zmhd/system/2026/09/09/030108167.shtml"),
    ("qh-bmwd-detail.html", "http://www.qinghai.gov.cn/msfw/system/2026/01/13/030090689.shtml"),
    ("qh-count.js", "http://www.qinghai.gov.cn/zmhd/system/count/0005002/000000000000/count_page_list_0005002000000000000.js"),
    ("gx-api_mailbox.js", "http://www.gxzf.gov.cn/jsq/2023gxzf/api_mailbox.js"),
    ("xj-queryLetter.js", "http://wsxf.xjxfj.gov.cn/html/js/queryLetter.js"),
    ("xj-index.js", "http://wsxf.xjxfj.gov.cn/html/js/index.js"),
    ("sd-sd_hd.js", "http://www.shandong.gov.cn/images/45409/sd_hd.js"),
    ("sd-ListDxal.html", "http://www.shandong.gov.cn/12345/szfwz/ListDxal.aspx"),
    ("sd-listworkloadzsk.html", "http://www.shandong.gov.cn/12345/szfwz/listworkloadzsk.aspx"),
]


def get(url):
    with httpx.Client(timeout=30, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False) as c:
        return c.get(url)


def main() -> int:
    for name, url in TARGETS:
        try:
            r = get(url)
        except Exception as e:  # noqa: BLE001
            print(f"\n== {name} ==  {url}\n  {type(e).__name__}: {e}")
            time.sleep(PAUSE)
            continue
        txt = r.text or ""
        with open(os.path.join(HERE, name), "w", encoding="utf-8") as f:
            f.write(txt)
        print(f"\n== {name} ==  HTTP {r.status_code}  len={len(txt)}  final={r.url}")
        time.sleep(PAUSE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
