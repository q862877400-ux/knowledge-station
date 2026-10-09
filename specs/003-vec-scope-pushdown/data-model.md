# Phase 1 · Data Model

> 只涉及**一张虚拟表**。不新增实体、不改任何关系。

## 实体：条款向量（`clause_vec`）

| 列 | 类型 | 约束 | 语义 |
|---|---|---|---|
| `clause_revision_id` | TEXT | **PRIMARY KEY** | 条款修订 id（ULID 前缀 `clrev_`）；与 `clause_revision` 一一对应 |
| **`doc_id`** | TEXT | 新增（**元数据列**） | **所属文档 id**；= `clause_revision.doc_id`。**范围提问就靠它过滤** |
| `embedding` | FLOAT[512] | — | 512 维向量（bge-small-zh-v1.5） |

### 变更前后

```sql
-- 变更前
CREATE VIRTUAL TABLE IF NOT EXISTS clause_vec USING vec0(
    clause_revision_id TEXT PRIMARY KEY,
    embedding FLOAT[512]
);

-- 变更后
CREATE VIRTUAL TABLE IF NOT EXISTS clause_vec USING vec0(
    clause_revision_id TEXT PRIMARY KEY,
    doc_id TEXT,                       -- 元数据列：参与 KNN 前置过滤
    embedding FLOAT[512]
);
```

### 为什么 `doc_id` 必须是**元数据列**而不是 `+doc_id`（aux）或 PRIMARY KEY

`sqlite-vec 0.1.9` 实测：**只有元数据列**参与 KNN 前置过滤。
`clause_revision_id TEXT PRIMARY KEY` 上做 `IN (子查询)` **不下推**（≥2 个 id 返回 `[]`）——
这正是本项要修的缺陷。见 [research.md](../research.md) R2。

## 不变式（**必须有判据钉住**）

| # | 不变式 | 判据 |
|---|---|---|
| **INV-1** | `clause_vec.doc_id` **恒等于** `clause_revision.doc_id`（按 `clause_revision_id` 关联） | 迁移后全表比对：**不一致行数 = 0** |
| **INV-2** | 迁移**不改变任何向量** | 迁移前后逐条比 `embedding` 字节：**不同 = 0** |
| **INV-3** | 行数不变 | 迁移前后 `COUNT(*)` 相同（663,634） |
| **INV-4** | 范围过滤**必须下推** | `test_vec_channel_is_restricted_without_the_model` 转绿（断言原样） |
| **INV-5** | 无范围路径**零回归** | 同数据同查询，新表 top-20 **逐条 == 旧表 top-20** |
| **INV-6** | 写入侧同步 | 新插入一条条款后，**它带 `doc_id`**，且能在范围提问里被查到 |

## 状态与迁移

- **不是** `ALTER TABLE`（虚拟表不支持加列）⇒ 迁移 = **建新表 → 拷贝 → 改名**。
- 迁移**必须**：① 先备份；② 单事务；③ 逐字节自检；④ 回滚步骤是**可执行命令**。
- 存量：**663,634 行**（2026-10-09 读数，会继续长 ⇒ 迁移脚本要**按当时的行数自检**，不写死）。

## 与其它表的关系

| 表 | 关系 |
|---|---|
| `clause_revision` | `clause_vec.clause_revision_id` ↔ `clause_revision.clause_revision_id`（1:1，**无外键**——虚拟表不支持 FK） |
| `clause_revision.doc_id` | `doc_id` 列的**来源**（迁移时 join 取得） |
| `doc_meta` | 间接：`clause_revision.doc_id` → `doc_meta.doc_id` |
| `clause_vec_qwen`（影子表） | **必须保持同形**（否则将来换表后范围提问照样坏） |

⚠ **无外键 ⇒ 无级联**：删文档时 `doc_delete.py` 按 `clause_revision_id` 清 `clause_vec`（既有逻辑，**不改**）。
