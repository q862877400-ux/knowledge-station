"""清洗 v3 · 步骤 4：用清洗后的金标给 E1 **重打分**（分层汇报，只当探索）。

外部评估明确：
 · "用 v2 金标对 E1 重新打分，不用重算向量"；
 · "结果只当探索，**不改写判决**；想翻案必须预登记新实验"。

因此本脚本**只做一件事**：把 `ab-result.json` 的逐条结果，按 `benchmark-v3.jsonl` 的
**分层标签**重新汇总（kind / 要求类 R1-R3 / 是否疑似解析残留），
并把**独立簇数**一起报出来 —— 因为 120 条只落在 64 个簇上，条目口径会高估信息量。

⚠ 不改任何一个原始数字，只重排呈现；不改 E1 判决。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\clean-v3\\04-rescore-by-stratum.py
"""
from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EXP = ROOT / "eval" / "recall-funnel" / "exp-1-contextual"
OUT = HERE / "e1-rescore-by-stratum.json"

#: 盲执行者报出的**疑似解析残留**（原样采用，不改）；用于敏感性检查
SUSPECT_PARSE = {"q163", "q164", "q166", "q167"}


def main() -> int:
    ab = json.loads((EXP / "ab-result.json").read_text(encoding="utf-8"))
    per = {r["i"]: r for r in ab["per_query"]}
    v3 = {json.loads(l)["i"]: json.loads(l)
          for l in (ROOT / "eval" / "recall-funnel" / "benchmark-v3.jsonl")
          .read_text(encoding="utf-8").splitlines() if l.strip()}

    rows = []
    for i, r in v3.items():
        p = per[i]
        rows.append({
            "i": i, "headline": p["headline"], "kind": r["kind"],
            "tier": r["v3"]["req_tier"], "cluster": r["v2"]["gold_cr_id"],
            "qid": f"q{i}", "suspect": f"q{i}" in SUSPECT_PARSE,
            **{f"{a}@{d}": bool(p[a][f"rank@{d}"]) for a in ("base", "ctx") for d in (20, 100, 1000)},
        })

    def blk(rows, label):
        d = {"label": label, "n_items": len(rows),
             "n_clusters": len({r["cluster"] for r in rows})}
        for dpt in (20, 100, 1000):
            b = sum(1 for r in rows if r[f"base@{dpt}"])
            c = sum(1 for r in rows if r[f"ctx@{dpt}"])
            d[f"@{dpt}"] = {
                "base_n": b, "ctx_n": c,
                "base": round(b / len(rows), 4) if rows else None,
                "ctx": round(c / len(rows), 4) if rows else None,
                "delta_pp": round((c - b) / len(rows) * 100, 2) if rows else None,
                "flip_in": sum(1 for r in rows if not r[f"base@{dpt}"] and r[f"ctx@{dpt}"]),
                "flip_out": sum(1 for r in rows if r[f"base@{dpt}"] and not r[f"ctx@{dpt}"]),
            }
        return d

    head = [r for r in rows if r["headline"]]
    req = [r for r in head if r["kind"] == "要求"]
    defi = [r for r in head if r["kind"] == "定义"]

    result = {
        "why": "外部评估：用清洗后的金标给 E1 重打分，不重算向量，只当探索，不改判决",
        "source": "ab-result.json（E1 逐条名次）+ benchmark-v3.jsonl（v3 分层标签）",
        "unchanged": "本脚本**不修改**任何 E1 原始数字、**不改判决**（判决见 exp-1-contextual/verdict.json）",
        "strata": {
            "headline_120_all": blk(head, "主结果 120 全部"),
            "headline_def": blk(defi, "主结果：定义类"),
            "headline_req_all": blk(req, "主结果：要求类（合计）"),
            "headline_req_R2": blk([r for r in req if r["tier"] == "R2"], "要求类 R2 条件/复合"),
            "headline_req_R3": blk([r for r in req if r["tier"] == "R3"], "要求类 R3 复杂规范关系"),
            "headline_req_R1": blk([r for r in req if r["tier"] == "R1"], "要求类 R1 原子（**本批为 0**）"),
            "sensitivity_excl_suspect_parse": blk(
                [r for r in head if not r["suspect"]], "敏感性：剔除 4 条疑似解析残留后"),
        },
        "reading": [
            "分层后每一格的**条数很小**（要求类总共 22 条、12 簇）⇒ 任何单格差异都在噪声里，**不许当结论**。",
            "价值在于**看结构**：本批**没有 R1（原子要求）** ⇒ 外部假设里『最该受益的那一档』在这套考卷上缺席。",
            "所有分层都报**独立簇数**；条目数 ≠ 信息量（120 条只落在 64 簇上）。",
        ],
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, v in result["strata"].items():
        a = v["@1000"]
        if a["base"] is None:
            print(f"{v['label']:38s} n={v['n_items']:3d} 簇={v['n_clusters']:3d}  **空分层**")
            continue
        print(f"{v['label']:38s} n={v['n_items']:3d} 簇={v['n_clusters']:3d} "
              f"@1000 {a['base']}→{a['ctx']} ({a['delta_pp']:+}pt, "
              f"进{a['flip_in']}/出{a['flip_out']})")
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
