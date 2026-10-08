"""city-sc-probe27：宜宾12345/雅安/眉山/达州/乐山 是否有公开信件列表。"""
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


def get(u, ref=None):
    h = {"User-Agent": UA}
    if ref:
        h["Referer"] = ref
    try:
        return requests.get(u, timeout=20, allow_redirects=True, headers=h)
    except Exception as e:  # noqa: BLE001
        return e


def probe(name, u, ref=None):
    w(f"\n===== {name} {u} =====")
    r = get(u, ref)
    if not hasattr(r, "status_code"):
        w(f"  ERR {r}")
        return
    ct = r.headers.get("content-type", "")[:40]
    w(f"  -> {r.status_code} len={len(r.text)} ct={ct} final={r.url}")
    if r.status_code != 200:
        return
    t = r.text
    for m in re.finditer(r'<script[^>]+src=["\']([^"\']+)["\']', t):
        s = m.group(1)
        if any(k in s.lower() for k in ("mail", "letter", "list", "api", "interaction", "common", "detail")):
            w("     [js] " + s[:140])
    for m in re.finditer(r'["\'](/?[A-Za-z0-9_\-/]*(?:api|letter|mail|list|find|page|detail)[A-Za-z0-9_\-/]*)["\']', t, re.I):
        w("     [api?] " + m.group(1)[:120])
    cnt = 0
    for m in re.finditer(r'href=["\']([^"\'#]*(?:letter|mail|detail|article|content|show)[^"\'#]*)["\']', t, re.I):
        cnt += 1
        if cnt <= 6:
            w("     [h] " + m.group(1)[:130])
    if cnt:
        w(f"     ... 共 {cnt} 条候选")


def main():
    OUT.write_text("", encoding="utf-8")
    probe("宜宾-12345门户", "http://12345.zwfwhfgjjfzj.yibin.gov.cn/WriteLetters/WriteLetter")
    probe("宜宾-lxxd-detail", "http://www.yibin.gov.cn/hdjl/szywm/xjcx/detail_9008.html")
    probe("雅安-mail", "https://www.yaan.gov.cn/mail/index.html")
    probe("雅安-12345", "https://www.yaan.gov.cn/12345.html")
    probe("眉山-swmail", "https://www.ms.gov.cn/mail12345/swmail.jsp?urltype=tree.TreeTempUrl&wbtreeid=5999")
    probe("达州-hdjl", "https://www.dazhou.gov.cn/news-list-hdjl.html")
    probe("乐山-robot", "https://www.leshan.gov.cn/front/interaction/robot")
    probe("乐山-wdzsk", "https://www.leshan.gov.cn/front/wdzsk/index")


if __name__ == "__main__":
    main()
