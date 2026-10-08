"""city-sc-probe6：攀枝花 mailbox 全部接口 / 成都 API / 绵阳备域 / 自贡重试。"""
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

    # ---- 攀枝花 mailbox 页面全部 /webapp 调用 ----
    w("## 攀枝花 mailbox 页面全部 /webapp 端点")
    for path in ("/hdcy/szxx/szxx/index.shtml", "/hdcy/szfbmxx/index.shtml",
                 "/hdcy/szxx/szxx/wyxx/index.shtml"):
        r = get("http://www.panzhihua.gov.cn" + path)
        if not hasattr(r, "text"):
            continue
        w(f"  --- {path} status={r.status_code} len={len(r.text)}")
        eps = sorted(set(re.findall(r'["\'](/webapp/[A-Za-z0-9_/]+)', r.text)))
        for e in eps:
            w("     " + e)
        # data:{...} 参数
        for m in re.finditer(r'url\s*:\s*["\'](/webapp/[^"\']+)["\'][\s\S]{0,200}?data\s*:\s*\{([^}]{0,200})\}', r.text):
            w(f"     CALL {m.group(1)} data={{{m.group(2).strip()}}}")

    # 试攀枝花 mailbox list 候选
    w("\n## 攀枝花 mailbox list 候选")
    for ep in ("/webapp/mailbox/getAllSubOrgan", "/webapp/mailbox/getMailList",
               "/webapp/mailbox/getMailboxList", "/webapp/mailbox/list",
               "/webapp/mailbox/getMailbox", "/webapp/mailbox/getMails"):
        rr = get("http://www.panzhihua.gov.cn" + ep, ref="http://www.panzhihua.gov.cn/hdcy/szxx/szxx/index.shtml",
                 params={"id": 2, "pageIndex": 1, "pageSize": 5})
        if hasattr(rr, "text"):
            w(f"  {ep} -> {rr.status_code} ct={rr.headers.get('content-type')} len={len(rr.text)} {rr.text[:150]!r}")
        else:
            w(f"  {ep} -> ERR {type(rr).__name__}")

    # ---- 成都 API（412 WAF，直接试 JSON 接口）----
    w("\n## 成都 直接试 JSON/接口")
    for u in ("https://www.chengdu.gov.cn/chengdu/hdjl/szxx/index.shtml",
              "http://www.chengdu.gov.cn/chengdu/hdjl/szxx/index.shtml",
              "https://www.chengdu.gov.cn/igs/front/search.jhtml",
              "https://www.chengdu.gov.cn/cdsrmzf/c105742/xxgk_list.shtml"):
        rr = get(u)
        if hasattr(rr, "text"):
            w(f"  {u} -> {rr.status_code} ct={rr.headers.get('content-type')} len={len(rr.text)} {rr.text[:80]!r}")
        else:
            w(f"  {u} -> ERR {type(rr).__name__}")

    # ---- 绵阳备域 ----
    w("\n## 绵阳备域")
    for u in ("https://my.gov.cn/", "http://my.gov.cn/",
              "https://www.my.gov.cn/", "http://www.my.gov.cn/"):
        rr = get(u)
        if hasattr(rr, "text"):
            ti = re.search(r"<title>([^<]*)</title>", rr.text)
            w(f"  {u} -> {rr.status_code} len={len(rr.text)} final={rr.url} title={ti.group(1)[:40] if ti else '?'}")
        else:
            w(f"  {u} -> ERR {type(rr).__name__}")

    # ---- 自贡重试 ----
    w("\n## 自贡重试")
    for u in ("http://www.zigong.gov.cn/", "https://www.zigong.gov.cn/",
              "http://www.zg.gov.cn/", "https://www.zg.gov.cn/"):
        rr = get(u)
        if hasattr(rr, "text"):
            ti = re.search(r"<title>([^<]*)</title>", rr.text)
            w(f"  {u} -> {rr.status_code} len={len(rr.text)} title={ti.group(1)[:40] if ti else '?'}")
        else:
            w(f"  {u} -> ERR {type(rr).__name__} {str(rr)[:60]}")


if __name__ == "__main__":
    main()
