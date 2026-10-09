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

## R1 · 现状为什么坏 —— **已复现**

**Decision**：确认根因 = 范围约束**没能下推进最近邻查找**。

**证据**（探针 Q1）：表 `vec0(clause_revision_id TEXT PRIMARY KEY, embedding FLOAT[512])`，
范围内 5 条、范围外 25 条与查询向量**完全一致**的近邻：

```
WHERE embedding MATCH ? AND k = 20
  AND clause_revision_id IN (SELECT value FROM json_each(?))     → 0 行
```

**Rationale**：范围子查询返回 **5 个 id** ⇒ 下推不发生 ⇒ 退化成"先 KNN 再筛" ⇒ 全局 top-20 全是范围外 ⇒ 筛完为空。
第 17 轮的读数（1 个 id 成功 / ≥2 个 id 返回 `[]`）**复现成功**。

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
