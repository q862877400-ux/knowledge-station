"""city-sc-probe5：泸州详情 / 攀枝花信箱接口 / 绵阳重测 / 德阳互动入口。"""
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

    # ---- 泸州 详情 ----
    w("## 泸州 详情 /LetterBox/15046")
    r = get("https://www.luzhou.gov.cn/LetterBox/15046")
    if hasattr(r, "text"):
        w(f"  status={r.status_code} len={len(r.text)}")
        txt = re.sub(r"<script[\s\S]*?</script>", " ", r.text)
        txt = re.sub(r"<[^>]+>", " ", txt)
        txt = re.sub(r"\s+", " ", txt).strip()
        w("  text=" + txt[:900])

    # ---- 攀枝花 市政府信箱 内联 JS ----
    w("\n## 攀枝花 /hdcy/szxx/szxx/index.shtml 内联 JS")
    r = get("http://www.panzhihua.gov.cn/hdcy/szxx/szxx/index.shtml")
    if hasattr(r, "text"):
        t = r.text
        w(f"  status={r.status_code} len={len(t)}")
        for m in re.finditer(r'url\s*:\s*["\']([^"\']+)["\']', t):
            w("     url: " + m.group(1))
        for m in re.finditer(r'(ajax|getJSON|\.load)\s*\(', t):
            s = max(0, m.start() - 120)
            w("     JS ..." + t[s:m.start() + 260].replace("\n", " ")[:360])

    # ---- 绵阳 重测（独立会话，打印最终 URL + title）----
    w("\n## 绵阳 重测")
    for u in ("https://www.mianyang.gov.cn/", "http://www.mianyang.gov.cn/",
              "https://www.mianyang.gov.cn/hdcy/index.shtml"):
        r = get(u)
        if hasattr(r, "text"):
            ti = re.search(r"<title>([^<]*)</title>", r.text)
            w(f"  {u} -> {r.status_code} len={len(r.text)} final={r.url} title={ti.group(1)[:50] if ti else '?'}")
        else:
            w(f"  {u} -> ERR {type(r).__name__} {str(r)[:50]}")

    # ---- 德阳 互动入口 ----
    w("\n## 德阳 互动入口探测")
    for u in ("https://www.deyang.gov.cn/hdjl/index.html",
              "https://www.deyang.gov.cn/szxxt/index.html",
              "https://www.deyang.gov.cn/gzcy/",
              "https://www.deyang.gov.cn/zmhd/",
              "https://www.deyang.gov.cn/hdcy/"):
        r = get(u)
        if hasattr(r, "text"):
            ti = re.search(r"<title>([^<]*)</title>", r.text)
            w(f"  {u} -> {r.status_code} len={len(r.text)} title={ti.group(1)[:40] if ti else '?'}")
        else:
            w(f"  {u} -> ERR {type(r).__name__}")


if __name__ == "__main__":
    main()
