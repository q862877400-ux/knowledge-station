"""stage23：南京 app.js 里回复选登组件的 API 路径。"""
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
    t = c.get(BASE + "/static/js/app.0e399158.js", timeout=30).text
    w(f"## app.js len={len(t)}")
    # 所有 url:"..." / path 字符串
    urls = sorted(set(re.findall(r'["\'`]([a-zA-Z][a-zA-Z0-9_/\-]{2,60})["\'`]', t)))
    cand = [u for u in urls if any(k in u.lower() for k in
            ("letter", "huifu", "zfxx", "xinxiang", "mail", "list", "query", "search", "page"))]
    w("## 候选路径:")
    for u in cand:
        w("   " + u)
    # 定位 huifuxuandeng 组件上下文
    for m in re.finditer(r"[Hh]uifuxuandeng", t):
        s = max(0, m.start() - 600)
        w("--CTX-- " + t[s:m.end() + 600].replace("\n", " ")[:1300])


if __name__ == "__main__":
    main()
