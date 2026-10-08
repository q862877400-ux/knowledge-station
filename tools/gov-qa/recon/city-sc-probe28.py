"""city-sc-probe28：宜宾 DoExcerpts/List + 雅安 leader/detail + 乐山 wdzsk 问答库。"""
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


def get(u, params=None, ref=None):
    h = {"User-Agent": UA}
    if ref:
        h["Referer"] = ref
    try:
        return requests.get(u, timeout=20, allow_redirects=True, headers=h, params=params)
    except Exception as e:  # noqa: BLE001
        return e


def main():
    OUT.write_text("", encoding="utf-8")

    w("===== 宜宾 DoExcerpts/List =====")
    for u in ["http://12345.zwfwhfgjjfzj.yibin.gov.cn/DoExcerpts/List",
              "http://12345.zwfwhfgjjfzj.yibin.gov.cn/ResultQuery/QueryList"]:
        r = get(u, ref="http://12345.zwfwhfgjjfzj.yibin.gov.cn/WriteLetters/WriteLetter")
        if hasattr(r, "status_code"):
            w(f"  {u} -> {r.status_code} ct={r.headers.get('content-type','')[:40]} len={len(r.text)}")
            w("     " + re.sub(r"\s+", " ", r.text[:400]))

    w("\n===== 雅安 mail 列表结构 =====")
    r = get("https://www.yaan.gov.cn/mail/index.html")
    if hasattr(r, "status_code") and r.status_code == 200:
        t = r.text
        i = t.find("/leader/detail/")
        w("  item ctx: " + re.sub(r"\s+", " ", t[max(0, i - 500):i + 250]))
        w("  detail links: " + str(len(re.findall(r"/leader/detail/", t))))
        for m in re.finditer(r'href=["\']([^"\']*(?:page|index_\d|list)[^"\']*)["\']', t):
            w("     [pg] " + m.group(1)[:120])

    w("\n===== 雅安 leader/detail 详情结构 =====")
    r = get("https://www.yaan.gov.cn/leader/detail/b718c611df12b4fc8eb292a9ae13bd7a.html")
    if hasattr(r, "status_code") and r.status_code == 200:
        t = r.text
        for kw in ["来信", "回复", "答复", "内容"]:
            i = t.find(kw)
            if i > 0:
                w(f"  [{kw}] " + re.sub(r"\s+", " ", t[max(0, i - 120):i + 400]))
                break

    w("\n===== 乐山 wdzsk 问答库 =====")
    r = get("https://www.leshan.gov.cn/front/wdzsk/index")
    if hasattr(r, "status_code") and r.status_code == 200:
        t = r.text
        for m in re.finditer(r'["\'](/front/[A-Za-z0-9_/\-]+)["\']', t):
            w("     [ep] " + m.group(1))
        i = t.find("ajax")
        if i > 0:
            w("  ajax ctx: " + re.sub(r"\s+", " ", t[max(0, i - 200):i + 400]))


if __name__ == "__main__":
    main()
