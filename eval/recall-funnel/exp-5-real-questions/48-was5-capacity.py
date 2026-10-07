"""部委问答扩采 · 第 5 步：**摸清 WAS5 接口的容量与取数方式**。

上一步已证实 `https://www.mee.gov.cn/was5/web/search` 返回**结构化 JSON**
（字段：`doctitle` 提问 / `doccontent` 答复 / `lxrq` `hfrq` 日期 / `docpuburl` 原文 / `hfdw` 回复单位 / `recid`）。

本步只读，量四件事：
 ① 两个频道的 `recordCount`（留言选登 223015 / 常见问题 232534）各有多少条；
 ② `perpage` 能不能放大（10 → 50 → 100）；
 ③ `page` 翻页是否有效（第 2 页是不是不同内容）；
 ④ 响应里有没有别的可用字段（比如「依据文件名」——那决定它能不能当金标）。

⚠ 礼貌抓取：每次请求间隔 2 秒，总请求数很少。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\48-was5-capacity.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "was5-capacity.json"
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
URL = "https://www.mee.gov.cn/was5/web/search"
BASE = {"orderby": "-DOCRELTIME", "keyword": ""}

#: (标签, 附加参数)
TRIES = [
    ("留言选登 ch223015 p1 pp10", {"channelid": "223015", "page": "1", "perpage": "10"}),
    ("常见问题 ch232534 p1 pp10", {"channelid": "232534", "page": "1", "perpage": "10"}),
    ("留言选登 pp50", {"channelid": "223015", "page": "1", "perpage": "50"}),
    ("留言选登 pp100", {"channelid": "223015", "page": "1", "perpage": "100"}),
    ("留言选登 p2", {"channelid": "223015", "page": "2", "perpage": "10"}),
    ("常见问题 pp100", {"channelid": "232534", "page": "1", "perpage": "100"}),
]


def main() -> int:
    import httpx
    out = {"why": "摸清生态环境部 WAS5 接口的容量与取数方式", "tries": []}
    with httpx.Client(timeout=30, headers={"User-Agent": UA, "Referer": "https://www.mee.gov.cn/hdjl/"},
                      follow_redirects=True, trust_env=False) as cli:
        for label, extra in TRIES:
            p = {**BASE, **extra}
            rec = {"label": label, "params": p}
            try:
                r = cli.get(URL, params=p)
                rec["status"] = r.status_code
                try:
                    j = r.json()
                except Exception:                                           # noqa: BLE001
                    rec["raw_head"] = r.text[:300]
                    print(f"  {label:26s} HTTP {r.status_code} 非 JSON：{r.text[:90]}", flush=True)
                    out["tries"].append(rec)
                    time.sleep(2)
                    continue
                items = j.get("items") or []
                rec.update({"code": j.get("code"), "recordCount": j.get("recordCount"),
                            "pageSize": j.get("pageSize"), "currentPage": j.get("currentPage"),
                            "n_items": len(items),
                            "item_keys": sorted(items[0].keys()) if items else [],
                            "title_sample": (items[0].get("doctitle") or "")[:70] if items else ""})
                print(f"  {label:26s} recordCount={j.get('recordCount')!s:>6s} "
                      f"pageSize={j.get('pageSize')!s:>4s} 本页 {len(items)} 条  "
                      f"首条：{rec['title_sample']}", flush=True)
            except Exception as e:                                          # noqa: BLE001
                rec["error"] = f"{type(e).__name__}: {e}"
                print(f"  {label:26s} ⛔ {type(e).__name__}: {e}", flush=True)
            out["tries"].append(rec)
            time.sleep(2)

    keys = next((t["item_keys"] for t in out["tries"] if t.get("item_keys")), [])
    out["item_keys"] = keys
    print(f"\n[cap] 单条记录的字段 = {keys}")
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
