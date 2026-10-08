"""河北 阶段五：深挖 沧州互动平台 / 省市场监管留言 / 省财政厅互动。"""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx  # noqa: E402

HERE = Path(__file__).resolve().parent
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
PAUSE = 1.5

TARGETS = [
    ("heb-scjg-leave", "http://scjg.hebei.gov.cn/look_leave_word.html"),
    ("heb-scjg-node993", "http://scjg.hebei.gov.cn/node/993"),
    ("heb-czt-hdjl", "http://czt.hebei.gov.cn/hdjl/"),
    ("heb-cz-rs-subzmhd", "http://rs.cangzhou.gov.cn/rs/c100293/subzmhd.shtml"),
    ("heb-cz-main", "http://www.cangzhou.gov.cn/cangzhou/c100035/zmhd.shtml"),
]


def main() -> int:
    with httpx.Client(timeout=30, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False) as cli:
        for name, url in TARGETS:
            try:
                r = cli.get(url)
            except Exception as e:  # noqa: BLE001
                print(f"[{name}] {url} -> {type(e).__name__}: {e}")
                continue
            body = r.text or ""
            (HERE / f"{name}.html").write_text(body, encoding="utf-8", errors="replace")
            print(f"[{name}] {url} -> {r.status_code} {len(body)}B")
            if r.status_code == 200:
                scripts = re.findall(r'<script[^>]+src="([^"]+)"', body)
                for s in scripts[:12]:
                    print(f"    SCRIPT {s}")
                for kw in ("留言", "咨询", "选登", "答复", "回复", "问", "答"):
                    if kw in body:
                        print(f"    KW {kw}: {body.count(kw)}")
                items = re.findall(r'<a [^>]*href="([^"]+\.(?:shtml|html|jhtml))"[^>]*>([^<]{6,60})</a>', body)
                for u, t in items[:10]:
                    print(f"    ITEM {t.strip()!r:44s} {u}")
            time.sleep(PAUSE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
