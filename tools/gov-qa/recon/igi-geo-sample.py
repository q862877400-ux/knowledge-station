"""IGI 城市门户 **地域真伪**抽样（只读，不落盘语料）。

## 为什么需要它
`recon/igi-city-probe.py` 只看**第一行**的地域 ⇒ 不足以判「真地域 / 单值恒定假地域」。
本仓已有教训：山西 / 内蒙古的 `PROVINCE/CITY/AREA` **逐条恒定 = 门户自身位置**（假，必须剥离），
而广西 / 宁夏 / 湖北 / 南宁是**真实且多变**（保留）。

判据：抽 N 行，统计 distinct(PROVINCE)、distinct(CITY)、distinct(AREA)。
- distinct(PROVINCE)==1 且 distinct(CITY)==1 且 distinct(AREA)==1 ⇒ **恒定 = 假**，剥离。
- AREA 出现多种（且都属本市） ⇒ **真**，保留。

用法：
  .venv/Scripts/python.exe tools/gov-qa/recon/igi-geo-sample.py shenyang nanjing
"""
from __future__ import annotations

import sys
import time
from collections import Counter
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
PAUSE = 1.5

LIST = ("{base}/IGI/nbhd/openGovmsgbox.do?method=listGovmsgboxs"
        "&siteId={sid}&order=1&appId=&pageIndex={pi}&pageSize=20")

TARGETS: dict[str, tuple[str, str, list[str]]] = {
    "shenyang": ("https://www.shenyang.gov.cn", "https://www.shenyang.gov.cn/", ["123", "118"]),
    "nanjing":  ("https://www.nanjing.gov.cn",  "https://www.nanjing.gov.cn/",  ["126", "130"]),
    "nanning":  ("https://www.nanning.gov.cn",  "https://www.nanning.gov.cn/",  ["8"]),
    "baotou":   ("https://www.baotou.gov.cn",   "https://www.baotou.gov.cn/",   ["46", "57"]),
}


def main() -> int:
    tags = sys.argv[1:] or list(TARGETS)
    for tag in tags:
        if tag not in TARGETS:
            print(f"[{tag}] 未知 tag")
            continue
        base, referer, sids = TARGETS[tag]
        for sid in sids:
            prov: Counter = Counter()
            city: Counter = Counter()
            area: Counter = Counter()
            n = 0
            with httpx.Client(timeout=40, headers={"User-Agent": UA},
                              follow_redirects=True, trust_env=False, verify=False) as cli:
                for pi in range(1, 6):          # 5 页 × 20 = 100 行
                    try:
                        r = cli.get(LIST.format(base=base, sid=sid, pi=pi),
                                    headers={"Referer": referer})
                        if r.status_code != 200:
                            print(f"[{tag}/{sid}] 第 {pi} 页 HTTP {r.status_code}，停")
                            break
                        _d = (r.json() or {}).get("datas") or {}
                        # ⚠ 行数组键逐站不同：沈阳/南京是 `data`，别只认 `list`。
                        rows = (_d.get("list") or _d.get("rows")
                                or _d.get("data") or [])
                    except Exception as e:                              # noqa: BLE001
                        print(f"[{tag}/{sid}] 第 {pi} 页异常 {type(e).__name__}: {e}")
                        break
                    if not rows:
                        break
                    for row in rows:
                        n += 1
                        prov[str(row.get("PROVINCE") or "")] += 1
                        city[str(row.get("CITY") or "")] += 1
                        area[str(row.get("AREA") or "")] += 1
                    time.sleep(PAUSE)
            pv = {k: v for k, v in prov.items() if k}
            cv = {k: v for k, v in city.items() if k}
            av = {k: v for k, v in area.items() if k}
            print(f"[{tag}] siteId={sid} 抽 {n} 行")
            print(f"   PROVINCE {len(pv)} 种: {dict(pv)}")
            print(f"   CITY     {len(cv)} 种: {dict(cv)}")
            print(f"   AREA     {len(av)} 种: {dict(sorted(av.items(), key=lambda x: -x[1]))}")
            verdict = "恒定=假(剥离)" if (len(pv) <= 1 and len(cv) <= 1 and len(av) <= 1) else "多变=真(保留)"
            print(f"   ⇒ 判据: {verdict}（非空率 AREA {sum(av.values())}/{n}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
