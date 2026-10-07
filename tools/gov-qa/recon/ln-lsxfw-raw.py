"""看辽宁「历史咨询服务」列表页结构：条目链接/内联内容/翻页方式。"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import UA  # noqa: E402

URL = "https://sthj.ln.gov.cn/sthj/zmhd/zxly/lszxfw/index.shtml"
RAW = HERE / "ln-lsxfw-raw.html"
NOTES = HERE / "ln-lsxfw-notes.txt"
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
        RAW.write_text(html, encoding="utf-8")
        with NOTES.open("w", encoding="utf-8") as f:
            f.write(f"status={r.status_code} len={len(html)}\n")
            for kw in ("咨询回复", "社会生活噪音", "标题：", "内容：", "createPageHTML",
                       "page", ".shtml", "回复"):
                for m in list(re.finditer(re.escape(kw), html))[:2]:
                    a, b = max(0, m.start() - 350), min(len(html), m.end() + 350)
                    f.write(f"\n--- 「{kw}」 ---\n{re.sub(chr(10), ' ', html[a:b])}\n")
            f.write("\n--- 形如 xxx.shtml 的链接（前 20）---\n")
            for h in sorted(set(re.findall(r'href="([^"]+\.shtml)"', html)))[:20]:
                f.write(f"  {h}\n")
            f.write("\n清洗后正文（前 800）：\n" + clean(html)[:800] + "\n")
    print("written", NOTES)
    return 0


if __name__ == "__main__":
    main()
