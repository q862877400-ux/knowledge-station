"""省 / 省会门户 IGI 平台**横向普查**（2026-10-09 新增）。

## 为什么做这个
§十四 证明：山西 / 广西 / 宁夏三省门户挂着 IGI（`/IGI/nbhd/openGovmsgbox.do`），
一省就是 **46/208/64 个 siteId、8.4 万 / 3.5 万 / 1.3 万条**，远超本模块任何单站。
⇒ 该平台极可能也挂在**别的省门户**上，只是从没人试过。
本脚本对「尚未确认有 IGI 适配器」的门户逐个打一发列表请求，判定是否 IGI。

★ 2026-10-09 上午场：`province` 集已跑完 ⇒ 命中 **内蒙古、天津**（详见 SITE-REGISTRY §十五）。
  同日补 `city` 集（省会 + 计划单列市）—— 既然内蒙古门户有，呼市/包头等**市级门户可能另有实例**。

## 判定口径（三种结果，不含糊）
 · `IGI`    ：HTTP 200 且返回体含 `datas`（IGI 特征）⇒ **有戏，去跑 igi-siteid-scan.py**
 · `NO`     ：HTTP 200 但不是 IGI 体 / 404 / 跳首页
 · `BLOCK`  ：403 / 412 / 超时 ⇒ 需带 Referer 或换 UA 再试，**不等于没有**

用法：
  .venv/Scripts/python.exe tools/gov-qa/recon/igi-portal-sweep.py            # 省门户（默认）
  .venv/Scripts/python.exe tools/gov-qa/recon/igi-portal-sweep.py city       # 省会 + 计划单列市
产出：`recon/igi-portal-sweep[-city].json`
纪律：请求间隔 1.5s，只打列表第 1 页 pageSize=1，不落语料。
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent

os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
PAUSE = 1.5

#: 省门户 (tag, base, referer)。已确认有 IGI 的不再列（山西/广西/宁夏/西藏/贵州/湖北/重庆/陕西/吉林）。
PORTALS = [
    ("beijing",   "https://www.beijing.gov.cn", "https://www.beijing.gov.cn/"),
    ("tianjin",   "https://www.tj.gov.cn",      "https://www.tj.gov.cn/"),
    ("hebei",     "https://www.hebei.gov.cn",   "https://www.hebei.gov.cn/"),
    ("neimenggu", "https://www.nmg.gov.cn",     "https://www.nmg.gov.cn/zmhd/"),
    ("liaoning",  "https://www.ln.gov.cn",      "https://www.ln.gov.cn/"),
    ("heilongjiang", "https://www.hlj.gov.cn",  "https://www.hlj.gov.cn/"),
    ("shanghai",  "https://www.sh.gov.cn",      "https://www.sh.gov.cn/"),
    ("jiangsu",   "https://www.jiangsu.gov.cn", "https://www.jiangsu.gov.cn/"),
    ("zhejiang",  "https://www.zj.gov.cn",      "https://www.zj.gov.cn/"),
    ("anhui",     "https://www.ah.gov.cn",      "https://www.ah.gov.cn/"),
    ("fujian",    "https://www.fj.gov.cn",      "https://www.fj.gov.cn/"),
    ("jiangxi",   "https://www.jiangxi.gov.cn", "https://www.jiangxi.gov.cn/"),
    ("shandong",  "https://www.shandong.gov.cn", "https://www.shandong.gov.cn/"),
    ("henan",     "https://www.henan.gov.cn",   "https://www.henan.gov.cn/"),
    ("hunan",     "https://www.hunan.gov.cn",   "https://www.hunan.gov.cn/"),
    ("guangdong", "https://www.gd.gov.cn",      "https://www.gd.gov.cn/"),
    ("hainan",    "https://www.hainan.gov.cn",  "https://www.hainan.gov.cn/"),
    ("sichuan",   "https://www.sc.gov.cn",      "https://www.sc.gov.cn/"),
    ("yunnan",    "https://www.yn.gov.cn",      "https://www.yn.gov.cn/"),
    ("gansu",     "https://www.gansu.gov.cn",   "https://www.gansu.gov.cn/"),
    ("qinghai",   "https://www.qinghai.gov.cn", "https://www.qinghai.gov.cn/"),
    ("xinjiang",  "https://www.xinjiang.gov.cn", "https://www.xinjiang.gov.cn/"),
]

#: 省会 + 计划单列市门户。⚠ 武汉/重庆已知有 IGI（hb-wuhan / cq-igi），不再列。
CITY_PORTALS = [
    ("shijiazhuang", "https://www.sjz.gov.cn",      "https://www.sjz.gov.cn/"),
    ("taiyuan",      "https://www.taiyuan.gov.cn",  "https://www.taiyuan.gov.cn/"),
    ("huhhot",       "https://www.huhhot.gov.cn",   "https://www.huhhot.gov.cn/"),
    ("baotou",       "https://www.baotou.gov.cn",   "https://www.baotou.gov.cn/"),
    ("shenyang",     "https://www.shenyang.gov.cn", "https://www.shenyang.gov.cn/"),
    ("dalian",       "https://www.dl.gov.cn",       "https://www.dl.gov.cn/"),
    ("changchun",    "https://www.changchun.gov.cn", "https://www.changchun.gov.cn/"),
    ("harbin",       "https://www.harbin.gov.cn",   "https://www.harbin.gov.cn/"),
    ("nanjing",      "https://www.nanjing.gov.cn",  "https://www.nanjing.gov.cn/"),
    ("hangzhou",     "https://www.hangzhou.gov.cn", "https://www.hangzhou.gov.cn/"),
    ("ningbo",       "https://www.ningbo.gov.cn",   "https://www.ningbo.gov.cn/"),
    ("hefei",        "https://www.hefei.gov.cn",    "https://www.hefei.gov.cn/"),
    ("fuzhou",       "https://www.fuzhou.gov.cn",   "https://www.fuzhou.gov.cn/"),
    ("xiamen",       "https://www.xm.gov.cn",       "https://www.xm.gov.cn/"),
    ("nanchang",     "https://www.nc.gov.cn",       "https://www.nc.gov.cn/"),
    ("jinan",        "https://www.jinan.gov.cn",    "https://www.jinan.gov.cn/"),
    ("qingdao",      "https://www.qingdao.gov.cn",  "https://www.qingdao.gov.cn/"),
    ("zhengzhou",    "https://www.zhengzhou.gov.cn", "https://www.zhengzhou.gov.cn/"),
    ("changsha",     "https://www.changsha.gov.cn", "https://www.changsha.gov.cn/"),
    ("guangzhou",    "https://www.gz.gov.cn",       "https://www.gz.gov.cn/"),
    ("shenzhen",     "https://www.sz.gov.cn",       "https://www.sz.gov.cn/"),
    ("nanning",      "https://www.nanning.gov.cn",  "https://www.nanning.gov.cn/"),
    ("haikou",       "https://www.haikou.gov.cn",   "https://www.haikou.gov.cn/"),
    ("chengdu",      "https://www.chengdu.gov.cn",  "https://www.chengdu.gov.cn/"),
    ("guiyang",      "https://www.guiyang.gov.cn",  "https://www.guiyang.gov.cn/"),
    ("kunming",      "https://www.km.gov.cn",       "https://www.km.gov.cn/"),
    ("lasa",         "https://www.lasa.gov.cn",     "https://www.lasa.gov.cn/"),
    ("xian",         "https://www.xa.gov.cn",       "https://www.xa.gov.cn/"),
    ("lanzhou",      "https://www.lanzhou.gov.cn",  "https://www.lanzhou.gov.cn/"),
    ("xining",       "https://www.xining.gov.cn",   "https://www.xining.gov.cn/"),
    ("yinchuan",     "https://www.yinchuan.gov.cn", "https://www.yinchuan.gov.cn/"),
    ("urumqi",       "https://www.urumqi.gov.cn",   "https://www.urumqi.gov.cn/"),
    ("suzhou",       "https://www.suzhou.gov.cn",   "https://www.suzhou.gov.cn/"),
    ("wuxi",         "https://www.wuxi.gov.cn",     "https://www.wuxi.gov.cn/"),
]

LIST = ("{base}/IGI/nbhd/openGovmsgbox.do?method=listGovmsgboxs"
        "&siteId=1&order=1&appId=&pageIndex=1&pageSize=1")


def main() -> int:
    import httpx

    which = (sys.argv[1] if len(sys.argv) > 1 else "province").strip().lower()
    targets = CITY_PORTALS if which == "city" else PORTALS
    suffix = "-city" if which == "city" else ""
    out: dict[str, dict] = {}
    with httpx.Client(timeout=25, headers={"User-Agent": UA},
                      follow_redirects=True, trust_env=False, verify=False) as cli:
        for tag, base, ref in targets:
            time.sleep(PAUSE)
            rec = {"base": base, "verdict": "NO", "http": None, "total": None, "note": ""}
            try:
                r = cli.get(LIST.format(base=base), headers={"Referer": ref})
                rec["http"] = r.status_code
                if r.status_code == 200:
                    try:
                        j = r.json()
                    except Exception:                                        # noqa: BLE001
                        rec["verdict"] = "NO"
                        rec["note"] = "200 但非 JSON（多半是首页 HTML）"
                    else:
                        if isinstance(j, dict) and "datas" in j:
                            pi = (j.get("datas") or {}).get("pageInfo") or {}
                            rec["verdict"] = "IGI"
                            rec["total"] = pi.get("totalResults")
                            rec["note"] = "★ 命中 IGI 平台"
                        else:
                            rec["note"] = f"200 JSON 但无 datas 键（键={list(j)[:6]}）"
                elif r.status_code in (403, 412):
                    rec["verdict"] = "BLOCK"
                    rec["note"] = "反爬拦截，需换 Referer/UA 复测"
                else:
                    rec["note"] = f"HTTP {r.status_code}"
            except Exception as e:                                           # noqa: BLE001
                rec["verdict"] = "BLOCK"
                rec["note"] = f"{type(e).__name__}: {e}"
            out[tag] = rec
            print(f"  [{tag:12s}] {rec['verdict']:5s} http={rec['http']} "
                  f"total={rec['total']} {rec['note']}", flush=True)

    p = HERE / f"igi-portal-sweep{suffix}.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    hit = [k for k, v in out.items() if v["verdict"] == "IGI"]
    print(f"==> IGI 命中 {len(hit)} 个：{hit}  -> {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
