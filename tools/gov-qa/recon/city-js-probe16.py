"""stage16：苏州 getBmxxDetail 明细端点参数 + 内容（补全问题正文）。"""
import json
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
    c.headers.update({"User-Agent": "Mozilla/5.0",
                      "Referer": "https://www.suzhou.gov.cn/szsrmzf/xhtml/hd/"})
    # main.js 里 getBmxxDetail 的调用上下文
    jt = c.get("https://www.suzhou.gov.cn/szsrmzf/xhtml/hd/assets/main.js",
               timeout=30).text
    for m in re.finditer(r"getBmxxDetail|TB\b", jt):
        s = max(0, m.start() - 160)
        w("CTX ..." + jt[s:m.end() + 160].replace("\n", " "))
    # 取一条 gid
    r = c.get("https://www.suzhou.gov.cn/consultfront/common/bmxxCommonlist",
              params={"currpage": 1, "check": "do", "pagesize": 5,
                      "deptcode": "", "keywords": ""}, timeout=30)
    it = r.json()["infolist"][0]
    gid = it["gid"]
    w(f"\n## gid={gid}")
    base = "https://www.suzhou.gov.cn/consultfront/common/getBmxxDetail"
    for params in ({"gid": gid}, {"id": gid}, {"GID": gid}, {"gid": gid, "check": "do"}):
        try:
            rr = c.get(base, params=params, timeout=30)
            w(f"GET {params} -> {rr.status_code} {rr.text[:300]}")
        except Exception as e:  # noqa: BLE001
            w(f"GET {params} -> {type(e).__name__} {e}")
    for params in ({"gid": gid},):
        try:
            rr = c.post(base, data=params, timeout=30)
            w(f"POST {params} -> {rr.status_code} {rr.text[:300]}")
        except Exception as e:  # noqa: BLE001
            w(f"POST {params} -> {type(e).__name__} {e}")


if __name__ == "__main__":
    main()
