"""苏州/无锡/连云港 明细接口定位（stage7）。"""
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
OUT = os.path.join(HERE, "city-js-probe7.txt")


def main() -> int:
    import httpx
    with httpx.Client(headers={"User-Agent": UA}, trust_env=False, timeout=25,
                      follow_redirects=True) as c, open(OUT, "w", encoding="utf-8") as f:
        def w(s=""):
            f.write(s + "\n")
            print(s[:220])

        w("## 苏州 完整项（看是否自带答复）")
        r = c.get("https://www.suzhou.gov.cn/consultfront/common/bmxxCommonlist",
                  params={"pageNum": 1, "pageSize": 1},
                  headers={"Referer": "https://www.suzhou.gov.cn/szsrmzf/hd_xjly/xjly.shtml"})
        it = (r.json().get("infolist") or [{}])[0]
        w(json.dumps(it, ensure_ascii=False, indent=1)[:1600])

        w("\n## 无锡：从 JS 找 detail/answer 接口")
        for js in ["/static_2023/js/list_page.js"]:
            try:
                jt = c.get("https://www.wuxi.gov.cn" + js,
                           headers={"Referer": "https://www.wuxi.gov.cn/hdjl/index.shtml"}).text
                for m in re.finditer(r'["\'](/mailbox/[^"\']+)["\']', jt):
                    w("  MAILBOX " + m.group(1))
                for m in re.finditer(r'url\s*[:=]\s*["\']([^"\']+)["\']', jt):
                    w("  URL " + m.group(1)[:110])
            except Exception as e:                                          # noqa: BLE001
                w(f"  {js} ERR {str(e)[:60]}")
        # 直接试常见 detail 路径（用 answerID）
        aid = it.get("answerID") if False else None
        r2 = c.get("https://www.wuxi.gov.cn/mailbox/letter/search",
                   params={"pageNum": 1, "pageSize": 1},
                   headers={"Referer": "https://www.wuxi.gov.cn/hdjl/index.html"})
        li = ((r2.json().get("data") or {}).get("data") or [{}])[0]
        w("  无锡 item full keys=" + str(list(li.keys())))
        aid = li.get("answerID")
        w(f"  answerID={aid}")
        for p in ["/mailbox/letter/getAnswer", "/mailbox/letter/answer",
                  "/mailbox/letter/detailByAnswer", "/mailbox/letter/searchAnswer"]:
            for key in ["answerID", "id"]:
                try:
                    rr = c.get("https://www.wuxi.gov.cn" + p, params={key: aid},
                               headers={"Referer": "https://www.wuxi.gov.cn/hdjl/index.html"})
                    if "数据未查到" not in rr.text:
                        w(f"  DET {p} {key} -> {rr.status_code} {rr.text[:160]}")
                except Exception as e:                                      # noqa: BLE001
                    w(f"  DET {p} ERR {str(e)[:50]}")
                time.sleep(0.4)

        w("\n## 连云港：从 JS 找 detail 接口")
        for u in ["http://www.lyg.gov.cn/zglygzfmhwz/lygmhwzsjbsy/js/jquery.tab.js",
                  "http://www.lyg.gov.cn/zglygzfmhwz/lygmhwzsjbsy/js/newheader.js"]:
            try:
                jt = c.get(u, headers={"Referer": "http://www.lyg.gov.cn/zglygzfmhwz/gzcy/gzcy.html"}).text
                for m in re.finditer(r'["\']([^"\']*(?:Letter|letter|mailBox|MailBox)[^"\']*)["\']', jt):
                    w("  " + m.group(1)[:110])
            except Exception as e:                                          # noqa: BLE001
                w(f"  {u} ERR {str(e)[:50]}")
        # 试 letterView 的正确参数（可能是 letterId / lrmailbox）
        for key in ["id", "letterId", "lrmailbox", "letternumber"]:
            try:
                rr = c.get("http://www.lyg.gov.cn/TrueCMS/mailBoxLetterController/getLetterDetail.do",
                           params={key: li and "x"}, headers={"Referer": "http://www.lyg.gov.cn/"})
                w(f"  try getLetterDetail {key} -> {rr.status_code} {rr.text[:80]}")
            except Exception as e:                                          # noqa: BLE001
                w(f"  ERR {str(e)[:50]}")
            time.sleep(0.4)

    print("written", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
