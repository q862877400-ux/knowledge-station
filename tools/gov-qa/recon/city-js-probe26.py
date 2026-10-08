"""stage26：南京 定位「回复选登」chunk + algk/listPage 字段。"""
import json
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
    c.headers.update({"User-Agent": "Mozilla/5.0",
                      "Referer": BASE + "/zhengfuxinxiang/huifuxuandeng?orgid=320113&type=sszxx"})
    h = c.get(BASE + "/zhengfuxinxiang/huifuxuandeng?orgid=320113&type=sszxx", timeout=30).text
    js = sorted(set(re.findall(r'(?:src|href)="([^"]+\.js)"', h)))

    w("## 含「回复选登」的 chunk")
    for j in js:
        ju = j if j.startswith("http") else BASE + (j if j.startswith("/") else "/" + j)
        try:
            t = c.get(ju, timeout=30).text
        except Exception:  # noqa: BLE001
            continue
        if "回复选登" in t or "huifuxuandeng" in t.lower():
            w(f"  {ju.split('/')[-1]} len={len(t)}")
            for m in re.finditer(r'["\'`](/?[a-zA-Z][a-zA-Z0-9_/\-]{3,80})["\'`]', t):
                s = m.group(1)
                if any(k in s.lower() for k in ("wsxf", "zfxx", "letter", "huifu", "algk", "list")):
                    w("     " + s)

    w("\n## algk/listPage 字段")
    rr = c.get(BASE + "/prod-api/wsxf/algk/listPage",
               params={"orgid": 320113, "type": "sszxx", "pageNum": 1, "pageSize": 3}, timeout=25)
    d = rr.json()
    w("  top=" + str({k: (type(v).__name__ if not isinstance(v, (str, int)) else v) for k, v in d.items()}))
    rows = d.get("rows") or []
    if rows:
        w("  row keys=" + str(list(rows[0].keys())))
        w("  row0=" + json.dumps(rows[0], ensure_ascii=False)[:900])


if __name__ == "__main__":
    main()
