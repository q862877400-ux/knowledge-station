"""从广东省政府门户抓厅局真实域名清单 → 逐个探测 hdjlpt 平台。

背景：recon/gd-dept-hdjlpt-probe.json 里 15 个候选域名 10 个是猜错的。
本脚本两步：
  1. 抓 gd.gov.cn 首页/部门页，提取「省政府部门」区里的 *.gd.gov.cn 链接 + 名称；
  2. 对每个域名探 `{dom}/hdjlpt?via=pc` + `letter/pubList`，命中记录年窗 total。
产出：recon/gd-dept-domains.json（全量清单+命中结果），给薄壳适配器当配置源。
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import unquote, urljoin

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")

sys.path.insert(0, str(HERE.parent))
from adapters._gd_hdjlpt_common import (  # noqa: E402
    API_PATH, PAGE_PATH, _post_list, _xsrf_token)
from adapters._liuyan_common import UA  # noqa: E402

PORTALS = [
    "https://www.gd.gov.cn/zwgk/wjnz/",
    "https://www.gd.gov.cn/gdgov/gov/dept.html",
    "https://www.gd.gov.cn/",
]

A_HREF_RE = re.compile(r'<a[^>]+href="(https?://[a-z0-9\-]+\.gd\.gov\.cn[^"]*)"[^>]*>(.*?)</a>', re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")


class _W:
    def __init__(self, client):
        self._c = client

    def post(self, *a, **k):
        return self._c.post(*a, **k)


def collect_domains(c) -> dict[str, str]:
    """域名 → 部门名（从门户页面链接锚文本取）。"""
    found: dict[str, str] = {}
    for portal in PORTALS:
        try:
            r = c.get(portal)
        except Exception as e:                                              # noqa: BLE001
            print(f"[portal] {portal} {type(e).__name__}")
            continue
        t = r.text or ""
        for href, inner in A_HREF_RE.findall(t):
            name = TAG_RE.sub("", inner).strip()
            m = re.match(r"https?://([a-z0-9\-]+)\.gd\.gov\.cn", href, re.I)
            if not m:
                continue
            dom = m.group(1)
            if dom in ("www", "gov", "app", "service", "yjzj", "statistics"):
                continue                       # 门户自身/公共服务域
            if dom not in found and 2 <= len(name) <= 20:
                found[dom] = name
        print(f"[portal] {portal} → {r.status_code}, 累计域名 {len(found)}")
        time.sleep(1.5)
    return found


def main() -> int:
    import httpx

    # 域名清单：优先用名录页抓到的全量（gd-dir-page.py 产出）
    list_file = HERE / "gd-dept-domains-full.json"
    if list_file.exists():
        entries = [(e["dom"], e["name"])
                   for e in json.loads(list_file.read_text(encoding="utf-8"))]
        print(f"[list] 使用名录页全量清单：{len(entries)} 个域名")
    else:
        with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                          timeout=15, follow_redirects=True) as c0:
            entries = list(collect_domains(c0).items())
        print(f"[list] 门户首页兜底清单：{len(entries)} 个域名")

    results = []
    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=15, follow_redirects=True) as c:
        w = _W(c)
        for dom, name in entries:
            base = f"https://{dom}.gd.gov.cn"
            rec = {"name": name, "dom": dom, "base": base}
            try:
                r0 = c.get(base + PAGE_PATH)
                rec["page"] = r0.status_code
                token = _xsrf_token(r0) if r0.status_code == 200 else None
                if token:
                    time.sleep(1.2)
                    j = _post_list(w, base=base, token=token, offset=0,
                                   limit=3,
                                   time_from=1759852800, time_to=1791388799)
                    d = j.get("data") or {}
                    lst = d.get("list") or []
                    rec["total"] = d.get("total")
                    rec["org"] = (lst[0].get("org_name") if lst else None)
                    print(f"[{name}] ★ total={rec['total']}", flush=True)
                else:
                    rec["hdjlpt"] = False
                    print(f"[{name}] 无 hdjlpt", flush=True)
            except Exception as e:                                          # noqa: BLE001
                rec["error"] = f"{type(e).__name__}: {str(e)[:60]}"
                print(f"[{name}] {type(e).__name__}", flush=True)
            results.append(rec)
            time.sleep(1.5)

    (HERE / "gd-dept-domains-probed.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    hits = [r for r in results if r.get("total") is not None]
    print(f"\n[gd-domains] 探测 {len(results)} 个，hdjlpt 命中 {len(hits)}：")
    for r in hits:
        print(f"  {r['name']} ({r['dom']}) total={r['total']}")
    return 0


if __name__ == "__main__":
    main()
