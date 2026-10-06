"""E1 配套：生成**人工抽查清单**（外部评估要的"质量闸门"，30~50 条）。

⚠ **这一项只能由人做。** 本脚本只负责把清单做成一页可勾选的表格，
   **不产生任何"已确认"的判定** —— 填完之后由人回填，判定才算数。

抽样规则（为了让人在有限时间里看得最准）：
 · **一条独立条文最多出一题**（171 条问法只落在 79 条独立条文上 ⇒ 不许同一条文反复问）；
 · 按类型分层：定义 / 要求 按总体比例分配；
 · 跨文档铺开；固定随机种子，可复算。

产出：
 · `human-check.csv` —— 直接填（Excel 打开，判定列填 对 / 错 / 多个都对 / 说不清）
 · `human-check.md`  —— 同一份内容，方便直接读

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\exp-1-contextual\\05-human-check.py [--n 40]
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--seed", type=int, default=20261006)
    args = ap.parse_args()

    v2 = [json.loads(l) for l in (HERE.parent / "benchmark-v2.jsonl").read_text(encoding="utf-8").splitlines()
          if l.strip()]

    # 一条独立条文只留一题（优先留 3/3 一致且无 gold 唯一性标记的）
    by_clause: dict[tuple, list[dict]] = defaultdict(list)
    for it in v2:
        by_clause[(it["gold_std"], str(it["gold_clause"]))].append(it)

    def prio(it: dict) -> tuple:
        flags = set(it["v2"]["flags"])
        return (0 if it["v2"]["bucket"] == "keep" else 1,
                1 if ({"gold_multi_def", "gold_dup_text"} & flags) else 0,
                it["i"])

    pool = [sorted(v, key=prio)[0] for v in by_clause.values()]
    rnd = random.Random(args.seed)

    # 分层：按 kind 的总体比例分配名额
    want_def = round(args.n * sum(1 for x in v2 if x["kind"] == "定义") / len(v2))
    picked: list[dict] = []
    for kind, quota in (("定义", want_def), ("要求", args.n - want_def)):
        sub = [x for x in pool if x["kind"] == kind]
        # 跨文档铺开：每个文档最多连续取
        rnd.shuffle(sub)
        seen_doc: dict[str, int] = defaultdict(int)
        chosen = []
        for x in sorted(sub, key=lambda y: seen_doc[y["v2"]["gold_doc_id"]]):
            if len(chosen) >= quota:
                break
            seen_doc[x["v2"]["gold_doc_id"]] += 1
            chosen.append(x)
        picked.extend(chosen)
    picked.sort(key=lambda x: x["i"])

    csv_path = HERE / "human-check.csv"
    md_path = HERE / "human-check.md"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["序号", "问法（用户原话）", "标准号", "条款号", "条文原文",
                    "你的判断（对 / 错 / 多个都对 / 说不清）", "备注"])
        for k, it in enumerate(picked, 1):
            w.writerow([k, it["query"], it["gold_std"], it["gold_clause"],
                        (it.get("gold_text") or "").replace("\r", ""), "", ""])

    lines = [
        "# 人工抽查清单（E1 的质量闸门）",
        "",
        f"**共 {len(picked)} 条。** 每条只问一件事：",
        "",
        "> **这个问法，答案真的是右边这条条文吗？**",
        "",
        "**怎么填**：在最后一列写 `对` / `错` / `多个都对` / `说不清`。",
        "",
        "- `错` ⇒ 这条 gold 不该用（会污染 A/B 实验的结论）；",
        "- `多个都对` ⇒ 说明库里不止一条合理答案 → 同样要标出来；",
        "- `说不清` ⇒ 也照填，**不要猜**。",
        "",
        "**⚠ 这不是重新做一套考卷**，只是回答\"我们现在是不是在拿错误目标调系统\"。",
        f"抽样：一条独立条文最多一题、按定义/要求分层、跨文档铺开（随机种子 {args.seed}，可复算）。",
        "",
        f"填完后请回填到 `human-check.csv`（同一份内容），我再把结果算进报告。",
        "",
        "| # | 问法（用户原话） | 正确条文 | 条文原文 | 判断 |",
        "|---|---|---|---|---|",
    ]
    for k, it in enumerate(picked, 1):
        txt = (it.get("gold_text") or "").replace("\n", " ").strip()
        if len(txt) > 180:
            txt = txt[:180] + "…"
        lines.append(f"| {k} | {it['query']} | {it['gold_std']} {it['gold_clause']} | {txt} |  |")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    n_def = sum(1 for x in picked if x["kind"] == "定义")
    print(f"[human] 抽出 {len(picked)} 条（定义 {n_def} / 要求 {len(picked)-n_def}）；"
          f"覆盖 {len({(x['gold_std'], x['gold_clause']) for x in picked})} 条独立条文、"
          f"{len({x['v2']['gold_doc_id'] for x in picked})} 篇文档")
    print(f"[human] 已写 {csv_path}")
    print(f"[human] 已写 {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
