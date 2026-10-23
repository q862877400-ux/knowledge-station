# knowledge（法规知识本体与分类）

**位置**：`src/core/knowledge/`
**一句话**：管法规/标准文档的目录、分类号与别名，让同一份文件在不同叫法下都能被找到。

## 职责

**知识库的组织层**：多级目录（`folder_store.py` 83.7 KB）、标准分类号 CCS（`ccs_fetcher.py` 43.5 KB / `ccs_backfill.py` 34.4 KB / `ccs_undo.py`）、文档编目（`doc_catalog.py`）、别名与大白话反查（`alias_extract.py`）、自动标签（`auto_tag.py`）。

**它不负责**：不做解析（`ingestion`）、不做检索排序（`retrieval`）、不做渠道巡检（`update`）。

## 对外提供什么

| 提供物 | 形式 | 调用方 |
|---|---|---|
| 知识库多级目录 | `folder_store.py` / `folder_filing_plan.py` | `api` 的目录端点、插件侧栏 |
| CCS 分类号查询与补全 | `ccs_fetcher.py` / `ccs_backfill.py` / `ccs_undo.py` | 入库与补全流程 |
| 文档编目 | `doc_catalog.py` | 界面 |
| 别名 / 大白话反查 | `alias_extract.py` | `retrieval`（换词可对） |
| 入库自动标签 | `auto_tag.py` | `ingestion` |

## 依赖什么

| 依赖 | 类型 | 用途 |
|---|---|---|
| `storage` | 上游模块 | 目录与编目的持久化 |
| 外部标准分类源 | 外部 | CCS 查询（**一条链、来源有序、每条都记来源**） |

## 明确不做什么

- **不做检索**：别名与分类是给 `retrieval` 用的**原料**，不在此排序。
- **不做权威性判定**：那在 `materials/authority.py`。
- **不做渠道覆盖台账**：那在 `update`。


## 规模与覆盖（2026-10-23 实测）

| 项 | 数字 |
|---|---|
| 文件数 | **22** 个 `.py` |
| 行数 | **6,769** |
| 提到本子系统的测试文件 | **27** 个 |

含 `law_source/` 子目录（法规官方源抓取）

> 数字口径：`rglob("*.py")` 排除 `__pycache__`；测试覆盖 = 在 `tests/*.py` 里出现过 `src.core.<本子系统>` 的文件数（**只是「提到」，不等于「被测」**）。

## 已知边界（诚实）

- **CCS 补全是插件自己做的**（2026-09-22 业主口径），不是外挂工具。
- ⚠ **`ccs_undo.py` 存在意味着补全可回滚**——改分类号 MUST 走可回滚的路径。
