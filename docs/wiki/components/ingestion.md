# ingestion（解析与入库）

**位置**：`src/core/ingestion/`
**一句话**：把 PDF / 扫描件 / Office / 网页变成条款，并带上能回到原文的坐标。

## 职责

**从原始文件到可检索的条款**。它接手的是用户丢进来的文件，交付的是「条款 + 它在原文里的位置」。

**规模**：`pipeline.py` **141 KB**（本模块最大），`mineru_adapter.py` 30.4 KB、`dry_run.py` 27.8 KB、`bulk.py` 27 KB、`mineru_cloud.py` 20.9 KB、`material_ingest.py` 20.1 KB。

**它不负责**：不负责判断该不该入库（那是用户与评审纪律）、不做检索（`retrieval`）、不存条款（`storage`）。

## 对外提供什么

| 提供物 | 形式 | 调用方 |
|---|---|---|
| 入库主管线 | `pipeline.py` | `api` 的入库端点 |
| MinerU 解析适配（本地 / 云端） | `mineru_adapter.py` / `mineru_cloud.py` | `pipeline` |
| 万级批量导入编排 | `bulk.py` | 运维 |
| 入库预览（Dry-Run） | `dry_run.py` | `api` 的预览端点（**只读**） |
| docx 一等公民入库 | `docx_ingest.py` / `docx_adapter.py` | 用户上传 Word（有 Word 走 COM 转 PDF 保 bbox；无 Word 走降级直解） |
| 常驻深度解析服务 | `deep_server.py` | GPU 攒批 |
| 材料入库 | `material_ingest.py` | `materials` |

## 依赖什么

| 依赖 | 类型 | 用途 |
|---|---|---|
| MinerU | 外部 | 版面解析与坐标 |
| PyMuPDF | 外部 | PDF 读取与渲染 |
| Word COM | 外部（可选） | docx → PDF |
| `storage` | 上游模块 | 落库 |

## 明确不做什么

- **不做检索**：入库只管把条款放好，怎么找是 `retrieval` 的事。
- **不做权威性判定**：材料可信度在 `materials/authority.py`。
- **不做去重决策**：近重复检测在 `materials/dedup.py`；本模块按调用方给的范围入库。
- **MUST NOT 在网关里放长任务**：解析是重活，走队列/常驻服务，不让 HTTP 请求等它。

## 已知边界（诚实）

- **docx 有两条路**：有 Word 时走 COM 转 PDF（**有 bbox**），无 Word 时降级直解（**可能没有 bbox**）。这会影响下游能不能定位到原文。
- **入库预览是只读的**：`dry_run.py` 不许落库。
