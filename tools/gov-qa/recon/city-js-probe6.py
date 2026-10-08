"""苏州/无锡/连云港 明细与结构实测（stage6）。"""
from __future__ import annotations

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
OUT = os.path.join(HERE, "city-js-probe6.txt")


def main() -> int:
    import httpx
    with httpx.Client(headers={"User-Agent": UA}, trust_env=False, timeout=25,
                      follow_redirects=True) as c, open(OUT, "w", encoding="utf-8") as f:
        def w(s=""):
            f.write(s + "\n")
            print(s[:200])

        # 苏州 bmxxCommonlist
        w("## 苏州 bmxxCommonlist")
        r = c.get("https://www.suzhou.gov.cn/consultfront/common/bmxxCommonlist",
                  params={"pageNum": 1, "pageSize": 3},
                  headers={"Referer": "https://www.suzhou.gov.cn/szsrmzf/hd_xjly/xjly.shtml"})
        j = r.json()
        w("keys=" + str(list(j.keys())))
        lst = j.get("infolist") or []
        if lst:
            w("item keys=" + str(list(lst[0].keys())))
            w(json.dumps(lst[0], ensure_ascii=False)[:900])
        gid = lst[0].get("gid") if lst else None
        # 试明细候选
        for p in [f"/consultfront/common/bmxxCommonDetail?gid={gid}",
                  f"/consultfront/consult/bmxxDetail?gid={gid}",
                  f"/consultfront/common/getBmxxDetail?gid={gid}",
                  f"/consultfront/common/bmxxCommomDetail?gid={gid}"]:
            try:
                rr = c.get("https://www.suzhou.gov.cn" + p,
                           headers={"Referer": "https://www.suzhou.gov.cn/szsrmzf/hd_xjly/xjly.shtml"})
                w(f"  DET {p.split('/')[-1]} -> {rr.status_code} {rr.text[:150]}")
            except Exception as e:                                          # noqa: BLE001
                w(f"  DET {p} ERR {str(e)[:60]}")
            time.sleep(0.6)

        # 无锡 letter/search
        w("\n## 无锡 letter/search")
        r = c.get("https://www.wuxi.gov.cn/mailbox/letter/search",
                  params={"pageNum": 1, "pageSize": 3},
                  headers={"Referer": "https://www.wuxi.gov.cn/hdjl/index.shtml"})
        j = r.json()
        d = j.get("data") or {}
        w("data keys=" + str(list(d.keys())))
        lst = d.get("data") or []
        if lst:
            w("item keys=" + str(list(lst[0].keys())))
            w(json.dumps(lst[0], ensure_ascii=False)[:900])
        # 试明细
        lid = (lst[0].get("id") or lst[0].get("letterId") or lst[0].get("code")) if lst else None
        w(f"letter id={lid}")
        for p in ["/mailbox/letter/detail", "/mailbox/letter/getLetterDetail",
                  "/mailbox/letter/info", "/mailbox/letter/searchDetail"]:
            try:
                rr = c.get("https://www.wuxi.gov.cn" + p,
                           params={"id": lid, "code": lid},
                           headers={"Referer": "https://www.wuxi.gov.cn/hdjl/index.shtml"})
                w(f"  DET {p.split('/')[-1]} -> {rr.status_code} {rr.text[:150]}")
            except Exception as e:                                          # noqa: BLE001
                w(f"  DET {p} ERR {str(e)[:60]}")
            time.sleep(0.6)

        # 连云港 getLetterList
        w("\n## 连云港 getLetterList")
        r = c.get("http://www.lyg.gov.cn/TrueCMS/mailBoxLetterController/getLetterList.do",
                  params={"pageNum": 1, "numPerPage": 3},
                  headers={"Referer": "http://www.lyg.gov.cn/zglygzfmhwz/gzcy/gzcy.html"})
        j = r.json()
        w("keys=" + str(list(j.keys())))
        cont = j.get("content") or {}
        w("content keys=" + str(list(cont.keys())))
        lst = cont.get("list") or []
        if lst:
            w("item keys=" + str(list(lst[0].keys())))
            w(json.dumps(lst[0], ensure_ascii=False)[:900])
        lid = lst[0].get("id") if lst else None
        rr = c.get("http://www.lyg.gov.cn/TrueCMS/visitorController/letterView.do",
                   params={"id": lid},
                   headers={"Referer": "http://www.lyg.gov.cn/zglygzfmhwz/gzcy/gzcy.html"})
        w(f"  DET letterView -> {rr.status_code} len={len(rr.text)}")
        import re as _re
        t = _re.sub(r"\s+", " ", _re.sub(r"<[^>]+>", " ", rr.text))
        w("  " + t[:400])

    print("written", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
