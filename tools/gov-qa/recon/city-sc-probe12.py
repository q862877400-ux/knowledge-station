"""city-sc-probe12：攀枝花 searchLetterPager 调用实参 / 自贡 szxx 页尾脚本。"""
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

    # ---- 攀枝花 searchLetterPager 调用 ----
    w("## 攀枝花 页面内 searchLetterPager 调用")
    r = get("http://www.panzhihua.gov.cn/hdcy/szxx/szxx/index.shtml")
    if hasattr(r, "text"):
        t = r.text
        for m in re.finditer(r'searchLetterPager', t):
            s = max(0, m.start() - 100)
            w("  ..." + re.sub(r"\s+", " ", t[s:m.end() + 500])[:650])
        for m in re.finditer(r'channelId\s*[:=]\s*["\']?([A-Za-z0-9_\-]+)', t):
            w("  channelId=" + m.group(1))
        for m in re.finditer(r'mailType\s*[:=]\s*["\']?([A-Za-z0-9_\-]*)', t):
            w("  mailType=" + m.group(1))

    # ---- 攀枝花 试 channelId 候选 ----
    w("\n## 攀枝花 channelId 候选实测")
    for cid in ("1", "2", "3", "4", "szxx", "mayor"):
        rr = get("http://www.panzhihua.gov.cn/webapp/mailbox/letterListJson",
                 ref="http://www.panzhihua.gov.cn/hdcy/szxx/szxx/index.shtml",
                 params={"channelId": cid, "mailType": "1", "pageNum": 1, "pageSize": 3, "orderStr": "replytime"})
        if hasattr(rr, "text"):
            w(f"  channelId={cid} -> {rr.status_code} len={len(rr.text)} {rr.text[:120]!r}")

    # ---- 自贡 szxx 页尾 ----
    w("\n## 自贡 szxx/pc/list.html 全文尾部")
    r = get("https://www.zg.gov.cn/zgsrmzf/szxx/pc/list.html")
    if hasattr(r, "text"):
        t = r.text
        w(t[3000:])
        w("  --- script src ---")
        for m in re.finditer(r'<script[^>]+src=["\']([^"\']+)["\']', t):
            w("     SRC " + m.group(1))


if __name__ == "__main__":
    main()
