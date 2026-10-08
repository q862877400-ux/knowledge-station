"""city-sc-probe38：达州 xinxiang 原始 HTML；眉山 list_content_ldxxnew.jsp 翻页+详情。"""
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


def get(u, ref=None, **kw):
    h = {"User-Agent": UA}
    if ref:
        h["Referer"] = ref
    try:
        return requests.get(u, timeout=25, allow_redirects=True, headers=h, **kw)
    except Exception as e:  # noqa: BLE001
        return e


def post(u, data=None, ref=None):
    h = {"User-Agent": UA, "Content-Type": "application/x-www-form-urlencoded"}
    if ref:
        h["Referer"] = ref
    try:
        return requests.post(u, data=data, timeout=25, allow_redirects=True, headers=h)
    except Exception as e:  # noqa: BLE001
        return e


def dec(r):
    try:
        return r.content.decode("utf-8")
    except Exception:  # noqa: BLE001
        return r.text


def main():
    OUT.write_text("", encoding="utf-8")

    w("===== 达州 /xinxiang/ 原始 HTML 片段 =====")
    r = get("https://www.dazhou.gov.cn/xinxiang/", ref="https://www.dazhou.gov.cn/")
    if hasattr(r, "status_code") and r.status_code == 200:
        t = dec(r)
        w(f"  len={len(t)}")
        for kw in ("来信选登", "来信统计", "href", "src=", "location", "window.open", "ifram"):
            for m in re.finditer(re.escape(kw), t):
                i = m.start()
                w(f"  [{kw}] " + re.sub(r"\s+", " ", t[max(0, i - 100):i + 160])[:260])
                break

    w("\n===== 达州 首页 AJAX 片段（书记信箱/市长信箱区域）=====")
    r = get("https://www.dazhou.gov.cn/", ref="https://www.dazhou.gov.cn/")
    if hasattr(r, "status_code") and r.status_code == 200:
        t = dec(r)
        for kw in ("xinxiang", "dzmyzjList", "dzmyzjDetail", "书记信箱"):
            for m in re.finditer(re.escape(kw), t):
                i = m.start()
                w(f"  [{kw}] " + re.sub(r"\s+", " ", t[max(0, i - 150):i + 220])[:360])
                break

    w("\n===== 眉山 POST 到 list_content_ldxxnew.jsp（翻页 pageNumber245916=2）=====")
    action = "http://www.ms.gov.cn/old13/list_content_ldxxnew.jsp?urltype=tree.TreeTempUrl&wbtreeid=7433"
    ref = "http://www.ms.gov.cn/old13/list_ldxx.jsp?urltype=tree.TreeTempUrl&wbtreeid=5761"
    r = post(action, data={"pageNumber245916": "2"}, ref=ref)
    if hasattr(r, "status_code") and r.status_code == 200:
        t = dec(r)
        guids = re.findall(r"do_detail\('([^']+)'\)", t)
        w(f"  -> {r.status_code} len={len(t)} do_detail={len(guids)} 首 guid={guids[:3]}")
        w("  " + re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"(?s)<script.*?</script>", " ", t)))[:500])
    else:
        w(f"  -> {getattr(r, 'status_code', r)}")

    w("\n===== 眉山 POST 详情（guid=c592f5c1-…）=====")
    g = "c592f5c1-26f5-416b-9daa-2677c2eaad2c"
    r = post(action, data={"guid": g}, ref=ref)
    if hasattr(r, "status_code") and r.status_code == 200:
        t = dec(r)
        w(f"  -> {r.status_code} len={len(t)}")
        body = re.sub(r"(?s)<script.*?</script>", " ", t)
        body = re.sub(r"(?s)<style.*?</style>", " ", body)
        txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body))
        j = txt.find("信件流水号")
        w("  " + txt[max(0, j):j + 1200])
    else:
        w(f"  -> {getattr(r, 'status_code', r)}")


if __name__ == "__main__":
    main()
