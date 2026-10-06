"""E1 结果拆解：把 `ab-result.json` 拆成"能挂回具体数据"的几块。

回答四个问题（全部来自逐条记录，不重新跑检索）：
 1. **按类型**（定义 / 要求）分别看：两臂的 @20/@100/@1000；
 2. **名次分布**：两臂都在前 1000 找到的那些条目，名次是往前往后挪？
 3. **翻进来 / 翻出去**分别是哪些题（附问法与类型），不是只报一个净数；
 4. **那 104 条"六路前 1000 都没有"** 里救回了哪些、同时丢了哪些原本能找到的。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-1-contextual\\09-analyze-ab.py
"""
from __future__ import annotations

import json
import statistics as st
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = HERE / "ab-analysis.json"


def rate(rows, arm, d):
    return round(sum(1 for r in rows if r[arm][f"rank@{d}"]) / len(rows), 4) if rows else None


def main() -> int:
    ab = json.loads((HERE / "ab-result.json").read_text(encoding="utf-8"))
    v2 = {json.loads(l)["i"]: json.loads(l)
          for l in (HERE.parent / "benchmark-v2.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()}
    per = ab["per_query"]
    head = [r for r in per if r["headline"]]

    def block(rows):
        out = {"n": len(rows)}
        for arm in ("base", "ctx"):
            for d in (20, 100, 1000):
                out[f"{arm}@{d}"] = rate(rows, arm, d)
        return out

    by_kind = {k: block([r for r in head if r["kind"] == k]) for k in ("定义", "要求")}

    # 名次分布：两臂都在前 1000 找到的。
    # ⚠ 独立复核 F3：初版只在**全量 171** 上算，却把它挂在"主结果 120 条"标题下面。
    #   现在**两套都出**、各自标明口径。
    def rank_dist_of(rows):
        both = [(r["base"]["rank"], r["ctx"]["rank"]) for r in rows
                if r["base"]["rank"] and r["ctx"]["rank"]]
        deltas = [a - b for a, b in both]        # 正数 = 名次数字变小 = 往前挪
        better = sum(1 for d in deltas if d > 0)
        worse = sum(1 for d in deltas if d < 0)
        return {
            "n_both_found": len(both),
            "base_median_rank": st.median([a for a, _ in both]) if both else None,
            "ctx_median_rank": st.median([b for _, b in both]) if both else None,
            "moved_closer": better, "moved_away": worse, "same": len(both) - better - worse,
            "median_rank_delta_closer_is_positive": st.median(deltas) if deltas else None,
        }

    rank_dist = {
        "all_171": rank_dist_of(per),
        "headline_120": rank_dist_of(head),
        "_note": "两个口径分别给；**引用时必须说清是哪一个**（初版把 171 的数挂在 120 标题下，复核 F3 打回）",
    }

    def describe(r):
        it = v2[r["i"]]
        return {"i": r["i"], "kind": r["kind"],
                "base_rank": r["base"]["rank"], "ctx_rank": r["ctx"]["rank"],
                "query": it["query"][:48],
                "gold": f"{it['gold_std']} {it['gold_clause']}"}

    flips_in = [describe(r) for r in per if not r["base"]["rank@1000"] and r["ctx"]["rank@1000"]]
    flips_out = [describe(r) for r in per if r["base"]["rank@1000"] and not r["ctx"]["rank@1000"]]
    flips_in_h = [describe(r) for r in head if not r["base"]["rank@1000"] and r["ctx"]["rank@1000"]]
    flips_out_h = [describe(r) for r in head if r["base"]["rank@1000"] and not r["ctx"]["rank@1000"]]

    result = {
        "meta": {"source": "ab-result.json", "headline_n": len(head), "all_n": len(per),
                 "_denominators": "凡出现「翻进/翻出」「救回」一律先看这一项属于哪个口径"
                                  "（headline_120 还是 all_171）"},
        "headline_by_kind": by_kind,
        "rank_distribution": rank_dist,
        "flips_at_1000": {
            "all_171": {"in": flips_in, "out": flips_out},
            "headline_120": {"in": flips_in_h, "out": flips_out_h},
        },
        "rescued_from_104": {
            "_scope": "**全量 171 条 + 六路同预算并集 @1000 口径**（不是向量单路，不是 120 条）",
            "n": len(ab.get("rescued_from_104", [])),
            "ids": ab.get("rescued_from_104", []),
        },
        "one_line": (
            f"主结果 {len(head)} 条：Vector@1000 {block(head)['base@1000']:.4f} → {block(head)['ctx@1000']:.4f}"
            f"（净 {round((len(flips_in_h) - len(flips_out_h)) / len(head) * 100, 2)}pt ="
            f" {len(flips_in_h) - len(flips_out_h)} 条，**条数口径**）；"
            f"但 @20 {block(head)['base@20']:.4f} → {block(head)['ctx@20']:.4f}；"
            f"**主结果 120 条口径**下前 1000 翻进 {len(flips_in_h)} / 翻出 {len(flips_out_h)}；"
            f"**全量 171 条口径**下翻进 {len(flips_in)} / 翻出 {len(flips_out)}"
            f"（两个口径不许混着说）"
        ),
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "flips_at_1000"},
                     ensure_ascii=False, indent=1))
    print("\n[翻进前 1000 的]", [(x["i"], x["kind"]) for x in flips_in])
    print("[翻出前 1000 的]", [(x["i"], x["kind"]) for x in flips_out])
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
