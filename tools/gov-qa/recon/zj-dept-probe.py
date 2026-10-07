"""浙江省 · 厅局真实域名 + 互动平台指纹批量侦察（广东打法的复制）。

三步（证据落 recon/zj-dept-probe.json）：
  1. 从 zj.gov.cn 首页找「省政府部门/机构」名录页；
  2. 抓名录页里全部 <xxx>.zj.gov.cn 域名 + 部门名；
  3. 每个域名探两个指纹：
     · /was5/web/search（TRS 检索中间件，200+小页=存在）
     · 首页里的互动/问答栏目链接（≥1 条记下，供下一步挖接口）
礼貌抓取：间隔 1.5s；错域名快速失败。
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

PORTAL = "https://www.zj.gov.cn/"
DOM_RE = re.compile(r'https?://([a-z0-9\-]+)\.zj\.gov\.cn', re.I)
A_HREF_RE = re.compile(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
NAV_KW = ("部门", "机构", "名录", "省政府", "组成部门", "直属")
INT_KW = ("互动", "问答", "常见问题", "留言", "咨询", "回应关切", "选登", "答复")


class _W:
    def __init__(self, client):
        self._c = client

    def post(self, *a, **k):
        return self._c.post(*a, **k)


def main() -> int:
    import httpx

    results = []
    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=15, follow_redirects=True) as c:
        w = _W(c)

        # ① 首页找名录页
        r = c.get(PORTAL)
        t = r.text or ""
        base = str(getattr(r, "url", PORTAL))
        dir_pages = []
        for href, inner in A_HREF_RE.findall(t):
            name = TAG_RE.sub("", inner).strip()
            if any(k in name for k in NAV_KW) and len(name) <= 12:
                full = urljoin(base, href)
                if full.startswith("http") and "zj.gov.cn" in full:
                    if full not in dir_pages:
                        dir_pages.append(full)
        print(f"[zj] 名录候选页 {len(dir_pages)}：{dir_pages[:5]}")

        # ② 抓名录页里的域名（首页也兜底）
        found: dict[str, str] = {}
        for page in [PORTAL] + dir_pages[:3]:
            try:
                rr = c.get(page)
            except Exception as e:                                          # noqa: BLE001
                print(f"[zj] {page} {type(e).__name__}")
                continue
            pt = rr.text or ""
            pbase = str(getattr(rr, "url", page))
            for href, inner in A_HREF_RE.findall(pt):
                name = TAG_RE.sub("", inner).strip()
                full = urljoin(pbase, href)
                m = DOM_RE.match(full)
                if not m:
                    continue
                dom = m.group(1)
                if dom in ("www", "app", "service", "zjzw", "zdh") or dom.isdigit():
                    continue
                if dom not in found and 2 <= len(name) <= 20:
                    found[dom] = name
            print(f"[zj] {page[:60]} → {rr.status_code}, 累计域名 {len(found)}")
            time.sleep(1.5)

        # ③ 每个域名两个指纹
        for dom, name in sorted(found.items()):
            base = f"https://{dom}.zj.gov.cn"
            rec = {"name": name, "dom": dom, "base": base}
            try:
                r2 = c.get(f"{base}/was5/web/search?channelid=1&perpage=1&page=1")
                rec["was5_status"] = r2.status_code
                was = r2.text or ""
                rec["was5_len"] = len(was)
                rec["was5_hit"] = r2.status_code == 200 and len(was) < 2000
                r3 = c.get(base + "/")
                home = r3.text or ""
                hbase = str(getattr(r3, "url", base + "/"))
                links = []
                for href, inner in A_HREF_RE.findall(home):
                    txt = TAG_RE.sub("", inner).strip()
                    if any(k in txt for k in INT_KW):
                        full = urljoin(hbase, href)
                        if full.startswith("http") and dom in full:
                            if all(full != u for u, _ in links):
                                links.append((full, txt))
                rec["hd_links"] = [{"url": u, "text": x} for u, x in links[:8]]
                print(f"[{name}] was5={rec['was5_status']}/{rec['was5_len']}B "
                      f"hit={rec['was5_hit']} links={len(links)}", flush=True)
            except Exception as e:                                          # noqa: BLE001
                rec["error"] = f"{type(e).__name__}"
                print(f"[{name}] {type(e).__name__}", flush=True)
            results.append(rec)
            time.sleep(1.5)

    (HERE / "zj-dept-probe.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    hits = [r for r in results if r.get("was5_hit")]
    print(f"\n[zj] 域名 {len(results)} 个，WAS5 命中 {len(hits)}："
          f"{[r['name'] for r in hits]}")
    return 0


if __name__ == "__main__":
    main()
