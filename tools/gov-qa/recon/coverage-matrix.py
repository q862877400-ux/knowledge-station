"""全国覆盖矩阵：把 data/ 里全部语料按**省级归属 × 来源**汇总成一张表。

归属判定（从强到弱）：
  1. `extra.pForumNames[0]`（留言板地方流自带省→市→县链）；
  2. `extra.fid_label` / `dept` 里的省市名（留言板定向版块）；
  3. 来源前缀：`gd-*` → 广东省；`hunan-*` → 湖南省；`gz-*` → 贵州省；`jl-*` → 吉林省……
     ⚠ 这一层**必须有**：IGI 站的**旧信**（如 gz-zrzy 的 2020 年那批）上游
     `extra.province/city/area` 全是空串，拿不到第 1/2 层的链，只能靠来源前缀归省。
     表里同时放「精确来源」与「省级简称族」两级 —— 新增同省适配器时族级已兜住，
     不必再改这张表（2026-10-08 就是漏改这张表，让 gz-zrzy 524 条掉进「未归属」）。
  4. 国家级来源（`mee`/`mem`/`people-liuyan`）→ 「国家级（部委）」。
产出：`recon/coverage-matrix.json`（机器可读）+ `recon/coverage-matrix.md`（人看）。
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"

PROVINCE_PREFIX = {
    # —— 精确到来源（优先匹配）——
    "sc-st": "四川省", "ah-st": "安徽省", "ln-st": "辽宁省",
    "gz-st": "贵州省", "gz-wjw": "贵州省", "gz-jyt": "贵州省", "gz-rst": "贵州省",
    "gz-zfcx": "贵州省", "gz-nynct": "贵州省", "gz-swt": "贵州省", "gz-zrzy": "贵州省",
    "jl-st": "吉林省", "jl-wjw": "吉林省", "jl-hrss": "吉林省", "jl-jt": "吉林省",
    # —— 省级简称族（兜底；新增同省适配器时不必再改本表）——
    "gd-": "广东省", "hunan-": "湖南省", "gz-": "贵州省", "jl-": "吉林省",
    "nx-": "宁夏回族自治区", "sx-": "山西省", "js-": "江苏省",
    "tj-": "天津市", "sn-": "陕西省", "cq-": "重庆市",
    "hlj-": "黑龙江省", "fj-": "福建省", "hn-": "河南省",
    "bj-": "北京市", "nmg-": "内蒙古自治区",
    "jx-": "江西省", "yn-": "云南省",
    "sh-": "上海市", "zj-": "浙江省",
    "xj-": "新疆维吾尔自治区", "gx-": "广西壮族自治区", "sd-": "山东省",
    "qh-": "青海省", "hi-": "海南省",
    "heb-": "河北省",
    "ah-": "安徽省", "ln-": "辽宁省", "sc-": "四川省",
    "hb-": "湖北省",
    "xz-": "西藏自治区",
}
NATIONAL = {"mee", "mem", "people-liuyan"}

#: 什么才算省级名（部委流的 pForumNames 装的是部委名，别混进来）
PROV_SUFFIX = ("省", "自治区", "特别行政区")
MUNICIPALITIES = ("北京市", "上海市", "天津市", "重庆市")


def _is_province(name: str) -> bool:
    if not name:
        return False
    if name in MUNICIPALITIES:
        return True
    return name.endswith(PROV_SUFFIX)


def province_of(rec: dict) -> str:
    extra = rec.get("extra") or {}
    pn = extra.get("pForumNames") or []
    if pn and _is_province(str(pn[0])):
        return str(pn[0])
    label = extra.get("fid_label") or ""
    if _is_province(label[:3]) if len(label) >= 3 else False:
        return label[:3]
    src = str(rec.get("source") or "")
    for pre, prov in PROVINCE_PREFIX.items():
        if src.startswith(pre):
            return prov
    if src in NATIONAL:
        return "国家级（部委）"
    return "（未归属）"


def main() -> int:
    matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    totals: dict[str, int] = defaultdict(int)
    src_totals: dict[str, int] = defaultdict(int)
    for f in sorted(DATA.glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            prov = province_of(rec)
            src = str(rec.get("source") or f.stem)
            matrix[prov][src] += 1
            totals[prov] += 1
            src_totals[src] += 1

    out = {"by_province": {p: dict(sorted(s.items(), key=lambda kv: -kv[1]))
                           for p, s in sorted(matrix.items(), key=lambda kv: -sum(kv[1].values()))},
           "province_totals": dict(sorted(totals.items(), key=lambda kv: -kv[1])),
           "source_totals": dict(sorted(src_totals.items(), key=lambda kv: -kv[1])),
           "grand_total": sum(totals.values()),
           "n_provinces_covered": len([p for p in totals if not p.startswith("（") and "国家级" not in p])}
    (HERE / "coverage-matrix.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    lines = ["# 全国覆盖矩阵（省级 × 来源）", "",
             f"语料总计 **{out['grand_total']}** 条；覆盖省级行政区 **{out['n_provinces_covered']}** 个"
             f"（另有「国家级（部委）」一类）。", "",
             "| 省级归属 | 条数 | 来源构成 |", "|---|---|---|"]
    for p, n in out["province_totals"].items():
        comp = "、".join(f"{s} {c}" for s, c in
                        list(out["by_province"][p].items())[:6])
        if len(out["by_province"][p]) > 6:
            comp += f" …共 {len(out['by_province'][p])} 个来源"
        lines.append(f"| {p} | {n} | {comp} |")
    lines += ["", "## 各来源总量", "", "| 来源 | 条数 |", "|---|---|"]
    for s, n in list(out["source_totals"].items())[:60]:
        lines.append(f"| {s} | {n} |")
    (HERE / "coverage-matrix.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[matrix] 总 {out['grand_total']} 条；省级单位 {out['n_provinces_covered']} 个；"
          f"来源 {len(src_totals)} 个")
    for p, n in list(out["province_totals"].items())[:12]:
        print(f"   {p}: {n}")
    print("written recon/coverage-matrix.json + .md")
    return 0


if __name__ == "__main__":
    main()
