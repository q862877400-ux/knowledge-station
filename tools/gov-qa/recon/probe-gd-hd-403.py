"""探针：广东「带 hdjlpt 指纹但落地页 403」的市 —— 403 是 WAF 还是真的没部署？

## 动机（2026-10-10 第 8 轮）

`recon/probe-city-middleware.py` 给东莞/汕头/韶关/河源/中山/珠海/佛山 都打了
`广东hdjlpt` 指纹，但 `probe-gd-city-hdjlpt.py` 判它们「死」——
理由是落地页 `/hdjlpt/published?via=pc` 返回 **403**。

**但 403 ≠ 不存在。** 惠州就是这么被误判的：它的 hdjlpt 在**独立域名**
`www.hzhmsb.cn`，主站上根本找不到。所以本轮做三件事：

1. **区分 403 的成因**：直接打 / 先访问首页种 Cookie 再打 / 换 UA 打 —— 三次对比。
   若「种 Cookie 后 200」⇒ 是 WAF 要求会话，不是没部署。
2. **在首页 HTML 里找真实互动入口**（`hd` 字段只是猜的路径）。
3. **对候选入口再实测**：是不是 hdjlpt 同款（有 XSRF-TOKEN cookie + pubList 可用）。

⚠ 输出由 Python 自己写文件 —— 不经 PowerShell 管道（会被重编码成乱码）。
只读，不落盘到 data/。
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx                                                          # noqa: E402

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

#: 带 hdjlpt 指纹但被 403 判死的市（+ 中山，它当时没 403 却也没采到）
TARGETS = [
    ("广东·东莞", "https://www.dongguan.gov.cn"),
    ("广东·汕头", "https://www.shantou.gov.cn"),
    ("广东·韶关", "https://www.sg.gov.cn"),
    ("广东·中山", "https://www.zs.gov.cn"),
    ("广东·佛山", "https://www.foshan.gov.cn"),
    ("广东·河源", "https://www.heyuan.gov.cn"),
    ("广东·珠海", "https://www.zhuhai.gov.cn"),
    ("广东·梅州", "https://www.mz.gov.cn"),
]

#: 要试的 hdjlpt 路径（相对 base）
PATHS = [
    "/hdjlpt/published?via=pc",
    "/hdjlpt",
    "/hdjlpt/letter/pubList",
]

#: 首页 HTML 里找互动入口用的关键词
KW = ("hdjlpt", "zmhd", "hd/", "hdjl", "互动", "留言", "信箱", "咨询", "民意",
      "12345", "问政", "网上信访", "我要写信")


def _hd_links(html: str, base: str) -> list[str]:
    """从首页 HTML 里挑出「疑似互动栏目」的链接。"""
    hits: list[str] = []
    for m in re.finditer(r'href=["\']([^"\']+)["\']', html, re.I):
        href = m.group(1).strip()
        if not href or href.startswith(("#", "javascript:", "mailto:")):
            continue
        low = href.lower()
        if any(k.lower() in low for k in KW):
            if href.startswith("//"):
                href = "https:" + href
            elif href.startswith("/"):
                href = base + href
            if href not in hits:
                hits.append(href)
    # 也把 JS 里出现的 hdjlpt 路径捞出来
    for m in re.finditer(r'["\'](/[A-Za-z0-9_\-/]*hdjlpt[A-Za-z0-9_\-/]*)["\']', html, re.I):
        p = base + m.group(1)
        if p not in hits:
            hits.append(p)
    return hits[:25]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    lines: list[str] = []

    def say(s: str = "") -> None:
        lines.append(s)

    for name, base in TARGETS:
        say(f"\n{'=' * 74}")
        say(f"{name}   {base}")
        say("=" * 74)
        with httpx.Client(timeout=25, follow_redirects=True,
                          trust_env=False, verify=False) as c:
            # ---- A) 先打落地页（冷会话）----
            for p in PATHS:
                try:
                    r = c.get(base + p, headers={"User-Agent": UA})
                    ct = r.headers.get("content-type", "")[:40]
                    sc = [ck.name for ck in r.cookies.jar]
                    say(f"  [冷] {p:34s} HTTP {r.status_code} len={len(r.text or '')} "
                        f"ct={ct} cookies={sc}")
                except Exception as e:                                  # noqa: BLE001
                    say(f"  [冷] {p:34s} FAIL {type(e).__name__}: {str(e)[:60]}")

            # ---- B) 先访问首页（种 Cookie）再打落地页 ----
            try:
                r0 = c.get(base + "/", headers={
                    "User-Agent": UA,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9",
                    "Upgrade-Insecure-Requests": "1",
                })
                say(f"  [首页] HTTP {r0.status_code} len={len(r0.text or '')} "
                    f"cookies={[ck.name for ck in r0.cookies.jar]}")
                home = r0.text or ""
            except Exception as e:                                      # noqa: BLE001
                say(f"  [首页] FAIL {type(e).__name__}: {str(e)[:60]}")
                home = ""

            for p in PATHS[:1] + PATHS[2:]:
                try:
                    r = c.get(base + p, headers={
                        "User-Agent": UA, "Referer": base + "/",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                        "Accept-Language": "zh-CN,zh;q=0.9",
                    })
                    ct = r.headers.get("content-type", "")[:40]
                    say(f"  [温] {p:34s} HTTP {r.status_code} len={len(r.text or '')} "
                        f"ct={ct} cookies={[ck.name for ck in r.cookies.jar]}")
                except Exception as e:                                  # noqa: BLE001
                    say(f"  [温] {p:34s} FAIL {type(e).__name__}: {str(e)[:60]}")

            # ---- C) 首页里的互动入口 ----
            if home:
                links = _hd_links(home, base)
                say(f"  ---- 首页疑似互动入口 {len(links)} 条 ----")
                for l in links[:20]:
                    say(f"    {l[:120]}")

    text = "\n".join(lines) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"written: {args.out} ({len(lines)} lines)")
    else:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
