"""探针：天水 / 拉萨 门户的政民互动栏目（补甘肃、西藏两个 `none` 单元）。

只读，不落盘。
"""
import os
import re
import sys

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx

FULL_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/avif,image/webp,*/*;q=0.8"),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}

SITES = [("甘肃·天水", "https://www.tianshui.gov.cn"),
         ("西藏·拉萨", "https://www.lasa.gov.cn")]

KW = ("政民互动", "互动交流", "12345", "市长信箱", "书记信箱", "我要写信",
      "网上信访", "民意征集", "留言", "咨询投诉", "政务服务", "来信选登")


def main() -> int:
    with httpx.Client(timeout=25, headers=FULL_HEADERS,
                      follow_redirects=True, trust_env=False, verify=False) as c:
        for name, base in SITES:
            print(f"\n{'=' * 58}\n{name}  {base}\n{'=' * 58}")
            try:
                r = c.get(base)
            except Exception as e:                                      # noqa: BLE001
                print(f"  FAIL {type(e).__name__}")
                continue
            t = r.text or ""
            hits = [k for k in KW if k in t]
            print(f"  HTTP {r.status_code} len={len(t)} 命中={hits}")
            seen = set()
            for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', t, re.S):
                href, txt = m.group(1), re.sub(r"<[^>]+>", "", m.group(2))
                txt = re.sub(r"\s+", " ", txt).strip()
                if any(k in txt for k in KW) and href not in seen:
                    seen.add(href)
                    print(f"      → {txt[:24]:26s} {href[:78]}")
                if len(seen) >= 10:
                    break
    return 0


if __name__ == "__main__":
    sys.exit(main())
