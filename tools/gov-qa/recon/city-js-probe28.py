"""stage28：淮安门户找互动入口 + 连云港重试。"""
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
    c.headers.update({"User-Agent": "Mozilla/5.0"})

    w("## 淮安门户互动入口")
    for home in ("https://www.huaian.gov.cn/", "http://www.huaian.gov.cn/"):
        try:
            r = c.get(home, timeout=30, allow_redirects=True)
            w(f"  {home} -> {r.status_code} len={len(r.text)} url={r.url}")
            # 找互动相关链接
            for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]{0,30})</a>', r.text):
                href, txt = m.group(1), m.group(2)
                if any(k in txt for k in ("互动", "信箱", "12345", "热线", "留言", "诉求", "信访", "征集", "访谈")):
                    w(f"     [{txt.strip()}] {href}")
            for m in re.finditer(r'(hdjl|huifu|xinxiang|mailbox|12345|letter|liuyan|wsts|sjxx|szxx)', r.text):
                pass
        except Exception as e:  # noqa: BLE001
            w(f"  {home} -> {type(e).__name__} {str(e)[:70]}")

    w("\n## 连云港重试")
    for scheme in ("http", "https"):
        for path in ("/TrueCMS/mailBoxLetterController/getLetterList.do",
                     "/zglygzfmhwz/gzcy/gzcy.html"):
            try:
                r = c.get(f"{scheme}://www.lyg.gov.cn{path}", timeout=25)
                w(f"  {scheme} {path} -> {r.status_code} len={len(r.text)}")
            except Exception as e:  # noqa: BLE001
                w(f"  {scheme} {path} -> {type(e).__name__} {str(e)[:60]}")


if __name__ == "__main__":
    main()
