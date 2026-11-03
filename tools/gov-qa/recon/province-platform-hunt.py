"""24 省（无适配器省份）问答/互动平台系统性重探 —— 阶段一：门户可达性 + 互动栏目发现。

背景：HANDOVER 第四节第 6 条列了 24 个「未落适配器」的省级行政区。旧结论（2026-10-07）
只探了少数中间件指纹、面很窄。本脚本系统重探：
  1. 省政府门户首页可达性（GET https://<域名>/）；
  2. 首页 + 常见互动路径（/hdjl/ /zmhd/ /hd/ /gzhd/ /wzly/ /lyb/ /hdjlpt 等）找互动栏目；
  3. 对找到的栏目页，挖内联 JS 的接口线索（channelid / api / list / mailList2ie 等）。

用法：
  python tools/gov-qa/recon/province-platform-hunt.py            # 全量
  python tools/gov-qa/recon/province-platform-hunt.py tj sh      # 只探指定省（域名子串）
产出：recon/province-platform-hunt-stage1.json

⚠ 礼貌抓取：每请求间隔 ≥1.5s；遇 403/412 立即停该站后续探测（不换 UA 绕）。
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

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
PAUSE = 1.6

#: (省, 门户域名) —— 省政府门户 / 政务服务网公开拼法
PORTALS: list[tuple[str, str]] = [
    ("天津", "www.tj.gov.cn"),
    ("上海", "www.sh.gov.cn"),
    ("北京", "www.beijing.gov.cn"),
    ("浙江", "www.zj.gov.cn"),
    ("福建", "www.fj.gov.cn"),
    ("宁夏", "www.nx.gov.cn"),
    ("云南", "www.yn.gov.cn"),
    ("陕西", "www.shaanxi.gov.cn"),
    ("甘肃", "www.gansu.gov.cn"),
    ("青海", "www.qinghai.gov.cn"),
    ("新疆", "www.xinjiang.gov.cn"),
    ("西藏", "www.xizang.gov.cn"),
    ("内蒙古", "www.nmg.gov.cn"),
    ("黑龙江", "www.hlj.gov.cn"),
    ("江西", "www.jiangxi.gov.cn"),
    ("湖北", "www.hubei.gov.cn"),
    ("河南", "www.henan.gov.cn"),
    ("山东", "www.shandong.gov.cn"),
    ("海南", "www.hainan.gov.cn"),
    ("重庆", "www.cq.gov.cn"),
    ("广西", "www.gxzf.gov.cn"),
    ("山西", "www.shanxi.gov.cn"),
    ("河北", "www.hebei.gov.cn"),
    ("江苏", "www.jiangsu.gov.cn"),
]

#: 常见互动栏目路径（相对门户根）
HD_PATHS = [
    "/hdjl/", "/zmhd/", "/hd/", "/gzhd/", "/wzly/", "/lyb/",
    "/hdjl/index.html", "/zmhd/index.html", "/hd/index.html",
    "/gzhd/index.html", "/wzly/index.html", "/hdjlpt",
    "/hdjlpt/", "/hzjl/", "/wszx/", "/zxts/", "/zjhd/",
]

KEYWORDS = ("互动", "问答", "常见问题", "留言", "咨询", "回应", "选登",
            "信箱", "公众参与", "政民", "投诉", "建言", "在线访谈")
NOISE = ("征集调查", "调查征集", "意见征集", "直播", "视频", "访谈预告")

A_HREF_RE = re.compile(r'<a[^>]+href="([^"#]+)"[^>]*>(.*?)</a>', re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<script[^>]*>(.*?)</script>", re.S | re.I)

#: 中间件指纹
FP = {
    "was5": re.compile(r"was5/web/search|leaveWordParams|interactionParams|ajaxCjwt", re.I),
    "igi": re.compile(r"/IGI/|listGovmsgboxs|viewGovmsgbox", re.I),
    "hdjlpt": re.compile(r"hdjlpt|letter/pubList", re.I),
    "mailList2ie": re.compile(r"mailList2ie", re.I),
    "channelid": re.compile(r"channelid['\"]?\s*[:=]\s*['\"]?(\d{3,8})", re.I),
    "api_hint": re.compile(r"[\"']([^\"']{0,90}(?:/api/|/ajax/|/interface/|/service/|mailList|pubList|\.json)[^\"']{0,50})[\"']", re.I),
}


def _get(cli, url):
    try:
        return cli.get(url, timeout=20)
    except Exception as e:                                              # noqa: BLE001
        return e


def _st(r):
    return getattr(r, "status_code", None)


def _text(r):
    return getattr(r, "text", "") or ""


def find_links(html: str, base: str, dom: str) -> list[dict]:
    out: list[dict] = []
    seen: set[str] = set()
    for href, inner in A_HREF_RE.findall(html or ""):
        t = TAG_RE.sub("", inner).strip()
        if not (2 <= len(t) <= 24):
            continue
        if any(k in t for k in KEYWORDS) and not any(n in t for n in NOISE):
            full = urljoin(base, href.strip())
            if full.startswith("http") and dom in full and full not in seen:
                seen.add(full)
                out.append({"url": full, "text": t})
    return out[:20]


def fingerprint(html: str) -> dict:
    fp = {}
    for name, rx in FP.items():
        m = rx.findall(html or "")
        if m:
            fp[name] = list(dict.fromkeys(m))[:6] if name in ("channelid", "api_hint") else True
    return fp


def main() -> int:
    import httpx

    only = [a for a in sys.argv[1:] if not a.startswith("--")]
    portals = [p for p in PORTALS if not only or any(o in p[1] for o in only)]

    results: list[dict] = []
    with httpx.Client(headers={"User-Agent": UA}, trust_env=False,
                      timeout=20, follow_redirects=True) as cli:
        for prov, dom in portals:
            rec: dict = {"province": prov, "domain": dom}
            print(f"[{prov}] https://{dom}/", flush=True)

            r = _get(cli, f"https://{dom}/")
            if isinstance(r, Exception):
                rec["home_status"] = None
                rec["home_err"] = type(r).__name__
                results.append(rec)
                print(f"    home=ERR {type(r).__name__}", flush=True)
                continue
            rec["home_status"] = _st(r)
            home = _text(r)
            base = str(getattr(r, "url", f"https://{dom}/"))
            rec["home_len"] = len(home)

            # 403/412 → 立即停该站（不硬刷）
            if _st(r) in (403, 412):
                rec["stopped"] = "403/412"
                results.append(rec)
                print(f"    home={_st(r)} 反爬，停", flush=True)
                continue

            links = find_links(home, base, dom)
            rec["home_links"] = links
            rec["home_fp"] = fingerprint(home)

            # 探常见互动路径
            path_hits: list[dict] = []
            for p in HD_PATHS:
                url = f"https://{dom}{p}"
                rr = _get(cli, url)
                time.sleep(PAUSE)
                if isinstance(rr, Exception):
                    path_hits.append({"path": p, "err": type(rr).__name__})
                    continue
                st = _st(rr)
                item = {"path": p, "status": st, "len": len(_text(rr))}
                if st == 200 and len(_text(rr)) > 1500:
                    item["fp"] = fingerprint(_text(rr))
                    item["links"] = find_links(_text(rr), str(getattr(rr, "url", url)), dom)
                path_hits.append(item)
                if st in (403, 412):
                    break
            rec["hd_paths"] = path_hits

            hit_paths = [h for h in path_hits if h.get("status") == 200 and h.get("len", 0) > 1500]
            fps = {k for h in hit_paths for k in (h.get("fp") or {})}
            rec["midware_hint"] = sorted(fps)
            results.append(rec)
            print(f"    home={rec['home_status']}/{rec['home_len']}B "
                  f"links={len(links)} hd_paths_200={len(hit_paths)} "
                  f"fp={sorted(fps)}", flush=True)
            time.sleep(PAUSE)

    out = HERE / "province-platform-hunt-stage1.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    reach = [r for r in results if r.get("home_status") == 200]
    dead = [r["domain"] for r in results if r.get("home_status") is None]
    print(f"\n[stage1] {len(results)} 省，可达 {len(reach)}，不可达 {len(dead)}: {dead}")
    print(f"[stage1] 证据已写 {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
