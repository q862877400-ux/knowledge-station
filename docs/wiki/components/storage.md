# storage（存取与 schema）

**位置**：`src/core/storage/`
**一句话**：一切数据进出的唯一通道，并持有 schema。

## 职责

**把 sqlite 的读写包成仓储**，对上层屏蔽 SQL 细节；**持有并演进 `schema.sql`**
（38 张表对象：35 实体 + 3 虚拟表 `clause_fts` / `clause_vec` / `material_fts`）。

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
| `clause_revision` / `source_span` | 条款与其原文坐标（`source_span` 实测 1,589,271 行） |
| `clause_fts` / `clause_vec` / `material_fts` | 3 张虚拟表（全文 / 向量 / 材料全文） |
| `doc_meta` | 文档元数据；**`file_path` 指向磁盘上的证据 PDF**（见 `docs/README.md` §三） |
| `update_channel` | 渠道台账（实测 131 行） |
| `material` / `material_chunk` / `material_project` | 材料平面 |

## 改了它会影响谁

**几乎所有子系统**（改 schema 是全仓影响面最大的一类改动）。

**⇒ 硬规矩**：改 schema / API / SSE 前 MUST 先读
`docs/ENCYCLOPEDIA.md` §8/§10 与 **`pipeline/03-contract-delta.md`**（契约增量台账），
并在台账里追加一条（含 DDL / 影响面 / **回滚 SQL**）。

## 已知边界（诚实）

- ⚠ **`doc_meta.file_path` 指向仓库内的两份 PDF**（`wenjianmulu/`）。它们是**活数据，勿删**——
  删了证据链就断。
- **`sqlite-vec` 是暴力扫**（官方自述 brute-force only），随条数线性。**换索引已登记，未做。**
- **运行产物在 `%APPDATA%\KnowledgeStation\`**，与代码彻底分离。
