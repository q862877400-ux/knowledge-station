"""jact 站 sysid 枚举器（地市通用）。

对给定 host 扫 sysid=1..N，调 `dataproxy_mailpublist.do` 读 totalRecord，
打印命中（totalRecord>0）的 sysid。用于避开「猜单个 sysid=空 ⇒ 误判无问答」。
用法：python recon/city-js-jact-scan.py <scheme> <host> [n_max]
"""
from __future__ import annotations

import os
import re
import sys
import time

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
TOTAL_RE = re.compile(r"totalRecord\s*=\s*([0-9.]+)")


def main() -> int:
    scheme = sys.argv[1] if len(sys.argv) > 1 else "https"
    host = sys.argv[2] if len(sys.argv) > 2 else "www.yancheng.gov.cn"
    n_max = int(sys.argv[3]) if len(sys.argv) > 3 else 300
    import httpx
    base = f"{scheme}://{host}"
    hits = []
    with httpx.Client(headers={"User-Agent": UA}, trust_env=False, timeout=15,
                      follow_redirects=True) as c:
        for sid in range(1, n_max + 1):
            url = (f"{base}/jact/front/dataproxy_mailpublist.do"
                   f"?startrecord=1&endrecord=19&perpage=19&groupSize=3&sysid={sid}")
            try:
                r = c.get(url, headers={"Referer": f"{base}/jact/front/main.do?sysid={sid}"})
                m = TOTAL_RE.search(r.text or "")
                tot = int(float(m.group(1))) if m else -1
            except Exception as e:                                          # noqa: BLE001
                tot = -2
                print(f"  sysid={sid} ERR {type(e).__name__}")
            if tot > 0:
                hits.append((sid, tot))
                print(f"  ★ sysid={sid} totalRecord={tot}")
            if sid % 25 == 0:
                print(f"  ...scanned {sid}")
            time.sleep(0.35)
    print(f"\n[{host}] 命中 {len(hits)} 个 sysid：")
    for sid, tot in hits:
        print(f"  sysid={sid}  totalRecord={tot}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
