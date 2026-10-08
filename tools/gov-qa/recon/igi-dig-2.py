"""IGI 深挖第 2 轮：贵州市场监管 / 自然资源 的信箱参数不在首页（首页的 siteId/appId
分属搜索页与智能问答 llm-app）。按已验证的贵州路径模式（生态厅 /hdjl/tzxx/xjgs/、
商务厅 /hdjl/）直接探测常见信箱路径，从页面 + 页面 JS 抠 listGovmsgboxs 参数并验证。

输出：recon/igi-dig-2.txt；命中页面原文存 recon/<abbr>-<路径slug>.html
"""
from __future__ import annotations

import re
import time
from pathlib import Path

import httpx

try:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from adapters._liuyan_common import UA
except Exception:
    UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

HERE = Path(__file__).resolve().parent
OUT = HERE / "igi-dig-2.txt"

SITES = [
    ("amr", "https://amr.guizhou.gov.cn"),
    ("zrzy", "https://zrzy.guizhou.gov.cn"),
]
PATHS = ["/hdjl/", "/hdjl/tzxx/", "/hdjl/tzxx/xjgs/", "/hdjl/tzxx/lyxd/",
         "/hdhd/", "/hdhd/tzxx/", "/zmhd/", "/zmhd/tzxx/", "/hd/"]

PARAM_RE = re.compile(r"(siteId|appId|groupId)\s*[=:]\s*['\"]?(\d+)['\"]?")


def find_params(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in re.findall(PARAM_RE, text or ""):
        out.setdefault(k, v)
    return out


def main() -> int:
    lines: list[str] = []
    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=12, follow_redirects=True) as c:
        for abbr, base in SITES:
            lines.append(f"== {abbr} {base} ==")
            tried: set[tuple[str, str]] = set()
            for path in PATHS:
                url = base + path
                try:
                    r = c.get(url)
                except Exception as e:
                    lines.append(f"  {path}  {type(e).__name__}")
                    continue
                if r.status_code != 200:
                    lines.append(f"  {path}  HTTP {r.status_code}")
                    continue
                txt = r.text or ""
                slug = re.sub(r"[^0-9A-Za-z]+", "_", path).strip("_")
                (HERE / f"{abbr}-{slug}.html").write_text(txt, encoding="utf-8")
                p = find_params(txt)
                # 页面 JS
                for m in re.findall(r'<script[^>]+src=["\']([^"\']+\.js)["\']', txt, re.I)[:3]:
                    import urllib.parse
                    jsurl = urllib.parse.urljoin(url, m)
                    try:
                        js = c.get(jsurl).text
                    except Exception:
                        continue
                    p2 = find_params(js)
                    if p2:
                        p = {**p2, **p}
                        lines.append(f"    JS {m} → {p2}")
                if not p:
                    continue
                lines.append(f"  {path}  参数 {p}")
                if p.get("siteId") and p.get("appId") and (p["siteId"], p["appId"], p.get("groupId")) not in tried:
                    tried.add((p["siteId"], p["appId"], p.get("groupId")))
                    gid = f"&groupId={p['groupId']}" if p.get("groupId") else ""
                    api = (f"{base}/IGI/nbhd/openGovmsgbox.do?method=listGovmsgboxs"
                           f"&siteId={p['siteId']}&order=1&appId={p['appId']}{gid}"
                           f"&pageIndex=1&pageSize=2")
                    try:
                        ar = c.get(api, headers={"Referer": url})
                        rows = ((ar.json() or {}).get("datas") or {}).get("data") or []
                        lines.append(f"    验证 HTTP {ar.status_code} n={len(rows)}"
                                     + (f" 例: {rows[0].get('TITLE')} {rows[0].get('PROVINCE')}/{rows[0].get('CITY')}/{rows[0].get('AREA')}" if rows else ""))
                    except Exception as e:
                        lines.append(f"    验证 {type(e).__name__}")
                    time.sleep(1)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
