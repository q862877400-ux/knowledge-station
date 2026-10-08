"""city-sc-probe34：眉山 互动交流 / 达州 民议征集 深挖。"""
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


def dec(r):
    try:
        return r.content.decode("utf-8")
    except Exception:  # noqa: BLE001
        return r.text


def main():
    OUT.write_text("", encoding="utf-8")

    w("===== 眉山 互动交流 /17_hudong/hdjl_index.jsp =====")
    u = "http://www.ms.gov.cn/17_hudong/hdjl_index.jsp?urltype=tree.TreeTempUrl&wbtreeid=1010"
    r = get(u, ref="http://www.ms.gov.cn/")
    if hasattr(r, "status_code") and r.status_code == 200:
        t = dec(r)
        w(f"  len={len(t)}")
        for m in re.finditer(r'href=["\']([^"\'#]+)["\']', t):
            h = m.group(1)
            if any(k in h for k in ("mail", "hdjl", "hudong", "list", "szxx", "shizhang", "sjxx", "jsp", "detail", "show")):
                w("  H " + h[:150])
        for kw in ("信箱", "互动", "办理", "选登", "公开"):
            i = t.find(kw)
            if i > 0:
                seg = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t[max(0, i - 100):i + 140]))
                w(f"  [{kw}] {seg[:220]}")

    w("\n===== 眉山 市长信箱 swmail.jsp =====")
    u = "http://www.ms.gov.cn/mail12345/swmail.jsp?urltype=tree.TreeTempUrl&wbtreeid=5999"
    r = get(u, ref="http://www.ms.gov.cn/")
    if hasattr(r, "status_code") and r.status_code == 200:
        t = dec(r)
        w(f"  len={len(t)}")
        for m in re.finditer(r'href=["\']([^"\'#]+)["\']', t):
            h = m.group(1)
            if any(k in h for k in ("mail", "list", "detail", "show", "jsp")):
                w("  H " + h[:150])
        body = re.sub(r"(?s)<script.*?</script>", " ", t)
        body = re.sub(r"(?s)<style.*?</style>", " ", body)
        w("  " + re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body))[:500])
    else:
        w(f"  -> {getattr(r, 'status_code', r)}")

    w("\n===== 达州 民议征集 index.php?s=dzmyzj =====")
    for u in ["https://www.dazhou.gov.cn/index.php?s=dzmyzj&c=home&m=index",
              "https://www.dazhou.gov.cn/index.php?s=dzmyzj&c=home",
              "https://www.dazhou.gov.cn/index.php?s=dzmyzj",
              "http://www.dazhou.gov.cn/index.php?s=dzmyzj&c=home"]:
        rr = get(u, ref="https://www.dazhou.gov.cn/")
        if hasattr(rr, "status_code"):
            ti = ""
            mm = re.search(r"<title>(.*?)</title>", dec(rr), re.S)
            if mm:
                ti = re.sub(r"\s+", " ", mm.group(1))[:40]
            w(f"  {u} -> {rr.status_code} len={len(rr.content)} title={ti}")

    w("\n===== 达州 news-list-hdjl.html =====")
    r = get("https://www.dazhou.gov.cn/news-list-hdjl.html", ref="https://www.dazhou.gov.cn/")
    if hasattr(r, "status_code") and r.status_code == 200:
        t = dec(r)
        w(f"  len={len(t)}")
        for m in re.finditer(r'href=["\']([^"\'#]+)["\']', t):
            h = m.group(1)
            if any(k in h for k in ("news", "detail", "content", "show", "hdjl", "letter", "mail")):
                w("  H " + h[:150])
        body = re.sub(r"(?s)<script.*?</script>", " ", t)
        body = re.sub(r"(?s)<style.*?</style>", " ", body)
        w("  " + re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body))[:600])
    else:
        w(f"  -> {getattr(r, 'status_code', r)}")


if __name__ == "__main__":
    main()
