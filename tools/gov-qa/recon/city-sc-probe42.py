"""city-sc-probe42：成都 / 广元（瑞数 412）替代入口试探。"""
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
OUT = Path(__file__).with_suffix(".txt")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
MOB = ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 "
       "(KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1")


def w(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    with OUT.open("a", encoding="utf-8") as f:
        f.write(s + "\n")


def get(u, ref=None, ua=UA):
    h = {"User-Agent": ua, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
         "Accept-Language": "zh-CN,zh;q=0.9"}
    if ref:
        h["Referer"] = ref
    try:
        return requests.get(u, timeout=20, allow_redirects=True, headers=h)
    except Exception as e:  # noqa: BLE001
        return e


def dec(r):
    try:
        return r.content.decode("utf-8")
    except Exception:  # noqa: BLE001
        return r.text


def probe(label, urls, ua=UA):
    w(f"\n===== {label} =====")
    for u in urls:
        r = get(u, ua=ua)
        if not hasattr(r, "status_code"):
            w(f"  {u} -> ERR {r}")
            continue
        ti = ""
        mm = re.search(r"<title>(.*?)</title>", dec(r), re.S)
        if mm:
            ti = re.sub(r"\s+", " ", mm.group(1))[:40]
        w(f"  {u} -> {r.status_code} len={len(r.content)} ct={r.headers.get('content-type','')[:30]} title={ti}")
        sc = r.headers.get("Set-Cookie", "")
        if sc and ("Ss" in sc or "azS" in sc or "wz" in sc.lower()):
            w("     SC " + sc[:120])


def main():
    OUT.write_text("", encoding="utf-8")

    probe("成都 主域与替代", [
        "https://www.chengdu.gov.cn/",
        "https://www.chengdu.gov.cn/chengdu/index.shtml",
        "https://cd12345.chengdu.gov.cn/",
        "https://12345.chengdu.gov.cn/",
        "https://wlzl.chengdu.gov.cn/",
        "https://www.chengdu.gov.cn/wlzl/",
        "https://m.chengdu.gov.cn/",
        "https://www.chengdu.gov.cn/hdjl/",
    ])

    probe("成都 移动 UA", [
        "https://www.chengdu.gov.cn/",
        "https://www.chengdu.gov.cn/hdjl/",
    ], ua=MOB)

    probe("广元 主域与替代", [
        "https://www.cngy.gov.cn/",
        "http://www.cngy.gov.cn/",
        "https://cngy.gov.cn/",
        "https://www.guangyuan.gov.cn/",
        "https://12345.cngy.gov.cn/",
        "https://www.cngy.gov.cn/hdjl/",
        "https://m.cngy.gov.cn/",
    ])

    probe("广元 移动 UA", [
        "https://www.cngy.gov.cn/",
    ], ua=MOB)

    # 常见政务站群 / 省级 12345
    probe("省级/其他候选", [
        "https://www.sc.gov.cn/",
        "https://12345.sc.gov.cn/",
    ])


if __name__ == "__main__":
    main()
