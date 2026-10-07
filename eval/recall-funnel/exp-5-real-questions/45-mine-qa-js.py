"""部委问答扩采 · 第 2 步：抓 JS 文件，**挖出真正的接口 URL 并试调**。

## 上一轮的线索（已实测）
 · **生态环境部** `/hdjl/` 里有 `.ajaxCjwtList` / `.ajaxCjwtPage` / `.ajaxLyxdList`，
   并引用 `hjb251010_query.js` ⇒ 列表是 AJAX 拉的，**接口 URL 应该在那个 JS 里**。
 · **市场监管总局** `xgzlyhd.samr.gov.cn/gjjly/` 引用 `arteryAjaxInterceptor.js` ⇒ artery 框架。

本脚本只读：抓 JS → 从 JS 里抽 URL → **对抽到的 URL 只做 HEAD/GET 试探**（看是否返回 JSON）。
**不批量下载、不写任何东西。**

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\45-mine-qa-js.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "qa-js-mine.json"
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")

#: 要抓的 JS（上一步从 HTML 里抽到的）
JS_TARGETS = [
    "https://www.mee.gov.cn/images/hjb251010_query.js",
    "https://www.mee.gov.cn/hdjl/images/hjb251010_query.js",
    "https://www.mee.gov.cn/images/jquery-3.7.1.min.js",      # 对照：jQuery 里不该有业务接口
    "https://xgzlyhd.samr.gov.cn/gjjly/webjars/artery/static/arteryAjaxInterceptor.js",
]
#: JS 里的 URL 线索
URL_PAT = re.compile(r"""["'`]((?:https?:)?/[^"'`\s)]{4,200})["'`]""")
FUNC_PAT = re.compile(r"(ajax\w*|url\s*[:=]\s*[\"'][^\"']+[\"'])")


def main() -> int:
    import httpx
    out = {"why": "从 JS 里挖部委问答的接口 URL", "js": []}
    with httpx.Client(timeout=25, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False) as cli:
        for u in JS_TARGETS:
            rec = {"url": u}
            try:
                r = cli.get(u)
                rec["status"] = r.status_code
                rec["len"] = len(r.text)
                if r.status_code == 200:
                    urls = sorted(set(URL_PAT.findall(r.text)))
                    rec["urls"] = urls[:30]
                    rec["funcs"] = sorted(set(FUNC_PAT.findall(r.text)))[:20]
                    rec["head"] = r.text[:400]
                    print(f"\n=== {u}\n    {r.status_code} len={len(r.text)}"
                          f"  URL 线索 {len(urls)} 个 ===", flush=True)
                    for x in urls[:16]:
                        print(f"        {x[:120]}", flush=True)
                    for f in rec["funcs"][:8]:
                        print(f"        fn? {f[:100]}", flush=True)
                else:
                    print(f"\n=== {u}\n    ⛔ HTTP {r.status_code}", flush=True)
            except Exception as e:                                          # noqa: BLE001
                rec["error"] = f"{type(e).__name__}: {e}"
                print(f"\n=== {u}\n    ⛔ {type(e).__name__}: {e}", flush=True)
            out["js"].append(rec)
            time.sleep(1.2)

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
