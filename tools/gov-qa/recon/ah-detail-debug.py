"""看安徽问答知识库明细页结构（写解析器前必须先看真实标记）。"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import UA  # noqa: E402

URL = "https://sthjt.ah.gov.cn/zmhd/wdzsk/123166701.html"
OUT = HERE / "ah-detail-debug.txt"
TAG_RE = re.compile(r"<[^>]+>")


def clean(h: str) -> str:
    h = re.sub(r"<script.*?</script>|<style.*?</style>", " ", h, flags=re.S | re.I)
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", h)).strip()


def main() -> int:
    import httpx

    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=20, follow_redirects=True) as c:
        r = c.get(URL)
        html = r.text or ""
        t = clean(html)
        with OUT.open("w", encoding="utf-8") as f:
            f.write(f"status={r.status_code} len_html={len(html)} len_text={len(t)}\n\n")
            f.write("全文（前 1600 字）:\n" + t[:1600] + "\n\n")
            for kw in ("问题", "答复", "解答", "回复", "咨询", "来源", "时间"):
                f.write(f"含「{kw}」: {t.count(kw)}\n")
            f.write("\n--- 正文块候选（class 含 content/main/xiangqing 的 div）---\n")
            for m in re.finditer(r'<div[^>]*class="([^"]*(?:content|main|detail|article|xx)[^"]*)"[^>]*>',
                                 html, re.I):
                f.write(f"  {m.group(1)}\n")
    print("written", OUT)
    return 0


if __name__ == "__main__":
    main()
