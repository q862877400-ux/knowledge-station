"""逐条统计安徽某一页的明细抓取结果（200? 解析成功?），定位 59 条丢失的真实原因。"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import UA  # noqa: E402
from adapters.ah_sthjt import LIST_URL, ITEM_RE, _parse_detail  # noqa: E402

OUT = HERE / "ah-page-diagnose.txt"


def main() -> int:
    import httpx

    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=20, follow_redirects=True) as c:
        with OUT.open("w", encoding="utf-8") as f:
            for page in (1, 5, 10):
                r = c.get(f"{LIST_URL}?wenda_keywords=&pageSize=&categoryId=&categoryCode=&organDn=&pageIndex={page}")
                items = ITEM_RE.findall(r.text or "")
                uniq = list({u: t for u, t in items}.items())
                f.write(f"\n=== 第 {page} 页：链接 {len(items)}，去重 {len(uniq)} ===\n")
                ok = bad = short = 0
                for u, t in uniq:
                    time.sleep(0.8)
                    d = c.get(u)
                    rec = None
                    if getattr(d, "status_code", 0) == 200:
                        try:
                            rec = _parse_detail(d.text or "")
                        except Exception as e:                              # noqa: BLE001
                            f.write(f"  异常 {u[-14:]} {type(e).__name__}\n")
                    if rec:
                        ok += 1
                    else:
                        bad += 1
                        f.write(f"  未解析 [{getattr(d,'status_code','?')}] {u}\n")
                f.write(f"  成功 {ok} / 未解析 {bad}\n")
                time.sleep(1)
    print("written", OUT)
    return 0


if __name__ == "__main__":
    main()
