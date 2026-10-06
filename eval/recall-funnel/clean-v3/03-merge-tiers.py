"""清洗 v3 · 步骤 3：**验收并合并盲分档结果**。

做四件事：
 1. **验收**盲执行者的输出（行数 / id 一一对应 / tier 合法 / reason 非空 / 无重复）——
    不合格就不许进统计（这是"执行者必须盲"之外的另一半：输出必须可机械校验）。
 2. 合并回 `benchmark-v2.jsonl`，产出 `benchmark-v3.jsonl`（新增 `v3.req_tier` 字段）。
 3. 出**分层统计**：全量 171 与主结果 120 各档多少条 / 多少独立簇。
 4. 把执行者自报的**规则歧义**原样落盘，供二审（人）裁定。

⚠ 本步骤**不修改 E1 的判决**，也不重算任何召回数字；它只产出分层标签。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\clean-v3\\03-merge-tiers.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
INPUT = HERE / "tier-input.jsonl"
LABELS = HERE / "tier-labels.jsonl"
BENCH_V2 = ROOT / "eval" / "recall-funnel" / "benchmark-v2.jsonl"
OUT_V3 = ROOT / "eval" / "recall-funnel" / "benchmark-v3.jsonl"
OUT_STATS = HERE / "tier-stats.json"

#: 执行者主动报告的规则歧义（原样留档，供人二审；**不许我替它改**）
AMBIGUITIES = [
    {"样本": ["q143", "q162", "q144", "q151", "q161", "q165"],
     "争点": "「应符合 GB/T 3811 的相关规定」这类**跨标准引用**，算不算 R3 的「跨条款/跨表格引用」？",
     "执行者的判法": "算 R3",
     "若改判的影响": "这几条会落到 R1 ⇒ 本批 R1 由 0 变成 6；**R1=0 这个结论对判法敏感**"},
    {"样本": ["q141", "q142"],
     "争点": "「有特殊要求时,供需双方协商确定」算不算 R3 的「例外/豁免」？",
     "执行者的判法": "算 R3",
     "若改判的影响": "这 2 条会落到 R2"},
    {"样本": ["q163", "q164"],
     "争点": "正文尾部粘有分节标题「8 标签、包装、贮存和运输要求」——**疑似解析残留**",
     "执行者的判法": "照判并在 reason 写明", "若改判的影响": "可能要进失败题 B 桶（条款无信息）"},
    {"样本": ["q166", "q167"],
     "争点": "以「第二十条 标题：」开头并夹「索引号：」等**解析残留**",
     "执行者的判法": "照判并在 reason 写明", "若改判的影响": "同上；这两条已在主结果 120 里"},
]


def main() -> int:
    if not LABELS.exists():
        print("⛔ 还没有 tier-labels.jsonl")
        return 1
    src = {json.loads(l)["id"]: json.loads(l)["text"]
           for l in INPUT.read_text(encoding="utf-8").splitlines() if l.strip()}
    lab = [json.loads(l) for l in LABELS.read_text(encoding="utf-8").splitlines() if l.strip()]

    problems = []
    if len(lab) != len(src):
        problems.append(f"行数不符：输入 {len(src)} / 输出 {len(lab)}")
    ids = [r["id"] for r in lab]
    if len(set(ids)) != len(ids):
        problems.append("id 有重复")
    if set(ids) != set(src):
        problems.append(f"id 与输入不一致：多 {sorted(set(ids)-set(src))} 缺 {sorted(set(src)-set(ids))}")
    for r in lab:
        if r.get("tier") not in ("R1", "R2", "R3"):
            problems.append(f"{r.get('id')} tier 非法：{r.get('tier')}")
        if not (r.get("reason") or "").strip():
            problems.append(f"{r.get('id')} reason 为空")
    print(f"[verify] 行数 {len(lab)}；分布 {dict(Counter(r['tier'] for r in lab))}")
    if problems:
        print("⛔ 验收不通过，不许进统计：")
        for p in problems:
            print("   -", p)
        return 1
    print("[verify] ✅ 通过：行数 / id 一一对应 / tier 合法 / reason 非空 / 无重复")

    tier_of = {r["id"]: r["tier"] for r in lab}
    reason_of = {r["id"]: r["reason"] for r in lab}
    v2 = [json.loads(l) for l in BENCH_V2.read_text(encoding="utf-8").splitlines() if l.strip()]
    EX = {"gold_multi_def", "gold_dup_text"}
    out = []
    for r in v2:
        row = dict(r)
        if r["kind"] == "要求":
            tid = f"q{r['i']}"
            row["v3"] = {"req_tier": tier_of.get(tid), "tier_reason": reason_of.get(tid),
                         "tier_rules_sha256_prefix": "d1d43346",
                         "tier_executor": "独立盲子代理（未接触任何分臂信息）"}
        else:
            row["v3"] = {"req_tier": None,
                         "tier_reason": "定义类不套 R1/R2/R3（见 RULES-FROZEN.md §三）"}
        out.append(row)
    OUT_V3.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in out), encoding="utf-8")

    def blk(rows):
        req = [r for r in rows if r["kind"] == "要求"]
        d = {"n_items": len(rows), "n_req": len(req)}
        for t in ("R1", "R2", "R3"):
            sub = [r for r in req if r["v3"]["req_tier"] == t]
            d[t] = {"n_items": len(sub), "n_clusters": len({r["v2"]["gold_cr_id"] for r in sub})}
        return d

    head = [r for r in out if r["v2"]["bucket"] == "keep" and not (EX & set(r["v2"]["flags"]))]
    stats = {
        "rules_frozen_sha256_prefix": "d1d43346",
        "executor": "独立盲子代理 a20f3679（fresh 上下文，只见 id+条文原文）",
        "verification": "脚本机械校验通过（行数/id/tier/reason/重复）",
        "all_171": blk(out),
        "headline_120": blk(head),
        "executor_reported_ambiguities": AMBIGUITIES,
        "reading": [
            "本批要求类**没有一条是 R1（原子要求）** —— 但 R1=0 对『跨标准引用算不算 R3』这一判法敏感（见歧义 1）。",
            "⇒ 不能直接说『这批题全是复杂要求』；要说『在现行判法下 R1=0，若改判则 R1 最多 6』。",
            "⚠ 分层标签只用于**分层汇报**；不许用来改 E1 判决（外部明确）。",
        ],
    }
    OUT_STATS.write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=1))
    print(f"\n已写 {OUT_V3}\n已写 {OUT_STATS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
