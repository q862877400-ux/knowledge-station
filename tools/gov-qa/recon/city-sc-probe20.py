"""city-sc-probe20：第 7~21 市 首页/互动页 找「数融 pc/list.html」模板与 API 线索。"""
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
OUT = Path(__file__).with_suffix(".txt")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

# (城市, 首页 URL)
HOMES = [
    ("遂宁", "https://www.suining.gov.cn/"),
    ("乐山", "https://www.leshan.gov.cn/"),
    ("南充", "https://www.nanchong.gov.cn/"),
    ("眉山", "https://www.ms.gov.cn/"),
    ("宜宾", "https://www.yibin.gov.cn/"),
    ("广安", "https://www.guang-an.gov.cn/"),
    ("达州", "https://www.dazhou.gov.cn/"),
    ("雅安", "https://www.yaan.gov.cn/"),
    ("巴中", "https://www.cnbz.gov.cn/"),
    ("资阳", "https://www.ziyang.gov.cn/"),
    ("阿坝州", "https://www.abazhou.gov.cn/"),
    ("甘孜州", "https://www.gzz.gov.cn/"),
    ("凉山州", "http://www.lsz.gov.cn/"),
    ("广元", "https://www.gy.gov.cn/"),
    ("内江", "https://www.neijiang.gov.cn/"),
]
PATS = ("pc/list.html", "hdjl", "szxx", "zmhd", "mail", "letter", "12345", "xfj", "interaction", "frontMail")


def w(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    with OUT.open("a", encoding="utf-8") as f:
        f.write(s + "\n")


def get(u):
    try:
        return requests.get(u, timeout=25, allow_redirects=True, headers={"User-Agent": UA})
    except Exception as e:  # noqa: BLE001
        return e


def main():
    OUT.write_text("", encoding="utf-8")
    for name, home in HOMES:
        w(f"\n===== {name} {home} =====")
        r = get(home)
        if not hasattr(r, "status_code"):
            w(f"  ERR {r}")
            continue
        w(f"  -> {r.status_code} len={len(r.text)} final={r.url}")
        if r.status_code != 200:
            continue
        t = r.text
        hits = []
        for m in re.finditer(r'href=["\']([^"\'#]+)["\']', t):
            h = m.group(1).strip()
            low = h.lower()
            if any(k in low for k in PATS):
                hits.append(h)
        seen = set()
        for h in hits:
            if h in seen:
                continue
            seen.add(h)
            w("     " + h[:150])
        # 找 pc/list.html 模板 & config.js
        for m in re.finditer(r'([A-Za-z0-9_\-]+)/hdjl/pc/list\.html', t):
            w("     [数融模板] " + m.group(0))
        for m in re.finditer(r'(/default/libs/config\.js|[A-Za-z0-9_\-/]+/js/basehd/config\.js|/default/xhtml/[^"\']+\.js)', t):
            w("     [cfg] " + m.group(1)[:120])


if __name__ == "__main__":
    main()
