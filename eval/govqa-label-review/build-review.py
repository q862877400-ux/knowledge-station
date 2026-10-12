# -*- coding: utf-8 -*-
"""造「gov-qa 标签复核包」（spec 005 T501 收口）。

## 为什么要这个（**替代原计划的人工抽检**）

`specs/005-govqa-conformance/tasks.md` 的 T501 原写：

> 「⏳ **需人（agent 无法替代，本条自认）** …**就等业主抽检**」
> 「67.8% 的标签是 SVM 猜的。**准确率只能人工核，agent 无法替代。**」

⚠ **这段已被业主裁定作废**（`docs/NOT-DOING.md` 第 23 条，2026-10-07 原话）：

> 「**放弃任何人工审核的幻想……只能去寻找更高级的AI的帮助，
> 事实核查部分和语言的部分可以分开做**」

⇒ 出路从"等人抽检"改成 **AI 复核**。本脚本照本仓既有先例
（`eval/recall-funnel/clean-v3/07-build-ai-review.py` 的**事实/语言两半分开送核**）。

## ⚠ 三条不许混的边界

1. **AI 判定 ≠ 人工确认** —— 产物一律标注「**AI 判定**」，**永不写成"人工确认"**。
2. **规格原文没改** —— 凡规格写着 `confirmed_by` **必须是人**的地方**照旧保留**，
   **不许**因为有了 AI 复核就写成"已满足"（NOT-DOING 第 23 条自己写明的）。
3. **本脚本只备材料，不做判定** —— 它不跑模型、不写结论。
   回填由外部 AI 完成（**下一轮**）。

## 为什么分两半（业主 2026-10-07 指示）

| 半 | 判什么 | 为什么单独 |
|---|---|---|
| **事实半** | 这个**标签**对不对（这条问句到底该归哪类） | 需要看懂内容 |
| **语言半** | 这条问句**是不是一个真提问**（还是乱码/标题/纯关键词） | 需要语感，**不看标签** |

⇒ 两半**判官不许看对方那半** —— 否则事实半会替语言半做判断，两半就退化成一半。

## 用法
    .venv\\Scripts\\python eval/govqa-label-review/build-review.py
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_SRC = Path(r"D:\AI\output\label-check-200.csv")

#: 标签全集（来自 spec 004 的标签口径）
LABELS = ("咨询", "求助", "投诉", "举报", "建议", "申诉", "表扬",
          "反映", "征求意见", "监察", "其他")


def main() -> int:
    ap = argparse.ArgumentParser(description="造 gov-qa 标签 AI 复核包")
    ap.add_argument("--src", default=str(DEFAULT_SRC))
    args = ap.parse_args()

    src = Path(args.src)
    if not src.exists():
        print(f"⛔ 源文件不在: {src}")
        return 1
    rows = list(csv.DictReader(src.open(encoding="utf-8-sig")))
    rows = [r for r in rows if (r.get("question") or "").strip()]
    print(f"[pk] 读入 {len(rows)} 条（来自 {src}）")

    src_dist = Counter(r["label_source"] for r in rows)
    print(f"[pk] label_source 分布: {dict(src_dist)}")

    fact, lang = [], []
    for r in rows:
        qid = f"{r['source']}|{r['id']}"
        q = r["question"].strip()
        fact.append({
            "qid": qid, "source": r["source"], "id": r["id"],
            "question": q, "label": r["label"],
            "label_source": r["label_source"],
        })
        lang.append({"qid": qid, "question": q})

    # ---- 事实半：给标签，判"对不对" ----
    fm = HERE / "ai-review-fact.md"
    with fm.open("w", encoding="utf-8") as fh:
        fh.write("# AI 复核包 · **事实半**（这个标签对不对？）\n\n")
        fh.write("> ⚠ **这是 AI 判定的输入材料，不是人工确认。**\n")
        fh.write("> 业主 2026-10-07 裁定：放弃人工审核，改用外部高级 AI 复核"
                 "（`docs/NOT-DOING.md` 第 23 条）。\n")
        fh.write("> ⚠ **规格原文没改** —— 凡写着 `confirmed_by` 必须是人处照旧保留；\n")
        fh.write("> 本产物**不得**被写成「已满足 FR-004 / SC-003」。\n\n")
        fh.write("## 要判什么\n\n")
        fh.write("给每条问句，判**它现在的标签对不对**，并给正确答案（若不对）。\n\n")
        fh.write(f"标签全集：{' / '.join(LABELS)}\n\n")
        fh.write("| 字段 | 填什么 |\n|---|---|\n")
        fh.write("| 标签对否 | `对` / `错` / `说不清` |\n")
        fh.write(f"| 正确标签 | 若判`错`，从标签全集里选一个 |\n")
        fh.write("| 理由 | 一句话 |\n\n")
        fh.write(f"## 待判条目（共 {len(fact)} 条）\n\n")
        for c in fact:
            fh.write(f"- **{c['qid']}**（现标：`{c['label']}`，来源：`{c['label_source']}`）\n")
            fh.write(f"  - 问句：{c['question']}\n")
            fh.write("  - 标签对否：{对 / 错 / 说不清}　正确标签：{}　理由：\n\n")
    (HERE / "ai-review-fact.jsonl").write_text(
        "\n".join(json.dumps(c, ensure_ascii=False) for c in fact) + "\n", encoding="utf-8")

    # ---- 语言半：**不给标签**，只判"是不是真提问" ----
    lm = HERE / "ai-review-lang.md"
    with lm.open("w", encoding="utf-8") as fh:
        fh.write("# AI 复核包 · **语言半**（这条问句是不是一个真提问？）\n\n")
        fh.write("> ⚠ **这一半故意不给标签。** 要判的是「**这条文本够不够格当一条提问**」，\n")
        fh.write("> 给了标签就变成判「标签对不对」——那是事实半的事。\n")
        fh.write("> ⚠ **这是 AI 判定的输入材料，不是人工确认。**\n\n")
        fh.write("## 要判什么（每条两问）\n\n")
        fh.write("1. **是不是真提问**：`是` / `否` / `说不清`\n")
        fh.write("   —— 是一条用户真的想问的问题吗？\n")
        fh.write("   （反例：`社保`、`医保报销` 这种**纯关键词**；乱码；纯标题）\n")
        fh.write("2. **有没有具体内容**：`有` / `无`\n")
        fh.write("   —— 问句里有没有能让检索有抓手的具体信息（对象/情形/时间/地点）？\n\n")
        fh.write(f"## 待判条目（共 {len(lang)} 条）\n\n")
        for c in lang:
            fh.write(f"- **{c['qid']}**：{c['question']}\n")
            fh.write("  - 是不是真提问：{是 / 否 / 说不清}　有没有具体内容：{有 / 无}\n\n")
    (HERE / "ai-review-lang.jsonl").write_text(
        "\n".join(json.dumps(c, ensure_ascii=False) for c in lang) + "\n", encoding="utf-8")

    # ---- 摘要（机器可读） ----
    summary = {
        "kind": "AI 判定（**不是**人工确认）",
        "source_csv": str(src),
        "source_rows": len(rows),
        "items_fact": len(fact),
        "items_lang": len(lang),
        "label_distribution": dict(Counter(r["label"] for r in rows).most_common()),
        "label_source_distribution": dict(src_dist.most_common()),
        "labels_universe": list(LABELS),
        "rule": "业主 2026-10-07 裁定：放弃人工审核，改用外部高级 AI 复核"
                "（docs/NOT-DOING.md 第 23 条）",
        "warning": "规格原文没改 —— confirmed_by 必须是人处照旧保留；"
                   "本产物不得被写成已满足 FR-004 / SC-003",
        "accuracy": None,   # ⚠ 明确未做：要等外部 AI 回填
    }
    (HERE / "review-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[pk] 事实半 → {fm.name} + ai-review-fact.jsonl（{len(fact)} 条）")
    print(f"[pk] 语言半 → {lm.name} + ai-review-lang.jsonl（{len(lang)} 条）")
    print(f"[pk] 摘要   → review-summary.json")
    print("[pk] ⚠ 本产物是 **AI 判定** 的输入材料，**不是人工确认**")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
