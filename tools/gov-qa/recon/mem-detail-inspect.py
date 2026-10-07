"""看应急管理部明细页的结构：答复正文在哪个容器里，好修 mem 适配器的抽取。"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")

sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import UA  # noqa: E402

# 从已有 mem 数据里取一个明细 URL
import json  # noqa: E402

DATA = HERE.parent / "data"


def main() -> int:
    import httpx

    rows = []
    for p in DATA.glob("mem-*.jsonl"):
        rows = [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    url = rows[0]["url"] if rows else "https://www.mem.gov.cn/hd/gzly/hdhdly/"
    print("sample url:", url)

    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=20, follow_redirects=True) as c:
        r = c.get(url)
    t = r.text
    (HERE / "mem-detail-sample.html").write_text(t, encoding="utf-8")
    print("status", r.status_code, "len", len(t))
    # 去掉 script/style 后的正文
    body = re.sub(r"<script.*?</script>", " ", t, flags=re.S | re.I)
    body = re.sub(r"<style.*?</style>", " ", body, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", body)
    text = re.sub(r"\s+", " ", text)
    print("\n--- 去脚本后的正文前 600 字 ---")
    print(text[:600])
    # 找可能的答复容器 class/id
    for m in re.finditer(r'<div[^>]+(class|id)="([^"]*(?:content|hf|reply|con|main|txt)[^"]*)"', t, re.I):
        print("容器>", m.group(0)[:110])
    return 0


if __name__ == "__main__":
    main()
