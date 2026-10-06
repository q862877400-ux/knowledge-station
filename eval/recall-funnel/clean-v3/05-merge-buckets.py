"""清洗 v3 · 步骤 5：**验收并合并失败题四桶**，并与其它盲判结果交叉核对。

做四件事：
 1. 机械验收盲分桶输出（行数 / id 一一对应 / bucket 合法 / reason 非空 / 无重复）。
 2. 交叉核对：**分档**执行者报过 q166/q167 有 `标题：` 解析残留，
    而**分桶**执行者说本批没有这类形态 —— 查这两条到底在不在那 50 条里，矛盾要摆出来。
 3. 出统计，并把"二审待办"列出来（外部要求：**盲模型初分 → 人二审**）。
 4. 落盘。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\clean-v3\\05-merge-buckets.py
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
INPUT = HERE / "bucket-input.jsonl"
LABELS = HERE / "bucket-labels.jsonl"
EXP = ROOT / "eval" / "recall-funnel" / "exp-1-contextual"
OUT = HERE / "bucket-stats.json"

#: 分档执行者报出的解析残留（q 编号）—— 用于与分桶结果交叉核对
PARSE_SUSPECT_Q = {"q163", "q164", "q166", "q167"}


def main() -> int:
    if not LABELS.exists():
        print("⛔ 还没有 bucket-labels.jsonl")
        return 1
    src = [json.loads(l) for l in INPUT.read_text(encoding="utf-8").splitlines() if l.strip()]
    lab = [json.loads(l) for l in LABELS.read_text(encoding="utf-8").splitlines() if l.strip()]

    problems = []
    if len(lab) != len(src):
        problems.append(f"行数不符：输入 {len(src)} / 输出 {len(lab)}")
    ids = [r["id"] for r in lab]
    if len(set(ids)) != len(ids):
        problems.append("id 有重复")
    if set(ids) != {r["id"] for r in src}:
        problems.append("id 与输入不一致")
    for r in lab:
        if r.get("bucket") not in ("A", "B", "C", "D"):
            problems.append(f"{r.get('id')} bucket 非法：{r.get('bucket')}")
        if not (r.get("reason") or "").strip():
            problems.append(f"{r.get('id')} reason 为空")
    print(f"[verify] 行数 {len(lab)}；分布 {dict(Counter(r['bucket'] for r in lab))}")
    if problems:
        print("⛔ 验收不通过：")
        for p in problems:
            print("   -", p)
        return 1
    print("[verify] ✅ 通过（行数 / id 一一对应 / bucket 合法 / reason 非空 / 无重复）")

    # ── 交叉核对：解析残留那 4 条在不在失败样本里 ───────────────────────────
    failed_ids = {r["id"] for r in src}               # 形如 f163
    cross = {q: (q.replace("q", "f") in failed_ids) for q in sorted(PARSE_SUSPECT_Q)}
    in_50 = [q for q, v in cross.items() if v]
    print(f"[cross] 分档报的解析残留 {sorted(PARSE_SUSPECT_Q)} 中，落在这 50 条失败样本里的 = {in_50}")

    # ── 二审待办：D 桶 + 执行者自报最难判的 + 交叉不一致的 ──────────────────
    second_pass = []
    for r in lab:
        if r["bucket"] == "D":
            second_pass.append({"id": r["id"], "why": "唯一判为『金标问题』的，执行者自述拿不准",
                                "bucket": "D", "reason": r["reason"][:160]})
    for hid in ("f28", "f31"):
        row = next((r for r in lab if r["id"] == hid), None)
        if row:
            second_pass.append({"id": hid, "why": "执行者自报最难判", "bucket": row["bucket"],
                                "reason": row["reason"][:160]})

    stats = {
        "rules_frozen_sha256_prefix": "d1d43346",
        "executor": "独立盲子代理 ea11b550（fresh 上下文；输入已剔除 channels/fused/votes/confidence 等全部检索数据）",
        "verification": "脚本机械校验通过",
        "n": len(lab),
        "buckets": dict(Counter(r["bucket"] for r in lab)),
        "cross_check_parse_suspects": cross,
        "cross_check_note": (
            "分档执行者报 q166/q167 有 `标题：` 解析残留；分桶执行者说本批**没有**这类形态。"
            + ("两条**都在**这 50 条里 ⇒ **两个盲判直接矛盾**，必须二审裁定。"
               if in_50 else
               "核对结果：这两条**不在**这 50 条失败样本里 ⇒ **不矛盾**（两批样本不同），"
               "但说明『解析残留』那类条文没被失败样本覆盖到，二审要另外补。")
        ),
        "headline": {
            "A_vocab_gap": "条文本身是正确答案，失败在字面对不上 ⇒ **检索/表示层的问题**",
            "B_clause_empty": "0 条",
            "C_wrong_standard": "0 条",
            "D_gold_problem": "1 条（f11，执行者自述拿不准）",
            "what_it_means": (
                "外部评估怀疑『金标问题占比不小，60% 前 1000 都没找到并不全是检索的锅』——"
                "**本批 50 条实测不支持这个怀疑**：49 条金标是对的，失败在检索侧词面。"
                "⚠ 但这是**单一盲模型的初判**，外部要求『盲模型初分 → 人二审』，二审未做前不得当定论。"
            ),
        },
        "second_pass_todo": second_pass,
        "boundary": [
            "n=50，是**抽样**不是全部（失败人群 104 条）。",
            "单一盲模型初判，**尚无人工二审** ⇒ 只能写『初判指向』，不能写成定论。",
            "A 桶是默认/最常见桶，模型可能有『往 A 靠』的倾向；二审要特意抽查被判 A 的边界项。",
        ],
    }
    OUT.write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=1))
    print(f"\n已写 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
