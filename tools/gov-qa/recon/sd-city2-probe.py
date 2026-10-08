"""山东地市 6–16 第二轮：jact 族实测 + 烟台 jpaas-jact + 其余市互动页深挖。
用法：python recon/sd-city2-probe.py
输出：recon/sd-city2-probe.txt
"""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import UA  # noqa: E402

OUT = HERE / "sd-city2-probe.txt"
FINGER = ("openGovmsgbox", "listGovmsgboxs", "/IGI/", "jact", "mailpub", "ajaxlist",
          "dataproxy", "channelid", "was5", "api-gateway", "e/search", "content.html")

# jact 族（sysid）
JACT = [
    ("济宁", "jining", "http://www.jining.gov.cn", "1"),
    ("威海", "weihai", "http://www.weihai.gov.cn", "61"),
    ("日照", "rizhao", "http://www.rizhao.gov.cn", "383"),
    ("滨州", "binzhou", "http://www.binzhou.gov.cn", "1206"),
]
# 待深挖市（互动页候选）
DIG = [
    ("潍坊", "weifang", ["http://www.weifang.gov.cn/xxgk/hdlist/",
                         "http://www.weifang.gov.cn/xxgk/xhdjl/"]),
    ("泰安", "taian", ["https://12345.taian.cn/website_web/",
                       "http://www.taian.gov.cn/"]),
    ("临沂", "linyi", ["http://www.linyi.gov.cn/hd/szxx-list.jsp?urltype=tree.TreeTempUrl&wbtreeid=1086",
                       "http://www.linyi.gov.cn/hd/hygq.htm"]),
    ("德州", "dezhou", ["http://www.dezhou.gov.cn/n1480/index.html",
                        "http://www.dezhou.gov.cn/n1480/n59452804/index.html"]),
    ("聊城", "liaocheng", ["http://www.liaocheng.gov.cn/channel_t_156_11559/",
                           "http://www.liaocheng.gov.cn/channel_t_156_11571/?page=1"]),
    ("菏泽", "heze", ["http://www.heze.gov.cn/zmhd/",
                      "http://www.heze.gov.cn/zmhd/szxx/"]),
]


def jact_total(c, base, sysid, method):
    url = f"{base}/jact/front/dataproxy_mailpublist.do?startrecord=1&endrecord=19&perpage=19&groupSize=3"
    params = {"sysid": str(sysid), "datadetailid": "", "dicvalue": "", "mailnumber": "",
              "querycode": "", "groupid": "", "mailstate": "", "starttime": "",
              "endtime": "", "keyword": "", "orderfield": "1"}
    ref = f"{base}/jact/front/mailpublist.do?sysid={sysid}"
    try:
        if method == "GET":
            r = c.get(f"{url}&{urlencode(params)}", headers={"Referer": ref})
        else:
            r = c.post(url, data=params, headers={"Referer": ref,
                       "X-Requested-With": "XMLHttpRequest"})
        m = re.search(r"totalRecord\s*=\s*([0-9.]+)", r.text or "")
        tid = re.search(r"transactId=(\d+)", r.text or "")
        return f"{r.status_code} total={m.group(1) if m else '?'} tid={tid.group(1) if tid else '-'}"
    except Exception as e:                                              # noqa: BLE001
        return f"{type(e).__name__}: {str(e)[:60]}"


def main() -> int:
    import httpx
    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      follow_redirects=True, timeout=15) as c:
        with OUT.open("w", encoding="utf-8") as f:
            # ---------- jact 族 ----------
            for city, abbr, base, sysid in JACT:
                f.write(f"\n## {city} {abbr} jact sysid={sysid} {base}\n")
                for method in ("POST", "GET"):
                    f.write(f"   {method}: {jact_total(c, base, sysid, method)}\n")
                    time.sleep(1)

            # ---------- 烟台 jpaas-jact ----------
            f.write("\n## 烟台 yantai jpaas-jact\n")
            yb = "http://www.yantai.gov.cn"
            ybase = yb + "/api-gateway/jpaas-jact-web-server/front"
            for pid, label in [("TBCxiImkDT42EEoX3QnkW", "网上民声"),
                               ("YgMOPJeFKdxv803E2TKqr", "市长信箱")]:
                u = f"{ybase}/find-mail-pub-list?pageNum=1&pageSize=5&platformUid={pid}&govOpen=1"
                try:
                    r = c.get(u, headers={"Referer": yb + "/col/col11783/index.html"})
                    body = r.text or ""
                    cnt = "?"
                    try:
                        cnt = r.json().get("count")
                    except Exception:                                       # noqa: BLE001
                        pass
                    f.write(f"   {label} platformUid={pid} → {r.status_code} count={cnt} "
                            f"len={len(body)}\n")
                    if r.status_code == 200 and 'iid' in body:
                        f.write(f"      sample={body[:180]}\n")
                except Exception as e:                                      # noqa: BLE001
                    f.write(f"   {label} → {type(e).__name__}: {str(e)[:60]}\n")
                time.sleep(1)

            # ---------- 其余市深挖 ----------
            for city, abbr, urls in DIG:
                f.write(f"\n## {city} {abbr}\n")
                for u in urls:
                    try:
                        r = c.get(u)
                        t = r.text or ""
                        f.write(f"   GET {u} → {r.status_code} ({len(t)})\n")
                        if r.status_code == 200:
                            (HERE / f"sd-city2-{abbr}-hd.html").write_text(t, encoding="utf-8")
                            f.write(f"      finger: {[k for k in FINGER if k in t]}\n")
                            for pat in set(re.findall(
                                    r'["\']([^"\']*(?:dataproxy|mailpub|ajaxlist|\.ashx|/api/|channelid|content\.html|list)[^"\']*)["\']',
                                    t, re.I))[:12]:
                                if len(pat) < 130:
                                    f.write(f"      cand: {pat}\n")
                    except Exception as e:                                      # noqa: BLE001
                        f.write(f"   GET {u} → {type(e).__name__}: {str(e)[:60]}\n")
                    time.sleep(1)
    print("written", OUT)
    return 0


if __name__ == "__main__":
    main()
