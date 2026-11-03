"""探针：找「洛阳 / 芜湖 / 宜昌」的 IGI siteId。

## 为什么高价值

抽查发现这 3 个市用 **IGI** 中间件 —— 而我们**已有 `igi-chunked.py` 分片驱动**
（山西 15 个 siteId / 广西 208 个 / 宁夏 64 个都靠它采）。
**只要找到 siteId 就能批量接入，不用写新适配器。**

## 怎么找

IGI 的门户首页/互动栏目里通常有：
- `siteId=<数字>` 出现在 JS 或链接里
- `/igi/` 路径
- 某个「站点列表」接口

只读，不落盘。
"""
import os
import re
import sys

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx

SITES = [
    ("河南·洛阳", "https://www.ly.gov.cn"),
    ("安徽·芜湖", "https://www.wuhu.gov.cn"),
    ("湖北·宜昌", "https://www.yichang.gov.cn"),
]

H = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Upgrade-Insecure-Requests": "1",
}

#: IGI 特征
PATTERNS = (
    r"siteId['\"]?\s*[:=]\s*['\"]?(\d+)",
    r"siteid['\"]?\s*[:=]\s*['\"]?(\d+)",
    r"/igi/[^\"'\s]{0,60}",
    r"igi[^\"'\s]{0,40}\.js",
    r"[\"'](/[a-zA-Z0-9_\-/]{0,50}igi[a-zA-Z0-9_\-/]{0,50})[\"']",
)


def main() -> int:
    with httpx.Client(timeout=20, headers=H, follow_redirects=True,
                      trust_env=False, verify=False) as c:
        for name, base in SITES:
            print(f"\n{'=' * 56}\n{name}  {base}\n{'=' * 56}")
            try:
                r = c.get(base)
            except Exception as e:                                      # noqa: BLE001
                print(f"  FAIL {type(e).__name__}")
                continue
            t = r.text or ""
            print(f"  HTTP {r.status_code} len={len(t)}")

            # ① siteId
            ids = sorted(set(re.findall(PATTERNS[0], t, re.I)) |
                         set(re.findall(PATTERNS[1], t, re.I)))
            print(f"  siteId 候选: {ids[:10]}")

            # ② /igi/ 路径
            paths = sorted(set(re.findall(PATTERNS[4], t, re.I)))[:8]
            print(f"  igi 路径: {paths}")

            # ③ 找「互动」栏目的链接
            for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', t, re.S):
                href, txt = m.group(1), re.sub(r"<[^>]+>", "", m.group(2))
                txt = re.sub(r"\s+", " ", txt).strip()
                if any(k in txt for k in ("互动", "信箱", "留言", "12345", "咨询")):
                    print(f"    → {txt[:20]:22s} {href[:80]}")

            # ④ 找 js 文件（siteId 常在 js 里）
            js = sorted(set(re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', t)))[:6]
            print(f"  script: {js}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
