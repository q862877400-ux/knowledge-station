"""AI 复核包（**分两半**：事实 / 语言）—— 替代原计划的 40 条人工抽查。

## 背景与边界（写进产物，防止被误读）
本仓规格 `specs/002-recall-funnel/contracts/benchmark.schema.md` 明确规定
「`confirmed_by` **必须是人**」「**不得用自动生成的答案** —— 自动答案会让整份诊断失效」。
本脚本**不改变那条规格**，只是把材料备好；是否用 AI 判定、以及是否修订规格，**由业主裁定**。
无论结果如何，产物一律标注为「**AI 判定**」，**永不写成"人工确认"**。

## 为什么分两半（业主 2026-10-07 指示）
 · **事实半**：这条条文**是不是**这个问法的正确答案？（需要强推理，且要能识别"另有更贴切的条款"）
 · **语言半**：这个问法**像不像**一个真外行说出来的话？（需要语感）
两半用不同的判据、且**语言半的判官不许看条文** —— 否则它判的是"像不像抄的"，不是"像不像人话"。

用法： .venv\\Scripts\\python.exe eval\\recall-funnel\\clean-v3\\07-build-ai-review.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SRC = ROOT / "eval" / "recall-funnel" / "exp-1-contextual" / "human-check.csv"
OUT_FACT = HERE / "ai-review-fact.md"
OUT_LANG = HERE / "ai-review-lang.md"
OUT_FACT_JSONL = HERE / "ai-review-fact.jsonl"
OUT_LANG_JSONL = HERE / "ai-review-lang.jsonl"


def main() -> int:
    rows = list(csv.DictReader(SRC.open(encoding="utf-8-sig")))
    rows = [r for r in rows if (r.get("问法（用户原话）") or "").strip()]
    print(f"[pk] 读入 {len(rows)} 条（来自 {SRC.name}）")

    fact, lang = [], []
    for r in rows:
        qid = f"s{r['序号']}"
        q = r["问法（用户原话）"]
        fact.append({"id": qid, "query": q, "gold_std": r["标准号"], "gold_clause": r["条款号"],
                     "gold_text": r["条文原文"], "system_suspicion": r["系统怀疑（供参考，不是结论）"]})
        # ⚠ 语言半**只给问法**，不给条文、不给标准号 —— 否则判的是"像不像抄的"
        lang.append({"id": qid, "query": q})

    OUT_FACT_JSONL.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in fact),
                              encoding="utf-8")
    OUT_LANG_JSONL.write_text("".join(json.dumps(x, ensure_ascii=False) + "\n" for x in lang),
                              encoding="utf-8")

    f = ["# AI 复核包 · **事实半**（这条条文是不是这个问法的正确答案？）", "",
         "> ⚠ **这是 AI 判定，不是人工确认。** 本仓规格要求 `confirmed_by` 必须是人；",
         "> 这份材料用于**替代**人工抽查，属于**业主裁定下的规格例外**，结果一律标注为「AI 判定」。", "",
         "## 你是谁、要判什么", "",
         "你要逐条回答一个问题：**下面这条标准条文，是不是上面那个问题的正确答案？**", "",
         "四选一（**不许含糊，拿不准就写第 4 个**）：", "",
         "| 选项 | 含义 |", "|---|---|",
         "| `对` | 这条就是该问题的正确答案 |",
         "| `错` | 不是这条（另有条文才是）|",
         "| `多个都对` | 库里不止一条同样贴切 ⇒ 该题的 gold 不唯一 |",
         "| `说不清` | 凭你掌握的信息无法判断（**照写，不要猜**）|", "",
         "另外**必须**回答一问：**这个问法有没有把答案「泄漏」进去**？",
         "（即：问法里是不是直接出现了条文里的术语/关键词，导致不用理解也能搜到）"
         " —— 写 `有` / `无` / `说不清`。", "",
         "## 判据（请照此执行）", "",
         "1. **只看给定的问法与条文**，不要去猜检索系统做得好不好；",
         "2. **`多个都对` 很重要**：国标里同一件事常常在几处重复规定；",
         "3. 条文若是**标题、目录、空壳、解析残留**（例如正文只有「标题：」），写 `错`；",
         "4. 「系统怀疑」那一列是**机械检查的提示，不是结论**，你不必采信。", "",
         f"## 待判条目（共 {len(fact)} 条）", ""]
    for x in fact:
        f += [f"### {x['id']}", "",
              f"- **问法**：{x['query']}",
              f"- **标准/条款**：{x['gold_std']} {x['gold_clause']}",
              "- **条文原文**：", "", "```", (x["gold_text"] or "").strip(), "```", "",
              f"- 系统怀疑（供参考）：{x['system_suspicion']}", "",
              f"- **你的判定**：{{对 / 错 / 多个都对 / 说不清}}　**泄漏**：{{有 / 无 / 说不清}}　**理由**：", ""]
    OUT_FACT.write_text("\n".join(f) + "\n", encoding="utf-8")

    g = ["# AI 复核包 · **语言半**（这问法像不像一个真外行说的话？）", "",
         "> ⚠ **这一半故意不给条文。** 因为要判的是「**像不像人话**」，",
         "> 给了条文就变成判「像不像从条文抄出来的」——那是另一件事。", "",
         "## 要判什么（每条两问）", "",
         "1. **自然度**：`像真人` / `像机器` / `说不清`",
         "   —— 像一个真的不懂行的使用者，用自己的话问出来的吗？",
         "2. **对象锚点**：`有` / `无`",
         "   —— 问法里**有没有留下能认出「在问什么东西」的线索**？",
         "   （例：「车间墙角那个呼呼吸空气测细菌的小圆盒子」→ **有**；",
         "     「那个东西怎么弄」→ **无**）", "",
         "**另答一问**：这问法**是不是硬凑出来的**（为了避开原文用词而故意绕）？写 `是` / `否` / `说不清`。", "",
         f"## 待判条目（共 {len(lang)} 条）", ""]
    for x in lang:
        g += [f"- **{x['id']}**：{x['query']}",
              f"  - 自然度：{{像真人 / 像机器 / 说不清}}　对象锚点：{{有 / 无}}　硬凑：{{是 / 否 / 说不清}}", ""]
    OUT_LANG.write_text("\n".join(g) + "\n", encoding="utf-8")

    print(f"[pk] 已写 {OUT_FACT.name} / {OUT_FACT_JSONL.name}（{len(fact)} 条，含条文）")
    print(f"[pk] 已写 {OUT_LANG.name} / {OUT_LANG_JSONL.name}（{len(lang)} 条，**只含问法**）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
