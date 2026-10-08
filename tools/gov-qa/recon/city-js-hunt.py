"""江苏 13 地市门户「政民互动」入口侦察。

抓门户首页（http+https）→ 抠含互动关键词的链接 → 打印候选 URL + 保存首页 HTML。
用法：python recon/city-js-hunt.py
输出：recon/city-js-hunt.txt + recon/city-js-<abbr>-home.html
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

CITIES = [
    ("南京", "nanjing", "www.nanjing.gov.cn"),
    ("无锡", "wuxi", "www.wuxi.gov.cn"),
    ("徐州", "xuzhou", "www.xz.gov.cn"),
    ("常州", "changzhou", "www.changzhou.gov.cn"),
    ("苏州", "suzhou", "www.suzhou.gov.cn"),
    ("南通", "nantong", "www.nantong.gov.cn"),
    ("连云港", "lianyungang", "www.lyg.gov.cn"),
    ("淮安", "huaian", "www.huaian.gov.cn"),
    ("盐城", "yancheng", "www.yancheng.gov.cn"),
    ("扬州", "yangzhou", "www.yangzhou.gov.cn"),
    ("镇江", "zhenjiang", "www.zhenjiang.gov.cn"),
    ("泰州", "taizhou", "www.taizhou.gov.cn"),
    ("宿迁", "suqian", "www.suqian.gov.cn"),
]

KW = ("政民互动", "互动交流", "12345", "市长信箱", "书记信箱", "留言", "咨询投诉",
      "网上民声", "民声", "回应", "信箱", "问政", "诉求", "建议", "民意", "热线")
OUT = HERE / "city-js-hunt.txt"


def links(html: str, base: str) -> list[tuple[str, str]]:
    out = []
    for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.I | re.S):
        href, txt = m.group(1), re.sub(r"<[^>]+>", "", m.group(2)).strip()
        if not txt:
            continue
        if any(k in txt for k in KW):
            out.append((txt[:40], urljoin(base, href)))
    return out


def main() -> int:
    import httpx
    with httpx.Client(headers={"User-Agent": UA}, trust_env=False, timeout=15,
                      follow_redirects=True) as c:
        with OUT.open("w", encoding="utf-8") as f:
            for city, abbr, host in CITIES:
                f.write(f"\n{'='*70}\n## {city} ({host})\n")
                got = False
                for scheme in ("https", "http"):
                    url = f"{scheme}://{host}/"
                    try:
                        r = c.get(url)
                        code = r.status_code
                    except Exception as e:                              # noqa: BLE001
                        f.write(f"  {url} → {type(e).__name__}: {str(e)[:80]}\n")
                        continue
                    f.write(f"  {url} → {code} ({len(r.text)} bytes) final={r.url}\n")
                    if code == 200 and not got:
                        got = True
                        (HERE / f"city-js-{abbr}-home.html").write_text(
                            r.text, encoding="utf-8")
                        seen = set()
                        for txt, href in links(r.text, str(r.url))[:60]:
                            if href in seen:
                                continue
                            seen.add(href)
                            f.write(f"      [{txt}] {href}\n")
                    time.sleep(1.0)
    print("written", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
