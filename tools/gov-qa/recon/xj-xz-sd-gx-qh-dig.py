"""深挖鲁/桂/青/新/藏 候选互动栏目页，存原始 HTML 并扫描问答/接口线索。"""
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

KW = re.compile(r"(hdjl|zmhd|12345|互动|问答|留言|信访|咨询|mailbox|guizaiwen|bmwd|wsxf|"
                r"\.action|\.do\b|api/|Ajax|ajax|json|list|page|pageIndex|dataproxy)", re.I)
A_RE = re.compile(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.S | re.I)
JS_RE = re.compile(r'(?:src|href)="([^"]+\.js[^"]*)"', re.I)
TAG = re.compile(r"<[^>]+>")

PAGES = [
    ("sd-col94092.html", "http://www.shandong.gov.cn/col/col94092/index.html"),
    ("sd-12345.html", "http://www.shandong.gov.cn/12345/default.aspx"),
    ("gx-hdjl.html", "http://www.gxzf.gov.cn/hdjl/"),
    ("gx-mailbox.html", "http://www.gxzf.gov.cn/hdjl/mailbox/index.shtml"),
    ("gx-guizaiwen.html", "http://www.gxzf.gov.cn/hdjl/guizaiwen/index.shtml"),
    ("qh-zmhd.html", "http://www.qinghai.gov.cn/zmhd/index.html"),
    ("qh-wsxf.html", "http://www.qinghai.gov.cn/zmhd/wsxf/index.html"),
    ("qh-bmwd.html", "http://www.qinghai.gov.cn/msfw/bmwd/index.html"),
    ("xj-onlineILsit.html",
     "http://wsxf.xjxfj.gov.cn/html/onlineInquiry/onlineILsit.jsp?regionCode=650000000000"),
    ("xj-main-index.html", "http://wsxf.xjxfj.gov.cn/html/main/index.jsp?regionCode=650000000000"),
    ("xz-zmhd.html", "http://www.xizang.gov.cn/zmhd/"),
]


def get(url):
    with httpx.Client(timeout=30, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False) as c:
        return c.get(url)


def main() -> int:
    for name, url in PAGES:
        try:
            r = get(url)
        except Exception as e:  # noqa: BLE001
            print(f"\n== {name} ==  {url}\n  {type(e).__name__}: {e}")
            time.sleep(PAUSE)
            continue
        html = r.text or ""
        with open(os.path.join(HERE, name), "w", encoding="utf-8") as f:
            f.write(html)
        print(f"\n== {name} ==  HTTP {r.status_code}  len={len(html)}  final={r.url}")
        print("  -- JS 引用 --")
        for m in sorted(set(JS_RE.findall(html)))[:15]:
            print("    " + m[:110])
        print("  -- 关键词链接 --")
        seen = set()
        for m in A_RE.finditer(html):
            href, txt = m.group(1), re.sub(r"\s+", " ", TAG.sub("", m.group(2))).strip()
            if KW.search(href):
                if href in seen:
                    continue
                seen.add(href)
                print(f"    {txt[:24]:24s}  {href[:110]}")
        time.sleep(PAUSE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
