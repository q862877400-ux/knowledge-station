"""江苏地市互动列表页深挖（stage3）：抓列表页 → 报告 iframe/JSON/分页接口线索。

用法：python recon/city-js-probe3.py
输出：recon/city-js-probe3.txt + recon/city-js-<abbr>-list.html
"""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")

PAGES = [
    ("徐州", "xuzhou", "https://www.xz.gov.cn/004/004005/selectList.html"),
    ("常州", "changzhou", "https://www.changzhou.gov.cn/gova/letter"),
    ("镇江", "zhenjiang", "https://www.zhenjiang.gov.cn/zhenjiang/12345zx/xjgs_list.shtml"),
    ("扬州", "yangzhou", "https://www.yangzhou.gov.cn/jyszzxhf/index.html"),
    ("无锡", "wuxi", "https://www.wuxi.gov.cn/fzlm/hdjlgny/hygl/wdzmhd/index.shtml"),
    ("宿迁", "suqian", "https://www.suqian.gov.cn/cnsq/xinxiang/bmxxi_frame.shtml"),
    ("苏州", "suzhou", "https://www.suzhou.gov.cn/szsrmzf/hd_xjly/xjly.shtml"),
    ("南通", "nantong", "https://www.nantong.gov.cn/ntsrmzf/sgkxj/sgkxj.html"),
    ("连云港", "lianyungang", "http://12345.lyg.gov.cn/"),
]
OUT = HERE / "city-js-probe3.txt"
URLPAT = re.compile(r"""(?:url|action|href|src)\s*[:=]\s*['"]([^'"]{6,160})['"]""", re.I)


def main() -> int:
    import httpx
    with httpx.Client(headers={"User-Agent": UA}, trust_env=False, timeout=20,
                      follow_redirects=True) as c, OUT.open("w", encoding="utf-8") as f:
        def w(s: str) -> None:
            f.write(s + "\n")

        for city, abbr, url in PAGES:
            w(f"\n{'='*70}\n## {city}  {url}")
            try:
                r = c.get(url)
            except Exception as e:                                          # noqa: BLE001
                w(f"  → {type(e).__name__}: {str(e)[:90]}")
                continue
            w(f"  → {r.status_code} ({len(r.text)} bytes) final={r.url}")
            if r.status_code != 200:
                continue
            (HERE / f"city-js-{abbr}-list.html").write_text(r.text, encoding="utf-8")
            h = r.text
            # iframe
            for m in re.finditer(r'<iframe[^>]+src=["\']([^"\']+)["\']', h, re.I):
                w(f"  IFRAME {urljoin(str(r.url), m.group(1))}")
            # 脚本里出现的数据接口候选
            keys = ("jpaas", "jact", "api", ".do", ".json", "list", "page", "search",
                    "query", "IGI", "msgbox", "letter", "xjgs", "zmhd")
            seen = set()
            for m in URLPAT.finditer(h):
                u = m.group(1)
                if any(k.lower() in u.lower() for k in keys) and u not in seen:
                    seen.add(u)
                    w(f"  URL {u[:150]}")
                    if len(seen) > 25:
                        break
            # 分页/总数线索
            for m in re.finditer(r'(total|count|页|共)\D{0,8}(\d{2,7})', h):
                pass
            for m in re.finditer(r'(共|total\w*|totalRecord)\D{0,10}(\d{2,7})', h):
                w(f"  COUNT? {m.group(0)[:60]!r}")
            time.sleep(1.0)
    print("written", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
