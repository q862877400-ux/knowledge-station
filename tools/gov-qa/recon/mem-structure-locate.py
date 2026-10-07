"""从已存的 mem 明细页 HTML 里定位「咨询/回复」正文区（修适配器抽取用）。"""
from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
HTML = HERE / "mem-detail-sample.html"


def strip_scripts(t: str) -> str:
    t = re.sub(r"<script.*?</script>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<style.*?</style>", " ", t, flags=re.S | re.I)
    t = re.sub(r"<!--.*?-->", " ", t, flags=re.S)
    return t


def main() -> int:
    t = HTML.read_text(encoding="utf-8")
    body = strip_scripts(t)
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", body))
    i = text.find("咨询")
    print("--- 正文（'咨询'起 800 字）---")
    print(text[i:i + 800])
    print("\n--- 含「回复」的片段 ---")
    for m in list(re.finditer("回复", text))[:4]:
        print("  ...", text[max(0, m.start() - 120):m.start() + 220].strip()[:330])
    print("\n--- .cont 容器内 HTML（前 1200 字）---")
    m = re.search(r'<div[^>]*class="[^"]*\bcont\b[^"]*"[^>]*>(.*?)</div>\s*</div>', body, re.S | re.I)
    if m:
        inner = m.group(1)
        plain = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", inner))
        print(plain[:900])
    else:
        print("未匹配到 .cont 容器；打印其起始位置上下文")
        j = body.find('class="cont"')
        print(body[max(0, j - 100):j + 1200] if j > 0 else "not found")
    return 0


if __name__ == "__main__":
    main()
