"""city-sc-probe40：达州 xinxiang 子页枚举；眉山 GET 方式详情/翻页。"""
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

    w("===== 达州 /xinxiang/ 所有 data-name =====")
    r = s.get("https://www.dazhou.gov.cn/xinxiang/", timeout=25)
    t = dec(r)
    names = re.findall(r'data-name="([^"]+)"', t)
    w("  data-name: " + ", ".join(names))
    for n in names:
        u = "https://www.dazhou.gov.cn/xinxiang/" + n
        rr = s.get(u, timeout=25, headers={"Referer": "https://www.dazhou.gov.cn/xinxiang/"})
        w(f"  {n} -> {rr.status_code} ct={rr.headers.get('content-type','')} len={len(rr.content)}")
        if rr.status_code == 200 and len(rr.content) > 300:
            tt = dec(rr)
            w("     " + re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", tt))[:300])
            for m in re.finditer(r"(\.ajax|url\s*:|/index\.php|url\s*\+|\.json|getList|page)", tt):
                i = m.start()
                w(f"     [{m.group(1)}] " + re.sub(r"\s+", " ", tt[max(0, i - 50):i + 200])[:260])
                break
    # js 里的 url 变量
    rj = s.get("https://www.dazhou.gov.cn/xinxiang/js/index.js", timeout=25)
    tj = dec(rj)
    for m in re.finditer(r"var\s+url\s*=\s*([^;]+);", tj):
        w("  [url var] " + m.group(1)[:200])

    w("\n===== 眉山 GET 详情（guid 作为 query）=====")
    g = "c592f5c1-26f5-416b-9daa-2677c2eaad2c"
    for u in [f"http://www.ms.gov.cn/old13/list_content_ldxxnew.jsp?urltype=tree.TreeTempUrl&wbtreeid=7433&guid={g}",
              f"http://www.ms.gov.cn/old13/list_content_ldxxnew.jsp?urltype=tree.TreeTempUrl&wbtreeid=7433&guid={g}&guid=",
              f"http://www.ms.gov.cn/old13/list_ldxx.jsp?urltype=tree.TreeTempUrl&wbtreeid=5761&guid={g}"]:
        rr = s.get(u, timeout=25, headers={"Referer": "http://www.ms.gov.cn/old13/list_ldxx.jsp?urltype=tree.TreeTempUrl&wbtreeid=5761"})
        tt = dec(rr)
        has = "暂无数据" not in tt
        w(f"  -> {rr.status_code} len={len(tt)} 有数据={has}")
        if has:
            body = re.sub(r"(?s)<script.*?</script>", " ", tt)
            body = re.sub(r"(?s)<style.*?</style>", " ", body)
            txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body))
            j = txt.find("信件流水号")
            w("     " + txt[max(0, j):j + 1000])

    w("\n===== 眉山 GET 翻页（pageNumber245916 query）=====")
    for pg in (2, 3):
        u = f"http://www.ms.gov.cn/old13/list_ldxx.jsp?urltype=tree.TreeTempUrl&wbtreeid=5761&pageNumber245916={pg}"
        rr = s.get(u, timeout=25, headers={"Referer": "http://www.ms.gov.cn/old13/list_ldxx.jsp?urltype=tree.TreeTempUrl&wbtreeid=5761"})
        tt = dec(rr)
        gs = re.findall(r"do_detail\('([^']+)'\)", tt)
        w(f"  pageNumber={pg} -> {rr.status_code} len={len(tt)} 首guid={gs[:2]}")


if __name__ == "__main__":
    main()
