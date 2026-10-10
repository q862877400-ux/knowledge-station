# vision（本地视觉反查）

**位置**：`src/core/vision/`
**一句话**：把一张截图或图纸认成文字，再用它去找条款——全程在本机。

## 职责

**截图 / 图纸 → 文字 → 条款定位**（`local_vision.py` 4.8 KB）：`ocr_image_text()` 先用 RapidOCR（本地、单图毫秒级），不可用或结果为空时回退本地 MinerU 的图片 OCR（模型级精度）；`vision_locate()` 拿 OCR 文本去 `retrieval` 的混合检索里找条款。

云通道已从这条链路退役（2026-09-01）：截图反查是用户主动操作，本模块**全程本地执行、零外发**。

## 对外提供什么

| 提供物 | 形式 | 调用方 |
|---|---|---|
| 截图反查（OCR + 检索） | `local_vision.vision_locate(image_path, top_k=5)` | `api/server.py` 的截图反查端点 |
| 图片 OCR 文本 | `local_vision.ocr_image_text(image_path, out_dir)` | 同链路 |
| 本地 MinerU 图片 OCR | `local_vision.ocr_image_locally(image_path, out_dir)` | OCR 回退路径 |

返回的是**候选条款**（`clause_revision_id` / `standard_no` / `clause_number` / `modality` / 正文前 200 字）与 OCR 文本前 300 字。

## 依赖什么

| 依赖 | 类型 | 用途 |
|---|---|---|
| rapidocr_onnxruntime（经 `figure_redraw.get_ocr`） | 外部库 | 首选本地 OCR |
| mineru CLI（子进程，`-m ocr`） | 外部程序 | OCR 回退 |
| `retrieval.hybrid_engine.perform_hybrid_search` | 上游模块 | 文本 → 条款候选 |
| `config.data_dir` | 同仓 | OCR 临时目录 `vision_tmp/` |

## 明确不做什么

- **不做版面解析**：带坐标的版面解析是 `ingestion` 的 MinerU 链路；本模块只回答「这图里写了什么、像哪一条」。
- **不做条款切分与入库**：那是 `ingestion`。
- **不判定对不对**：返回候选，不下结论、不核验（核验在 `verification`）。
- **不联网、不外发**：云视觉通道已退役；要重新引入必须走外发审计（`llm/egress_audit`）。
- **不做扫描页方向纠正的执行**：翻转由入库管线在无文本层页面触发，本模块只为截图反查提供定位。

## 关键数据

不持有表。临时文件写在 `data_dir/vision_tmp/<图片名>/`。

## 改了它会影响谁

- **`api/server.py` 的截图反查端点**：返回结构直接决定界面显示
- **`retrieval`**：OCR 文本当查询串用，改截断长度会改命中面

## 已知边界（诚实）

- **查询串只取 OCR 文本的前 400 字**：长截图 / 多栏图会截断，命中结果随之偏。
- **两条 OCR 路径质量不同**：RapidOCR 快但弱，回退到 MinerU 才有模型级精度——用户看到的差别来自这个回退是否触发。
- **仓内有一份被否决的方案**：`../../archive/research-process/WSL2-VLM-BACKEND-DECISION.md` 记录了 WSL2 后端那次「否决，保留复议权」。改本模块前先读它。
