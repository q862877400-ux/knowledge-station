"""stage10：苏州/无锡 分页参数名 + 南通 siteId + 南京 huifuxuandeng。"""
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
OUT = os.path.join(HERE, "city-js-probe10.txt")


def main() -> int:
    import httpx
    with httpx.Client(headers={"User-Agent": UA}, trust_env=False, timeout=25,
                      follow_redirects=True) as c, open(OUT, "w", encoding="utf-8") as f:
        def w(s=""):
            f.write(s + "\n")
            print(s[:300])

        # 苏州 分页参数名穷举
        w("## 苏州 bmxxCommonlist 分页参数名")
        base = "https://www.suzhou.gov.cn/consultfront/common/bmxxCommonlist"
        ref = {"Referer": "https://www.suzhou.gov.cn/szsrmzf/hd_xjly/xjly.shtml"}
        first = None
        for key in ["pageNum", "page", "currentPage", "pageNo", "pageIndex", "start", "offset"]:
            r = c.get(base, params={key: 2, "pageSize": 10}, headers=ref)
            l = r.json().get("infolist") or []
            t = l[0].get("consult_title") if l else None
            w(f"  {key}=2 -> n={len(l)} first={t}")
            time.sleep(0.3)

        # 无锡 分页参数名穷举
        w("\n## 无锡 letter/search 分页参数名")
        base2 = "https://www.wuxi.gov.cn/mailbox/letter/search"
        ref2 = {"Referer": "https://www.wuxi.gov.cn/hdjl/index.html"}
        for key in ["pageNum", "page", "currentPage", "pageNo", "pageIndex", "start"]:
            r = c.get(base2, params={key: 2, "pageSize": 10}, headers=ref2)
            l = ((r.json().get("data") or {}).get("data")) or []
            t = l[0].get("title") if l else None
            w(f"  {key}=2 -> n={len(l)} first={t}")
            time.sleep(0.3)
        # 无锡 完整 item（找答复字段）
        r = c.get(base2, params={"page": 1, "size": 1}, headers=ref2)
        it = (((r.json().get("data") or {}).get("data")) or [{}])[0]
        w("  无锡 item 全字段=" + json.dumps(it, ensure_ascii=False)[:1500])

        # 南通 siteId
        w("\n## 南通 siteId")
        h = c.get("https://www.nantong.gov.cn/ntsrmzf/sgkxj/sgkxj.html",
                  headers={"Referer": "https://www.nantong.gov.cn/"}).text
        for m in re.finditer(r'siteId["\']?\s*[:=]\s*["\']?([0-9a-fA-F-]{20,})', h):
            w("  siteId=" + m.group(1))
        for m in re.finditer(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', h):
            w("  UUID " + m.group(0))
        # 试 getInteractiveJson
        for sid in re.findall(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', h)[:3]:
            r = c.get("https://www.nantong.gov.cn/truecms/visitorController/getInteractiveJson.do",
                      params={"numPerPage": 5, "siteId": sid},
                      headers={"Referer": "https://www.nantong.gov.cn/ntsrmzf/sgkxj/sgkxj.html"})
            w(f"  getInteractiveJson siteId={sid} -> {r.status_code} {r.text[:200]}")
            time.sleep(0.5)

        # 南京 huifuxuandeng
        w("\n## 南京 szxx huifuxuandeng")
        for u in ["https://szxx.nanjing.gov.cn:32767/zhengfuxinxiang/huifuxuandeng?orgid=320113&type=sszxx",
                  "https://szxx.nanjing.gov.cn:32767/zhengfuxinxiang/huifuxuandeng?orgid=320113&type=sszxx&pageNum=1",
                  "https://szxx.nanjing.gov.cn:32767/zfxx/letterList?orgid=320113&type=sszxx"]:
            try:
                r = c.get(u, headers={"Referer": "https://www.nanjing.gov.cn/hdjl/"})
                w(f"  {u[-70:]} -> {r.status_code} {r.text[:150]}")
            except Exception as e:                                          # noqa: BLE001
                w(f"  {u[-70:]} ERR {type(e).__name__} {str(e)[:60]}")
            time.sleep(0.6)

    print("written", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
