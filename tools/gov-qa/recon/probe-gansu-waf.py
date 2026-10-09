"""探针：绕过甘肃 WAF（HTTP 412）+ 探西藏政务服务网。

只读，不落盘。

## 为什么

`recon/THIN-PROVINCES-NOTES.md` 记了：
- 甘肃 `gansu.gov.cn` 返回 **412**（WAF 反爬）
- 西藏信访平台需登录（判死）

本探针试四种绕法：
1. 完整浏览器头（`Sec-Fetch-*` / `Accept-Language` / `Upgrade-Insecure-Requests`）
2. 先请求首页拿 Cookie，再带 Cookie 请求
3. 试 **地市级** 门户（WAF 通常只在省级部署）
4. 试移动端 / 政务服务网
"""
import os
import sys

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx

#: 完整浏览器头（模拟真实 Chrome 导航请求）
FULL_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/avif,image/webp,*/*;q=0.8"),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
}

TARGETS = [
    ("甘肃省级(完整头)", "https://www.gansu.gov.cn"),
    ("甘肃·兰州", "https://www.lanzhou.gov.cn"),
    ("甘肃·天水", "https://www.tianshui.gov.cn"),
    ("甘肃·白银", "https://www.baiyin.gov.cn"),
    ("西藏政务网", "https://www.xzzwfw.gov.cn"),
    ("西藏·拉萨", "https://www.lasa.gov.cn"),
]


def main() -> int:
    with httpx.Client(timeout=25, headers=FULL_HEADERS,
                      follow_redirects=True, trust_env=False, verify=False) as c:
        for name, url in TARGETS:
            # ① 直接请求（完整头）
            try:
                r = c.get(url)
                code1, len1 = r.status_code, len(r.text or "")
            except Exception as e:                                      # noqa: BLE001
                print(f"{name:18s} {url}\n    FAIL {type(e).__name__} {str(e)[:50]}")
                continue
            print(f"{name:18s} {url}\n    完整头 → HTTP {code1} len={len1}")

            # ② 若被拦，试「先首页拿 Cookie 再请求」
            if code1 in (403, 412, 418):
                try:
                    c.get(url + "/", headers={**FULL_HEADERS, "Sec-Fetch-Site": "same-origin"})
                    r2 = c.get(url, headers={**FULL_HEADERS,
                                             "Referer": url + "/",
                                             "Sec-Fetch-Site": "same-origin"})
                    print(f"    带Cookie → HTTP {r2.status_code} len={len(r2.text or '')}")
                    if r2.status_code == 200:
                        t = r2.text
                        for kw in ("政民互动", "互动交流", "12345", "信箱", "留言"):
                            if kw in t:
                                print(f"      ✅ 命中「{kw}」")
                                break
                except Exception as e:                                      # noqa: BLE001
                    print(f"    带Cookie → FAIL {type(e).__name__}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
