"""浙江「民呼我为统一平台」地市码探测：验证 code=33xx00 是否返回该市来件。

背景：省平台 zj-mhww 用 code=330000 取全省（totalItem=49218）。
若地市码 330100..331100 各返回该市数据 ⇒ **一个平台覆盖 11 个地级市**。
输出：recon/city-js-zj-zjmhww-probe.txt
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")

BASE = "https://zxts.zjzwfw.gov.cn"
LIST_URL = BASE + "/zlh/zsapi/xfpt/OTMelbwjyz/OTMjkerj"
DETAIL_URL = BASE + "/zlh/zsapi/xfpt/OTMelbwjyz/OTMrwgaxid"
HEADERS = {
    "Content-Type": "application/json;charset=UTF-8",
    "Referer": BASE + "/zwmhww/",
    "Origin": BASE,
}
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")

# 浙江 11 个地级市行政区划码
CITIES = [
    ("杭州", "330100"), ("宁波", "330200"), ("温州", "330300"), ("嘉兴", "330400"),
    ("湖州", "330500"), ("绍兴", "330600"), ("金华", "330700"), ("衢州", "330800"),
    ("舟山", "330900"), ("台州", "331000"), ("丽水", "331100"),
]
OUT = HERE / "city-js-zj-zjmhww-probe.txt"


def main() -> int:
    import httpx
    with httpx.Client(headers={"User-Agent": UA}, trust_env=False, timeout=25,
                      follow_redirects=True) as c, OUT.open("w", encoding="utf-8") as f:
        def w(s: str) -> None:
            f.write(s + "\n")
            print(s)

        w("浙江民呼我为统一平台 · 地市码探测（2026-10-09）")
        w(f"LIST {LIST_URL}")
        for name, code in CITIES:
            try:
                r = c.post(LIST_URL, json={"code": code, "bt": "", "bldw": "",
                                           "pageNum": 1, "pageSize": 3},
                           headers=HEADERS)
                j = r.json()
                data = (j or {}).get("data") or {}
                total = data.get("totalItem")
                rows = data.get("list") or []
                first = rows[0].get("storeid") if rows else None
                w(f"  {name} code={code} → HTTP {r.status_code} totalItem={total} "
                  f"本页={len(rows)} 首条storeid={first}")
                # 取首条明细验证答复
                if first:
                    time.sleep(1.5)
                    dr = c.get(DETAIL_URL, params={"storeId": first}, headers=HEADERS)
                    dd = (dr.json() or {}).get("data") or {}
                    dfyj = str(dd.get("dfyj") or "")
                    bt = str(dd.get("bt") or "")
                    w(f"      明细 {first} → HTTP {dr.status_code} 标题前40={bt[:40]!r} "
                      f"答复长度={len(dfyj)} 答复前60={dfyj[:60]!r}")
            except Exception as e:                                          # noqa: BLE001
                w(f"  {name} code={code} → {type(e).__name__}: {str(e)[:100]}")
            time.sleep(1.5)
    print("written", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
