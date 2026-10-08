"""山东地市 第四轮：淄博/济南 jact 真实接口 + 青岛 mailboxpage/qdgov-web。
用法：python recon/sd-city-probe4.py
输出：recon/sd-city-probe4.txt
"""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import UA  # noqa: E402

OUT = HERE / "sd-city-probe4.txt"


def grab(c, f, url, save=None, show_api=True):
    try:
        r = c.get(url, timeout=15)
        f.write(f"  GET {url} → {r.status_code} len={len(r.text)}\n")
        if save and r.status_code == 200:
            (HERE / save).write_text(r.text, encoding="utf-8")
        if show_api and r.status_code == 200:
            for pat in set(re.findall(
                    r'["\']([^"\']*(?:dataproxy|mailpub|\.do|\.ashx|api-gateway|jpaas|ajaxpro)[^"\']*)["\']',
                    r.text, re.I)):
                if len(pat) < 160:
                    f.write(f"     api: {pat}\n")
        return r
    except Exception as e:                                              # noqa: BLE001
        f.write(f"  GET {url} → {type(e).__name__}: {str(e)[:90]}\n")
        return None


def main() -> int:
    import httpx
    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      follow_redirects=True) as c:
        with OUT.open("w", encoding="utf-8") as f:
            # ---------- 淄博 ----------
            f.write("=" * 70 + "\n## 淄博 zibo\n")
            zb = "http://www.zibo.gov.cn"
            grab(c, f, zb + "/jact/front/mailpublist.do?sysid=1", "sd-city-zibo-list.html")
            time.sleep(1)
            grab(c, f, zb + "/jact/front/main.do?sysid=54", "sd-city-zibo-main54.html")
            time.sleep(1)
            # jact 前端 JS 里找接口
            for js in ["/jact_files/pagemodel/default-template/page.js"]:
                grab(c, f, zb + js, "sd-city-zibo-page.js", show_api=False)
                time.sleep(1)

            # ---------- 济南 ----------
            f.write("\n" + "=" * 70 + "\n## 济南 jinan\n")
            jb = "http://www.jinan.gov.cn"
            grab(c, f, jb + "/api-gateway/jpaas-jact-web-server/front/mail-pub-list.do"
                      "?platformIid=HTMi0SM6aXpdnEJDZH931&govOpen=1",
                 "sd-city-jinan-maillist2.html")
            time.sleep(1)
            grab(c, f, jb + "/jact_files/pagemodel/default-template/page.js",
                 "sd-city-jinan-page.js", show_api=False)
            time.sleep(1)
            grab(c, f, jb + "/jact_files/pagemodel/default-template/domain.js",
                 "sd-city-jinan-domain.js", show_api=False)

            # ---------- 青岛 ----------
            f.write("\n" + "=" * 70 + "\n## 青岛 qingdao\n")
            qb = "http://www.qingdao.gov.cn"
            grab(c, f, qb + "/mailboxpage-qd/city/NewGovMailTopList.html",
                 "sd-city-qingdao-toplist.html")
            time.sleep(1)
            grab(c, f, qb + "/qdgov-web/qdlist", "sd-city-qingdao-qdlist.txt")
    print("written", OUT)
    return 0


if __name__ == "__main__":
    main()
