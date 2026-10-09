"""探针：把「洛阳 / 芜湖 / 宜昌」页面里 **IGI 的真实上下文** dump 出来。

## 为什么要重做

上一版 `probe-igi-cities.py` 只抓了 `siteId=NNN` 的**数字**，得到
洛阳 `4103000021` / 芜湖 `6787231,6787891` / 宜昌 `54` —— 但**没有验证**这些是不是
IGI 的 siteId。⚠ 洛阳那个数 **恰好等于它的行政区划代码 410300**，
极可能是别的 CMS（`siteId` 这个词被滥用），**不是 IGI**。

GOAL.md 硬约束 #7：「否定性结论必须用数据证伪」/ #6：「判死前必须实测」。
⇒ 本探针**只看上下文、不猜**：把含 `igi` / `siteId` / `openGovmsgbox` 的片段
连同前后 120 字符一起打印，再**实测 IGI 列表接口**是否真返回 `datas.data`。

## 关键工程细节

**输出由 Python 自己写文件**（`--out`），不经 PowerShell 管道 ——
PowerShell 的 `Out-File` 会把 UTF-8 当 GBK 再编码一次 ⇒ 中文全成乱码（上一轮踩过）。

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

SITES = [
    ("河南·洛阳", "https://www.ly.gov.cn"),
    ("安徽·芜湖", "https://www.wuhu.gov.cn"),
    ("湖北·宜昌", "https://www.yichang.gov.cn"),
]

H = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Upgrade-Insecure-Requests": "1",
}

#: 想看到上下文的特征
CTX_PATTERNS = (
    re.compile(r"igi", re.I),
    re.compile(r"siteId\s*[:=]", re.I),
    re.compile(r"openGovmsgbox", re.I),
    re.compile(r"msgbox", re.I),
)

#: IGI 通用列表接口（`_igi_common.LIST_TPL`）
IGI_LIST = ("{base}/nbhd/openGovmsgbox.do?method=listGovmsgboxs"
            "&siteId={sid}&order=1&appId={aid}&pageIndex=1&pageSize=20")


def _ctx(text: str, m: re.Match, span: int = 120) -> str:
    a = max(0, m.start() - span)
    b = min(len(text), m.end() + span)
    return re.sub(r"\s+", " ", text[a:b])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="", help="把报告写到该文件（UTF-8），默认 stdout")
    args = ap.parse_args()

    lines: list[str] = []

    def say(s: str = "") -> None:
        lines.append(s)

    with httpx.Client(timeout=25, headers=H, follow_redirects=True,
                      trust_env=False, verify=False) as c:
        for name, base in SITES:
            say(f"\n{'=' * 70}")
            say(f"{name}  {base}")
            say("=" * 70)
            try:
                r = c.get(base)
            except Exception as e:                                    # noqa: BLE001
                say(f"  FAIL {type(e).__name__}: {str(e)[:60]}")
                continue
            t = r.text or ""
            say(f"  HTTP {r.status_code} len={len(t)}  final={r.url}")

            # ---- 1) IGI / siteId 上下文（去重，最多 12 条） -----------------
            seen: set[str] = set()
            shown = 0
            for pat in CTX_PATTERNS:
                for m in pat.finditer(t):
                    frag = _ctx(t, m)
                    key = frag[100:160]
                    if key in seen:
                        continue
                    seen.add(key)
                    say(f"    [ctx] …{frag}…")
                    shown += 1
                    if shown >= 12:
                        break
                if shown >= 12:
                    break
            if shown == 0:
                say("    （页面里没有任何 igi / siteId / msgbox 字样）")

            # ---- 2) 互动类栏目链接 -----------------------------------------
            links: list[tuple[str, str]] = []
            for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                                 t, re.S):
                href = m.group(1)
                txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", m.group(2))).strip()
                if txt and any(k in txt for k in
                               ("互动", "信箱", "留言", "12345", "咨询", "建议", "投诉")):
                    links.append((txt[:24], href))
            say(f"  ---- 互动链接 {len(links)} 条 ----")
            for txt, href in links[:10]:
                say(f"    {txt:26s} {href[:100]}")

            # ---- 3) 实测 IGI 列表接口（用页面里出现的数字当 siteId 试） -----
            cand_ids = sorted(set(re.findall(r"siteId\s*[:=]\s*['\"]?(\d+)", t, re.I)))
            if cand_ids:
                say(f"  ---- 实测 IGI 接口（siteId 候选 {cand_ids[:6]}）----")
                for sid in cand_ids[:4]:
                    for aid in ("", "1"):
                        url = IGI_LIST.format(base=base, sid=sid, aid=aid)
                        try:
                            rr = c.get(url, headers={"Referer": base + "/"})
                            ok = False
                            n = 0
                            try:
                                j = rr.json()
                                rows = (j.get("datas") or {}).get("data") or []
                                n = len(rows)
                                ok = n > 0
                            except Exception:                             # noqa: BLE001
                                pass
                            say(f"    siteId={sid:12s} appId={aid or '-':2s} "
                                f"HTTP {rr.status_code} 行数={n} {'✅' if ok else ''}")
                        except Exception as e:                            # noqa: BLE001
                            say(f"    siteId={sid:12s} appId={aid or '-':2s} "
                                f"FAIL {type(e).__name__}")
            else:
                say("  （页面无 siteId，跳过 IGI 实测）")

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
