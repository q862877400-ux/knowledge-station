"""在 gd.gov.cn 首页里找「省政府部门/政府机构」名录页的真实地址，并抓全清单。"""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")

sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import UA  # noqa: E402


def main() -> int:
    import httpx

    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=15, follow_redirects=True) as c:
        r = c.get("https://www.gd.gov.cn/")
        t = r.text
        # 找锚文本含「部门/机构/单位名录」的链接
        for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>([^<]*(?:部门|机构|单位|组成)[^<]*)</a>', t):
            print("NAV>", m.group(2).strip()[:20], "->", m.group(1)[:100])
        # 也找 gd.gov.cn 下的目录页
        pages = sorted(set(re.findall(
            r'href="(/(?:zwgk|gdgov|zfjg|jgsz)[^"]*)"', t)))
        print("dir-like pages:", *pages[:15], sep="\n  ")
    return 0


if __name__ == "__main__":
    main()
