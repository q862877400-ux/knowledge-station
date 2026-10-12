# Implementation Plan: 真人问答评测尺子（召回线）

**Branch**: `010-real-question-ruler` | **Date**: 2026-10-12 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/010-real-question-ruler/spec.md`

## Summary

从 415,742 条真人问答里，按**与 `measure-locate-rate.py` 逐字一致**的判据挑出
"答复点名了库内文件"的候选（实测 **28,597** 条），经**五道机械过滤 + 分层抽样**，
产出 **500 条**召回尺子（含 gold、来源、口语度分层），并配可独立复算的校验脚本。

**技术路径**：新建 `eval/real-question-ruler/`（与 `eval/recall-funnel/` 同级），
一个 `build.py`（造尺子）+ 一个 `verify.py`（独立复算）+ 一个 `README.md`（口径）。

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: 只读 `sqlite3` + 标准库（**不引入新依赖**）

**Storage**:
- 输入①：`tools/gov-qa/data/*.jsonl`（592 文件 / 415,742 条，**只读**）
- 输入②：生产库 `%APPDATA%\KnowledgeStation\database\knowledge.db`（**`mode=ro`**）
- 输出：`eval/real-question-ruler/ruler-v1.jsonl` + `stats-v1.json`

**Testing**: pytest（根 `tests/`）

**Target Platform**: Windows（脚本跨平台）

**Constraints**:
- **不写**任何输入（FR-001）
- 判据**只有一个所有者**（FR-002）
- **固定随机种子**，产物可复现（FR-003）

**Scale/Scope**: 读 415,742 条 → 候选 28,597 → 抽样 500

## Constitution Check

| 原则 | 本特性怎么满足 |
|---|---|
| **I 说人话** | 汇报说"用真人真问造了一把 500 题的尺子"、"来源不偏科"；不说分层抽样/权重 |
| **II 从事实出发** | ⚠ 本特性**没有**直接照抄方案稿的"先做 500 条"，而是**先复算**：方案稿里的 28,597 是 2026-10-11 的数，本轮**重算**并与官方脚本对账；对不上就写实际值 |
| **III 证据优于断言** | 每个数字挂复算命令；SC-005/006 要求 **500/500** 可追溯；SC-009 变异自验 |
| **IV 一个事实一个归属层** | 完整口径写 `eval/real-question-ruler/README.md`；方案稿只链接 |
| **V 假绿判 failed** | 变异自验（把投诉类塞回 L1 必须变红）；排除计数必须出现在产物里 |
| **VI 门禁为准** | `-Full` N/N · exit=0 |
| **VII 不撞车** | 只读 `tools/gov-qa/data/**`，**不写** |

**结论**：无违规。

## Project Structure

### Documentation (this feature)

```text
specs/010-real-question-ruler/
├── spec.md      # 已完成
├── plan.md      # 本文件
└── tasks.md     # 下一步
```

### Source Code

```text
eval/real-question-ruler/          # 新增（与 recall-funnel 同级）
├── build.py                       # 造尺子（只读输入，写本目录）
├── verify.py                      # 独立复算（不依赖 build 的内存状态）
├── README.md                      # 口径（每个数字怎么数出来的）
├── ruler-v1.jsonl                 # 产物：500 条
└── stats-v1.json                  # 产物：分层统计 + 排除计数

tests/
└── test_real_question_ruler.py    # 回归判据（含变异自验）
```

**Structure Decision**：`eval/` 下按尺子分目录（既有惯例：`eval/golden/`、
`eval/recall-funnel/`、`eval/lay-phrasing/` 各一个目录）。判据函数**不**新写一份 ——
直接从 `tools/gov-qa/measure-locate-rate.py` **import**（FR-002：一个判据一个所有者）。

## 判据设计（**先定判据，再写实现**）

### 五道过滤（每一道都记排除数）

| # | 过滤 | 判据 | 预期排除 |
|---|---|---|---|
| F1 | 非考卷 | 答复没点名库内文件 | 387,145（415,742 − 28,597） |
| F2 | 投诉/举报 | 22 个特征词命中 `question` | 实测 4,213（14.7%） |
| F3 | 问句过长 | `len(question) > 200` | 实测 7,317（25.6%） |
| F4 | 问句过短 | `len(question) < 8` | 待测 |
| F5 | 重复 | 同 `question` 只留 1 条 | 实测 587 组 |

⚠ **F2 与 F3 是"排除"，F4/F5 是"去重与下限"** —— 四者都必须**分别计数**（FR-004/005/007）。

### 分层抽样（FR-003）

- **按 `source` 分层**（592 个源）；
- 每层配额 = **按候选数的平方根比例**分配（避免大源通吃，也避免小源挤爆）；
- 层内用**固定种子**随机抽（种子写进产物元数据）；
- 抽完**校验**：最大单一 source 占比 ≤ 10%、覆盖 ≥ 20 个 source（SC-003）。

### 口语度分层（L2）

| 层 | 判据 |
|---|---|
| `zero_overlap` | 问句与 gold 文档**全文**无 ≥2 字公共子串 |
| `has_overlap` | 有 ≥2 字公共子串 |
| `has_term` | 问句里出现了库内术语（`term_bridge` 的术语表） |

⚠ **`gold` 到文档级**（不是条款级）⇒ "零重合"是拿**整篇文档的全文**比的，
这与 `lay-phrasing` 拿**单条条文**比**不是一回事** ⇒ README 必须写明，不许混用数字。

### 产物 schema（FR-006）

```json
{
  "id": "<原记录 id 或 url>",
  "source": "ah-kb",
  "url": "https://...",
  "dept": "安徽省林业局",
  "question": "……",
  "q_len": 21,
  "gold_std": ["中华人民共和国野生动物保护法"],
  "gold_doc_id": ["doc_01M4..."],
  "gold_weak": false,
  "layering": "zero_overlap",
  "dup_count": 1,
  "has_clause_ref": true
}
```

### 有牙的断言（SC-009 变异自验）

| 变异 | 必须变红 |
|---|---|
| 把投诉类塞回 L1 | 是（SC-002） |
| 把 >200 字塞回 L1 | 是（SC-002） |
| 让某个 source 占 >10% | 是（SC-003） |
| 抽掉 gold_std | 是（SC-005） |

## 实施顺序

1. **T001** `build.py`：读输入 → 五道过滤（各自计数）→ 分层抽样 → 写产物
2. **T002** `verify.py`：独立复算（不 import build 的中间状态）
3. **T003** 跑 build，对账读数（28,597 候选 / 五道排除数）
4. **T004** 写 `README.md`（口径 + 复算命令）
5. **T005** 回归测试（分层/占比/排除/可追溯）+ 变异自验
6. **T006** 门禁 `-Full`
7. **T007** 小提交 + 快照

## Complexity Tracking

无违规项。

## 风险与回退

| 风险 | 缓解 |
|---|---|
| 判据与官方脚本分叉 | **import** 它，不复制（FR-002）；README 写明"数字应与它一致" |
| 抽样不可复现 | 固定种子写进产物；verify.py 用同一判据独立复算 |
| 500 条凑不齐 | **明写实际条数**并说明（SC-001 允许），**不许**拿投诉类凑数 |
| 大源通吃 | 分层配额 + SC-003 断言 |
| "零重合"口径被误当 `lay-phrasing` 那组数 | README 显著位置写明**不是一回事** |
