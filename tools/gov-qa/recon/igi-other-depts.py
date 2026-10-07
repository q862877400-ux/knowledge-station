"""探吉林/贵州**其他厅局**是否也用 IGI 平台（若是，县级覆盖可成片扩）。

思路：IGI 是厂商产品，同一省的多个厅局站可能都挂了 `厅长信箱`。
对候选站点首页与常见信箱路径抓取，搜指纹 `/IGI/`、`openGovmsgbox`、`siteId`。
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
    ("贵州", "省应急管理厅", "https://yjt.guizhou.gov.cn/"),
    ("贵州", "省卫生健康委", "https://wjw.guizhou.gov.cn/"),
    ("贵州", "省市场监督管理局", "https://amr.guizhou.gov.cn/"),
    ("贵州", "省交通运输厅", "https://jt.guizhou.gov.cn/"),
    ("吉林", "省应急管理厅", "https://yjt.jl.gov.cn/"),
    ("吉林", "省卫生健康委", "https://wsjkw.jl.gov.cn/"),
    ("吉林", "省市场监督管理厅", "https://scjg.jl.gov.cn/"),
]
SUBS = ["", "hdjl/", "zmhd/", "hdjl/tzxx/xjgs/", "zmhd/tzxx/lyxd/", "zmhd/tzxx/"]
FINGER = ("/IGI/", "openGovmsgbox", "listGovmsgboxs")
OUT = HERE / "igi-other-depts.txt"


def main() -> int:
    import httpx

    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=12, follow_redirects=True) as c:
        with OUT.open("w", encoding="utf-8") as f:
            for prov, name, site in SITES:
                found = False
                for sub in SUBS:
                    url = site + sub
                    try:
                        r = c.get(url)
                        html = r.text or ""
                        hits = {k: html.count(k) for k in FINGER if k in html}
                        if hits:
                            found = True
                            f.write(f"★ {prov}{name} {url} [{r.status_code}] 指纹 {hits}\n")
                            for m in list(re.finditer(
                                    r"(siteId|appId|groupId)\s*[=:]\s*'?(\d+)", html))[:6]:
                                f.write(f"      {m.group(0)}\n")
                    except Exception as e:                                  # noqa: BLE001
                        if sub == "":
                            f.write(f"  {prov}{name} {url} → {type(e).__name__}\n")
                    time.sleep(0.6)
                if not found:
                    f.write(f"  {prov}{name} 无指纹（试过 {len(SUBS)} 个路径）\n")
    print("written", OUT)
    return 0


if __name__ == "__main__":
    main()
