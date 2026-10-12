# gov-qa 标签复核包（T501 收口）

> **本目录替代原计划的「人工抽检」。**
> 业主 2026-10-07 裁定（`docs/NOT-DOING.md` 第 23 条，原话照抄）：
> 「**放弃任何人工审核的幻想……只能去寻找更高级的AI的帮助，
> 事实核查部分和语言的部分可以分开做**」
>
> ⚠ **本目录的产物是「AI 判定」的输入材料，不是「人工确认」。**
> **永不**写成 `confirmed_by=人`，**也不得**被写成「已满足 FR-004 / SC-003」。

---

## 这是什么

`specs/005-govqa-conformance/tasks.md` 的 **T501** 原写：

> 「⏳ **需人（agent 无法替代，本条自认）**……**就等业主抽检**」
> 「67.8% 的标签是 SVM 猜的。**准确率只能人工核，agent 无法替代。**」

⚠ **那段已被业主裁定作废。** 出路改成 **AI 复核** —— 本目录就是那份复核包。

## 怎么用

```powershell
Set-Location 'D:\AI\work space\zcode'
.venv\Scripts\python.exe eval\govqa-label-review\build-review.py
```

**产物**（都在本目录）：

| 文件 | 是什么 | 给谁 |
|---|---|---|
| `ai-review-fact.md` | **事实半**复核包（带标签，判"对不对"） | 外部 AI |
| `ai-review-fact.jsonl` | 同上，机器可读 | 脚本 |
| `ai-review-lang.md` | **语言半**复核包（**不带标签**，判"是不是真提问"） | 外部 AI |
| `ai-review-lang.jsonl` | 同上，机器可读 | 脚本 |
| `review-summary.json` | 条数、标签分布、边界声明 | 脚本 |

## 为什么分两半（**这不是我的发明，是业主指示**）

| 半 | 判什么 | 关键约束 |
|---|---|---|
| **事实半** | 这个**标签**对不对（该归哪类） | 要看内容 |
| **语言半** | 这条文本**够不够格当一条提问** | ⚠ **不给标签** —— 给了就变成判"标签对不对"，两半退化成一半 |

**实测验证**：`ai-review-lang.jsonl` 的字段只有 `qid` 与 `question`
（**没有 `label`**）⇒ 语言半确实拿不到标签。

## 输入与规模（2026-10-12 实测）

| 项 | 值 |
|---|---|
| 源 | `D:/AI/output/label-check-200.csv` |
| 行数 | **191**（`label_ok` 已填 **0 / 191**） |
| `label_source` | `source_label` **101** / `model` **80** / `too_short` **10** |
| 标签分布 | 其他 30 · 咨询 20 · 投诉 20 · 举报 20 · 求助 20 · 申诉 20 · 表扬 20 · 建议 20 · 反映 10 · 征求意见 10 · 监察 1 |

> ⚠ **67.8% 与本文的 41.9% 是两回事，别混**：
> * **67.8%** = `docs/archive/research-process/GOVQA-DIAGNOSIS-2026-10-10.md` 里的
>   **全量语料**口径：`model`（SVM 预测）**267,863 条**（占 39.5 万条的 67.8%）。
> * **41.9%** = **本目录这份 191 条样本**里 `model` 占 80 条。
> ⇒ 两者**基数不同**（全量 vs 样本），**不许互相引用**。

## ⚠ 本目录**不做什么**（边界，防止被误读）

1. **不做判定** —— `build-review.py` 只备材料，不跑模型、不写结论。
2. **不声称准确率** —— `review-summary.json` 的 `accuracy` 字段是 **`null`**。
   准确率要等外部 AI **真的回填**，那是**下一轮**的事。
3. **不改规格** —— 规格里 `confirmed_by` 必须是人处**照旧保留**。
4. **不删旧说法** —— T501 的原话（含"agent 无法替代"）在 `tasks.md` 里**保留**，
   更正写在它旁边（本仓规矩：打回的说法就地更正并留痕）。

## 复核完之后怎么回填（**留给下一轮**）

外部 AI 回填后：
1. 把结果写回 `ai-review-fact.jsonl` / `ai-review-lang.jsonl`（各加一列）；
2. **准确率从回填数据算**，写进 `review-summary.json` 的 `accuracy`；
3. **标注"AI 判定"**，不许写成"人工确认"；
4. 若发现某类标签系统性错，登记进 `docs/NOT-DOING.md` 或对应 spec 的 tasks。

## 复算命令

```powershell
Set-Location 'D:\AI\work space\zcode'
.venv\Scripts\python.exe eval\govqa-label-review\build-review.py       # 重造复核包
.venv\Scripts\python.exe -m pytest tests/test_govqa_label_review.py -q  # 回归判据
```
