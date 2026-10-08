"""city-sc-probe11：攀枝花 letterListJson 正确参数 / 自贡 szxx ajaxUrl 配置。"""
import json
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
    REF = "http://www.panzhihua.gov.cn/hdcy/szxx/szxx/index.shtml"

    # ---- 攀枝花 组织树 ----
    w("## 攀枝花 getAllSubOrgan?id=2 树")
    r = get("http://www.panzhihua.gov.cn/webapp/mailbox/getAllSubOrgan", ref=REF, params={"id": 2})
    if hasattr(r, "text"):
        try:
            d = r.json()
            def walk(n, depth=0):
                if depth > 2:
                    return
                for c in (n.get("children") or []):
                    w("   " + "  " * depth + f"id={c.get('id')} name={c.get('name') or c.get('organName')} channelId={c.get('channelId')}")
                    walk(c, depth + 1)
            w("   root id=" + str(d.get("id")) + " name=" + str(d.get("name")))
            walk(d)
        except Exception as e:  # noqa: BLE001
            w("   non-json: " + r.text[:300])

    # ---- 攀枝花 letterListJson 实测 ----
    w("\n## 攀枝花 /webapp/mailbox/letterListJson")
    for params in ({"channelId": 2, "mailType": 1, "pageNum": 1, "pageSize": 5, "orderStr": "replytime"},
                   {"channelId": "2", "mailType": "1", "pageNum": 1, "pageSize": 5, "orderStr": "replytime"},
                   {"channelId": 2, "mailType": "", "pageNum": 1, "pageSize": 5, "orderStr": "replytime"},
                   {"channelId": "", "mailType": 1, "pageNum": 1, "pageSize": 5, "orderStr": "replytime"}):
        rr = get("http://www.panzhihua.gov.cn/webapp/mailbox/letterListJson", ref=REF, params=params)
        if hasattr(rr, "text"):
            w(f"  {params} -> {rr.status_code} ct={rr.headers.get('content-type')} len={len(rr.text)} {rr.text[:200]!r}")
        else:
            w(f"  {params} -> ERR {type(rr).__name__}")

    # ---- 自贡 szxx 页脚本 + ajaxUrl ----
    w("\n## 自贡 szxx/pc/list.html 全文")
    r = get("https://www.zg.gov.cn/zgsrmzf/szxx/pc/list.html")
    if hasattr(r, "text"):
        w(r.text[:3000])

    w("\n## 自贡 找 ajaxUrl 配置脚本")
    for u in ("https://www.zg.gov.cn/zgsrmzf/pc2025/hd/js/config.js",
              "https://www.zg.gov.cn/zgsrmzf/pc2025/js/config.js",
              "https://www.zg.gov.cn/default/js/config.js",
              "https://www.zg.gov.cn/zgsrmzf/pc2025/hd/js/common.js",
              "https://www.zg.gov.cn/zgsrmzf/pc2025/hd/js/szxx.js",
              "https://www.zg.gov.cn/zgsrmzf/pc2025/hd/js/list.js"):
        rr = get(u)
        if hasattr(rr, "text") and rr.status_code == 200:
            w(f"  {u} -> 200 len={len(rr.text)}")
            for m in re.finditer(r'ajaxUrl[\s\S]{0,400}', rr.text):
                w("     " + re.sub(r"\s+", " ", m.group(0))[:400])
                break


if __name__ == "__main__":
    main()
