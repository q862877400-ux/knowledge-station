"""stage27：常州 明细获取路径（主域 ajax detail / 子域 show / 列表是否含答复）。"""
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
OUT = Path(__file__).with_suffix(".txt")


def w(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    with OUT.open("a", encoding="utf-8") as f:
        f.write(s + "\n")


def main():
    OUT.write_text("", encoding="utf-8")
    c = requests.Session()
    c.headers.update({"User-Agent": "Mozilla/5.0",
                      "Referer": "https://www.changzhou.gov.cn/gova/letter/index.php"})
    idx = "https://www.changzhou.gov.cn/gova/letter/index.php"
    h = c.get(idx, timeout=30).text
    w("## index.php 内 ajax/detail 上下文")
    for kw in ("ajax.php", "action=", "show", "detail", "id="):
        for m in re.finditer(re.escape(kw), h):
            s = max(0, m.start() - 120)
            w(f"--[{kw}]-- " + h[s:m.end() + 160].replace("\n", " ")[:300])

    w("\n## 主域 ajax.php 各种 action")
    for params in ({"action": "detail", "id": 365},
                   {"action": "show", "id": 365},
                   {"action": "content", "id": 365},
                   {"action": "list", "page": 1, "pagesize": 100},
                   {"action": "list", "page": 1, "limit": 100}):
        try:
            r = c.get("https://www.changzhou.gov.cn/gova/letter/ajax.php",
                      params=params, timeout=25)
            w(f"  {params} -> {r.status_code} len={len(r.text)} {r.text[:120]!r}")
        except Exception as e:  # noqa: BLE001
            w(f"  {params} -> {type(e).__name__} {str(e)[:60]}")

    w("\n## 子域明细页（带完整头重试）")
    for u in ("https://sgj.changzhou.gov.cn/index.php?m=letter&c=index&a=show&id=365",
              "http://sgj.changzhou.gov.cn/index.php?m=letter&c=index&a=show&id=365"):
        try:
            r = c.get(u, timeout=25, headers={"Referer": idx,
                                              "Accept": "text/html,application/xhtml+xml",
                                              "Accept-Language": "zh-CN,zh;q=0.9"})
            w(f"  {u} -> {r.status_code} len={len(r.text)}")
            txt = re.sub(r"<[^>]+>", " ", r.text)
            txt = re.sub(r"\s+", " ", txt).strip()
            w("    text=" + txt[:400])
        except Exception as e:  # noqa: BLE001
            w(f"  {u} -> {type(e).__name__} {str(e)[:60]}")


if __name__ == "__main__":
    main()
