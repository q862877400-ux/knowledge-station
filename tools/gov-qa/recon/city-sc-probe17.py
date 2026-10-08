"""city-sc-probe17：四川第 7~21 市门户首页 → 互动入口（扫 href 全集，含短域名回退）。"""
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
OUT = Path(__file__).with_suffix(".txt")

CITIES = [
    ("广元", "guangyuan", "https://www.guangyuan.gov.cn/"),
    ("遂宁", "suining", "https://www.suining.gov.cn/"),
    ("内江", "neijiang", "https://www.neijiang.gov.cn/"),
    ("乐山", "leshan", "https://www.leshan.gov.cn/"),
    ("南充", "nanchong", "https://www.nanchong.gov.cn/"),
    ("眉山", "meishan", "https://www.ms.gov.cn/"),
    ("宜宾", "yibin", "https://www.yibin.gov.cn/"),
    ("广安", "guangan", "https://www.guang-an.gov.cn/"),
    ("达州", "dazhou", "https://www.dazhou.gov.cn/"),
    ("雅安", "yaan", "https://www.yaan.gov.cn/"),
    ("巴中", "bazhong", "https://www.cnbz.gov.cn/"),
    ("资阳", "ziyang", "https://www.ziyang.gov.cn/"),
    ("阿坝州", "aba", "https://www.abazhou.gov.cn/"),
    ("甘孜州", "ganzi", "https://www.gzz.gov.cn/"),
    ("凉山州", "liangshan", "https://www.lsz.gov.cn/"),
]
KW = ("互动", "信箱", "12345", "热线", "留言", "诉求", "信访", "征集", "访谈", "问答",
      "咨询", "投诉", "建议", "appeal", "hdjl", "szxx", "zmhd", "letter", "mail", "xfj")


def w(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    with OUT.open("a", encoding="utf-8") as f:
        f.write(s + "\n")


def fetch(home):
    for u in (home, home.replace("https://", "http://"), home.replace("http://", "https://")):
        try:
            r = requests.get(u, timeout=20, allow_redirects=True,
                             headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
            return u, r
        except Exception as e:  # noqa: BLE001
            last = f"{type(e).__name__}"
    return home, last


def main():
    OUT.write_text("", encoding="utf-8")
    for name, py, home in CITIES:
        w(f"\n===== {name} {py} {home} =====")
        u, r = fetch(home)
        if not hasattr(r, "status_code"):
            w(f"  {u} -> ERR {r}")
            continue
        w(f"  {u} -> {r.status_code} len={len(r.text)} final={r.url}")
        if r.status_code != 200:
            continue
        hits = []
        for m in re.finditer(r'href=["\']([^"\'#]+)["\']', r.text):
            href = m.group(1).strip()
            low = href.lower()
            if any(k in low for k in KW):
                hits.append(href)
        seen = set()
        for h in hits:
            if h in seen:
                continue
            seen.add(h)
            w("     " + h[:140])


if __name__ == "__main__":
    main()
