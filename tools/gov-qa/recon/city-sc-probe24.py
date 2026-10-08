"""city-sc-probe24：南充 IGI siteId 枚举(1..30) + 乐山/宜宾/广元/凉山 入口深挖。"""
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
OUT = Path(__file__).with_suffix(".txt")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"


def w(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    with OUT.open("a", encoding="utf-8") as f:
        f.write(s + "\n")


def get(u, **kw):
    try:
        return requests.get(u, timeout=20, allow_redirects=True, headers={"User-Agent": UA}, **kw)
    except Exception as e:  # noqa: BLE001
        return e


def igi_enum():
    w("\n===== 南充 IGI siteId 枚举 1..30 =====")
    for sid in range(1, 31):
        r = get("https://www.nanchong.gov.cn/IGI/nbhd/openGovmsgbox.do",
                params={"method": "listGovmsgboxs", "siteId": sid, "order": 1,
                        "appId": 1, "pageIndex": 1, "pageSize": 1},
                headers={"Referer": "https://www.nanchong.gov.cn/hdjl/"})
        if not hasattr(r, "status_code") or r.status_code != 200:
            continue
        try:
            pi = (r.json().get("datas") or {}).get("pageInfo") or {}
        except Exception:                                                   # noqa: BLE001
            continue
        tot = pi.get("totalResults")
        if tot:
            w(f"  siteId={sid} totalResults={tot}")


def hrefs(name, u, kws):
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
        if any(k in h.lower() for k in kws):
            seen.add(h)
            w("     " + h[:150])
    # js
    for m in re.finditer(r'<script[^>]+src=["\']([^"\']+)["\']', t):
        s = m.group(1)
        if any(k in s.lower() for k in ("mail", "hdjl", "zmhd", "szxx", "letter", "interaction", "common", "index")):
            w("     [js] " + s[:140])


def main():
    OUT.write_text("", encoding="utf-8")
    igi_enum()
    hrefs("乐山-政民互动", "https://www.leshan.gov.cn/lsswszf/zmhd/index.html",
          ("mail", "letter", "hdjl", "szxx", "zmhd", "wyxx", "xiaozhang", "shizhang"))
    hrefs("宜宾-hdjl", "https://www.yibin.gov.cn/hdjl/", ("mail", "letter", "szxx", "wyxx", "szywm", "zmhd"))
    hrefs("广元-首页", "https://www.gy.gov.cn/", ("hdjl", "zmhd", "szxx", "mail", "letter", "xfj", "12345", "hd", "zx", "shouzhang", "wenzheng"))
    hrefs("凉山-zmhd", "http://www.lsz.gov.cn/hdjl/zmhd/", ("mail", "letter", "szxx", "wyxx", "zmhd", "12345", "hd"))
    hrefs("达州-hdjl", "https://www.dazhou.gov.cn/news-list-hdjl.html", ("mail", "letter", "szxx", "zmhd", "hd", "zx"))
    hrefs("巴中-zmhd", "https://www.cnbz.gov.cn/zmhd/index.html", ("mail", "letter", "szxx", "zmhd", "ldxx", "sjxx"))
    hrefs("眉山-hdjl", "https://www.ms.gov.cn/17_hudong/hdjl_index.jsp?urltype=tree.TreeTempUrl&wbtreeid=1010",
          ("mail", "letter", "szxx", "zmhd", "hd"))


if __name__ == "__main__":
    main()
