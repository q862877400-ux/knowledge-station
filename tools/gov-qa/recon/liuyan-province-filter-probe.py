"""试 df 列表是否支持「按省过滤」（能的话，一个省的地市数据可成片取）。

已知：df 不带 fid = 全国时间流（实测被北京版块占满）；带 fid = 单版块。
未知：有没有「按省聚合」的参数（父 fid / 省 id 之类）。
本脚本对候选参数各试一次，看返回是否**跨多个地市**（跨市 = 命中了省聚合）。
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ["NO_PROXY"] = (os.environ.get("NO_PROXY") or "").replace("[::1]", "::1")

sys.path.insert(0, str(HERE.parent))
from adapters._liuyan_common import BASE, _envelope, _headers  # noqa: E402

# 用广东省做实验：省委书记 fid=575、省长=576
CANDS = [
    {"pFid": "575"}, {"parentFid": "575"}, {"parentId": "575"}, {"pid": "575"},
    {"provinceId": "575"}, {"provinceFid": "575"}, {"areaId": "575"},
    {"fid": "575", "withSub": 1}, {"fid": "575", "includeSub": 1},
    {"fid": "575", "deep": 1},
]


def main() -> int:
    import httpx

    out = []
    with httpx.Client(trust_env=False, timeout=20) as c:
        for param in CANDS:
            p = {"showUnAnswer": 0, "lastItem": "", "position": 1,
                 "rows": 10, "orderType": 2}
            p.update(param)
            path = "/v1/threads/list/df"
            rec = {"param": param}
            try:
                r = c.post(BASE + path, content=_envelope(path, p),
                           headers=_headers(f"{BASE}/threads/list"))
                rec["status"] = r.status_code
                if "json" in r.headers.get("content-type", ""):
                    data = ((r.json().get("resultData") or {}).get("data")) or []
                    rec["n"] = len(data)
                    pns = {tuple(x.get("pForumNames") or []) for x in data}
                    rec["distinct_forums"] = len(pns)
                    rec["sample"] = [list(x)[:2] for x in list(pns)[:4]]
            except Exception as e:                                          # noqa: BLE001
                rec["error"] = type(e).__name__
            out.append(rec)
            print(json.dumps(rec, ensure_ascii=False).encode("ascii", "replace").decode()[:200],
                  flush=True)
            # 判据：返回里出现「广东省」才说明该参数真的按省过滤
            hit_gd = any("广东" in str(x) for x in (rec.get("sample") or []))
            if rec.get("n") and hit_gd:
                print("   [HIT] returned Guangdong items -> province filter works")
                break
            time.sleep(2)
    (HERE / "liuyan-province-filter-probe.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    main()
