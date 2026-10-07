"""扫可达省份的厅局站是否也用 IGI 平台（指纹：openGovmsgbox / /IGI/ / listGovmsgboxs）。

命中即意味着可以**直接复用 `_igi_common.py` 基座**再加一省（且带县级归属）。
"""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import UA  # noqa: E402

SITES = [
    ("天津", "https://sthj.tj.gov.cn/"),
    ("上海", "https://sthj.sh.gov.cn/"),
    ("北京", "https://sthjj.beijing.gov.cn/"),
    ("浙江", "https://sthjt.zj.gov.cn/"),
    ("福建", "https://sthjt.fujian.gov.cn/"),
    ("宁夏", "https://sthjt.nx.gov.cn/"),
    ("云南", "https://sthjt.yn.gov.cn/"),
    ("陕西", "https://sthjt.shaanxi.gov.cn/"),
]
SUBPATHS = ["", "hdjl/", "zmhd/", "hdjl/tzxx/", "zmhd/tzxx/"]
FINGER = ("openGovmsgbox", "/IGI/", "listGovmsgboxs", "nbhd/")
OUT = HERE / "igi-spread-scan.txt"


def main() -> int:
    import httpx

    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=12, follow_redirects=True) as c:
        with OUT.open("w", encoding="utf-8") as f:
            for prov, site in SITES:
                for sub in SUBPATHS:
                    url = site + sub
                    try:
                        r = c.get(url)
                        html = r.text or ""
                        hits = {k: html.count(k) for k in FINGER if k in html}
                        if hits:
                            f.write(f"★ {prov} {url} [{r.status_code}] 指纹 {hits}\n")
                            for m in list(re.finditer(r"(siteId|appId|groupId)\s*[=:]\s*'?(\d+)",
                                                      html))[:6]:
                                f.write(f"      {m.group(0)}\n")
                        else:
                            f.write(f"  {prov} {url} [{r.status_code}] len={len(html)} 无指纹\n")
                    except Exception as e:                                  # noqa: BLE001
                        f.write(f"  {prov} {url} → {type(e).__name__}\n")
                    time.sleep(0.8)
    print("written", OUT)
    return 0


if __name__ == "__main__":
    main()
