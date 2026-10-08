"""实测：山东 12345 API、山东反馈回应列表、青海分页变体。"""
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
        print("== 山东 12345 CommonHandler.ashx (szf_wz_base_list) ==")
        u = "http://www.shandong.gov.cn/12345/szfwz/CommonHandler.ashx"
        for meth in ("post", "get"):
            try:
                if meth == "post":
                    r = c.post(u, data={"opreate": "szf_wz_base_list", "page": "1", "limit": "20"},
                               headers={"Referer": "http://www.shandong.gov.cn/12345/szfwz/ListDxal.aspx"})
                else:
                    r = c.get(u, params={"opreate": "szf_wz_base_list", "page": "1", "limit": "20"},
                              headers={"Referer": "http://www.shandong.gov.cn/12345/szfwz/ListDxal.aspx"})
                print(f"  [{meth}] HTTP {r.status_code} len={len(r.text or '')}")
                print("    " + (r.text or "")[:500].replace("\n", " "))
            except Exception as e:  # noqa: BLE001
                print(f"  [{meth}] {type(e).__name__}: {e}")
            time.sleep(PAUSE)

        print("== 山东 反馈回应 /col/col100084/index.html ==")
        r = c.get("http://www.shandong.gov.cn/col/col100084/index.html")
        txt = r.text or ""
        open(os.path.join(HERE, "sd-col100084.html"), "w", encoding="utf-8").write(txt)
        print(f"  HTTP {r.status_code} len={len(txt)}")
        print("  条目数(fkhylist)=", txt.count("fkhylist"))
        for m in re.finditer(r"href=\"(http://www\.shandong\.gov\.cn/art/[^\"]+)\"[^>]*title=\"([^\"]*)\"", txt):
            print("    " + m.group(2)[:40] + "  " + m.group(1))
        # 找分页线索
        for kw in ["createPage", "pageCount", "totalPage", "index_", "countPage"]:
            i = txt.find(kw)
            if i >= 0:
                print(f"    [pager] {kw}: " + re.sub(r"\s+", " ", txt[i:i+120]))
        time.sleep(PAUSE)

        print("== 青海 分页变体 ==")
        variants = [
            "http://www.qinghai.gov.cn/zmhd/system/count/0005002/000000000000/000/000/c0005002000000000000_000000026.shtml",
            "http://www.qinghai.gov.cn/zmhd/system/count//0005002/000000000000/000/000/c0005002000000000000_000000026.shtml",
            "http://www.qinghai.gov.cn/zmhd/system/count/0005002/000000000000/000/000/c0005002000000000000_000000002.shtml",
        ]
        for u in variants:
            try:
                r = c.get(u)
                n = (r.text or "").count('class="item"')
                print(f"  HTTP {r.status_code} len={len(r.text or '')} items={n}  {u}")
            except Exception as e:  # noqa: BLE001
                print(f"  {type(e).__name__}: {e}  {u}")
            time.sleep(PAUSE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
