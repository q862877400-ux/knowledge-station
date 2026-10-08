"""city-sc-probe2：成都(http/412) / 自贡重试 / 泸州LetterBox / 攀枝花+绵阳 hdcy / 德阳 nav。"""
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


def get(c, url, ref=None):
    h = {"Referer": ref} if ref else {}
    for u in (url, url.replace("https://", "http://"), url.replace("http://", "https://")):
        try:
            r = c.get(u, timeout=25, allow_redirects=True, headers=h)
            return r
        except Exception:  # noqa: BLE001
            continue
    return None


def main():
    OUT.write_text("", encoding="utf-8")
    c = requests.Session()
    c.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

    for label, urls in [
        ("成都", ["https://www.chengdu.gov.cn/", "http://www.chengdu.gov.cn/"]),
        ("自贡", ["https://www.zigong.gov.cn/", "http://www.zigong.gov.cn/"]),
        ("攀枝花 hdcy", ["http://www.panzhihua.gov.cn/hdcy/zwfwbmrx/index.shtml"]),
        ("绵阳 hdcy", ["http://www.mianyang.gov.cn/hdcy/zwfwbmrx/index.shtml"]),
        ("泸州 LetterBox list", ["https://www.luzhou.gov.cn/LetterBox/sjszxx/List",
                                "https://www.luzhou.gov.cn/LetterBox/notice"]),
        ("德阳", ["https://www.deyang.gov.cn/", "http://www.deyang.gov.cn/"]),
    ]:
        w(f"\n===== {label} =====")
        for u in urls:
            r = get(c, u)
            if r is None:
                w(f"  {u} -> ERR")
                continue
            w(f"  {u} -> {r.status_code} len={len(r.text)} ct={r.headers.get('content-type')}")
            if r.status_code != 200:
                continue
            # 打印 ajax / api / do 端点
            for m in re.finditer(r'(?:url\s*[:=]\s*["\']|action=["\'])([^"\']{3,120})', r.text):
                pass
            eps = set(re.findall(r'["\'](/?[A-Za-z][A-Za-z0-9_/\.\-]*\.(?:do|json|action|ashx))["\']', r.text))
            for e in sorted(eps)[:20]:
                w(f"     EP {e}")
            # LetterBox / API 路径
            for m in re.finditer(r'["\'](/[A-Za-z][A-Za-z0-9_/\.\-]*(?:List|list|Search|search|Detail|detail|Ajax|ajax|Query|query)[A-Za-z0-9_/\.\-]*)["\']', r.text):
                w(f"     P {m.group(1)[:100]}")


if __name__ == "__main__":
    main()
