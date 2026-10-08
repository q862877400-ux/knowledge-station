"""stage8：苏州答复字段完整性 + 无锡/连云港明细接口定位。"""
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
OUT = os.path.join(HERE, "city-js-probe8.txt")


def main() -> int:
    import httpx
    with httpx.Client(headers={"User-Agent": UA}, trust_env=False, timeout=25,
                      follow_redirects=True) as c, open(OUT, "w", encoding="utf-8") as f:
        def w(s=""):
            f.write(s + "\n")
            print(s[:260])

        # 苏州 答复字段
        w("## 苏州 bmxxCommonlist 答复字段")
        r = c.get("https://www.suzhou.gov.cn/consultfront/common/bmxxCommonlist",
                  params={"pageNum": 1, "pageSize": 2},
                  headers={"Referer": "https://www.suzhou.gov.cn/szsrmzf/hd_xjly/xjly.shtml"})
        for it in (r.json().get("infolist") or []):
            w("  title=" + str(it.get("consult_title")))
            w("  revert_content(len=%d)=" % len(str(it.get("consult_revert_content") or ""))
              + str(it.get("consult_revert_content"))[:300])

        # 无锡 list_page.js
        w("\n## 无锡 list_page.js")
        jt = c.get("https://www.wuxi.gov.cn/static_2023/js/list_page.js",
                   headers={"Referer": "https://www.wuxi.gov.cn/hdjl/index.shtml"}).text
        for m in re.finditer(r'url\s*[:=]\s*["\']([^"\']+)["\']', jt):
            w("  URL " + m.group(1)[:120])
        for m in re.finditer(r'/mailbox/[A-Za-z0-9_/]+', jt):
            w("  MB " + m.group(0))

        # 无锡 hdjl/index.shtml 内联脚本
        w("\n## 无锡 hdjl/index.shtml 内联 ajax")
        h = c.get("https://www.wuxi.gov.cn/hdjl/index.shtml",
                  headers={"Referer": "https://www.wuxi.gov.cn/"}).text
        for m in re.finditer(r'(url\s*:\s*["\'][^"\']+["\']|/mailbox/[A-Za-z0-9_/]+|/intertidwebapp/[A-Za-z0-9_/]+)', h):
            w("  " + m.group(0)[:120])

        # 连云港 gzcy.html 内联脚本
        w("\n## 连云港 gzcy.html 内联 ajax")
        h2 = c.get("http://www.lyg.gov.cn/zglygzfmhwz/gzcy/gzcy.html",
                   headers={"Referer": "http://www.lyg.gov.cn/"}).text
        for m in re.finditer(r'(url\s*[:=]\s*["\'][^"\']+["\']|getLetter[A-Za-z]*|letterView|TrueCMS/[A-Za-z0-9_/.]+)', h2):
            w("  " + m.group(0)[:120])
        # 找内联 script 段
        i = h2.find('getLetterList')
        if i >= 0:
            w("  --- around getLetterList ---")
            w("  " + re.sub(r"\s+", " ", h2[i-400:i+500])[:800])

        # 连云港 试 letterView 用 lrmailbox / letternumber
        w("\n## 连云港 letterView 试参")
        r3 = c.get("http://www.lyg.gov.cn/TrueCMS/mailBoxLetterController/getLetterList.do",
                   params={"pageNum": 1, "numPerPage": 1},
                   headers={"Referer": "http://www.lyg.gov.cn/zglygzfmhwz/gzcy/gzcy.html"})
        li = (((r3.json().get("content") or {}).get("list")) or [{}])[0]
        w("  item=" + json.dumps(li, ensure_ascii=False)[:400])
        for key in ["id", "lrmailbox", "letternumber", "mailbox"]:
            for path in ["/TrueCMS/visitorController/letterView.do",
                         "/TrueCMS/mailBoxLetterController/getLetterContent.do",
                         "/TrueCMS/mailBoxLetterController/letterDetail.do"]:
                try:
                    rr = c.get("http://www.lyg.gov.cn" + path, params={key: li.get(key)},
                               headers={"Referer": "http://www.lyg.gov.cn/zglygzfmhwz/gzcy/gzcy.html"})
                    if rr.status_code == 200 and len(rr.text) > 200:
                        w(f"  {path} {key}={li.get(key)} -> {rr.status_code} {len(rr.text)}B")
                except Exception as e:                                      # noqa: BLE001
                    pass
                time.sleep(0.3)

    print("written", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
