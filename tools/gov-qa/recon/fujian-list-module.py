"""福建 sthj_2020.min.js → requirejs paths → 'list' 模块定位。

已知：wyzx 页 `require(["jquery","add",'list',"dialog"], …)` 用 `Mode:'wasdoc'`
渲染 20325 条咨询（channelid=280067, classsql=dockind=3）。'list' 模块的
真实路径在 requirejs 配置里 —— 本脚本从 /images/sthj_2020.min.js 找 paths
配置，顺带找 wasdoc 渲染时的明细 URL 模板与 s 字段映射。
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")

sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import UA  # noqa: E402

BASE = "https://sthjt.fujian.gov.cn"
BUNDLE = f"{BASE}/images/sthj_2020.min.js"


def main() -> int:
    import httpx

    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=25, follow_redirects=True) as c:
        r = c.get(BUNDLE)
        t = r.text
        print(f"bundle {BUNDLE} → {r.status_code} / {len(t)}B")
        (HERE / "fujian-sthj2020.min.js").write_text(t, encoding="utf-8")

        # requirejs paths 配置
        for m in re.finditer(r"paths\s*:\s*\{(.{0,600}?)\}", t, re.S):
            seg = m.group(1)
            if "list" in seg or "wasdoc" in seg.lower():
                print("paths>", re.sub(r"\s+", " ", seg)[:500])

        # 'list' 模块名到 URL 的映射（各种写法）
        for m in re.finditer(r"[\"']list[\"']\s*:\s*[\"']([^\"']+)[\"']", t):
            print("list-module:", m.group(1))

        # wasdoc / was5 相关
        for m in list(re.finditer(r"wasdoc|was5?/web/[\w/]+", t))[:20]:
            a, b = max(0, m.start() - 120), min(len(t), m.end() + 200)
            print("---", m.group(0), "@", m.start())
            print(re.sub(r"\s+", " ", t[a:b])[:320])
    return 0


if __name__ == "__main__":
    main()
