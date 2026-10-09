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
- [ ] T019 跑 `pwsh -File scripts/run-gates.ps1 -Quick`（**不新增本项引入的红**）
- [ ] T020 写归属层：`docs/DEVELOPMENT-HISTORY.md` + `AUTO-CHAIN-HANDOFF.md`
- [ ] T021 **派独立复核**（本项属**必验类别**：改 schema + 动生产数据）

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
