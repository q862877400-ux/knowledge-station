# 表读写关系

> **由 `scripts/survey/03-render.py` 从 `data/*.json` 生成，勿手改。**
> 数字与 JSON 一一对应；要改数字请重跑生成器。

## 一、口径

扫描 `src/**/*.py` 里的 SQL 字面量：写 = INSERT/REPLACE/UPDATE/DELETE 后面的表名；读 = FROM/JOIN 后面的表名。**只抓字面量**：f-string 拼出来的表名看不到（本仓实测有 7 处）。表名必须在种子库 `sqlite_master` 里存在，否则丢弃（避免把 CTE 别名当表）。

## 二、总账

| 项 | 数 |
|---|---:|
| 表 | **59** |
| 静态查不到写入方的表 | **19** |
| 静态查不到读取方的表 | **18** |

> ⚠ 这两行是**计数，不是判断**。「查不到」有三种可能：① 真的没人动；
> ② 表名用 f-string 拼的（本仓实测 7 处）；③ 由 SQLite 自己维护（如 FTS 影子表）。

## 三、每张表的读写方

| 表 | 写入方 | 读取方 |
|---|:--:|:--:|
| `alias_store` | 1 | 2 |
| `announcement_observed` | 1 | 2 |
| `app_config` | 4 | 4 |
| `audit_log` | **0** | **0** |
| `bulk_import_batch` | 2 | 5 |
| `channel_test_case` | 1 | 1 |
| `clause_fts` | 3 | 4 |
| `clause_fts_config` | **0** | **0** |
| `clause_fts_content` | **0** | **0** |
| `clause_fts_data` | **0** | **0** |
| `clause_fts_docsize` | **0** | **0** |
| `clause_fts_idx` | **0** | **0** |
| `clause_patch` | 3 | 4 |
| `clause_revision` | 2 | 16 |
| `clause_vec_chunks` | **0** | **0** |
| `clause_vec_info` | **0** | **0** |
| `clause_vec_metadatachunks00` | **0** | **0** |
| `clause_vec_metadatatext00` | **0** | **0** |
| `clause_vec_rowids` | **0** | **0** |
| `clause_vec_vector_chunks00` | **0** | **0** |
| `debug_dump` | 3 | 4 |
| `doc_ccs_state` | 2 | 3 |
| `doc_filing_state` | 3 | 3 |
| `doc_meta` | 10 | 31 |
| `doc_page_geometry` | 2 | 1 |
| `event_log` | 9 | 2 |
| `evidence_edge` | 2 | 2 |
| `feedback_log` | **0** | 1 |
| `folder` | 1 | 1 |
| `folder_member` | 3 | 3 |
| `gap_analysis` | 1 | **0** |
| `internal_policy` | 1 | 2 |
| `law_catalog` | 1 | 1 |
| `legal_obligation` | 2 | 3 |
| `material` | 1 | 2 |
| `material_chunk` | 1 | 1 |
| `material_fts_config` | **0** | **0** |
| `material_fts_content` | **0** | **0** |
| `material_fts_data` | **0** | **0** |
| `material_fts_docsize` | **0** | **0** |
| `material_fts_idx` | **0** | **0** |
| `material_project` | 1 | 1 |
| `obligation_list` | 1 | 2 |
| `operation_log` | 2 | 1 |
| `project_list` | 1 | 4 |
| `remapping_queue` | 1 | 1 |
| `review_point` | **0** | 1 |
| `review_task` | 1 | 2 |
| `snapshot_meta` | 1 | 1 |
| `source_span` | 3 | 6 |
| `update_change_event` | 3 | 6 |
| `update_channel` | 1 | 2 |
| `update_check_batch` | 2 | 2 |
| `user_annotation` | 1 | 3 |
| `user_bookmark` | 1 | 5 |
| `user_bookmark_folder` | 1 | 1 |
| `user_doc_bookmark` | 2 | 4 |
| `watch_list` | 1 | 3 |
| `write_queue` | 1 | 1 |

## 四、详细（谁写谁读）

### `alias_store`

写入：`src/core/knowledge/alias_extract.py`

读取：`src/core/api/server.py`、`src/core/knowledge/alias_extract.py`

### `announcement_observed`

写入：`src/core/update/announce.py`

读取：`src/core/update/announce.py`、`src/core/update/web_ingest.py`

### `app_config`

写入：`src/core/update/announce.py`、`src/core/update/discover.py`、`src/core/update/inspector.py`、`src/core/update/subscriptions.py`

读取：`src/core/update/announce.py`、`src/core/update/discover.py`、`src/core/update/inspector.py`、`src/core/update/subscriptions.py`

### `bulk_import_batch`

写入：`src/core/ingestion/bulk.py`、`src/core/update/inspector.py`

读取：`src/core/api/routes_update.py`、`src/core/ingestion/bulk.py`、`src/core/update/inspector.py`、`src/core/update/report.py`、`src/core/update/scheduler.py`

### `channel_test_case`

写入：`src/core/update/channel_test.py`

读取：`src/core/update/channel_test.py`

### `clause_fts`

写入：`src/core/ingestion/pypdf_backfill.py`、`src/core/storage/clause_repo.py`、`src/core/storage/doc_delete.py`

读取：`src/core/retrieval/hybrid_engine.py`、`src/core/retrieval/term_bridge.py`、`src/core/storage/clause_repo.py`、`src/core/storage/doc_delete.py`

### `clause_patch`

写入：`src/core/ingestion/pypdf_backfill.py`、`src/core/storage/clause_repo.py`、`src/core/storage/doc_delete.py`

读取：`src/core/api/server.py`、`src/core/ingestion/pypdf_backfill.py`、`src/core/storage/clause_repo.py`、`src/core/storage/doc_delete.py`

### `clause_revision`

写入：`src/core/storage/clause_repo.py`、`src/core/storage/doc_delete.py`

读取：`src/core/api/server.py`、`src/core/compliance/gap_analysis.py`、`src/core/exports/backlinks.py`、`src/core/ingestion/pypdf_backfill.py`、`src/core/ingestion/span_calibration.py`、`src/core/ingestion/span_verify.py`、`src/core/llm/ks_answer.py`、`src/core/retrieval/hybrid_engine.py`、`src/core/retrieval/term_bridge.py`、`src/core/storage/backup.py`、`src/core/storage/clause_repo.py`、`src/core/storage/doc_delete.py`、`src/core/storage/impact.py`、`src/core/storage/user_data.py`、`src/core/storage/versioning.py`、`src/core/update/data_package.py`

### `debug_dump`

写入：`src/core/api/server.py`、`src/core/llm/egress_audit.py`、`src/core/storage/debug_dump_retention.py`

读取：`src/core/api/server.py`、`src/core/exports/backlinks.py`、`src/core/llm/egress_audit.py`、`src/core/storage/debug_dump_retention.py`

### `doc_ccs_state`

写入：`src/core/knowledge/ccs_store.py`、`src/core/knowledge/ccs_undo.py`

读取：`src/core/knowledge/ccs_backfill.py`、`src/core/knowledge/ccs_store.py`、`src/core/knowledge/ccs_undo.py`

### `doc_filing_state`

写入：`src/core/knowledge/folder_store.py`、`src/core/storage/clause_repo.py`、`src/core/storage/doc_delete.py`

读取：`src/core/knowledge/folder_store.py`、`src/core/storage/clause_repo.py`、`src/core/storage/doc_delete.py`

### `doc_meta`

写入：`src/core/ingestion/bulk.py`、`src/core/ingestion/pipeline.py`、`src/core/ingestion/smoke_ingest.py`、`src/core/knowledge/auto_tag.py`、`src/core/knowledge/ccs_store.py`、`src/core/knowledge/ccs_undo.py`、`src/core/knowledge/law_source/ingest.py`、`src/core/storage/clause_repo.py`、`src/core/storage/doc_delete.py`、`src/core/update/change_repo.py`

读取：`src/core/api/routes_law.py`、`src/core/api/server.py`、`src/core/compliance/gap_analysis.py`、`src/core/exports/effect_report.py`、`src/core/ingestion/bulk.py`、`src/core/ingestion/docx_ingest.py`、`src/core/ingestion/dry_run.py`、`src/core/ingestion/law_text.py`、`src/core/ingestion/pipeline.py`、`src/core/ingestion/pypdf_backfill.py`、`src/core/ingestion/reingest.py`、`src/core/ingestion/smoke_ingest.py`、`src/core/ingestion/span_verify.py`、`src/core/knowledge/ccs_backfill.py`、`src/core/knowledge/ccs_store.py`、`src/core/knowledge/ccs_undo.py`、`src/core/knowledge/folder_store.py`、`src/core/knowledge/law_source/ingest.py`、`src/core/knowledge/law_source/update.py`、`src/core/llm/ks_answer.py`、`src/core/materials/track_l.py`、`src/core/retrieval/hybrid_engine.py`、`src/core/storage/backup.py`、`src/core/storage/clause_repo.py`、`src/core/storage/doc_delete.py`、`src/core/storage/user_data.py`、`src/core/storage/versioning.py`、`src/core/update/change_repo.py`、`src/core/update/data_package.py`、`src/core/update/inspector.py`、`src/core/update/web_ingest.py`

### `doc_page_geometry`

写入：`src/core/storage/clause_repo.py`、`src/core/storage/doc_delete.py`

读取：`src/core/storage/doc_delete.py`

### `event_log`

写入：`src/core/ingestion/bulk.py`、`src/core/ingestion/pipeline.py`、`src/core/ingestion/span_calibration.py`、`src/core/storage/channel_repo.py`、`src/core/storage/clause_repo.py`、`src/core/storage/doc_delete.py`、`src/core/storage/write_queue.py`、`src/core/update/change_repo.py`、`src/core/update/inspector.py`

读取：`src/core/api/server.py`、`src/core/update/inspector.py`

### `evidence_edge`

写入：`src/core/storage/clause_repo.py`、`src/core/storage/doc_delete.py`

读取：`src/core/retrieval/hybrid_engine.py`、`src/core/storage/doc_delete.py`

### `feedback_log`


读取：`src/core/llm/fewshot.py`

### `folder`

写入：`src/core/knowledge/folder_store.py`

读取：`src/core/knowledge/folder_store.py`

### `folder_member`

写入：`src/core/knowledge/folder_store.py`、`src/core/storage/clause_repo.py`、`src/core/storage/doc_delete.py`

读取：`src/core/knowledge/folder_store.py`、`src/core/storage/clause_repo.py`、`src/core/storage/doc_delete.py`

### `gap_analysis`

写入：`src/core/compliance/gap_analysis.py`

### `internal_policy`

写入：`src/core/compliance/gap_analysis.py`

读取：`src/core/api/server.py`、`src/core/compliance/gap_analysis.py`

### `law_catalog`

写入：`src/core/knowledge/law_source/catalog.py`

读取：`src/core/knowledge/law_source/catalog.py`

### `legal_obligation`

写入：`src/core/compliance/gap_analysis.py`、`src/core/storage/doc_delete.py`

读取：`src/core/compliance/gap_analysis.py`、`src/core/storage/doc_delete.py`、`src/core/update/data_package.py`

### `material`

写入：`src/core/storage/material_repo.py`

读取：`src/core/api/routes_materials.py`、`src/core/storage/material_repo.py`

### `material_chunk`

写入：`src/core/storage/material_repo.py`

读取：`src/core/storage/material_repo.py`

### `material_project`

写入：`src/core/storage/material_repo.py`

读取：`src/core/storage/material_repo.py`

### `obligation_list`

写入：`src/core/storage/user_data.py`

读取：`src/core/exports/backlinks.py`、`src/core/storage/user_data.py`

### `operation_log`

写入：`src/core/ingestion/law_text.py`、`src/core/ingestion/pipeline.py`

读取：`src/core/api/server.py`

### `project_list`

写入：`src/core/storage/user_data.py`

读取：`src/core/exports/backlinks.py`、`src/core/storage/impact.py`、`src/core/storage/user_data.py`、`src/core/update/data_package.py`

### `remapping_queue`

写入：`src/core/storage/clause_repo.py`

读取：`src/core/storage/clause_repo.py`

### `review_point`


读取：`src/core/exports/backlinks.py`

### `review_task`

写入：`src/core/compliance/gap_analysis.py`

读取：`src/core/api/server.py`、`src/core/update/data_package.py`

### `snapshot_meta`

写入：`src/core/storage/backup.py`

读取：`src/core/storage/backup.py`

### `source_span`

写入：`src/core/ingestion/span_calibration.py`、`src/core/storage/clause_repo.py`、`src/core/storage/doc_delete.py`

读取：`src/core/api/server.py`、`src/core/ingestion/span_calibration.py`、`src/core/ingestion/span_verify.py`、`src/core/llm/ks_answer.py`、`src/core/storage/clause_repo.py`、`src/core/storage/doc_delete.py`

### `update_change_event`

写入：`src/core/storage/doc_delete.py`、`src/core/update/change_repo.py`、`src/core/update/inspector.py`

读取：`src/core/api/routes_update.py`、`src/core/storage/doc_delete.py`、`src/core/update/change_repo.py`、`src/core/update/data_package.py`、`src/core/update/inspector.py`、`src/core/update/report.py`

### `update_channel`

写入：`src/core/storage/channel_repo.py`

读取：`src/core/storage/channel_repo.py`、`src/core/update/channel_test.py`

### `update_check_batch`

写入：`src/core/update/change_repo.py`、`src/core/update/inspector.py`

读取：`src/core/update/change_repo.py`、`src/core/update/report.py`

### `user_annotation`

写入：`src/core/storage/user_data.py`

读取：`src/core/storage/impact.py`、`src/core/storage/user_data.py`、`src/core/update/data_package.py`

### `user_bookmark`

写入：`src/core/storage/user_data.py`

读取：`src/core/api/server.py`、`src/core/exports/backlinks.py`、`src/core/storage/impact.py`、`src/core/storage/user_data.py`、`src/core/update/data_package.py`

### `user_bookmark_folder`

写入：`src/core/storage/user_data.py`

读取：`src/core/storage/user_data.py`

### `user_doc_bookmark`

写入：`src/core/storage/doc_delete.py`、`src/core/storage/user_data.py`

读取：`src/core/api/server.py`、`src/core/storage/doc_delete.py`、`src/core/storage/user_data.py`、`src/core/update/inspector.py`

### `watch_list`

写入：`src/core/storage/doc_delete.py`

读取：`src/core/storage/doc_delete.py`、`src/core/update/data_package.py`、`src/core/update/inspector.py`

### `write_queue`

写入：`src/core/storage/write_queue.py`

读取：`src/core/storage/write_queue.py`
