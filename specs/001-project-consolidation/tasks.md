---

description: "Task list for 001-project-consolidation"
---

# Tasks: 项目整理与接手文档体系

**Input**: Design documents from `/specs/001-project-consolidation/`
**Prerequisites**: [plan.md](./plan.md)、[spec.md](./spec.md)、[research.md](./research.md)、[data-model.md](./data-model.md)、[contracts/](./contracts/)、[quickstart.md](./quickstart.md)

**约束（每条任务都受它管）**：
- MUST NOT 触碰别人的未提交改动：`pelican-bike.html`、`tests/test_jev_cn_baseline.py`、
  `plugin/src/*.bak-20260927-*`、`docs/research/HINDSIGHT-CAPABILITY-AUDIT-2026-09-28.md`、
  `docs/research/HINDSIGHT-FACTCHECK-2026-09-30.md`
- MUST NOT 改 `AGENTS.md`
- 不可逆删除前 MUST 留可恢复路径；`var/` 下**只移动不删除**

**路径约定**：所有路径相对仓库根 `D:\AI\work space\zcode`。

---

## Phase 1: Setup（开工准备）

- [ ] T001 建 `docs/naming-convention.md`，把 [contracts/naming-convention.md](./contracts/naming-convention.md) 的九节规范落为仓库内正式规范；并在 `docs/README.md` 建之前先占位指向它
- [ ] T002 记录开工基线到 `specs/001-project-consolidation/baseline.md`：`git status --porcelain` 全文、五份"别人的文件"的 SHA256、门禁结果（`pwsh -File scripts/run-gates.ps1 -Quick`）、`docs/` 文件清单与总体积
- [ ] T003 [P] 建目录骨架：`docs/archive/{old-plans,old-baselines,research-process,review-briefs}/`、`docs/wiki/components/`、`docs/trash-2026-10-05/`（回收区，先于任何删除存在）

---

## Phase 2: Foundational（挡在所有故事之前的）

**⚠️ 本阶段不完，任何故事都不许开工。**

- [ ] T004 写 `scripts/docs/check-links.py`：全仓 markdown 链接目标存在性检查；输出"断链 N 处"与逐条清单；**独立于门禁**运行。这是 [quickstart.md](./quickstart.md) V1 的依赖
- [ ] T005 用 T004 的脚本跑一次开工基线，把结果追加进 `specs/001-project-consolidation/baseline.md`（**开工前就有多少断链要如实记下**，否则收口时无法区分新旧）
- [ ] T006 写 `scripts/docs/scan-rename-targets.py`：机械扫描全部 `docs/**/*.md` 与目录名，按 [contracts/naming-convention.md](./contracts/naming-convention.md) 的规则算出违规项，输出 JSON（每项：现名 / 建议新名 / 违规规则编号 / 被引用次数）

---

## Phase 3: User Story 1 — 定名字（Priority: P1）🎯 MVP

**Goal**: 命名规范落定并全量执行；改名后全仓断链为 0。
**Independent Test**: 随机抽 20 个文件，仅凭路径判断分类，与对应表一致率 100%（[quickstart.md](./quickstart.md) V2）。

- [ ] T007 [US1] 用 T006 的输出生成 `specs/001-project-consolidation/rename-map.md`（E2 名称对应表）：每行含现名 / 新名 / 归属分类 / 改名理由 / 受影响引用数。**必须覆盖全部违规项；跳过项单列一节写明原因**
- [ ] T008 [US1] 人工审 `specs/001-project-consolidation/rename-map.md`：检查有无两个不同文件算出同一新名（撞车必须停下来报告，不许静默加后缀）；检查例外清单外是否有人需要全大写
- [ ] T009 [US1] 写 `scripts/docs/apply-rename.ps1`：读 `rename-map.md`，用 `git mv` 机械执行；每步打印；失败即停
- [ ] T010 [US1] 用 T009 执行重命名，并按 [contracts/naming-convention.md](./contracts/naming-convention.md) §八 同步修正三类引用：文档间链接（基线 **207** 处）、代码里引用的文档路径（基线 **28** 处）、门禁脚本断言
- [ ] T011 [US1] 跑 `scripts/docs/check-links.py`，**残留必须为 0**（SC-001），结果追加进 `specs/001-project-consolidation/baseline.md`。若有残留，逐个修正后重跑，不许只改计数
- [ ] T012 [US1] 用 `git grep` 全仓搜全部旧名，确认残留 0；把命令与输出记进 `specs/001-project-consolidation/baseline.md`
- [ ] T013 [US1] 跑门禁 `pwsh -File scripts/run-gates.ps1 -Quick`，退出码必须 0；测试通过数不得低于 T002 记的基线
- [ ] T014 [US1] 更新 `docs/naming-convention.md`：把执行中发现的、规范没覆盖到的情况补进去（规范 MUST 反映实际执行过的判定）
- [ ] T015 [US1] 收口提交并更新 `specs/001-project-consolidation/baseline.md`：改了什么 / 为什么 / 边界

**Checkpoint**: 名字统一后，仅凭路径即可判断分类。**此处可独立交付。**

---

## Phase 4: User Story 2 — 归位（Priority: P2）

**Goal**: 杂物清理、历史分门别类、`var/` 整理；仓库顶层每项都有归属。
**Independent Test**: 列出仓库顶层条目，逐条说出归属；说不出归属的即失败（[quickstart.md](./quickstart.md) V3）。

- [ ] T016 [US2] 清点仓库顶层条目（`Get-ChildItem . -Force`），逐个定性，产出 `specs/001-project-consolidation/top-level-inventory.md`：每项含"是什么 / 归哪类 / 处置（保留/归档/移走）"
- [ ] T017 [P] [US2] 写 `docs/archive/README.md`（E6 归档索引）：四类的判据 + 位置 + "要查某类历史该怎么做"
- [ ] T018 [US2] 迁移 `docs/verify-briefs/` 的 14 份（271 KB）到 `docs/archive/review-briefs/`，保留来源路径可追溯
- [ ] T019 [US2] `docs/DEVELOPMENT-HISTORY.md` 分层（research D5）：早期轮次迁 `docs/archive/history/`，正文保留近期轮次 + **一行索引**；**决策理由、作废留痕、关键实测数字必须留在正文**
- [ ] T020 [US2] 按 research D2 的判据挑出 `old-plans` / `old-baselines` / `research-process` 三类归档件，逐份登记理由后迁入；**拿不准的一律进归档、不删**
- [ ] T021 [US2] 清理明确无用件：先把候选**移动**到 `docs/trash-2026-10-05/`（不用删除），列清单留待复核；候选判据见 spec FR-009
- [ ] T022 [P] [US2] 整理 `var/` 的 9 个子目录：每个写一行用途说明到 `var/README.md`（本地文件，不进版本控制也可）；明显临时产物移入 `var/_trash-2026-10-05/`；**业务资料（cad / articles 等）不动**
- [ ] T023 [US2] 处理根目录的两份散落报告 `B3A-REPORT.md` / `B3B-REPORT.md`：按 T016 的定性归位
- [ ] T024 [US2] 跑门禁 `-Quick` 确认没改坏；确认 T002 记的五份"别人的文件"哈希未变（SC-009）
- [ ] T025 [US2] 收口提交并更新 `specs/001-project-consolidation/baseline.md`

**Checkpoint**: 仓库顶层每项可答"它是什么、在哪一类"。**此处可独立交付。**

---

## Phase 5: User Story 3 — 读懂（Priority: P3）

**Goal**: 分级 wiki 建成，外人只读它即可了解项目目标与现状。
**Independent Test**: 派一个从未读过本仓的 agent，只给 `README.md`，问三类问题，正确率 ≥ 80%（[quickstart.md](./quickstart.md) V5）。

- [ ] T026 [US3] 写 `docs/README.md`（E4 大 map）：仓库每一类文件 × 位置 × 功能 × 是否受版本控制；**顶层条目覆盖率必须 100%**
- [ ] T027 [P] [US3] 写 `docs/wiki/architecture.md`：项目目标 + 当前阶段 + 主要子系统一览（一页读懂的入口）
- [ ] T028 [P] [US3] 写 19 篇子系统契约到 `docs/wiki/components/`，逐篇按 [contracts/component-contract.md](./contracts/component-contract.md) 的模板；**「明确不做什么」必填，且每条要说清该由谁做**
- [ ] T029 [P] [US3] 写 `plugin/` 对外工具的契约（`ks_ping` / `ks_resolve_clause` / `ks_answer`，`ks_materials` 可并入），同样落在 `docs/wiki/components/`
- [ ] T030 [US3] 改造既有总览并入 wiki（spec FR-019）：`ENCYCLOPEDIA.md` / `INTRODUCTION.md` / `VISION-TREE.md` 按职责拆分——仍然算数的并入 wiki，过期的按 T020 归入 `old-baselines`，**不许留下与 wiki 重叠的第二套总览**
- [ ] T031 [US3] 把 `README.md`（仓库根）改成 wiki 入口：一屏内说清项目是什么、从哪读起，并链接到 `docs/README.md` → `wiki/architecture.md` → `wiki/components/`
- [ ] T032 [US3] 在 `docs/README.md` 里写明 wiki 的**更新责任**（spec FR-018）：改了哪类代码该改哪份文档
- [ ] T033 [US3] 重跑 `scripts/docs/gen-doc-index.py` 生成 `docs/INDEX.md`（文件名已变，索引必须同步）
- [ ] T034 [US3] 收口提交并重跑 `scripts/docs/check-links.py` 确认断链仍为 0

**Checkpoint**: 外人只读 wiki 即可答出项目目标、现状、功能归属。

---

## Phase 6: Polish & 跨故事收口

- [ ] T035 跑 [quickstart.md](./quickstart.md) 全部九条验收（V1–V9），逐条记结果到 `specs/001-project-consolidation/acceptance.md`
- [ ] T036 派一个**没读过本仓的 agent** 验 V5（只给 `README.md`，问三类问题），把它的原始回答与评分记进 `acceptance.md`。**不许我自己代答**（本仓已有"父代理看串了"的实测记录）
- [ ] T037 复核 `docs/trash-2026-10-05/` 的清单：逐项确认"确实无用"，确认后删除；**拿不准的移回归档区**
- [ ] T038 跑全量门禁 `pwsh -File scripts/run-gates.ps1 -Full`，退出码 0
- [ ] T039 核对 SC-009：五份"别人的文件"（`pelican-bike.html`、`tests/test_jev_cn_baseline.py`、`plugin/src/*.bak-20260927-*`、两份 `docs/research/HINDSIGHT-*`）的哈希与 `specs/001-project-consolidation/baseline.md` 逐字节一致
- [ ] T040 写 `specs/001-project-consolidation/acceptance.md` 的结论节：逐条 SC-001..SC-009 给"达成/未达成 + 证据"
- [ ] T041 收口提交 + 快照 `& .\scripts\snapshot-project.ps1 -Label 项目整理收口`

---

## Dependencies（故事完成顺序）

```
Phase 1 Setup
   └─> Phase 2 Foundational（T004/T005/T006 是全故事的公共前置）
          ├─> Phase 3 US1 定名字（P1）  ← 必须最先，否则后续成果立刻过期
          │      └─> Phase 4 US2 归位（P2）  ← 依赖 US1 的新名字
          │             └─> Phase 5 US3 读懂（P3）← 依赖 US1 的名字与 US2 的结构
          │                    └─> Phase 6 收口
```

**为什么 US1 必须先做**（写进 [research.md](./research.md) D1）：
先清理和建 wiki 再改名，这两样的成果会立刻过期（wiki 里写的路径、归档索引里的路径全要重写）。

**US2 与 US3 的关系**：US2 把东西归位，US3 才写得准"东西在哪"。
但 **US3 的大 map（T026）可以在 US2 部分完成后就开写**，只要 T016 的顶层清点已完成。

---

## Parallel Execution（可并行的）

| 批次 | 并行任务 | 前置 |
|---|---|---|
| 1 | T003（建骨架） | 无 |
| 2 | T017（归档索引）∥ T022（`var/` 整理）∥ T028/T029（组件契约，19+3 篇可分派） | 各自前置完成 |
| 3 | T027（项目现状）∥ T028 ∥ T029 | T026 完成 |

**T028 是最大的可并行面**：19 篇子系统契约彼此独立，可派多个 subagent 同时写。

---

## Implementation Strategy

**MVP = Phase 1 + Phase 2 + Phase 3（US1）**。
只做这些就交付完整价值：**名字统一、断链为 0、仅凭路径即可判断分类**。
这也是风险最高的部分（235 处引用要动），先做完先暴露问题。

**增量交付**：每个 Phase 结束都停在"可交付 + 门禁绿"的状态上，各自一次提交。

**不许跳步**：US1 未收口前不许开 US2——否则 US2 的搬运会与 US1 的改名互相污染。

---

## Notes

- `[P]` = 可并行（不同文件、无未完成依赖）
- 每条任务收口 MUST 提交，提交消息写清"改了什么 / 为什么 / 边界"
- **删除类任务（T021/T037）分两步**：先移动到回收区 → 复核清单 → 才真删。
  `var/` 下的东西**永不真删**（不受版本控制，删了没有安全网）
