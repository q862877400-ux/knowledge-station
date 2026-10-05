# law-source（官方法规来源管线）

**位置**：`src/core/knowledge/law_source/`
**一句话**：把官方法规原文抓进来，走与标准件完全同构的入库链。

## 职责

**法规侧的数据源层**。链路：`flk.npc.gov.cn`（国家法律法规数据库）+ `gov.cn`（国务院政策文件库）→ 官方带格式 Word → LibreOffice/WPS 转 PDF → 现有 `run_full_ingest` 管线。产物**与标准件完全同构**（预览/高亮/目录/条款修正都是同一套）。

主要模块：`catalog.py` 22.4 KB（编目）、`verify.py` 15.2 KB（核验）、`ingest.py` 10.1 KB（入库）、`govcn_client.py` / `flk_client.py`（两个来源客户端）。

**它不负责**：不做渠道巡检（`update`）、不做解析本身（`ingestion`）、不做条款检索（`retrieval`）。

## 对外提供什么

| 官方法规编目 | `catalog.py` | `api` 的 `/laws/*` |
| 来源客户端 | `flk_client.py` / `govcn_client.py` | 抓取 |
| 法规入库 | `ingest.py` | `ingestion` 管线 |
| 核验 | `verify.py` | 入库前后 |

## 依赖什么

| `ingestion` 的 `run_full_ingest` | 同仓 | 完整入库管线 |
| LibreOffice / WPS | 外部 | Word → PDF 转换 |
| `storage` | 同仓 | 落库 |

## 明确不做什么

- 🔴 **MUST NOT 抓白名单以外的域**：**来源域白名单在 `http.py` 强制**，别绕过它。
- **不做效力判定**：现行/废止/被代替的状态来自官方，不是本模块算的。
- **不做非官方来源的法规**：这里只接官方站。

## 已知边界（诚实）

- **产物与标准件同构**是刻意设计：**改入库链 MUST 两边一起看**，不要只改法规侧。
- ⚠ 代码注释里提到「主计划 v4.3」——**那份主计划已不在文档集合里**，引用它时注意它是历史文件。
- **引擎侧的接口探测核实于 2026-06**（见 `flk_client.py` / `govcn_client.py` 的 docstring），**可能已经变了**。
