"""stage13：苏州 main.js 里 bmxxCommonlist 调用点 + 参数构造。"""
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


def main():
    OUT.write_text("", encoding="utf-8")
    c = requests.Session()
    c.headers.update({"User-Agent": "Mozilla/5.0"})
    jt = c.get("https://www.suzhou.gov.cn/szsrmzf/xhtml/hd/assets/main.js",
               timeout=30).text
    w(f"## main.js len={len(jt)}")
    # 找 bmxxCommonlist 所有出现及其上下文
    for m in re.finditer(r"bmxxCommonlist", jt):
        s = max(0, m.start() - 400)
        e = min(len(jt), m.end() + 400)
        w("----")
        w(jt[s:e])
    # 找包含 pageNum / pageSize / currentPage 的请求构造
    for kw in ("pageNum", "pageSize", "currentPage", "pageNo"):
        idxs = [m.start() for m in re.finditer(kw, jt)]
        w(f"\n## kw={kw} count={len(idxs)}")
        for i in idxs[:6]:
            w("  ..." + jt[max(0, i - 120):i + 120].replace("\n", " "))


if __name__ == "__main__":
    main()
