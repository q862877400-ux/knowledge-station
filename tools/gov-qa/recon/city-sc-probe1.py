"""city-sc-probe1：四川前 6 市门户首页 → 互动栏目入口提取。

成都/自贡/攀枝花/泸州/德阳/绵阳。https 失败试 http。
"""
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
OUT = Path(__file__).with_suffix(".txt")

CITIES = [
    ("成都", "chengdu", "https://www.chengdu.gov.cn/"),
    ("自贡", "zigong", "https://www.zigong.gov.cn/"),
    ("攀枝花", "panzhihua", "https://www.panzhihua.gov.cn/"),
    ("泸州", "luzhou", "https://www.luzhou.gov.cn/"),
    ("德阳", "deyang", "https://www.deyang.gov.cn/"),
    ("绵阳", "mianyang", "https://www.mianyang.gov.cn/"),
]
KW = ("互动", "信箱", "12345", "热线", "留言", "诉求", "信访", "征集", "访谈", "问答", "咨询", "投诉")


def w(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    with OUT.open("a", encoding="utf-8") as f:
        f.write(s + "\n")


def fetch(c, url):
    for u in (url, url.replace("https://", "http://")):
        try:
            r = c.get(u, timeout=25, allow_redirects=True)
            return u, r
        except Exception as e:  # noqa: BLE001
            last = f"{type(e).__name__} {str(e)[:60]}"
    return url, last


def main():
    OUT.write_text("", encoding="utf-8")
    c = requests.Session()
    c.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    for name, py, home in CITIES:
        w(f"\n===== {name} {py} {home} =====")
        u, r = fetch(c, home)
        if not hasattr(r, "status_code"):
            w(f"  {u} -> ERR {r}")
            continue
        w(f"  {u} -> {r.status_code} len={len(r.text)} final={r.url}")
        hits = []
        for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]{1,40})</a>', r.text):
            href, txt = m.group(1).strip(), m.group(2).strip()
            if any(k in txt for k in KW):
                hits.append((txt, href))
        seen = set()
        for txt, href in hits:
            if (txt, href) in seen:
                continue
            seen.add((txt, href))
            w(f"     [{txt}] {href}")
        if not hits:
            w("     （无匹配互动链接）")


if __name__ == "__main__":
    main()
