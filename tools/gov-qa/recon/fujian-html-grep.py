"""从已存的福建 wyzx 整页 HTML 里找：列名 / 明细链接 / list 模块 JS 地址。"""
from __future__ import annotations

import os
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")

HTML = HERE / "fujian-wyzx-full.html"


def main() -> int:
    t = HTML.read_text(encoding="utf-8")
    print("len", len(t))
    for kw in ("咨询标题", "提问", "答复", "回复", "受理", "办件", "标题"):
        for m in list(re.finditer(kw, t))[:2]:
            a, b = max(0, m.start() - 80), min(len(t), m.end() + 80)
            print(f"KW> {kw}:", re.sub(r"\s+", " ", t[a:b])[:170])
    links = sorted(set(re.findall(r'href="([^"]*(?:cjwt|zx|xx|hf)[^"]*\.shtml)"', t)))
    print("cand links:", *(f"  {u}" for u in links[:10]), sep="\n")
    js = sorted(set(re.findall(r'src="([^"]+\.js)"', t)))
    print("scripts:", *(f"  {u}" for u in js[:15]), sep="\n")
    idx = t.find("listArgs")
    if idx > 0:
        print("listArgs context:")
        print(t[max(0, idx - 200):idx + 700])
    return 0


if __name__ == "__main__":
    main()
