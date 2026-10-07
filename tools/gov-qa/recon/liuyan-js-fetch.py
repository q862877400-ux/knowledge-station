"""人民网领导留言板 · JS 包下载与签名算法挖掘。

已知（2026-10-09 浏览器实捕）：
  POST https://liuyan.people.com.cn/v1/threads/list/bw
  body = {"appCode":"PC42ce3bfa4980a9","token":"…","signature":"<32hex>",
          "param":"{\\"fid\\":\\"5062\\",\\"showUnAnswer\\":1,\\"typeId\\":5,
                    \\"lastItem\\":\\"\\",\\"position\\":1,\\"rows\\":10,\\"orderType\\":2}"}
  · 空签名被拒（SN0001"appCode为空或者签名信息为空"）⇒ 签名必验。
本脚本：下载全部 JS 包到 recon/liuyan-js/，找 signature 的生成处与算法。
"""
from __future__ import annotations

import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
JS_DIR = HERE / "liuyan-js"

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")

LIST_URL = "https://liuyan.people.com.cn/threads/list?fid=5062"
SRC_RE = re.compile(r'script[^>]+src=["\']([^"\']+\.js)["\']')


def main() -> int:
    import httpx

    JS_DIR.mkdir(exist_ok=True)
    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=30, follow_redirects=True) as c:
        r = c.get(LIST_URL)
        srcs = re.findall(SRC_RE, r.text)
        print(f"index scripts: {len(srcs)}")
        for s in srcs:
            url = s if s.startswith("http") else "https://liuyan.people.com.cn" + s
            rr = c.get(url)
            name = url.rsplit("/", 1)[-1]
            (JS_DIR / name).write_bytes(rr.content)
            text = rr.text
            hits = []
            for kw in ("signature", "appCode", "md5", "MD5"):
                n = text.count(kw)
                if n:
                    hits.append(f"{kw}x{n}")
            print(f"  {'HIT ' if hits else '    '}{name} {len(rr.content)}B  {hits}")
    return 0


if __name__ == "__main__":
    main()
