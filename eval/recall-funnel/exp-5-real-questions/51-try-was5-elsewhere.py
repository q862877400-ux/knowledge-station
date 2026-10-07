"""部委问答扩采 · 第 7 步：**拿 WAS5 这个模式去各部委试**（快路子）。

## 为什么值得试
生态环境部的问答是 `https://www.mee.gov.cn/was5/web/search?channelid=...` ——
**WAS5 是政府站常见的检索中间件**。若其它部委也用同一套，扩采就是"换域名 + 换频道号"的事，
不必逐个写 JS 适配器。

## 做法（只读、礼貌）
对每个候选站点试 `GET /was5/web/search`（带一个空的通用参数），看：
 · HTTP 状态；② 响应是不是 JSON（含 `recordCount`/`items`）；③ 若 200 但不是 JSON，记下形态。
**每个域名只试 1～2 次，间隔 2 秒。**

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\51-try-was5-elsewhere.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "was5-elsewhere.json"
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")

SITES = [
    ("住房和城乡建设部", "https://www.mohurd.gov.cn"),
    ("国家市场监督管理总局", "https://www.samr.gov.cn"),
    ("国家卫生健康委员会", "http://www.nhc.gov.cn"),
    ("应急管理部", "https://www.mem.gov.cn"),
    ("人力资源和社会保障部", "http://www.mohrss.gov.cn"),
    ("生态环境部(对照)", "https://www.mee.gov.cn"),
]


def main() -> int:
    import httpx
    out = {"why": "拿 WAS5 模式去各部委试，看能否复用同一套取数方式", "sites": []}
    with httpx.Client(timeout=20, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False) as cli:
        for name, base in SITES:
            for path in ("/was5/web/search", "/was5/web/search/"):
                rec = {"name": name, "url": base + path}
                try:
                    r = cli.get(base + path)
                    rec["status"] = r.status_code
                    rec["len"] = len(r.text)
                    rec["ctype"] = r.headers.get("content-type", "")
                    is_json = False
                    try:
                        j = r.json()
                        is_json = isinstance(j, dict)
                        rec["json_keys"] = sorted(j.keys())[:8] if is_json else None
                        rec["recordCount"] = j.get("recordCount") if is_json else None
                    except Exception:                                       # noqa: BLE001
                        pass
                    rec["is_json"] = is_json
                    rec["head"] = r.text[:120]
                    tag = "★ JSON" if is_json else ("非 JSON" if r.status_code == 200 else "")
                    print(f"  {name:22s} {r.status_code} len={len(r.text):7d} {tag} "
                          f"{rec.get('recordCount') or ''} {path}", flush=True)
                    if is_json:
                        out["sites"].append(rec)
                        break
                except Exception as e:                                      # noqa: BLE001
                    print(f"  {name:22s} ⛔ {type(e).__name__} {path}", flush=True)
                out["sites"].append(rec)
                time.sleep(2)

    hits = [s for s in out["sites"] if s.get("is_json")]
    print(f"\n[w] 命中 WAS5 JSON 的站点 = {len(hits)}")
    for h in hits:
        print(f"    ★ {h['name']}  recordCount={h.get('recordCount')}")
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
