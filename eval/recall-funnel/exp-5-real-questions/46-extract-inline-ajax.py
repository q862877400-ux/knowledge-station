"""部委问答扩采 · 第 3 步：**把页面内联 JS 里那段 AJAX 定义挖出来**。

## 为什么改这一招
上一步抓的是外链 JS（`hjb251010_query.js` 那个路径被重定向成了页面本身，拿到的不是 JS）。
而 `.ajaxCjwtList` 这些字样**是在 `/hdjl/` 的 HTML 里**出现的 ⇒ 接口定义**内联在页面里**。

本脚本只读：抓页面 → 定位包含 `ajaxCjwtList` / `ajaxList` 的 `<script>` 段 → 打印出来 + 抽 `url:`。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\46-extract-inline-ajax.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "inline-ajax.json"
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")

PAGES = [
    ("生态环境部/互动交流", "https://www.mee.gov.cn/hdjl/"),
    ("生态环境部/常见问题", "https://www.mee.gov.cn/hdjl/cjwt/"),
    ("市场监管总局/公众留言", "https://xgzlyhd.samr.gov.cn/gjjly/"),
    ("市场监管总局/互动", "https://www.samr.gov.cn/hd/"),
]
#: 找 `<script>...</script>` 段
SCRIPT_BLOCK = re.compile(r"<script[^>]*>(.*?)</script>", re.S | re.I)
#: 段里要有的关键词（说明这段是列表加载逻辑）
KEY = re.compile(r"ajax\w*List|ajax\w*Page|currentPage|countPage|\$\.get|\$\.post|fetch\(")
#: 段里的 url 线索
URL_IN_JS = re.compile(r"""url\s*[:=]\s*["']([^"']+)["']|["']((?:https?:)?/[A-Za-z0-9_\-./?=&%]{3,150})["']""")


def main() -> int:
    import httpx
    out = {"why": "从部委页面内联 JS 里挖列表接口", "pages": []}
    with httpx.Client(timeout=25, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False) as cli:
        for label, u in PAGES:
            rec = {"label": label, "url": u, "blocks": []}
            try:
                r = cli.get(u)
                t = r.text
                rec["status"] = r.status_code
                rec["len"] = len(t)
                print(f"\n=== {label}  {r.status_code} len={len(t)} ===", flush=True)
                for m in SCRIPT_BLOCK.finditer(t):
                    body = m.group(1)
                    if not KEY.search(body) or len(body) < 60:
                        continue
                    urls = []
                    for a, b in URL_IN_JS.findall(body):
                        v = (a or b).strip()
                        if v and not v.endswith((".js", ".css", ".png", ".jpg", ".gif")):
                            urls.append(v)
                    rec["blocks"].append({"len": len(body), "urls": sorted(set(urls))[:12],
                                          "head": body.strip()[:700]})
                    if len(rec["blocks"]) >= 3:
                        break
                print(f"    命中内联段 {len(rec['blocks'])} 个", flush=True)
                for b in rec["blocks"]:
                    print(f"      -- 段（{b['len']} 字）URL 线索：{b['urls']}", flush=True)
                    print("         " + b["head"][:400].replace("\n", " "), flush=True)
            except Exception as e:                                          # noqa: BLE001
                rec["error"] = f"{type(e).__name__}: {e}"
                print(f"    ⛔ {type(e).__name__}: {e}", flush=True)
            out["pages"].append(rec)
            time.sleep(1.5)

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
