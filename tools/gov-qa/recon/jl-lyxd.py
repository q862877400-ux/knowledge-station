"""找吉林厅「留言选登」的入口与列表形态（WAS5 通道也可达，两条路都查）。"""
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

BASE = "https://sthjt.jl.gov.cn"
PAGE = BASE + "/zmhd/"
OUT = HERE / "jl-lyxd.txt"
TAG_RE = re.compile(r"<[^>]+>")


def clean(h: str) -> str:
    h = re.sub(r"<script.*?</script>|<style.*?</style>", " ", h, flags=re.S | re.I)
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", h)).strip()


def main() -> int:
    import httpx

    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=20, follow_redirects=True) as c:
        r = c.get(PAGE)
        html = r.text or ""
        with OUT.open("w", encoding="utf-8") as f:
            f.write(f"zmhd [{r.status_code}] len={len(html)}\n")
            # 留言选登 附近的链接
            for m in list(re.finditer("留言选登", html))[:3]:
                a, b = max(0, m.start() - 600), min(len(html), m.end() + 600)
                f.write(f"\n--- 留言选登 上下文 ---\n{re.sub(chr(10),' ', html[a:b])}\n")
            f.write("\n--- 所有站内链接（含 lyxd/liuyan/zxly 关键词）---\n")
            for h in sorted(set(re.findall(r'href="([^"]+)"', html))):
                if any(k in h.lower() for k in ("lyxd", "liuyan", "zxly", "hdjl", "wszx", "mail")):
                    f.write(f"  {h}\n")
            f.write("\n正文片段：\n" + clean(html)[:1200] + "\n")
        # 试几个常见入口
        with OUT.open("a", encoding="utf-8") as f:
            for cand in ("/zmhd/lyxd/", "/zmhd/lyxd/index.shtml", "/zmhd/liuyan/",
                         "/zmhd/zxly/", "/zmhd/wszx/"):
                url = urljoin(BASE, cand)
                try:
                    rr = c.get(url)
                    f.write(f"\n试 {url} → [{rr.status_code}] len={len(rr.text or '')}\n")
                    if rr.status_code == 200 and len(rr.text or "") > 3000:
                        f.write("   正文：" + clean(rr.text)[:300] + "\n")
                except Exception as e:                                      # noqa: BLE001
                    f.write(f"\n试 {url} → {type(e).__name__}\n")
                time.sleep(1.5)
    print("written", OUT)
    return 0


if __name__ == "__main__":
    main()
