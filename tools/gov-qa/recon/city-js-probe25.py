"""stage25：南京 /prod-api/wsxf/* 接口实测（回复选登候选）。"""
import json
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
    paths = ["/prod-api/wsxf/xfj/listPage", "/prod-api/wsxf/algk/listPage",
             "/prod-api/wsxf/ly/list", "/prod-api/wsxf/xfj/listZxqs",
             "/prod-api/wsxf/xfj/wsfhList", "/prod-api/wsxf/jdalnw/list",
             "/prod-api/wsxf/xfj/getListBySjhXm"]
    for p in paths:
        for params in ({"orgid": 320113, "type": "sszxx", "pageNum": 1, "pageSize": 5},
                       {"orgid": "320113", "type": "sszxx", "pageNum": 1, "pageSize": 5,
                        "curPage": 1}):
            try:
                rr = c.get(BASE + p, params=params, timeout=25)
                ct = rr.headers.get("content-type", "")
                head = rr.text[:150].replace("\n", " ")
                w(f"  GET {p} {list(params)} -> {rr.status_code} ct={ct} len={len(rr.text)} {head!r}")
                if "json" in ct and rr.status_code == 200:
                    try:
                        d = rr.json()
                        w("     keys=" + str(list(d.keys())[:15]) if isinstance(d, dict) else f"     type={type(d).__name__}")
                    except Exception:  # noqa: BLE001
                        pass
                # POST 也试
                rr2 = c.post(BASE + p, json=params, timeout=25)
                w(f"  POST {p} -> {rr2.status_code} ct={rr2.headers.get('content-type','')} len={len(rr2.text)} {rr2.text[:120]!r}")
            except Exception as e:  # noqa: BLE001
                w(f"  {p} -> {type(e).__name__} {str(e)[:60]}")


if __name__ == "__main__":
    main()
