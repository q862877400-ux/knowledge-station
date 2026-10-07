"""部委问答扩采 · 侦察：找出三家的**真实数据接口**（它们的列表页是 JS/接口驱动的）。

## 背景（已实测，不要重新论证）
 · **应急管理部**：静态列表，已跑通（10 页 / 66 条）✅
 · **生态环境部** `mee.gov.cn/hdjl/`：httpx 200、76KB，但**抽不到明细页链接** ⇒ 列表是 JS/接口驱动
 · **住建部**：`/hdjl/` 404，但首页可达（curl_cffi 也通）
 · **市场监管总局** `xgzlyhd.samr.gov.cn/gjjly/`：200 但只有 7.9KB ⇒ 典型 JS 应用
 · 卫健委 / 国家消防救援局：直连 **412**（需真浏览器或找接口）

本脚本**只读**：把每个站点的 HTML/JS 抓下来，从里面**找出接口 URL**（ajax/json/api/action 等），
并试着直接调它。**不下载数据集、不写任何东西。**

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-5-real-questions\\44-probe-qa-apis.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "qa-api-probe.json"
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")

TARGETS = {
    "生态环境部": ["https://www.mee.gov.cn/hdjl/",
                   "https://www.mee.gov.cn/hdjl/cjwt/",
                   "https://www.mee.gov.cn/hdjl/zxly/"],
    "住房和城乡建设部": ["https://www.mohurd.gov.cn/",
                         "https://www.mohurd.gov.cn/hdjl/index.html"],
    "国家市场监督管理总局": ["https://xgzlyhd.samr.gov.cn/gjjly/",
                             "https://www.samr.gov.cn/hd/"],
}

#: 从 HTML/JS 里挖接口线索
URL_PAT = re.compile(r"""["'`]([^"'`\s]{4,200}?(?:ajax|json|api|action|query|list|search|page)"""
                      r"""[^"'`\s]{0,120}?)["'`]""", re.I)
SCRIPT_SRC = re.compile(r"""<script[^>]+src=["']([^"']+)["']""", re.I)


def main() -> int:
    import httpx
    out = {"why": "扩采部委问答前，找出三家真实数据接口（列表页是 JS/接口驱动）", "sites": {}}
    with httpx.Client(timeout=25, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False) as cli:
        for name, urls in TARGETS.items():
            rows = []
            for u in urls:
                rec = {"url": u}
                try:
                    r = cli.get(u)
                    t = r.text
                    rec["status"] = r.status_code
                    rec["len"] = len(t)
                    rec["apis"] = sorted(set(URL_PAT.findall(t)))[:14]
                    rec["scripts"] = [s for s in SCRIPT_SRC.findall(t)][:8]
                    # 页面里有没有 "共N页/共N条" 这类分页线索（说明是接口驱动）
                    rec["pager_hint"] = bool(re.search(r"共\s*\d+\s*[页条]|totalCount|pageCount", t, re.I))
                    print(f"[{name}] {r.status_code} len={len(t):7d} "
                          f"接口线索 {len(rec['apis'])} 个 脚本 {len(rec['scripts'])} 个 {u}", flush=True)
                    for a in rec["apis"][:8]:
                        print(f"        api? {a[:110]}", flush=True)
                except Exception as e:                                          # noqa: BLE001
                    rec["error"] = f"{type(e).__name__}: {e}"
                    print(f"[{name}] ⛔ {type(e).__name__} {u}", flush=True)
                rows.append(rec)
                time.sleep(1.5)
            out["sites"][name] = rows

    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
