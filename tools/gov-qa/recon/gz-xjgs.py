"""探贵州厅「信件公示」（/hdjl/tzxx/xjgs/）：列表形态、是否含答复、翻页方式。"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import UA  # noqa: E402

PAGES = [
    ("贵州·信件公示", "https://sthj.guizhou.gov.cn/hdjl/tzxx/xjgs/"),
    ("贵州·互动交流", "https://sthj.guizhou.gov.cn/hdjl/"),
]
TAG_RE = re.compile(r"<[^>]+>")
OUT = HERE / "gz-xjgs.txt"


def clean(h: str) -> str:
    h = re.sub(r"<script.*?</script>|<style.*?</style>", " ", h, flags=re.S | re.I)
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", h)).strip()


def main() -> int:
    import httpx

    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=20, follow_redirects=True) as c:
        with OUT.open("w", encoding="utf-8") as f:
            for label, url in PAGES:
                r = c.get(url)
                html = r.text or ""
                f.write(f"\n=== {label} [{r.status_code}] len={len(html)} {url}\n")
                f.write("正文前 900：" + clean(html)[:900] + "\n")
                arts = sorted(set(re.findall(r'href="([^"]+\.(?:html|shtml|jsp)[^"]*)"', html)))[:12]
                f.write("候选链接：\n")
                for a in arts:
                    f.write(f"   {a}\n")
                for kw in ("createPageHTML", "pageIndex", "pageNo", "index_", "ajax", "json"):
                    if kw in html:
                        m = re.search(re.escape(kw) + r".{0,120}", html, re.S)
                        f.write(f"   [{kw}] {re.sub(chr(10),' ', m.group(0))[:140]}\n")
    print("written", OUT)
    return 0


if __name__ == "__main__":
    main()
