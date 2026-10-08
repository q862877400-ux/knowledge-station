"""抓鲁/桂/青门户首页 + 新疆/西藏信访页原始 HTML，打印互动/问答相关链接与 JS 片段。

产物：recon/{sd,gx,qh}-home.html、recon/xj-wsxf-queryIndex.html、recon/xz-wsxx.html 等。
"""
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

KEY = re.compile(r"(hdjl|zmhd|hd/|gzhd|wzly|lyb|hdjlpt|12345|互动|问答|留言|信访|咨询|wsxf|xf|jxzc|wenda|"
                 r"hdhd|hygq|fkxd|wszx|sjzc|zxts|wyyz|jact|was5|IGI)", re.I)
A_RE = re.compile(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.S | re.I)
TAG = re.compile(r"<[^>]+>")


def get(url, **kw):
    with httpx.Client(timeout=30, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False) as c:
        return c.get(url, **kw)


def save(name, url):
    try:
        r = get(url)
    except Exception as e:  # noqa: BLE001
        print(f"  {url} -> {type(e).__name__}: {e}")
        return None
    p = os.path.join(HERE, name)
    with open(p, "w", encoding="utf-8") as f:
        f.write(r.text or "")
    print(f"  saved {name}  HTTP {r.status_code}  len={len(r.text or '')}  final={r.url}")
    return r


def scan_links(html, base=""):
    seen = set()
    for m in A_RE.finditer(html or ""):
        href, txt = m.group(1), re.sub(r"\s+", " ", TAG.sub("", m.group(2))).strip()
        if KEY.search(href) or KEY.search(txt):
            k = (href, txt)
            if k in seen:
                continue
            seen.add(k)
            print(f"    {txt[:28]:28s}  {href[:100]}")


def main() -> int:
    print("== 山东 http ==")
    r = save("sd-home.html", "http://www.shandong.gov.cn/")
    if r:
        scan_links(r.text)
    time.sleep(PAUSE)

    print("== 广西 http ==")
    r = save("gx-home.html", "http://www.gxzf.gov.cn/")
    if r:
        scan_links(r.text)
    time.sleep(PAUSE)

    print("== 青海 http ==")
    r = save("qh-home.html", "http://www.qinghai.gov.cn/")
    if r:
        scan_links(r.text)
    time.sleep(PAUSE)

    print("== 新疆信访 queryIndex ==")
    r = save("xj-wsxf-queryIndex.html",
             "http://wsxf.xjxfj.gov.cn/html/onlineInquiry/queryIndex.jsp?regionCode=650000000000")
    if r:
        scan_links(r.text)
    time.sleep(PAUSE)

    print("== 西藏信访 wsxx ==")
    r = save("xz-wsxx.html", "http://xzxf.xizang.gov.cn/ocp/wsxx.html")
    if r:
        scan_links(r.text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
