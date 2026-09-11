# 第三轮 · 契约与方案（五项）

## R-A 批量导入：取消扫描上限，且不卡死
**方案**（有界并发 + 分片 checkpoint，非无界并发）：
- fast_scan **循环扫描直到目录文件穷尽**，不再 200 截断；`batch_size` 语义改为"每处理 200 个文件落一次 checkpoint"（断点粒度，非上限）
- 并发恒为 `scan_concurrency=2`（线程池有界，不会因取消上限而并发爆炸）
- 每处理一批即 `_save_ckpt`（可暂停：循环内每批检查 pause 标志/批次状态，用户点终止最迟 200 文件内生效）
- 内存有界：checkpoint 队列 35k 条 ≈ 数 MB 元数据，无文件内容驻留
- 验收：造 450 文件（batch_size=200）→ 一次启动扫完全部 450；中途 pause → 恰在下一批边界停；resume 后继续扫完

## R-B span 坐标系通用自动校准（新导入自动 + 存量可重跑）
**通解**：抽取独立模块 `src/core/ingestion/span_calibration.py`：
- `calibrate_spans(pdf_path, spans) -> spans(normalized)`：对每页构建**文字行中心表**（fitz words 按行聚类），对每个 span 的 bbox 取两种解释（直读/ H−y 换算）的中心，**投票给"距离最近文字行"更近的解释**（最近行匹配，解决 50140 碎片投票分裂的根因——旧法拿碎片中心比条款块首行，碎片越靠后偏差越大导致 8:6 分裂）
- 文档级投票（多数决）→ 顶部原点则全量翻转 y'=H−y
- **接入点（新文件自动校准）**：`pipeline.run_full_ingest` 在 span 写库前调用；`bulk.parse_loop`/fast_scan 骨架不产生 span（解析走 run_full_ingest 自动覆盖）
- **存量**：`scripts/repair_span_origin.py` 改为复用该模块（删除自身重复投票逻辑）
- 验收：GB 50140-2005 全 span 投票不再分裂（一致判定）；全部文档 dry-run 0 需翻转；新造一个"翻转坐标"测试 PDF 走 run_full_ingest → 入库即被自动纠正

## R-C 高亮吸附半行偏差·根因修复
根因链条：R-B 未做时 bbox 本身偏 → 吸附窗口(±max(14,h*0.8))不够大够不到真行。R-B 落地后 bbox 归位，吸附仅兜底；同时把吸附窗口对称加宽到 `padY = max(20, h*1.2)`（覆盖上下各一整行），杜绝边缘半行漏吸。改 `PdfViewer.tsx` 一处常量。

## R-D browser4 截图损坏 → 重装
`npm install -g browser4-cli@latest` + `browser4-cli install`（runtime 重装到 BROWSER4_RUNTIME_DIR），验证：对任意页面 screenshot 输出 >10KB 的合法 PNG（文件头 89 50 4E 47）。不通过则回退 `close-all` + 删 state 目录重初始化再验。

## R-E 架构重叠（laws_db vs law_source/update）——本轮搁置（业主指示）

## 全局验收
全量 pytest ≥343+3 不回退；tsc 0（涉前端时）；真实引擎冒烟：450 文件导入全扫完 + GB 30871 引用高亮仍精确。
