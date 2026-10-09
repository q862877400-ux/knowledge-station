"""把「已知域名的地级市门户」**按中间件归类** —— 为「一个适配器覆盖一片」做准备。

## 为什么

`recon/build-city-domains.py` 产出了 city→域名 映射（拼音假设实测命中 ~89%）。
但**域名 ≠ 可采** —— 要采还得知道每个市用哪套 CMS / 哪个列表接口。

逐市写适配器是 O(n)；**按中间件归类后是 O(中间件数)** ——
这正是 GOAL.md 说的「**找到一个接口 = 找到一片站点**」。

## 本探针干什么

对每个市门户：
1. 抓首页（+ 常见互动栏目路径），**按指纹归类**中间件
2. 抽出「互动 / 留言 / 信箱 / 12345 / 咨询」类栏目的**入口 URL**
3. 把结果按中间件分组输出 ⇒ 下一轮**只挑最大的那一组**写适配器

## 指纹表（沿用 `REUSE-FOR-ANNOUNCEMENTS.md` §2 + 本仓已实测的）

| 中间件 | 指纹 |
|---|---|
| IGI | `openGovmsgbox` / `/IGI/` |
| TRS WAS5 | `urltype=tree.TreeTempUrl` / `wbtreeid=` |
| jact | `/jact/front/` / `sysid=\d+` |
| 龙讯科技 | `data-setting=` + `labelName` / `/site/label/` |
| EWB（河北 webBuilder） | `/EWB-FRONT/` / `siteGuid` |
| Hanweb/万户 | `/u/search/ajaxlist` |
| 湖南统一平台 | `hd.hunan.gov.cn` |
| 广东 hdjlpt | `/hdjlpt/letter/` |
| 瑞数 WAF | HTTP 412 + `$_ts.cd` |

只写 `recon/`，不碰 `data/`。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
import httpx                                                          # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "city-middleware.json"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
H = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Upgrade-Insecure-Requests": "1",
}

#: (中间件名, 指纹正则列表) —— 命中任一即算
FINGERPRINTS = [
    ("IGI", (r"openGovmsgbox", r"/IGI/")),
    ("WAS5", (r"urltype=tree\.TreeTempUrl", r"wbtreeid=", r"/was5/")),
    ("jact", (r"/jact/front/", r"sysid=\d+")),
    ("龙讯", (r"data-setting=", r"/site/label/", r"labelName:")),
    ("EWB", (r"/EWB-FRONT/", r"siteGuid")),
    ("Hanweb", (r"/u/search/ajaxlist",)),
    ("湖南统一平台", (r"hd\.hunan\.gov\.cn",)),
    ("广东hdjlpt", (r"/hdjlpt/",)),
    ("瑞数WAF", (r"\$_ts\.cd", r"\$_ss\.cd")),
]

#: 常见互动栏目路径（依次试）
HD_PATHS = ("", "/zmhd/", "/zmhd/index.html", "/hdjl/", "/szxx/", "/12345/",
            "/hzjl/", "/ldxx/")

#: 栏目名关键词
HD_WORDS = ("互动", "留言", "信箱", "12345", "咨询", "建议", "投诉", "政民",
            "问政", "民声", "热线", "回应")

A_RE = re.compile(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.S)
TAG_RE = re.compile(r"<[^>]+>")


def _text(frag: str) -> str:
    return re.sub(r"\s+", "", TAG_RE.sub("", frag or ""))


def classify(text: str) -> "list[str]":
    hits = []
    for name, pats in FINGERPRINTS:
        if any(re.search(p, text, re.I) for p in pats):
            hits.append(name)
    return hits


def find_hd_link(base: str, text: str) -> str:
    """从页面里抽「互动类」栏目入口（绝对化）。"""
    for m in A_RE.finditer(text):
        href, frag = m.group(1), _text(m.group(2))
        if not frag or len(frag) > 16:
            continue
        if any(w in frag for w in HD_WORDS):
            if href.startswith("http"):
                return href
            try:
                return str(httpx.URL(base).join(href))
            except Exception:                                           # noqa: BLE001
                continue
    return ""


def work(item: "tuple[str, dict]") -> "tuple[str, dict]":
    city, info = item
    base = info.get("url") or f"https://www.{info.get('host', '')}.gov.cn/"
    out = {"province": info.get("province", ""), "base": base,
           "middleware": [], "hd": "", "status": 0, "note": ""}
    with httpx.Client(headers=H, follow_redirects=True,
                      trust_env=False, verify=False) as c:
        seen = ""
        for p in HD_PATHS:
            url = base.rstrip("/") + p if p else base
            try:
                r = c.get(url, timeout=12)
            except Exception as e:                                      # noqa: BLE001
                out["note"] = f"{type(e).__name__}"
                continue
            t = r.text or ""
            if r.status_code == 200 and len(t) > 500:
                out["status"] = 200
                seen = (seen + "\n" + t)[:400_000]
                mw = classify(t)
                for m in mw:
                    if m not in out["middleware"]:
                        out["middleware"].append(m)
                if not out["hd"]:
                    out["hd"] = find_hd_link(str(r.url), t)
            elif r.status_code in (403, 412):
                out["note"] = f"HTTP {r.status_code}（疑似 WAF）"
                break
    if not seen:
        out["note"] = out["note"] or "不可达"
    return city, out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--domains", default=str(HERE / "city-domains.json"))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    src = Path(args.domains)
    if not src.exists():
        print(f"❌ 找不到 {src}（先跑 build-city-domains.py）", file=sys.stderr)
        return 1
    domains = json.loads(src.read_text(encoding="utf-8"))
    print(f"待测门户 {len(domains)} 个", flush=True)

    result: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        for i, (city, info) in enumerate(ex.map(work, list(domains.items())), 1):
            result[city] = info
            if i % 25 == 0:
                print(f"  进度 {i}/{len(domains)}", flush=True)

    Path(args.out).write_text(
        json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True),
        encoding="utf-8")

    # ---- 汇总：按中间件分组（下一轮挑最大的那组写适配器） ----------------
    from collections import Counter
    groups: Counter = Counter()
    for info in result.values():
        if info["middleware"]:
            groups["+".join(sorted(info["middleware"]))] += 1
        else:
            groups["（未识别）"] += 1
    print("\n按中间件分组：")
    for name, n in groups.most_common():
        print(f"  {n:4d}  {name}")
    n_hd = sum(1 for v in result.values() if v["hd"])
    print(f"\n找到互动栏目入口：{n_hd}/{len(result)}")
    print(f"→ {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
