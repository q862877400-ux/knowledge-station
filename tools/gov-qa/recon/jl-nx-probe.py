"""探吉林与宁夏两家厅局站的互动栏目可用性。

吉林：`sthjt.jl.gov.cn/zmhd/` + WAS5 通道线索（`125.32.96.149:8081/was5/web/search?channelid=226700`）
宁夏：`sthjt.nx.gov.cn/yqhy/hdzx/`（互动咨询）+ 厅长信箱挂在 `app.12345.nx.gov.cn` 平台
只做可达性与列表形态判断，不做全量抓取。
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

TARGETS = [
    ("吉林·政民互动", "https://sthjt.jl.gov.cn/zmhd/"),
    ("吉林·WAS5通道", "http://125.32.96.149:8081/was5/web/search?channelid=226700"),
    ("宁夏·互动咨询", "https://sthjt.nx.gov.cn/yqhy/hdzx/"),
    ("宁夏·厅长信箱(12345)", "https://app.12345.nx.gov.cn/cns-bmfw-webrest/pages/Leader/service_openlist?emailFlag=7&deptGuid=46166aa4-792c-4f05-a315-abd04c14f4ff"),
]
TAG_RE = re.compile(r"<[^>]+>")
OUT = HERE / "jl-nx-probe.txt"


def clean(h: str) -> str:
    h = re.sub(r"<script.*?</script>|<style.*?</style>", " ", h, flags=re.S | re.I)
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", h)).strip()


def main() -> int:
    import httpx

    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=15, follow_redirects=True) as c:
        with OUT.open("w", encoding="utf-8") as f:
            for label, url in TARGETS:
                try:
                    r = c.get(url)
                    html = r.text or ""
                    f.write(f"\n=== {label} [{r.status_code}] len={len(html)} {url}\n")
                    f.write("正文前 500：" + clean(html)[:500] + "\n")
                    arts = sorted(set(re.findall(r'href="([^"]*(?:detail|article|content|zxly|hdzx)[^"]*)"',
                                                 html, re.I)))[:8]
                    f.write("候选明细链接：\n")
                    for a in arts:
                        f.write(f"   {a}\n")
                except Exception as e:                                      # noqa: BLE001
                    f.write(f"\n=== {label} → {type(e).__name__} {url}\n")
                time.sleep(2)
    print("written", OUT)
    return 0


if __name__ == "__main__":
    main()
