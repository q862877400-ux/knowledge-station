"""city-sc-probe9：自贡 szxx API / 绵阳 nav 源 / 攀枝花 mailbox.js ajax。"""
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

    # ---- 自贡 szxx ----
    w("## 自贡 /zgsrmzf/szxx/pc/list.html")
    r = get("https://www.zg.gov.cn/zgsrmzf/szxx/pc/list.html")
    if hasattr(r, "text"):
        t = r.text
        w(f"  status={r.status_code} len={len(t)}")
        for m in re.finditer(r'<script[^>]+src=["\']([^"\']+)["\']', t):
            w("     SRC " + m.group(1))
        for m in re.finditer(r'url\s*[:=]\s*["\']([^"\']+)["\']', t):
            w("     URL " + m.group(1))
        eps = sorted(set(re.findall(r'["\'](/[A-Za-z][A-Za-z0-9_/\.\-]*(?:Json|json|List|list|query|Query|do)[A-Za-z0-9_/\.\-]*)["\']', t)))
        for e in eps[:20]:
            w("     EP " + e)
    w("\n## 自贡 collect_list.js")
    r = get("https://www.zg.gov.cn/zgsrmzf/pc2025/hd/js/collect_list.js")
    if hasattr(r, "text"):
        t = r.text
        w(f"  status={r.status_code} len={len(t)}")
        for m in re.finditer(r'url\s*[:=]\s*["\']([^"\']+)["\']', t):
            w("     URL " + m.group(1))
        eps = sorted(set(re.findall(r'["\'](/[A-Za-z][A-Za-z0-9_/\.\-]*(?:Json|json|List|list|query|Query|do)[A-Za-z0-9_/\.\-]*)["\']', t)))
        for e in eps[:25]:
            w("     EP " + e)

    # ---- 绵阳 nav ----
    w("\n## 绵阳 首页 script src + 互动关键词上下文")
    r = get("https://www.my.gov.cn/")
    if hasattr(r, "text"):
        t = r.text
        for m in re.finditer(r'<script[^>]+src=["\']([^"\']+)["\']', t):
            w("     SRC " + m.group(1))
        for kw in ("互动", "信箱", "12345", "hdjl", "szxx", "留言"):
            idx = [m.start() for m in re.finditer(kw, t)]
            w(f"     {kw}: {len(idx)}")
            for i in idx[:2]:
                w("        ..." + t[max(0, i - 100):i + 100].replace("\n", " "))

    # ---- 攀枝花 mailbox.js ajax ----
    w("\n## 攀枝花 mailbox.js ajax 上下文")
    r = get("http://www.panzhihua.gov.cn/static/js/mailbox.js")
    if hasattr(r, "text"):
        t = r.text
        for m in re.finditer(r'url\s*[:=]\s*([^,\n]{0,120})', t):
            w("     URL " + m.group(1).strip())
        for m in re.finditer(r'(getMail|getLetter|MailList|mailList|List|list)\s*[:(]', t):
            s = max(0, m.start() - 60)
            w("     HIT ..." + t[s:m.end() + 120].replace("\n", " ")[:200])


if __name__ == "__main__":
    main()
