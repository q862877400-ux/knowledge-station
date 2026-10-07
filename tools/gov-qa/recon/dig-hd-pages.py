"""省级站侦察第二步：定向挖掘。

三件事（证据全落 recon/dig-hd-pages.json）：
  A. 对已确认 WAS5 指纹的站点，抓它的「互动交流」栏目页，
     挖内联 JS 里的 channelid / interactionParams / leaveWordParams / was5 调用。
  B. 看浙江省生态环境厅那 55976B 的 was5 响应到底是什么（是错误页还是真数据）。
  C. 对直连失败的省站做「直连 vs 业主代理(127.0.0.1:7897)」对照
     —— README 坑 2 只在部级站上测过"代理不是原因"，省级还没测过。
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
PROXY = "http://127.0.0.1:7897"

SCRIPT_RE = re.compile(r"<script[^>]*>(.*?)</script>", re.S | re.I)
SRC_RE = re.compile(r"<script[^>]+src=[\"']([^\"']+)[\"']", re.I)
IFRAME_RE = re.compile(r"<iframe[^>]+src=[\"']([^\"']+)[\"']", re.I)
CHANNELID_RE = re.compile(r"channelid['\"]?\s*[:=]\s*['\"]?(\d{3,8})", re.I)
WAS5_URL_RE = re.compile(r"[\"']([^\"']*was5?/web/search[^\"']*)[\"']", re.I)
KEY = ("channelid", "interactionparams", "leavewordparams", "was5", "ajaxcjwt")


def dig_page(label: str, html: str) -> dict:
    """从一个页面里挖出全部接口线索。"""
    blocks = []
    for s in SCRIPT_RE.findall(html):
        if any(k in s.lower() for k in KEY):
            blocks.append(s[:1500])
    srcs = SRC_RE.findall(html)
    iframes = IFRAME_RE.findall(html)
    was_urls = list(dict.fromkeys(WAS5_URL_RE.findall(html)))
    cids = list(dict.fromkeys(CHANNELID_RE.findall(html)))
    return {"label": label, "script_blocks": blocks, "script_srcs": srcs[:15],
            "iframes": iframes[:8], "was5_urls": was_urls, "channelids": cids}


def main() -> int:
    import httpx

    out: dict = {"A_栏目页挖掘": [], "B_浙江was5响应": None, "C_代理对照": []}

    with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True,
                      trust_env=False, timeout=20) as cli:
        # ── A+B：定向挖掘 ──────────────────────────────────────────────
        targets = [
            ("湖南省生态环境厅·互动交流", "https://sthjt.hunan.gov.cn/sthjt/hdjl/index.html"),
            ("湖南省应急管理厅·互动交流", "https://yjt.hunan.gov.cn/yjt/hdjl/hdjl_index.html"),
            ("福建省生态环境厅·公众参与", "https://sthjt.fujian.gov.cn/gzcy/"),
            ("广东省应急管理厅·互动平台", "https://yjgl.gd.gov.cn/hdjlpt"),
            ("浙江省生态环境厅·was5响应",
             "https://sthjt.zj.gov.cn/was5/web/search?channelid=1&perpage=1&page=1"),
        ]
        for label, url in targets:
            try:
                r = cli.get(url)
                rec = {"label": label, "url": url, "status": r.status_code,
                       "len": len(r.text or ""), "ctype": r.headers.get("content-type", "")}
                if label.endswith("was5响应"):
                    rec["head"] = (r.text or "")[:1200]
                    out["B_浙江was5响应"] = rec
                else:
                    rec.update(dig_page(label, r.text or ""))
                    out["A_栏目页挖掘"].append(rec)
                print(f"[A/B] {label}: {r.status_code} / {len(r.text or '')}B", flush=True)
            except Exception as e:                                          # noqa: BLE001
                print(f"[A/B] {label}: 网络错误 {type(e).__name__}", flush=True)
                out["A_栏目页挖掘"].append({"label": label, "url": url,
                                            "error": f"{type(e).__name__}"})
            time.sleep(1.5)

        # ── C：直连 vs 代理对照（只测首页可达性，超时 8s）────────────────
        dead = ["https://yjt.hebei.gov.cn/", "https://jsthjt.jiangsu.gov.cn/",
                "https://sthj.henan.gov.cn/", "https://sthj.cq.gov.cn/",
                "https://yjgl.cq.gov.cn/", "https://sthj.shanxi.gov.cn/"]
        with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True,
                          trust_env=False, timeout=8, proxy=PROXY) as pcli:
            for u in dead:
                row = {"url": u}
                for mode, c in (("direct", cli), ("proxy", pcli)):
                    try:
                        r = c.get(u)
                        row[mode] = f"{r.status_code}/{len(r.text or '')}B"
                    except Exception as e:                                  # noqa: BLE001
                        row[mode] = type(e).__name__
                    time.sleep(1.2)
                out["C_代理对照"].append(row)
                print(f"[C] {u} direct={row['direct']} proxy={row['proxy']}", flush=True)

    path = HERE / "dig-hd-pages.json"
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n[dig] 证据已写 {path}")
    return 0


if __name__ == "__main__":
    main()
