"""city-sc-probe8：攀枝花 mailbox.js / 自贡 yjzj API / 绵阳 nav 全链接。"""
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

    # ---- 攀枝花 mailbox.js ----
    w("## 攀枝花 /static/js/mailbox.js")
    r = get("http://www.panzhihua.gov.cn/static/js/mailbox.js")
    if hasattr(r, "text"):
        t = r.text
        w(f"  status={r.status_code} len={len(t)}")
        for m in re.finditer(r'["\'](/webapp/[A-Za-z0-9_/]+)["\']', t):
            w("     EP " + m.group(1))
        for m in re.finditer(r'url\s*:\s*["\']([^"\']+)["\']', t):
            w("     URL " + m.group(1))
        # 找 list 相关函数
        for m in re.finditer(r'function\s+([A-Za-z_]+)\s*\(', t):
            pass
        eps = sorted(set(re.findall(r'/webapp/[A-Za-z0-9_/]+', t)))
        w("     ALL " + str(eps))

    # ---- 自贡 yjzj ----
    w("\n## 自贡 /zgsrmzf/yjzj/pc/list.html")
    r = get("https://www.zg.gov.cn/zgsrmzf/yjzj/pc/list.html")
    if hasattr(r, "text"):
        t = r.text
        w(f"  status={r.status_code} len={len(t)}")
        for m in re.finditer(r'url\s*[:=]\s*["\']([^"\']+)["\']', t):
            w("     URL " + m.group(1))
        eps = sorted(set(re.findall(r'["\'](/[A-Za-z][A-Za-z0-9_/\.\-]*(?:\.do|\.json|List|list|Json|json|query|Query)[A-Za-z0-9_/\.\-]*)["\']', t)))
        for e in eps[:20]:
            w("     EP " + e)

    # 自贡 首页 nav 全链接
    w("\n## 自贡 首页 全部 nav a（前 70）")
    r = get("https://www.zg.gov.cn/")
    if hasattr(r, "text"):
        for m in list(re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]{1,24})</a>', r.text))[:70]:
            w(f"     [{m.group(2).strip()}] {m.group(1)}")

    # ---- 绵阳 nav 全链接 ----
    w("\n## 绵阳 首页 全部 a（前 80）")
    r = get("https://www.my.gov.cn/")
    if hasattr(r, "text"):
        for m in list(re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]{1,24})</a>', r.text))[:80]:
            w(f"     [{m.group(2).strip()}] {m.group(1)}")


if __name__ == "__main__":
    main()
