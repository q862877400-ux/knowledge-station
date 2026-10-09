"""探人大「征求意见」栏目的列表结构 —— 判断能否批量采。

对每个候选栏目：取列表页 → 找分页规律 → 取一条详情 → 看正文是否有实质内容。
"""
import os
import re
import sys

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")

LISTS = [
    ("江苏人大", "https://www.jsrd.gov.cn/gzcy/fgzqyj/"),
    ("广东人大", "https://www.gdpc.gov.cn/gdrdw/zyfb/fgyjzj/index.html"),
    ("河南人大", "https://www.hnrd.gov.cn/channel/16168.html"),
    ("山东人大", "http://www.sdrd.gov.cn"),
    ("全国人大", "http://www.npc.gov.cn/c2/kgfb/202608/t20260828_457237.html"),
]

#: 常见分页参数
PAGE_PAT = re.compile(r"(index[_\-]?\d+\.(?:html?|shtml?)|page[_=]?\d+|_\d+\.shtml?)", re.I)


def main() -> int:
    with httpx.Client(timeout=25, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False, verify=False) as c:
        for name, url in LISTS:
            print(f"\n{'=' * 66}\n{name}  {url}\n{'=' * 66}")
            try:
                r = c.get(url)
            except Exception as e:                                      # noqa: BLE001
                print(f"  FAIL {type(e).__name__} {str(e)[:60]}")
                continue
            t = r.text or ""
            print(f"  HTTP {r.status_code}  len={len(t)}")
            # 列表条目：<a href> 里含「草案/征求/条例/办法/规定」
            items = []
            for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', t, re.S):
                href, txt = m.group(1), re.sub(r"<[^>]+>", "", m.group(2))
                txt = re.sub(r"\s+", " ", txt).strip()
                if len(txt) >= 6 and any(k in txt for k in
                                         ("草案", "征求", "条例", "办法", "规定", "决定")):
                    items.append((txt, href))
            print(f"  列表条目 {len(items)} 条，前 5：")
            for txt, href in items[:5]:
                print(f"    · {txt[:40]:42s} {href[:80]}")
            # 分页线索
            pg = sorted(set(PAGE_PAT.findall(t)))[:8]
            print(f"  分页线索: {pg}")
            # 取一条详情
            if items:
                href = items[0][1]
                if href.startswith("//"):
                    href = "https:" + href
                elif href.startswith("/"):
                    from urllib.parse import urlparse
                    u = urlparse(url)
                    href = f"{u.scheme}://{u.netloc}{href}"
                elif not href.startswith("http"):
                    continue
                try:
                    d = c.get(href)
                    body = re.sub(r"<script.*?</script>", "", d.text, flags=re.S | re.I)
                    body = re.sub(r"<style.*?</style>", "", body, flags=re.S | re.I)
                    body = re.sub(r"<[^>]+>", " ", body)
                    body = re.sub(r"\s+", " ", body).strip()
                    print(f"  详情 HTTP {d.status_code} len={len(d.text)} 正文约 {len(body)} 字")
                    print(f"    正文片段: {body[:150]}")
                except Exception as e:                                  # noqa: BLE001
                    print(f"  详情 FAIL {type(e).__name__}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
