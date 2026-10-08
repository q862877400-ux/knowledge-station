"""stage22：南京 SPA 回复选登接口定位（grep 全部 chunk）。"""
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
OUT = Path(__file__).with_suffix(".txt")
BASE = "https://szxx.nanjing.gov.cn:32767"


def w(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    with OUT.open("a", encoding="utf-8") as f:
        f.write(s + "\n")


def main():
    OUT.write_text("", encoding="utf-8")
    c = requests.Session()
    c.headers.update({"User-Agent": "Mozilla/5.0"})
    u = BASE + "/zhengfuxinxiang/huifuxuandeng?orgid=320113&type=sszxx"
    h = c.get(u, timeout=30).text
    js = sorted(set(re.findall(r'(?:src|href)="([^"]+\.js)"', h)))
    w(f"## chunks={len(js)}")
    pats = re.compile(r'["\'`](/?[a-zA-Z][a-zA-Z0-9_/\-]*(?:letter|Letter|huifu|Huifu|xinxiang|Xinxiang|mailbox|Mailbox|zfxx|api|Api|list|List)[a-zA-Z0-9_/\-]*)["\'`]')
    for j in js:
        ju = j if j.startswith("http") else BASE + (j if j.startswith("/") else "/" + j)
        try:
            t = c.get(ju, timeout=30).text
        except Exception as e:  # noqa: BLE001
            w(f"  {ju} ERR {type(e).__name__}")
            continue
        hits = set()
        for m in pats.finditer(t):
            s = m.group(1)
            if any(k in s for k in ("letter", "Letter", "huifu", "Huifu", "mailbox", "Mailbox", "zfxx")):
                hits.add(s)
        if hits:
            w(f"  [{ju.split('/')[-1]}] " + " | ".join(sorted(hits)[:20]))
        # axios baseURL
        for m in re.finditer(r'baseURL\s*[:=]\s*["\'`]([^"\'`]+)', t):
            w(f"     baseURL {ju.split('/')[-1]} -> {m.group(1)}")
    # 直接试常见前缀
    w("\n## 试常见 API 前缀")
    for p in ("/zfxx/letterList", "/api/letter/list", "/zfxx/api/letterList",
              "/zhengfuxinxiang/letterList", "/api/zfxx/letterList"):
        try:
            rr = c.get(BASE + p, params={"orgid": 320113, "type": "sszxx", "pageNum": 1},
                       timeout=20)
            ct = rr.headers.get("content-type", "")
            w(f"  {p} -> {rr.status_code} ct={ct} len={len(rr.text)} {rr.text[:80]!r}")
        except Exception as e:  # noqa: BLE001
            w(f"  {p} -> {type(e).__name__}")


if __name__ == "__main__":
    main()
