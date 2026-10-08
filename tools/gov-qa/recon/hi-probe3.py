"""海南 阶段三：实测 /u/search/ajaxlist 政策问答接口。"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx  # noqa: E402

HERE = Path(__file__).resolve().parent
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")

API = "https://www.hainan.gov.cn/u/search/ajaxlist"
CHANNELS = {
    "政策问答": "41996292c8494145865bc7aafe48a9b1",
}


def main() -> int:
    with httpx.Client(timeout=40, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False) as cli:
        for name, cid in CHANNELS.items():
            print(f"=== {name} channel_id={cid} ===")
            r = cli.post(API, params={"channel_id": cid},
                         data={"searchWord": "", "curPage": "0", "PageSize": "15"},
                         headers={"Referer": "https://www.hainan.gov.cn/hainan/zcwd/zcwd.shtml",
                                  "X-Requested-With": "XMLHttpRequest"})
            print(f"HTTP {r.status_code} {len(r.text)}B")
            (HERE / "hi-ajaxlist-test.json").write_text(r.text, encoding="utf-8", errors="replace")
            try:
                j = r.json()
            except Exception as e:  # noqa: BLE001
                print("非 JSON:", r.text[:400]); continue
            page = j.get("page") or {}
            print(f"allRow={page.get('allRow')} totalPage={page.get('totalPage')} "
                  f"currentPage={page.get('currentPage')} list={len(page.get('list') or [])}")
            for it in (page.get("list") or [])[:5]:
                print(f"  · {it.get('title')!r}")
                print(f"    url={it.get('url')}")
                print(f"    memo={(it.get('memo') or '')[:120]!r}")
            time.sleep(1.5)
    return 0


if __name__ == "__main__":
    sys.exit(main())
