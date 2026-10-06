# Implementation Plan: 召回漏斗诊断与第一轮改进

**Branch**: `002-recall-funnel` | **Date**: 2026-10-06 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-recall-funnel/spec.md`

## Summary

**要解决的技术问题**：现有几个命中率数字口径不一、互相独立，**分不出"第一跳为什么丢"** —— 是文档表示、提问表达、检索通道，还是索引本身。

**技术路线**：**先冻结基线，再用"漏斗"把丢失位置定位到具体环节**，然后**一次只改一处**做 A/B。**诊断完成前不动任何检索算法。**

**⇒ 交付物是一份能判读的漏斗表 + 一次有止损线的改进实验，不是"命中率涨到 X%"。**

---

## Technical Context

**Language/Version**: Python 3（引擎侧）；Node.js（DSH 插件侧，本周期不动）

**Primary Dependencies**（实测自 `src/core/retrieval/`）：

| 项 | 实测值 | 出处 |
|---|---|---|
| 语义模型 | **fastembed `bge-small-zh-v1.5`**（CPU / ONNX） | `retrieval/embedder.py` |
| **向量维度** | **512** | `embedder.py` 的 `EMBEDDING_DIM`；`storage/schema.sql` 的 `FLOAT[512]` |
| 重排器 | fastembed `TextCrossEncoder`（`BAAI/bge-reranker-v2-m3`） | `retrieval/reranker.py` |
| 分词 | jieba | `src/core/text_utils.py` |
| **按字检索** | **有** —— `clause_fts` 表 + `fts_match_expr()` | `text_utils.py` / `hybrid_engine.py` |
| **向量索引** | **sqlite-vec v0.1.9**（虚拟表 `FLOAT[512]`） | `storage/schema.sql` |
| 默认取回数 | `top_k = 5` | `hybrid_engine.py` |

**🔴 关键发现（改变本计划的重点）：本仓【已经实现了六条召回通道】**，不是单路：

| 通道 | 是什么 |
|---|---|
| **A** | 条款号 / 法条号**精确匹配**（**权重最高 2.0**） |
| **B** | （待 Phase 0 从代码确认） |
| **C** | sqlite-vec **向量检索** |
| **D** | **模态**（`应` / `不应` / `宜` 这类强制程度） |
| **E** | **法理要素** |
| **F** | （待 Phase 0 从代码确认） |

**⇒ 外部方案建议的"多路召回"本仓已经在做；而天花板仍只有 41.6%。**
**⇒ 所以"再加一路"不是本计划的答案，"定位到哪一路/哪一环出问题"才是。**

**🔴 另一条已实测的缺陷（`hybrid_engine.py` 注释原文）**：

> 「通道 A/D/E 原先没有上限，实测模态 `'应'` 一次拉 **140,555 条**（全库 26.9%）。
> 通道 A 候选 522,000 行里，名次 >500 被砍掉 **177,829 行 = 34.1%**；
> **384 / 6,793 篇文档的全部条款都被砍光**（通道 A 对它们完全失效）。
> ⇒ 在把通道 A/D/E 的排序改成"与相关性有关"之前，不许给它们加行数上限。」

**⇒ 权重最高的通道（A）对 384 篇文档整条失效。这是一个与"表示能力"无关的、可独立验证的丢失机制。**

**Storage**: **SQLite**（单文件库）；向量用 sqlite-vec 虚拟表；全文用 FTS

**Testing**: pytest（本仓 `tests/`，约 163 个测试文件）；另有独立于门禁的文档链接检查 `scripts/docs/check-links.py`

**Target Platform**: 本机 Windows 单机

**实测机器规格**：

```
CPU   Intel Core i7-14700KF   20 物理核 / 28 逻辑核
内存  63.8 GB
GPU   NVIDIA GeForce RTX 4080 SUPER
```

**Project Type**: 单体桌面应用（本地引擎 + 宿主插件），**数据与代码分离**，运行产物在 `%APPDATA%\KnowledgeStation\`

**Performance Goals**（本周期只要求"跑得完"，不要求"跑得快"）：
- 能在**可接受时间内**对 150～200 条问题跑完四个检索角度 × 四个截断位置
- 不设延迟目标 —— **本周期是诊断，不是性能优化**

**Constraints**:
- **语料冻结在 522,021 条**，不扩容
- **`gen-V2.jsonl` 只读** —— 它是既有数字的唯一基准
- **诊断完成前不得改任何检索算法**（FR-016）
- **单机跑完**，不引入分布式组件

**Scale/Scope**:
- 基准集 150～200 条 × 4 个检索角度 × 4 个截断位置
- 周期 7～10 天

---

## Constitution Check

*GATE: 必须过。Phase 0 前一次，Phase 1 设计后再一次。*

| 原则 | 本计划怎么守 | 结论 |
|---|---|---|
| **I. 说人话** | 交付物与验收判据用"能说出问题出在哪一层"表述；技术细节留在本文件与 `research.md`，**向业主汇报时转成大白话** | ✅ 过 |
| **II. 从事实出发，不迎合** | 本计划的重心正是**否定"再换一个向量模型"这类直觉判断**；四个数字口径不一，**先核口径再决策**（FR-002/003） | ✅ 过 |
| **III. 证据优于断言** | 每个结论 MUST 挂回原始数据（SC-005）；抽样 MUST 写明是抽样；**"未做" MUST 写明** | ✅ 过 |
| **IV. 一个事实一个归属层** | 诊断数据落 `eval/`；方法说明落该目录 README；**总纲只留指针** | ✅ 过 |
| **V. 留痕不许悄悄删** | 既有 96 条金标的用途**不改、不删**；口径更正就地留痕（"原以为 X，实为 Y"） | ✅ 过 |
| **VI. 先查有没有现成的** | 已查：本仓**已有六条通道**、已有 `check-links.py`、已有 `bunny-benchmark` 流水线 ⇒ **复用，不新造** | ✅ 过 |
| **VII. 提案前对已否决台账** | ✅ **Phase 0 已做**：台账 22 条逐条比对，见 `research.md` R5。直接相关的两条：**#21「不重建 522k 索引」已于 2026-09-30 解除**（⇒ Retrieval Text 实验允许重算向量）；**#22「三字滑窗」业主否决**（⇒ 全文侧改动不得采用） | ✅ 过 |

**Phase 0 前结论**：**无违反**。

### Phase 1 设计后复查

| 原则 | 复查结果 |
|---|---|
| **I. 说人话** | ✅ 未退化：`quickstart.md` 与验收判据仍用业务语言 |
| **II. 从事实出发** | ✅ **更强了**：`research.md` 查实了一条**推翻直觉判断**的证据 —— 41.6% 所依赖的"候选只有 500 个"条件**已作废**，所以"是排序问题"这个推论**不能采信** |
| **III. 证据优于断言** | ✅ `research.md` 每条结论带出处；`contracts/funnel.schema.md` 要求"做不到就写明做不到" |
| **IV. 一个事实一个归属层** | ✅ plan 的 Structure Decision 定了每个产物的物理归属，且**方法说明单独落 `eval/recall-funnel/README.md`** |
| **V. 留痕不许悄悄删** | ✅ 既有 96 条金标用途不变；旧数字**保留但标注"不得用作决策依据"**（不是删掉） |
| **VI. 先查有没有现成的** | ✅ 已复用 `check-links.py`、bunny 三路流水线；`data-model.md` 明确**不建表** |
| **VII. 对已否决台账** | ✅ 见 Phase 0 前的表 |

**⇒ Phase 1 后结论：无违反。无需填写 Complexity Tracking。**

---

## Project Structure

### Documentation (this feature)

```text
specs/002-recall-funnel/
├── plan.md              # 本文件
├── research.md          # Phase 0 产出（口径确认 + 通道清点 + 台账比对）
├── data-model.md        # Phase 1 产出（基准题 / 基线快照 / 漏斗记录 / 实验）
├── quickstart.md        # Phase 1 产出（跑通漏斗的验证步骤）
├── contracts/           # Phase 1 产出（漏斗记录与基线快照的格式契约）
├── checklists/
│   └── requirements.md  # 规格质量检查表（已完成）
└── tasks.md             # Phase 2 产出（/speckit-tasks，本命令不产生）
```

### Source Code (repository root)

**本仓是单体结构，不套用模板的三选一。实际布局：**

```text
src/core/                    # Python 引擎
├── retrieval/               # ← 本周期的主战场（不动，只读）
│   ├── hybrid_engine.py     #   六条通道、RRF 融合
│   ├── embedder.py          #   bge-small-zh-v1.5 / 512 维
│   ├── reranker.py          #   bge-reranker-v2-m3
│   └── term_bridge.py       #   术语桥（第 6 天的实验对象）
├── storage/                 # schema.sql + clause_repo.py
└── text_utils.py            # fts_match_expr / segment_for_fts

eval/                        # 评测资产（本周期产出落这里）
├── lay-phrasing/            # 1,832 条外行说法（只读，提问候选来源）
├── golden/                  # 96 条防倒退金标（用途不变）
└── bunny-benchmark/         # bunny 三路判定流水线（可复用）

scripts/
└── docs/check-links.py      # 链接检查（复用）

specs/002-recall-funnel/     # 本特征的规格与设计文档
```

**Structure Decision**：

**本周期【不新增源码目录】**，因为：
1. 诊断脚本是**一次性测量工具**，归属 `eval/recall-funnel/`（与 `eval/lay-phrasing/`、`eval/bunny-benchmark/` 同级）
2. **检索代码本周期一律不动**（FR-016），所以没有 `src/` 下的新增
3. 复用已有的 `check-links.py` 与 bunny 流水线，不新造

**⇒ 产出的物理归属**：

| 产物 | 落哪 |
|---|---|
| 基准题（150～200 条） | `eval/recall-funnel/benchmark.jsonl` |
| 基线快照 | `eval/recall-funnel/baseline-v0/`（`config.json` / `metrics.json` / `results.jsonl`） |
| 漏斗记录 | `eval/recall-funnel/funnel.jsonl` |
| 测量脚本 | `eval/recall-funnel/*.py` |
| 方法说明与口径 | `eval/recall-funnel/README.md` |
| 改进实验结果 | `eval/recall-funnel/exp-<n>/` |

---

## Phase 0：待研究的问题（research.md 要解决的）

| # | 问题 | 为什么必须解决 |
|---|---|---|
| **R1** | **旧数字的确切口径** | 总纲 L43/L45/L46 与 L235 **分母不同**（1832 vs 458）、子集不同。**不核清就不能当基线，也不能解释 41.6%** |
| **R2** | **41.6% 那个"命中集合"是怎么算的** | 它是**哪个/哪几个通道的并集**、取多少条？**它直接决定"是不是排序问题"这个结论** |
| **R3** | **通道 A 对 384 篇文档失效，现在还成立吗** | 注释记的是过去的实测；**本周期要重测**（这是可独立验证的丢失机制） |
| **R4** | **通道 B 与 F 是什么** | Technical Context 里两项未知 |
| **R5** | **逐条对 `docs/NOT-DOING.md`** | 宪法原则 VII 要求；**尤其 #22 三字滑窗** |

## Phase 1：要产出的设计物

- **`data-model.md`**：四个实体的字段与关系（基准题 / 基线快照 / 漏斗记录 / 改进实验）
- **`contracts/`**：
  - `benchmark.schema.md` —— 基准题的字段契约（含多答案、子集标签、库外标记）
  - `baseline.schema.md` —— 基线快照三件套的字段契约
  - `funnel.schema.md` —— 漏斗记录的字段契约（四角度 × 四截断位置）
- **`quickstart.md`**：跑通漏斗的验证步骤（含"用 20 条先跑通"的路径）

---

## Complexity Tracking

> 本计划**无宪法违反**，故本节留空。

**刻意保持简单的三处**（记下来，防止后期膨胀）：

1. **不引入新的存储**：诊断数据全落 JSONL 文件，**不建表**。
2. **不引入新的检索组件**：四个角度全部用**已有的** `hybrid_engine` 与 `clause_fts`，只是**分别调用**。
3. **不新建框架**：测量脚本是平铺的 `.py`，与 `eval/lay-phrasing/` 同风格。
