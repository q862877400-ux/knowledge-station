"""河北 阶段六：扫省直部门 /hdjl/qzxx/ 同款群众信箱。"""
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

DEPTS = ["gat", "gxt", "hbdrc", "hbepb", "hbsa", "hebwb", "jtt", "jygl", "jyt",
         "lycy", "minzheng", "mw", "nync", "rta", "scjg", "sft", "sgdb", "sjt",
         "slt", "sport", "swj", "swt", "szj", "tjj", "tyjrswt", "wenwu", "whly",
         "wsjkw", "czt"]

PATHS = ["/hdjl/qzxx/", "/hdjl/"]


def main() -> int:
    with httpx.Client(timeout=20, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False) as cli:
        for d in DEPTS:
            for path in PATHS:
                url = f"http://{d}.hebei.gov.cn{path}"
                try:
                    r = cli.get(url)
                except Exception as e:  # noqa: BLE001
                    print(f"[{d}{path}] {type(e).__name__}")
                    time.sleep(PAUSE)
                    continue
                b = r.text or ""
                tag = ""
                if r.status_code == 200:
                    n = len(re.findall(r'class="clearfix">\s*<span class="t', b))
                    if "群众信箱" in b or "qzxx" in b:
                        tag = f"  ★群众信箱 条目~{n}"
                    hits = re.findall(r'<a [^>]*href="([^"]*(?:qzxx|liuyan|hdjl)[^"]*)"[^>]*>([^<]{2,20})</a>', b)
                    if hits:
                        tag += "  links=" + ",".join(f"{t}:{u}" for u, t in hits[:4])
                print(f"[{d}{path}] {r.status_code} {len(b)}B{tag}")
                time.sleep(PAUSE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
