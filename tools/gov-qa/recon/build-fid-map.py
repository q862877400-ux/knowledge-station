"""从已采的留言板数据生成「省市 → fid」映射表（供 people-liuyan-fid 定向采集）。

数据来源：`data/people-liuyan-df-*.jsonl` 每行的 `extra.fid` + `extra.pForumNames`
（省→市→县）+ `dept`（承办单位）。
产出：`recon/liuyan-fid-map.json`，按 (省, 承办单位) 去重，附已采条数。
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
OUT = HERE / "liuyan-fid-map.json"


def main() -> int:
    rows = []
    for p in DATA.glob("people-liuyan-df-*.jsonl"):
        rows += [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()
                 if l.strip()]
    agg: dict[tuple, dict] = {}
    prov_counter: Counter = Counter()
    for r in rows:
        e = r.get("extra") or {}
        fid = e.get("fid")
        if not fid:
            continue
        pn = e.get("pForumNames") or []
        province = pn[0] if pn else None
        city = pn[1] if len(pn) > 1 else None
        label = r.get("dept") or province or str(fid)
        key = (province, label)
        item = agg.setdefault(key, {"fid": str(fid), "label": label,
                                    "province": province, "city": city, "n": 0})
        item["n"] += 1
        prov_counter[province or "（无）"] += 1
    out = sorted(agg.values(), key=lambda x: (-x["n"], str(x["province"])))
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[fid-map] 版块 {len(out)} 个（来自 {len(rows)} 条记录），"
          f"覆盖省级单位 {len(prov_counter)} 个")
    for p, n in prov_counter.most_common():
        print(f"   {p}: {n} 条")
    print("written", OUT)
    return 0


if __name__ == "__main__":
    main()
