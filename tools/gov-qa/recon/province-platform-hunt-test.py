"""24 省互动平台重探 —— 阶段三：实测候选接口（通/不通都要落证据）。

对每个候选接口发一次请求，打印 status / 长度 / 前若干条标题。
用法：python recon/province-platform-hunt-test.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")

import httpx  # noqa: E402


def show(tag, r):
    print(f"\n### {tag}")
    print(f"    status={r.status_code} len={len(r.text or '')} ct={r.headers.get('content-type','')}")
    t = (r.text or "").strip()
    print("    body[:400]:", t[:400].replace("\n", " "))


def main() -> int:
    out = []
    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=25, follow_redirects=True) as c:
        # 1) 宁夏 IGI 列表
        u = "https://www.nx.gov.cn/IGI/nbhd/openGovmsgbox.do"
        try:
            r = c.get(u, params={"method": "listGovmsgboxs", "siteId": 115,
                                 "order": 1, "appID": "4", "pageIndex": 1, "pageSize": 10},
                      headers={"Referer": "https://www.nx.gov.cn/hdjl/"})
            show("宁夏 listGovmsgboxs", r)
            out.append({"site": "宁夏", "url": str(r.request.url), "status": r.status_code,
                        "len": len(r.text or ""), "body": (r.text or "")[:3000]})
        except Exception as e:                                              # noqa: BLE001
            print("宁夏 ERR", type(e).__name__, e)
            out.append({"site": "宁夏", "error": type(e).__name__})

        # 2) 山西 IGI 列表
        u = "http://www.shanxi.gov.cn/IGI/nbhd/openGovmsgbox.do"
        try:
            r = c.get(u, params={"method": "listGovmsgboxs", "siteId": 110,
                                 "pageIndex": 1, "pageSize": 10, "appId": 1742326},
                      headers={"Referer": "http://www.shanxi.gov.cn/zmhd/"})
            show("山西 listGovmsgboxs", r)
            out.append({"site": "山西", "url": str(r.request.url), "status": r.status_code,
                        "len": len(r.text or ""), "body": (r.text or "")[:3000]})
        except Exception as e:                                              # noqa: BLE001
            print("山西 ERR", type(e).__name__, e)
            out.append({"site": "山西", "error": type(e).__name__})

        # 3) 内蒙古 xinxiang api
        u = "https://www.nmg.gov.cn/xinxiang/api/getCaseInfoList"
        try:
            r = c.post(u, json={"title": "", "first": 1, "pageSize": 5},
                       headers={"Referer": "https://www.nmg.gov.cn/zmhd/",
                                "Content-Type": "application/json"})
            show("内蒙古 getCaseInfoList", r)
            out.append({"site": "内蒙古", "url": u, "status": r.status_code,
                        "len": len(r.text or ""), "body": (r.text or "")[:3000]})
        except Exception as e:                                              # noqa: BLE001
            print("内蒙古 ERR", type(e).__name__, e)
            out.append({"site": "内蒙古", "error": type(e).__name__})

    (HERE / "province-platform-hunt-test.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n[test] 证据已写 province-platform-hunt-test.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
