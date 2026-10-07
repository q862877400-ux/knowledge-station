"""部委问答扩采 · 住建部 + 市场监管总局：**先找到问答入口，再找列表接口**。

## 已知（实测，不要重新论证）
 · **住建部** `mohurd.gov.cn`：首页 200；`/hdjl/index.html` **404** ⇒ 问答入口在别处。
 · **市场监管总局** 公众留言站 `xgzlyhd.samr.gov.cn/gjjly/`：200 但只 7.9KB，
   引用 `arteryAjaxInterceptor.js` ⇒ **artery 框架**，列表由接口拉。

## 本脚本做什么（只读）
 ① 抓首页/站内，**抽出「互动 / 问答 / 咨询 / 留言 / 常见问题」类的链接**；
 ② 对市场监管总局那个站，把它引用的 **JS bundle 全抓下来**，从里面挖接口 URL
    （artery 框架的接口通常在 webjars 的 js 里，或页面模板里声明）。

**不批量抓取、不写任何东西。**

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\50-probe-mohurd-samr.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "probe-mohurd-samr.json"
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")

PAGES = [
    ("住建部首页", "https://www.mohurd.gov.cn/"),
    ("市场监管总局首页", "https://www.samr.gov.cn/"),
    ("市监公众留言站", "https://xgzlyhd.samr.gov.cn/gjjly/"),
]
WANT = re.compile(r"互动|问答|咨询|留言|常见问题|公众参与|交流|hdjl|zxtz|lyxd")
A_HREF = re.compile(r"""<a[^>]+href=["']([^"']+)["'][^>]*>(.{0,40}?)</a>""", re.S | re.I)
SRC = re.compile(r"""<script[^>]+src=["']([^"']+)["']""", re.I)
#: JS 里的接口形态（artery 常用 /xxx/query、/xxx/list、rest 风格）
API_IN_JS = re.compile(r"""["']((?:https?:)?/[A-Za-z0-9_\-./]{3,120}"""
                       r"""(?:query|list|page|search|data|ajax|get)[A-Za-z0-9_\-./]*)["']""")


def main() -> int:
    import httpx
    out = {"why": "找住建部与市监总局的问答入口与列表接口", "pages": []}
    with httpx.Client(timeout=25, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False) as cli:
        for label, u in PAGES:
            rec = {"label": label, "url": u}
            try:
                r = cli.get(u)
                t = r.text
                base = str(r.url)
                rec["status"] = r.status_code
                rec["len"] = len(t)
                links = []
                for href, text in A_HREF.findall(t):
                    txt = re.sub(r"<[^>]+>", "", text).strip()
                    if WANT.search(href) or WANT.search(txt):
                        links.append({"text": txt[:24], "href": href[:110]})
                rec["links"] = links[:14]
                rec["scripts"] = [s for s in SRC.findall(t)][:12]
                print(f"\n=== {label} {r.status_code} len={len(t)} ===", flush=True)
                for lk in rec["links"]:
                    print(f"    链接 [{lk['text']}] → {lk['href']}", flush=True)
                for s in rec["scripts"]:
                    print(f"    js   {s[:100]}", flush=True)
            except Exception as e:                                          # noqa: BLE001
                rec["error"] = f"{type(e).__name__}: {e}"
                print(f"\n=== {label} ⛔ {type(e).__name__}: {e}", flush=True)
            out["pages"].append(rec)
            time.sleep(1.5)

        # 对市监那个站：把它的 js 全抓下来挖接口
        js_recs = []
        for s in (out["pages"][2].get("scripts") or [])[:8]:
            url = s if s.startswith("http") else "https://xgzlyhd.samr.gov.cn" + ("" if s.startswith("/") else "/") + s
            try:
                rr = cli.get(url)
                if rr.status_code == 200:
                    apis = sorted(set(API_IN_JS.findall(rr.text)))
                    js_recs.append({"url": url, "len": len(rr.text), "apis": apis[:16]})
                    print(f"\n[js] {url}  len={len(rr.text)}  接口线索 {len(apis)}", flush=True)
                    for a in apis[:10]:
                        print(f"       api? {a[:100]}", flush=True)
            except Exception as e:                                          # noqa: BLE001
                print(f"\n[js] ⛔ {url} {type(e).__name__}", flush=True)
            time.sleep(1.2)
        out["samr_js"] = js_recs

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
