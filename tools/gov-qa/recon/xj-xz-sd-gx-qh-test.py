"""接口实测：广西 IGI、新疆信访端点、青海静态分页。"""
from __future__ import annotations

import os
import sys
import time

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx  # noqa: E402

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
PAUSE = 1.5


def show(label, r):
    body = r.text or ""
    print(f"  {label} -> HTTP {r.status_code} len={len(body)}")
    print("    " + body[:400].replace("\n", " "))


def main() -> int:
    with httpx.Client(timeout=30, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False) as c:
        print("== 广西 IGI 列表 ==")
        u = ("http://www.gxzf.gov.cn/IGI/nbhd/openGovmsgbox.do?method=listGovmsgboxs"
             "&order=1&siteId=3&appId=133&pageSize=5&pageIndex=1")
        r = c.get(u, headers={"Referer": "http://www.gxzf.gov.cn/hdjl/mailbox/index.shtml"})
        show("list", r)
        time.sleep(PAUSE)

        print("== 青海 群众诉求回应 第2页 ==")
        u2 = ("http://www.qinghai.gov.cn/zmhd/system/count/0005002/000000000000/000/000/"
              "c0005002000000000000_000000002.shtml")
        show("qh-p2", c.get(u2))
        time.sleep(PAUSE)

        print("== 新疆 getLetterList ==")
        u3 = ("http://wsxf.xjxfj.gov.cn/letter/pre-accept-letter-info!getLetterList.action"
              "?regionCode=650000000000")
        show("getLetterList", c.post(u3, data={"pageIndex": "1", "pageSize": "7"},
             headers={"Referer": "http://wsxf.xjxfj.gov.cn/html/onlineInquiry/onlineILsit.jsp"}))
        time.sleep(PAUSE)

        print("== 新疆 letterFeedbackList ==")
        u4 = "http://wsxf.xjxfj.gov.cn/letter/pre-accept-letter-info!letterFeedbackList.action"
        show("letterFeedbackList", c.post(u4, data={"maxResults": "50"},
             headers={"Referer": "http://wsxf.xjxfj.gov.cn/html/main/index.jsp"}))
        time.sleep(PAUSE)

        print("== 新疆 checkLogon ==")
        show("checkLogon", c.post("http://wsxf.xjxfj.gov.cn/user/network-user-info!checkLogon.action",
             data={}, headers={"Referer": "http://wsxf.xjxfj.gov.cn/html/main/index.jsp"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
