"""探其他省是否也部署了吉林同款「海云/信箱开放接口」平台。

两条证据线：
 ① 直接试 `https://haiyun.<省缩写>.gov.cn/IGI/`（吉林实测存在）；
 ② 到各省厅局首页/互动页里搜平台指纹（`nbhd` / `openGovmsgbox` / `haiyun` / `contextPath`）。
任一命中即可按吉林适配器模式扩展（**能带县级归属**）。
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

HAIYUN_HOSTS = [("黑龙江", "hlj"), ("辽宁", "ln"), ("内蒙古", "nmg"), ("河北", "hebei"),
                ("山东", "sd"), ("安徽", "ah"), ("湖北", "hb"), ("湖南", "hn"),
                ("江西", "jx"), ("陕西", "sn")]
DEPT_SITES = [("辽宁", "https://sthj.ln.gov.cn/"),
              ("黑龙江", "https://sthjt.hlj.gov.cn/"),
              ("贵州", "https://sthj.guizhou.gov.cn/"),
              ("天津", "https://sthj.tj.gov.cn/"),
              ("河北", "https://hbepb.hebei.gov.cn/")]
FINGERPRINTS = ("nbhd", "openGovmsgbox", "haiyun", "contextPath", "listGovmsgboxs")
OUT = HERE / "haiyun-spread-probe.txt"


def main() -> int:
    import httpx

    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=12, follow_redirects=True) as c:
        with OUT.open("w", encoding="utf-8") as f:
            f.write("== ① 试 haiyun 主机 ==\n")
            for prov, abbr in HAIYUN_HOSTS:
                for host in (f"https://haiyun.{abbr}.gov.cn/IGI/",
                             f"https://haiyun.{abbr}.gov.cn/"):
                    try:
                        r = c.get(host)
                        f.write(f"  {prov} {host} → [{r.status_code}] len={len(r.text or '')}\n")
                    except Exception as e:                                  # noqa: BLE001
                        f.write(f"  {prov} {host} → {type(e).__name__}\n")
                    time.sleep(0.8)
            f.write("\n== ② 厅局站内搜平台指纹 ==\n")
            for prov, site in DEPT_SITES:
                try:
                    r = c.get(site)
                    html = r.text or ""
                    hits = {k: html.count(k) for k in FINGERPRINTS if html.count(k)}
                    f.write(f"  {prov} {site} [{r.status_code}] len={len(html)} 指纹: {hits}\n")
                    # 找互动/信箱相关链接
                    links = sorted(set(re.findall(
                        r'href="([^"]*(?:zmhd|hdjl|tzxx|lyxd|xxzx|mailbox)[^"]*)"', html, re.I)))[:5]
                    for l in links:
                        f.write(f"      {l}\n")
                except Exception as e:                                      # noqa: BLE001
                    f.write(f"  {prov} {site} → {type(e).__name__}\n")
                time.sleep(1.2)
    print("written", OUT)
    return 0


if __name__ == "__main__":
    main()
