"""取吉林留言选登列表页与它的 ajax 脚本，找出数据接口。"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import UA  # noqa: E402

BASE = "https://sthjt.jl.gov.cn"
LIST = BASE + "/zmhd/tzxx/lyxd/"
JS = BASE + "/images/ajax_index_cmy_20211110.js"
OUT = HERE / "jl-lyxd-api.txt"
TAG_RE = re.compile(r"<[^>]+>")


def clean(h: str) -> str:
    h = re.sub(r"<script.*?</script>|<style.*?</style>", " ", h, flags=re.S | re.I)
    return re.sub(r"\s+", " ", TAG_RE.sub(" ", h)).strip()


def main() -> int:
    import httpx

    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=20, follow_redirects=True) as c:
        with OUT.open("w", encoding="utf-8") as f:
            r = c.get(LIST)
            f.write(f"列表 {LIST} [{r.status_code}] len={len(r.text or '')}\n")
            f.write("正文前 700：" + clean(r.text or "")[:700] + "\n")
            j = c.get(JS)
            f.write(f"\n脚本 {JS} [{j.status_code}] len={len(j.text or '')}\n")
            js = j.text or ""
            for kw in ("ajax", "url", "lyxd", "siteId", "appId", "page"):
                for m in list(re.finditer(kw, js, re.I))[:4]:
                    a, b = max(0, m.start() - 160), min(len(js), m.end() + 160)
                    f.write(f"\n--- js「{kw}」---\n{re.sub(chr(10),' ', js[a:b])}\n")
    print("written", OUT)
    return 0


if __name__ == "__main__":
    main()
