# Implementation Plan: 按目录范围提问时，向量通道要真的在范围内找

**Branch**: `003-vec-scope-pushdown` | **Date**: 2026-10-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-vec-scope-pushdown/spec.md`

## Summary

**问题**：`clause_vec` 的范围过滤写成 `clause_revision_id IN (子查询)`，而 `clause_revision_id` 是
`vec0` 的 **TEXT PRIMARY KEY** —— sqlite-vec **不拿它做 KNN 前置过滤**：**只要范围子查询返回的 id 里
有一个在向量表里没有对应行，整体就返回 `[]`**（全都有向量才正常；**与 id 个数、表大小都无关**）
⇒ 「按目录范围提问」在向量通道上**假报"范围内没有"**。
⚠ **初版这里写的是"≥2 个 id 恒返回 `[]`"—— 那句【已作废】**（依据的探针喂的是文档 id 不是条款 id），
更正依据见 [research.md](research.md) R1-更正。

**修法**：给 `vec0` 加一个**元数据列** `doc_id TEXT`，范围过滤改走
`doc_id IN (SELECT value FROM json_each(?))` —— **本轮实测这是唯一能下推的写法**（见 [research.md](research.md) R2）。

**迁移**：已有 663,634 行**纯 SQL 拷贝**（不重跑嵌入模型，逐字节一致，分钟级）。

**为什么现在做**：第 17 轮第一次把 `-Full` 跑通后，`tests/test_kb_scope_retrieval.py::test_vec_channel_is_restricted_without_the_model`
现形。它是**用户可见的功能缺陷**，且**判据不许放宽**。

## Technical Context

**Language/Version**: Python 3.13（引擎）｜项目内 `.venv/Scripts/python.exe`

**Primary Dependencies**: `sqlite-vec 0.1.9`（`vec0` 虚拟表）｜SQLite **3.53.1**｜裸 `sqlite3`（无 ORM）

**Storage**: `%APPDATA%\KnowledgeStation\database\knowledge.db`（3.1 GB；**核对一律 `mode=ro`**）；
`clause_vec` = `clause_revision` = **663,634 行**

**Testing**: `pytest`；本仓门禁 `pwsh -File scripts/run-gates.ps1 -Quick|-Full`

**Target Platform**: Windows（本机）＋ 仓外 DSH 插件

**Project Type**: 单仓（Python 引擎 `src/core/` + Node 插件 `plugin/`）

**Performance Goals**: 单次范围提问**不劣化**（实测 0.96 → 0.97 ms/次 KNN，同量级）

**Constraints**: ① **零回归**（不加范围的主路径逐条不变）；② **向量一条不许变**（迁移是搬运）；
③ **判据一个字不许放宽**；④ 迁移要**可回滚**且**先备份**；⑤ 属**必验类别**（改 schema + 动生产数据）

**Scale/Scope**: 真库 663,634 行向量；范围常见几十~上百篇文档

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| 原则 | 本项如何满足 |
|---|---|
| **I 说人话** | 已产出 [`读我-大白话版.md`](读我-大白话版.md)（无表名/接口名，只说"点下去会怎样、代价是什么、能不能退回"） |
| **II 从事实出发** | 修法是**实测**出来的（`probes/`），且**否掉了三个"看着像"的写法**；没有迎合"加个索引就行"的直觉 |
| **III 证据优于断言** | 每条结论都挂探针读数；**未做的写明"未做"**（partition key 未采用、未测其代价） |
| **IV 一个事实一个归属层** | 结论 → `docs/DEVELOPMENT-HISTORY.md`；存储契约 → `pipeline/03-contract-delta.md`；本目录只留方案与证据 |
| **V 留痕不许悄悄删** | 第 17 轮那句错话（"子查询 = 带约束的 KNN"）**保留原文 + 就地更正**，见用例 docstring 与 research.md R1 |
| **VI 先查现成的** | 先查了 `sqlite-vec` 自身的**元数据列**能力（文档化特性），没有自造索引/分区方案 |
| **VII 对已否决台账** | 已对 `docs/NOT-DOING.md`：本项**不是**"改排序键"（0.4b）、**不是**"列先验"（E9 已堵死），是新缺陷 |

**Gate 结论：通过**（无违规需豁免）。**Phase 1 后复核：仍通过**（设计未引入新表、新依赖、新接口）。

## Project Structure

### Documentation (this feature)

```text
specs/003-vec-scope-pushdown/
├── spec.md              # 需求（做什么、为什么）
├── 读我-大白话版.md      # 给业主看的一句话版
├── plan.md              # 本文件
├── research.md          # Phase 0：修法为什么成立（实测）
├── data-model.md        # Phase 1：表形状与不变式
├── contracts/           # Phase 1：存储契约 + 查询契约 + 迁移契约
├── quickstart.md        # Phase 1：怎么验（可跑的判据）
├── checklists/          # 需求质量检查单
├── probes/              # 可复跑探针（修法证据）
└── tasks.md             # Phase 2（/speckit-tasks 产出）
```

### Source Code (repository root)

```text
src/core/storage/
├── schema.sql                     # ← 改：clause_vec 加 doc_id TEXT
├── clause_repo.py                 # ← 改：两处 INSERT 带 doc_id
└── sqlite_db.py                   #   不改（executescript 全量执行；虚拟表无 ALTER）

src/core/retrieval/
└── hybrid_engine.py               # ← 改：向量通道范围过滤走 doc_id

pipeline/03-contract-delta.md      # ← 改（红线：先契约后实现）
tests/test_contract.py             # ← 改（同上）
tests/test_kb_scope_retrieval.py   # ← 只改 fixture（塞向量带 doc_id），断言一字不改
tests/test_embedding_rebuild_resume.py  # ← 改：正则同步新 DDL 形状

eval/recall-funnel/exp-17-embedding-production-plan/
└── rebuild-shadow.py              # ← 改：影子表保持"与生产同形"

scripts/
└── migrate-clause-vec-doc-id.py   # ← 新：迁移（纯 SQL 拷贝 + 备份 + 回滚步骤）
```

**Structure Decision**：**单项目结构**（本仓既有形状）。改动面 = **1 张虚拟表的 DDL + 4 个源文件/测试 + 1 个迁移脚本 + 2 份契约文档**，
**不新增目录、不新增依赖、不改 API/SSE/通道枚举**。

## Phase 0 → Phase 1 产物

- **Phase 0**：[research.md](research.md) —— 修法成立性 + 三个反例 + 边界四条 + 连带影响九项
- **Phase 1**：[data-model.md](data-model.md)（表形状与不变式）｜[contracts/](contracts/)（存储 + 查询 + 迁移契约）｜[quickstart.md](quickstart.md)（怎么验）

## Complexity Tracking

> 无宪法违规需豁免。

| 项 | 说明 |
|---|---|
| 为什么**必须**动 schema | `sqlite-vec` 的过滤只认**元数据列**；`TEXT PRIMARY KEY` 推不下去（实测）。**没有不改表的等价修法**。 |
| 为什么**不**重算向量 | 实测纯拷贝**逐字节一致** ⇒ 重算只会引入风险，不带来收益。 |
| 为什么**不**顺手做 exp-17 接生产 | 那是**另一条线**（换模型 + 指令前缀），行为改动、独立必验；本项**只修范围下推**。 |
