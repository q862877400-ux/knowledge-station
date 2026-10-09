"""探针：三市「互动/咨询」栏目的**真实列表结构** —— 找可复用的中间件。

## 背景（数据驱动，不是猜）

`recon/probe-igi-context.py` 用**实测**推翻了「洛阳/芜湖/宜昌 用 IGI」：
三市 IGI 接口全部 **HTTP 404**，它们的 `siteId` 属于别的 CMS：
 · 洛阳 `siteId=4103000021` → `t.ly.gov.cn/openview/api/view/selectsiteopen`（内容开放 API）
 · 芜湖 `siteId=6787231` → 龙讯科技 CMS 的 `data-setting`（**页面里带 `messageBoardInfoList`**）
 · 宜昌 `siteId=54` → `hubei.gov.cn/zxjy/zxft`（省级在线访谈）

## 本探针要回答的问题

**芜湖的「政民互动」是不是一套可复用的 CMS 接口？**（龙讯 CMS 装机量很大，
若能打通 ⇒ 一次覆盖一片，正是 GOAL.md 说的「找到一个就等于找到一片」）

对每个市：抓互动栏目页 → dump
 1. 含「咨询/留言/信箱/列表/详情」的链接（判断是服务端渲染还是 JS）
 2. `data-setting` / `labelName` / `file:` 这类 CMS 配置（找列表接口名）
 3. `api` / `.json` / `.do` / `/label/` 端点候选
并**实测**候选端点是否返回数据。

⚠ 输出由 Python 自己写文件（`--out`）—— 不经 PowerShell 管道（会被重编码成乱码）。
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
H = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Upgrade-Insecure-Requests": "1",
}

#: (市名, 互动栏目页)
PAGES = [
    ("河南·洛阳", "https://www.ly.gov.cn/zmhd/wszx/"),
    ("安徽·芜湖", "https://www.wuhu.gov.cn/zmhd/index.html"),
    ("湖北·宜昌", "http://www.yichang.gov.cn/Szrx/"),
]

#: 想看的端点候选（相对 base）
END_CANDIDATES = (
    "/site/label/8888",
    "/c1/wuhu/messageBoardInfoList-wh-01.json",
    "/c1/wuhu/messageBoardInfoList-wh-01.js",
    "/c1/wuhu/messageBoardInfoList-wh-01",
)


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
            say(f"\n{'=' * 70}")
            say(f"{name}  {url}")
            say("=" * 70)
            try:
                r = c.get(url)
            except Exception as e:                                    # noqa: BLE001
                say(f"  FAIL {type(e).__name__}: {str(e)[:60]}")
                continue
            t = r.text or ""
            say(f"  HTTP {r.status_code} len={len(t)} final={r.url}")

            # 1) 条目链接（含 id 参数的，通常是明细）
            detail = re.findall(r'href=["\']([^"\']*(?:detail|content|show|info|id=)[^"\']*)["\']',
                                t, re.I)
            say(f"  ---- 疑似明细链接 {len(set(detail))} 条 ----")
            for d in sorted(set(detail))[:8]:
                say(f"    {d[:110]}")

            # 2) CMS 配置：data-setting / labelName / file:
            ds = re.findall(r'data-setting="([^"]{10,300})"', t)
            if ds:
                say(f"  ---- data-setting {len(ds)} 条 ----")
                for d in ds[:10]:
                    say(f"    {re.sub(chr(92) + 's+', ' ', d)[:160]}")
            lab = re.findall(r"labelName\s*[:=]\s*['\"]?([A-Za-z_]{4,40})", t)
            if lab:
                say(f"  ---- labelName: {sorted(set(lab))[:12]}")
            fil = re.findall(r"file\s*:\s*['\"]([^'\"]{4,80})['\"]", t)
            if fil:
                say(f"  ---- file: {sorted(set(fil))[:12]}")

            # 3) 端点候选
            api = re.findall(r'["\'](/[A-Za-z0-9_\-/]*(?:api|label|list|search|json)[A-Za-z0-9_\-/]*)["\']',
                             t, re.I)
            say(f"  ---- 端点候选 {len(set(api))} 条 ----")
            for a in sorted(set(api))[:12]:
                say(f"    {a[:110]}")

            # 4) 实测（只对芜湖试，避免无谓请求）
            if "wuhu" in url:
                say("  ---- 实测端点 ----")
                origin = "https://www.wuhu.gov.cn"
                for ep in END_CANDIDATES:
                    try:
                        rr = c.get(origin + ep, headers={"Referer": url})
                        body = rr.text or ""
                        say(f"    {ep:58s} HTTP {rr.status_code} len={len(body)} "
                            f"ct={rr.headers.get('content-type', '')[:30]}")
                        say(f"      head: {re.sub(chr(92) + 's+', ' ', body[:180])}")
                    except Exception as e:                                # noqa: BLE001
                        say(f"    {ep:58s} FAIL {type(e).__name__}")

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
