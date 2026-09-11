# 万级批量导入编排器 · 实现契约（pipeline/06 落地）

> 目标：35000 个标准 PDF / 100+GB。三阶段：快扫建目录（小时级可用）→ 异步全量解析（逐夜滚动）→ 首检入列。

## 文件清单（白名单，防并行冲突）
- 新建 `src/core/ingestion/bulk.py`（编排器，唯一新增核心）
- 新建 `tests/test_bulk_import.py`
- 追加 `src/core/api/server.py`（3 条路由）
- 追加 `src/renderer/UpdatePanel.tsx`（「批量导入」页签）
- 追加 `tests/test_update_api.py`（鉴权用例）

## 数据契约（复用既有表，零新表）
- `bulk_import_batch`（表31，batch_kind='bulk_ingest'）：status/checkpoint_json 断点续跑
- `doc_meta` 骨架行：快扫产出 `quality_grade='C'` + `doc_type` 沿用 + 标记字段用 `normative_refs` 存 `{"bulk_import":"pending_parse"}`（不新增列，契约零变更）
- 写路径全部走 write_transaction；审计 event_log event_type='bulk/batch_*'

## API
| 方法 | 端点 | 语义 |
|---|---|---|
| POST | /api/v1/ingest/bulk | `{src_dir, batch_size?=200}` → 启动快扫批次 {batch_id}；重复运行 409/UPD-2001 |
| GET | /api/v1/ingest/bulk/{batch_id} | 进度（快扫 checked/total + 解析队列 stats） |
| POST | /api/v1/ingest/bulk/{batch_id}/pause·resume | 断点控制 |

## 实现要点（bulk.py）
1. `fast_scan(src_dir)`：os.walk 收 *.pdf → 逐文件 PyMuPDF 首页抽 standard_no/standard_name/年代 → file_hash 防重（doc_meta+checkpoint 双查）→ 插骨架行 → quarantine 失败件
2. `parse_loop(batch_id)`：从 checkpoint 队列取件调 `run_full_ingest(reingest=False)` 逐夜预算 `bulk.parse_daily_budget`=2000；每 5 批自动 VACUUM INTO 快照
3. 状态机/断点：复用 inspector 的 ckpt 结构（queue/errors/pause_reason）+ paused/running/done/failed
4. 首检入列：解析成功的 standard_no 进巡检 tier0（新入库未首检 SQL 天然覆盖）

## 验收
1. 快扫：临时目录造 5 个假 PDF（含标准号文本）→ 骨架行/防重/隔离区正确
2. 断点：扫描到一半 pause → 杀进程 → resume 不重复
3. 预算/快照：mock parse 预算截断 + 每 5 批快照触发
4. 全量 pytest ≥322+3；tsc 0
