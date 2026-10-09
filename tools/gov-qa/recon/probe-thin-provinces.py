"""探针：西藏 / 甘肃 省政府门户的政民互动入口（补 `none` 单元）。

只读，不落盘。
"""
import os
import re
import sys

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")

#: 候选入口（http/https 都试）
SITES = [
    ("西藏", ["http://www.xizang.gov.cn", "https://www.xizang.gov.cn"]),
    ("甘肃", ["http://www.gansu.gov.cn", "https://www.gansu.gov.cn"]),
]

#: 政民互动相关关键词
KW = ("政民互动", "互动交流", "12345", "省长信箱", "我要写信", "网上信访",
      "公众参与", "民意征集", "留言", "咨询投诉", "政务服务")


def main() -> int:
    with httpx.Client(timeout=25, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False, verify=False) as c:
        for name, urls in SITES:
            print(f"\n{'=' * 60}\n{name}\n{'=' * 60}")
            for url in urls:
                try:
                    r = c.get(url)
                except Exception as e:                                  # noqa: BLE001
                    print(f"  {url} FAIL {type(e).__name__} {str(e)[:50]}")
                    continue
                t = r.text or ""
                hits = [k for k in KW if k in t]
                print(f"  {url} HTTP {r.status_code} len={len(t)} 命中={hits}")
                if not hits:
                    continue
                seen = set()
                for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', t, re.S):
                    href, txt = m.group(1), re.sub(r"<[^>]+>", "", m.group(2))
                    txt = re.sub(r"\s+", " ", txt).strip()
                    if any(k in txt for k in KW) and href not in seen:
                        seen.add(href)
                        print(f"      → {txt[:26]:28s} {href[:80]}")
                    if len(seen) >= 8:
                        break
                break            # 该站成功一个就够
    return 0


if __name__ == "__main__":
    sys.exit(main())
