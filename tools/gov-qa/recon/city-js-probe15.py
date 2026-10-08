"""stage15：苏州 bmxxCommonlist 正确分页参数 currpage/pagesize 验证。"""
import json
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
    base = "https://www.suzhou.gov.cn/consultfront/common/bmxxCommonlist"
    for method in ("GET", "POST"):
        for params in (
            {"currpage": 1, "check": "do", "pagesize": 10, "deptcode": "", "keywords": ""},
            {"currpage": 2, "check": "do", "pagesize": 10, "deptcode": "", "keywords": ""},
            {"currpage": 3, "check": "do", "pagesize": 10, "deptcode": "", "keywords": ""},
            {"currpage": 2, "check": "do", "pagesize": 20, "deptcode": "", "keywords": ""},
        ):
            try:
                if method == "GET":
                    r = c.get(base, params=params, timeout=30)
                else:
                    r = c.post(base, data=params, timeout=30)
                d = r.json()
                info = d.get("infolist") or []
                first = info[0].get("consult_title") if info else None
                w(f"{method} {params} -> status={r.status_code} totalcount={d.get('totalcount')} "
                  f"n={len(info)} first={first}")
            except Exception as e:  # noqa: BLE001
                w(f"{method} {params} -> {type(e).__name__} {e}")
    # 展示一条完整 item
    r = c.get(base, params={"currpage": 1, "check": "do", "pagesize": 10,
                            "deptcode": "", "keywords": ""}, timeout=30)
    d = r.json()
    if d.get("infolist"):
        w("\n## item keys=" + str(list(d["infolist"][0].keys())))
        w("## item=" + json.dumps(d["infolist"][0], ensure_ascii=False)[:800])
    w("\n## top keys=" + str(list(d.keys())))


if __name__ == "__main__":
    main()
