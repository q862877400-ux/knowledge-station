# Tasks: 按目录范围提问时，向量通道要真的在范围内找

**Input**: Design documents from `/specs/003-vec-scope-pushdown/`

**Prerequisites**: [plan.md](plan.md) · [spec.md](spec.md) · [research.md](research.md) · [data-model.md](data-model.md) · [contracts/](contracts/contracts.md)

**Tests**: **本仓强制**（门禁 = pytest），且本项规格 FR-010 明写「**判据一个字不许放宽**」⇒ 测试任务必做。

**Organization**: 按 user story 分组（US1=P1 功能修复 / US2=P2 零回归 / US3=P3 迁移不重算）。

## Format: `[ID] [P?] [Story] Description`

- **[P]**：不同文件、无未完成依赖，可并行
- **[Story]**：US1 / US2 / US3

## Path Conventions

单仓：`src/`、`tests/`、`scripts/`、`specs/` 在仓库根。

---

## Phase 1: Setup

- [x] T001 跑两个探针确认修法成立 —— `specs/003-vec-scope-pushdown/probes/probe-vec-scope-fix.py` + `-fix2.py`
  **判据**：Q2a 返回 `['in_weak']`（1 行）；Q1 返回 0 行（复现）。**已做，读数见 research.md**

---

## Phase 2: Foundational（阻塞全部；**本仓红线：先契约后实现**）

- [x] T002 在 `pipeline/03-contract-delta.md` 追加「向量通道范围下推」契约增量节（含**回滚 SQL/命令**）
- [x] T003 在 `tests/test_contract.py` 加 `clause_vec` 形状契约用例（有 `doc_id` 列、是**普通列**、`embedding` 仍 512）
- [x] T004 改 `src/core/storage/schema.sql`：`clause_vec` DDL 加 `doc_id TEXT`
- [x] T005 改 `src/core/storage/clause_repo.py`（入库路径）INSERT 带 `doc_id`
- [x] T006 改 `src/core/storage/clause_repo.py`（补丁重算路径）INSERT 带 `doc_id`

**Checkpoint**：契约与写入侧就位 ⇒ 才允许改读侧。

---

## Phase 3: User Story 1 —— 在目录范围内提问，向量路不再假报"没有" (P1) 🎯 MVP

**Goal**：`hybrid_engine` 向量通道的范围过滤**真的下推**。
**Independent Test**：隔离库里，范围内放 1 条**全局最远**的条款 + 范围外 25 条**与查询完全一致**的近邻 ⇒ 必须返回范围内那条、且无范围外混入。

- [x] T007 [US1] 改 `src/core/retrieval/hybrid_engine.py`：向量通道范围过滤改走
  `doc_id IN (SELECT value FROM json_each(?))`（**唯一合法写法**，见 contracts Q1）
- [x] T008 [US1] 改 `tests/test_kb_scope_retrieval.py` 的 fixture：塞向量时带 `doc_id`
  ⚠ **断言一个字不改**（含"必须有命中"与"不许混进范围外"两条）
- [x] T009 [US1] 跑 `pytest tests/test_kb_scope_retrieval.py -q` ⇒ **全绿**（那条真缺陷用例转绿）
- [x] T010 [US1] **变异验证**：① 改回 `clause_revision_id IN (…)` ⇒ **必须红**；
  ② 改成字面量列表 `IN (?,?)` ⇒ **必须红**（返回范围外）。跑完**逐字节还原**（`sha256sum` 前后一致）

**Checkpoint**：US1 独立可验。

---

## Phase 4: User Story 2 —— 不限定范围时，行为一字不变 (P2)

**Goal**：主路径零回归。
**Independent Test**：同数据同查询，旧表 / 新表 top-20 **逐条相同**。

- [x] T011 [P] [US2] 用探针 Q6 复核"无范围 top-20 逐条相同"（`probe-vec-scope-fix2.py`）
- [x] T012 [US2] 跑 `pytest tests/test_kb_scope_retrieval.py tests/test_doc_batch_delete.py tests/test_retrieval.py -q` ⇒ 全绿

**Checkpoint**：US1 + US2 同时成立。

---

## Phase 5: User Story 3 —— 已入库的 66 万条向量不许重算 (P3)

**Goal**：迁移是**搬运**，不是重算；分钟级；逐字节可核；可回滚。
**Independent Test**：迁移前后行数相同、向量逐字节相同、`doc_id` 与 `clause_revision` 全表一致。

- [x] T013 [US3] 写 `scripts/migrate-clause-vec-doc-id.py`：
  `--dry-run`（只读预演）/ `--apply` / `--db-copy`（全库备份）/ **幂等** / **三项自检** / 回滚步骤写进 docstring
- [x] T014 [US3] `--dry-run` 只读预演：算出待迁移行数、抽查几条 `clause_revision_id → doc_id` 映射
- [x] T015 [US3] `--apply --db-copy` 真跑（**先备份**；单事务；自检不过即失败）
- [x] T016 [US3] 迁移后核 INV-1/2/3：行数相同 / 向量 0 处不同 / `doc_id` 0 处不一致

**Checkpoint**：真库可用了。

---

## Phase 6: Polish & Cross-Cutting

- [x] T017 [P] 改 `tests/test_embedding_rebuild_resume.py::test_shadow_dim_matches_production_schema`
  的正则：**同步新 DDL 形状**，但**意图不变**（断言维度 == 512）
- [x] T018 [P] 改 `eval/recall-funnel/exp-17-embedding-production-plan/rebuild-shadow.py`：
  影子表 DDL 加 `doc_id TEXT` 并回填（保持"与生产同形"）
- [x] T019 跑 `pwsh -File scripts/run-gates.ps1 -Quick`（**不新增本项引入的红**）
  ⇒ **5/5 · exit=0**（`tsc` / `mypy` / `verify:commands 22/22` / `pssa-guard` / `smoke 42/42 套全过`，11m07s）
- [x] T020 写归属层：`docs/DEVELOPMENT-HISTORY.md` + `AUTO-CHAIN-HANDOFF.md`
- [x] T021 **派独立复核**（本项属**必验类别**：改 schema + 动生产数据）

---

## Dependencies & Execution Order

```
T001 (探针)  ──► T002/T003 (契约)  ──► T004 (schema)  ──► T005/T006 (写入侧)
                                                            │
                                                            ▼
                                    T007 (读侧) ──► T008 ──► T009 ──► T010 (变异)
                                                            │
                                          T011/T012 (零回归) ┘
                                                            │
                                                            ▼
                                    T013 ──► T014 ──► T015 ──► T016 (迁移)
                                                            │
                                                            ▼
                                          T017/T018 (连带) ──► T019/T020/T021
```

- **契约（T002/T003）必须先于实现**（本仓红线：`pipeline/03-contract-delta.md` → `tests/test_contract.py` → `schema.sql`）
- **写入侧（T005/T006）必须先于迁移（T015）** —— 否则新入库的条款会静默没有 `doc_id`
- **迁移（T015）必须后于读侧（T007）** —— 代码先就位，再动数据

## Parallel Opportunities

- T002 / T003 可并行（不同文件）
- T005 / T006 可并行（同一文件两处，但互不依赖 ⇒ 建议同一人顺序改，避免冲突）
- T011 / T012 可并行
- T017 / T018 可并行

## Implementation Strategy

**MVP = US1（P1）**：T001–T010 跑完，那条真缺陷用例转绿，就已经是**用户可见的修复**。
US2 是**回归防线**（不新增功能，但必须成立）；US3 是**让真库跟上**（不改代码，改数据）。

## Notes

- ⚠ **判据不许放宽**（FR-010）：`test_kb_scope_retrieval.py` 的断言**一个字不改**，只改它自己的 fixture。
- ⚠ **范围过滤只许用 `doc_id IN (SELECT value FROM json_each(?))`** —— 字面量列表与 `OR` 实测**会返回范围外**（比现状更糟）。
- ⚠ 迁移**不许重跑嵌入模型**（实测纯拷贝逐字节一致）。
- ⚠ 本项**不碰**禁碰区（`tools/gov-qa/**`、公告组件），**不做** exp-17 接生产。

---

## Phase 7: Convergence

> `/speckit-converge` 于 **2026-10-09** 跑：读 `spec.md` / `plan.md` / `tasks.md` 作为**唯一意图源**，
> 逐条比对**当前代码与产物**（不是 diff、不看历史）。**只追加，不改上面任何一条。**
>
> **清点**：FR-001…FR-010 共 10 条｜SC-001…SC-006 共 6 条｜plan 决策 3 条｜宪法 7 条。
> **判定**：FR-002/003/004/005/006/007/008/010、SC-001/002/003/004/006 **均已满足**（各有读数，见上）。
> **发现 5 条未闭合**（下表），按严重度排序追加为任务。
>
> | ID | gap | 严重度 | 源 | 证据 | 剩余工作 |
> |---|---|---|---|---|---|
> | F1 | `partial` | **HIGH** | FR-009 / SC-005 | 写侧 `doc_id` 只有**静态锚点**判据（`test_contract.py` 数 INSERT 次数）；`test_kb_scope_retrieval.py` 的夹具是**直接 INSERT**、**绕过** `clause_repo` | 补**端到端**判据：真经 `clause_repo.insert_clauses` 写一条 → 断言 `clause_vec.doc_id == clause_revision.doc_id` |
> | F2 | `missing` | **HIGH** | FR-009（运行前置） | 迁移的**运行前置**没写进任何产物：跑着的两个 `-m src.core.main` 是旧代码，仍按**两列**写向量 ⇒ `doc_id` 为空 ⇒ 新条款在范围提问里**静默消失** | 把"**引擎必须重启**"写进 `contracts/` 与 `quickstart.md`，并给**重启后的核验命令** |
> | F3 | `missing` | MEDIUM | plan / `contracts` M5 | `clause_vec_pre003`（回滚源）占 **2.6 GB**（库 2.96→5.6 GB），而 **C 盘 93% 满**；spec/contracts 只说"保留"，**没说何时可删、删前要满足什么** | 定**回收时机与前置判据**（复核通过 + 备份在 + 无 NULL `doc_id`），并写进 `contracts/` |
> | F4 | `partial` | LOW | 本轮过程 | `probes/probe-vec-scope-fix.py` 的 **Q1 已标作废**，但**脚本仍会跑那个无意义查询并打印"❌ 返回空"** ⇒ 后人只看输出会被误导 | 把 Q1 改成**生产形态**（或整段删掉），保留"作废"留痕 |
> | F5 | `unrequested` | LOW | 本轮过程 | 我在 `-Full` 跑着时又提交了两次（`46f45c6` / `f6bb3ef`）⇒ **该读数不对应单一提交**（违反本仓"边改边验"） | **工作树静默时重跑一次 `-Full`**，记可引用的读数 |
>
> ⚠ **宪法检查：无违规**（七条逐条核过；说人话 → `读我-大白话版.md`；从事实出发 → 本轮那次自我更正；
> 留痕 → 错话保留 + 就地更正）。

- [x] T022 [F1] 补**端到端**写侧判据：经 `clause_repo.insert_clauses` 真写一条（把嵌入器打桩成可用）
  ⇒ 断言 `clause_vec.doc_id` == `clause_revision.doc_id`；并做**变异**（去掉 `doc_id` ⇒ 必须红）
  per FR-009 / SC-005 (`partial`)
- [x] T023 [F2] 把"**引擎必须重启**"写进 `contracts/contracts.md`（迁移契约 M7）与 `quickstart.md` §4，
  并给**重启后的核验命令**（`migrate-clause-vec-doc-id.py --dry-run` 看 `doc_id 为空` 是否为 0）
  per FR-009 (`missing`)
- [x] T024 [F3] 定 `clause_vec_pre003` 的**回收时机与前置判据**（复核 PASS + 全库副本在 + `doc_id` 空值 0
  + 与 `clause_revision` 零不一致）⇒ 写进 `contracts/contracts.md`；**回收动作本身等业主点头**
  per plan / contracts M5 (`missing`)
- [x] T025 [F4] 改 `probes/probe-vec-scope-fix.py`：把 **Q1** 换成生产形态（`clause_revision_id IN
  (SELECT clause_revision_id FROM clause_revision WHERE doc_id IN (json_each))`）或整段删掉，
  **保留"作废"留痕** per 本轮过程 (`partial`)
- [x] T026 [F5] **工作树静默时**重跑 `run-gates.ps1 -Full` 并记可引用读数（含 junit 的 failed 清单）
  per 本轮过程 (`unrequested`)
  ⇒ **2026-10-10 07:42 收口**：`-Full` = **9/9 · exit=0**（`tsc` / `mypy` 153 文件 /
  `verify:commands 22/22` / `pssa-guard` / `smoke 42/42` / `pytest 2695 passed · 0 failed · 2 skipped` /
  引擎门禁 / `verify-tools-real 9/9` / 真宿主 e2e / 棘轮 `2692 ≥ 2692`），**junit 的 failed 清单为空**。
  **静默已机械核**：该跑窗口（07:13–07:45）里**代码面**（`src/ tests/ plugin/ scripts/`）
  **零提交**（`git log --since=... --name-only` 过滤该四前缀为空）；窗口内唯一提交 `88644c6`
  只动 `tools/gov-qa/**`（另一个自动化）。⇒ 这次读数**对应单一代码面**（`3f23206`）。
  ⚠ **同一代码面的第一次跑（07:26）是 8/9**：`pytest` 1 条红
  （`test_measure_harness.py::test_尺能量出_def_没有把事件循环堵住`）。已定性为
  **非本批引入的 GIL 争用型 flake**并登记进 `docs/TEST-FLAKES.md`（含**复现探针**与两个被证伪的候选）。

**下一步**：跑 `/speckit-implement` 收掉 T022–T026（其中 **T024 的回收动作要业主点头**）；
之后再跑一次 `converge` 应只剩更少项。

---

## Phase 8: Convergence（**复核回复轮**，2026-10-09）

> 独立复核（`general-purpose-1`，冻结 `verify-freeze-spec003-vecscope` = `f5fd5ce`）判定
> **有条件 PASS**（**无 P0**；P1×1 / P2×4）。报告已**字节级归档**：
> `docs/verify-briefs/VERIFY-REPORT-spec003-vecscope.md`（sha256 `9f489a68…`，16,171 B）。
> **逐条处置如下**（按本仓"打回就地更正并留痕"）。

- [x] T027 [P1] **把已作废的说法从残留里清掉**（**复核抓到的真问题**）：
  我先前只改了 `research.md` / `spec.md` / 大白话版 / 契约增量，**漏了 6 处** ——
  `hybrid_engine.py` / `schema.sql` / `test_contract.py` / `test_kb_scope_retrieval.py`×2 /
  `plan.md` / `data-model.md`。现已**逐处改成复核确认的精确条件**
  （"**只要范围子查询返回的 id 里有一个在向量表里没有对应行，整体就返回 `[]`**"），
  并**保留原话 + 更正留痕**（原则 V：不许留"半作废"的句子）。
  ⚠ 其中 `hybrid_engine.py` 里那句引用 `probe-vec-scope-fix.py` Q1 的**也是被推翻的那条** ⇒ 一并改掉。
- [x] T028 [P2-①] 迁移脚本 docstring 补**孤儿向量**说明（`vec0` 的 TEXT 列拒 NULL ⇒ 事务内失败、
  整体回滚，不留半成品；实测真库孤儿 **0**）。
- [x] T029 [P2-②] 迁移脚本 docstring 把"自检不过 ⇒ 整体回滚"**拆成两段**：
  事务内 3 条（不过即回滚）+ 事务后 1 条（**逐字节比对在 COMMIT 之后** ⇒ 不过**不会**自动回滚，
  靠脚本打印回滚命令兜）—— 原来那句**把两段混成一句，不准确**。
- [x] T030 [P2-③] `probes/probe-vec-scope-fix.py` 的 **Q3 崩溃**（`vec0` 无 `rowid` 列）⇒ 包 try/except，
  **不再把 Q4 带崩**；同时把收尾那句"Q2a/Q2b 才是修法"**更正**（Q2b 是**反例**）。
- [x] T031 [P2-④] `research.md` 引用的 `probe-scale-flip2.py` **不存在**（副本已改名 `probe-mechanism.py`）⇒ 改正。

**下一步**：只剩 **T026**（工作树静默时重跑 `-Full`）；其余全收。
