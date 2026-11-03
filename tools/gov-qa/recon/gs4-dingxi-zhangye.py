"""定西（jact, http）与张掖（IGI, http）实测。"""
from __future__ import annotations

import os
import re

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")


def dingxi(cli):
    host = "www.dingxi.gov.cn"
    for sysid in ("91", "3"):
        base = f"http://{host}"
        url = (f"{base}/jact/front/dataproxy_mailpublist.do"
               f"?startrecord=1&endrecord=19&perpage=19&groupSize=3")
        body = {"sysid": sysid, "datadetailid": "", "dicvalue": "", "mailnumber": "",
                "querycode": "", "groupid": "", "mailstate": "", "starttime": "",
                "endtime": "", "keyword": ""}
        r = cli.post(url, data=body, headers={
            "Referer": f"{base}/jact/front/mailpublist.do?sysid={sysid}",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded"})
        t = r.text or ""
        m = re.search(r"totalRecord\s*=\s*([0-9.]+)", t)
        print(f"\n### DINGXI sysid={sysid} HTTP {r.status_code} totalRecord={m.group(1) if m else '?'} len={len(t)}")
        print(t[:300].replace("\n", " "))


def zhangye(cli):
    base = "http://www.zhangye.gov.cn/IGI"
    for sid in ("9", "15", "19", "20", "23", "61", "67", "77"):
        url = (f"{base}/nbhd/openGovmsgbox.do?method=listGovmsgboxs"
               f"&siteId={sid}&order=1&appId=&pageIndex=1&pageSize=20")
        r = cli.get(url, headers={"Referer": "http://www.zhangye.gov.cn/hdjl/"})
        try:
            j = r.json()
            total = (j.get("datas") or {}).get("totalResults")
            n = len((j.get("datas") or {}).get("data") or [])
        except Exception:
            total, n = "?", 0
        print(f"DINGXI? no. ZHANGYE siteId={sid} HTTP {r.status_code} total={total} pageN={n}")


def main():
    with httpx.Client(timeout=40, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False) as cli:
        dingxi(cli)
        print()
        zhangye(cli)


if __name__ == "__main__":
    main()
