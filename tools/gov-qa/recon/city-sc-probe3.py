"""city-sc-probe3：泸州 LetterBox 数据接口 / 德阳 iList / 攀枝花+绵阳 首页接口。"""
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


def get(c, url, ref=None, method="get", **kw):
    h = {"Referer": ref} if ref else {}
    try:
        if method == "get":
            return c.get(url, timeout=25, allow_redirects=True, headers=h, **kw)
        return c.post(url, timeout=25, allow_redirects=True, headers=h, **kw)
    except Exception as e:  # noqa: BLE001
        return e


def main():
    OUT.write_text("", encoding="utf-8")
    c = requests.Session()
    c.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

    # ---- 泸州 列表页找 ajax ----
    w("## 泸州 sjszxx/List 内 ajax/query 上下文")
    r = get(c, "https://www.luzhou.gov.cn/LetterBox/sjszxx/List")
    if hasattr(r, "text"):
        for kw in ("letterbox/query", "$.ajax", "ajax(", "url:", "LetterBox/"):
            for m in re.finditer(re.escape(kw), r.text):
                s = max(0, m.start() - 150)
                w(f"--[{kw}]-- " + r.text[s:m.end() + 250].replace("\n", " ")[:420])
                break

    # ---- 泸州 letterbox/query 试参 ----
    w("\n## 泸州 /letterbox/query 试参")
    for params in ({"pageIndex": 1, "pageSize": 10},
                   {"page": 1, "rows": 10},
                   {"pageNum": 1, "pageSize": 10},
                   {"letterCategoryId": 141, "pageIndex": 1, "pageSize": 10}):
        rr = get(c, "https://www.luzhou.gov.cn/letterbox/query", ref="https://www.luzhou.gov.cn/LetterBox/sjszxx/List", params=params)
        if isinstance(rr, Exception):
            w(f"  {params} -> ERR {type(rr).__name__}")
        else:
            w(f"  {params} -> {rr.status_code} ct={rr.headers.get('content-type')} len={len(rr.text)} {rr.text[:140]!r}")

    # ---- 德阳 iList ----
    w("\n## 德阳 iList / iListGKJson")
    for u in ("https://www.deyang.gov.cn/info/iListGKJson.jsp",
              "https://www.deyang.gov.cn/info/iList.jsp"):
        for params in ({}, {"tm_id": "1"}, {"c": "1"}, {"classid": "1"}, {"t": "1"}):
            rr = get(c, u, ref="https://www.deyang.gov.cn/", params=params)
            if isinstance(rr, Exception):
                w(f"  {u} {params} -> ERR {type(rr).__name__}")
            else:
                w(f"  {u} {params} -> {rr.status_code} ct={rr.headers.get('content-type')} len={len(rr.text)} {rr.text[:120]!r}")

    # ---- 德阳 首页找互动 ----
    w("\n## 德阳 首页 互动关键词")
    r = get(c, "https://www.deyang.gov.cn/")
    if hasattr(r, "text"):
        for kw in ("互动", "信箱", "12345", "留言", "诉求", "访谈", "征集"):
            idx = [m.start() for m in re.finditer(kw, r.text)]
            w(f"  {kw}: {len(idx)}")
            for i in idx[:2]:
                w("     ..." + r.text[max(0, i - 80):i + 80].replace("\n", " "))

    # ---- 攀枝花/绵阳 首页 ----
    w("\n## 攀枝花/绵阳 首页接口")
    for name, home in (("攀枝花", "http://www.panzhihua.gov.cn/"),
                       ("绵阳", "http://www.mianyang.gov.cn/")):
        r = get(c, home)
        if not hasattr(r, "text"):
            w(f"  {name} -> ERR {type(r).__name__}")
            continue
        w(f"  {name} -> {r.status_code} len={len(r.text)}")
        eps = set(re.findall(r'["\'](/?[A-Za-z][A-Za-z0-9_/\.\-]*\.(?:do|jsp|json|shtml|ashx|action))["\']', r.text))
        for e in sorted(eps)[:25]:
            w(f"     EP {e}")


if __name__ == "__main__":
    main()
