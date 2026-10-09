---
description: "Task list for 政务问答采集系统的可运维化"
---

# Tasks: 政务问答采集系统的可运维化

**Input**: Design documents from `specs/004-govqa-operationalization/`

**Prerequisites**: plan.md ✅ / spec.md ✅ / research.md ✅ / data-model.md ✅ / contracts/ ✅

**Tests**: 本特性**包含测试任务** —— 因为 spec 的 12 条 Success Criteria 全部要求
「可外部观察的验证」，不写测试就无法证明达成（宪法 III 证据优于断言）。

**Organization**: 按用户故事分组，每条故事可独立实现、独立测试、独立交付。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可并行（不同文件、无未完成依赖）
- **[Story]**: US1 / US2 / US3 / US4
- 所有路径相对仓库根 `D:/AI/work space/zcode/`

## Path Conventions

本项目是**单项目 CLI 工具**：源码在 `tools/gov-qa/`，测试在 `tools/gov-qa/tests/`。

---

## Phase 1: Setup（项目初始化）

- [ ] T001 建 `tools/gov-qa/state/` 目录并在 `.gitignore` 里排除 `state/.poll.lock`（锁文件不入库，水位入库存）
- [ ] T002 [P] 建 `tools/gov-qa/tests/` 目录与 `tests/__init__.py`
- [ ] T003 [P] 在 `tools/gov-qa/` 下建 `common.py`：提供 `atomic_append_jsonl(path, rec)`（O_APPEND 单行写入）、`file_lock(path, timeout)`（文件锁）、`iter_records(glob)`（流式读 jsonl）三个工具函数
- [ ] T004 [P] 在 `tools/gov-qa/common.py` 加 `ascii_kv(dict)` 输出器：**所有机器可读输出必须走它**，保证纯 ASCII（R5 教训）

---

## Phase 2: Foundational（阻塞性前置，必须全部完成才能开始任何用户故事）

**⚠ 关键：本阶段不完成，US1–US4 都无法开始。**

- [ ] T005 在 `tools/gov-qa/state.py` 定义 `Watermark` 数据结构与读写：字段 `channel_key / type / value / updated_at / last_batch_count / last_success_at / consecutive_failures`（见 data-model.md E2），存 `state/watermarks.json`
- [ ] T006 [P] 在 `tools/gov-qa/state.py` 实现**水位只在成功后前移**（FR-003）：失败时只 `consecutive_failures += 1`，`value` 不动
- [ ] T007 [P] 在 `tools/gov-qa/state.py` 实现**水位损坏安全退化**（FR-006）：JSON 解析失败时返回「无水位」并标记 `needs_full=True`，不抛异常
- [ ] T008 [P] 在 `tools/gov-qa/state.py` 实现 `idset` 型水位的 **LRU 上限 50,000**（data-model.md E2 明确要求，否则 JSON 无限膨胀）
- [ ] T009 在 `tools/gov-qa/channel.py` 定义 `Channel` 数据结构（见 data-model.md E1），并从 `adapters.ADAPTERS` + 各模块 `SITE` 自动构建通道清单
- [ ] T010 [P] 在 `tools/gov-qa/channel.py` 实现**水位类型推断**：按 adapter 特征猜 `page` / `since` / `idset`，猜不出默认 `idset`（最安全）
- [ ] T011 [P] 在 `tools/gov-qa/channel.py` 实现 `region` 归属映射（从 `SITE["level"]` + `SITE["name"]` 解析出省/市，供 US2 用）
- [ ] T012 写 `tools/gov-qa/tests/test_state.py`：覆盖水位前移/失败不前移/损坏退化/LRU 四条规则
- [ ] T013 [P] 写 `tools/gov-qa/tests/test_channel.py`：验证通道清单覆盖全部 adapter（数量与 `ADAPTERS` 一致）

**Checkpoint**: 水位与通道两层就绪 ⇒ 可以开始 US1

---

## Phase 3: US1 —— 增量轮询（Priority: P1）🎯 MVP

**Goal**: 一条命令拿到全部通道的新增，且幂等、可断点续跑、可安全退化。

**Independent Test**: 连续两次 `poll.py --all`，第二次 `ADDED=0` 且全库 `DUPS=0`；
再人为破坏水位，验证不崩溃且退化为全量。

### 实现

- [ ] T014 [US1] 在 `tools/gov-qa/poll.py` 实现 CLI 骨架与参数解析：`--all / --channel / --level / --region / --dry-run / --quiet / --full`（契约见 contracts/poll.md）
- [ ] T015 [US1] 在 `tools/gov-qa/poll.py` 实现**增量调度核心**：对每个通道，按水位类型决定「从哪开始翻 / 翻到哪停」
  - `page` 型：从第 1 页开始，翻到「本页全部已见过」即停
  - `since` 型：只取时间 > 水位的条目
  - `idset` 型：翻全量但按 id 去重
- [ ] T016 [P] [US1] 在 `tools/gov-qa/poll.py` 实现**边采边落盘**（R3）：每条 `atomic_append_jsonl` 后立即 `flush`，不用「跑完才写」
- [ ] T017 [P] [US1] 在 `tools/gov-qa/poll.py` 实现**落盘前去重**（R2）：按 `(source, id)` 检查是否已在库（用内存 set + 每通道缓存）
- [ ] T018 [P] [US1] 在 `tools/gov-qa/poll.py` 实现**故障隔离**（FR-021/SC-012）：单通道异常被捕获，记录后继续下一通道
- [ ] T019 [US1] 在 `tools/gov-qa/poll.py` 实现**并发锁**（R7）：抢不到 `state/.poll.lock` 时退出码返回 `3`（不是失败）
- [ ] T020 [US1] 在 `tools/gov-qa/poll.py` 实现**退出码契约**：`0` 全成功 / `1` 有通道失败 / `2` 致命 / `3` 锁冲突
- [ ] T021 [US1] 在 `tools/gov-qa/poll.py` 实现**输出契约**：人类可读（中文汇总表）+ `--quiet` 纯 ASCII `KEY=VALUE`（走 T004 的 `ascii_kv`）
- [ ] T022 [US1] 在 `tools/gov-qa/poll.py` 实现 `--timing` 输出 `pages_fetched`（quickstart 场景 1.3 要求 —— 只看「新增 0 条」不能证明增量生效）

### 测试（必须）

- [ ] T023 [US1] 写 `tools/gov-qa/tests/test_poll_idempotent.py`：**SC-002** —— 连续两次轮询，第二次 `ADDED=0` 且 id 集合不变
- [ ] T024 [P] [US1] 写 `tools/gov-qa/tests/test_poll_resume.py`：**SC-003** —— 采集途中 kill，重跑后无重复且不丢数据
- [ ] T025 [P] [US1] 写 `tools/gov-qa/tests/test_poll_watermark_broken.py`：**FR-006** —— 水位损坏时不崩溃、退化为全量、不产生重复
- [ ] T026 [P] [US1] 写 `tools/gov-qa/tests/test_poll_isolation.py`：**SC-012** —— 一个通道失败不影响其他通道
- [ ] T027 [P] [US1] 写 `tools/gov-qa/tests/test_poll_lock.py`：**R7** —— 两个进程同时跑，一个返回 3，另一个正常完成
- [ ] T028 [US1] 写 `tools/gov-qa/recon/verify-idempotent.py`：**可自动跑的幂等验证器**（把 SC-002 从「靠人记」变成「一条命令」）

**Checkpoint**: US1 完成 ⇒ 用户唯一明说的目的达成 ⇒ **这是 MVP**

---

## Phase 4: US2 —— 覆盖完整性（Priority: P2）

**Goal**: 31 省级 + 333 地级每个都有销号行，弱区带缺口数值与未覆盖渠道清单。

**Independent Test**: `coverage-report.py --quiet` 输出 `PROV_TOTAL=31` / `CITY_TOTAL=333`；
`--region 云南省 --uncovered` 能列出未建源渠道。

- [ ] T029 [US2] 在 `tools/gov-qa/coverage.py` 定义 `CoverageUnit`（见 data-model.md E4）与聚合逻辑：从 `Channel.region` + 落盘量算 `total_records / gap / status`
- [ ] T030 [US2] 在 `tools/gov-qa/coverage.py` 内置 **31 个省级行政区 + 333 个地级行政区**的权威名单（含省直辖县级市处理规则）
- [ ] T031 [P] [US2] 在 `tools/gov-qa/coverage.py` 实现 `ratio_to_median`（R4）：按**同级**中位数算比值，不跨级比
- [ ] T032 [P] [US2] 在 `tools/gov-qa/coverage.py` 实现 `uncovered_channels`（FR-010）：列出该地区**尚未建源的渠道**；已穷尽的显式写「已穷尽」不留空
- [ ] T033 [P] [US2] 在 `tools/gov-qa/coverage.py` 实现**达标下限可调**：`--threshold-province`（默认 3000）/ `--threshold-city`（默认 500）
- [ ] T034 [P] [US2] 在 `tools/gov-qa/coverage.py` 实现**按口径过滤** `--scope law_std`（配合 GOAL.md 的「口径收窄」，分母可按新口径重算）
- [ ] T035 [US2] 写 `tools/gov-qa/coverage-report.py` CLI：`--level / --thin --top N / --region X --uncovered / --quiet`，退出码 `1` = 有 `none` 单元（契约见 contracts/coverage.md）
- [ ] T036 [US2] 写 `tools/gov-qa/tests/test_coverage.py`：验证 31/333 行数、gap 计算、`uncovered_channels` 非空或显式「已穷尽」

**Checkpoint**: US2 完成 ⇒ 能回答「还缺哪里、缺多少、缺什么渠道」

---

## Phase 5: US3 —— 数据可用性（Priority: P2）

**Goal**: 标签真实准确率可测、无静默空字段。

**Independent Test**: `field-audit.py` 报出「问题与答复同时为空」= 0；
`label-accuracy.py --sample 200 --export` 能导出人工核对表。

- [ ] T037 [US3] 写 `tools/gov-qa/recon/field-audit.py`：逐字段非空率 + **单独列出 `question` 为空但 `answer` 非空**的记录并带来源（FR-015）
- [ ] T038 [P] [US3] 在 `field-audit.py` 里报告「问题与答复同时为空」的条数，**SC-008 要求 = 0**
- [ ] T039 [US3] 写 `tools/gov-qa/recon/label-accuracy.py --sample N --export <csv>`：分层抽样（覆盖各标签、各来源），导出可人工核对的 CSV
- [ ] T040 [P] [US3] 在 `label-accuracy.py` 实现 `--score <csv>`：读人工填的 `label_ok` 列算真实准确率
- [ ] T041 [P] [US3] 在 `label-accuracy.py` 里**强制留痕**：未核对时输出「明确未做」，不许用模型自评数充数（宪法 III）
- [ ] T042 [US3] 修 `nat-mohurd` 的 `question` 为空问题（GOAL.md 下轮待办 2；已在 data-model.md E3 的验证规则里写明「指纹输入字段必须参与空值处理」）
- [ ] T043 [US3] 为 `extra.ingested_at` 与 `extra.scope_tag` 两个新字段写回填脚本 `tools/gov-qa/recon/backfill-derived.py`（data-model.md 的「本特性对现有数据的改动」要求纯新增、可回滚）

**Checkpoint**: US3 完成 ⇒ 能回答「这份数据的标签能不能信」

---

## Phase 6: US4 —— 自愈与可观测（Priority: P3）

**Goal**: 一句话结论、故障一次检出、纯 ASCII 接口。

**Independent Test**: 人为制造 3 类故障，`health.py --detail` 一次全检出并定位到文件。

- [ ] T044 [US4] 写 `tools/gov-qa/health.py`：聚合 4 项判据（数据总数 / 零数据适配器 / 重复 id / 标签覆盖）为 `HealthReport`（见 data-model.md E5）
- [ ] T045 [P] [US4] 在 `health.py` 实现**一句话结论**（SC-011）：`✅ 当前可用` 或 `❌ 当前不可用：<原因>`，中文，首行即结论（宪法 I 说人话）
- [ ] T046 [P] [US4] 在 `health.py` 实现 `--quiet` 纯 ASCII 输出：`VERDICT= / TOTAL= / FLOOR= / EMPTY= / DUPS= / COVERAGE= / ELAPSED=`（走 T004 的 `ascii_kv`）
- [ ] T047 [P] [US4] 在 `health.py` 实现 `--trace <file>`：追加执行轨迹（时间 / 解析值 / 结论），复用 `check.sh` 的 trace 思路
- [ ] T048 [US4] 在 `health.py` 实现**耗时统计**并在超 60s 时警告（SC-010）
- [ ] T049 [US4] 写 `tools/gov-qa/tests/test_health.py`：制造 3 类故障（删文件 / 塞重复 id / 注册空适配器）验证一次全检出（SC-009）
- [ ] T050 [P] [US4] 在 `tools/gov-qa/recon/audit-coverage.py` 加 `--coverage-table` 与 `--gaps --unit X`（quickstart 场景 2 要求，复用 US2 的 `coverage.py`）
- [ ] T051 [P] [US4] 在 `tools/gov-qa/recon/audit-coverage.py` 加 `--health`（quickstart 场景 4.1 要求，委托给 `health.py`）

**Checkpoint**: US4 完成 ⇒ 能回答「现在能不能用」

---

## Phase 7: Polish & 跨切面

- [ ] T052 [P] 更新 `tools/gov-qa/SITE-REGISTRY.md`：登记每个通道的 `watermark_type` 与 `self_reported_total`（M1 要求）
- [ ] T053 [P] 写 `tools/gov-qa/README.md`：面向使用者的「怎么轮询 / 怎么看覆盖 / 怎么体检」三段说明（宪法 I：说人话，不用内部术语）
- [ ] T054 按 `quickstart.md` 的 **9 个验证场景**逐条跑通，把实测结果写回 `quickstart.md`（宪法 III：证据优于断言）
- [ ] T055 [P] 在 `GOAL.md` 更新 §三 基线与 §四 验收条件（把新的 `poll.py` / `health.py` 纳入闸门或明确不纳入）
- [ ] T056 [P] 跑全量回归：`check.sh` 必须仍然绿（不能因新代码破坏原闸门）
- [ ] T057 更新 `docs/DEVELOPMENT-HISTORY.md`（宪法 IV：做过什么归这个文件）

---

## Dependencies（用户故事完成顺序）

```
Phase 1 Setup (T001–T004)
      ↓
Phase 2 Foundational (T005–T013)   ← 阻塞全部
      ↓
   ┌──┴──────────────────────┐
   ↓                         ↓
Phase 3 US1 (T014–T028)   Phase 4 US2 (T029–T036)   ← US1/US2 可并行
   ↓                         ↓
   └──┬──────────────────────┘
      ↓
Phase 5 US3 (T037–T043)
      ↓
Phase 6 US4 (T044–T051)
      ↓
Phase 7 Polish (T052–T057)
```

**故事间依赖**：
- US2 依赖 Phase 2 的 `Channel.region`（T011），**不依赖 US1**
- US3 独立（只读数据），**可与 US1/US2 并行**
- US4 的 `health.py` 聚合 US1–US3 的产出，**依赖三者**

---

## Parallel Execution Examples

**US1 内部可并行**（不同文件）：
```
T016 边采边落盘  ‖  T017 落盘前去重  ‖  T018 故障隔离  ‖  T022 --timing
```

**测试可并行**：
```
T024 中断可续  ‖  T025 水位损坏  ‖  T026 故障隔离  ‖  T027 并发锁
```

**US1 与 US2 可并行**（不同文件、无依赖）：
```
（US1）T014–T022 poll.py      ‖      （US2）T029–T034 coverage.py
```

---

## Implementation Strategy

### MVP First（只做 US1）

1. 完成 Phase 1 + Phase 2（T001–T013）
2. 完成 Phase 3（US1，T014–T028）
3. **停下来验证**：跑 `verify-idempotent.py` + quickstart 场景 1 全部子场景
4. **此时已经达成用户唯一明说的目的** —— 可以交付

### Incremental Delivery

| 增量 | 内容 | 交付价值 |
|---|---|---|
| 1 | US1 | 「一个轮询拿到最新」—— 用户唯一明说的目的 |
| 2 | + US2 | 「知道还缺哪里、缺多少」 |
| 3 | + US3 | 「知道标签能不能信」 |
| 4 | + US4 | 「一条命令知道能不能用」 |
| 5 | + Polish | 可交接、可维护 |

### 关于测试的说明

本特性**不是 TDD** —— 测试任务排在实现之后（T023–T028 在 T014–T022 之后）。
理由：这些测试大多是**端到端行为验证**（幂等、中断续跑、并发锁），
需要先有可运行的 `poll.py` 才能测。**但测试必须写**，因为 12 条 SC 全靠它们证明。

---

## 汇总

- **总任务数**：57
- **按故事**：Setup 4 / Foundational 9 / US1 15 / US2 8 / US3 7 / US4 8 / Polish 6
- **并行机会**：US1 与 US2 可并行；US1 内部 4 项可并行；测试 4 项可并行
- **MVP 范围**：Phase 1+2+3（T001–T028，28 个任务）
- **格式校验**：全部任务符合 `- [ ] T### [P?] [US?] 描述 + 文件路径`
