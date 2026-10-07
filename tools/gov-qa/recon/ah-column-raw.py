"""看安徽问答知识库栏目的原始 HTML：条目链接写法与翻页方式（不猜，直接看源码）。"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import UA  # noqa: E402

URL = "https://sthjt.ah.gov.cn/content/column/26703211"
OUT = HERE / "ah-column-raw.html"
OUT2 = HERE / "ah-column-notes.txt"


def main() -> int:
    import httpx

    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=20, follow_redirects=True) as c:
        r = c.get(URL)
        html = r.text or ""
        OUT.write_text(html, encoding="utf-8")
        with OUT2.open("w", encoding="utf-8") as f:
            f.write(f"status={r.status_code} len={len(html)}\n\n")
            # 找第一个问题标题在源码里的上下文
            for kw in ("吸塑工艺", "废离子交换树脂", "分页", "problemList", "ajax",
                       "/content/article/"):
                for m in list(re.finditer(re.escape(kw), html))[:2]:
                    a, b = max(0, m.start() - 300), min(len(html), m.end() + 300)
                    f.write(f"--- 「{kw}」 上下文 ---\n{html[a:b]}\n\n")
            # 所有 script src 与内联 ajax url
            f.write("--- scripts ---\n")
            for s in re.findall(r'<script[^>]+src="([^"]+)"', html)[:20]:
                f.write(f"  {s}\n")
            f.write("--- ajax/url 线索 ---\n")
            for u in sorted(set(re.findall(r'url\s*:\s*["\']([^"\']+)["\']', html)))[:20]:
                f.write(f"  {u}\n")
    print("written", OUT2)
    return 0


if __name__ == "__main__":
    main()
