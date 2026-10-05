# domain（域模型契约）

**位置**：`src/core/domain/`
**一句话**：全项目共用的对象定义与模态强度常量，T00 冻结。

## 职责

**Pydantic 域模型契约**（`models.py` 7.4 KB）：`PageGeometryModel`、`SourceSpanModel`、`ClauseRevisionModel`、`DocumentMetaModel`、`EvidenceEdgeModel`、`ReviewPointModel`、`ModalityViolation`、`VerificationResult`，以及两个类型别名 `KnowledgeType` / `Modality` 与权威常量 `MODALITY_STRENGTH`。

它是**同一进程内的类型依据**：子系统之间传的对象长什么样，以这里为准。

## 对外提供什么

| 提供物 | 形式 | 调用方 |
|---|---|---|
| 条款 / 坐标 / 文档模型 | `ClauseRevisionModel` / `SourceSpanModel` / `PageGeometryModel` / `DocumentMetaModel` | `ingestion`（`pipeline` / `docx_ingest` / `law_text`）、`storage`（`clause_repo` / `versioning`）、`retrieval/hybrid_engine`、`llm/ks_answer` |
| 模态强度字典 | `MODALITY_STRENGTH` | `verification/typed_verifier`、`knowledge/classifier`、`retrieval`、`storage/versioning` |
| 核验结果模型 | `VerificationResult` / `ModalityViolation` | 核验链路 |
| 引用边与评审点 | `EvidenceEdgeModel` / `ReviewPointModel` | 证据与评审 |

## 依赖什么

| 依赖 | 类型 | 用途 |
|---|---|---|
| pydantic | 外部库 | 模型定义与字段校验 |

**没有别的依赖**：本模块不 import 仓内任何子系统。

## 明确不做什么

- **不放业务逻辑**：没有判定、没有算法；行为在各自的子系统里。
- **不做 IO**：不读写库、不读文件、不联网。
- **不另建第二份模态强度**：`MODALITY_STRENGTH` 是权威常量，别处**只读**；要改走契约变更流程并同步 `verification` 与 `knowledge/classifier`。
- **不做 schema 演进决策**：加字段、改语义由改动方发起，须全仓评估影响面（引用方见上表）。

## 关键数据

| 对象 | 关键字段 | 说明 |
|---|---|---|
| `SourceSpanModel` | `page_number` / `bbox` / `span_type` | **bbox 是 PDF 坐标（左下原点，`[x1,y1,x2,y2]`）**，不是屏幕坐标 |
| `ClauseRevisionModel` | `clause_revision_id` / `clause_key` / `standard_no` / `clause_number` / `content_text` | 条款与它的一处修订 |
| `MODALITY_STRENGTH` | 词 → 强度 0~5 | 「严禁 / 禁止」5，「应当 / 必须」3，「可以」1，「鼓励」0 |

## 改了它会影响谁

**几乎全部子系统**——凡是用条款对象的地方都受影响（`ingestion`、`storage`、`retrieval`、`llm`、`verification`、`quality`）。

⇒ 改 `models.py` 的字段或 `MODALITY_STRENGTH` 的取值 MUST 先按上表逐个调用方看一遍。

## 已知边界（诚实）

- **T00 冻结**：这份契约是早期冻结的；改动需评估全仓影响，不要顺手加字段。
- **`bbox` 的坐标系只有一种**：PDF 坐标、左下原点。前端要显示必须自己换算，别把屏幕坐标写回库。
- ⚠ **字段描述 ≠ 运行时语义**：本仓曾照 OpenAPI 的文字描述当根因、被复核推翻。字段的实际行为以产生它的代码为准。
