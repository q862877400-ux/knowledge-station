# Tasks: 召回漏斗诊断与第一轮改进（002-recall-funnel）

**Input**: Design documents from `specs/002-recall-funnel/`
**Prerequisites**: plan.md（已读）、spec.md（已读）、research.md、data-model.md、contracts/、quickstart.md

> **状态图例**：`[x]` = **已完成且可核**（附产物路径）｜`[ ]` = **未完成**（附"做完的标志"）。
> **⚠ 本文件按 Spec Kit 规范生成，但有一条与通常不同**：这是一个**已经跑过一半**的周期，
> 所以**已完成项逐条带产物**、未完成项逐条带验收判据 —— **不许把"没做"写成"待优化"**（宪法原则 III）。
> 交接文档 `docs/HANDOVER-2026-10-06.md` §五「未完成」那张表**逐条落进了本文件**（见下方对照）。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行（不同文件、无未完成依赖）
- **[Story]**: 所属用户故事（US1 / US2 / US3）
- 每条任务都带**确切文件路径**

## 交接 §五 对照表（**读完这张表再读任务**）

| 交接 §五 | 本文件里的落点 | 现状 |
|---|---|---|
| 1 等外部 AI 评估 | 前置条件（不在任务内） | ✅ 已拿到 |
| 2 `tasks.md` 没生成 | **本文件** | ✅ 已生成 |
| 3 诊断本体没跑 | Phase 3（T009–T017） | ⚠ **主体已跑**（T009–T014 ✅）；**T015–T017 三项未做** |
| 4 规格按"四路"写的要改 | Phase 2 T008 | ✅ 已更正（`cee48cf`） |
| 5 两批考卷口径不同 | Phase 6 T031 | ❌ 未做 |
| **6（收口时新发现）** | Phase 3 T015–T017 / Phase 4 T022 / Phase 6 T030 | ❌ 未做 |

---

## Phase 1: Setup（共享前置）

**Purpose**: 把"在哪跑、跑的是哪个版本、产物放哪"钉死。

- [x] T001 确认真库可**只读**打开并记下语料规模（`clause_revision` = 522,021 / `doc_meta` = 6,797），
      开跑与收尾各核对一次 mtime；方法与结论落在 `eval/recall-funnel/README.md` §二.3
- [x] T002 [P] 目录与产物归属定死：测量脚本与产物一律进 `eval/recall-funnel/`
      （与 `eval/lay-phrasing/`、`eval/bunny-benchmark/` 同级），方法说明单独一篇 `README.md`
- [x] T003 冻结代码版本：`git tag step-240-recall-funnel-phase0` / `step-241-recall-funnel-phase0-r2`
      （快照脚本 `scripts/snapshot-project.ps1`），供基线追溯

**Checkpoint**: 跑得动、版本可查、产物有家。

---

## Phase 2: Foundational（阻塞所有用户故事）

**Purpose**: 先把"口径"和"现状"钉死。**这一步不做完，后面所有数字都不可比。**

- [x] T004 [FR-002] 查清既有那几个数字（53% / 6.8% / 5.8% / 41.6% / 24.5% / 11.8%）的**确切定义**：
      分母各是 1832 / 458 / 1651、41.6% 依赖的"候选术语只有 500 个"**已作废**
      → `specs/002-recall-funnel/research.md` R1/R2
- [x] T005 [P] [FR-001] 盘出当前检索链路的全部关键配置（模型与维度 / 全文实现 / 向量索引类型 /
      六条通道的触发条件与取回上限 / 融合权重与截断位置 / 机器），并记录**每一项的出处**
      → `eval/recall-funnel/config-inventory.md`
- [x] T006 [FR-003] 结论：**旧数字不得用作任何技术决策依据**（分母不一致 + 关键推论条件已作废）
      → `research.md` R1/R2 末节
- [x] T007 实测六条通道在当前库里的**真实可触发情况**：A 触发 0/171、D 8/171、
      **E/F 恒 0**（E 的字段 `subject` 非空仅 2,171 且还要 `knowledge_type='legal'` 只剩 1,148；
      F 匹配的 `behavior_scope_segmented` **全库 0 行**）→ `config-inventory.md` §四
- [x] T008 把「四个检索角度 / `semantic_exact` vs `semantic_ann`」的旧口径**就地更正**为实测事实
      （本仓 `clause_vec` 是 `vec0`、无 ANN）→ 7 篇文档，提交 `cee48cf`

**Checkpoint**: 口径统一、现状清楚 —— 可以开始量了。

---

## Phase 3: User Story 1 - 看清正确条文是在哪一步被丢掉的（P1）🎯 MVP

**Goal**: 每条问题逐条给出"六条通道各自第几名 + 合起来之后第几名"，并归并成**三档**结论。

**Independent Test**: 拿 20 条已知答案的问题跑一遍，能说清每条在哪一档。

- [x] T009 [US1] 基准文件：对 `eval/reverse-benchmark/benchmark-171.jsonl` 做**轻清洗**
      （3/3 一致 143；再去掉 gold 在库里不唯一的 23 ⇒ **主结果 120**），标 `bucket` / `flags`
      → `eval/recall-funnel/benchmark-v2.jsonl` + `benchmark-v2-stats.json`
- [x] T010 [US1] 漏斗逐条测量：171 条 × 六条通道（生产口径 + 深读 @100/@1000）+ 融合后，
      逐条落盘、**边跑边写 + 断点续跑** → `eval/recall-funnel/funnel-per-query.jsonl`（脚本 `funnel.py`）
- [x] T011 [US1] 仪器自检 `replica_check`：每条问法把"通道副本前 20"与
      `perform_hybrid_search(单通道)` 逐个比 ⇒ **171/171 一致**
      （⚠ 覆盖面：只 A/B/C/D 四路、只比前 20；深读名次另由复核抽验）
- [x] T012 [US1] 汇总表：每通道 @20/@100/@1000、**两个并集口径分开命名**
      （`same_budget` / `prod_caps`）、融合后名次 → `eval/recall-funnel/funnel-summary.json`（`summarize.py`）
- [x] T013 [US1] 分诊成三档 + 留证失败样本 50 条：
      够不着 **104** / 被截断 **48** / 融合丢 **4** / 进得了用户看的 8 条 **9**
      → `failure-samples.jsonl`、`REPORT.md` §C
- [x] T014 [US1] 结论报告 A–F → `eval/recall-funnel/REPORT.md`
- [ ] **T015 [US1] 🔴 未做 —— 基准的"人工确认"**（FR-004 / SC-003 要求"每条的答案经人工确认"）。
      本批 gold 是**从条文反推问法 + 另一个模型盲判 3 次**，**不是人工确认的**，
      这条**违反** `contracts/benchmark.schema.md` 的"`confirmed_by` 必须是人"。
      **做完的标志**：抽 **≥30 条**（跨定义/要求、跨 register）请人逐条判"这条问法的答案确实是它吗"，
      结果落 `eval/recall-funnel/benchmark-v2-humancheck.jsonl`，并在 `REPORT.md` §八 更新该条限制的实际影响；
      若做不到，**MUST 在报告里把"人工确认"降级为"未做"，不许含糊**。
- [ ] **T016 [US1] 未做 —— 按 spec 的四个子集切片**（FR-005 / FR-009：短条款 / 字面零重合 / 带标准号 / 普通）。
      实测只切了 **kind（定义/要求）** 与 **零重合**；**"短条款"（<40 字）与"带标准号"两个切片没有做**。
      **做完的标志**：`funnel-summary.json` 里出现 `by_subset`，四个子集各有命中率**且各带分母**。
- [ ] **T017 [US1] 未做 —— `answer_out_of_corpus` 字段**（FR-006：答案不在库内的题要能标出并排除）。
      本批 171 条 gold **全部在库内**（171/171 可查）⇒ 本轮不构成风险，但**字段不存在** ⇒ 换考卷时会裸奔。
      **做完的标志**：`benchmark-v2.jsonl` 每条带该布尔字段，且统计时能排除。

**Checkpoint（MVP）**：T009–T014 已完成，**"丢在哪一步"已能说出**（见 `REPORT.md` 零节）。
但 T015–T017 未做 ⇒ **MVP 的"基准可信度"这一半尚未收口**。

---

## Phase 4: User Story 2 - 有一份可复跑的"改动前"基线（P2）

**Goal**: 配置、指标、逐条结果三样都冻住，以后任何改动都拿它当对照。

**Independent Test**: 同一套配置连跑两次，两次结果一致。

- [x] T018 [P] [US2] 配置记录（等价 `config.json`，**以散文式盘点代替**）→ `config-inventory.md`
- [x] T019 [P] [US2] 逐条原始结果（等价 `results.jsonl`）→ `funnel-per-query.jsonl`
- [x] T020 [US2] 指标（等价 `metrics.json`）：**每个数都带分母** → `funnel-summary.json`
- [x] T021 [US2] 可复跑：抽 12 条各跑两遍逐字一致（`determinism.json`）；
      **加强**：全量 171 条重跑对照，逐条通道名次 **0 处差异**（`rerun-consistency.json`，基线由 `git show` 取回，可复算）
- [x] T022 [US2] 记录代码版本（快照 `step-240` / `step-241`）供"这份基线是哪版跑的"追溯
- [ ] **T023 [US2] 未做 —— 按 `contracts/baseline.schema.md` 的三件套格式建基线**。
      现状是"散文 + jsonl"，**不是**契约要求的 `baseline-v0/{config,metrics,results}`。
      契约已在 `cee48cf` 里**如实标注"原定目录从未落地"**；
      **做完的标志**：要么补齐三件套，要么把契约改成与实际一致（**二选一，不许两套并存**）。

**Checkpoint**：US2 的**实质**已具备（配置/指标/逐条结果/可复跑），差的是**格式**。

---

## Phase 5: User Story 3 - 能用同一批问题比较"改了一处"带来的变化（P3）

**Goal**: 只改一处、其余冻结，在同一批问题上跑出改前/改后两组数。

**Independent Test**: 只改一个环节、其他全部固定，跑出改前/改后两组数。

- [ ] **T024 [US3] 🔴 未做 —— 第一个改进实验**（FR-013/FR-015）。**一步都没跑。**
      按 spec FR-015，第一个实验**只许改"文档送给模型理解时所用的文本"**（原文/页码/坐标一律不动）。
      **做完的标志**：`eval/recall-funnel/exp-1-<改动名>/` 里有 `changed`（只有一项）+ 改前/改后两组数。
- [ ] **T025 [US3] 未做 —— 开跑前先写止损线**（FR-014：放弃 / 观察 / 推广三档阈值）。
      **必须写在跑之前**，跑完再补无效。**做完的标志**：`exp-1-*/stop_loss.json` 的 mtime **早于** 结果文件。
- [ ] **T026 [US3] 未做 —— 改前/改后对照与结论**（SC-004）。
      结论必须直接从前后的数字读出，**不接受"感觉变好了"**。
      **做完的标志**：`exp-1-*/verdict.json`，且每条结论能挂回具体条目。

**Checkpoint**：**US3 一格都没动** —— 本周期还没进入"改动"阶段。

---

## Phase 6: Polish & Cross-Cutting

- [x] T027 口径与复跑说明 → `eval/recall-funnel/README.md`
- [x] T028 更正留痕：两轮独立复核共 15 条问题逐条登记（含原错话与改法）→ `REPORT.md` §八
- [x] T029 小提交 + 快照（`step-240` / `step-241`）+ 冻结批次标签 `verify-freeze-funnel-1/2/3`
- [ ] **T030 未做 —— 把本次收口结果写回交接文档**：`docs/HANDOVER-2026-10-06.md` §五 那张表
      保留原表 + 追加"收口结果"列，**不删历史**。**做完的标志**：该文档 §五 每行都有 ✅/❌ 与出处。
- [ ] **T031 未做 —— 两批考卷的口径说明**（交接 §五 第 5 条）。
      `eval/bunny-benchmark/`（正向，24 条且**自标"只能算待复验"**：同一对输入 4 次调用结论相反）
      vs `eval/reverse-benchmark/`（反向，171 条）**口径不同、不许混用**。
      **做完的标志**：一处归属层写明各自的造法、样本量、已知缺陷、**能用它算什么/不能算什么**。
- [ ] **T032 未做 —— 下次改进实验前的准备**：按本仓纪律，
      ① 开跑前 `git tag` 冻结批次并数出提交条数写进任务书；② 派 verifier 前机械确认"没人在写这棵树"；
      ③ 只跑被触碰面的最小证据 + 快照。**做完的标志**：`exp-1-*/` 目录旁有一份 `PRE-EXP-CHECKLIST.md` 并逐项打过勾。

---

## Dependencies & Execution Order

### Phase 依赖

- **Phase 1（Setup）**：无依赖，已完成
- **Phase 2（Foundational）**：依赖 Phase 1，已完成 —— **它阻塞所有用户故事**
- **Phase 3（US1）**：依赖 Phase 2，主体已完成；**T015 是 T016/T017 的前置**（基准没确认，切片口径也没意义）
- **Phase 4（US2）**：依赖 Phase 2；T023 与 Phase 3 **可并行**（不同文件）
- **Phase 5（US3）**：**依赖 US1 的 T015 与 US2 的 T023** ——
  **基准未确认、基线格式未定，就跑改进实验 = 拿两把不同的尺子量**
- **Phase 6**：T030/T031 可与 Phase 5 并行；T032 是 Phase 5 的前置

### 用户故事依赖

- **US1（P1）**：可在 Phase 2 后立即开始 —— 是 US2/US3 的前提
- **US2（P2）**：可在 Phase 2 后开始，与 US1 并行（不同文件），但其"基线"要等 US1 的基准确定
- **US3（P3）**：**必须等 US1 的 T015 + US2 的 T023**

### 并行机会

- Phase 2 的 T005 与 T004 可并行（前者读代码/库，后者读文档）
- Phase 3 的 T010 与 T011 **不可并行**（T011 是对 T010 副本的校验，同一份仪器）
- Phase 4 的 T018/T019 可并行（不同文件）
- **T015（人工确认）与 T031（两批口径）可并行** —— 分属不同文件、互不依赖

---

## Parallel Example: US1 的收口两项

```bash
# 两项互不依赖，可同时开工（不同文件）：
Task: "T015 抽 ≥30 条做人工确认 → eval/recall-funnel/benchmark-v2-humancheck.jsonl"
Task: "T031 写两批考卷口径说明 → eval/benchmark-batches-README.md"
```

---

## Implementation Strategy

### MVP First（US1）

1. Phase 1 + Phase 2（已完成）
2. Phase 3 主体（T009–T014，**已完成**）→ **STOP and VALIDATE**：`REPORT.md` 零节能说出"丢在哪一步"
3. **MVP 尚未收口的部分**：T015（人工确认）—— 它决定"上面那些百分比能信到什么程度"

### Incremental Delivery

1. Setup + Foundational → ✅
2. US1 主体 → ✅（结论已出）
3. US1 收口（T015–T017）→ **下一步做这个**
4. US2 格式对齐（T023）→ 与 3 并行
5. US3（T024–T026）→ **只有 3、4 完成后才允许开跑**

### 三条不许越的线

1. **T015 没做之前，不许把 `REPORT.md` 的百分比当成"系统的召回率"引用**（宪法原则 III）。
2. **T025 的止损线必须先写**，跑完再补无效（FR-014）。
3. **诊断（Phase 3/4）完成前不得改任何检索算法**（FR-016）—— 本轮已遵守。

---

## Notes

- `[P]` = 不同文件、无未完成依赖
- **已完成项一律附产物路径**，可直接点开核
- **未完成项一律附"做完的标志"**，不接受"待优化"这种写法
- 每完成一条：小提交 + 快照；提交信息写清"改了什么 / 为什么 / 边界"
