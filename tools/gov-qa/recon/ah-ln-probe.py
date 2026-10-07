"""探安徽「问答知识库」与辽宁「咨询服务/历史咨询服务」两处的规模与结构。"""
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

PAGES = [
    ("安徽·问答知识库", "https://sthjt.ah.gov.cn/content/column/26703211"),
    ("安徽·互动交流", "https://sthjt.ah.gov.cn/zmhd/index.html"),
    ("辽宁·咨询服务", "https://sthj.ln.gov.cn/sthj/zmhd/zxly/index.shtml"),
    ("辽宁·历史咨询服务", "https://sthj.ln.gov.cn/sthj/zmhd/zxly/lszxfw/index.shtml"),
    ("辽宁·回应关切", "https://sthj.ln.gov.cn/sthj/zmhd/hygq/index.shtml"),
]
TAG_RE = re.compile(r"<[^>]+>")
OUT = HERE / "ah-ln-probe.txt"


def clean(h: str) -> str:
    h = re.sub(r"<script.*?</script>|<style.*?</style>", " ", h, flags=re.S | re.I)
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", h)).strip()


def main() -> int:
    import httpx

    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=20, follow_redirects=True) as c:
        with OUT.open("w", encoding="utf-8") as f:
            for label, url in PAGES:
                try:
                    r = c.get(url)
                except Exception as e:                                      # noqa: BLE001
                    f.write(f"\n=== {label} {url} → {type(e).__name__}\n")
                    continue
                html = r.text or ""
                arts = sorted(set(re.findall(
                    r'href="([^"]*(?:/content/article/|/content/column/|/zxly/|/lszxfw/)[^"]*)"',
                    html)))
                f.write(f"\n=== {label} [{r.status_code}] len={len(html)} "
                        f"文章链接 {len(arts)}\n")
                for a in arts[:10]:
                    f.write(f"   {a}\n")
                txt = clean(html)
                f.write("   正文片段: " + txt[200:700] + "\n")
    print("written", OUT)
    return 0


if __name__ == "__main__":
    main()
