"""甘肃剩余市州侦察：天水 / 临夏（worker-gansu）。只读探测。"""
from __future__ import annotations

import os
import re
import sys

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")


def get(cli, tag, url, ref=None, n=600):
    h = {"Referer": ref} if ref else {}
    try:
        r = cli.get(url, headers=h)
    except Exception as e:                                                  # noqa: BLE001
        print(f"\n### {tag}\n  URL {url}\n  ERR {type(e).__name__}: {str(e)[:150]}")
        return None
    body = r.text or ""
    print(f"\n### {tag}\n  URL {url}\n  HTTP {r.status_code} len={len(body)} "
          f"ct={r.headers.get('content-type','')[:40]}")
    print("  " + re.sub(r"\s+", " ", body[:n]))
    return body


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    with httpx.Client(timeout=30, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False) as cli:
        if which in ("all", "tianshui"):
            get(cli, "TS home", "http://www.tianshui.gov.cn/")
            get(cli, "TS lybpl", "http://www.tianshui.gov.cn/zmhd/lybpl_comprehensive.jsp?wbtreeid=10192")
            get(cli, "TS zmhd", "http://www.tianshui.gov.cn/zmhd/")
        if which in ("all", "linxia"):
            get(cli, "LX home", "http://www.linxia.gov.cn/")
            get(cli, "LX xjxd", "http://www.linxia.gov.cn/lxz/zmhd/xjxd/")
            get(cli, "LX zzxjxd", "http://www.linxia.gov.cn/lxz/zmhd/zzxjxd/")


if __name__ == "__main__":
    main()
