"""city-sc-probe4：泸州列表结构+分页 / 攀枝花·绵阳 hdcy 子栏目 / 德阳找信箱。"""
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


def get(url, ref=None, **kw):
    c = requests.Session()
    c.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    if ref:
        c.headers["Referer"] = ref
    try:
        return c.get(url, timeout=25, allow_redirects=True, **kw)
    except Exception as e:  # noqa: BLE001
        return e


def main():
    OUT.write_text("", encoding="utf-8")

    # ---- 泸州 列表页 ----
    w("## 泸州 LetterBox/sjszxx/List 结构")
    r = get("https://www.luzhou.gov.cn/LetterBox/sjszxx/List")
    if hasattr(r, "text"):
        t = r.text
        w(f"  status={r.status_code} len={len(t)}")
        # 标题 link
        for m in re.finditer(r'<a[^>]+href=["\']([^"\']*LetterBox[^"\']*)["\'][^>]*>([^<]{2,60})</a>', t):
            w(f"     [{m.group(2).strip()[:40]}] {m.group(1)}")
        # 分页
        for m in re.finditer(r'List_?\d+', t):
            pass
        pages = sorted(set(re.findall(r'List[_/]?(\d+)', t)))
        w("     分页候选: " + str(pages[:20]))
        # 有无答复字段
        for kw in ("答复", "回复", "处理结果", "信件内容", "来信内容"):
            w(f"     含「{kw}」: {t.count(kw)}")

    # ---- 泸州 详情页探测 ----
    w("\n## 泸州 详情页探测")
    for u in ("https://www.luzhou.gov.cn/LetterBox/sjszxx/Detail/1",
              "https://www.luzhou.gov.cn/LetterBox/sjszxx/List_2",
              "https://www.luzhou.gov.cn/LetterBox/Detail/1"):
        rr = get(u)
        if hasattr(rr, "text"):
            w(f"  {u} -> {rr.status_code} len={len(rr.text)}")
        else:
            w(f"  {u} -> ERR {type(rr).__name__}")

    # ---- 攀枝花 ----
    for name, base in (("攀枝花", "http://www.panzhihua.gov.cn"),
                       ("绵阳", "http://www.mianyang.gov.cn")):
        w(f"\n## {name} hdcy 子栏目")
        for path in ("/hdcy/szxx/szxx/index.shtml", "/hdcy/szfbmxx/index.shtml",
                     "/hdcy/index.shtml", "/hdcy/zwfwbmrx/index.shtml"):
            rr = get(base + path)
            if hasattr(rr, "text"):
                title = re.search(r"<title>([^<]*)</title>", rr.text)
                w(f"  {path} -> {rr.status_code} len={len(rr.text)} title={title.group(1)[:40] if title else '?'}")
                if rr.status_code == 200:
                    eps = set(re.findall(r'["\'](/[A-Za-z][A-Za-z0-9_/\.\-]*(?:\.do|\.json|\.jsp|Ajax|ajax|Json|json)[A-Za-z0-9_/\.\-]*)["\']', rr.text))
                    for e in sorted(eps)[:10]:
                        w(f"       EP {e}")
            else:
                w(f"  {path} -> ERR {type(rr).__name__}")

    # ---- 德阳 ----
    w("\n## 德阳 找信箱")
    for u in ("https://www.deyang.gov.cn/hdjl/", "https://www.deyang.gov.cn/szxx/",
              "https://www.deyang.gov.cn/hd/"):
        rr = get(u)
        if hasattr(rr, "text"):
            w(f"  {u} -> {rr.status_code} len={len(rr.text)}")
        else:
            w(f"  {u} -> ERR {type(rr).__name__}")


if __name__ == "__main__":
    main()
