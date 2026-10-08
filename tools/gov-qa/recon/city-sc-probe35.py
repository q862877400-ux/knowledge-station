"""city-sc-probe35：达州 ThinkPHP 民议征集 JSON + 眉山 WCM 来信选登。"""
import json
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
    h = {"User-Agent": UA, "X-Requested-With": "XMLHttpRequest"}
    if ref:
        h["Referer"] = ref
    try:
        return requests.get(u, timeout=20, allow_redirects=True, headers=h, **kw)
    except Exception as e:  # noqa: BLE001
        return e


def dec(r):
    try:
        return r.content.decode("utf-8")
    except Exception:  # noqa: BLE001
        return r.text


def main():
    OUT.write_text("", encoding="utf-8")

    w("===== 达州 民议征集列表 JSON =====")
    for page in (1, 2):
        u = f"https://www.dazhou.gov.cn/index.php?s=dzmyzj&c=home&m=dzmyzjList&page={page}"
        r = get(u, ref="https://www.dazhou.gov.cn/")
        if hasattr(r, "status_code"):
            w(f"  {u} -> {r.status_code} ct={r.headers.get('content-type','')} len={len(r.content)}")
            if r.status_code == 200:
                w("  " + dec(r)[:900])
        else:
            w(f"  {u} -> {r}")

    w("\n===== 达州 民议征集详情 =====")
    u = "https://www.dazhou.gov.cn/index.php?s=dzmyzj&c=home&m=dzmyzjDetail&id=1"
    r = get(u, ref="https://www.dazhou.gov.cn/")
    if hasattr(r, "status_code"):
        w(f"  id=1 -> {r.status_code} ct={r.headers.get('content-type','')} len={len(r.content)}")
        w("  " + dec(r)[:600])

    w("\n===== 达州 书记信箱 news-list-hdjl.html 列表条目 =====")
    r = get("https://www.dazhou.gov.cn/news-list-hdjl.html", ref="https://www.dazhou.gov.cn/")
    if hasattr(r, "status_code") and r.status_code == 200:
        t = dec(r)
        # 找信件条目
        for m in re.finditer(r'news-show-(\d+)\.html', t):
            i = m.start()
            seg = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t[max(0, i - 300):i + 100]))
            w(f"  [show {m.group(1)}] {seg[:200]}")
            break
        # ajax
        for m in re.finditer(r"(url\s*:|\.ajax|getList|/index\.php)", t):
            i = m.start()
            w(f"  [{m.group(1)}] " + re.sub(r"\s+", " ", t[max(0, i - 60):i + 220])[:280])
            break
        # 分页
        for kw in ("page=", "list-hdjl", "totalPage", "pageCount"):
            for m in re.finditer(re.escape(kw), t):
                i = m.start()
                w(f"  [{kw}] " + re.sub(r"\s+", " ", t[max(0, i - 80):i + 120])[:200])
                break

    w("\n===== 眉山 WCM 来信选登 list_ldxx.jsp =====")
    u = "http://www.ms.gov.cn/old13/list_ldxx.jsp?urltype=tree.TreeTempUrl&wbtreeid=5761"
    r = get(u, ref="http://www.ms.gov.cn/17_hudong/hdjl_index.jsp?urltype=tree.TreeTempUrl&wbtreeid=1010")
    if hasattr(r, "status_code") and r.status_code == 200:
        t = dec(r)
        w(f"  len={len(t)}")
        for m in re.finditer(r'href=["\']([^"\'#]+)["\']', t):
            h = m.group(1)
            if any(k in h for k in ("ldxx", "detail", "show", "content", "nr.jsp", "list")):
                w("  H " + h[:150])
        body = re.sub(r"(?s)<script.*?</script>", " ", t)
        body = re.sub(r"(?s)<style.*?</style>", " ", body)
        w("  " + re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body))[:700])
        # 分页
        for kw in ("page", "Page", "下一页", "共"):
            for m in re.finditer(re.escape(kw), t):
                i = m.start()
                w(f"  [{kw}] " + re.sub(r"\s+", " ", t[max(0, i - 80):i + 120])[:200])
                break
    else:
        w(f"  -> {getattr(r, 'status_code', r)}")


if __name__ == "__main__":
    main()
