"""通用「厅局互动栏目」挖掘：对给定站点找互动入口 → 挖列表接口线索。

用法（默认三家可达的直辖市/省级生态环境部门）：
    python recon/dept-hd-dig.py [站点根 URL ...]
产出：recon/dept-hd-dig.json（每站的入口页、接口线索、内联 JS 片段）。

⚠ 只做检索与证据留存，不做批量抓取；每请求间隔 2s。
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

sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import UA  # noqa: E402

DEFAULT_SITES = [
    ("四川省生态环境厅", "https://sthjt.sc.gov.cn/"),
    ("北京市生态环境局", "https://sthjj.beijing.gov.cn/"),
    ("上海市生态环境局", "https://sthj.sh.gov.cn/"),
    ("贵州省生态环境厅", "https://sthj.guizhou.gov.cn/"),
]

KEY = ("互动", "问答", "留言", "咨询", "常见问题", "回应", "选登", "信箱", "公众参与")
API_RE = re.compile(r"[\"']([^\"']{0,80}(?:/api/|/ajax/|\.json|/list|/search)[^\"']{0,60})[\"']", re.I)
HINT_RE = re.compile(r"(channelid|was5|leaveWord|interactionParams|pageSize|pageNo|currentPage)", re.I)
A_HREF_RE = re.compile(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<script[^>]*>(.*?)</script>", re.S | re.I)


def dig(c, url: str, depth: int = 1) -> dict:
    rec: dict = {"url": url}
    try:
        r = c.get(url)
    except Exception as e:                                                  # noqa: BLE001
        return {"url": url, "error": type(e).__name__}
    rec["status"] = r.status_code
    rec["len"] = len(r.text or "")
    if r.status_code != 200:
        return rec
    html = r.text or ""
    base = str(r.url)
    links = []
    for href, inner in A_HREF_RE.findall(html):
        t = TAG_RE.sub("", inner).strip()
        if any(k in t for k in KEY) and 2 <= len(t) <= 18:
            full = urljoin(base, href)
            if full.startswith("http") and full not in [x[0] for x in links]:
                links.append((full, t))
    rec["hd_links"] = links[:10]
    rec["api_hints"] = list(dict.fromkeys(API_RE.findall(html)))[:10]
    blocks = [s[:900] for s in SCRIPT_RE.findall(html) if HINT_RE.search(s)]
    rec["script_blocks"] = blocks[:3]
    if depth > 0:
        rec["sub"] = []
        for full, t in links[:3]:
            time.sleep(2)
            sub = dig(c, full, depth=0)
            sub["text"] = t
            rec["sub"].append(sub)
    return rec


def main() -> int:
    import httpx

    args = sys.argv[1:]
    sites = ([(a, a) for a in args] if args else DEFAULT_SITES)
    out = []
    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=20, follow_redirects=True) as c:
        for name, url in sites:
            print(f"[dig] {name} {url}", flush=True)
            rec = dig(c, url)
            rec["name"] = name
            out.append(rec)
            print(f"      → {rec.get('status', rec.get('error'))} "
                  f"links={len(rec.get('hd_links', []))} "
                  f"api={rec.get('api_hints', [])[:3]}", flush=True)
            time.sleep(2)
    (HERE / "dept-hd-dig.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[dig] 证据已写 recon/dept-hd-dig.json")
    return 0


if __name__ == "__main__":
    main()
