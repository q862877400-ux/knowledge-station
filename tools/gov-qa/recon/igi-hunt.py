"""IGI 厅局自动搜寻：抓站点 → 抠 siteId/appId/groupId → **直接调接口验证**是否可用。

为什么做成一条龙：IGI 按厅局挂载，逐个手抠参数太慢；这里对候选站点自动完成
「指纹识别 → 参数提取 → 接口验证 → 报告条数」，命中即可直接落适配器。
用法：python recon/igi-hunt.py [输出文件名]（默认 igi-hunt.txt；重跑请换名，别覆盖历史证据）
输出：recon/igi-hunt.txt
"""
from __future__ import annotations

import json
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

CANDIDATES = [
    # —— 2026-10-07 第一批（证据见 igi-hunt.txt）——
    ("贵州", "市场监管局", "https://amr.guizhou.gov.cn/", "gz"),
    ("贵州", "交通运输厅", "https://jt.guizhou.gov.cn/", "gz"),
    ("贵州", "教育厅", "https://jyt.guizhou.gov.cn/", "gz"),
    ("贵州", "人力资源社会保障厅", "https://rst.guizhou.gov.cn/", "gz"),
    ("贵州", "自然资源厅", "https://zrzy.guizhou.gov.cn/", "gz"),
    ("贵州", "住房城乡建设厅", "https://zfcxjst.guizhou.gov.cn/", "gz"),
    ("贵州", "农业农村厅", "https://nynct.guizhou.gov.cn/", "gz"),
    ("吉林", "交通运输厅", "https://jt.jl.gov.cn/", "jl"),
    ("吉林", "教育厅", "https://jyt.jl.gov.cn/", "jl"),
    ("吉林", "人力资源和社会保障厅", "https://hrss.jl.gov.cn/", "jl"),
    ("吉林", "自然资源厅", "https://zrzy.jl.gov.cn/", "jl"),
    ("吉林", "农业农村厅", "https://nynct.jl.gov.cn/", "jl"),
    # —— 2026-10-08 第二批：贵州/吉林其余厅局（交接 §4.2：IGI 还有大量厅局没探）——
    ("贵州", "水利厅", "https://sl.guizhou.gov.cn/", "gz"),
    ("贵州", "工业和信息化厅", "https://gxj.guizhou.gov.cn/", "gz"),
    ("贵州", "文化和旅游厅", "https://wlt.guizhou.gov.cn/", "gz"),
    ("贵州", "商务厅", "https://swt.guizhou.gov.cn/", "gz"),
    ("吉林", "发展和改革委员会", "https://fgw.jl.gov.cn/", "jl"),
    ("吉林", "工业和信息化厅", "https://jlgxj.jl.gov.cn/", "jl"),
    ("吉林", "文化和旅游厅", "https://wlt.jl.gov.cn/", "jl"),
    ("吉林", "商务厅", "https://swt.jl.gov.cn/", "jl"),
    ("吉林", "水利厅", "https://sl.jl.gov.cn/", "jl"),
    ("吉林", "交通运输厅(jtyst)", "https://jtyst.jl.gov.cn/", "jl"),
]
FINGER = ("openGovmsgbox", "listGovmsgboxs", "/IGI/")
SUBS = ["", "hdjl/", "zmhd/", "hdjl/tzxx/xjgs/", "zmhd/tzxx/lyxd/", "hdjl/tzxx/", "hd/"]
PARAM_RE = r"(siteId|appId|groupId)\s*[=:]\s*'?(\d+)'?"
#: 新跑用新文件名（python igi-hunt.py igi-hunt-2.txt），别覆盖历史证据
OUT = HERE / (sys.argv[1] if len(sys.argv) > 1 else "igi-hunt.txt")


def scan_js(c, html: str, page: str, params: dict[str, str], f) -> None:
    """抓指纹页链出的同域 .js（至多 3 个），把其中的 IGI 参数并入。

    背景：贵州市场监管局首页只内联 siteId/appId（groupId 可能在 JS 里），
    贵州自然资源厅首页只有 siteId —— 参数不全时靠这一步补齐。
    """
    host = urlparse(page).netloc
    scanned = 0
    for s in re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', html, re.I):
        url = urljoin(page, s)
        if urlparse(url).netloc != host or not url.lower().endswith(".js"):
            continue
        try:
            r = c.get(url, timeout=8)
            txt = r.text or ""
        except Exception:                                          # noqa: BLE001
            continue
        found = re.findall(PARAM_RE, txt)
        if found:
            for k, v in found:
                params.setdefault(k, v)
            f.write(f"     JS参数 {url} → {dict(found)}\n")
        scanned += 1
        time.sleep(0.3)
        if scanned >= 3:
            break


def try_api(c, sites: list[str], sid: str, aid: str, gid: str | None, ref: str) -> dict:
    """对该参数组合试各个候选 base，返回第一个 200 且含 datas 的结果。"""
    for base in sites:
        g = f"&groupId={gid}" if gid else ""
        url = (f"{base}/nbhd/openGovmsgbox.do?method=listGovmsgboxs"
               f"&siteId={sid}&order=1&appId={aid}{g}&pageIndex=1&pageSize=2")
        try:
            r = c.get(url, headers={"Referer": ref})
            if r.status_code == 200 and "datas" in (r.text or ""):
                rows = (r.json().get("datas") or {}).get("data") or []
                return {"base": base, "n": len(rows), "ok": True,
                        "sample": (rows[0].get("TITLE") if rows else None),
                        "chain": ([rows[0].get("PROVINCE"), rows[0].get("CITY"),
                                   rows[0].get("AREA")] if rows else None)}
        except Exception:                                                   # noqa: BLE001
            continue
        time.sleep(0.5)
    return {"ok": False}


def main() -> int:
    import httpx

    with httpx.Client(headers={"User-Agent": UA}, trust_env=False, timeout=12,
                      follow_redirects=True) as c:
        with OUT.open("w", encoding="utf-8") as f:
            for prov, dept, site, abbr in CANDIDATES:
                params: dict[str, str] = {}
                hit_page = None
                for sub in SUBS:
                    url = site + sub
                    try:
                        r = c.get(url)
                        html = r.text or ""
                    except Exception as e:                                  # noqa: BLE001
                        f.write(f"  {prov}{dept} {url} → {type(e).__name__}\n")
                        break
                    if any(k in html for k in FINGER):
                        hit_page = url
                        for k, v in re.findall(PARAM_RE, html):
                            params.setdefault(k, v)
                        scan_js(c, html, url, params, f)
                        if len(params) >= 2:
                            break
                    time.sleep(0.5)
                if not hit_page:
                    f.write(f"  {prov}{dept} 无 IGI 指纹\n")
                    continue
                sid, aid, gid = params.get("siteId"), params.get("appId"), params.get("groupId")
                f.write(f"★ {prov}{dept} 指纹页 {hit_page} 参数 {params}\n")
                if not (sid and aid):
                    f.write("     参数不足，跳过验证\n")
                    continue
                bases = [site.rstrip("/") + "/IGI"]
                if abbr == "jl":
                    bases.insert(0, "https://haiyun.jl.gov.cn/IGI")
                res = try_api(c, bases, sid, aid, gid, hit_page)
                f.write(f"     验证：{json.dumps(res, ensure_ascii=False)}\n")
                time.sleep(1)
    print("written", OUT)
    return 0


if __name__ == "__main__":
    main()
