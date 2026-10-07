"""探「问政四川」（wz.sc.gov.cn）—— 四川省统一问政平台，看有没有公开问答列表与接口。

线索来源：省级站普遍存在"全省统一互动平台"（湖南模式已验证）；
四川的对应物是问政四川（省委省政府主办）。
本脚本：首页可达性 → 找问答列表链接 → 挖内联 JS 里的接口线索。
"""
from __future__ import annotations

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

ENTRIES = [
    "https://wz.sc.gov.cn/",
    "https://wz.sc.gov.cn/wzsc/",
    "http://wz.sc.gov.cn/",
]
KEY = ("互动", "问答", "留言", "问政", "回复", "选登", "咨询")
API_RE = re.compile(r"[\"']([^\"']*(?:/api/|ajax|json|list)[^\"']*)[\"']", re.I)
A_HREF_RE = re.compile(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")


def main() -> int:
    import httpx

    out = []
    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=20, follow_redirects=True) as c:
        for url in ENTRIES:
            rec = {"url": url}
            try:
                r = c.get(url)
                rec["status"] = r.status_code
                rec["final"] = str(r.url)
                html = r.text or ""
                rec["len"] = len(html)
                if r.status_code == 200 and "html" in r.headers.get("content-type", ""):
                    links = []
                    for href, inner in A_HREF_RE.findall(html):
                        t = TAG_RE.sub("", inner).strip()
                        if any(k in t for k in KEY) and 2 <= len(t) <= 16:
                            full = urljoin(str(r.url), href)
                            if full.startswith("http") and full not in [x[0] for x in links]:
                                links.append((full, t))
                    rec["links"] = links[:12]
                    rec["api_hints"] = list(dict.fromkeys(API_RE.findall(html)))[:10]
                print(f"[wz] {url} → {rec.get('status')} len={rec.get('len')} "
                      f"links={len(rec.get('links', []))} api={len(rec.get('api_hints', []))}",
                      flush=True)
            except Exception as e:                                          # noqa: BLE001
                rec["error"] = f"{type(e).__name__}"
                print(f"[wz] {url} → {type(e).__name__}", flush=True)
            out.append(rec)
            time.sleep(2)

    # 深入前几个问答栏目
    seen = set()
    for rec in out:
        for full, text in (rec.get("links") or [])[:4]:
            if full in seen:
                continue
            seen.add(full)
            try:
                r = c.get(full)
                html = r.text or ""
                hints = list(dict.fromkeys(API_RE.findall(html)))[:8]
                print(f"    [{text}] {full[:70]} → {r.status_code} len={len(html)} api={hints[:4]}",
                      flush=True)
                rec.setdefault("sub", []).append(
                    {"url": full, "text": text, "status": r.status_code,
                     "api_hints": hints})
            except Exception as e:                                          # noqa: BLE001
                print(f"    [{text}] {full[:60]} → {type(e).__name__}")
            time.sleep(2)

    import json
    (HERE / "sc-wenzheng-probe.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[wz] 证据已写 recon/sc-wenzheng-probe.json")
    return 0


if __name__ == "__main__":
    main()
