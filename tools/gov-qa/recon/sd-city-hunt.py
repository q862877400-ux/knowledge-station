"""山东地市级门户「政民互动」入口侦察（前 5 市：济南/青岛/淄博/枣庄/东营）。

思路：抓门户首页（http+https）→ 抠含互动关键词的链接 → 打印候选 URL，人工/后续脚本
再逐个套中间件指纹（IGI / WAS5 / jact / hanweb / enorth / 静态）。
用法：python recon/sd-city-hunt.py
输出：recon/sd-city-hunt.txt + recon/sd-city-<abbr>-home.html
"""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import UA  # noqa: E402

CITIES = [
    ("济南", "jinan", ["http://www.jinan.gov.cn/", "https://www.jinan.gov.cn/"]),
    ("青岛", "qingdao", ["http://www.qingdao.gov.cn/", "https://www.qingdao.gov.cn/"]),
    ("淄博", "zibo", ["http://www.zibo.gov.cn/", "https://www.zibo.gov.cn/"]),
    ("枣庄", "zaozhuang", ["http://www.zaozhuang.gov.cn/", "https://www.zaozhuang.gov.cn/"]),
    ("东营", "dongying", ["http://www.dongying.gov.cn/", "https://www.dongying.gov.cn/"]),
]

KW = ("政民互动", "互动交流", "12345", "市长信箱", "书记信箱", "留言", "咨询投诉",
      "网上民声", "民声", "回应", "信箱", "问政", "诉求", "建议")
OUT = HERE / "sd-city-hunt.txt"


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
            for city, abbr, urls in CITIES:
                f.write(f"\n{'='*70}\n## {city} ({abbr})\n")
                got = False
                for url in urls:
                    try:
                        r = c.get(url)
                        code = r.status_code
                    except Exception as e:                              # noqa: BLE001
                        f.write(f"  {url} → {type(e).__name__}: {str(e)[:80]}\n")
                        continue
                    f.write(f"  {url} → {code} ({len(r.text)} bytes)\n")
                    if code == 200 and not got:
                        got = True
                        (HERE / f"sd-city-{abbr}-home.html").write_text(r.text, encoding="utf-8")
                        for txt, href in links(r.text, url)[:40]:
                            f.write(f"      [{txt}] {href}\n")
                    time.sleep(1.0)
    print("written", OUT)
    return 0


if __name__ == "__main__":
    main()
