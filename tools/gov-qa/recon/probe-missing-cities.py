"""探针：抽查几个「缺来源」的地级市门户，看它们用不用同一套中间件。

## 为什么

`recon/missing-cities.py` 报 **262 个地级市没有来源**（总数 334，已有 72）。
如果这些市**大量复用同一套中间件**（GOAL.md 说过「找到一个就等于找到一片」），
那就能用**一个适配器覆盖一片**。

## 本探针查什么

对每个市门户：
1. 能否访问（HTTP 状态）
2. 是否出现 **WAS5** 特征（`urltype=tree.TreeTempUrl` / `wbtreeid=` / `leadermail`）
3. 是否出现 **jact** 特征（`/jact/front/` / `sysid=`）
4. 是否出现 **IGI** 特征（`siteId=` / `igi`）
5. 是否出现其它常见中间件（`jpaas` / `szxx` / `hdjl` 路径）

只读，不落盘。
"""
import os
import re
import sys

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx

#: 抽查样本：跨省、跨区域，覆盖「缺得多」的几个省
CANDIDATES = [
    ("广东·佛山", "https://www.foshan.gov.cn"),
    ("广东·珠海", "https://www.zhuhai.gov.cn"),
    ("河南·洛阳", "https://www.ly.gov.cn"),
    ("河南·开封", "https://www.kaifeng.gov.cn"),
    ("安徽·芜湖", "https://www.wuhu.gov.cn"),
    ("云南·曲靖", "https://www.qj.gov.cn"),
    ("湖南·株洲", "https://www.zhuzhou.gov.cn"),
    ("辽宁·大连", "https://www.dl.gov.cn"),
    ("黑龙江·齐齐哈尔", "https://www.qqhr.gov.cn"),
    ("广西·柳州", "https://www.liuzhou.gov.cn"),
    ("河北·唐山", "https://www.tangshan.gov.cn"),
    ("湖北·宜昌", "https://www.yichang.gov.cn"),
]

H = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
}

SIGNS = [
    ("WAS5", (r"urltype=tree\.TreeTempUrl", r"wbtreeid=", r"leadermail")),
    ("jact", (r"/jact/front/", r"sysid=\d+")),
    ("IGI", (r"siteId=\d+", r"/igi/")),
    ("jpaas", (r"jpaas",)),
    ("szxx/hdjl", (r"/szxx/", r"/hdjl/", r"/zmhd/")),
]


def main() -> int:
    with httpx.Client(timeout=20, headers=H, follow_redirects=True,
                      trust_env=False, verify=False) as c:
        for name, url in CANDIDATES:
            try:
                r = c.get(url)
            except Exception as e:                                      # noqa: BLE001
                print(f"{name:18s} FAIL {type(e).__name__} {str(e)[:40]}")
                continue
            t = r.text or ""
            found = []
            for label, pats in SIGNS:
                if any(re.search(p, t, re.I) for p in pats):
                    found.append(label)
            mark = "✅" if r.status_code == 200 else "⚠️"
            print(f"{name:18s} {mark} HTTP {r.status_code} len={len(t):7d} "
                  f"中间件={found or ['（未识别）']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
