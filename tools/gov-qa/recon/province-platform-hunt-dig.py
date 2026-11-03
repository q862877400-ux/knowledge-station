"""24 省互动平台重探 —— 阶段二：对指定互动栏目页深挖接口。

给定若干入口 URL（来自 stage1 的 home_links / hd_paths.links，或手工指定），
逐页抓取并：
  1. 挖中间件指纹（was5 / igi / hdjlpt / mailList2ie / channelid / api）；
  2. 挖内联 <script> 里含接口关键词的片段；
  3. 挖列表页里的 .js 文件链接并抓取，继续挖接口；
  4. 挖站内「互动」子栏目链接（下一层）。

用法：
  python recon/province-platform-hunt-dig.py --out stage2-ningxia.json \
      "宁夏|https://www.nx.gov.cn/zmhd/" "宁夏|https://www.nx.gov.cn/hdjl/"
产出：--out 指定的 json 文件（默认 stage2.json）
⚠ 每请求间隔 1.6s；遇 403/412 停该 URL 的后续。
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
PAUSE = 1.6

KEYWORDS = ("互动", "问答", "常见问题", "留言", "咨询", "回应", "选登",
            "信箱", "公众参与", "政民", "投诉", "建言", "在线访谈", "知识库")
NOISE = ("征集调查", "调查征集", "意见征集", "直播", "视频", "访谈预告")

A_HREF_RE = re.compile(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<script[^>]*>(.*?)</script>", re.S | re.I)
JS_SRC_RE = re.compile(r'<script[^>]+src="([^"]+\.js[^"]*)"', re.I)

HINT_RE = re.compile(
    r"(channelid|was5|leaveWord|interactionParams|mailList2ie|listGovmsgboxs|"
    r"viewGovmsgbox|pubList|/api/|/ajax/|/interface/|/service/|pageSize|pageNo|"
    r"currentPage|pageIndex|url\s*[:=]|ajax\()", re.I)
API_RE = re.compile(
    r"[\"']([^\"'\s]{4,140}(?:/api/|/ajax/|/interface/|/service/|/IGI/|mailList|"
    r"pubList|listGov|\.do|\.json)[^\"'\s]{0,60})[\"']", re.I)
FP = {
    "was5": re.compile(r"was5/web/search|leaveWordParams|interactionParams|ajaxCjwt", re.I),
    "igi": re.compile(r"/IGI/|listGovmsgboxs|viewGovmsgbox|govmsgbox", re.I),
    "hdjlpt": re.compile(r"hdjlpt|letter/pubList", re.I),
    "mailList2ie": re.compile(r"mailList2ie", re.I),
}


def _get(cli, url):
    try:
        return cli.get(url, timeout=20)
    except Exception as e:                                              # noqa: BLE001
        return e


def fp_of(html: str) -> dict:
    d = {}
    for name, rx in FP.items():
        if rx.search(html or ""):
            d[name] = True
    cid = re.findall(r"channelid['\"]?\s*[:=]\s*['\"]?(\d{3,8})", html or "", re.I)
    if cid:
        d["channelid"] = list(dict.fromkeys(cid))[:8]
    return d


def links_of(html: str, base: str) -> list[dict]:
    out, seen = [], set()
    for href, inner in A_HREF_RE.findall(html or ""):
        t = TAG_RE.sub("", inner).strip()
        if 2 <= len(t) <= 26 and any(k in t for k in KEYWORDS) and not any(n in t for n in NOISE):
            full = urljoin(base, href.strip())
            if full.startswith("http") and full not in seen:
                seen.add(full)
                out.append({"url": full, "text": t})
    return out[:15]


def dig(cli, name: str, url: str, depth: int) -> dict:
    rec = {"name": name, "url": url, "depth": depth}
    r = _get(cli, url)
    time.sleep(PAUSE)
    if isinstance(r, Exception):
        rec["error"] = type(r).__name__
        return rec
    rec["status"] = r.status_code
    html = r.text or ""
    rec["len"] = len(html)
    if r.status_code in (403, 412):
        rec["stopped"] = "403/412"
        return rec
    if r.status_code != 200:
        return rec
    base = str(getattr(r, "url", url))
    rec["fp"] = fp_of(html)
    rec["api_hints"] = list(dict.fromkeys(API_RE.findall(html)))[:12]
    rec["script_blocks"] = [s[:1200] for s in SCRIPT_RE.findall(html)
                            if HINT_RE.search(s)][:4]
    rec["hd_links"] = links_of(html, base)
    # 挖外链 JS
    js = []
    for src in JS_SRC_RE.findall(html):
        full = urljoin(base, src)
        if full.startswith("http"):
            js.append(full)
    rec["js_files"] = list(dict.fromkeys(js))[:6]
    if depth > 0:
        rec["js_mined"] = []
        for ju in rec["js_files"][:3]:
            jr = _get(cli, ju)
            time.sleep(PAUSE)
            if isinstance(jr, Exception) or getattr(jr, "status_code", None) != 200:
                continue
            jt = jr.text or ""
            rec["js_mined"].append({
                "url": ju,
                "fp": fp_of(jt),
                "api_hints": list(dict.fromkeys(API_RE.findall(jt)))[:15],
            })
    return rec


def main() -> int:
    import httpx

    args = sys.argv[1:]
    out_path = HERE / "stage2.json"
    items: list[tuple[str, str]] = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--out":
            out_path = HERE / args[i + 1]
            i += 2
            continue
        if "|" in a:
            n, u = a.split("|", 1)
            items.append((n, u))
        i += 1
    if not items:
        print("用法：--out out.json '省|URL' ...")
        return 2

    results = []
    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=20, follow_redirects=True) as cli:
        for n, u in items:
            print(f"[dig] {n} {u}", flush=True)
            rec = dig(cli, n, u, depth=1)
            results.append(rec)
            print(f"      → {rec.get('status', rec.get('error'))} len={rec.get('len')} "
                  f"fp={rec.get('fp')} api={rec.get('api_hints', [])[:3]}", flush=True)
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[dig] 证据已写 {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
