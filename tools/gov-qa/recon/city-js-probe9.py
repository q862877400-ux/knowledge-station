"""stage9：苏州/无锡 完整字段 + 连云港 letterView 内容 + 南通/南京。"""
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
OUT = os.path.join(HERE, "city-js-probe9.txt")


def main() -> int:
    import httpx
    with httpx.Client(headers={"User-Agent": UA}, trust_env=False, timeout=25,
                      follow_redirects=True) as c, open(OUT, "w", encoding="utf-8") as f:
        def w(s=""):
            f.write(s + "\n")
            print(s[:300])

        w("## 苏州 item 完整 JSON")
        r = c.get("https://www.suzhou.gov.cn/consultfront/common/bmxxCommonlist",
                  params={"pageNum": 1, "pageSize": 1},
                  headers={"Referer": "https://www.suzhou.gov.cn/szsrmzf/hd_xjly/xjly.shtml"})
        w(json.dumps((r.json().get("infolist") or [{}])[0], ensure_ascii=False, indent=1))
        # 分页语义
        for pn in [1, 2, 20]:
            rr = c.get("https://www.suzhou.gov.cn/consultfront/common/bmxxCommonlist",
                       params={"pageNum": pn, "pageSize": 10},
                       headers={"Referer": "https://www.suzhou.gov.cn/szsrmzf/hd_xjly/xjly.shtml"})
            l = rr.json().get("infolist") or []
            w(f"  pageNum={pn} n={len(l)} first={l[0].get('consult_title') if l else None}")

        w("\n## 无锡 item 完整 JSON")
        r2 = c.get("https://www.wuxi.gov.cn/mailbox/letter/search",
                   params={"pageNum": 1, "pageSize": 1},
                   headers={"Referer": "https://www.wuxi.gov.cn/hdjl/index.html"})
        d = (r2.json().get("data") or {})
        w(json.dumps((d.get("data") or [{}])[0], ensure_ascii=False, indent=1)[:1800])
        # 分页
        for pn in [1, 2, 20]:
            rr = c.get("https://www.wuxi.gov.cn/mailbox/letter/search",
                       params={"pageNum": pn, "pageSize": 10},
                       headers={"Referer": "https://www.wuxi.gov.cn/hdjl/index.html"})
            l = ((rr.json().get("data") or {}).get("data")) or []
            w(f"  pageNum={pn} n={len(l)} first={l[0].get('title') if l else None}")

        w("\n## 连云港 letterView 内容（lrmailbox）")
        r3 = c.get("http://www.lyg.gov.cn/TrueCMS/mailBoxLetterController/getLetterList.do",
                   params={"pageNum": 1, "numPerPage": 1},
                   headers={"Referer": "http://www.lyg.gov.cn/zglygzfmhwz/gzcy/gzcy.html"})
        li = (((r3.json().get("content") or {}).get("list")) or [{}])[0]
        w("  list item=" + json.dumps(li, ensure_ascii=False)[:300])
        rr = c.get("http://www.lyg.gov.cn/TrueCMS/visitorController/letterView.do",
                   params={"lrmailbox": li.get("lrmailbox"), "id": li.get("id")},
                   headers={"Referer": "http://www.lyg.gov.cn/zglygzfmhwz/gzcy/gzcy.html"})
        t = re.sub(r"\s+", " ", re.sub(r"<script.*?</script>", " ",
                                       re.sub(r"<[^>]+>", " ", rr.text), flags=re.S))
        w("  letterView text=" + t[:600])

        w("\n## 南通 TrueCMS：试 getInteractiveJson / getPetitionListByType")
        for u in ["https://www.nantong.gov.cn/truecms/visitorController/getInteractiveJson.do?numPerPage=5&siteId=",
                  "https://www.nantong.gov.cn/truecms/letterController/xxList.do?numPerPage=10&pageNum=1"]:
            try:
                rr = c.get(u, headers={"Referer": "https://www.nantong.gov.cn/ntsrmzf/sgkxj/sgkxj.html"})
                w(f"  {u.split('/')[-1][:40]} -> {rr.status_code} {rr.text[:160]}")
            except Exception as e:                                          # noqa: BLE001
                w(f"  ERR {str(e)[:60]}")
            time.sleep(0.6)

        w("\n## 南京 hdjl 内联/脚本")
        h = c.get("https://www.nanjing.gov.cn/hdjl/", headers={"Referer": "https://www.nanjing.gov.cn/"}).text
        for m in re.finditer(r'src=["\']([^"\']+\.js[^"\']*)["\']', h, re.I):
            w("  JS " + m.group(1))
        for m in re.finditer(r'(https?://[^"\'\s]+|/[A-Za-z][^"\'\s]{3,60})', h):
            s = m.group(0)
            if any(k in s.lower() for k in ("hdjl", "szxx", "letter", "mail", "api", "zhengfuxinxiang")):
                w("  CAND " + s[:110])

    print("written", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
