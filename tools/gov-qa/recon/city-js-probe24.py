"""stage24：南京 全 chunk 扫 API 路径（baseURL=/prod-api/）。"""
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
    h = c.get(BASE + "/zhengfuxinxiang/huifuxuandeng?orgid=320113&type=sszxx", timeout=30).text
    js = sorted(set(re.findall(r'(?:src|href)="([^"]+\.js)"', h)))
    pat = re.compile(r'["\'`](/?[a-zA-Z][a-zA-Z0-9_/\-]{3,80})["\'`]')
    kw = ("zfxx", "letter", "huifu", "xinxiang", "query", "list", "mail", "juzhang", "szxx")
    for j in js:
        ju = j if j.startswith("http") else BASE + (j if j.startswith("/") else "/" + j)
        try:
            t = c.get(ju, timeout=30).text
        except Exception as e:  # noqa: BLE001
            w(f"  {ju} ERR {type(e).__name__}")
            continue
        hits = set()
        for m in pat.finditer(t):
            s = m.group(1)
            low = s.lower()
            if any(k in low for k in kw) and not s.startswith("chunk") and "/static" not in s:
                hits.add(s)
        if hits:
            w(f"  [{ju.split('/')[-1]}] " + " | ".join(sorted(hits)[:25]))


if __name__ == "__main__":
    main()
