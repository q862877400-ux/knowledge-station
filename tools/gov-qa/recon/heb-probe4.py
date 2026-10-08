"""河北 阶段四：探省直部门 + 市级门户的公开问答/留言选登。"""
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
    ("heb-dept-sft", "http://sft.hebei.gov.cn/"),
    ("heb-dept-czt", "http://czt.hebei.gov.cn/"),
    ("heb-dept-wsjkw", "http://wsjkw.hebei.gov.cn/"),
    ("heb-dept-jyt", "http://jyt.hebei.gov.cn/"),
    ("heb-dept-scjg", "http://scjg.hebei.gov.cn/"),
    ("heb-city-hd", "https://www.hd.gov.cn/zmhd/"),
    ("heb-city-cangzhou", "http://www.cangzhou.gov.cn/cangzhou/c100035/zmhd.shtml"),
    ("heb-city-qhd", "https://www.qhd.gov.cn/index/zmhd/zfxx.html"),
    ("heb-city-baoding", "http://www.baoding12345.cn/"),
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
            print(f"[{name}] {url} -> {r.status_code} {len(body)}B")
            if r.status_code == 200:
                (HERE / f"{name}.html").write_text(body, encoding="utf-8", errors="replace")
                hits = re.findall(r'<a [^>]*href="([^"]+)"[^>]*>([^<]{2,30})</a>', body)
                for u, t in hits:
                    if any(k in t for k in
                           ("互动", "问答", "知识库", "留言", "咨询", "常见", "回应",
                            "选登", "政民", "热点", "智能", "我要问", "答问")):
                        print(f"    LINK {t.strip()!r:20s} {u}")
            time.sleep(PAUSE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
