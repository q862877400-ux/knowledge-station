"""安徽省生态环境厅 · public/column 型 CMS 列表页探测。

线索：recon/probe-provinces.json 里安徽的「政策解读咨询」链接是
/public/column/21691?type=4&catId=32710371&action=list —— 地址可直接拼，
若列表+翻页是常规形态，就是全省站群通用的第二类中间件（非 WAS5）。
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

URL = "https://sthjt.ah.gov.cn/public/column/21691?type=4&catId=32710371&action=list"


def main() -> int:
    import httpx

    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=20, follow_redirects=True) as c:
        r = c.get(URL)
    t = r.text
    print("status", r.status_code, "len", len(t))
    links = re.findall(r'href="([^"]+)"[^>]*>([^<]{6,60})<', t)
    qa = [(u, x) for u, x in links
          if any(k in x for k in ("咨询", "问答", "答复", "回复", "提问"))]
    print("QA-ish links:")
    for u, x in qa[:10]:
        print("  ", x.strip()[:40], "->", u[:110])
    for kw in ("ajax", "json", "createPageHTML", "countPage", "totalpage", "recordCount"):
        n = len(re.findall(kw, t, re.I))
        if n:
            print(f"{kw} x{n}")
    (HERE / "anhui-column.html").write_text(t, encoding="utf-8")
    return 0


if __name__ == "__main__":
    main()
