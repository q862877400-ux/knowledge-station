"""city-sc-probe33：眉山 / 达州 互动栏目深挖（首页链接 + 候选接口）。"""
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


def links(t, kws):
    seen = []
    for m in re.finditer(r'href=["\']([^"\'#]+)["\']', t):
        h = m.group(1)
        if any(k in h for k in kws) and h not in seen:
            seen.append(h)
    return seen


def main():
    OUT.write_text("", encoding="utf-8")

    w("===== 眉山 首页 互动相关链接 =====")
    r = get("https://www.ms.gov.cn/")
    if hasattr(r, "status_code") and r.status_code == 200:
        t = dec(r)
        for h in links(t, ["zmhd", "mail", "hdjl", "12345", "xinfang", "wsxf", "szxx", "shizhang", "liuyan", "hd"]):
            w("  H " + h[:140])
        # 关键栏目文字
        for kw in ("市长信箱", "书记信箱", "12345", "政民互动", "互动交流", "写信", "网上信访"):
            i = t.find(kw)
            if i > 0:
                seg = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t[max(0, i - 120):i + 120]))
                w(f"  [{kw}] {seg[:220]}")

    w("\n===== 眉山 候选接口探测 =====")
    for u in ["https://www.ms.gov.cn/mail12345/",
              "https://www.ms.gov.cn/mail12345/index.jsp",
              "https://www.ms.gov.cn/mail12345/list.jsp",
              "https://www.ms.gov.cn/hdjl/index.html",
              "https://www.ms.gov.cn/zmhd/",
              "https://www.ms.gov.cn/szxx/index.html",
              "https://www.ms.gov.cn/api/mail/list"]:
        rr = get(u, ref="https://www.ms.gov.cn/")
        if hasattr(rr, "status_code"):
            ti = ""
            mm = re.search(r"<title>(.*?)</title>", dec(rr), re.S)
            if mm:
                ti = re.sub(r"\s+", " ", mm.group(1))[:40]
            w(f"  {u} -> {rr.status_code} len={len(rr.content)} title={ti}")

    w("\n===== 达州 首页 互动相关链接 =====")
    r = get("https://www.dazhou.gov.cn/")
    if hasattr(r, "status_code") and r.status_code == 200:
        t = dec(r)
        for h in links(t, ["zmhd", "mail", "hdjl", "12345", "xinfang", "wsxf", "szxx", "shizhang", "liuyan", "hd", "interview", "zxta"]):
            w("  H " + h[:140])
        for kw in ("市长信箱", "书记信箱", "12345", "政民互动", "互动交流", "网上信访", "在线访谈"):
            i = t.find(kw)
            if i > 0:
                seg = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t[max(0, i - 120):i + 120]))
                w(f"  [{kw}] {seg[:220]}")

    w("\n===== 达州 候选路径（含 http）=====")
    for u in ["https://www.dazhou.gov.cn/zmhd/",
              "http://www.dazhou.gov.cn/zmhd/index.html",
              "https://www.dazhou.gov.cn/hdjl/index.html",
              "https://www.dazhou.gov.cn/szxx/index.html",
              "https://www.dazhou.gov.cn/mail/",
              "http://www.dazhou.gov.cn/"]:
        rr = get(u, ref="https://www.dazhou.gov.cn/")
        if hasattr(rr, "status_code"):
            ti = ""
            mm = re.search(r"<title>(.*?)</title>", dec(rr), re.S)
            if mm:
                ti = re.sub(r"\s+", " ", mm.group(1))[:40]
            w(f"  {u} -> {rr.status_code} len={len(rr.content)} title={ti}")


if __name__ == "__main__":
    main()
