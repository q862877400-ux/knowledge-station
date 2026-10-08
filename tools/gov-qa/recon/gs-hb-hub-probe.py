"""GS/HB 站点侦察：探测门户/子域/中间件指纹的可达性（GS 与 HB）。

用法：python recon/gs-hb-hub-probe.py
纪律：请求间隔 >=1.5s；不写 adapters/、data/、*.md。
"""
from __future__ import annotations

import os
import re
import time

import httpx

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")

CANDIDATES = [
    # 甘肃
    "http://www.gansu.gov.cn/",
    "http://zwfw.gansu.gov.cn/",
    "http://www.gsxfj.gov.cn/",
    "http://www.gsxfj.gov.cn:8088/wsxf-online/",
    "http://www.gsei.com.cn/",
    "http://rst.gansu.gov.cn/",
    # 甘肃 IGI / TRS / jact 指纹
    "http://www.gansu.gov.cn/IGI/nbhd/openGovmsgbox.do?method=listGovmsgboxs&siteId=&appId=",
    "http://www.gansu.gov.cn/was5/web/search?channelid=1",
    "http://www.gansu.gov.cn/jact/front/mailpubdetail.do",
    # 湖北
    "http://www.hubei.gov.cn/",
    "http://zwfw.hubei.gov.cn/",
    "http://www.hubei.gov.cn/IGI/nbhd/openGovmsgbox.do?method=listGovmsgboxs&siteId=&appId=",
    "http://www.hubei.gov.cn/was5/web/search?channelid=1",
    # 湖北 12345 / 信访 / 子域
    "http://wsxf.hubei.gov.cn/",
    "http://www.hubei.gov.cn/hdjl/",
    "http://www.hubei.gov.cn/zmhd/",
    "http://www.hubei.gov.cn/hd/",
    "http://zwfw.hubei.gov.cn/hdjl/",
    "http://hbj.hubei.gov.cn/",
    "http://rst.hubei.gov.cn/",
    "http://nyt.hubei.gov.cn/",
    "http://wjw.hubei.gov.cn/",
    "http://zjt.hubei.gov.cn/",
]


def main() -> None:
    out = []
    for u in CANDIDATES:
        try:
            r = httpx.get(u, headers={"User-Agent": UA}, timeout=15,
                          follow_redirects=True, trust_env=False, verify=False)
            title = ""
            m = re.search(r"<title>(.*?)</title>", r.text, re.S | re.I)
            if m:
                title = m.group(1).strip()[:40]
            line = (f"{u} -> {r.status_code} {len(r.content)}B "
                    f"final={str(r.url)[:70]} title={title!r}")
        except Exception as e:                                                   # noqa: BLE001
            line = f"{u} -> ERR {type(e).__name__} {str(e)[:70]}"
        print(line, flush=True)
        out.append(line)
        time.sleep(1.5)
    with open("recon/gs-hb-hub-probe.txt", "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
