"""city-sc-probe21：第 7~21 市 互动落地页深挖 —— 列 script、条目链接、api 线索。"""
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
OUT = Path(__file__).with_suffix(".txt")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"

PAGES = [
    ("遂宁", "https://www.suining.gov.cn/szxx.html"),
    ("乐山", "https://www.leshan.gov.cn/lsswszf/zmhd/index.html"),
    ("南充", "https://www.nanchong.gov.cn/hdjl/"),
    ("南充-szxx", "https://www.nanchong.gov.cn/hdjl/szxx/"),
    ("眉山-swmail", "https://www.ms.gov.cn/mail12345/swmail.jsp?urltype=tree.TreeTempUrl&wbtreeid=5999"),
    ("宜宾", "https://www.yibin.gov.cn/hdjl/szywm/wyxx/"),
    ("达州", "https://www.dazhou.gov.cn/news-list-hdjl.html"),
    ("巴中-szxx", "https://www.cnbz.gov.cn/zmhd/ldxx/szxx/index.html"),
    ("阿坝-hdmailbox", "https://www.abazhou.gov.cn/abazhou/c101014/hd_mailbox.shtml"),
    ("阿坝-12345", "https://www.abazhou.gov.cn/abazhou/rexian/12345rx.shtml"),
    ("甘孜", "https://www.gzz.gov.cn/hdjl"),
    ("凉山-zmhd", "http://www.lsz.gov.cn/hdjl/zmhd/"),
    ("凉山-12345", "http://12345.lsz.gov.cn/"),
    ("广元-首页再扫", "https://www.gy.gov.cn/"),
]
SCRIPT_RE = re.compile(r'<script[^>]+src=["\']([^"\']+)["\']', re.I)
HREF_RE = re.compile(r'href=["\']([^"\'#]+)["\']')
ITEM_RE = re.compile(r'(20\d{6}|t20\d{6}|/\d{6,}|id=\d+|infoId|contentId|mailId|letterId|/\d{4}/|detail|show)')


def w(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    with OUT.open("a", encoding="utf-8") as f:
        f.write(s + "\n")


def get(u):
    try:
        return requests.get(u, timeout=25, allow_redirects=True, headers={"User-Agent": UA})
    except Exception as e:  # noqa: BLE001
        return e


def main():
    OUT.write_text("", encoding="utf-8")
    for name, u in PAGES:
        w(f"\n===== {name} {u} =====")
        r = get(u)
        if not hasattr(r, "status_code"):
            w(f"  ERR {r}")
            continue
        w(f"  -> {r.status_code} len={len(r.text)} final={r.url}")
        if r.status_code != 200:
            continue
        t = r.text
        for m in SCRIPT_RE.finditer(t):
            src = m.group(1)
            if any(k in src.lower() for k in ("mail", "hdjl", "zmhd", "szxx", "list", "api", "common", "config", "index", "interaction")):
                w("     [js] " + src[:150])
        # api-ish strings
        for m in re.finditer(r'["\'](/[A-Za-z0-9_\-/]*(?:api|mail|letter|list|detail|interaction|front)[A-Za-z0-9_\-/]*)["\']', t, re.I):
            w("     [api?] " + m.group(1)[:120])
        # 条目链接
        seen = set()
        cnt = 0
        for m in HREF_RE.finditer(t):
            h = m.group(1).strip()
            if h in seen:
                continue
            if ITEM_RE.search(h) and any(k in h.lower() for k in ("mail", "letter", "detail", "show", "hdjl", "szxx", "zmhd", "content", "info", "202")):
                seen.add(h)
                cnt += 1
                if cnt <= 8:
                    w("     [item] " + h[:140])
        if cnt:
            w(f"     ... 共 {cnt} 条候选条目链接")


if __name__ == "__main__":
    main()
