"""人民网领导留言板 · 签名算法挖掘（第二轮：全量 JS 引用，不只 <script src>）。

上一轮只抓了 <script src>，没找到业务逻辑（SPA 的 chunk 是运行时注入的）。
这一轮：把首页 HTML 原文里**一切**含 `.js` 的 URL（script/link/preload/内联字符串）
都抠出来下载，再在全部文件里搜 signature 的生成处。
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
#: 任何形态的 js 引用
URL_RE = re.compile(r'(?:https?:)?//[^"\'\s()<>]+?\.js(?:\?[^"\'\s()<>]*)?|/[\w\-./]+\.js(?:\?[^"\'\s()<>]*)?')
SKIP = ("appx", "tinymce", "aliyuncaptcha", "geolocation", "jweixin")


def main() -> int:
    import httpx

    JS_DIR.mkdir(exist_ok=True)
    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=30, follow_redirects=True) as c:
        c_nv = httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                            timeout=30, follow_redirects=True, verify=False)
        r = c.get(LIST_URL)
        urls = list(dict.fromkeys(URL_RE.findall(r.text)))
        # SPA 常见的运行时 chunk 也直接猜目录清单：从已抓到的 chunk 名推出前缀
        urls += [
            "https://liuyan.people.com.cn/pcjs/chunk-vendors.119899a02e4309955c60.js",
            "https://liuyan.people.com.cn/pcjs/chunk-2a793a25.f9ae1b9b5055a5f4d23e.js",
            "https://liuyan.people.com.cn/pcjs/chunk-27afe662.420e4546f71edfe5916d.js",
            "https://liuyan.people.com.cn/pcjs/chunk-f9276b72.d3f607df033bc447ada7.js",
        ]
        print(f"candidate js urls: {len(urls)}")
        results = []
        for u in urls:
            if any(k in u.lower() for k in SKIP):
                continue
            if not u.startswith("http"):
                u = "https://liuyan.people.com.cn" + u
            u = re.sub(r"(https://[^/]+?)\.(/)", r"\1\2", u)   # 尾部点归一化
            try:
                rr = c.get(u)
            except Exception:                                           # noqa: BLE001
                try:
                    rr = c_nv.get(u)
                except Exception as e:                                   # noqa: BLE001
                    print(f"  skip {u[-60:]} ({type(e).__name__})")
                    continue
            name = u.rsplit("/", 1)[-1].split("?")[0]
            (JS_DIR / name).write_bytes(rr.content)
            text = rr.text
            n_sig = len(re.findall(r"signature", text, re.I))
            n_code = len(re.findall(r"appCode", text, re.I))
            n_md5 = len(re.findall(r"\bmd5\b", text, re.I))
            results.append((name, len(rr.content), n_sig, n_code, n_md5))
            if n_sig or n_code or n_md5:
                print(f"  HIT {name} {len(rr.content)}B sig={n_sig} appCode={n_code} md5={n_md5}")
    print("done")
    return 0


if __name__ == "__main__":
    main()
