"""city-sc-probe13：自贡 来信选登 lxxd API / 攀枝花 500 详情 / 泸州分页确认。"""
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

    # ---- 自贡 来信选登 ----
    w("## 自贡 /zgsrmzf/lxxd/pc/list.html")
    r = get("https://www.zg.gov.cn/zgsrmzf/lxxd/pc/list.html")
    if hasattr(r, "text"):
        t = r.text
        w(f"  status={r.status_code} len={len(t)}")
        for m in re.finditer(r'<script[^>]+src=["\']([^"\']+)["\']', t):
            w("     SRC " + m.group(1))
        for m in re.finditer(r'ajaxUrl[\s\S]{0,300}', t):
            w("     AJAX " + re.sub(r"\s+", " ", m.group(0))[:300])
        for m in re.finditer(r'url\s*[:=]\s*["\']([^"\']+)["\']', t):
            w("     URL " + m.group(1))
        # 内联脚本
        for m in re.finditer(r'<script(?![^>]*src)[^>]*>([\s\S]{0,1500}?)</script>', t):
            w("     JS>>> " + re.sub(r"\s+", " ", m.group(1))[:800])

    # 自贡 尝试常见 API 前缀（hd/list）
    w("\n## 自贡 试 list API")
    for u in ("https://www.zg.gov.cn/zgsrmzf/hd/api/list",
              "https://www.zg.gov.cn/api/hd/list",
              "https://www.zg.gov.cn/zgsrmzf/lxxd/pc/listJson.html",
              "https://www.zg.gov.cn/zgsrmzf/lxxd/listJson"):
        rr = get(u, ref="https://www.zg.gov.cn/zgsrmzf/lxxd/pc/list.html")
        if hasattr(rr, "text"):
            w(f"  {u} -> {rr.status_code} ct={rr.headers.get('content-type')} len={len(rr.text)} {rr.text[:120]!r}")

    # ---- 攀枝花 500 详情 ----
    w("\n## 攀枝花 500 响应体")
    rr = get("http://www.panzhihua.gov.cn/webapp/mailbox/letterListJson",
             ref="http://www.panzhihua.gov.cn/hdcy/szxx/szxx/index.shtml",
             params={"channelId": 2, "mailType": 1, "pageNum": 1, "pageSize": 3, "orderStr": "replytime"})
    if hasattr(rr, "text"):
        txt = re.sub(r"<[^>]+>", " ", rr.text)
        w("  " + re.sub(r"\s+", " ", txt)[:600])
    w("\n## 攀枝花 getMailboxInfo")
    rr = get("http://www.panzhihua.gov.cn/webapp/mailbox/getMailboxInfo",
             ref="http://www.panzhihua.gov.cn/hdcy/szxx/szxx/index.shtml", params={"id": 2})
    if hasattr(rr, "text"):
        w(f"  -> {rr.status_code} len={len(rr.text)} {rr.text[:200]!r}")

    # ---- 泸州 分页/总数 ----
    w("\n## 泸州 分页确认")
    for u in ("https://www.luzhou.gov.cn/LetterBox/sjszxx/List",
              "https://www.luzhou.gov.cn/LetterBox/sjszxx/List_2",
              "https://www.luzhou.gov.cn/LetterBox/sjszxx/List_3"):
        rr = get(u)
        if hasattr(rr, "text"):
            ids = re.findall(r'/LetterBox/(\d+)', rr.text)
            w(f"  {u} -> {rr.status_code} 信件数={len(set(ids))} 例={sorted(set(ids))[:5]}")


if __name__ == "__main__":
    main()
