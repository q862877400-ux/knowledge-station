"""调试四川知识库明细页：把清洗后文本的前后段落打出来，看解析标记到底长什么样。"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import UA  # noqa: E402

BASE = "https://sthjt.sc.gov.cn"
LIST = BASE + "/sthjt/c250403/zmhdzsk_index.shtml"
DETAIL_RE = re.compile(r'href="(/sthjt/c25040\d/\d{4}/\d{1,2}/\d{1,2}/[0-9a-f]{32}\.shtml)"')
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<script.*?</script>|<style.*?</style>", re.S | re.I)
OUT = HERE / "sc-detail-debug.txt"


def clean(html: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", SCRIPT_RE.sub(" ", html))).strip()


def main() -> int:
    import httpx

    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=20, follow_redirects=True) as c:
        r = c.get(LIST)
        links = sorted(set(DETAIL_RE.findall(r.text or "")))
        with OUT.open("w", encoding="utf-8") as f:
            f.write(f"列表 {r.status_code}，明细链接 {len(links)}\n")
            for href in links[:3]:
                d = c.get(BASE + href)
                t = clean(d.text or "")
                f.write(f"\n===== {href} ({d.status_code}, 长度 {len(t)}) =====\n")
                f.write("前 500：\n" + t[:500] + "\n")
                f.write("后 500：\n" + t[-500:] + "\n")
                for kw in ("解答内容", "解答", "答复", "问题", "发布时间", "来源"):
                    f.write(f"  含「{kw}」: {t.count(kw)} 次\n")
    print("written", OUT)
    return 0


if __name__ == "__main__":
    main()
