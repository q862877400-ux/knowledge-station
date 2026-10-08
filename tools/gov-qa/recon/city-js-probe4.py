"""江苏剩余 7 市深挖（stage4）：苏州 SPA / 无锡 / 南通 / 连云港 / 南京 / 淮安 / 常州。

用法：python recon/city-js-probe4.py
输出：recon/city-js-probe4.txt
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
OUT = HERE / "city-js-probe4.txt"
API_RE = re.compile(r"""["']((?:/|https?://)[^"'\s]{4,120})["']""")
KEY = ("letter", "mail", "xjly", "zmhd", "hd_", "list", "api", "query",
       "/rest", "/u/", "szxx", "srmzf", "msgbox", "jact", "ajax")


def dig(c, f, name, urls, grepjs=True):
    f.write(f"\n{'='*70}\n## {name}\n")
    for url in urls:
        try:
            r = c.get(url)
        except Exception as e:                                              # noqa: BLE001
            f.write(f"  {url} → {type(e).__name__}: {str(e)[:80]}\n")
            continue
        f.write(f"  {url} → {r.status_code} ({len(r.text)})\n")
        if r.status_code != 200:
            continue
        h = r.text
        seen = set()
        for m in API_RE.finditer(h):
            u = m.group(1)
            if any(k in u.lower() for k in KEY) and u not in seen and not u.endswith(
                    (".css", ".png", ".jpg", ".gif", ".ico", ".woff", ".woff2")):
                seen.add(u)
                f.write(f"    URL {u[:130]}\n")
                if len(seen) > 30:
                    break
        if grepjs:
            jss = []
            for m in re.finditer(r'src=["\']([^"\']+\.js[^"\']*)["\']', h, re.I):
                jss.append(urljoin(str(r.url), m.group(1)))
            for js in jss[:6]:
                try:
                    jr = c.get(js)
                    if jr.status_code != 200:
                        continue
                    jt = jr.text
                    f.write(f"    JS {js.split('/')[-1][:30]} ({len(jt)}B)\n")
                    jseen = set()
                    for m in API_RE.finditer(jt):
                        u = m.group(1)
                        if (any(k in u.lower() for k in KEY)
                                and u not in jseen and len(u) > 5):
                            jseen.add(u)
                            f.write(f"      -> {u[:120]}\n")
                            if len(jseen) > 12:
                                break
                    time.sleep(0.4)
                except Exception:                                           # noqa: BLE001
                    pass
        time.sleep(0.8)


def main() -> int:
    import httpx
    with httpx.Client(headers={"User-Agent": UA}, trust_env=False, timeout=25,
                      follow_redirects=True) as c, OUT.open("w", encoding="utf-8") as f:
        dig(c, f, "苏州 xjly SPA 资源", [
            "https://www.suzhou.gov.cn/szsrmzf/xhtml/hd/assets/main.js",
            "https://www.suzhou.gov.cn/szsrmzf/hd_gzjd/gzjd.shtml",
            "https://www.suzhou.gov.cn/szsrmzf/hd_xjly/xjly.shtml"])
        dig(c, f, "无锡 互动/信箱", [
            "https://www.wuxi.gov.cn/fzlm/hdjlgny/lxblgny/wyxx/index.shtml",
            "https://www.wuxi.gov.cn/fzlm/hdjlgny/ftzb/ftzblmsy/index.shtml",
            "https://www.wuxi.gov.cn/hdjl/index.shtml"])
        dig(c, f, "南通 市长信箱页", [
            "https://www.nantong.gov.cn/ntsrmzf/sgkxj/sgkxj.html",
            "https://www.nantong.gov.cn/ntsrmzf/bumxx/bumxx.html"])
        dig(c, f, "连云港 TrueCMS", [
            "https://www.lyg.gov.cn/zglygzfmhwz/gzcy/gzcy.html",
            "http://12345.lyg.gov.cn/"])
        dig(c, f, "南京 门户", [
            "https://www.nanjing.gov.cn/",
            "http://www.nanjing.gov.cn/",
            "https://www.nanjing.gov.cn/hdjl/",
            "http://www.nanjing.gov.cn/hdjl/"])
        dig(c, f, "淮安 门户", [
            "https://www.huaian.gov.cn/",
            "https://www.huaian.gov.cn/col/16655_185673/index.html"])
    print("written", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
