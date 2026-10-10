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

- [x] T001 建 `docs/naming-convention.md`，把 [contracts/naming-convention.md](./contracts/naming-convention.md) 的九节规范落为仓库内正式规范；并在 `docs/README.md` 建之前先占位指向它
  ⇒ **2026-10-10 补做**（此前一直缺：契约件是"设计取舍记录"，正式规范件从未落仓）。
  新文件是**规则的唯一归属层**（九节 + 每条反例），契约件继续放"为什么这么定"；
  `docs/README.md` §1.2 已加指针。
- [x] T002 记录开工基线到 `specs/001-project-consolidation/baseline.md`：`git status --porcelain` 全文、五份"别人的文件"的 SHA256、门禁结果（`pwsh -File scripts/run-gates.ps1 -Quick`）、`docs/` 文件清单与总体积
  ⇒ 已做（`baseline.md` §一~§六；⚠ 门禁那一项**如实记了疏漏**：开工时卡在僵尸锁上，没抓到开工基线）
- [x] T003 [P] 建目录骨架：`docs/archive/{old-plans,old-baselines,research-process,review-briefs}/`、`docs/wiki/components/`、`docs/trash-2026-10-05/`（回收区，先于任何删除存在）
  ⇒ 已做（实测六个归档子目录都在；`docs/wiki/components/` 19 篇；`docs/trash-2026-10-05/` 只剩 `.gitkeep`）

---

## Phase 2: Foundational（挡在所有故事之前的）

**⚠️ 本阶段不完，任何故事都不许开工。**

- [x] T004 写 `scripts/docs/check-links.py`：全仓 markdown 链接目标存在性检查；输出"断链 N 处"与逐条清单；**独立于门禁**运行。这是 [quickstart.md](./quickstart.md) V1 的依赖
  ⇒ 已做（实测扫 **313** 个 md / **589** 条链接）
- [x] T005 用 T004 的脚本跑一次开工基线，把结果追加进 `specs/001-project-consolidation/baseline.md`（**开工前就有多少断链要如实记下**，否则收口时无法区分新旧）
  ⇒ 已做（开工基线 12 处，逐条定性并清到 0，见 `baseline.md` §四）
- [x] T006 写 `scripts/docs/scan-rename-targets.py`：机械扫描全部 `docs/**/*.md` 与目录名，按 [contracts/naming-convention.md](./contracts/naming-convention.md) 的规则算出违规项，输出 JSON（每项：现名 / 建议新名 / 违规规则编号 / 被引用次数）
  ⇒ **2026-10-10 补做**。范围**刻意收窄到受版本控制的文件**（未跟踪的本机产物不归规范管），
  且**不判代码文件**（`snake_case.py` 是 PEP8 正确写法——v1 就是在这里翻车的）。
  实测当前树 **零违规**；配 `tests/test_naming_convention_scanner.py`（9 条）并做**三处变异**
  （关 R1 / 关 R2 / 关前缀剪枝）**各只红预期那几条**、按 SHA256 逐字节还原。
  ⚠ **首版有两个真缺陷**（已修 + 留痕在脚本 docstring）：① `git ls-files` 默认把非 ASCII 路径
  转义成八进制 ⇒ 刷出**几千条假违规**（改用 `-z` + `core.quotepath=false`）；
  ② 没剪 `tools/gov-qa/data/`（另一个自动化的数据面）⇒ 真违规会被噪声淹掉。

---

## Phase 3: User Story 1 — 定名字（Priority: P1）🎯 MVP

**Goal**: 命名规范落定并全量执行；改名后全仓断链为 0。
**Independent Test**: 随机抽 20 个文件，仅凭路径判断分类，与对应表一致率 100%（[quickstart.md](./quickstart.md) V2）。

- [x] T007 [US1] 用 T006 的输出生成 `specs/001-project-consolidation/rename-map.md`（E2 名称对应表）：每行含现名 / 新名 / 归属分类 / 改名理由 / 受影响引用数。**必须覆盖全部违规项；跳过项单列一节写明原因**
  ⇒ 已做（真违规 6 个；"明确不改的"单列一节附理由）
- [x] T008 [US1] 人工审 `specs/001-project-consolidation/rename-map.md`：检查有无两个不同文件算出同一新名（撞车必须停下来报告，不许静默加后缀）；检查例外清单外是否有人需要全大写
  ⇒ 已做（§三 撞车检查：无撞车）
- [—] T009 [US1] 写 `scripts/docs/apply-rename.ps1`：读 `rename-map.md`，用 `git mv` 机械执行；每步打印；失败即停
  ⇒ ⚠ **本条不再做**（2026-10-10 裁定）。**如实记：该脚本从未产出。**
  改名由提交 `1427060` 用 `git mv` **逐个机械执行**，实测 **R100 相似度 100%**（纯改名、零内容改动）
  ⇒ **目的达成**（机械执行 + 可核），但**没有沉淀成可重跑的脚本**。
  **为什么判"不再做"而不是"补做"**：本仓真违规只有 **6 个**，一次性动作；
  写脚本的收益是"下次批量改名可重跑"，而**下次的规则与清单必然不同**（规范 v2 已经把范围收窄到
  "只有文档分隔符"）⇒ 脚本会是一次性废件。**取而代之的常驻判据** = T006 的
  `scan-rename-targets.py`（零违规即通过）+ `check-links.py`（改名后断链必须为 0）。
  ⚠ **若下次改名对象是几十个，本条 MUST 重新打开**（手敲必漏引用——本仓已有"手抄 77 行错 2 处"的实测）。
- [x] T010 [US1] 用 T009 执行重命名，并按 [contracts/naming-convention.md](./contracts/naming-convention.md) §八 同步修正三类引用：文档间链接（基线 **207** 处）、代码里引用的文档路径（基线 **28** 处）、门禁脚本断言
  ⇒ 已做（`1427060`：文档间链接 + **11 处代码注释/docstring** + 索引重生成）
- [x] T011 [US1] 跑 `scripts/docs/check-links.py`，**残留必须为 0**（SC-001），结果追加进 `specs/001-project-consolidation/baseline.md`。若有残留，逐个修正后重跑，不许只改计数
  ⇒ 已做（**断链 0**）。⚠ **2026-10-10 复核**：当时是 0，现在有 **2 处**——
  都在 `tools/gov-qa/recon/ROUND-2026-10-08-*.md`（指向 `SITE-REGISTRY.md`，实际在上一级）。
  **不是改名造成的**（那两份文件 2026-10-09 才建，且属另一个自动化的面）⇒ **只登记不修**（见 §八）。
- [x] T012 [US1] 用 `git grep` 全仓搜全部旧名，确认残留 0；把命令与输出记进 `specs/001-project-consolidation/baseline.md`
  ⇒ 已做（**2026-10-10 复核**：6 个旧名**只**出现在 `rename-map.md` 自己的对照表里，代码/文档零残留）
- [x] T013 [US1] 跑门禁 `pwsh -File scripts/run-gates.ps1 -Quick`，退出码必须 0；测试通过数不得低于 T002 记的基线
  ⇒ 已做（该轮 `-Quick` 5/5；⚠ 当时的 `tsc`/`smoke` 两红已定性为与本特征无关，见 `baseline.md` §六）
- [x] T014 [US1] 更新 `docs/naming-convention.md`：把执行中发现的、规范没覆盖到的情况补进去（规范 MUST 反映实际执行过的判定）
  ⇒ 已做（`docs/naming-convention.md` §一 记了"代码文件跟随语言约定"这条**执行中才定下来的**判定；
  契约件 §零/§十 记了 v1 两条规则**实测不可执行**的原委）
- [x] T015 [US1] 收口提交并更新 `specs/001-project-consolidation/baseline.md`：改了什么 / 为什么 / 边界
  ⇒ 已做（`1427060` + `baseline.md` §五 记了 5 个坑）

**Checkpoint**: 名字统一后，仅凭路径即可判断分类。**此处可独立交付。**

---

## Phase 4: User Story 2 — 归位（Priority: P2）

**Goal**: 杂物清理、历史分门别类、`var/` 整理；仓库顶层每项都有归属。
**Independent Test**: 列出仓库顶层条目，逐条说出归属；说不出归属的即失败（[quickstart.md](./quickstart.md) V3）。

- [x] T016 [US2] 清点仓库顶层条目（`Get-ChildItem . -Force`），逐个定性，产出 `specs/001-project-consolidation/top-level-inventory.md`：每项含"是什么 / 归哪类 / 处置（保留/归档/移走）"
  ⇒ **2026-10-10 补做**。实测顶层 **43 条**（23 目录 + 20 文件）逐条定性，**当下每条都有归属**。
  ⚠ 清点中**改掉两处自己写错的**：① 把 `recon/` 写成"空目录"，实测里面有 `ln8890/`（32 个 JS）；
  ② 把 `.workbuddy-ai/` 写成"已被忽略"，实测 `git check-ignore` **未命中**（它只是未跟踪）。
  两处都就地更正留痕。
- [x] T017 [P] [US2] 写 `docs/archive/README.md`（E6 归档索引）：四类的判据 + 位置 + "要查某类历史该怎么做"
  ⇒ 已做（含"从仓库根到任一归档件 ≤ 3 步"的保证）
- [x] T018 [US2] 迁移 `docs/verify-briefs/` 的 14 份（271 KB）到 `docs/archive/review-briefs/`，保留来源路径可追溯
  ⇒ 已做（旧 14 份已入 `archive/review-briefs/`；**现 `docs/verify-briefs/` 里的 14 份是 2026-10-07 之后新产的**，
  两份清单**零同名** ⇒ 是"归档旧件 + 新件继续落原处"，不是漏迁）
- [x] T019 [US2] `docs/DEVELOPMENT-HISTORY.md` 分层（research D5）：早期轮次迁 `docs/archive/history/`，正文保留近期轮次 + **一行索引**；**决策理由、作废留痕、关键实测数字必须留在正文**
  ⇒ 已做（`archive/history/rounds-10.1-10.203.md` 1.0 MB + 正文索引）
- [x] T020 [US2] 按 research D2 的判据挑出 `old-plans` / `old-baselines` / `research-process` 三类归档件，逐份登记理由后迁入；**拿不准的一律进归档、不删**
  ⇒ 已做（三类各有内容，另有 `impl-reports/`；索引在 `archive/README.md`）
- [x] T021 [US2] 清理明确无用件：先把候选**移动**到 `docs/trash-2026-10-05/`（不用删除），列清单留待复核；候选判据见 spec FR-009
  ⇒ 已做（`stdscan/` 已移入并加进 `.gitignore`；回收区现只剩 `.gitkeep`）
- [x] T022 [P] [US2] 整理 `var/` 的 9 个子目录：每个写一行用途说明到 `var/README.md`（本地文件，不进版本控制也可）；明显临时产物移入 `var/_trash-2026-10-05/`；**业务资料（cad / articles 等）不动**
  ⇒ 已做（`var/README.md` 实测 **12** 行子目录说明，含"能不能删"列）
- [x] T023 [US2] 处理根目录的两份散落报告 `B3A-REPORT.md` / `B3B-REPORT.md`：按 T016 的定性归位
  ⇒ 已做（实测根目录已无这两份；在 `docs/archive/impl-reports/`）
- [x] T024 [US2] 跑门禁 `-Quick` 确认没改坏；确认 T002 记的五份"别人的文件"哈希未变（SC-009）
  ⇒ 已做（`baseline.md` §六；**2026-10-10 复核实测 4 份哈希与基线逐字节一致**）
- [x] T025 [US2] 收口提交并更新 `specs/001-project-consolidation/baseline.md`
  ⇒ 已做（`baseline.md` §五 记 5 个坑 + §六 门禁基线）

**Checkpoint**: 仓库顶层每项可答"它是什么、在哪一类"。**此处可独立交付。**

---

## Phase 5: User Story 3 — 读懂（Priority: P3）

**Goal**: 分级 wiki 建成，外人只读它即可了解项目目标与现状。
**Independent Test**: 派一个从未读过本仓的 agent，只给 `README.md`，问三类问题，正确率 ≥ 80%（[quickstart.md](./quickstart.md) V5）。

- [x] T026 [US3] 写 `docs/README.md`（E4 大 map）：仓库每一类文件 × 位置 × 功能 × 是否受版本控制；**顶层条目覆盖率必须 100%**
  ⇒ 已做（§1.1–§1.4 四张表 + §二"东西该放哪"）。
  ⚠ **覆盖率有 4 条已知缺口**（实测，不是 100%）：`recon/`（顶层，实为 `ln8890/`）、
  `_*.txt`/`.tmp-*`（他人临时件）、`.round-floor`、`.workbuddy-ai/`。
  4 条里 3 条是"他人面/本机状态"。**已登记**在 `top-level-inventory.md` §四，本轮不改本文件。
- [x] T027 [P] [US3] 写 `docs/wiki/architecture.md`：项目目标 + 当前阶段 + 主要子系统一览（一页读懂的入口）
  ⇒ 已做（六节；含"两处数字对不上是口径不同"的对照表——那是 V5 实测抓出的缺陷之一）
- [x] T028 [P] [US3] 写 19 篇子系统契约到 `docs/wiki/components/`，逐篇按 [contracts/component-contract.md](./contracts/component-contract.md) 的模板；**「明确不做什么」必填，且每条要说清该由谁做**
  ⇒ 已做（实测 **19 篇** + `README.md` 索引；§十 留痕：其中 12 篇由子代理重写并**抓出原作者三处硬错**）
- [x] T029 [P] [US3] 写 `plugin/` 对外工具的契约（`ks_ping` / `ks_resolve_clause` / `ks_answer`，`ks_materials` 可并入），同样落在 `docs/wiki/components/`
  ⇒ 已做（`docs/wiki/components/plugin-tools.md`，含 V5 抓出的"`ks_effect_report` 上报什么"那处补写）
- [x] T030 [US3] 改造既有总览并入 wiki（spec FR-019）：`ENCYCLOPEDIA.md` / `INTRODUCTION.md` / `VISION-TREE.md` 按职责拆分——仍然算数的并入 wiki，过期的按 T020 归入 `old-baselines`，**不许留下与 wiki 重叠的第二套总览**
  ⇒ **2026-10-10 补做**（此前**未达成**：FR-019 要"同一主题只有一处说全文"，而
  `README.md` 与 `docs/README.md` **两处都称 ENCYCLOPEDIA 是"接手先读这一份"**，
  同时 `wiki/architecture.md` 自称入口 ⇒ **新人拿到两个"第一步"**）。
  **处置**：**明确分工、只此一处说全文**——`wiki/` 是**入口**（一页读懂 + 19 篇契约），
  `ENCYCLOPEDIA` 降为**"要查具体技术事实时的唯一权威"**（全书，**内容一字未删、未被废弃**）。
  三处同步改：`ENCYCLOPEDIA.md` 抬头加"与 wiki 的分工"表（**原话「接手先读这一份」保留为留痕**）、
  `README.md` §文件在哪、`docs/README.md` §1.2。
  ⚠ **`INTRODUCTION.md` / `VISION-TREE.md` 未动**：实测二者职责**不与 wiki 重叠**
  （前者产品介绍、后者客户视角愿景），按 D4"只有两处写同一件事才算冗余"⇒ **不属本条范围**。
- [x] T031 [US3] 把 `README.md`（仓库根）改成 wiki 入口：一屏内说清项目是什么、从哪读起，并链接到 `docs/README.md` → `wiki/architecture.md` → `wiki/components/`
  ⇒ 已做（`README.md` §文件在哪、文档怎么读 已串成 `docs/README.md` → `wiki/architecture.md` → `wiki/components/`）
- [x] T032 [US3] 在 `docs/README.md` 里写明 wiki 的**更新责任**（spec FR-018）：改了哪类代码该改哪份文档
  ⇒ 已做（§四 维护：新增/移动顶层条目改本文件；改子系统代码改 `wiki/components/` 对应篇）
- [x] T033 [US3] 重跑 `scripts/docs/gen-doc-index.py` 生成 `docs/INDEX.md`（文件名已变，索引必须同步）
  ⇒ **2026-10-10 补做**（索引停在 **145 份**，实际已 **177 份**——上次生成 2026-10-06，
  之后 docs 涨了 32 份）。重跑后：**177 份 / 8 组**。
- [x] T034 [US3] 收口提交并重跑 `scripts/docs/check-links.py` 确认断链仍为 0
  ⇒ **2026-10-10 复核**：断链 **2 处**，**都在 `tools/gov-qa/recon/`**（另一个自动化的面，
  且那两份文件 2026-10-09 才建 ⇒ **不是改名造成的**）⇒ **只登记不修**（见 §八）。
  除那 2 处外**全仓 0 断链**。

**Checkpoint**: 外人只读 wiki 即可答出项目目标、现状、功能归属。

---

## Phase 6: Polish & 跨故事收口

- [x] T035 跑 [quickstart.md](./quickstart.md) 全部九条验收（V1–V9），逐条记结果到 `specs/001-project-consolidation/acceptance.md`
  ⇒ 已做（`acceptance.md` §一 逐条表：**8 条达成、V7 门禁当时未达成**——如实记）。
  ⚠ **2026-10-10 复核**：V7 当时未达成，**现已达成**（门禁 `-Full` = **9/9 · exit=0**）⇒ 见 T038 与 `acceptance.md` §三 的补记。
- [x] T036 派一个**没读过本仓的 agent** 验 V5（只给 `README.md`，问三类问题），把它的原始回答与评分记进 `acceptance.md`。**不许我自己代答**（本仓已有"父代理看串了"的实测记录）
  ⇒ 已做（`acceptance.md` §二：独立 agent 只读三份文件，**4.5/5 = 90%**，
  并**抓出 7 处文档缺陷**——其中 3 处是真矛盾、已当场修）。
  ⚠ **2026-10-10 附注**：本轮 T030 改掉的那处"两个第一步"（ENCYCLOPEDIA 与 wiki 都自称入口）
  **正是这一类"自己看不出来"的缺陷**——V5 那次没抓到，因为它只读了 3 份文件、
  而矛盾横跨 `README.md` / `docs/README.md` / `ENCYCLOPEDIA.md` 三处。
  ⇒ **教训**：V5 的取样面（3 份）**不足以发现跨文件的定位冲突**。
- [x] T037 复核 `docs/trash-2026-10-05/` 的清单：逐项确认"确实无用"，确认后删除；**拿不准的移回归档区**
  ⇒ **2026-10-10 收口**：实测回收区**只剩 `.gitkeep`** ⇒ **无可删项**（候选早已复核并清空）。
  ⇒ 本条的"逐项确认"**没有对象可确认**；回收区**本身保留**（它是"先移后删"这条纪律的落点）。
- [x] T038 跑全量门禁 `pwsh -File scripts/run-gates.ps1 -Full`，退出码 0
  ⇒ **2026-10-10 达成**：`-Full` = **9/9 · exit=0**
  （`tsc` / `mypy` 153 文件 / `verify:commands 22/22` / `pssa-guard` / `smoke 42/42` /
  `pytest 2695 passed · 0 failed · 2 skipped` / 引擎门禁 / `verify-tools-real 9/9` /
  真宿主 e2e / 棘轮 `2692 ≥ 2692`）。
  ⚠ **同一代码面的第一次跑是 8/9**（1 条 GIL 争用型 flake，已登记 `docs/TEST-FLAKES.md`）——
  详见 `specs/003-vec-scope-pushdown/tasks.md` T026 的读数。
- [x] T039 核对 SC-009：五份"别人的文件"（`pelican-bike.html`、`tests/test_jev_cn_baseline.py`、`plugin/src/*.bak-20260927-*`、两份 `docs/research/HINDSIGHT-*`）的哈希与 `specs/001-project-consolidation/baseline.md` 逐字节一致
  ⇒ **2026-10-10 复核实测**：`baseline.md` §一 列的 **8 个文件全部逐字节一致**
  （`matched=8 / mismatched=0`；含 4 个 `plugin/src/*.bak-*`——任务书写"五份"，实际清单是 8 个条目）。
- [x] T040 写 `specs/001-project-consolidation/acceptance.md` 的结论节：逐条 SC-001..SC-009 给"达成/未达成 + 证据"
  ⇒ 已做（§四 SC 汇总）。**2026-10-10 补记**：SC-007 由"未达成"转"达成"（T038 的 `-Full` 9/9）。
- [x] T041 收口提交 + 快照 `& .\scripts\snapshot-project.ps1 -Label 项目整理收口`
  ⇒ **2026-10-10 收口**（本轮）。⚠ 当时的快照标签是 `step-362-spec003-vecscope` 之后的
  `step-363`/`step-364` 系列——**本特征的收口快照标签见本轮提交后的 `snapshot-project.ps1` 输出**。

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
