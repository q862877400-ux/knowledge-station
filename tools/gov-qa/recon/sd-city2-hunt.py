"""山东地市 6–16 市入口侦察：抓门户首页（http+https）→ 抠互动链接 + 中间件指纹。
用法：python recon/sd-city2-hunt.py
输出：recon/sd-city2-hunt.txt + recon/sd-city2-<abbr>-home.html
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
sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import UA  # noqa: E402

CITIES = [
    ("烟台", "yantai", "yantai.gov.cn"),
    ("潍坊", "weifang", "weifang.gov.cn"),
    ("济宁", "jining", "jining.gov.cn"),
    ("泰安", "taian", "taian.gov.cn"),
    ("威海", "weihai", "weihai.gov.cn"),
    ("日照", "rizhao", "rizhao.gov.cn"),
    ("临沂", "linyi", "linyi.gov.cn"),
    ("德州", "dezhou", "dezhou.gov.cn"),
    ("聊城", "liaocheng", "liaocheng.gov.cn"),
    ("滨州", "binzhou", "binzhou.gov.cn"),
    ("菏泽", "heze", "heze.gov.cn"),
]
KW = ("政民互动", "互动交流", "12345", "市长信箱", "书记信箱", "留言", "咨询投诉",
      "网上民声", "民声", "回应", "信箱", "问政", "诉求", "建议", "我要")
FINGER = ("openGovmsgbox", "listGovmsgboxs", "/IGI/", "jact", "jpaas-jact",
          "mailpub", "dataproxy", "ajaxlist", "channelid", "was5")
OUT = HERE / "sd-city2-hunt.txt"


def links(html: str, base: str) -> list[tuple[str, str]]:
    out = []
    for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html, re.I | re.S):
        href, txt = m.group(1), re.sub(r"<[^>]+>", "", m.group(2)).strip()
        if not txt:
            continue
        if any(k in txt for k in KW):
            out.append((txt[:36], urljoin(base, href)))
    return out


def main() -> int:
    import httpx
    with httpx.Client(headers={"User-Agent": UA}, trust_env=False, timeout=15,
                      follow_redirects=True) as c:
        with OUT.open("w", encoding="utf-8") as f:
            for city, abbr, host in CITIES:
                f.write(f"\n{'='*70}\n## {city} ({abbr}) {host}\n")
                got = False
                for scheme in ("http", "https"):
                    url = f"{scheme}://www.{host}/"
                    try:
                        r = c.get(url)
                        code = r.status_code
                    except Exception as e:                                  # noqa: BLE001
                        f.write(f"  {url} → {type(e).__name__}: {str(e)[:70]}\n")
                        continue
                    f.write(f"  {url} → {code} ({len(r.text)} bytes)\n")
                    if code == 200 and not got:
                        got = True
                        (HERE / f"sd-city2-{abbr}-home.html").write_text(
                            r.text, encoding="utf-8")
                        hits = [k for k in FINGER if k in r.text]
                        f.write(f"     finger-hits: {hits}\n")
                        seen = set()
                        for txt, href in links(r.text, url):
                            if href in seen:
                                continue
                            seen.add(href)
                            f.write(f"       [{txt}] {href}\n")
                    time.sleep(0.8)
    print("written", OUT)
    return 0


if __name__ == "__main__":
    main()
