# storage（存取与 schema）

**位置**：`src/core/storage/`
**一句话**：一切数据进出的唯一通道，并持有 schema。

## 职责

**把 sqlite 的读写包成仓储**，对上层屏蔽 SQL 细节；**持有并演进 `schema.sql`**
（**44 张表对象**：`schema.sql` 里 `CREATE TABLE` 44 条，其中 3 张虚拟表 `clause_fts` / `clause_vec` / `material_fts`。
2026-10-23 实测；旧文「38 张」已过期。库内 `sqlite_master` 实际 62 张，差额是 FTS/vec 的影子表）。

**它不负责**：数据从哪来（`ingestion` / `update`）、怎么检索（`retrieval`）、怎么用（`api`）。

## 对外提供什么

| 提供物 | 形式 | 调用方 |
|---|---|---|
| 条款仓储 | `clause_repo.py`（44.2 KB，最大） | `api` / `retrieval` / `compliance` |
| 渠道台账仓储 | `channel_repo.py`（`update_channel`） | `api` / `update` |
| 材料仓储 | `material_repo.py` | `api` / `materials` |
| 连接与 schema | `sqlite_db.py` | 全部 |
| 用户数据 | `user_data.py` | 界面与设置 |
| 批量级联删除 | `doc_delete.py` | 界面（用户验收批量删除后接线） |
| 快照备份与回滚 | `backup.py` | 运维 |
| 版本化 | `versioning.py` | 数据演进 |
| 写队列 | `write_queue.py` + `write_queue_bootstrap.py` | 并发写 |
| 影响面分析 | `impact.py` | 改数据前的评估 |
| 调试转储保留 | `debug_dump_retention.py` | **唯一所有者**：两类记录**各自清理**，互不挤占 |

## 依赖什么

| 依赖 | 类型 | 用途 |
|---|---|---|
| sqlite + `sqlite-vec` | 外部 | 存储与向量索引 |
| `schema.sql` | 仓内文件 | 表定义 |

## 明确不做什么

- **不做检索排序**：只按调用方给的条件取数；"谁排前面"是 `retrieval` 的事。
- **不做解析**：PDF/Office 解析在 `ingestion`。
- **不做业务规则**：合规判断在 `compliance`。
- **`debug_dump_retention` 不许被别的模块代劳**——它是该策略的**唯一所有者**
  （否则两类记录互相挤占，本仓已有过一次该形态的问题）。

## 关键数据

| 表/对象 | 说明 |
|---|---|
| `clause_revision` / `source_span` | 条款与其原文坐标（`source_span` 实测 **1,842,493** 行（2026-10-23；旧文 1,589,271 已过期）） |
| `clause_fts` / `clause_vec` / `material_fts` | 3 张虚拟表（全文 / 向量 / 材料全文） |
| `doc_meta` | 文档元数据；**`file_path` 指向磁盘上的证据 PDF**（见 `docs/README.md` §三） |
| `update_channel` | 渠道台账（实测 131 行） |
| `material` / `material_chunk` / `material_project` | 材料平面 |

## 改了它会影响谁

**几乎所有子系统**（改 schema 是全仓影响面最大的一类改动）。

**⇒ 硬规矩**：改 schema / API / SSE 前 MUST 先读
`docs/ENCYCLOPEDIA.md` §8/§10 与 **`pipeline/03-contract-delta.md`**（契约增量台账），
并在台账里追加一条（含 DDL / 影响面 / **回滚 SQL**）。


## 规模与覆盖（2026-10-23 实测）

| 项 | 数字 |
|---|---|
| 文件数 | **13** 个 `.py` |
| 行数 | **3,198** |
| 提到本子系统的测试文件 | **88** 个 |

**被最多测试提到**；入度最高（被引 120 行）

> 数字口径：`rglob("*.py")` 排除 `__pycache__`；测试覆盖 = 在 `tests/*.py` 里出现过 `src.core.<本子系统>` 的文件数（**只是「提到」，不等于「被测」**）。

## 已知边界（诚实）

- ⚠ **`doc_meta.file_path` 指向仓库内的两份 PDF**（`wenjianmulu/`）。它们是**活数据，勿删**——
  删了证据链就断。
- **`sqlite-vec` 是暴力扫**（官方自述 brute-force only），随条数线性。**换索引已登记，未做。**
- **运行产物在包内 `var/data/`**，与代码在同一个包里（便携化要求：换台机器知识库跟着走），
  但**不受版本控制**。
  **⚠ 旧文写的是 `%APPDATA%\KnowledgeStation\`，那个目录已于 2026-10-17 便携化后不存在**
  （实测 `Test-Path` 为假；`get_settings().data_dir` 现返回 `<仓根>/var/data`）。
  ⇒ **新克隆的仓是空库**。
  **2026-10-23 已补种子库**（见下），所以"能否开发与回归"不再被这件事卡住。
- **生产库实测规模**（2026-10-23）：`knowledge.db` 目录 13.82 GB / 单文件 2.90 GB，
  8,983 部标准 / 663,634 条条款 / 1,842,493 条位置片段。

## 种子库（随仓提交的测试语料）

| 项 | 值 |
|---|---|
| 位置 | `tests/fixtures/seed/knowledge-seed.db` |
| 体积 | **13.3 MB** |
| 内容 | **82 部标准 / 4,809 条条款 / 16,198 条位置片段 / 1,127 个目录 / FTS 4,809 行** |
| 生成 | `python scripts/make-seed-db.py --docs 60`（需本机有完整 `var/data`） |
| 使用 | pytest fixture `seed_data_dir`（`tests/conftest.py`） |
| 护栏 | `tests/test_seed_db_guard.py`（6 条）+ `tests/test_real_corpus_retrieval.py`（7 条） |

**为什么要有它**：`var/data` 进不了版本控制 ⇒ 在这之前，
「在真库上验证」在门禁里**结构上做不到**（实测 3,076 条用例跑在真库上的是 0 条）。
这正是 `resolve_clause` 跨标准误命中（wiki §四 #2）能活到今天的原因 ——
那条 SQL 在空库上永远返回 `None`，走不到误命中分支。

**挑样本的判据不是"随便抽"**：`scripts/make-seed-db.py` 的 `MUST_INCLUDE` 钉了
9 部受害标准 + 3 部被误命中的别家标准 + 2 部年份宽容正向样本。
**少一部，那条缺陷就复现不了。**

**它不解决什么**：82 部 ≠ 8,983 部。六路检索的**召回率与排序质量**、
`parse_out` 里的图片与公式、材料平面、巡检台账，仍只有完整库能验。

**⚠ 用它写测试时必踩的坑**：`get_db_connection()` 是**按线程缓存**的。
切 `KS_DATA_DIR` 前不 `close_thread_connection()`，会拿到前一个用例的旧连接
⇒ 读到空库。症状是**单跑绿、全跑红**（已实测）。
