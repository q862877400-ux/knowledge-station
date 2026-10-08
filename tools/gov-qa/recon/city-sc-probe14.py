"""city-sc-probe14：绵阳 my.gov.cn / 德阳 / 攀枝花 session 流。"""
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
OUT = Path(__file__).with_suffix(".txt")


def w(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    with OUT.open("a", encoding="utf-8") as f:
        f.write(s + "\n")


def main():
    OUT.write_text("", encoding="utf-8")
    c = requests.Session()
    c.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

    # ---- 绵阳 常见互动路径 ----
    w("## 绵阳 my.gov.cn 常见路径")
    for p in ("/hdjl/", "/hdjl/index.html", "/szxx/", "/zmhd/", "/hd/", "/hdcy/",
              "/mysrmzf/hdjl/", "/mysrmzf/szxx/", "/mysrmzf/zmhd/index.html"):
        try:
            r = c.get("https://www.my.gov.cn" + p, timeout=20, allow_redirects=True)
            ti = re.search(r"<title>([^<]*)</title>", r.text)
            w(f"  {p} -> {r.status_code} len={len(r.text)} title={ti.group(1).strip()[:40] if ti else '?'}")
        except Exception as e:  # noqa: BLE001
            w(f"  {p} -> ERR {type(e).__name__}")

    # 绵阳 首页里的所有 href（含相对）
    w("\n## 绵阳 首页全部 href 唯一值")
    try:
        t = c.get("https://www.my.gov.cn/", timeout=25).text
        hrefs = sorted(set(re.findall(r'href=["\']([^"\'#]+)["\']', t)))
        for h in hrefs[:60]:
            w("   " + h)
    except Exception as e:  # noqa: BLE001
        w("   ERR " + str(e)[:60])

    # ---- 德阳 ----
    w("\n## 德阳 常见路径")
    for p in ("/hdjl/", "/zmhd/", "/szxx/", "/hd/", "/hdcy/", "/gzhd/", "/wzsz/"):
        try:
            r = c.get("https://www.deyang.gov.cn" + p, timeout=20, allow_redirects=True)
            ti = re.search(r"<title>([^<]*)</title>", r.text)
            w(f"  {p} -> {r.status_code} len={len(r.text)} title={ti.group(1).strip()[:40] if ti else '?'}")
        except Exception as e:  # noqa: BLE001
            w(f"  {p} -> ERR {type(e).__name__}")
    w("\n## 德阳 首页全部 href 唯一值")
    try:
        t = c.get("https://www.deyang.gov.cn/", timeout=25).text
        for h in sorted(set(re.findall(r'href=["\']([^"\'#]+)["\']', t)))[:60]:
            w("   " + h)
    except Exception as e:  # noqa: BLE001
        w("   ERR " + str(e)[:60])

    # ---- 攀枝花 session 流 ----
    w("\n## 攀枝花 session 流")
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    try:
        s.get("http://www.panzhihua.gov.cn/hdcy/szxx/szxx/index.shtml", timeout=25)
        rr = s.get("http://www.panzhihua.gov.cn/webapp/mailbox/letterListJson",
                   headers={"Referer": "http://www.panzhihua.gov.cn/hdcy/szxx/szxx/index.shtml",
                            "X-Requested-With": "XMLHttpRequest"},
                   params={"channelId": 2, "mailType": 1, "pageNum": 1, "pageSize": 5,
                           "orderStr": "replytime"}, timeout=25)
        w(f"  letterListJson(session) -> {rr.status_code} len={len(rr.text)} {rr.text[:120]!r}")
        # getAllSubOrgan 同 session
        rr2 = s.get("http://www.panzhihua.gov.cn/webapp/mailbox/getAllSubOrgan",
                    headers={"Referer": "http://www.panzhihua.gov.cn/hdcy/szxx/szxx/index.shtml",
                             "X-Requested-With": "XMLHttpRequest"}, params={"id": 2}, timeout=25)
        w(f"  getAllSubOrgan(session) -> {rr2.status_code} len={len(rr2.text)}")
    except Exception as e:  # noqa: BLE001
        w(f"  ERR {type(e).__name__} {str(e)[:60]}")


if __name__ == "__main__":
    main()
