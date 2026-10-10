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
- **M6**：迁移脚本**幂等**（已迁移过再跑 = 空操作；且**仍会报** `doc_id 为空` / `与 clause_revision 不一致` 的条数）。
- **M7**（**运行前置，2026-10-09 收敛轮补**）：**迁移之后必须重启引擎**（`-m src.core.main`）。
  跑着的旧进程仍是**旧代码**（只按两列写向量）⇒ 它写入的条款 `doc_id` 会是**空**
  ⇒ 那些条款会在「按目录范围提问」里**静默消失** —— 正是 FR-009 要防的。
  **核验命令**：`python scripts/migrate-clause-vec-doc-id.py --dry-run`
  ⇒ 看 `doc_id 为空` 是否为 **0**；不为 0 时脚本会打印**回填 SQL**。
- **M8**（**回滚源回收，2026-10-09 收敛轮补**）：`clause_vec_pre003`（普通表）是回滚源，
  占 **2.6 GB**（库 2.96 → 5.6 GB），**不该长期留着**（C 盘紧张时会咬人）。
  **回收前置（四条全满足才可删）**：① 独立复核 **PASS**；② 全库副本仍在（`backup/`）；
  ③ `doc_id 为空` == 0；④ 与 `clause_revision` **零不一致**。
  ⚠ **回收动作本身要业主点头**（删了就只剩全库副本那条回滚路）。

  ### ✅ **已执行（2026-10-10 14:3x）—— 且发现"只剩全库副本"这个顾虑本身不成立**

  **授权**：业主 2026-10-10「我给你一切授权，一切需要拍板的事情都采纳你的建议」
  ⇒ M8 里"要业主点头"那条**转为已授权**。

  **四条前置逐条复测（只读真库，全部 PASS）**：
  ① 独立复核 PASS ✅（[VERIFY-REPORT-spec003-vecscope](../../../docs/verify-briefs/VERIFY-REPORT-spec003-vecscope.md)，
     判定"有条件 PASS、无 P0"）｜② 全库副本在 ✅（`backup/` 下三份，各 663,634 条）｜
  ③ `doc_id` 为空 **0** ✅｜④ 孤儿（对不上 `clause_revision`）**0** ✅。

  **★ 本轮补第五条前置 —— 它把"要不要删"这个问题从"权衡"变成了"没有代价"**：
  ⑤ **`clause_vec_pre003` 可被 `clause_vec` 完整重建**：逐条比对 **663,634** 条的
  `(clause_revision_id, embedding)` ⇒ **嵌入不一致 0 / pre003 独有 0**。
  ⇒ 回滚源**零独有信息** —— 重建就是**一条 SQL**：

  ```sql
  CREATE TABLE clause_vec_pre003 AS
    SELECT clause_revision_id, embedding FROM clause_vec;
  ```

  **不需要重算嵌入、不需要模型、不需要原文。** 回滚脚本落在
  `var/tmp/clause-vec-pre003-rollback.sql`（**一行 SQL，不是一份 2.6 GB 副本** ——
  那样会把刚回收的空间又吃回去）。**该 SQL 已在临时库里真跑过验证**
  （抽样 2,000 条：重建 2,000 条、逐条比对相同 2,000 / 不同 0）。

  ⚠ **原 M8 那句"删了就只剩全库副本那条回滚路"要更正**：实测**有两条**回滚路，
  且新发现的那条**更省**（一行 SQL vs 恢复 2.9 GB 的库文件）。

  **执行与读数**：
  | 步 | 动作 | 读数 |
  |---|---|---|
  | 1 | `DROP TABLE clause_vec_pre003`（单事务） | 残留对象 **0**；`clause_vec` 仍 663,634；`doc_id` 为空仍 0；向量表仍可查 |
  | 2 | `VACUUM` | **5.49 GB → 2.88 GB**（回收 **2.61 GB**），用时 0.6 分钟 |
  | 3 | `PRAGMA wal_checkpoint(TRUNCATE)` | ⚠ **这一步是必需的**：VACUUM 在 WAL 模式下把整库重写**先写进 `-wal`**（实测涨到 **2.90 GB**）⇒ 不截断的话磁盘上反而是 `2.88 + 2.90 = 5.78 GB`，**比删之前还大**，"回收了 2.61 GB"在磁盘上就是假话。截断后 `-wal` = **0** |
  | 4 | `PRAGMA integrity_check` | **ok**；`clause_revision` 663,634；`evidence_edge` 22,992（未变） |

  **净效果**：库文件 **5.49 GB → 2.88 GB**；C 盘空闲 **76.90 → 82.40 GB**。

  **边界**：只 `DROP` 这一张表 + `VACUUM`；不动 schema、不动 `clause_vec` 任何行、
  不动其余五条通道；`backup/` 三份副本**一份未删**（M8 前置② 的保障仍在）。

---

## 契约 4 · 判据（不许放宽）

| 判据 | 位置 | 要求 |
|---|---|---|
| 向量通道被范围堵住 | `tests/test_kb_scope_retrieval.py::test_vec_channel_is_restricted_without_the_model` | **转绿**；**断言一个字不改**（含"必须有命中"与"不许混进范围外"） |
| 表形状 | `tests/test_contract.py`（新增用例） | `clause_vec` 有 `doc_id` 列且为普通列；`embedding` 仍 512 |
| 影子表同形 | `tests/test_embedding_rebuild_resume.py::test_shadow_dim_matches_production_schema` | 正则**同步新形状**，意图（维度 = 512）不变 |
| 范围写法不许退化 | 新增用例 | 把查询改回 `clause_revision_id IN (…)` ⇒ **必须红**（变异验证） |
