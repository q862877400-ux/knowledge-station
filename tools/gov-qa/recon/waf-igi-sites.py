"""阶段二：对「IGI 返回 statusCode=200 空列表（siteId=1 无数据）」的站点，
枚举 siteId + 试 Referer，找出真正有数据的 site。

策略：
  · 对每个候选 host：先不带 Referer 枚举 siteId=1..60，记 totalResults>0 的；
  · 再带 Referer（该站互动页）枚举一遍补漏；
  · 空 siteId 且空 regions 报 301「siteId与regions不能同时为空」说明同族。
纪律：间隔 >= 1.5s。产出 recon/waf-igi-sites-<tag>.json。
"""
from __future__ import annotations

import json
import sys
import time

import httpx

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
PAUSE = 1.5

# (tag, host, referer候选, scheme)
TARGETS = [
    ("xizang", "www.xizang.gov.cn", "http://www.xizang.gov.cn/zmhd/", "http"),
    ("shaanxi", "www.shaanxi.gov.cn", "http://www.shaanxi.gov.cn/hd/wxszsjh/lyxd/", "http"),
    ("tianjin", "www.tj.gov.cn", "http://www.tj.gov.cn/zmhd/", "http"),
    ("chongqing", "www.cq.gov.cn", "http://www.cq.gov.cn/hdjl/", "http"),
    ("guizhou", "www.guizhou.gov.cn", "http://www.guizhou.gov.cn/", "http"),
    ("sx-hd", "rst.hubei.gov.cn", "http://rst.hubei.gov.cn/hdjl/", "http"),
    ("hb-wjw", "wjw.hubei.gov.cn", "http://wjw.hubei.gov.cn/", "http"),
    ("hn-hd", "www.hainan.gov.cn", "http://www.hainan.gov.cn/hainan/zcwd/zcwd.shtml", "http"),
    ("jx-hd", "www.jiangxi.gov.cn", "http://www.jiangxi.gov.cn/", "http"),
    ("hlj2", "www.hlj.gov.cn", "http://www.hlj.gov.cn/", "http"),
]

LIST = ("{base}/IGI/nbhd/openGovmsgbox.do?method=listGovmsgboxs"
        "&siteId={sid}&order=1&appId=&pageIndex=1&pageSize=1")


def total(cli, url, referer):
    try:
        r = cli.get(url, headers={"Referer": referer})
    except Exception as e:  # noqa: BLE001
        return f"ERR:{type(e).__name__}", 0, None
    if r.status_code != 200:
        return r.status_code, 0, None
    try:
        j = r.json()
    except Exception:  # noqa: BLE001
        return 200, -1, "nonjson"
    datas = j.get("datas") or {}
    pi = datas.get("pageInfo") or {}
    rows = datas.get("data") or []
    return 200, int(pi.get("totalResults") or 0), (rows[0] if rows else None)


def enumerate_sites(cli, host, scheme, referer, lo, hi):
    base = f"{scheme}://{host}"
    hits = {}
    for sid in range(lo, hi + 1):
        time.sleep(PAUSE)
        st, tot, _ = total(cli, LIST.format(base=base, sid=sid), referer)
        if st == 200 and tot and tot > 0:
            hits[str(sid)] = tot
            print(f"    site={sid} total={tot}", flush=True)
    return hits


def main() -> int:
    lo, hi = 1, 60
    only = sys.argv[1] if len(sys.argv) > 1 else ""
    out = {}
    with httpx.Client(timeout=20, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False, verify=False) as cli:
        for tag, host, referer, scheme in TARGETS:
            if only and only not in tag:
                continue
            print(f"\n===== {tag} {host} =====", flush=True)
            # 探 301 判定同族
            time.sleep(PAUSE)
            st0, _, _ = total(cli, LIST.format(base=f"{scheme}://{host}", sid=""), referer)
            print(f"  空siteId -> {st0}", flush=True)
            hits = enumerate_sites(cli, host, scheme, referer, lo, hi)
            out[tag] = {"host": host, "referer": referer, "scheme": scheme,
                        "empty_site_status": st0, "sites": hits,
                        "total": sum(hits.values())}
            print(f"  ==> {tag}: {len(hits)} site / {sum(hits.values())} 条", flush=True)
    path = "recon/waf-igi-sites.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n写入 {path}")
    for tag, v in out.items():
        print(f"  {tag:10s} {v['host']:24s} sites={len(v['sites'])} total={v['total']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
