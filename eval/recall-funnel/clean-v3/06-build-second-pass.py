"""清洗 v3 · 步骤 6：**生成人工二审表**（外部要求：盲模型初分 → 人二审）。

二审要看的四类（一共约 21 条，一页可勾完）：
 A. **四桶**：唯一判为「金标问题」的那条 + 执行者自报最难判的 2 条；
 B. **三档判法歧义**：跨标准引用那 6 条（算不算 R3）、豁免那 2 条（算不算 R3）；
 C. **疑似解析残留**：4 条（分档执行者报的）；
 D. **A 桶随机抽查 10 条** —— 因为 A 是默认桶，模型可能有「往 A 靠」的倾向（我自己写的边界，必须查）。

⚠ 规则**已冻结**：二审只许**改个案标签**，**不许回头改规则**（外部硬要求）。
输出：`human-second-pass.csv`（可勾选）+ `human-second-pass.md`（一页看完）。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\clean-v3\\06-build-second-pass.py
"""
from __future__ import annotations

import csv
import json
import random
import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
BENCH = ROOT / "eval" / "recall-funnel" / "benchmark-v3.jsonl"
BUCKET_IN = HERE / "bucket-input.jsonl"
BUCKET_LAB = HERE / "bucket-labels.jsonl"
TIER_LAB = HERE / "tier-labels.jsonl"
OUT_CSV = HERE / "human-second-pass.csv"
OUT_MD = HERE / "human-second-pass.md"
SEED = 20261007


def main() -> int:
    bench = {json.loads(l)["i"]: json.loads(l)
             for l in BENCH.read_text(encoding="utf-8").splitlines() if l.strip()}
    binp = {json.loads(l)["id"]: json.loads(l)
            for l in BUCKET_IN.read_text(encoding="utf-8").splitlines() if l.strip()}
    blab = {json.loads(l)["id"]: json.loads(l)
            for l in BUCKET_LAB.read_text(encoding="utf-8").splitlines() if l.strip()}
    tlab = {json.loads(l)["id"]: json.loads(l)
            for l in TIER_LAB.read_text(encoding="utf-8").splitlines() if l.strip()}

    rows = []

    def add(kind, tid, question_zh, model_call, detail, options):
        rows.append({"类别": kind, "编号": tid, "要你回答的问题": question_zh,
                     "盲模型判的": model_call, "依据/原文": detail[:300],
                     "你的裁定（照下面选项写）": "" , "选项": options})

    # A. 四桶二审
    for bid in ("f11", "f28", "f31"):
        if bid in blab:
            r = binp[bid]
            add("A·四桶", bid,
                "这条的正确答案（下面的条文）到底对不对？",
                f"{blab[bid]['bucket']} —— {blab[bid]['reason'][:120]}",
                f"问：{r['query']}\n答({r['gold_std']} {r['gold_clause']})：{r['gold_text']}",
                "对 / 错 / 多个都对 / 说不清")

    # B. 三档判法歧义
    for qid in ("q143", "q162", "q144", "q151", "q161", "q165", "q141", "q142"):
        if qid in tlab:
            i = int(qid[1:])
            t = bench.get(i, {})
            add("B·三档歧义", qid,
                "这条要求算「R3 复杂规范关系」还是「R1 原子要求／R2 条件复合」？",
                f"{tlab[qid]['tier']} —— {tlab[qid]['reason'][:120]}",
                (t.get("gold_text") or "")[:300],
                "R1 / R2 / R3")

    # C. 疑似解析残留
    for qid in ("q163", "q164", "q166", "q167"):
        i = int(qid[1:])
        b = bench.get(i, {})
        add("C·解析残留", qid,
            "这条条文内容是**实质条文**还是**解析残留**（标题/空壳）？",
            "分档执行者报：疑似解析残留，已照判未跳过",
            (b.get("gold_text") or "")[:300],
            "实质条文 / 解析残留 / 说不清")

    # D. A 桶随机抽查
    a_ids = sorted(k for k, v in blab.items() if v["bucket"] == "A")
    rnd = random.Random(SEED)
    for bid in rnd.sample(a_ids, min(10, len(a_ids))):
        r = binp[bid]
        add("D·A桶抽查", bid,
            "盲模型说这条只是『字面对不上』、条文本身是对的 —— 你同意吗？",
            f"A —— {blab[bid]['reason'][:110]}",
            f"问：{r['query']}\n答({r['gold_std']} {r['gold_clause']})：{r['gold_text']}",
            "同意(A) / 其实是金标问题(D) / 条款无信息(B) / 标准找错(C)")

    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["类别", "编号", "要你回答的问题", "盲模型判的",
                                           "依据/原文", "你的裁定（照下面选项写）", "选项"])
        w.writeheader()
        for r in rows:
            w.writerow(r)

    lines = [
        "# 人工二审表（清洗 v3 · 盲模型初分 → 人二审）",
        "",
        f"**共 {len(rows)} 条，一页可答完。** 规则**已冻结**（sha256 `d1d43346…`）：",
        "",
        "> **你只许改「个案标签」，不许回头改规则** —— 这是外部评估的硬要求。",
        "",
        "| 类别 | 编号 | 要你回答的问题 | 盲模型判的 | 你的裁定 |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        q = r["要你回答的问题"]
        m = r["盲模型判的"].replace("|", "/")
        lines.append(f"| {r['类别']} | {r['编号']} | {q} | {m[:110]} |  |")
    lines += [
        "",
        "## 为什么要你二审（三条理由，都是我自己写的边界，不是客套）",
        "",
        "1. **四桶里 A 是默认桶**：50 条里 49 条判了 A。模型可能有「往 A 靠」的倾向 ⇒ 专门抽查了 10 条 A。",
        "2. **三档判法有一处真歧义**：『应符合 GB/T 3811 的相关规定』这类**跨标准引用**算不算 R3 —— "
        "若不算，那几条落 R1，**「本批没有 R1」这个结论就会变**。",
        "3. **D 桶只有 1 条，而执行者自己说拿不准** —— 这一条直接决定「金标问题占比」这个说法成不成立。",
        "",
        "## 填完请回填 `human-second-pass.csv` 的最后一列",
        "",
        "选项就写在每行的「选项」列里（例如 `对 / 错 / 多个都对 / 说不清`）。",
        "**照填就行，包括「说不清」** —— 不确定的照实写，比猜一个更有用。",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[second-pass] 已写 {OUT_CSV.name}（{len(rows)} 行）与 {OUT_MD.name}")
    from collections import Counter
    print("[second-pass] 分类计数 =", dict(Counter(r["类别"] for r in rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
