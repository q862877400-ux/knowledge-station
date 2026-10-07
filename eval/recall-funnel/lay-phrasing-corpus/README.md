# 外行说法语料（**§1.2 全部数字的唯一来源**）

> **为什么专门存这一份、还写了这页**：这份语料原先只躺在 `var/tmp/` 下，
> 而 `.gitignore` 把 `var/*` **整体排除** ⇒ 它**不受版本保护**。
> 它的两个兄弟 `gen-V1.jsonl`、`lay-phrasing.jsonl` **已经消失了**。
> 一旦这份也没了，`docs/RETRIEVAL-LONG-RANGE-PLAN.md` §1.2 那条主线的判据
> （"53% 一个字都对不上"）就**再也量不了**。
> ⇒ 2026-10-07 从 `var/tmp/` 拷进版本库，并记下校验值。

## 文件

| 文件 | 内容 | sha256（前 16） |
|---|---|---|
| **`gen-V2.jsonl`** | **500 个术语 / 1,832 条外行说法** ← **主件** | `e637e4aa14c8ac95` |
| `gen-V3-all.jsonl` | 58 行 | `6e274f730800f559` |
| `gen-V4.jsonl` | 98 行 | `b75204ae6234bbb9` |
| `lay-50.jsonl` | 50 行 | `2516ff2f336e29e5` |

## 主件的数据形态

每行一个术语；`lay` 字段是**该术语的 4 条外行说法**，每条带 `register`：

```json
{"term": "线分类法",
 "lay": [{"text": "仓库里把大箱套小盒一层层往下排会被消防罚吗？", "register": "owner"},
         {"text": "这批螺丝到底是一级套一级分着摆还是平铺开？",   "register": "worker"},
         {"text": "咱们货架从大到小分了5层算不算符合收纳规矩？", "register": "newcomer"},
         {"text": "超市按吃的用的、再按干的湿的找，怎么找不到？", "register": "consumer"}]}
```

- `register` 四档：**owner（老板）/ worker（工人）/ newcomer（新人）/ consumer（消费者）**；
- **1,832 = (500 − 42) × 4** —— 有 **42 个术语的 `lay` 为空**（`gen-V2` 那版新机制把它们写成空，
  带 `why_empty` 说明，见 `docs/research/lay-phrasing-scaleup-test.md` §二）。
- 复算命令（本页数字都可用它核）：
  ```powershell
  .venv\Scripts\python.exe -c "import json,pathlib;rows=[json.loads(l) for l in pathlib.Path('eval/recall-funnel/lay-phrasing-corpus/gen-V2.jsonl').read_text(encoding='utf-8').splitlines() if l.strip()];print(len(rows), sum(len(r.get('lay') or []) for r in rows))"
  ```

## 边界（别把它当"考卷"用）

- 这是**术语 → 说法**的对照表，用来量**"换个说法还找不找得到"**（判据①），
  **不是**一份带正确答案的考卷；它没有 gold 条款；
- 它生成于 2026-09-25，**当时跑在 19 篇快照库上**（见计划 §3 那条登记），
  与现在的 8,983 篇不是同一套库 ⇒ **重跑这些数字前要先确认口径**。
