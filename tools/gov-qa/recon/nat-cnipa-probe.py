"""侦察：国家知识产权局 jact 各 sysid 的「已答问题」列表与明细（worker-national 自用）。

用法：.venv/Scripts/python.exe tools/gov-qa/recon/nat-cnipa-probe.py
"""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx  # noqa: E402

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
BASE = "https://www.cnipa.gov.cn/jact/front"
TAG_RE = re.compile(r"<[^>]+>")
SID_RE = re.compile(r"transactId=(\d+)")
TITLE_RE = re.compile(r"title='[^']*'[^>]*>([^<]+)</a>")


def txt(x: str) -> str:
    x = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", x, flags=re.S | re.I)
    x = TAG_RE.sub(" ", x)
    x = x.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", x).strip()


def main() -> int:
    sids = sys.argv[1:] or ["6", "11", "12", "13", "14", "16"]
    with httpx.Client(timeout=30, headers={"User-Agent": UA}, follow_redirects=True,
                      trust_env=False) as cli:
        for sid in sids:
            ref = f"https://www.cnipa.gov.cn/jact/front/main.do?sysid={sid}"
            r = cli.post(f"{BASE}/dataproxy_mailpublist.do",
                         params={"sysid": sid, "startrecord": 0, "endrecord": 5, "perpage": 5},
                         headers={"Referer": ref})
            body = r.text
            tot = re.search(r"totalRecord=([0-9.]+)", body)
            tids = SID_RE.findall(body)
            titles = TITLE_RE.findall(body)
            print(f"=== sysid={sid} HTTP {r.status_code} total={tot.group(1) if tot else '?'} "
                  f"first_tid={tids[0] if tids else '?'}")
            if tids:
                d = cli.get(f"{BASE}/mailpubdetail.do",
                            params={"transactId": tids[0], "sysid": sid}, headers={"Referer": ref})
                t = txt(d.text)
                i = t.find("答复内容")
                j = t.find("问题内容")
                print("  Q:", t[j:j + 120] if j > 0 else "?")
                print("  A:", t[i:i + 220] if i > 0 else "?")
            time.sleep(1.2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
