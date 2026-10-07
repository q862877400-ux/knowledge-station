"""部委问答扩采 · 第 4 步：**试调 WAS5 接口**（生态环境部）。

## 线索（上一步从页面内联 JS 挖到）
```
接口： /was5/web/search
留言选登： channelid=223015, orderby=-DOCRELTIME, perpage=10, page=N
常见问题： channelid=232534, 同上
```
若它能返回结构化数据，生态环境部的问答就能**成规模**取，不必逐页爬静态列表。

本脚本只读：**只试调 2～3 次**（礼貌），打印状态、内容类型与响应前 1200 字。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\47-try-was5.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "was5-try.json"
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")

#: (标签, URL, 参数)——`was5/web/search` 常见两种调用风格，都试
TRIES = [
    ("GET 查询串", "https://www.mee.gov.cn/was5/web/search",
     {"channelid": "223015", "keyword": "", "orderby": "-DOCRELTIME", "perpage": "10", "page": "1"}),
    ("GET 带上游页", "https://www.mee.gov.cn/was5/web/search",
     {"channelid": "223015", "searchword": "", "orderby": "-DOCRELTIME",
      "perpage": "10", "page": "1", "outlinepage": "10"}),
]


def main() -> int:
    import httpx
    out = {"why": "试调生态环境部的 WAS5 接口，看能否成规模取问答", "tries": []}
    with httpx.Client(timeout=30, headers={"User-Agent": UA, "Referer": "https://www.mee.gov.cn/hdjl/"},
                      follow_redirects=True, trust_env=False) as cli:
        for label, url, params in TRIES:
            rec = {"label": label, "url": url, "params": params}
            try:
                r = cli.get(url, params=params)
                rec["status"] = r.status_code
                rec["ctype"] = r.headers.get("content-type", "")
                rec["len"] = len(r.text)
                rec["head"] = r.text[:1200]
                print(f"\n=== {label} → HTTP {r.status_code}  {rec['ctype']}  {rec['len']} 字节 ===",
                      flush=True)
                print(rec["head"][:900].replace("\n", " "), flush=True)
            except Exception as e:                                          # noqa: BLE001
                rec["error"] = f"{type(e).__name__}: {e}"
                print(f"\n=== {label} ⛔ {type(e).__name__}: {e}", flush=True)
            out["tries"].append(rec)
            time.sleep(2)

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
