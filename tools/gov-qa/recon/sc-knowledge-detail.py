"""看四川知识库明细页结构与列表翻页方式（决定适配器写法）。"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")

sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import UA  # noqa: E402

DETAIL = "https://sthjt.sc.gov.cn/sthjt/c250404/2026/9/18/4c9cce44f3e54ad5a1da33c802c30e47.shtml"
LIST2 = "https://sthjt.sc.gov.cn/sthjt/c250403/zmhdzsk_index_1.shtml"
TAG_RE = re.compile(r"<[^>]+>")


def main() -> int:
    import httpx

    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=20, follow_redirects=True) as c:
        for label, url in (("明细", DETAIL), ("列表第2页", LIST2)):
            r = c.get(url)
            html = r.text or ""
            body = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S | re.I)
            text = re.sub(r"\s+", " ", TAG_RE.sub(" ", body)).strip()
            print(f"\n=== {label} {r.status_code} len={len(html)}")
            print("正文前 700 字：")
            print(text[:700])
            if label == "列表第2页":
                links = re.findall(r'href="(/sthjt/c2504\d\d/[^"]+\.shtml)"', html)
                print("明细链接数:", len(links), "样例:", links[:3])
                print("翻页线索:", re.findall(r"index_\d+\.shtml", html)[:6])
    return 0


if __name__ == "__main__":
    main()
