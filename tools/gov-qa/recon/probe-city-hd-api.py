r"""探针（通用）：给一批「互动栏目 URL」，dump 出**可能的列表接口**。

## 为什么需要它

`recon/probe-gd-city-hdjlpt.py` 实测：18 个带 `广东hdjlpt` 指纹的市里
**只有 8 个能采**，另 10 个 `/hdjlpt/published` 返回 404/502
⇒ 它们**没在自己域名下部署 hdjlpt**，互动栏目挂在别的系统上。

⇒ 要**逐个看它们的互动页到底调什么接口**。这个探针把这一步通用化：
输入 `{城市: 互动栏目 URL}`，输出每页的
 · `data-setting` / `labelName` / `file:`（CMS 配置，找列表接口名）
 · `.do` / `/api/` / `.json` / `/list` / `/label/` 端点候选
 · 含「留言/咨询/详情」的链接（判断服务端渲染还是 JS）

⚠ 输出由 Python 自己写文件（`--out`）—— 不经 PowerShell 管道（会被重编码）。
只读，不落盘到 data/。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx                                                          # noqa: E402

H = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Upgrade-Insecure-Requests": "1",
}

EP_RE = re.compile(r'["\'](/[A-Za-z0-9_\-/.]*(?:api|list|label|search|json|do|query)'
                   r'[A-Za-z0-9_\-/.]*)["\']', re.I)
A_RE = re.compile(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.S)
TAG_RE = re.compile(r"<[^>]+>")


def _t(f: str) -> str:
    return re.sub(r"\s+", "", TAG_RE.sub("", f or ""))


def dump_one(c: httpx.Client, city: str, url: str) -> "list[str]":
    L: list[str] = [f"\n{'=' * 70}", f"{city}  {url}", "=" * 70]
    try:
        r = c.get(url, timeout=20)
    except Exception as e:                                            # noqa: BLE001
        L.append(f"  FAIL {type(e).__name__}: {str(e)[:60]}")
        return L
    t = r.text or ""
    L.append(f"  HTTP {r.status_code} len={len(t)} final={r.url}")
    if r.status_code != 200:
        return L

    ds = re.findall(r'data-setting="([^"]{10,300})"', t)
    if ds:
        L.append(f"  ---- data-setting {len(ds)} 条 ----")
        for d in ds[:8]:
            L.append(f"    {re.sub(chr(92) + 's+', ' ', d)[:170]}")
    lab = re.findall(r"labelName\s*[:=]\s*['\"]?([A-Za-z_]{4,40})", t)
    if lab:
        L.append(f"  ---- labelName: {sorted(set(lab))[:12]}")
    fil = re.findall(r"file\s*:\s*['\"]([^'\"]{4,90})['\"]", t)
    if fil:
        L.append(f"  ---- file: {sorted(set(fil))[:12]}")

    eps = sorted(set(EP_RE.findall(t)))
    L.append(f"  ---- 端点候选 {len(eps)} 条 ----")
    for e in eps[:14]:
        L.append(f"    {e[:100]}")

    arts = sorted(set(re.findall(r'href=["\']([^"\']*(?:detail|content|show)[^"\']*)["\']',
                                 t, re.I)))
    L.append(f"  ---- 疑似明细链接 {len(arts)} 条 ----")
    for a in arts[:6]:
        L.append(f"    {a[:100]}")

    nav = [( _t(m.group(2)), m.group(1)) for m in A_RE.finditer(t)
           if _t(m.group(2)) and len(_t(m.group(2))) <= 14
           and any(w in _t(m.group(2)) for w in ("留言", "咨询", "建议", "投诉",
                                                 "互动", "信箱", "12345", "问政"))]
    L.append(f"  ---- 相关导航 {len(nav)} 条 ----")
    for txt, href in nav[:8]:
        L.append(f"    {txt:14s} {href[:90]}")
    return L


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", default="",
                    help="JSON：{城市: 互动栏目 URL}")
    ap.add_argument("--from-mw", default="",
                    help="改用 recon/city-middleware.json（配 --province 用 hd/base）")
    ap.add_argument("--province", default="", help="配合 --from-mw：只看该省")
    ap.add_argument("--exclude-keys", default="",
                    help="配合 --from-mw：排除这些**适配器 key**（已覆盖的市）")
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    if args.pages:
        pages = json.loads(Path(args.pages).read_text(encoding="utf-8"))
    elif args.from_mw:
        mw = json.loads(Path(args.from_mw).read_text(encoding="utf-8"))
        pages = {}
        for city, v in mw.items():
            if args.province and v.get("province") != args.province:
                continue
            pages[city] = v.get("hd") or v.get("base")
    else:
        print("❌ 需要 --pages 或 --from-mw", file=sys.stderr)
        return 1

    L: list[str] = []
    with httpx.Client(headers=H, follow_redirects=True, trust_env=False,
                      verify=False) as c:
        for city, url in sorted(pages.items()):
            L += dump_one(c, city, url)

    text = "\n".join(L) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"written: {args.out} ({len(L)} lines)")
    else:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
