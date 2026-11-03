"""甘肃 4 源实测探针（worker-gansu）。只做只读探测，不改任何东西。"""
from __future__ import annotations

import json
import os
import sys

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")


def show(tag, r, n=400):
    body = r.text or ""
    print(f"\n### {tag} -> HTTP {r.status_code} len={len(body)}")
    print(body[:n].replace("\n", " "))


def probe_baiyin(cli):
    base = "https://www.baiyin.gov.cn/api-gateway/jpaas-jact-web-server/front"
    hdr = {"Referer": "https://www.baiyin.gov.cn/"}
    # 变体 A：报告里的 page/limit
    a = f"{base}/find-mail-pub-list?platformIid=dc0a47c54dce496a9cc6321fac5a973a&page=1&limit=10"
    show("BAIYIN A page/limit", cli.get(a, headers=hdr))
    # 变体 B：layui pageNum/pageSize
    b = f"{base}/find-mail-pub-list?platformIid=dc0a47c54dce496a9cc6321fac5a973a&pageNum=1&pageSize=10"
    show("BAIYIN B pageNum/pageSize", cli.get(b, headers=hdr))
    # 变体 C：platformUid + orderType
    c = (f"{base}/find-mail-pub-list?platformUid=dc0a47c54dce496a9cc6321fac5a973a"
         f"&pageNum=1&pageSize=10&orderType=2")
    show("BAIYIN C platformUid/orderType", cli.get(c, headers=hdr))


def probe_longnan(cli):
    hdr = {"Referer": "https://www.longnan.gov.cn/zmhd/szxx/index.html"}
    idx = cli.get("https://www.longnan.gov.cn/zmhd/szxx/index.html", headers=hdr)
    print(f"\n### LONGNAN index -> HTTP {idx.status_code} cookies={dict(cli.cookies)}")
    url = ("https://www.longnan.gov.cn/site/label/8888?labelName=messageBoardPageList"
           "&pageIndex=1&pageSize=14&siteId=4448177&columnId=4450039&action=singleList&isJson=true")
    r = cli.get(url, headers=hdr)
    show("LONGNAN list", r, 1200)


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    with httpx.Client(timeout=40, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False) as cli:
        if which in ("all", "baiyin"):
            probe_baiyin(cli)
        if which in ("all", "longnan"):
            probe_longnan(cli)


if __name__ == "__main__":
    main()
