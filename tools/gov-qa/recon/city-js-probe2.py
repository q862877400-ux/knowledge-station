"""江苏地市「政民互动」二级页指纹侦察（stage2）。

抓各市互动栏目页 → 抓其中的 .js → grep 中间件指纹（jpaas-jact / jact / IGI / hanweb /
龙讯 label / 静态列表），并打印互动页里的候选明细/列表链接。
用法：python recon/city-js-probe2.py
输出：recon/city-js-probe2.txt + recon/city-js-<abbr>-hd.html
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

# (城市, abbr, 互动页 URL, 参考 host)
PAGES = [
    ("无锡", "wuxi", "https://www.wuxi.gov.cn/hdjl/index.shtml"),
    ("徐州", "xuzhou", "https://www.xz.gov.cn/004/interactive.html"),
    ("常州", "changzhou", "https://www.changzhou.gov.cn/gova/letter"),
    ("苏州", "suzhou", "https://www.suzhou.gov.cn/szsrmzf/zmhd/zmhd.shtml"),
    ("南通", "nantong", "https://www.nantong.gov.cn/ntsrmzf/sgkxj/sgkxj.html"),
    ("连云港", "lianyungang", "https://www.lyg.gov.cn/zglygzfmhwz/gzcy/gzcy.html"),
    ("扬州", "yangzhou", "https://www.yangzhou.gov.cn/hdjl/index.html"),
    ("镇江", "zhenjiang", "https://www.zhenjiang.gov.cn/zhenjiang/12345zx/xjgs_list.shtml"),
    ("宿迁", "suqian", "https://www.suqian.gov.cn/cnsq/hdjl/hdjl.shtml"),
    ("南京", "nanjing", "https://www.nanjing.gov.cn/"),
    ("淮安", "huaian", "https://www.huaian.gov.cn/"),
    ("盐城", "yancheng", "https://www.yancheng.gov.cn/"),
]

FP = ("jpaas-jact", "jact", "/IGI/", "openGovmsgbox", "label/8888", "hanweb",
      "mail-pub", "mailpub", "sysid", "siteId", "platformUid", "platformIid",
      "xjgs", "zmhd", "12345", "find-mail")
OUT = HERE / "city-js-probe2.txt"


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
                w(f"  {url} → {type(e).__name__}: {str(e)[:90]}")
                continue
            w(f"  → {r.status_code} ({len(r.text)} bytes)")
            if r.status_code != 200:
                continue
            (HERE / f"city-js-{abbr}-hd.html").write_text(r.text, encoding="utf-8")
            html = r.text
            # 指纹命中
            hits = [k for k in FP if k.lower() in html.lower()]
            w(f"  指纹命中: {hits}")
            # 候选链接（含互动/信件/详情关键词）
            for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                                 html, re.I | re.S):
                href, txt = m.group(1), re.sub(r"<[^>]+>", "", m.group(2)).strip()
                if any(k in txt for k in ("信箱", "留言", "选登", "公开", "12345",
                                          "详情", "更多", "查询", "诉求", "热点")):
                    w(f"      [{txt[:30]}] {urljoin(str(r.url), href)}")
            # 抓同域 JS 里的接口串
            js_seen = set()
            for m in re.finditer(r'src=["\']([^"\']+\.js[^"\']*)["\']', html, re.I):
                js = urljoin(str(r.url), m.group(1))
                if js in js_seen:
                    continue
                js_seen.add(js)
                if len(js_seen) > 8:
                    break
                try:
                    jr = c.get(js)
                    if jr.status_code == 200:
                        for pat in (r"[\w./-]*(?:jpaas-jact|jact|openGovmsgbox|label/8888|"
                                    r"mail-?pub|mailpub)[\w./?=&-]*"):
                            for mm in re.finditer(pat, jr.text, re.I):
                                s = mm.group(0)
                                if len(s) > 8:
                                    w(f"      JS接口 {js.split('/')[-1][:24]}: {s[:110]}")
                        time.sleep(0.6)
                except Exception:                                           # noqa: BLE001
                    pass
            time.sleep(1.0)
    print("written", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
