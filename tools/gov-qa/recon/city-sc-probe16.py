"""city-sc-probe16：成都 全头/备域 / 攀枝花 channelId 与 POST 试。"""
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


FULL = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def main():
    OUT.write_text("", encoding="utf-8")

    # ---- 成都 全头 ----
    w("## 成都 全头测试")
    for u in ("https://www.chengdu.gov.cn/", "https://www.chengdu.gov.cn/cdsrmzf/c105742/xxgk_list.shtml",
              "https://www.chengdu.gov.cn/chengdu/hdjl/index.shtml"):
        try:
            r = requests.get(u, headers=FULL, timeout=25)
            w(f"  {u} -> {r.status_code} len={len(r.text)} setcookie={r.headers.get('set-cookie','')[:80]!r}")
        except Exception as e:  # noqa: BLE001
            w(f"  {u} -> ERR {type(e).__name__}")

    # 成都 备域 / 常见互动路径
    w("\n## 成都 备域/路径")
    for u in ("https://www.chengdu.gov.cn/chengdu/hdjl/szxx/index.shtml",
              "https://www.chengdu.gov.cn/cdsrmzf/c105742/hdjl.shtml",
              "https://hd.chengdu.gov.cn/", "http://hd.chengdu.gov.cn/",
              "https://www.chengdu.gov.cn/cdsrmzf/c105742/list.shtml"):
        try:
            r = requests.get(u, headers=FULL, timeout=20)
            w(f"  {u} -> {r.status_code} len={len(r.text)}")
        except Exception as e:  # noqa: BLE001
            w(f"  {u} -> ERR {type(e).__name__}")

    # ---- 攀枝花 channelId 搜索 ----
    w("\n## 攀枝花 页面 channelId 线索")
    c = requests.Session()
    c.headers.update(FULL)
    t = c.get("http://www.panzhihua.gov.cn/hdcy/szxx/szxx/index.shtml", timeout=25).text
    for kw in ("channelId", "channel", "searchLetterPager", "mailType", "orgId", "organId"):
        for m in re.finditer(kw, t):
            s = max(0, m.start() - 80)
            w(f"  [{kw}] ..." + re.sub(r"\s+", " ", t[s:m.end() + 120])[:200])
            break

    w("\n## 攀枝花 letterListJson POST/GET 试")
    for method in ("get", "post"):
        for params in ({"channelId": 3, "mailType": 1, "pageNum": 1, "pageSize": 5, "orderStr": "replytime"},
                       {"channelId": 3, "mailType": "", "pageNum": 1, "pageSize": 5},
                       {"channelId": 4, "mailType": 1, "pageNum": 1, "pageSize": 5},
                       {"channelId": 0, "mailType": 1, "pageNum": 1, "pageSize": 5}):
            try:
                fn = getattr(c, method)
                r = fn("http://www.panzhihua.gov.cn/webapp/mailbox/letterListJson",
                       params=params, headers={"Referer": "http://www.panzhihua.gov.cn/hdcy/szxx/szxx/index.shtml",
                                               "X-Requested-With": "XMLHttpRequest"}, timeout=25)
                w(f"  {method} {params} -> {r.status_code} len={len(r.text)} {r.text[:90]!r}")
            except Exception as e:  # noqa: BLE001
                w(f"  {method} {params} -> ERR {type(e).__name__}")

    # 攀枝花 12345 便民热线页内接口
    w("\n## 攀枝花 12345 页内接口")
    t2 = c.get("http://www.panzhihua.gov.cn/hdcy/zwfwbmrx/index.shtml", timeout=25).text
    for m in re.finditer(r'url\s*[:=]\s*["\']([^"\']+)["\']', t2):
        w("  URL " + m.group(1))
    for m in re.finditer(r'/webapp/[A-Za-z0-9_/]+', t2):
        w("  EP " + m.group(0))


if __name__ == "__main__":
    main()
