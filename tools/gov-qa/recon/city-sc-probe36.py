"""city-sc-probe36：达州 xinxiang/ + hdjl 列表结构；眉山 WCM 分页/详情。"""
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


def dec(r):
    try:
        return r.content.decode("utf-8")
    except Exception:  # noqa: BLE001
        return r.text


def main():
    OUT.write_text("", encoding="utf-8")

    w("===== 达州 市长信箱 /xinxiang/ =====")
    for u in ["https://www.dazhou.gov.cn/xinxiang/",
              "https://www.dazhou.gov.cn/xinxiang/index.html",
              "https://www.dazhou.gov.cn/xinxiang/list.html"]:
        r = get(u, ref="https://www.dazhou.gov.cn/")
        if hasattr(r, "status_code"):
            ti = ""
            mm = re.search(r"<title>(.*?)</title>", dec(r), re.S)
            if mm:
                ti = re.sub(r"\s+", " ", mm.group(1))[:50]
            w(f"  {u} -> {r.status_code} ct={r.headers.get('content-type','')} len={len(r.content)} title={ti}")

    w("\n===== 达州 news-list-hdjl.html 正文与 AJAX =====")
    r = get("https://www.dazhou.gov.cn/news-list-hdjl.html", ref="https://www.dazhou.gov.cn/")
    if hasattr(r, "status_code") and r.status_code == 200:
        t = dec(r)
        # 找 list 容器
        for m in re.finditer(r"(?s)<(ul|div)[^>]*(?:list|hdjl|letter)[^>]*>(.{0,900})", t):
            seg = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(0)))
            if len(seg.strip()) > 80:
                w("  [container] " + seg[:300])
        # 所有 .ajax / url:
        for m in re.finditer(r"(\.ajax|url\s*:|getList|getlist|/index\.php\?s=)", t):
            i = m.start()
            w(f"  [{m.group(1)}] " + re.sub(r"\s+", " ", t[max(0, i - 80):i + 260])[:340])
        # 分页链接
        for m in re.finditer(r'href=["\']([^"\']*(?:hdjl|page)[^"\']*)["\']', t):
            w("  PAGELINK " + m.group(1)[:140])

    w("\n===== 眉山 WCM changeleadermailpage 函数 + 详情链接 =====")
    u = "http://www.ms.gov.cn/old13/list_ldxx.jsp?urltype=tree.TreeTempUrl&wbtreeid=5761"
    r = get(u, ref="http://www.ms.gov.cn/17_hudong/hdjl_index.jsp?urltype=tree.TreeTempUrl&wbtreeid=1010")
    if hasattr(r, "status_code") and r.status_code == 200:
        t = dec(r)
        i = t.find("changeleadermailpage")
        if i > 0:
            w("  [js] " + re.sub(r"\s+", " ", t[max(0, i - 400):i + 900])[:1300])
        # 详情链接
        w("  --- 信件条目链接 ---")
        for m in re.finditer(r'href=["\']([^"\']*(?:ldxx|mail|detail|nr|content|show)[^"\']*)["\']', t):
            h = m.group(1)
            if "jsp" in h or "htm" in h:
                w("  D " + h[:150])
        # 信件行
        for m in re.finditer(r'(?:ldxx|mail)[^"\']*?(\d{4,})', t):
            pass
        body = re.sub(r"(?s)<script.*?</script>", " ", t)
        j = body.find("信件流水号")
        if j > 0:
            w("  [list area] " + re.sub(r"\s+", " ", body[j:j + 1200])[:1000])

    w("\n===== 眉山 明细候选（从列表抓 id）=====")
    # 常见 WCM 明细页
    for u in ["http://www.ms.gov.cn/old13/content_ldxx.jsp?urltype=tree.TreeTempUrl&wbtreeid=5761",
              "http://www.ms.gov.cn/old13/ldxx_nr.jsp?urltype=tree.TreeTempUrl&wbtreeid=5761"]:
        rr = get(u, ref="http://www.ms.gov.cn/")
        if hasattr(rr, "status_code"):
            w(f"  {u} -> {rr.status_code} len={len(rr.content)}")


if __name__ == "__main__":
    main()
