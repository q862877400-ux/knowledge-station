"""stage29：淮安 互动栏目深挖（导航全链接 + 候选 URL）。"""
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
OUT = Path(__file__).with_suffix(".txt")


def w(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    with OUT.open("a", encoding="utf-8") as f:
        f.write(s + "\n")


def main():
    OUT.write_text("", encoding="utf-8")
    c = requests.Session()
    c.headers.update({"User-Agent": "Mozilla/5.0"})
    h = c.get("https://www.huaian.gov.cn/", timeout=30).text
    w("## 淮安首页全部导航链接")
    seen = set()
    for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]{1,40})</a>', h):
        href, txt = m.group(1), m.group(2).strip()
        if href in seen or not txt:
            continue
        seen.add(href)
        w(f"   [{txt}] {href}")
    w("\n## 淮安候选 URL 探测")
    for u in ("https://www.huaian.gov.cn/col/16655_185673/index.html",
              "https://12345.huaian.gov.cn/",
              "http://12345.huaian.gov.cn/",
              "https://www.huaian.gov.cn/hdjl/",
              "https://www.huaian.gov.cn/col/16653_544327/index.html",
              "https://szxx.huaian.gov.cn/",
              "https://www.huaian.gov.cn/col/col16655/index.html"):
        try:
            r = c.get(u, timeout=20, allow_redirects=True)
            w(f"  {u} -> {r.status_code} len={len(r.text)} url={r.url}")
        except Exception as e:  # noqa: BLE001
            w(f"  {u} -> {type(e).__name__} {str(e)[:60]}")


if __name__ == "__main__":
    main()
