# Implementation Plan: 法规目录补齐与定时刷新 + 历次版本链

**Feature Branch**: `006-law-catalog-refresh`

**Spec**: [spec.md](./spec.md)

**Created**: 2026-10-10

---

## 摘要

三件事，按 spec 的优先级：

1. **P1（MVP）**：修 `law_catalog` 的**存量时效漂移（1,130 条）+ 补新增（1,187 条）**，
   并把刷新接入既有巡检调度器，使其**自动周期执行**。
2. **P2**：接 flk 详情接口的 `lsyg`（历史沿革），提供**历次版本链**查询 + HTTP 端点。
3. **P3**：把 std-law-watch 的四条接口事实与一条**结论冲突**并入 KS 归属文档。

**关键约束**：不改 `NOT-DOING.md` #20；不并入 std-law-watch 的 64 站注册表；
所有网络请求经 `law_source/http.py` 白名单出口。

---

## 技术上下文

| 项 | 值 | 出处 |
|---|---|---|
| 语言/运行时 | Python 3.12 + FastAPI（`src/core/`） | `pyproject.toml` |
| 存储 | SQLite（`%APPDATA%\KnowledgeStation\database\knowledge.db`） | `src/core/storage/sqlite_db.py` |
| 既有客户端 | `src/core/knowledge/law_source/flk_client.py`（`search`/`detail`/`enum_data`/`download`） | 实测 `search` 返回 `code=200 total=30910` |
| 既有目录器 | `src/core/knowledge/law_source/catalog.py`（`refresh_catalog` 已实现分片+账本+幂等 upsert） | 代码审读 |
| 既有调度器 | `src/core/update/scheduler.py`（`UpdateScheduler.tick()`，2 秒轮询，可注入假时钟） | 代码审读 |
| 既有配置面 | `inspector.get_config` / `set_config`（`app_config` 表） | `src/core/update/inspector.py` |
| HTTP 出口 | `src/core/knowledge/law_source/http.py`（域白名单 5 个官方域 + 限速 + 重试 + 魔数校验） | 代码审读 |
| 测试 | pytest，`testpaths=["tests"]`；门禁 `scripts/run-gates.ps1` | `pyproject.toml` |

---

## 现状核查（写方案前逐条实测，不采信 std-law-watch 的文档结论）

| 断言 | 实测结果 | 处置 |
|---|---|---|
| `refresh_catalog` 分片覆盖完整？ | 28 个叶子分类 `total` 之和 = **30,909**；空条件 = **30,910**，差 1 | ✅ 分片策略**不改** |
| 缺失是"抓不到"还是"没跑"？ | `updated_at` 全为 **2026-08-25**；`law_manifest` 28 分类全 `done=true`；`update/` 里 `refresh_catalog` 命中 **0 行** | ✅ 是**没跑**，补机制即可 |
| KS 现有 `sxx` 是否可信？ | **1,130 条与官方不一致**（864 有效→已修改、147 有效→已废止、60 已修改→已废止…） | ⚠ **新增 FR-001a**，刷新须修状态 |
| `lsyg` 在 KS 有实现吗？ | `git grep lsyg -- src` = **0 行**（仅 `channel_seed.json` 一句备注） | ✅ US2 是真空白 |
| `highSearch` 在 KS 有吗？ | `git grep highSearch` = **0 行** | ✅ US3 是真空白 |
| 官方接口今天可用吗？ | `flk_client.search("")` → `code=200 total=30910` | ✅ 可用，方案不依赖预热 workaround |

**⚠ 一处必须记住的既有事实**：`catalog.py` 的增量判据已经是
「`prev.title == title and prev.sxx == sxx` 才跳过」（见该文件 `refresh_catalog` 内 `prev` 分支）
⇒ **FR-001a 不需要改判据逻辑，只需让它真的跑起来**。这是本方案能"低风险"的关键。

---

## 架构决策

### D1：复用 `refresh_catalog`，不新写刷新器

`refresh_catalog` 已具备：分类级断点续传（`cat_state[code]`）、
幂等 upsert（`ON CONFLICT(bbbs) DO UPDATE`）、
`title`/`sxx` 变化才写库的增量判据、翻页保险丝、账本落盘。
**缺的只有"被自动调用"**。

⇒ 新增代码量最小、风险最低。**不引入 std-law-watch 的 `flk_index.py`**
（它是"扁平 CSV 索引"形态，与本仓"SQLite 目录表"形态不同，并入等于两套真值）。

### D2：法规刷新**自建轻量后台线程**，接入 `run()` 启动点（⚠ 就地更正，见下）

**⚠ 原方案作废（2026-10-10 实测推翻）**：原 D2 写的是"在 `UpdateScheduler.tick()` 内
新增第三条动作"。实测发现 **`UpdateScheduler` 在生产里从未被启动过**：

- `tick()` 只被 `_run()` 调用（`scheduler.py:104`）；
- `_run()` 只被 `start()` 调用（`scheduler.py:88`）；
- **`start()` 全仓无人调用**——`git grep UpdateScheduler` 在 `src/` 只命中
  `scheduler.py` 自身与 `update/__init__.py` 的 re-export；
  其余命中全在 `tests/test_update_inspector.py`。

⇒ 若按原方案接进 `tick()`，**刷新永远不会跑**，等于又一个假绿。
这正是本仓纪律「**工具正常返回 ≠ 工具是对的**」的又一个实例
（调度器代码看着完整、测试全绿，但生产路径上没人拉它）。

**更正后的方案**：法规刷新用**自己的 daemon 线程**，在
`src/core/api/server.py` 的 `run()` 里启动——照抄既有先例
`write_queue_bootstrap.start_write_worker()`（`server.py:3292-3296`，
同样是"引擎启动时拉一个后台循环"，且失败不阻塞启动）。

**为什么不去修那个死调度器**：`UpdateScheduler` 的职责是**创建巡检批次**
（`create_inspect_batch`），一旦启动就会每 7 天自动建批、**进日预算池**——
那是业主没要求的**行为变更**，且与法规目录刷新无关。
按本仓纪律「跨轮次的额外发现只登记，不在当轮顺手实施」，
**本轮只登记、不修**（登记见 `research.md` R5）。

**为什么不做成"懒加载"**（查询目录时顺手刷新）：首次刷新需约 12 分钟，
会把一次普通查询阻塞 12 分钟——不可接受。

### D3：法规刷新**不进** `bulk_import_batch`，用 `app_config` 记上次时间

理由（更正后仍成立）：`bulk_import_batch` 的语义是"标准号巡检批"
（有 tier、有预算、有暂停原因），法规刷新没有这些属性。
硬塞进去会污染该表统计口径。

⇒ 用 `app_config` 键 `law.catalog_last_refresh_at` 记时间，
与 `inspect.budget_date` 的既有做法同构。

### D4：版本链用**按需查询**，不做全量预抓

`lsyg` 只在**详情接口**返回。全量预抓 3 万条详情 = 3 万次请求（按 0.6 秒限速 ≈ **5 小时**），
且绝大多数法规不会被打开。

⇒ 提供**按 `bbbs` 查询**的端点，调用时才请求；结果可短时缓存（见 D5）。

### D5：版本链**不落库**（本特性范围内）

落库需要新表 + 迁移 + 失效策略，而 `lsyg` 是**低频读取**（用户点开某部法规时）。
在 P2 先做**透传查询**（与既有 `/api/v1/laws/verify` 同构——它也是透传 `verify_law`）。
若后续需要缓存，另立 spec。

**留痕**：这是有意的范围收窄，不是遗漏。spec 的 SC-004/005 只要求"能查到、错误可辨"。

---

## 实施阶段

### 阶段 0：基线取证（不改代码）

- 记录刷新前：`law_catalog` 行数、时效不一致条数、2026-08 条数。
- 产出机器可读基线（供 SC-001/001a 对照）。
- **交付**：`specs/006-law-catalog-refresh/baseline.json`。

### 阶段 1：刷新可自动触发（P1，MVP）

| 步骤 | 内容 | 文件 |
|---|---|---|
| 1.1 | `catalog.py` 增加 `refresh_catalog_if_due()`：读配置周期 + 上次时间，到期才跑 | `src/core/knowledge/law_source/catalog.py` |
| 1.2 | **新建** `law_refresh.py`：后台 daemon 线程（start/stop），轮询到期触发 | `src/core/knowledge/law_source/law_refresh.py`（新） |
| 1.3 | `server.py` 的 `run()` 里启动该线程（照抄 `start_write_worker` 先例） | `src/core/api/server.py` |
| 1.4 | 配置键常量 + 缺省值（`law.catalog_refresh_days` = 1） | 同上 |
| 1.5 | 单元测试：到期触发 / 未到期不触发 / 关闭（≤0）不触发 / 线程生命周期 | `tests/test_law_catalog_refresh.py` |

**验收**：SC-002（幂等）、SC-003（自动触发）。

### 阶段 2：跑一次真实全量刷新（P1 收口）

- 对**真库**跑一次 `refresh_catalog()`，量 SC-001 / SC-001a。
- **风险控制**：真库有备份机制（`%APPDATA%\KnowledgeStation\backups\`）；
  刷新只做 upsert，不删行。
- **诚实边界**：这一步耗时约 12 分钟（1,187 条新增 + 3 万条比对，0.6 秒限速），
  且**依赖外网**。若官方不可达，本阶段**明确标未做**，不伪造读数。

**验收**：SC-001（≥30,900 且 2026-08 ≥600）、SC-001a（不一致 = 0）。

### 阶段 3：版本链（P2）

| 步骤 | 内容 | 文件 |
|---|---|---|
| 3.1 | `flk_client.py` 增加 `history(bbbs)`：解析 `lsyg` → 版本列表 | `src/core/knowledge/law_source/flk_client.py` |
| 3.2 | `FlkDetail` 暴露 `lsyg`（或新增轻量函数） | 同上 |
| 3.3 | HTTP 端点 `GET /api/v1/laws/history?bbbs=` | `src/core/api/routes_law.py` |
| 3.4 | 单元测试：多版本降序 / 无 `lsyg` 返空 / 网络失败返错误 | `tests/test_law_source.py` |

**验收**：SC-004、SC-005。

### 阶段 4：知识并入（P3）

| 步骤 | 内容 | 文件 |
|---|---|---|
| 4.1 | 四条接口事实（`highSearch` / 30,000 墙 / `codeId≠id` / `xgzl` 文号）+ 出处 | `docs/LAW-SOURCE-PLAN.md` |
| 4.2 | `download/pc` **结论冲突**并列记录 + 标"未实测仲裁" | `docs/ENCYCLOPEDIA.md` + `docs/LAW-SOURCE-PLAN.md` |
| 4.3 | std-law-watch 目录的处置口径（保留只读、只并知识不并代码） | `docs/LAW-SOURCE-PLAN.md` |

**验收**：SC-007（可 `grep`）。

### 阶段 5：门禁与收工

- `pwsh -File scripts/run-gates.ps1 -Quick` → exit 0。
- 小提交 + 快照（`scripts/snapshot-project.ps1 -Label law-catalog-refresh`）。
- 更新 `docs/DEVELOPMENT-HISTORY.md`（做过什么）与 spec 的收口记录。

**验收**：SC-006。

---

## 风险与对策

| 风险 | 概率 | 对策 |
|---|---|---|
| 官方接口改版导致刷新失败 | 低 | 已有 `RuntimeError`（enum 解析失败）+ 分类级 warning 继续；失败明确报错不静默 |
| 全量刷新耗时超预期 | 中 | 分类级断点续传，可中断重跑；账本保证不重复劳动 |
| 刷新把真库写坏 | 低 | 只 upsert 不删；跑前已有 backups；幂等可重跑 |
| 时效"修正"其实是官方口径不同 | **已排除** | 抽样 16/16 一致（见 `research.md` R2） |
| 后台线程影响引擎启动 | 低 | 照抄 `start_write_worker` 先例：`try/except` 包住，失败不阻塞启动 |
| 后台线程在测试里泄漏 | 中 | 提供 `stop()`；测试用 `try/finally` 关停；daemon 线程不阻进程退出 |
| 刷新与用户查询并发写库 | 低 | `write_transaction()` 短事务 + 幂等 upsert；SQLite WAL 既有并发语义 |
| ⚠ `UpdateScheduler` 是死代码 | **已确认** | 本轮**只登记不修**（见 `research.md` R5）；不顺手改，避免行为变更 |

---

## 待澄清（提交业主前先自问）

1. 刷新周期缺省 1 天是否合适？——**取 1 天**：法规发布频率约每天几十条，
   且时效漂移需要快收敛；请求量小（每天约 3 万条比对 ≈ 300 页，0.6 秒限速 ≈ 3 分钟）。
2. 是否要 UI？——**本特性不做 UI**。既有 `/api/v1/laws/catalog` 已能查；
   版本链端点先给 API，UI 另立。
3. std-law-watch 目录删不删？——**不删**，保留只读（含 `_diag/` 原始证据）。
