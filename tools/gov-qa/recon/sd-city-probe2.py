"""山东地市 第二轮：jact 端点实测 + 青岛/淄博/枣庄互动页抓取。
用法：python recon/sd-city-probe2.py
输出：recon/sd-city-probe2.txt
"""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import UA  # noqa: E402

OUT = HERE / "sd-city-probe2.txt"
FINGER = ("openGovmsgbox", "listGovmsgboxs", "/IGI/", "jact", "mailpub", "ajaxlist",
          "dataproxy", "was5", "channelid", "e/search", "api-gateway")


def get(c, f, url, **kw):
    try:
        r = c.get(url, timeout=15, **kw)
        f.write(f"  GET {url} → {r.status_code} ({len(r.text)} bytes)\n")
        return r
    except Exception as e:                                              # noqa: BLE001
        f.write(f"  GET {url} → {type(e).__name__}: {str(e)[:90]}\n")
        return None


def post(c, f, url, data, ref):
    try:
        r = c.post(url, data=data, headers={"Referer": ref,
                   "X-Requested-With": "XMLHttpRequest"}, timeout=15)
        f.write(f"  POST {url} → {r.status_code} ({len(r.text)} bytes) body[:120]={r.text[:120]!r}\n")
        return r
    except Exception as e:                                              # noqa: BLE001
        f.write(f"  POST {url} → {type(e).__name__}: {str(e)[:90]}\n")
        return None


def main() -> int:
    import httpx
    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      follow_redirects=True) as c:
        with OUT.open("w", encoding="utf-8") as f:
            # ---------- 东营：经典 jact ----------
            f.write("=" * 70 + "\n## 东营 dongying (jact sysid=129)\n")
            base = "http://www.dongying.gov.cn"
            get(c, f, base + "/jact/front/main.do?sysid=129")
            time.sleep(1)
            get(c, f, base + "/jact/front/mailpublist.do?sysid=129")
            time.sleep(1)
            r = post(c, f, base + "/jact/front/dataproxy_mailpublist.do"
                     "?startrecord=1&endrecord=19&perpage=19&groupSize=3",
                     {"sysid": "129", "datadetailid": "", "dicvalue": "", "mailnumber": "",
                      "querycode": "", "groupid": "", "mailstate": "", "starttime": "",
                      "endtime": "", "keyword": ""},
                     base + "/jact/front/mailpublist.do?sysid=129")
            if r is not None and r.status_code == 200:
                m = re.search(r"totalRecord\s*=\s*([0-9.]+)", r.text)
                f.write(f"     totalRecord={m.group(1) if m else '?'}\n")

            # ---------- 济南：api-gateway jact ----------
            f.write("\n" + "=" * 70 + "\n## 济南 jinan (jact api-gateway)\n")
            jb = "http://www.jinan.gov.cn"
            ju = (jb + "/api-gateway/jpaas-jact-web-server/front/mail-pub-list.do"
                  "?platformIid=HTMi0SM6aXpdnEJDZH931&govOpen=1&submitTargetIds="
                  "0114,0171,0115,0116,0117,0118,0119,0120,0121,0123,0124,0126,0127,"
                  "0128,0130,0132,0134,0135,0140,0141,0144,0146,0148,0151,0156,0133,"
                  "0159,0160,0163,0161,0137,0166,0138,0149,0513,2203,2414,2422,0515,"
                  "2479,2583,0145,622fntKBvD,sk7AtT5lCN,0147,1BF7PVWSQb,0152,0324,1921")
            r = get(c, f, ju)
            if r is not None and r.status_code == 200:
                f.write(f"     body[:300]={r.text[:300]!r}\n")
                for k in FINGER:
                    if k in r.text:
                        f.write(f"     finger-hit: {k}\n")
            time.sleep(1)
            # 试经典 jact 路径是否也在 jinan
            get(c, f, jb + "/jact/front/main.do")
            time.sleep(1)
            # 市长信箱页
            get(c, f, jb + "/col/col156/yhdlts/index.html")

            # ---------- 青岛 / 淄博 / 枣庄：抓互动页找指纹 ----------
            for city, abbr, urls in [
                ("青岛", "qingdao", ["http://www.qingdao.gov.cn/zmhd/",
                                     "http://www.qingdao.gov.cn/zmhd/index.html"]),
                ("淄博", "zibo", ["http://www.zibo.gov.cn/col/col6/index.html",
                                  "https://www.zibo.gov.cn/col/col1464/index.html"]),
                ("枣庄", "zaozhuang", ["http://www.zaozhuang.gov.cn/zmhd/",
                                       "http://www.zaozhuang.gov.cn/zmhd/index.html"]),
            ]:
                f.write("\n" + "=" * 70 + f"\n## {city} {abbr}\n")
                for u in urls:
                    r = get(c, f, u)
                    if r is not None and r.status_code == 200:
                        (HERE / f"sd-city-{abbr}-hd.html").write_text(r.text, encoding="utf-8")
                        hits = [k for k in FINGER if k in r.text]
                        f.write(f"     finger-hits: {hits}\n")
                        # 抠链接
                        seen = set()
                        for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                                             r.text, re.I | re.S):
                            href = urljoin(u, m.group(1))
                            txt = re.sub(r"<[^>]+>", "", m.group(2)).strip()[:30]
                            if href in seen:
                                continue
                            seen.add(href)
                            if any(k in txt + href for k in
                                   ("12345", "信箱", "留言", "咨询", "互动", "jact",
                                    "mailpub", "zmhd", "col")):
                                f.write(f"       [{txt}] {href}\n")
                    time.sleep(1)
    print("written", OUT)
    return 0


if __name__ == "__main__":
    main()
