# Phase 1 · Contracts

> 本项**没有**对外 HTTP/SSE 接口变化。契约 = **存储契约**（表形状）+ **查询契约**（范围过滤的写法）。

---

## 契约 1 · 存储（`clause_vec` 形状）

**权威真源**：`src/core/storage/schema.sql`；契约增量记录在 `pipeline/03-contract-delta.md`；
机械断言在 `tests/test_contract.py`。

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS clause_vec USING vec0(
    clause_revision_id TEXT PRIMARY KEY,
    doc_id TEXT,
    embedding FLOAT[512]
);
```

**规则**：

- **R1**：`doc_id` **必须是元数据列**（普通列）。写成 `+doc_id`（aux）或去掉 `TEXT PRIMARY KEY` 都**不满足**本契约。
- **R2**：`doc_id` 的值**必须等于** `clause_revision.doc_id`（INV-1）。
- **R3**：**任何**往 `clause_vec` 写入的路径都必须提供 `doc_id`（入库 / 补丁重算 / 影子表）。
  缺了不会报错（列可空），但那条条款**会在范围提问里静默消失** —— 这是本契约最要紧的一条。
- **R4**：`embedding` 维度**不变**（512）。本项**不**升维。

---

## 契约 2 · 查询（范围过滤的**唯一**合法写法）

### 向量通道（`hybrid_engine` 通道 C）

```sql
SELECT clause_revision_id, distance FROM clause_vec
 WHERE doc_id IN (SELECT value FROM json_each(?))      -- ← 范围（唯一合法写法）
   AND embedding MATCH ? AND k = 20
 ORDER BY distance
```

**规则**：

- **Q1**：范围过滤**只许**用 `doc_id IN (SELECT value FROM json_each(?))`。
  **禁止**写成字面量列表 `doc_id IN (?, ?)` 或 `doc_id = ? OR doc_id = ?` ——
  实测这两种**会返回范围外的行**（比现状更糟：现状是"假报没有"，它们是"假报有"）。见 research.md R2。
- **Q2**：`doc_id` 为 `NULL` 的**存量行**（若迁移没跑完）在范围提问里**不出现**——
  这是**正确**的（那条不属于任何已知文档），但**迁移必须跑完**，否则是"静默漏"。
- **Q3**：**不指定范围**时（`doc_ids is None`）**不加任何范围条件**，行为与今天逐字相同。
- **Q4**：**空范围**（`doc_ids == []`）⇒ 在**进 SQL 之前**就返回 `[]`（既有逻辑，不改）。
- **Q5**：其余五条通道（exact / fts / modality / legal_element / behavior_scope）的写法**不动**
  （它们用 `clause_revision.doc_id` 关联，本来就下推）。

---

## 契约 3 · 迁移

**输入**：现有 `clause_vec`（663,634 行）
**输出**：同形新表，`doc_id` 全部回填，向量**逐字节不变**

**规则**：

- **M1**：**先备份**（全库副本 + 边级/行级备份），备份路径写进产物。
- **M2**：**纯 SQL 拷贝**（`INSERT … SELECT … JOIN clause_revision`），**不许重跑嵌入模型**。
- **M3**：**单事务**；失败即整体回滚。
- **M4**：自检三项——行数相同 / 向量逐字节相同 / `doc_id` 与 `clause_revision` 全表一致；**任一不过即失败**。
- **M5**：回滚 = 把备份改回名字（**可执行命令**，不是"理论上可以"）。
- **M6**：迁移脚本**幂等**（已迁移过再跑 = 空操作）。

---

## 契约 4 · 判据（不许放宽）

| 判据 | 位置 | 要求 |
|---|---|---|
| 向量通道被范围堵住 | `tests/test_kb_scope_retrieval.py::test_vec_channel_is_restricted_without_the_model` | **转绿**；**断言一个字不改**（含"必须有命中"与"不许混进范围外"） |
| 表形状 | `tests/test_contract.py`（新增用例） | `clause_vec` 有 `doc_id` 列且为普通列；`embedding` 仍 512 |
| 影子表同形 | `tests/test_embedding_rebuild_resume.py::test_shadow_dim_matches_production_schema` | 正则**同步新形状**，意图（维度 = 512）不变 |
| 范围写法不许退化 | 新增用例 | 把查询改回 `clause_revision_id IN (…)` ⇒ **必须红**（变异验证） |
