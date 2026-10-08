"""city-sc-probe22：广元互动入口 + 乐山/巴中/阿坝/凉山/宜宾/达州/眉山 API 线索。"""
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
OUT = Path(__file__).with_suffix(".txt")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
KW = ("互动", "信箱", "12345", "热线", "留言", "诉求", "信访", "征集", "访谈", "问答",
      "咨询", "投诉", "建议", "appeal", "hdjl", "szxx", "zmhd", "letter", "mail", "xfj", "shrd", "zwft")


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


def scan_href(name, u):
    w(f"\n===== {name} {u} =====")
    r = get(u)
    if not hasattr(r, "status_code"):
        w(f"  ERR {r}")
        return
    w(f"  -> {r.status_code} len={len(r.text)} final={r.url}")
    if r.status_code != 200:
        return
    t = r.text
    seen = set()
    for m in re.finditer(r'href=["\']([^"\'#]+)["\']', t):
        h = m.group(1).strip()
        if h in seen:
            continue
        if any(k in h.lower() for k in KW) or any(k in h for k in KW):
            seen.add(h)
            w("     " + h[:150])


def raw_scan(name, u, kws):
    w(f"\n===== {name} {u} =====")
    r = get(u)
    if not hasattr(r, "status_code"):
        w(f"  ERR {r}")
        return
    w(f"  -> {r.status_code} len={len(r.text)} ct={r.headers.get('content-type','')[:40]}")
    if r.status_code != 200:
        return
    t = r.text
    for m in re.finditer(r'<script[^>]+src=["\']([^"\']+)["\']', t):
        w("     [js] " + m.group(1)[:150])
    for kw in kws:
        for m in re.finditer(kw, t):
            i = m.start()
            w(f"     [{kw}] " + re.sub(r"\s+", " ", t[max(0, i - 110):i + 150])[:260])
            break


def main():
    OUT.write_text("", encoding="utf-8")
    scan_href("广元-首页", "https://www.gy.gov.cn/")
    raw_scan("乐山-hdjl.js", "https://www.leshan.gov.cn/lsswszf/resource/js/hdjl.js",
             ["ajax", "url", "list", "page"])
    raw_scan("巴中-common.min", "https://www.cnbz.gov.cn/assets/js/common.min.js",
             ["api", "list", "zmhd", "szxx", "ldxx"])
    raw_scan("阿坝-hdmailbox", "https://www.abazhou.gov.cn/abazhou/c101014/hd_mailbox.shtml",
             ["ajax", "api", "mail", "url", "form"])
    raw_scan("凉山-zmhd", "http://www.lsz.gov.cn/hdjl/zmhd/", ["ajax", "api", "list", "url"])
    raw_scan("凉山-12345", "http://12345.lsz.gov.cn/", ["ajax", "api", "list", "url", "notice"])
    raw_scan("宜宾-hdjl", "https://www.yibin.gov.cn/hdjl/", ["ajax", "api", "mail", "list", "url"])
    raw_scan("达州-hdjl", "https://www.dazhou.gov.cn/news-list-hdjl.html", ["ajax", "api", "list", "url"])
    raw_scan("眉山-hdjl_index", "https://www.ms.gov.cn/17_hudong/hdjl_index.jsp?urltype=tree.TreeTempUrl&wbtreeid=1010",
             ["ajax", "api", "mail", "list", "url"])


if __name__ == "__main__":
    main()
