"""city-sc-probe26：广元真域名试探 + 宜宾/巴中/凉山/乐山 列表 API 深挖。"""
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


def get(u, params=None, ref=None):
    h = {"User-Agent": UA}
    if ref:
        h["Referer"] = ref
    try:
        return requests.get(u, timeout=20, allow_redirects=True, headers=h, params=params)
    except Exception as e:  # noqa: BLE001
        return e


def main():
    OUT.write_text("", encoding="utf-8")
    w("===== 广元真域名试探 =====")
    for u in ["https://www.cngy.gov.cn/", "http://www.cngy.gov.cn/", "https://cngy.gov.cn/",
              "http://www.scgy.gov.cn/", "https://www.scgy.gov.cn/",
              "https://www.guangyuan.gov.cn/", "http://www.guangyuan.gov.cn/",
              "https://www.gy.gov.cn/", "https://www.gyzf.gov.cn/"]:
        r = get(u)
        if hasattr(r, "status_code"):
            title = ""
            m = re.search(r"<title>(.*?)</title>", r.text, re.S)
            if m:
                title = m.group(1).strip()[:40]
            w(f"  {u} -> {r.status_code} len={len(r.text)} final={r.url} title={title}")
        else:
            w(f"  {u} -> ERR {r}")

    w("\n===== 宜宾 lxxd 页 /fsp 接口 =====")
    r = get("https://www.yibin.gov.cn/hdjl/szywm/lxxd/")
    if hasattr(r, "status_code") and r.status_code == 200:
        t = r.text
        for m in re.finditer(r'/fsp-yibin-v2024/[A-Za-z0-9_/\-]+', t):
            w("  [fsp] " + m.group(0))
        for kw in ("listPage", "getLetter", "letterList", "pageNum", "getPage"):
            for m in re.finditer(kw, t):
                i = m.start()
                w(f"  [{kw}] " + re.sub(r"\s+", " ", t[max(0, i - 100):i + 140])[:240])
                break

    w("\n===== 巴中 szxx 页列表接口 =====")
    r = get("https://www.cnbz.gov.cn/zmhd/ldxx/szxx/index.html")
    if hasattr(r, "status_code") and r.status_code == 200:
        t = r.text
        for m in re.finditer(r'(/[A-Za-z0-9_\-]+)+\.(?:do|json|action)', t):
            w("  [ep] " + m.group(0))
        for kw in ("list", "List", "page", "ajax", "url"):
            for m in re.finditer(kw, t):
                i = m.start()
                seg = re.sub(r"\s+", " ", t[max(0, i - 80):i + 140])
                if "ajax" in seg or "url" in seg.lower():
                    w(f"  [{kw}] " + seg[:220])
                    break

    w("\n===== 凉山 12345 通知子页 =====")
    for p in ["/notice/xjxd/", "/notice/12345jj/", "/notice/ggtz/"]:
        r = get("http://12345.lsz.gov.cn" + p)
        if hasattr(r, "status_code"):
            w(f"  {p} -> {r.status_code} len={len(r.text)}")
            if r.status_code == 200:
                for m in re.finditer(r'href=["\']([^"\'#]*(?:article|notice)[^"\'#]*)["\']', r.text):
                    w("     [h] " + m.group(1)[:130])
                    break

    w("\n===== 乐山 全站找信箱 =====")
    for p in ["/lsswszf/zmhd/", "/lsswszf/zmhd/index.html", "/lsswszf/", "/lsswszf/szxx/",
              "/lsswszf/zmhd/szxx/", "/lsswszf/zmhd/hdjl/"]:
        r = get("https://www.leshan.gov.cn" + p)
        if hasattr(r, "status_code"):
            w(f"  {p} -> {r.status_code} len={len(r.text)}")


if __name__ == "__main__":
    main()
