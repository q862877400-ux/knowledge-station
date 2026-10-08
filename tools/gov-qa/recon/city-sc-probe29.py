"""city-sc-probe29：乐山信箱页定位 + 凉山/雅安/眉山/达州 复核。"""
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


def get(u, ref=None):
    h = {"User-Agent": UA}
    if ref:
        h["Referer"] = ref
    try:
        return requests.get(u, timeout=20, allow_redirects=True, headers=h)
    except Exception as e:  # noqa: BLE001
        return e


def text_of(t):
    t = re.sub(r"(?s)<script.*?</script>", " ", t)
    t = re.sub(r"(?s)<style.*?</style>", " ", t)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))


def main():
    OUT.write_text("", encoding="utf-8")

    w("===== 乐山 zmhd 页 全部链接 + 板块文字 =====")
    r = get("https://www.leshan.gov.cn/lsswszf/zmhd/index.html")
    if hasattr(r, "status_code") and r.status_code == 200:
        for m in re.finditer(r'href=["\']([^"\'#]+)["\']', r.text):
            w("  H " + m.group(1)[:140])
        w("  TEXT: " + text_of(r.text)[:600])
    w("\n===== 乐山 候选信箱页 =====")
    for p in ["/lsswszf/zmhd/szxx/index.html", "/lsswszf/zmhd/xjcx/index.html",
              "/lsswszf/zmhd/hdjl/index.html", "/lsswszf/zmhd/hdjl.shtml",
              "/front/mail/box/list", "/front/mail/box/pageList",
              "/front/mail/box/page/list", "/front/mail/box/index",
              "/front/mail/box/findPage", "/front/mail/box/queryPage"]:
        rr = get("https://www.leshan.gov.cn" + p, ref="https://www.leshan.gov.cn/lsswszf/zmhd/index.html")
        if hasattr(rr, "status_code"):
            ct = rr.headers.get("content-type", "")[:24]
            w(f"  {p} -> {rr.status_code} {ct} len={len(rr.text)}")

    w("\n===== 凉山 zmhd 页 文字/链接 =====")
    r = get("http://www.lsz.gov.cn/hdjl/zmhd/")
    if hasattr(r, "status_code") and r.status_code == 200:
        w("  TEXT: " + text_of(r.text)[:500])

    w("\n===== 凉山 12345 首页文字 =====")
    r = get("http://12345.lsz.gov.cn/")
    if hasattr(r, "status_code") and r.status_code == 200:
        w("  TEXT: " + text_of(r.text)[:500])

    w("\n===== 雅安 mail.js =====")
    r = get("https://www.yaan.gov.cn/mail/v2/js/mail.js")
    if hasattr(r, "status_code") and r.status_code == 200:
        w("  " + re.sub(r"\s+", " ", r.text)[:500])

    w("\n===== 达州 12345 平台 =====")
    for u in ["http://zxbl.sczwfw.gov.cn/app/serviceYouHua/newMainDh?areaCode=511700000000",
              "https://www.dazhou.gov.cn/", "https://www.dazhou.gov.cn/news-list-dzxcj.html"]:
        rr = get(u)
        if hasattr(rr, "status_code"):
            w(f"  {u} -> {rr.status_code} len={len(rr.text)}")
            if rr.status_code == 200:
                w("     " + text_of(rr.text)[:250])


if __name__ == "__main__":
    main()
