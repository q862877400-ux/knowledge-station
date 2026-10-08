"""IGI 深挖：对「指纹已中但 n=0 / 参数不足」的站点，从**信箱页 + 页面 JS** 里找真实参数。

背景（HANDOVER §4.3 两个 n=0 案例 + 贵州自然资源厅参数不足）：
首页内联的参数可能是旧默认值；真实参数在信箱页（`zmhd/tzxx/lyxd/` 这类路径，
吉林自然资源厅的 `ajax_index_cmy_20211110.js` 即此类证据）或页面链出的 JS 里。
本脚本对每个候选：
  1. 存首页原文（`recon/<abbr>-home.html`）
  2. 抽 href 含 (hdjl|zmhd|lyxd|xjgs|igi|hdhd) 的同域链接，至多访问 4 个并存原文
  3. 扫描所有页面 + 页面 JS（每页至多 3 个）里的 {siteId, appId, groupId}，
     收集**所有不同的参数组合**（不只取第一个）
  4. 每个参数组合直接调接口验证（站点自带 /IGI；吉林另试 haiyun.jl.gov.cn/IGI），
     报告 n
用法：python recon/igi-dig.py [输出文件名]（默认 igi-dig.txt）
"""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")
sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import UA  # noqa: E402

OUT = HERE / (sys.argv[1] if len(sys.argv) > 1 else "igi-dig.txt")

#: (abbr, 名称, 站点, 省)——都是「指纹已中但验证 n=0 或参数不足」的
SITES = [
    ("amr", "贵州市场监管局", "https://amr.guizhou.gov.cn", "贵州"),
    ("zrzy", "贵州自然资源厅", "https://zrzy.guizhou.gov.cn", "贵州"),
    ("hrss", "吉林人社", "https://hrss.jl.gov.cn", "吉林"),
    ("jtyst", "吉林交通运输", "https://jtyst.jl.gov.cn", "吉林"),
]

LINK_RE = re.compile(r'href=["\']([^"\'#?]+)["\']', re.I)
SCRIPT_RE = re.compile(r'<script[^>]+src=["\']([^"\']+)["\']', re.I)
PARAM_RE = r'(siteId|appId|groupId)\s*[=:]\s*["\']?(\d+)["\']?'
MAILBOX_KW = re.compile(r'hdjl|zmhd|lyxd|xjgs|igi|hdhd', re.I)


def find_params(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in re.findall(PARAM_RE, text or ""):
        out.setdefault(k, v)
    return out


def try_api(c, bases: list[str], p: dict[str, str], ref: str) -> list[dict]:
    for base in bases:
        g = f"&groupId={p['groupId']}" if p.get("groupId") else ""
        url = (f"{base}/nbhd/openGovmsgbox.do?method=listGovmsgboxs"
               f"&siteId={p['siteId']}&order=1&appId={p['appId']}{g}"
               f"&pageIndex=1&pageSize=2")
        try:
            r = c.get(url, headers={"Referer": ref})
            if r.status_code == 200 and "datas" in (r.text or ""):
                rows = (r.json().get("datas") or {}).get("data") or []
                return [{"base": base, "n": len(rows), "ok": True,
                        "sample": (rows[0].get("TITLE") if rows else None),
                        "chain": ([rows[0].get("PROVINCE"), rows[0].get("CITY"),
                                   rows[0].get("AREA")] if rows else None)}]
        except Exception:                                                     # noqa: BLE001
            continue
        time.sleep(0.5)
    return [{"base": bases[0], "n": 0, "ok": False, "sample": None, "chain": None}]


def main() -> int:
    import httpx

    with httpx.Client(headers={"User-Agent": UA}, trust_env=False, timeout=12,
                      follow_redirects=True) as c:
        with OUT.open("w", encoding="utf-8") as f:
            for abbr, name, site, prov in SITES:
                host = urlparse(site).netloc
                f.write(f"== {name} {site}\n")
                bases = [site.rstrip("/") + "/IGI"]
                if prov == "吉林":
                    bases.insert(0, "https://haiyun.jl.gov.cn/IGI")
                params_sets: list[tuple[str, dict[str, str]]] = []
                seen: set[tuple] = set()
                # 1) 首页
                try:
                    r = c.get(site)
                    home = r.text or ""
                except Exception as e:                                        # noqa: BLE001
                    f.write(f"   首页 {type(e).__name__}\n")
                    continue
                (HERE / f"{abbr}-home.html").write_text(home, encoding="utf-8")
                p = find_params(home)
                if p:
                    params_sets.append(("首页", p))
                    seen.add(tuple(sorted(p.items())))
                # 2) 信箱页
                links = []
                for s in LINK_RE.findall(home):
                    u = urljoin(site, s)
                    if (urlparse(u).netloc == host and MAILBOX_KW.search(u)
                            and u not in links):
                        links.append(u)
                pages: list[str] = []
                for i, u in enumerate(links[:4]):
                    try:
                        r = c.get(u)
                        html = r.text or ""
                    except Exception as e:                                    # noqa: BLE001
                        f.write(f"   页 {u} → {type(e).__name__}\n")
                        continue
                    pages.append(u)
                    (HERE / f"{abbr}-p{i}.html").write_text(html, encoding="utf-8")
                    p = find_params(html)
                    if p:
                        key = tuple(sorted(p.items()))
                        if key not in seen:
                            params_sets.append((u, p))
                            seen.add(key)
                    # 3) 页面 JS（至多 3 个）
                    jsn = 0
                    for s in SCRIPT_RE.findall(html):
                        jurl = urljoin(u, s)
                        if (urlparse(jurl).netloc != host
                                or not jurl.lower().endswith(".js")):
                            continue
                        try:
                            jr = c.get(jurl, timeout=8)
                            jtxt = jr.text or ""
                        except Exception:                                    # noqa: BLE001
                            continue
                        (HERE / f"{abbr}-p{i}-js{jsn}.js").write_text(jtxt, encoding="utf-8")
                        jp = find_params(jtxt)
                        if jp:
                            key = tuple(sorted(jp.items()))
                            if key not in seen:
                                params_sets.append((jurl, jp))
                                seen.add(key)
                        jsn += 1
                        time.sleep(0.3)
                        if jsn >= 3:
                            break
                    time.sleep(0.5)
                # 4) 逐组合验证
                if not params_sets:
                    f.write("   未找到任何参数\n")
                for desc, p in params_sets:
                    if not (p.get("siteId") and p.get("appId")):
                        f.write(f"   组合 {desc} {p} 参数不足，跳过\n")
                        continue
                    res = try_api(c, bases, p, desc if desc.startswith("http") else site)
                    f.write(f"   组合 {desc} {p} → {res[0]}\n")
                    time.sleep(1)
    print("written", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
