"""city-sc-probe15：德阳 appeal 模块 / 绵阳互动栏目定位。"""
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


def get(c, url, ref=None, **kw):
    h = {"Referer": ref} if ref else {}
    try:
        return c.get(url, timeout=25, allow_redirects=True, headers=h, **kw)
    except Exception as e:  # noqa: BLE001
        return e


def main():
    OUT.write_text("", encoding="utf-8")
    c = requests.Session()
    c.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

    # ---- 德阳 appeal ----
    w("## 德阳 /appeal/list.jsp")
    for u in ("https://www.deyang.gov.cn/appeal/list.jsp?model_id=1&tm_id=26",
              "https://www.deyang.gov.cn/appeal/list.jsp?model_id=18&tm_id=26",
              "https://www.deyang.gov.cn/appeal/list.jsp?model_id=18&tm_id=28"):
        r = get(c, u, ref="https://www.deyang.gov.cn/")
        if hasattr(r, "text"):
            ti = re.search(r"<title>([^<]*)</title>", r.text)
            w(f"  {u} -> {r.status_code} len={len(r.text)} title={ti.group(1).strip()[:50] if ti else '?'}")
            for m in re.finditer(r'url\s*[:=]\s*["\']([^"\']+)["\']', r.text):
                w("     URL " + m.group(1))
            eps = sorted(set(re.findall(r'["\'](/[A-Za-z][A-Za-z0-9_/\.\-]*(?:\.jsp|\.do|Json|json|List|list)[A-Za-z0-9_/\.\-?=&]*)["\']', r.text)))
            for e in eps[:20]:
                w("     EP " + e)
            # 详情链接
            for m in list(re.finditer(r'href=["\']([^"\']*appeal[^"\']*)["\'][^>]*>([^<]{2,40})</a>', r.text))[:15]:
                w(f"     L [{m.group(2).strip()[:30]}] {m.group(1)}")
        else:
            w(f"  {u} -> ERR {type(r).__name__}")

    # 德阳 appeal 列表 JSON 试
    w("\n## 德阳 appeal listJson 试")
    for u in ("https://www.deyang.gov.cn/appeal/listJson.jsp?model_id=1&tm_id=26&pageIndex=1&pageSize=5",
              "https://www.deyang.gov.cn/appeal/getList.jsp?model_id=1&tm_id=26&page=1",
              "https://www.deyang.gov.cn/appeal/list.jsp?model_id=1&tm_id=26&pageIndex=2"):
        r = get(c, u, ref="https://www.deyang.gov.cn/appeal/list.jsp?model_id=1&tm_id=26")
        if hasattr(r, "text"):
            w(f"  {u} -> {r.status_code} ct={r.headers.get('content-type')} len={len(r.text)} {r.text[:150]!r}")

    # ---- 绵阳 找互动 ----
    w("\n## 绵阳 首页 nav 脚本/链接（含 互动 关键）")
    r = get(c, "https://www.my.gov.cn/")
    if hasattr(r, "text"):
        t = r.text
        for kw in ("互动", "信箱", "12345", "hdjl", "szxx", "zmhd", "app", "hdcy"):
            idx = [m.start() for m in re.finditer(kw, t, re.I)]
            if idx:
                w(f"  {kw}: {len(idx)}")
                for i in idx[:2]:
                    w("     ..." + t[max(0, i - 90):i + 90].replace("\n", " "))
        # 所有 list.shtml 链接（栏目）
        for h in sorted(set(re.findall(r'href=["\'](/mysrmzf/c\d+[^"\']*)["\']', t)))[:40]:
            w("   C " + h)


if __name__ == "__main__":
    main()
