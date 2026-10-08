"""stage11：苏州 main.js 参数 + 无锡完整项 + 南京 SPA JS。"""
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
OUT = os.path.join(HERE, "city-js-probe11.txt")


def main() -> int:
    import httpx
    with httpx.Client(headers={"User-Agent": UA}, trust_env=False, timeout=25,
                      follow_redirects=True) as c, open(OUT, "w", encoding="utf-8") as f:
        def w(s=""):
            f.write(s + "\n")
            print(s[:300])

        # 苏州 main.js 里 bmxxCommonlist 的调用上下文
        w("## 苏州 main.js bmxxCommonlist 上下文")
        jt = c.get("https://www.suzhou.gov.cn/szsrmzf/xhtml/hd/assets/main.js").text
        for m in re.finditer(r"bmxxCommonlist", jt):
            i = m.start()
            w("  ..." + re.sub(r"\s+", " ", jt[i-260:i+260]))
            w("  ----")

        # 无锡 完整 item（含答复）
        w("\n## 无锡 item 完整（page=1）")
        r = c.get("https://www.wuxi.gov.cn/mailbox/letter/search",
                  params={"page": 1, "size": 3},
                  headers={"Referer": "https://www.wuxi.gov.cn/hdjl/index.html"})
        d = r.json().get("data") or {}
        w("  keys=" + str(list(d.keys())))
        it = (d.get("data") or [{}])[0]
        w("  item keys=" + str(list(it.keys())))
        w("  item=" + json.dumps(it, ensure_ascii=False)[:2000])

        # 南京 SPA 资源
        w("\n## 南京 szxx SPA 资源")
        h = c.get("https://szxx.nanjing.gov.cn:32767/zhengfuxinxiang/huifuxuandeng?orgid=320113&type=sszxx",
                  headers={"Referer": "https://www.nanjing.gov.cn/hdjl/"}).text
        w("  len=" + str(len(h)))
        for m in re.finditer(r'(src|href)=["\']([^"\']+)["\']', h, re.I):
            u = m.group(2)
            if any(k in u.lower() for k in (".js", "static", "assets")):
                w("  RES " + u[:120])

    print("written", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
