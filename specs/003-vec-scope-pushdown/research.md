# Phase 0 · Research

> 本文件回答"**修法成立吗**"。所有结论都来自**本轮实测**（`probes/` 两个可复跑脚本），不是推断。

## 环境

| 项 | 值 |
|---|---|
| `sqlite-vec` | **0.1.9** |
| SQLite | **3.53.1** |
| 探针 | `probes/probe-vec-scope-fix.py` / `probes/probe-vec-scope-fix2.py`（纯内存库，**不碰真库**） |
| 复跑 | `.venv/Scripts/python.exe specs/003-vec-scope-pushdown/probes/probe-vec-scope-fix.py` |

---

## R1 · 现状为什么坏 —— ⚠⚠ **本节初版写错了，2026-10-09 就地更正（留痕）**

### R1-更正① · 先认错：初版那句"**已复现**"站不住

初版依据是探针 `probe-vec-scope-fix.py` 的 **Q1**。**那个 Q1 写错了**：
它查的是 `clause_revision_id IN (SELECT value FROM json_each(?))`，
而喂进去的是**文档 id**（`["in_doc"]`）**不是条款 id** ⇒ 那是个**无意义的查询**，
它返回 0 行**不能**当作"复现"。**该结论作废。**

### R1-更正② · 真正的失效条件（判决性实验）

`probe-scale-flip2.py`（**直接 SQL 跑两种写法** —— 不是经 `perform_hybrid_search`，
因为那已经是新代码，会把自己标成"旧写法"）：

| 范围外近邻 N | 范围内**有向量**的条款数 `m` | 旧写法 `clause_revision_id IN (子查询)` | 新写法 `doc_id IN (json_each)` |
|---|---|---|---|
| 25 / 200 / 2,000 / 20,000 / 100,000 | **1** | ❌ **返回空** | ✅ 返回范围内那条 |
| 25 / 200 / 2,000 / 20,000 / 100,000 | **5** | ✅ 正常 | ✅ 正常 |

⇒ **失效条件既不是"范围里有几个 id"、也不是表的大小**，而是：
**范围子查询返回的 id 里，只有【一部分】在向量表里真的有向量。**
`m` == 范围条款数 ⇒ 旧写法正常；`m` 小于范围条款数 ⇒ **返回空**。

### R1-更正③ · 真库现状（**必须如实说，这条推翻了"用户可见故障"的说法**）

**真库上这个条件【目前不成立】**（2026-10-09 实测）：

- `clause_vec` = `clause_revision` = **663,634** 行；
- **"有条款但没有向量"的文档 = 0 篇**（全表 `LEFT JOIN` 计数，不是抽样）；
- 拿**1 / 2 / 3 / 5 / 10 / 50 条条款**的文档逐一当范围 ⇒ 旧写法**都返回范围内、零越界**。

⇒ **旧写法在今天的真库上工作正常。** 本项**不是"当前正在发生的用户可见故障"**，
而是**一个潜在脆弱点**：只要某个目录里出现**有条款却没有向量**的文档，
向量通道就会**静默返回空**（假报"范围内没有"）。

**这条路径是可达的**（所以值得修）：

1. **入库时嵌入模型不可用** —— `insert_clauses_in_txn` 的 `vec_ok = False` 会**跳过向量写入**
   （设计如此，R30 精神）⇒ 那批条款没有向量；
2. **部分重建**（`exp-17` 的影子表只跑一部分就换表）；
3. 删向量后未回填。

**修它的理由**：① 现状靠"所有条款都有向量"这个**偶然事实**在撑，**没有判据守着**；
② 一旦破坏，症状是**静默的**（用户看到的是"这里没有"）；③ 单测（夹具 5 条只有 1 条有向量）
**就是红的** —— 它在守的正是这个性质，且第 17 轮的 `-Full` junit 里它是**权威红**。

**Alternatives considered**：无（这是要修的对象）。

---

## R2 · 修法 —— **给 `vec0` 加元数据列 `doc_id`**

**Decision**：把表改成 `vec0(clause_revision_id TEXT PRIMARY KEY, doc_id TEXT, embedding FLOAT[512])`，
范围过滤改成 **`doc_id IN (SELECT value FROM json_each(?))`**。

**证据**（探针 Q2a）：同一组数据，新表 ⇒ **返回 1 行 `['in_weak']`**（范围内那条，且它是**全局最远**的那条）。
⇒ **真的下推了**。

**Rationale**：`sqlite-vec` 的**元数据列**（普通列，非 `PRIMARY KEY`）**参与 KNN 前置过滤**；
而 `TEXT PRIMARY KEY` 那一列**不参与**。所以"在 `clause_revision_id` 上加约束"永远推不下去，
"在 `doc_id` 上加约束"可以。

**Alternatives considered**：

| 备选 | 结论 | 证据 |
|---|---|---|
| 维持现状 + 只改文档说明 | ❌ 功能仍是坏的 | R1 |
| 用 `clause_revision_id` 加约束（现状写法） | ❌ 不下推 | Q1 |
| **`doc_id` 字面量列表 `IN (?, ?)`** | ❌ **混进范围外 20 行** | Q2b |
| **`doc_id = ? OR doc_id = ?`** | ❌ **混进范围外 20 行** | Q2d |
| `rowid IN (…)` | ❌ **`no such column: rowid`** | Q3 |
| partition key | 未采用（元数据列已够；分区会把 8,983 篇文档切成 8,983 个分区，未验其查询代价） | Q4 未跑通 |
| 后置筛（KNN 后按 `doc_id` 过滤） | ❌ 要把 `k` 开到全表 | R1 的机制 |

> ⚠ **这一格是本项最重要的一条**：**看着像的写法（字面量列表 / OR）比现状更糟** ——
> 现状返回空（"假报没有"），它们**返回范围外的东西**（"假报有"）。
> 所以范围过滤**只许用 `json_each` 子查询这一种写法**，并**必须有判据钉住**。

---

## R3 · 边界 —— 全验通

| 问 | 读数 | 结论 |
|---|---|---|
| **Q5** 范围 = 100 篇文档 | 返回 `['in_weak']` | ✅ **范围大小不设上限** |
| **Q6** 不加范围（历史路径） | 旧表 / 新表 top-20 **逐条相同** | ✅ **零回归** |
| **Q8** 范围指向的文档没有向量 | 0 行、**不报错** | ✅ 空结果不是错误 |
| **Q9** 元数据列对无范围 KNN 的代价 | 0.96 ms/次 → **0.97 ms/次** | ✅ **无劣化** |

---

## R4 · 迁移 —— **不用重算向量**

**Decision**：迁移 = **纯 SQL 拷贝**（`INSERT … SELECT clause_revision_id, doc_id, embedding`），**不重跑嵌入模型**。

**证据**（探针 Q7）：拷贝 30 行，**逐字节不同的 = 0**。

**Rationale**：`doc_id` 从 `clause_revision.doc_id` 关联取得（库里已有），向量原样搬运。
⇒ 迁移是**分钟级**，且**逐字节可核**（不必承担 fp16 批不变性那 8.4e-4 的浮点风险）。

**Alternatives considered**：重跑嵌入模型（`exp-17/rebuild-shadow.py` 那条路）——
❌ 要 ~1 小时、引入新的浮点变量、且**没有必要**（向量没变）。

---

## R5 · 连带影响（**改动面清单**）

| # | 位置 | 为什么必须动 |
|---|---|---|
| 1 | `src/core/storage/schema.sql` | `clause_vec` DDL 加 `doc_id TEXT` |
| 2 | `src/core/storage/clause_repo.py:332` | 入库写向量时要带 `doc_id`（**否则新条款静默查不到**） |
| 3 | `src/core/storage/clause_repo.py:428` | 补丁重算向量时同样要带 `doc_id` |
| 4 | `src/core/retrieval/hybrid_engine.py:216/312` | 向量通道范围过滤改走 `doc_id` |
| 5 | `pipeline/03-contract-delta.md` + `tests/test_contract.py` | **本仓红线：改 schema 先改契约** |
| 6 | `tests/test_embedding_rebuild_resume.py::test_shadow_dim_matches_production_schema` | ⚠ **它的正则钉死了 DDL 形状**（`…PRIMARY KEY,\s*embedding FLOAT\[512\]`）⇒ 加列会让它红，**必须同步改** |
| 7 | `eval/recall-funnel/exp-17-…/rebuild-shadow.py` | 影子表自称"与生产同形" ⇒ 生产加了列，影子表也要加（否则将来换表范围提问照样坏） |
| 8 | 迁移脚本（新） | 把已有 663,634 行搬到新表 |
| 9 | `tests/test_kb_scope_retrieval.py` | ⚠ **判据一个字不改**（FR-010）；只改它自己的 fixture（塞向量时要带 `doc_id`） |

⚠ **不改**：`doc_delete.py`（按 `clause_revision_id` 删，不涉及 `doc_id`）；
`tests/test_doc_batch_delete.py`（同上，插向量那两行要补 `doc_id`，属测试适配）。
