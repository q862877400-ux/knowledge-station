# Phase 1 · Quickstart（怎么验）

> 每一步都是**可执行命令 + 预期读数**。判据见 [contracts/contracts.md](contracts/contracts.md) §4。

## 0. 前置

```bash
cd "D:/AI/work space/zcode"
PY=".venv/Scripts/python.exe"        # 托管 Python 跑不了 src.core.*（无 pydantic）
```

## 1. 修法成立性（**不碰真库**，纯内存库）

```bash
$PY specs/003-vec-scope-pushdown/probes/probe-vec-scope-fix.py
$PY specs/003-vec-scope-pushdown/probes/probe-vec-scope-fix2.py
```

**预期**：

| 探针 | 预期读数 |
|---|---|
| fix.py | Q1 现状 **0 行**（复现）；**Q2a 新写法 1 行 `['in_weak']`**；Q2b/Q2d **混进范围外**（反例） |
| fix2.py | Q5 100 篇范围**仍下推**；Q6 无范围路径**逐条相同**；Q7 拷贝**逐字节一致**；Q8 空范围**0 行不报错**；Q9 性能同量级 |

⚠ 若 Q2a 不是 1 行 ⇒ **修法不成立，停下来**（`sqlite-vec` 版本变了？）。

## 2. 判据（**修好后必须绿**）

```bash
$PY -m pytest tests/test_kb_scope_retrieval.py -q          # 含那条真缺陷用例
$PY -m pytest tests/test_contract.py -q                    # 存储契约
$PY -m pytest tests/test_embedding_rebuild_resume.py -q     # 影子表同形
$PY -m pytest tests/test_doc_batch_delete.py -q             # 删文档路径（插向量已带 doc_id）
```

**预期**：全绿；`test_vec_channel_is_restricted_without_the_model` **不再红**。

## 3. 变异验证（**判据必须有牙**）

把 `hybrid_engine` 的范围过滤**改回** `clause_revision_id IN (…)` ⇒
`test_kb_scope_retrieval.py` **必须红**；改回后**逐字节还原**（`sha256sum` 前后一致）。

同样，把 `doc_id` 的过滤换成字面量列表 `IN (?, ?)` ⇒ **也必须红**（返回范围外的行）。

## 4. 迁移（**动真库**；先备份）

```bash
# ① 只读预演（不写库）：算出要搬多少行、抽查几条
$PY scripts/migrate-clause-vec-doc-id.py --dry-run

# ② 真跑（含备份 + 自检）
$PY scripts/migrate-clause-vec-doc-id.py --apply --db-copy
```

**预期读数**：

| 项 | 预期 |
|---|---|
| 行数 | 迁移前后相同（**663,634**，按当时实数自检） |
| 向量字节 | 逐条比对 **0 处不同** |
| `doc_id` 一致性 | 与 `clause_revision` 关联比对 **0 处不一致** |
| 耗时 | **分钟级** |
| 备份 | 全库副本 + 行级备份，路径打印出来 |

## 5. 端到端（真库，走**生产代码路径**）

```bash
$PY specs/003-vec-scope-pushdown/probes/e2e-real-db.py
```

**预期读数**（2026-10-09 实测，663,634 行真库）：

| 场景 | 预期 |
|---|---|
| 范围提问（`channels=["vec"]` + `doc_ids=5 篇`） | **10 条、零越界** |
| 不限定范围（历史路径） | **10 条** |
| 空范围 `doc_ids=[]` | **0 条**（不许退化成全库） |

⚠ 这一步走的是**生产的 `perform_hybrid_search`**，不是手写 SQL ——
本轮已经因为手写 SQL 写错过一次，所以**必须有这一步**。

## 6. 门禁

```powershell
pwsh -File scripts/run-gates.ps1 -Quick
```

**预期**：**不再有本项引入的新红**（`tsc` / `smoke` 两个历史红与本项无关，见交接单）。
