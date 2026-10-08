"""city-sc-probe39：达州 xinxiang 子页 letter-city.html；眉山 Session 翻页。"""
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


def dec(r):
    try:
        return r.content.decode("utf-8")
    except Exception:  # noqa: BLE001
        return r.text


def main():
    OUT.write_text("", encoding="utf-8")
    s = requests.Session()
    s.headers.update({"User-Agent": UA})

    w("===== 达州 xinxiang 子页 letter-city.html =====")
    for u in ["https://www.dazhou.gov.cn/xinxiang/html/letter-city.html",
              "https://www.dazhou.gov.cn/xinxiang/js/index.js",
              "https://www.dazhou.gov.cn/xinxiang/js/letter-city.js"]:
        try:
            r = s.get(u, timeout=25, headers={"Referer": "https://www.dazhou.gov.cn/xinxiang/"})
        except Exception as e:  # noqa: BLE001
            w(f"  {u} -> {e}")
            continue
        w(f"  {u} -> {r.status_code} ct={r.headers.get('content-type','')} len={len(r.content)}")
        if r.status_code == 200:
            t = dec(r)
            w("   " + re.sub(r"\s+", " ", t)[:1200])
            for m in re.finditer(r"(\.ajax|url\s*:|/index\.php|fetch\(|data-name|\.json)", t):
                i = m.start()
                w(f"   [{m.group(1)}] " + re.sub(r"\s+", " ", t[max(0, i - 60):i + 220])[:280])

    w("\n===== 达州 试 letter-city 数据接口 =====")
    for u in ["https://www.dazhou.gov.cn/xinxiang/data/letter-city.json",
              "https://www.dazhou.gov.cn/index.php?s=xinxiang&c=home&m=list",
              "https://www.dazhou.gov.cn/xinxiang/letter/list"]:
        try:
            r = s.get(u, timeout=20, headers={"Referer": "https://www.dazhou.gov.cn/xinxiang/"})
        except Exception as e:  # noqa: BLE001
            w(f"  {u} -> {e}")
            continue
        w(f"  {u} -> {r.status_code} ct={r.headers.get('content-type','')} len={len(r.content)}")
        if r.status_code == 200:
            w("   " + re.sub(r"\s+", " ", dec(r))[:400])

    w("\n===== 眉山 Session 翻页（GET 拿 cookie 再 POST）=====")
    list_url = "http://www.ms.gov.cn/old13/list_ldxx.jsp?urltype=tree.TreeTempUrl&wbtreeid=5761"
    r0 = s.get(list_url, timeout=25, headers={"Referer": "http://www.ms.gov.cn/17_hudong/hdjl_index.jsp?urltype=tree.TreeTempUrl&wbtreeid=1010"})
    w(f"  GET list -> {r0.status_code} cookies={list(s.cookies.keys())}")
    t0 = dec(r0)
    g0 = re.findall(r"do_detail\('([^']+)'\)", t0)
    w(f"  page1 guid 数={len(g0)} 首={g0[:2]}")
    for pg in (2, 3):
        r = s.post(list_url, data={"pageNumber245916": str(pg)}, timeout=25,
                   headers={"Referer": list_url, "Content-Type": "application/x-www-form-urlencoded"})
        t = dec(r)
        g = re.findall(r"do_detail\('([^']+)'\)", t)
        w(f"  POST pageNumber={pg} -> {r.status_code} len={len(t)} do_detail={len(g)} 首={g[:2]}")

    w("\n===== 眉山 Session 详情（do_detail 到 list_content_ldxxnew.jsp）=====")
    action = "http://www.ms.gov.cn/old13/list_content_ldxxnew.jsp?urltype=tree.TreeTempUrl&wbtreeid=7433"
    if g0:
        r = s.post(action, data={"guid": g0[0]}, timeout=25,
                   headers={"Referer": list_url, "Content-Type": "application/x-www-form-urlencoded"})
        t = dec(r)
        w(f"  -> {r.status_code} len={len(t)}")
        body = re.sub(r"(?s)<script.*?</script>", " ", t)
        body = re.sub(r"(?s)<style.*?</style>", " ", body)
        txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body))
        j = txt.find("信件流水号")
        w("  " + txt[max(0, j):j + 1400])


if __name__ == "__main__":
    main()
