"""探针：从**省政府门户**里挖出「地市门户」的链接 —— 建 city→域名 映射。

## 为什么需要它（M4 的根阻塞）

`coverage-report.py --missing-cities` 给出**193 个零记录地级市**，
但**要采就得先知道它们的域名**。全仓没有一张完整的 city→域名 表
（只有零散的 `igi-portal-sweep-city2.json` 云南几个市、`gd-dept-domains-full.json` 广东**厅局**）。

## 思路

省政府门户的「地市导航 / 市县之窗 / 友情链接」栏目通常列出**全部地市门户**。
⇒ 抓省门户页 + 常见导航路径，抽出 `<a>`，**用该省的地级市名单去匹配链接文本**。

## 判定（不接受「抽到个链接就算」）

1. 链接文本里含市名（或市名去「市」）
2. 域名为 `*.gov.cn` 且**不是**省级门户自身
3. **实测**该域名是否可达（HTTP 200）—— 写进结果，不猜

⚠ 输出由 Python 自己写文件（`--out`），不经 PowerShell 管道（会重编码成乱码）。
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

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from regions import PROVINCE_CITIES                                   # noqa: E402

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
H = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Upgrade-Insecure-Requests": "1",
}

#: 省名 → (省门户根, 可能的「地市导航」路径)
PROVINCES = [
    ("广东省", "https://www.gd.gov.cn",
     ["/", "/gdsz/", "/zwgk/", "/sq/"]),
    ("河南省", "https://www.henan.gov.cn",
     ["/", "/dts/", "/hngk/"]),
    ("安徽省", "https://www.ah.gov.cn",
     ["/", "/ahsz/", "/szf/"]),
    ("云南省", "https://www.yn.gov.cn",
     ["/", "/yngk/", "/yx/"]),
    ("湖南省", "https://www.hunan.gov.cn",
     ["/", "/hnsz/", "/dts/"]),
]

A_RE = re.compile(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.S)
TAG_RE = re.compile(r"<[^>]+>")
HOST_RE = re.compile(r"^[a-z0-9.\-]+$")


def _text(frag: str) -> str:
    return re.sub(r"\s+", "", TAG_RE.sub("", frag or ""))


def _host(url: str) -> str:
    m = re.match(r"https?://([^/]+)", url, re.I)
    return (m.group(1) if m else "").lower().lstrip("www.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    ap.add_argument("--dump", action="store_true",
                    help="诊断模式：打印页面上所有 gov.cn 主机 + 市名出现的上下文")
    args = ap.parse_args()

    L: list[str] = []

    def say(s: str = "") -> None:
        L.append(s)

    with httpx.Client(timeout=25, headers=H, follow_redirects=True,
                      trust_env=False, verify=False) as c:
        for prov, root, paths in PROVINCES:
            cities = PROVINCE_CITIES.get(prov, [])
            # 市名 → 匹配用的短名（去「市」；自治州/地区取前 2 字）
            short = {}
            for city in cities:
                base = city.rstrip("市")
                for suf in ("回族自治州", "蒙古族藏族自治州", "藏族自治州",
                            "傣族景颇族自治州", "苗族侗族自治州",
                            "布依族苗族自治州", "哈尼族彝族自治州",
                            "彝族自治州", "白族自治州", "自治州",
                            "地区", "盟"):
                    if base.endswith(suf):
                        base = base[: -len(suf)]
                        break
                short[city] = base[:2] if len(base) > 3 else base

            say("=" * 72)
            say(f"{prov}  共 {len(cities)} 个地级行政区   门户 {root}")
            say("=" * 72)
            if args.dump:
                try:
                    r = c.get(root)
                    t = r.text or ""
                except Exception as e:                                # noqa: BLE001
                    say(f"  FAIL {type(e).__name__}")
                    continue
                hosts: dict[str, int] = {}
                for m in A_RE.finditer(t):
                    h = _host(m.group(1))
                    if h:
                        hosts[h] = hosts.get(h, 0) + 1
                say(f"  ---- 页面上的主机（共 {len(hosts)}）----")
                for h, n in sorted(hosts.items(), key=lambda kv: -kv[1])[:30]:
                    say(f"     {n:4d}  {h}")
                say("  ---- 市名出现处（取前 3 个市各 2 处上下文）----")
                shown = 0
                for city in cities[:3]:
                    base = city.rstrip("市")
                    for mm in list(re.finditer(re.escape(base), t))[:2]:
                        a = max(0, mm.start() - 90)
                        b = min(len(t), mm.end() + 90)
                        say(f"     [{city}] …{re.sub(chr(92) + 's+', ' ', t[a:b])}…")
                        shown += 1
                say(f"  （共展示 {shown} 处）")
                say("")
                continue

            found: dict[str, str] = {}
            for path in paths:
                url = root + path
                try:
                    r = c.get(url)
                except Exception as e:                                # noqa: BLE001
                    say(f"  {url:44s} FAIL {type(e).__name__}")
                    continue
                t = r.text or ""
                say(f"  {url:44s} HTTP {r.status_code} len={len(t)}")
                if r.status_code != 200:
                    continue
                selfhost = _host(str(r.url))
                for m in A_RE.finditer(t):
                    href, frag = m.group(1), _text(m.group(2))
                    if not frag or len(frag) > 8:
                        continue
                    for city, s in short.items():
                        if city in found:
                            continue
                        if frag == city or frag == s or frag == city.rstrip("市"):
                            h = _host(href)
                            if not h or h == selfhost or "gov.cn" not in h:
                                continue
                            found[city] = href if href.startswith("http") else \
                                str(httpx.URL(url).join(href))
            say(f"  ⇒ 从导航页抽到 {len(found)} 个市链接：")
            for city, u in sorted(found.items()):
                say(f"     {city:12s} {u[:80]}")

            # 实测可达性
            if found:
                say("  ---- 实测可达性 ----")
                ok = 0
                for city, u in sorted(found.items()):
                    try:
                        rr = c.get(u, timeout=12)
                        good = rr.status_code == 200
                        ok += 1 if good else 0
                        say(f"     {city:12s} HTTP {rr.status_code} "
                            f"{'✅' if good else ''}  final={rr.url}")
                    except Exception as e:                            # noqa: BLE001
                        say(f"     {city:12s} FAIL {type(e).__name__}")
                say(f"  ⇒ 可达 {ok}/{len(found)}")
            say("")

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
