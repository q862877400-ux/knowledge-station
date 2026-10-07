"""看四川厅「领导信箱」与「回应关切」列表的规模与明细形态。"""
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
    ("领导信箱", "https://sthjt.sc.gov.cn/sthjt/c103053/newldxx.shtml"),
    ("回应关切", "https://sthjt.sc.gov.cn/sthjt/c100447/list_w.shtml"),
    ("知识库", "https://sthjt.sc.gov.cn/sthjt/c250403/zmhdzsk_index.shtml"),
]
TAG_RE = re.compile(r"<[^>]+>")


def main() -> int:
    import httpx

    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=20, follow_redirects=True) as c:
        for label, url in PAGES:
            r = c.get(url)
            html = r.text or ""
            # 明细链接（同栏目下的文章）
            det = sorted(set(re.findall(r'href="(/sthjt/c\d+/[^"]+\.shtml)"', html)))
            det = [d for d in det if not d.endswith(("index.shtml", "list_w.shtml", "index_1.shtml"))]
            print(f"\n=== {label} {r.status_code} len={len(html)} 明细链接 {len(det)}")
            for d in det[:5]:
                print("   ", d)
            # 分页
            pg = re.findall(r"createPageHTML\(\s*(\d+)", html)
            pg2 = re.findall(r"index_(\d+)\.shtml", html)
            print("    分页: createPageHTML", pg[:1], " index_N", sorted(set(pg2))[:5])
    return 0


if __name__ == "__main__":
    main()
