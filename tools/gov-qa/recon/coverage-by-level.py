"""省市县**三级覆盖**统计：按 `pForumNames` 归属链的层级统计，回答"市县到了没有"。

对每条记录看 `extra.pForumNames`（省→市→县 链）与 `fid_label`：
 · 链长 1 = 只到省；链长 2 = 到市；链长 3+ = 到县/区。
产出 `recon/coverage-by-level.md` + `.json`：总体三级分布、覆盖到的市/县个数、与来源交叉。
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
OUT_MD = HERE / "coverage-by-level.md"
OUT_JSON = HERE / "coverage-by-level.json"


PROV_SUFFIX = ("省", "自治区", "特别行政区")
MUNICIPALITIES = ("北京市", "上海市", "天津市", "重庆市")


def _is_province(name: str) -> bool:
    return bool(name) and (name in MUNICIPALITIES or name.endswith(PROV_SUFFIX))


def level_of(pn: list) -> str:
    n = len([x for x in pn if x])
    if n == 0:
        return "无归属链"
    if n == 1:
        return "省级"
    if n == 2:
        return "省+市/区"
    return "省+市+县"


def main() -> int:
    lv: Counter = Counter()
    lv_by_src: dict[str, Counter] = defaultdict(Counter)
    cities: set = set()
    counties: set = set()
    provinces: set = set()
    samples: dict[str, list] = defaultdict(list)
    total = 0
    for f in sorted(DATA.glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            total += 1
            extra = rec.get("extra") or {}
            pn = [x for x in (extra.get("pForumNames") or []) if x]
            lvl = level_of(pn)
            lv[lvl] += 1
            src = str(rec.get("source") or "?")
            lv_by_src[src][lvl] += 1
            if pn and _is_province(str(pn[0])):
                provinces.add(pn[0])
            if len(pn) >= 2 and _is_province(str(pn[0])):
                cities.add((pn[0], pn[1]))
            if len(pn) >= 3 and _is_province(str(pn[0])):
                counties.add((pn[0], pn[1], pn[2]))
            if len(samples[lvl]) < 3:
                samples[lvl].append({"source": src, "chain": pn,
                                     "dept": rec.get("dept")})
    out = {
        "total": total,
        "by_level": dict(lv),
        "distinct_provinces": len(provinces),
        "distinct_city_pairs": len(cities),
        "distinct_county_triples": len(counties),
        "by_source": {k: dict(v) for k, v in sorted(lv_by_src.items(),
                                                    key=lambda kv: -sum(kv[1].values()))},
        "samples": samples,
    }
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    lines = ["# 省市县三级覆盖", "",
             f"记录总计 **{total}** 条；覆盖省级单位 **{len(provinces)}** 个，"
             f"省市组合 **{len(cities)}** 个，省市县组合 **{len(counties)}** 个。", "",
             "| 归属链层级 | 条数 | 占比 |", "|---|---|---|"]
    for k in ("省级", "省+市/区", "省+市+县", "无归属链"):
        n = lv.get(k, 0)
        lines.append(f"| {k} | {n} | {n / total * 100:.1f}% |" if total else f"| {k} | 0 | - |")
    lines += ["", "## 样例", ""]
    for k, items in samples.items():
        for it in items[:2]:
            lines.append(f"- [{k}] `{it['source']}` {' > '.join(it['chain']) or '（无链）'} "
                         f"（{it['dept'] or '—'}）")
    lines += ["", "## 各来源的层级构成（前 12）", "",
              "| 来源 | 省级 | 省+市 | 省+市+县 | 无链 |", "|---|---|---|---|---|"]
    for src, c in list(out["by_source"].items())[:12]:
        lines.append(f"| {src} | {c.get('省级', 0)} | {c.get('省+市/区', 0)} | "
                     f"{c.get('省+市+县', 0)} | {c.get('无归属链', 0)} |")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[levels] 总 {total} | 省级 {lv.get('省级',0)} | 省+市 {lv.get('省+市/区',0)} | "
          f"省+市+县 {lv.get('省+市+县',0)} | 无链 {lv.get('无归属链',0)}")
    print(f"[levels] 覆盖省级 {len(provinces)} / 省市组合 {len(cities)} / 省市县组合 {len(counties)}")
    print("written recon/coverage-by-level.md + .json")
    return 0


if __name__ == "__main__":
    main()
