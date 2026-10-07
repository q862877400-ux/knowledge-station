"""抓广东省政府厅局名录页（/zwgk/szfjg/）的完整子域清单。

产出：recon/gd-dept-domains-full.json（名称+域名全量），下一步逐个探 hdjlpt。
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")

sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import UA  # noqa: E402

DIR_PAGES = [
    "https://www.gd.gov.cn/zwgk/szfjg/index.html",
    "http://www.gd.gov.cn/yw/szfjg/index.html",
]
A_HREF_RE = re.compile(r'<a[^>]+href="(https?://[a-z0-9\-]+\.gd\.gov\.cn[^"]*)"[^>]*>(.*?)</a>', re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")


def main() -> int:
    import httpx

    found: dict[str, str] = {}
    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=15, follow_redirects=True) as c:
        for page in DIR_PAGES:
            try:
                r = c.get(page)
            except Exception as e:                                          # noqa: BLE001
                print(f"[dir] {page} {type(e).__name__}")
                continue
            t = r.text or ""
            for href, inner in A_HREF_RE.findall(t):
                name = TAG_RE.sub("", inner).strip()
                m = re.match(r"https?://([a-z0-9\-]+)\.gd\.gov\.cn", href, re.I)
                if not m:
                    continue
                dom = m.group(1)
                if dom in ("www", "app", "service", "statistics", "yjzj"):
                    continue
                if dom not in found and 2 <= len(name) <= 20:
                    found[dom] = name
            print(f"[dir] {page} → {r.status_code}, 累计 {len(found)}")
            time.sleep(1.5)

    out = [{"name": n, "dom": d} for d, n in sorted(found.items(), key=lambda x: x[1])]
    (HERE / "gd-dept-domains-full.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[gd] 全量域名 {len(out)} 个：")
    for r in out:
        print(f"  {r['name']:20s} {r['dom']}.gd.gov.cn")
    return 0


if __name__ == "__main__":
    main()
