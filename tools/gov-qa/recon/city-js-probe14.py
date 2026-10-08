"""stage14：定位苏州 bmxxCommonlist 调用点（RB 常量使用处）+ totalcount。"""
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
    for kw in ("totalcount", "totalCount", "getBmxxDeptlist", "BmxxDeptlist"):
        idxs = [m.start() for m in re.finditer(kw, jt)]
        w(f"## kw={kw} count={len(idxs)}")
        for i in idxs[:4]:
            w("  ..." + jt[max(0, i - 250):i + 250].replace("\n", " "))
        w("")
    # RB 使用处（排除定义处 "RB=\"/consultfront"）
    idxs = [m.start() for m in re.finditer(r"RB", jt)]
    w(f"## 'RB' 出现 {len(idxs)} 次")
    cnt = 0
    for i in idxs:
        ctx = jt[max(0, i - 200):i + 200].replace("\n", " ")
        if "consultfront" in ctx or "url:" in ctx or "params" in ctx or "data:" in ctx:
            w("  ..." + ctx)
            cnt += 1
            if cnt > 12:
                break


if __name__ == "__main__":
    main()
