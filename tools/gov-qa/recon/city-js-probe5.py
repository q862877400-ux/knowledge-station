"""江苏剩余市接口实测（stage5）：苏州/无锡/连云港/南通/南京。

用法：python recon/city-js-probe5.py
输出：recon/city-js-probe5.txt
"""
from __future__ import annotations

import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
OUT = os.path.join(HERE, "city-js-probe5.txt")


def show(f, tag, r):
    ct = r.headers.get("content-type", "")
    body = (r.text or "")[:260].replace("\n", " ")
    f.write(f"  {tag} -> {r.status_code} [{ct[:30]}] {body}\n")
    print(f"  {tag} -> {r.status_code} {body[:120]}")


def main() -> int:
    import httpx
    with httpx.Client(headers={"User-Agent": UA}, trust_env=False, timeout=25,
                      follow_redirects=True) as c, open(OUT, "w", encoding="utf-8") as f:
        def w(s=""):
            f.write(s + "\n")

        # 苏州
        w("## 苏州 /consultfront")
        for p in ["/consultfront/common/gzjdCommonlist",
                  "/consultfront/common/bmxxCommonlist",
                  "/consultfront/common/getGzjdDeptlist",
                  "/consultfront/common/getBmxxDeptlist"]:
            u = "https://www.suzhou.gov.cn" + p
            ref = "https://www.suzhou.gov.cn/szsrmzf/hd_gzjd/gzjd.shtml"
            for method in ("get", "post"):
                try:
                    if method == "get":
                        r = c.get(u, headers={"Referer": ref})
                    else:
                        r = c.post(u, json={"pageNum": 1, "pageSize": 10},
                                   headers={"Referer": ref})
                    show(f, f"{p.split('/')[-1]} {method}", r)
                except Exception as e:                                      # noqa: BLE001
                    w(f"  {p} {method} ERR {type(e).__name__}: {str(e)[:70]}")
                time.sleep(0.8)

        # 无锡
        w("\n## 无锡 /mailbox")
        for p in ["/mailbox/letter/search", "/mailbox/type/list",
                  "/mailbox/department/list", "/mailbox/process/count"]:
            u = "https://www.wuxi.gov.cn" + p
            ref = "https://www.wuxi.gov.cn/hdjl/index.shtml"
            for method in ("get", "post"):
                try:
                    if method == "get":
                        r = c.get(u, params={"pageNum": 1, "pageSize": 10},
                                  headers={"Referer": ref})
                    else:
                        r = c.post(u, data={"pageNum": 1, "pageSize": 10},
                                   headers={"Referer": ref})
                    show(f, f"{p.split('/')[-1]} {method}", r)
                except Exception as e:                                      # noqa: BLE001
                    w(f"  {p} {method} ERR {type(e).__name__}: {str(e)[:70]}")
                time.sleep(0.8)

        # 连云港
        w("\n## 连云港 TrueCMS")
        u = ("http://www.lyg.gov.cn/TrueCMS/mailBoxLetterController/getLetterList.do"
             "?pageNum=1&numPerPage=4")
        try:
            r = c.get(u, headers={"Referer": "http://www.lyg.gov.cn/zglygzfmhwz/gzcy/gzcy.html"})
            show(f, "getLetterList", r)
        except Exception as e:                                              # noqa: BLE001
            w(f"  getLetterList ERR {type(e).__name__}: {str(e)[:70]}")

        # 南通 TrueCMS
        w("\n## 南通 TrueCMS")
        for u in ["https://www.nantong.gov.cn/truecms/letterController/xxList.do?numPerPage=10&pageNum=1",
                  "https://www.nantong.gov.cn/truecms/letterController/xxList.do?numPerPage=10&pageNum=1&type="]:
            try:
                r = c.get(u, headers={"Referer": "https://www.nantong.gov.cn/ntsrmzf/sgkxj/sgkxj.html"})
                show(f, u.split("?")[1][:40], r)
            except Exception as e:                                          # noqa: BLE001
                w(f"  ERR {type(e).__name__}: {str(e)[:70]}")
            time.sleep(0.8)

        # 南京
        w("\n## 南京 /hdjl + 外链信箱")
        for u in ["https://www.nanjing.gov.cn/hdjl/",
                  "https://szxx.nanjing.gov.cn:32767/zhengfuxinxiang/huifuxuandeng?orgid=320113&type=sszxx",
                  "https://szxx.nanjing.gov.cn:32767/zhengfuxinxiang?orgid=320113&type=sszxx"]:
            try:
                r = c.get(u, headers={"Referer": "https://www.nanjing.gov.cn/hdjl/"})
                show(f, u[:60], r)
            except Exception as e:                                          # noqa: BLE001
                w(f"  {u[:60]} ERR {type(e).__name__}: {str(e)[:70]}")
            time.sleep(0.8)

    print("written", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
