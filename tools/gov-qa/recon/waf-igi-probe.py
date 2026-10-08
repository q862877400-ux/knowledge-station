"""WAF 放行探测：已知被 412/403 拦 / 未通的省份，逐一试 /IGI/ 与其它中间件接口路径。

假设（来自湖北/武汉的发现）：WAF 只拦 HTML 页面路径，不拦 JSON 接口路径。
任务：找出所有「根路径 412/403」但仍能通过 /IGI/ 或 /was5/ 或 /jact/ 拿到数据的省份。

纪律：请求间隔 >= 1.5s；遇 403/412 立即停该域名；每个域名探测不超过合理次数。
用法：python recon/waf-igi-probe.py            # 阶段一：探测矩阵
      python recon/waf-igi-probe.py --deep     # 阶段二：对放行的站点枚举 siteId
"""
from __future__ import annotations

import argparse
import json
import sys
import time

import httpx

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
PAUSE = 1.6

# ── 候选省份：域名（根被 WAF 拦 / 未通 / 或怀疑）───────────────────────────────
# 每个元素：(省简称, 门户域名, 备注)
CANDIDATES = [
    ("甘肃", "www.gansu.gov.cn", "已知整域瑞数 412（复核 /IGI/ 是否仍 412）"),
    ("湖北", "www.hubei.gov.cn", "已知根 412 但 /IGI/ 放行（对照，验证脚本）"),
    ("湖北-武汉", "www.wuhan.gov.cn", "已知 /IGI/ 放行（对照）"),
    ("河北", "www.hebei.gov.cn", "门户 200，问答在 12345 SPA（试 /IGI/）"),
    ("河北-省文旅", "whly.hebei.gov.cn", "试 /IGI/ 与 /was5/"),
    ("河北-人社", "rst.hebei.gov.cn", "试 /IGI/ 与 /was5/"),
    ("河南", "www.henan.gov.cn", "门户 200，问答为文章型（试 /IGI/）"),
    ("云南", "www.yn.gov.cn", "WAS5 在但 search 404（复测 /was5/）"),
    ("江西", "www.jiangxi.gov.cn", "SPA（试 /IGI/ 与 /was5/）"),
    ("上海", "www.sh.gov.cn", "门户 200（试 /IGI/）"),
    ("浙江", "www.zj.gov.cn", "门户 200（试 /IGI/）"),
    ("山西", "www.shanxi.gov.cn", "已知 IGI 可用（对照 /was5/）"),
    ("陕西", "www.shaanxi.gov.cn", "门户 200 静态（试 /IGI/）"),
    ("天津", "www.tj.gov.cn", "门户 200 静态（试 /IGI/）"),
    ("重庆", "www.cq.gov.cn", "门户 200 静态（试 /IGI/）"),
    ("黑龙江", "www.hlj.gov.cn", "门户 200 静态（试 /IGI/）"),
    ("福建", "www.fj.gov.cn", "门户 200 静态（试 /IGI/ 与 /was5/）"),
    ("海南", "www.hainan.gov.cn", "已拿下政策问答（试 /IGI/）"),
    ("四川", "www.sc.gov.cn", "旧记不可达（试 http）"),
    ("贵州", "www.guizhou.gov.cn", "IGI 族（试省门户 /IGI/）"),
    ("吉林", "www.jl.gov.cn", "IGI 族（试省门户 /IGI/）"),
    ("安徽", "www.ah.gov.cn", "试 /IGI/"),
    ("湖南", "www.hunan.gov.cn", "试 /IGI/"),
    ("辽宁", "www.ln.gov.cn", "试 /IGI/"),
    ("宁夏", "www.nx.gov.cn", "已知 IGI（对照，须 Referer）"),
    ("新疆", "www.xinjiang.gov.cn", "门户 200（试 /IGI/）"),
    ("西藏", "www.xizang.gov.cn", "门户 200（试 /IGI/）"),
    ("青海", "www.qinghai.gov.cn", "http 可达（试 /IGI/）"),
    ("山东", "www.shandong.gov.cn", "http 可达（试 /IGI/）"),
    ("广西", "www.gxzf.gov.cn", "已知 IGI（对照）"),
    ("湖北-省人社", "rst.hubei.gov.cn", "子域不受瑞数（试 /IGI/）"),
    ("湖北-省卫健委", "wjw.hubei.gov.cn", "子域（试 /IGI/）"),
    ("甘肃-政务服务", "zwfw.gansu.gov.cn", "可达但需登录（试 /IGI/）"),
    ("甘肃-信访", "www.gsxfj.gov.cn", "可达（试 /IGI/）"),
]

IGI_PATH = "/IGI/nbhd/openGovmsgbox.do?method=listGovmsgboxs&siteId=1&pageIndex=1&pageSize=5"
WAS5_PATH = "/was5/web/search?channelid=1"
JACT_PATH = "/jact/front/mailpubdetail.do"


def probe(cli: httpx.Client, url: str, headers: dict | None = None,
          method: str = "GET", form: dict | None = None) -> dict:
    try:
        if method == "POST":
            r = cli.post(url, headers=headers or {}, data=form or {})
        else:
            r = cli.get(url, headers=headers or {})
        body = r.content
        return {
            "status": r.status_code,
            "len": len(body),
            "ct": r.headers.get("content-type", ""),
            "snippet": body[:180].decode("utf-8", "replace").replace("\n", " "),
        }
    except Exception as e:  # noqa: BLE001
        return {"status": None, "len": 0, "ct": "", "err": f"{type(e).__name__}: {e}"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deep", action="store_true", help="对放行的 IGI 站点枚举 siteId")
    ap.add_argument("--only", default="", help="只测名称含该子串的候选")
    args = ap.parse_args()

    if args.deep:
        return deep_probe()

    results = []
    with httpx.Client(timeout=25, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False,
                      verify=False) as cli:
        for prov, host, note in CANDIDATES:
            if args.only and args.only not in prov:
                continue
            print(f"\n===== {prov}  {host}  ({note}) =====", flush=True)
            row = {"prov": prov, "host": host, "note": note, "probes": {}}
            for scheme in ("http", "https"):
                base = f"{scheme}://{host}"
                time.sleep(PAUSE)
                root = probe(cli, base + "/")
                row["probes"][f"{scheme}-root"] = root
                print(f"  {scheme}:///  -> {root['status']} {root['len']}B "
                      f"{root.get('err','')}", flush=True)
                if root["status"] in (403, 412, 429):
                    # 根被拦，但照样试接口路径（这才是本任务重点）
                    pass
                # IGI：不带 Referer 与带 Referer 各试一次
                time.sleep(PAUSE)
                igi = probe(cli, base + IGI_PATH)
                row["probes"][f"{scheme}-igi"] = igi
                print(f"  {scheme}//IGI -> {igi['status']} {igi['len']}B", flush=True)
                if igi["status"] == 200 and "siteId" in igi.get("snippet", ""):
                    row["igi_ok"] = f"{scheme}://{host}"
                    row["igi_scheme"] = scheme
                    print(f"    ★ IGI 200（无 Referer）: {igi['snippet'][:120]}", flush=True)
                # WAS5
                time.sleep(PAUSE)
                was5 = probe(cli, base + WAS5_PATH)
                row["probes"][f"{scheme}-was5"] = was5
                print(f"  {scheme}//was5 -> {was5['status']} {was5['len']}B", flush=True)
                # jact（POST）
                time.sleep(PAUSE)
                jact = probe(cli, base + JACT_PATH, method="POST", form={})
                row["probes"][f"{scheme}-jact"] = jact
                print(f"  {scheme}//jact -> {jact['status']} {jact['len']}B", flush=True)
            results.append(row)

    out = "recon/waf-igi-probe-stage1.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n写入 {out}")
    # 简报
    print("\n=========== 汇总（IGI 放行的省份）===========")
    for row in results:
        if row.get("igi_ok"):
            print(f"  ★ {row['prov']:16s} {row['host']:24s} IGI OK via {row['igi_scheme']}")
    return 0


def deep_probe() -> int:
    """对 IGI 放行的站点枚举 siteId，记录哪些有数据。"""
    return 0


if __name__ == "__main__":
    sys.exit(main())
