"""福建省生态环境厅 · 厅长信箱/网上咨询 接口挖掘（WAS5 指纹已确认存在）。

上级证据：recon/probe-provinces.json（was5 指纹 200/800B）+ dig2-js.json（栏目链接）。
本脚本：抓 /gzcy/tzxx/ 与 /gzcy/tzxx/wyzx/（及其"选登/回复"类子链接），
挖内联 JS 的 channelid / was5 调用 / 明细页链接形态。
礼貌抓取：间隔 2.5s。
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
sys.path.insert(0, str(HERE.parent))     # 复用模块根的常量（本脚本在 recon/ 下）

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")

from adapters._liuyan_common import UA  # noqa: E402  ← 统一 UA（限流教训）

SCRIPT_RE = re.compile(r"<script[^>]*>(.*?)</script>", re.S | re.I)
CHANNELID_RE = re.compile(r"channelid['\"]?\s*[:=]\s*['\"]?(\d{3,8})", re.I)
WAS5_RE = re.compile(r"[\"']([^\"']*was5?/web/search[^\"']*)[\"']", re.I)
A_HREF_RE = re.compile(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
KEY = ("channelid", "leaveword", "interactionparams", "was5", "ajaxcjwt", "hflist", "xuanDeng".lower())

TARGETS = [
    "https://sthjt.fujian.gov.cn/gzcy/tzxx/",
    "https://sthjt.fujian.gov.cn/gzcy/tzxx/wyzx/",
]


def main() -> int:
    import httpx

    out = []
    with httpx.Client(headers={"User-Agent": UA}, follow_redirects=True,
                      trust_env=False, timeout=25) as c:
        seen_pages = set()
        queue = list(TARGETS)
        while queue and len(seen_pages) < 6:
            url = queue.pop(0)
            if url in seen_pages:
                continue
            seen_pages.add(url)
            try:
                r = c.get(url)
            except Exception as e:                                          # noqa: BLE001
                print(f"[fj] {url} 网络错误 {type(e).__name__}", flush=True)
                continue
            rec = {"url": url, "status": r.status_code, "len": len(r.text or "")}
            html = r.text or ""
            if r.status_code == 200:
                rec["channelids"] = list(dict.fromkeys(CHANNELID_RE.findall(html)))[:10]
                rec["was5_urls"] = list(dict.fromkeys(WAS5_RE.findall(html)))[:6]
                blocks = []
                for s in SCRIPT_RE.findall(html):
                    if any(k in s.lower() for k in KEY):
                        blocks.append(s[:1200])
                rec["script_blocks"] = blocks[:4]
                # 子链接（选登/回复/更多形态）
                subs = []
                for href, inner in A_HREF_RE.findall(html):
                    text = TAG_RE.sub("", inner).strip()
                    if any(k in text for k in ("选登", "回复", "信箱", "咨询", "更多")):
                        full = urljoin(url, href)
                        if "fujian.gov.cn" in full:
                            subs.append(f"{text} -> {full}")
                rec["sub_links"] = list(dict.fromkeys(subs))[:15]
                # 把「信箱/咨询」类子链接入队（深度 1 层）
                for s in rec["sub_links"]:
                    u = s.split(" -> ", 1)[-1]
                    if any(k in u for k in ("tzxx", "wyzx", "xxgk", "hf")) and u not in seen_pages:
                        queue.append(u)
            out.append(rec)
            print(f"[fj] {url} → {rec.get('status')} cids={rec.get('channelids')}",
                  flush=True)
            time.sleep(2.5)

    (HERE / "fujian-tzxx-dig.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[fj] 证据已写 {HERE / 'fujian-tzxx-dig.json'}")
    return 0


if __name__ == "__main__":
    main()
