"""city-sc-probe25：南充 IGI siteId 枚举(修正) + 宜宾来信选登/巴中/凉山/广元 深挖。"""
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
OUT = Path(__file__).with_suffix(".txt")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
H = {"User-Agent": UA}


def w(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    with OUT.open("a", encoding="utf-8") as f:
        f.write(s + "\n")


def get(u, params=None, ref=None):
    h = dict(H)
    if ref:
        h["Referer"] = ref
    try:
        return requests.get(u, timeout=20, allow_redirects=True, headers=h, params=params)
    except Exception as e:  # noqa: BLE001
        return e


def igi_enum():
    w("\n===== 南充 IGI siteId 枚举 1..40 =====")
    for sid in range(1, 41):
        r = get("https://www.nanchong.gov.cn/IGI/nbhd/openGovmsgbox.do",
                params={"method": "listGovmsgboxs", "siteId": sid, "order": 1,
                        "appId": 1, "pageIndex": 1, "pageSize": 1},
                ref="https://www.nanchong.gov.cn/hdjl/")
        if not hasattr(r, "status_code") or r.status_code != 200:
            continue
        try:
            pi = (r.json().get("datas") or {}).get("pageInfo") or {}
        except Exception:                                                   # noqa: BLE001
            continue
        tot = pi.get("totalResults")
        if tot:
            w(f"  siteId={sid} totalResults={tot}")


def inspect(name, u, kws, ref=None):
    w(f"\n===== {name} {u} =====")
    r = get(u, ref=ref)
    if not hasattr(r, "status_code"):
        w(f"  ERR {r}")
        return
    w(f"  -> {r.status_code} len={len(r.text)} ct={r.headers.get('content-type','')[:40]} final={r.url}")
    if r.status_code != 200:
        return
    t = r.text
    for m in re.finditer(r'<script[^>]+src=["\']([^"\']+)["\']', t):
        s = m.group(1)
        if any(k in s.lower() for k in ("mail", "hdjl", "zmhd", "szxx", "letter", "list", "api", "common", "interaction", "detail")):
            w("     [js] " + s[:150])
    seen = set()
    for m in re.finditer(r'href=["\']([^"\'#]+)["\']', t):
        h = m.group(1).strip()
        if h in seen:
            continue
        if any(k in h.lower() for k in kws):
            seen.add(h)
            w("     [h] " + h[:140])
    for kw in ("ajax", "url:", "/api/", "api/", "getList", "findList", "listPage"):
        for m in re.finditer(re.escape(kw), t):
            i = m.start()
            w(f"     [{kw}] " + re.sub(r"\s+", " ", t[max(0, i - 90):i + 150])[:240])
            break


def main():
    OUT.write_text("", encoding="utf-8")
    igi_enum()
    inspect("宜宾-来信选登", "https://www.yibin.gov.cn/hdjl/szywm/lxxd/",
            ("mail", "letter", "szxx", "wyxx", "lxxd", "detail", "show"))
    inspect("巴中-市长信箱", "https://www.cnbz.gov.cn/zmhd/ldxx/szxx/index.html",
            ("mail", "letter", "szxx", "zmhd", "ldxx", "detail", "api", "list"))
    inspect("凉山-hdnew", "http://www.lsz.gov.cn/hdjl/zmhd/hdnew/",
            ("mail", "letter", "szxx", "zmhd", "detail", "api", "list"))
    inspect("凉山-12345通知", "http://12345.lsz.gov.cn/notice/2026-09/03/article_2026090311030010183.html",
            ("mail", "letter", "notice", "article", "api"))
    inspect("广元-导航再扫", "https://www.gy.gov.cn/", ("hd", "zm", "mail", "letter", "xf", "12345", "szxx", "shouzhang", "wenzheng", "hu", "dong"))


if __name__ == "__main__":
    main()
