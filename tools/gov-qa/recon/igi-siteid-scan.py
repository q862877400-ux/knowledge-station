"""IGI `siteId` 全域枚举（含 appId 过滤语义）——2026-10-09 新增。

## 为什么重扫
旧脚本 `recon/waf-igi-sites.py` 只枚举 **siteId=1..60**，而实测：
 · 宁夏有效 siteId = **115**（在窗口外 ⇒ 旧扫必然漏）；
 · 湖北门户有效 siteId 含 **71**（在窗口外，见 recon/gs-hb-igi-sites.txt）。
⇒ 「1..60」这个窗口本身有盲区，必须扩到 300 重扫。

## 新发现：`appId` 是**过滤条件**，不是站点标识
实测（2026-10-09）：
 · 山西 siteId=36, appId=584617 → total=**826**；同 siteId 空 appId → total=**4653**。
 · 山西 siteId=110, appId=1742326 → 1872；同 siteId 空 appId → 1872（无差）。
⇒ 空 appId = **不按应用过滤**（该 siteId 全部记录）；带 appId = 只看该应用的记录。
⇒ 枚举与采集都应优先用**空 appId**，否则会漏掉未挂到已知 appId 的记录。

## 用法
  .venv/Scripts/python.exe recon/igi-siteid-scan.py <tag>
  tag ∈ {shanxi, guangxi, ningxia, xizang, guizhou, hubei}
产出 recon/igi-siteid-<tag>.json（siteId → totalResults）。
纪律：请求间隔 1.5s；只读列表第 1 页 pageSize=1；不落盘语料。
"""
from __future__ import annotations

import json
import sys
import time

import httpx

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
PAUSE = 1.5
LIST = ("{base}/IGI/nbhd/openGovmsgbox.do?method=listGovmsgboxs"
        "&siteId={sid}&order=1&appId={aid}&pageIndex=1&pageSize=1")

TARGETS = {
    "shanxi":   ("http://www.shanxi.gov.cn",  "http://www.shanxi.gov.cn/zmhd/",            1, 300),
    "guangxi":  ("http://www.gxzf.gov.cn",    "http://www.gxzf.gov.cn/hdjl/mailbox/index.shtml", 1, 300),
    "ningxia":  ("https://www.nx.gov.cn",     "https://www.nx.gov.cn/hdjl/",              1, 300),
    "xizang":   ("http://www.xizang.gov.cn",  "http://www.xizang.gov.cn/zmhd/",           1, 300),
    "guizhou":  ("http://www.guizhou.gov.cn", "http://www.guizhou.gov.cn/",               1, 300),
    "hubei":    ("http://www.hubei.gov.cn",   "http://www.hubei.gov.cn/hdjl/",            1, 300),
}


def probe(cli, base, sid, aid, referer):
    try:
        r = cli.get(LIST.format(base=base, sid=sid, aid=aid), headers={"Referer": referer})
    except Exception as e:                                                   # noqa: BLE001
        return "ERR:" + type(e).__name__, 0
    if r.status_code != 200:
        return r.status_code, 0
    try:
        j = r.json()
    except Exception:                                                        # noqa: BLE001
        return 200, -1
    datas = j.get("datas") or {}
    pi = datas.get("pageInfo") or {}
    return 200, int(pi.get("totalResults") or 0)


def main() -> int:
    tag = sys.argv[1] if len(sys.argv) > 1 else ""
    if tag not in TARGETS:
        print("usage: igi-siteid-scan.py <" + "|".join(TARGETS) + ">")
        return 2
    base, referer, lo, hi = TARGETS[tag]
    hits: dict[str, int] = {}
    with httpx.Client(timeout=25, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False, verify=False) as cli:
        for sid in range(lo, hi + 1):
            time.sleep(PAUSE)
            st, tot = probe(cli, base, sid, "", referer)
            if st == 200 and tot and tot > 0:
                hits[str(sid)] = tot
                print(f"  [{tag}] siteId={sid} total={tot}", flush=True)
            elif st != 200:
                print(f"  [{tag}] siteId={sid} -> {st}", flush=True)
    out = {"tag": tag, "base": base, "referer": referer,
           "range": [lo, hi], "appId": "", "sites": hits, "total": sum(hits.values())}
    path = f"tools/gov-qa/recon/igi-siteid-{tag}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"==> [{tag}] {len(hits)} site / {sum(hits.values())} 条 -> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
