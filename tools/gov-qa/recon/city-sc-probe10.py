"""city-sc-probe10：攀枝花 letterListJson 实测 / 自贡 collect_list.js 全文 / 绵阳 nav 源。"""
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


def get(url, ref=None, **kw):
    c = requests.Session()
    c.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    if ref:
        c.headers["Referer"] = ref
    try:
        return c.get(url, timeout=25, allow_redirects=True, **kw)
    except Exception as e:  # noqa: BLE001
        return e


def main():
    OUT.write_text("", encoding="utf-8")
    REF = "http://www.panzhihua.gov.cn/hdcy/szxx/szxx/index.shtml"

    # ---- 攀枝花 letterListJson ----
    w("## 攀枝花 /mailbox/letterListJson 实测")
    for base in ("http://www.panzhihua.gov.cn", "http://www.panzhihua.gov.cn/webapp"):
        for params in ({"pageIndex": 1, "pageSize": 5},
                       {"pageNum": 1, "pageSize": 5},
                       {"id": 2, "pageIndex": 1, "pageSize": 5},
                       {"organId": 2, "pageIndex": 1, "pageSize": 5}):
            rr = get(base + "/mailbox/letterListJson", ref=REF, params=params)
            if hasattr(rr, "text"):
                w(f"  {base} {params} -> {rr.status_code} ct={rr.headers.get('content-type')} len={len(rr.text)} {rr.text[:180]!r}")
            else:
                w(f"  {base} {params} -> ERR {type(rr).__name__}")

    # ---- 攀枝花 mailbox.js letterListJson 调用上下文 ----
    w("\n## 攀枝花 mailbox.js letterListJson 调用上下文")
    r = get("http://www.panzhihua.gov.cn/static/js/mailbox.js")
    if hasattr(r, "text"):
        t = r.text
        for m in re.finditer(r'letterListJson', t):
            s = max(0, m.start() - 200)
            w("  ..." + t[s:m.end() + 400].replace("\n", " ")[:600])
            break

    # ---- 自贡 collect_list.js 全文 ----
    w("\n## 自贡 collect_list.js 全文")
    r = get("https://www.zg.gov.cn/zgsrmzf/pc2025/hd/js/collect_list.js")
    if hasattr(r, "text"):
        w(r.text[:2500])

    # ---- 自贡 szxx list.html 内联 ----
    w("\n## 自贡 szxx/pc/list.html 内联 JS")
    r = get("https://www.zg.gov.cn/zgsrmzf/szxx/pc/list.html")
    if hasattr(r, "text"):
        for m in re.finditer(r'<script(?![^>]*src)[^>]*>([\s\S]{0,1200}?)</script>', r.text):
            w("  JS>>> " + m.group(1).strip()[:1000])

    # ---- 绵阳 nav ----
    w("\n## 绵阳 首页 nav HTML 片段")
    r = get("https://www.my.gov.cn/")
    if hasattr(r, "text"):
        t = r.text
        # 找 header/nav
        m = re.search(r'<div[^>]*class="[^"]*nav[^"]*"[\s\S]{0,4000}', t)
        if m:
            seg = re.sub(r"\s+", " ", m.group(0))
            w("  NAV>>> " + seg[:2500])
        # 所有 a href（含嵌套）
        for mm in list(re.finditer(r'href=["\']([^"\']+)["\']', t))[:80]:
            pass


if __name__ == "__main__":
    main()
