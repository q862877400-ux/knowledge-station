"""看四川省生态环境厅「回应关切」与「互动知识库」两个列表页的形态。

关心三件事：① 是否列表型（问题+答复成对）；② 分页方式（静态 index_N 还是接口）；
③ 有没有接口线索。
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

PAGES = [
    ("回应关切", "https://sthjt.sc.gov.cn/sthjt/c100447/list_w.shtml"),
    ("互动知识库", "https://sthjt.sc.gov.cn/sthjt/c250403/zmhdzsk_index.shtml"),
]
TAG_RE = re.compile(r"<[^>]+>")
A_HREF_RE = re.compile(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', re.I | re.S)
API_RE = re.compile(r"[\"']([^\"']{0,90}(?:/api/|/ajax/|\.json|list_w|createPageHTML|countPage)[^\"']{0,60})[\"']", re.I)


def main() -> int:
    import httpx

    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=20, follow_redirects=True) as c:
        for label, url in PAGES:
            r = c.get(url)
            html = r.text or ""
            print(f"\n=== {label} {url}\n    {r.status_code} len={len(html)}")
            items = []
            for href, inner in A_HREF_RE.findall(html):
                t = TAG_RE.sub("", inner).strip()
                if 6 <= len(t) <= 60 and not any(k in t for k in ("首页", "更多", "下一页", "上一页")):
                    items.append((t, href))
            print(f"    链接样本 {len(items)} 条：")
            for t, h in items[:8]:
                print(f"      · {t[:40]} -> {h[:80]}")
            print("    api/分页线索:", list(dict.fromkeys(API_RE.findall(html)))[:6])
            for kw in ("createPageHTML", "countPage", "pageSize", "total"):
                n = len(re.findall(kw, html, re.I))
                if n:
                    print(f"      {kw} x{n}")
    return 0


if __name__ == "__main__":
    main()
