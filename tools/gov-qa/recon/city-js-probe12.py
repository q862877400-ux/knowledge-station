"""stage12：无锡 resultAnswer 确认 + 苏州分页参数穷举（GET/POST form/json）。"""
from __future__ import annotations

import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
OUT = os.path.join(HERE, "city-js-probe12.txt")


def main() -> int:
    import httpx
    with httpx.Client(headers={"User-Agent": UA}, trust_env=False, timeout=25,
                      follow_redirects=True) as c, open(OUT, "w", encoding="utf-8") as f:
        def w(s=""):
            f.write(s + "\n")
            print(s[:320])

        w("## 无锡 resultAnswer")
        r = c.get("https://www.wuxi.gov.cn/mailbox/letter/search",
                  params={"page": 1, "size": 2},
                  headers={"Referer": "https://www.wuxi.gov.cn/hdjl/index.html"})
        for it in ((r.json().get("data") or {}).get("data") or [])[:2]:
            w("  title=" + str(it.get("title")))
            w("  content=" + str(it.get("content"))[:80])
            w("  resultAnswer(len=%d)=" % len(str(it.get("resultAnswer") or ""))
              + str(it.get("resultAnswer"))[:200])
            w("  doState=%s depName=%s beginTime=%s endTime=%s"
              % (it.get("doState"), it.get("depName"), it.get("beginTime"), it.get("endTime")))
        # 确认 size 是否生效
        for sz in [5, 20]:
            rr = c.get("https://www.wuxi.gov.cn/mailbox/letter/search",
                       params={"page": 1, "size": sz},
                       headers={"Referer": "https://www.wuxi.gov.cn/hdjl/index.html"})
            w(f"  size={sz} n={len(((rr.json().get('data') or {}).get('data')) or [])}")

        w("\n## 苏州 bmxxCommonlist 分页穷举")
        base = "https://www.suzhou.gov.cn/consultfront/common/bmxxCommonlist"
        ref = {"Referer": "https://www.suzhou.gov.cn/szsrmzf/hd_xjly/xjly.shtml"}
        def first(j):
            l = j.get("infolist") or []
            return l[0].get("consult_title") if l else None
        tests = [
            ("GET", {"pageNum": 2, "pageSize": 10}),
            ("GET", {"pageNum": 2, "pageSize": 10, "deptId": ""}),
            ("POSTform", {"pageNum": 2, "pageSize": 10}),
            ("POSTjson", {"pageNum": 2, "pageSize": 10}),
            ("POSTjson", {"page": 2, "size": 10}),
            ("POSTjson", {"pageNum": 2, "pageSize": 10, "deptId": "", "type": ""}),
            ("GET", {"curPage": 2, "pageSize": 10}),
            ("GET", {"pageNo": 2, "limit": 10}),
        ]
        for kind, params in tests:
            try:
                if kind == "GET":
                    r = c.get(base, params=params, headers=ref)
                elif kind == "POSTform":
                    r = c.post(base, data=params, headers=ref)
                else:
                    r = c.post(base, json=params, headers=ref)
                j = r.json()
                w(f"  {kind} {params} -> first={first(j)}")
            except Exception as e:                                          # noqa: BLE001
                w(f"  {kind} {params} ERR {str(e)[:60]}")
            time.sleep(0.4)

    print("written", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
