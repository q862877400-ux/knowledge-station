"""探针：中山/河源 hdjlpt 模块在但 `pubList` total=0 —— 找它们**真正的**公开留言栏目。

（2026-10-10 第 8 轮）

## 已知（实测）
 · 中山/河源：`POST /hdjlpt/letter/pubList` → `errcode:0, total:0`
   （参数名正确 —— 对照组汕尾同参数下 total=27）⇒ **hdjlpt 这个模块的公开信箱是空的**
 · 惠州先例：主站的 hdjlpt 没数据，**真入口在独立域名 `www.hzhmsb.cn`**

⇒ hdjlpt 只是「互动交流平台」的**其中一个**子模块。同一个市还可能有：
  12345 平台 / 民意直通车 / 领导信箱 / 网上信访 / 问政平台 ……
本探针沿「首页 → 互动栏目页」**爬两层**，把所有疑似互动入口列出来并按域外/域内分组，
再对**域外**入口（如 `12345.zs.gov.cn`）单独标注 —— 那是最可能藏数据的地方。

⚠ 只读。输出由 Python 自己写文件（不经 PowerShell 管道）。
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx                                                          # noqa: E402

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
H = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Upgrade-Insecure-Requests": "1",
}

#: (名, 互动栏目页) —— 用 §8.1 探针已确认的真入口
PAGES = [
    ("广东·中山", "http://www.zs.gov.cn/zmhd/index.html"),
    ("广东·河源", "http://www.heyuan.gov.cn/zmhd/index.html"),
    ("广东·东莞", "https://www.dg.gov.cn/zmhd/index.html"),
    ("广东·韶关", "https://www.sg.gov.cn/hd/index.html"),
    ("广东·珠海", "https://www.zhuhai.gov.cn/hd/index.html"),
]

#: 互动关键词
KW = ("留言", "信箱", "咨询", "投诉", "12345", "问政", "民意", "互动", "信访",
      "诉求", "选登", "公开", "答复", "sjxx", "wszx", "zmhd", "hdjl", "appeal",
      "letter", "lyxd", "zjdc", "rdhy", "public", "order", "km")

#: 明确不是问答的（§8.1 教训）
NEG = ("访谈预告", "访谈计划", "ftjhyg", "ftyg", "ldjf", "简历", "直播", "图片",
       "征集调查", "民意征集", "立法", "意见征集", "在线访谈", "wqhg", "ftgj")


def _links(html: str, base: str) -> list[tuple[str, str]]:
    """返回 (href, 锚文本)。"""
    out: list[tuple[str, str]] = []
    for m in re.finditer(r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                         html, re.I | re.S):
        href, txt = m.group(1).strip(), re.sub(r"<[^>]+>", "", m.group(2))
        txt = re.sub(r"\s+", "", txt)[:40]
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        low = (href + txt).lower()
        if any(n.lower() in low for n in NEG):
            continue
        if any(k.lower() in low for k in KW):
            out.append((urljoin(base, href), txt))
    # 去重保序
    seen, uniq = set(), []
    for u, t in out:
        if u not in seen:
            seen.add(u)
            uniq.append((u, t))
    return uniq


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    lines: list[str] = []

    def say(s: str = "") -> None:
        lines.append(s)

    with httpx.Client(timeout=25, headers=H, follow_redirects=True,
                      trust_env=False, verify=False) as c:
        for name, url in PAGES:
            say(f"\n{'=' * 74}")
            say(f"{name}   {url}")
            say("=" * 74)
            try:
                r = c.get(url)
            except Exception as e:                                      # noqa: BLE001
                say(f"  FAIL {type(e).__name__}: {str(e)[:70]}")
                continue
            t = r.text or ""
            say(f"  HTTP {r.status_code} len={len(t)} final={r.url}")
            root = e = urlparse(str(r.url))
            root_dom = f"{e.scheme}://{e.netloc}"
            links = _links(t, root_dom)
            say(f"  ---- 疑似互动入口 {len(links)} 条 ----")
            for u, txt in links[:30]:
                mark = "  <== 域外" if urlparse(u).netloc and urlparse(u).netloc != e.netloc else ""
                say(f"    {txt[:16]:18s} {u[:104]}{mark}")

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
