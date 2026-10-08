"""最终验证：山东 dataproxy 分页+明细、广西 IGI 明细、青海页区分、西藏替代路径。"""
from __future__ import annotations

import os
import re
import sys
import time

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx  # noqa: E402

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
HERE = os.path.dirname(os.path.abspath(__file__))
PAUSE = 1.5


def main() -> int:
    with httpx.Client(timeout=30, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False) as c:
        print("== 山东 dataproxy.jsp 第1/2页 ==")
        base = ("http://www.shandong.gov.cn/module/web/jpage/dataproxy.jsp"
                "?webid=410&path=http://www.shandong.gov.cn/&columnid=100084"
                "&unitid=496859&permissiontype=0")
        for pg in (1, 2):
            r = c.get(base + f"&page={pg}",
                      headers={"Referer": "http://www.shandong.gov.cn/col/col100084/index.html"})
            t = r.text or ""
            links = re.findall(r'href="([^"]+/art/[^"]+)"[^>]*>([^<]*)</a>', t)
            print(f"  page{pg}: HTTP {r.status_code} len={len(t)} 链接数={len(links)}")
            for u, ti in links[:3]:
                print(f"      {ti[:36]}  {u}")
            time.sleep(PAUSE)

        print("== 山东 反馈回应明细 ==")
        r = c.get("http://www.shandong.gov.cn/art/2026/9/18/art_100084_26569.html")
        t = r.text or ""
        open(os.path.join(HERE, "sd-art-detail.html"), "w", encoding="utf-8").write(t)
        print(f"  HTTP {r.status_code} len={len(t)}")
        for kw in ["无线电台", "答复", "回复", "TRS", "conTxt", "class=\"view"]:
            print("    ", kw, t.find(kw))

        print("== 广西 IGI 明细 ==")
        u = ("http://www.gxzf.gov.cn/IGI/nbhd/openGovmsgbox.do?method=listGovmsgboxs"
             "&order=1&siteId=3&appId=133&pageSize=1&pageIndex=1")
        r = c.get(u, headers={"Referer": "http://www.gxzf.gov.cn/hdjl/mailbox/index.shtml"})
        mid = None
        try:
            d = r.json()["datas"]["data"][0]
            mid = d.get("METADATAID")
            print("   list item:", {k: str(d.get(k))[:40] for k in
                  ("TITLE", "METADATAID", "ISREPLY", "PROVINCE", "CITY", "AREA", "DEALDEPTNAME")})
        except Exception as e:  # noqa: BLE001
            print("   parse err", e)
        time.sleep(PAUSE)
        if mid:
            du = ("http://www.gxzf.gov.cn/IGI/nbhd/openGovmsgbox.do?method=viewGovmsgbox"
                  f"&siteId=3&metadataId={mid}")
            dr = c.get(du, headers={"Referer": "http://www.gxzf.gov.cn/hdjl/mailbox/index.shtml"})
            try:
                dd = dr.json()["datas"]
                reps = dd.get("REPLYS") or []
                print(f"   detail HTTP {dr.status_code} REPLYS={len(reps)} "
                      f"ans_len={len((reps[-1].get('REPLYHTMLCONTENT') or '')) if reps else 0}")
            except Exception as e:  # noqa: BLE001
                print("   detail err", e, (dr.text or "")[:200])

        print("== 青海 index vs page026 首条对比 ==")
        for name, u in (("index", "http://www.qinghai.gov.cn/zmhd/wsxf/index.html"),
                        ("p026", "http://www.qinghai.gov.cn/zmhd/system/count/0005002/000000000000/000/000/c0005002000000000000_000000026.shtml")):
            r = c.get(u)
            t = r.text or ""
            # 取左侧第一个 /zmhd/system 明细链接
            m = re.search(r'href="(http://www\.qinghai\.gov\.cn/zmhd/system/[^"]+)"[^>]*title="([^"]*)"', t)
            print(f"  {name}: HTTP {r.status_code} 首条={m.group(2)[:30] if m else None} {m.group(1) if m else ''}")
            time.sleep(PAUSE)

        print("== 西藏 替代路径 ==")
        for u in ("http://xzxf.xizang.gov.cn/ocp/wypj.html",
                  "http://xzxf.xizang.gov.cn/ocp/wyjy.html",
                  "http://xzxf.xizang.gov.cn/ocp/xfzn.html"):
            try:
                r = c.get(u)
                print(f"  {u} -> HTTP {r.status_code} len={len(r.text or '')} final={r.url}")
            except Exception as e:  # noqa: BLE001
                print(f"  {u} -> {type(e).__name__}: {e}")
            time.sleep(PAUSE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
