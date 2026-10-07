"""诊断安徽问答知识库「列表有、采不到」的那批条目：抽样看明细页到底缺什么。"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import UA  # noqa: E402
from adapters.ah_sthjt import BASE, LIST_URL, ITEM_RE, QA_RE, _text  # noqa: E402

OUT = HERE / "ah-gap-diagnose.txt"


def main() -> int:
    import httpx

    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=20, follow_redirects=True) as c:
        # 取最后一页（页数最多、最可能有另一模板）
        r = c.get(f"{LIST_URL}?wenda_keywords=&pageSize=&categoryId=&categoryCode=&organDn=&pageIndex=15")
        items = ITEM_RE.findall(r.text or "")
        with OUT.open("w", encoding="utf-8") as f:
            f.write(f"第 15 页条目 {len(items)}\n")
            for u, t in items[:5]:
                d = c.get(u)
                txt = _text(d.text or "")
                has_qa = bool(QA_RE.search(txt))
                f.write(f"\n--- {u} [{d.status_code}] 文本 {len(txt)} 问/答标记={'有' if has_qa else '无'}\n")
                f.write(txt[:400] + "\n")
    print("written", OUT)
    return 0


if __name__ == "__main__":
    main()
