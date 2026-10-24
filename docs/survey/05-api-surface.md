# 接口面（后端 + 前端路由）

> **由 `scripts/survey/03-render.py` 从 `data/*.json` 生成，勿手改。**
> 数字与 JSON 一一对应；要改数字请重跑生成器。

## 一、口径

后端 = `src/core/api/*.py` 里的 `@app.verb("path")` 装饰器，**逐条列出，不抽样**。前端 = `plugin/client/*.ts(x)` 里 `register({...path...})` 的路由注册。

## 二、总账

| 项 | 条 |
|---|---:|
| 后端路由 | **176** |
| 后端文件 | 9 |
| 前端路由注册 | **37** |

## 三、后端：按文件分布

| 文件 | 端点 |
|---|---:|
| `src/core/api/server.py` | 67 |
| `src/core/api/routes_update.py` | 32 |
| `src/core/api/routes_kb_folders.py` | 24 |
| `src/core/api/routes_materials.py` | 18 |
| `src/core/api/routes_channels.py` | 10 |
| `src/core/api/routes_law.py` | 10 |
| `src/core/api/routes_ingest_preview.py` | 6 |
| `src/core/api/routes_report.py` | 6 |
| `src/core/api/routes_settings.py` | 3 |

## 四、后端：全部端点（**逐条，不抽样**）

| 方法 | 路径 | 处理函数 | 位置 |
|---|:---|:---|
| POST | `/api/v1/aliases/extract` | `aliases_extract` | `src/core/api/server.py:1693` |
| GET | `/api/v1/annotations` | `get_annotations` | `src/core/api/server.py:1434` |
| POST | `/api/v1/annotations` | `add_annotation` | `src/core/api/server.py:1439` |
| DELETE | `/api/v1/annotations/{annotation_id}` | `del_annotation` | `src/core/api/server.py:1451` |
| GET | `/api/v1/bookmark-folders` | `get_bookmark_folders` | `src/core/api/server.py:1251` |
| POST | `/api/v1/bookmark-folders` | `create_bookmark_folder` | `src/core/api/server.py:1256` |
| POST | `/api/v1/bookmark-folders/move-clause` | `move_clause_bookmark` | `src/core/api/server.py:1290` |
| POST | `/api/v1/bookmark-folders/move-doc` | `move_doc_bookmark` | `src/core/api/server.py:1304` |
| GET | `/api/v1/bookmark-folders/tree` | `bookmark_folders_tree` | `src/core/api/server.py:1318` |
| DELETE | `/api/v1/bookmark-folders/{folder_id}` | `delete_bookmark_folder` | `src/core/api/server.py:1280` |
| PUT | `/api/v1/bookmark-folders/{folder_id}` | `rename_bookmark_folder` | `src/core/api/server.py:1268` |
| GET | `/api/v1/bookmarks` | `get_bookmarks` | `src/core/api/server.py:1184` |
| POST | `/api/v1/bookmarks` | `add_bookmark` | `src/core/api/server.py:1189` |
| DELETE | `/api/v1/bookmarks/by-clause/{clause_key}` | `del_bookmark_by_clause` | `src/core/api/server.py:1201` |
| DELETE | `/api/v1/bookmarks/{bookmark_id}` | `del_bookmark` | `src/core/api/server.py:1208` |
| GET | `/api/v1/channels` | `list_channels` | `src/core/api/routes_channels.py:69` |
| POST | `/api/v1/channels` | `create_channel` | `src/core/api/routes_channels.py:122` |
| POST | `/api/v1/channels/probe` | `probe_channels` | `src/core/api/routes_channels.py:237` |
| DELETE | `/api/v1/channels/{channel_id}` | `remove_channel` | `src/core/api/routes_channels.py:190` |
| GET | `/api/v1/channels/{channel_id}` | `get_channel` | `src/core/api/routes_channels.py:112` |
| PATCH | `/api/v1/channels/{channel_id}` | `update_channel` | `src/core/api/routes_channels.py:154` |
| POST | `/api/v1/channels/{channel_id}/enabled` | `set_channel_enabled` | `src/core/api/routes_channels.py:178` |
| POST | `/api/v1/channels/{channel_id}/test` | `run_channel_test` | `src/core/api/routes_channels.py:228` |
| GET | `/api/v1/channels/{channel_id}/test-case` | `get_channel_test_case` | `src/core/api/routes_channels.py:221` |
| POST | `/api/v1/channels/{channel_id}/test-case` | `set_channel_test_case` | `src/core/api/routes_channels.py:203` |
| POST | `/api/v1/chat/completions` | `chat_completions` | `src/core/api/server.py:1764` |
| POST | `/api/v1/clauses/office-edit/commit` | `office_edit_commit` | `src/core/api/server.py:2292` |
| GET | `/api/v1/clauses/office-edit/poll` | `office_edit_poll` | `src/core/api/server.py:2281` |
| DELETE | `/api/v1/clauses/office-edit/{session_id}` | `office_edit_cancel` | `src/core/api/server.py:2303` |
| GET | `/api/v1/clauses/patches` | `get_patches` | `src/core/api/server.py:518` |
| POST | `/api/v1/clauses/patches` | `create_patch` | `src/core/api/server.py:361` |
| DELETE | `/api/v1/clauses/patches/{patch_id}` | `remove_patch` | `src/core/api/server.py:524` |
| GET | `/api/v1/clauses/resolve` | `resolve_clause` | `src/core/api/server.py:414` |
| GET | `/api/v1/clauses/{clause_revision_id}/backlinks` | `clause_backlinks` | `src/core/api/server.py:2312` |
| GET | `/api/v1/clauses/{clause_revision_id}/meta` | `clause_meta` | `src/core/api/server.py:2365` |
| POST | `/api/v1/clauses/{clause_revision_id}/office-edit` | `office_edit_start` | `src/core/api/server.py:2265` |
| GET | `/api/v1/clauses/{clause_revision_id}/spans` | `clause_spans` | `src/core/api/server.py:2324` |
| POST | `/api/v1/compare` | `compare_docs_endpoint` | `src/core/api/server.py:1661` |
| POST | `/api/v1/compliance/gap-analysis` | `run_gap` | `src/core/api/server.py:1506` |
| GET | `/api/v1/compliance/policies` | `list_policies` | `src/core/api/server.py:1498` |
| POST | `/api/v1/compliance/policies` | `import_policy` | `src/core/api/server.py:1491` |
| POST | `/api/v1/data/package/export` | `data_package_export` | `src/core/api/routes_update.py:613` |
| POST | `/api/v1/data/package/import` | `data_package_import` | `src/core/api/routes_update.py:629` |
| GET | `/api/v1/data/quality-issues` | `data_quality_issues` | `src/core/api/server.py:474` |
| GET | `/api/v1/diagnostics/debug-dumps` | `debug_dumps` | `src/core/api/server.py:2512` |
| GET | `/api/v1/diagnostics/health-board` | `health_board` | `src/core/api/server.py:2463` |
| POST | `/api/v1/discover/classify` | `discover_classify` | `src/core/api/routes_update.py:402` |
| POST | `/api/v1/discover/search` | `discover_search` | `src/core/api/routes_update.py:410` |
| GET | `/api/v1/discover/watchlist` | `watchlist_get` | `src/core/api/routes_update.py:436` |
| POST | `/api/v1/discover/watchlist` | `watchlist_post` | `src/core/api/routes_update.py:443` |
| GET | `/api/v1/doc-bookmarks` | `get_doc_bookmarks` | `src/core/api/server.py:1217` |
| POST | `/api/v1/doc-bookmarks` | `add_doc_bookmark` | `src/core/api/server.py:1222` |
| DELETE | `/api/v1/doc-bookmarks/by-doc/{doc_id}` | `del_doc_bookmark_by_doc` | `src/core/api/server.py:1234` |
| DELETE | `/api/v1/doc-bookmarks/{doc_bookmark_id}` | `del_doc_bookmark` | `src/core/api/server.py:1241` |
| GET | `/api/v1/documents` | `doc_list` | `src/core/api/server.py:841` |
| POST | `/api/v1/documents/batch-delete` | `documents_batch_delete` | `src/core/api/server.py:904` |
| GET | `/api/v1/documents/categories` | `doc_categories` | `src/core/api/server.py:858` |
| POST | `/api/v1/documents/impact` | `impact_analysis` | `src/core/api/server.py:2447` |
| GET | `/api/v1/documents/{doc_id}/assets/{fname}` | `doc_asset` | `src/core/api/server.py:1618` |
| GET | `/api/v1/documents/{doc_id}/clauses` | `doc_full_clauses` | `src/core/api/server.py:1544` |
| GET | `/api/v1/documents/{doc_id}/clauses-by-prefix` | `clauses_by_prefix` | `src/core/api/server.py:1526` |
| GET | `/api/v1/documents/{doc_id}/figure/{fig_no}` | `get_document_figure` | `src/core/api/server.py:564` |
| GET | `/api/v1/documents/{doc_id}/file` | `get_document_file` | `src/core/api/server.py:541` |
| GET | `/api/v1/documents/{doc_id}/formula/{fno}` | `get_document_formula` | `src/core/api/server.py:718` |
| GET | `/api/v1/documents/{doc_id}/table-image/{page_no}/{tbl_idx}` | `get_document_table_image` | `src/core/api/server.py:780` |
| GET | `/api/v1/documents/{doc_id}/tree` | `document_tree` | `src/core/api/server.py:927` |
| GET | `/api/v1/documents/{doc_id}/versions` | `doc_versions` | `src/core/api/server.py:1516` |
| POST | `/api/v1/documents/{old_doc_id}/migrate-patches` | `migrate_patches_api` | `src/core/api/server.py:2252` |
| GET | `/api/v1/egress/audit` | `egress_audit` | `src/core/api/server.py:2235` |
| GET | `/api/v1/egress/audit/export` | `egress_audit_export` | `src/core/api/server.py:2242` |
| POST | `/api/v1/export/citations` | `export_citations` | `src/core/api/server.py:1721` |
| GET | `/api/v1/export/download` | `download_export` | `src/core/api/server.py:1752` |
| GET | `/api/v1/health` | `health` | `src/core/api/server.py:338` |
| POST | `/api/v1/ingest/bulk` | `bulk_ingest_start` | `src/core/api/routes_update.py:504` |
| GET | `/api/v1/ingest/bulk/{batch_id}` | `bulk_ingest_status` | `src/core/api/routes_update.py:544` |
| POST | `/api/v1/ingest/bulk/{batch_id}/abort` | `bulk_ingest_abort` | `src/core/api/routes_update.py:601` |
| POST | `/api/v1/ingest/bulk/{batch_id}/resume` | `bulk_ingest_resume` | `src/core/api/routes_update.py:576` |
| POST | `/api/v1/ingest/preview` | `ingest_preview` | `src/core/api/routes_ingest_preview.py:59` |
| POST | `/api/v1/ingest/preview/batch` | `ingest_preview_batch` | `src/core/api/routes_ingest_preview.py:91` |
| GET | `/api/v1/ingest/preview/inbox` | `ingest_preview_inbox` | `src/core/api/routes_ingest_preview.py:138` |
| POST | `/api/v1/ingest/preview/jobs` | `ingest_preview_job_start` | `src/core/api/routes_ingest_preview.py:162` |
| GET | `/api/v1/ingest/preview/jobs/{job_id}` | `ingest_preview_job_status` | `src/core/api/routes_ingest_preview.py:205` |
| POST | `/api/v1/ingest/preview/jobs/{job_id}/abort` | `ingest_preview_job_abort` | `src/core/api/routes_ingest_preview.py:219` |
| POST | `/api/v1/kb/ccs/backfill` | `kb_ccs_backfill` | `src/core/api/routes_kb_folders.py:562` |
| POST | `/api/v1/kb/ccs/backfill/cancel` | `kb_ccs_backfill_cancel` | `src/core/api/routes_kb_folders.py:630` |
| GET | `/api/v1/kb/ccs/backfill/status` | `kb_ccs_backfill_status` | `src/core/api/routes_kb_folders.py:616` |
| GET | `/api/v1/kb/ccs/plan` | `kb_ccs_plan` | `src/core/api/routes_kb_folders.py:544` |
| GET | `/api/v1/kb/ccs/summary` | `kb_ccs_summary` | `src/core/api/routes_kb_folders.py:514` |
| GET | `/api/v1/kb/folders` | `kb_list_folders` | `src/core/api/routes_kb_folders.py:117` |
| POST | `/api/v1/kb/folders` | `kb_create_folder` | `src/core/api/routes_kb_folders.py:199` |
| GET | `/api/v1/kb/folders/flat` | `kb_flat_folders` | `src/core/api/routes_kb_folders.py:146` |
| DELETE | `/api/v1/kb/folders/{folder_id}` | `kb_delete_folder` | `src/core/api/routes_kb_folders.py:279` |
| PUT | `/api/v1/kb/folders/{folder_id}` | `kb_rename_folder` | `src/core/api/routes_kb_folders.py:218` |
| POST | `/api/v1/kb/folders/{folder_id}/copy` | `kb_copy_folder` | `src/core/api/routes_kb_folders.py:252` |
| GET | `/api/v1/kb/folders/{folder_id}/delete-preview` | `kb_describe_delete` | `src/core/api/routes_kb_folders.py:267` |
| GET | `/api/v1/kb/folders/{folder_id}/items` | `kb_folder_items` | `src/core/api/routes_kb_folders.py:170` |
| POST | `/api/v1/kb/folders/{folder_id}/move` | `kb_move_folder` | `src/core/api/routes_kb_folders.py:228` |
| GET | `/api/v1/kb/inbox` | `kb_inbox` | `src/core/api/routes_kb_folders.py:384` |
| POST | `/api/v1/kb/inbox/confirm` | `kb_inbox_confirm` | `src/core/api/routes_kb_folders.py:640` |
| POST | `/api/v1/kb/inbox/reingest` | `kb_inbox_reingest` | `src/core/api/routes_kb_folders.py:468` |
| GET | `/api/v1/kb/inbox/reingest/status` | `kb_inbox_reingest_status` | `src/core/api/routes_kb_folders.py:501` |
| POST | `/api/v1/kb/members` | `kb_add_members` | `src/core/api/routes_kb_folders.py:298` |
| POST | `/api/v1/kb/members/copy` | `kb_copy_members` | `src/core/api/routes_kb_folders.py:361` |
| POST | `/api/v1/kb/members/move` | `kb_move_members` | `src/core/api/routes_kb_folders.py:340` |
| POST | `/api/v1/kb/members/remove` | `kb_remove_members` | `src/core/api/routes_kb_folders.py:322` |
| POST | `/api/v1/kb/scope/resolve` | `kb_scope_resolve` | `src/core/api/routes_kb_folders.py:662` |
| GET | `/api/v1/kb/stage-labels` | `kb_stage_labels` | `src/core/api/routes_kb_folders.py:456` |
| POST | `/api/v1/ks/answer` | `ks_answer_endpoint` | `src/core/api/server.py:2202` |
| GET | `/api/v1/laws/catalog` | `law_catalog` | `src/core/api/routes_law.py:131` |
| POST | `/api/v1/laws/catalog/refresh` | `law_catalog_refresh` | `src/core/api/routes_law.py:150` |
| GET | `/api/v1/laws/change-signals` | `law_change_signals` | `src/core/api/routes_law.py:199` |
| POST | `/api/v1/laws/check-updates` | `law_check_updates` | `src/core/api/routes_law.py:122` |
| POST | `/api/v1/laws/compliance-guard` | `compliance_guard` | `src/core/api/routes_law.py:231` |
| GET | `/api/v1/laws/history` | `law_history` | `src/core/api/routes_law.py:173` |
| POST | `/api/v1/laws/ingest` | `law_ingest` | `src/core/api/routes_law.py:82` |
| POST | `/api/v1/laws/search` | `law_search` | `src/core/api/routes_law.py:44` |
| GET | `/api/v1/laws/sources` | `law_sources` | `src/core/api/routes_law.py:32` |
| GET | `/api/v1/laws/verify` | `law_verify` | `src/core/api/routes_law.py:161` |
| GET | `/api/v1/materials/projects` | `materials_list_projects` | `src/core/api/routes_materials.py:85` |
| POST | `/api/v1/materials/projects` | `materials_create_project` | `src/core/api/routes_materials.py:67` |
| POST | `/api/v1/materials/projects/{project_id}/collect` | `materials_collect` | `src/core/api/routes_materials.py:140` |
| GET | `/api/v1/materials/projects/{project_id}/inbox` | `materials_inbox` | `src/core/api/routes_materials.py:89` |
| GET | `/api/v1/materials/projects/{project_id}/locators` | `materials_locator_summary` | `src/core/api/routes_materials.py:337` |
| GET | `/api/v1/materials/projects/{project_id}/materials` | `materials_list` | `src/core/api/routes_materials.py:191` |
| POST | `/api/v1/materials/projects/{project_id}/scan` | `materials_scan` | `src/core/api/routes_materials.py:105` |
| GET | `/api/v1/materials/projects/{project_id}/search` | `materials_search` | `src/core/api/routes_materials.py:205` |
| GET | `/api/v1/materials/tiers` | `materials_tiers` | `src/core/api/routes_materials.py:222` |
| DELETE | `/api/v1/materials/{material_id}` | `materials_delete` | `src/core/api/routes_materials.py:330` |
| GET | `/api/v1/materials/{material_id}` | `materials_get` | `src/core/api/routes_materials.py:229` |
| GET | `/api/v1/materials/{material_id}/chunks` | `materials_chunks` | `src/core/api/routes_materials.py:239` |
| POST | `/api/v1/materials/{material_id}/lifecycle` | `materials_set_lifecycle` | `src/core/api/routes_materials.py:318` |
| GET | `/api/v1/materials/{material_id}/locators` | `materials_locator_health` | `src/core/api/routes_materials.py:357` |
| POST | `/api/v1/materials/{material_id}/reverify` | `materials_reverify_locators` | `src/core/api/routes_materials.py:370` |
| POST | `/api/v1/materials/{material_id}/review` | `materials_review` | `src/core/api/routes_materials.py:254` |
| POST | `/api/v1/materials/{material_id}/role` | `materials_set_role` | `src/core/api/routes_materials.py:305` |
| POST | `/api/v1/materials/{material_id}/tier` | `materials_set_tier` | `src/core/api/routes_materials.py:289` |
| GET | `/api/v1/operation-log` | `operation_log` | `src/core/api/server.py:1679` |
| GET | `/api/v1/projects` | `get_projects` | `src/core/api/server.py:1458` |
| POST | `/api/v1/projects` | `create_project` | `src/core/api/server.py:1463` |
| POST | `/api/v1/projects/{project_id}/clauses` | `project_add_clause` | `src/core/api/server.py:1470` |
| DELETE | `/api/v1/projects/{project_id}/clauses/{clause_revision_id}` | `project_remove_clause` | `src/core/api/server.py:1481` |
| GET | `/api/v1/report/effect` | `effect_report` | `src/core/api/routes_report.py:36` |
| GET | `/api/v1/report/effect/color` | `effect_report_by_color` | `src/core/api/routes_report.py:75` |
| GET | `/api/v1/report/effect/docs` | `effect_report_docs` | `src/core/api/routes_report.py:54` |
| POST | `/api/v1/report/effect/export` | `effect_report_export` | `src/core/api/routes_report.py:94` |
| POST | `/api/v1/report/research` | `research_report` | `src/core/api/routes_report.py:118` |
| POST | `/api/v1/report/research/draft` | `research_report_draft` | `src/core/api/routes_report.py:171` |
| GET | `/api/v1/settings/api-config` | `api_config_get` | `src/core/api/routes_settings.py:18` |
| PUT | `/api/v1/settings/api-config` | `api_config_put` | `src/core/api/routes_settings.py:32` |
| POST | `/api/v1/settings/api-config/test` | `api_config_test` | `src/core/api/routes_settings.py:66` |
| GET | `/api/v1/snapshots` | `list_snapshots` | `src/core/api/server.py:2431` |
| POST | `/api/v1/snapshots` | `create_snapshot` | `src/core/api/server.py:2424` |
| POST | `/api/v1/snapshots/{snapshot_id}/restore` | `restore_snapshot` | `src/core/api/server.py:2436` |
| POST | `/api/v1/update/announce-export` | `announce_export` | `src/core/api/routes_update.py:327` |
| POST | `/api/v1/update/announce-ingest` | `announce_ingest` | `src/core/api/routes_update.py:357` |
| GET | `/api/v1/update/announce-ingest/pending` | `announce_ingest_pending` | `src/core/api/routes_update.py:347` |
| GET | `/api/v1/update/announce-ingest/triage` | `announce_ingest_triage` | `src/core/api/routes_update.py:387` |
| GET | `/api/v1/update/announce-items` | `announce_items` | `src/core/api/routes_update.py:320` |
| POST | `/api/v1/update/announce-scan` | `announce_scan` | `src/core/api/routes_update.py:232` |
| GET | `/api/v1/update/announce-scan/last` | `announce_scan_last` | `src/core/api/routes_update.py:255` |
| GET | `/api/v1/update/announce-sources` | `announce_sources_list` | `src/core/api/routes_update.py:261` |
| POST | `/api/v1/update/announce-sources` | `announce_sources_add` | `src/core/api/routes_update.py:274` |
| DELETE | `/api/v1/update/announce-sources/{source_id}` | `announce_sources_remove` | `src/core/api/routes_update.py:308` |
| PUT | `/api/v1/update/announce-sources/{source_id}` | `announce_sources_update` | `src/core/api/routes_update.py:295` |
| GET | `/api/v1/update/batch/{batch_id}` | `update_batch_progress` | `src/core/api/routes_update.py:89` |
| POST | `/api/v1/update/batch/{batch_id}/pause` | `update_batch_pause` | `src/core/api/routes_update.py:107` |
| POST | `/api/v1/update/batch/{batch_id}/resume` | `update_batch_resume` | `src/core/api/routes_update.py:118` |
| GET | `/api/v1/update/batches` | `update_batches` | `src/core/api/routes_update.py:142` |
| GET | `/api/v1/update/changes` | `update_changes` | `src/core/api/routes_update.py:149` |
| POST | `/api/v1/update/changes/{change_id}/ack` | `update_change_ack` | `src/core/api/routes_update.py:171` |
| POST | `/api/v1/update/changes/{change_id}/manual` | `update_change_manual` | `src/core/api/routes_update.py:186` |
| POST | `/api/v1/update/check` | `update_check` | `src/core/api/routes_update.py:38` |
| POST | `/api/v1/update/report-xlsx/{batch_id}` | `update_report_xlsx` | `src/core/api/routes_update.py:209` |
| GET | `/api/v1/update/subscriptions` | `subscriptions_get` | `src/core/api/routes_update.py:473` |
| PUT | `/api/v1/update/subscriptions` | `subscriptions_put` | `src/core/api/routes_update.py:483` |
| POST | `/api/v1/vision/locate` | `vision_locate` | `src/core/api/server.py:2408` |

## 五、前端路由注册

| 路径 | kind | 常量已解析 | 位置 |
|---|:--:|:--:|---|
| `/ks/announce/summary` | exact | ✓ | `plugin/src/announce.js:557` |
| `/ks/announce/scan` | exact | ✓ | `plugin/src/announce.js:579` |
| `/ks/announce/sources` | exact | ✓ | `plugin/src/announce.js:646` |
| `/ks/announce/sources` | prefix | ✓ | `plugin/src/announce.js:668` |
| `/ks/announce/export` | exact | ✓ | `plugin/src/announce.js:711` |
| `/ks/announce/ingest/pending` | exact | ✓ | `plugin/src/announce.js:821` |
| `/ks/announce/ingest` | exact | ✓ | `plugin/src/announce.js:832` |
| `/ks/announce/ingest/triage` | exact | ✓ | `plugin/src/announce.js:853` |
| `/ks/announce/change-signals` | exact | ✓ | `plugin/src/announce.js:864` |
| `/ks/announce/auto-ingest` | exact | ✓ | `plugin/src/announce.js:886` |
| `/ks/channels` | exact | ✓ | `plugin/src/channels.js:160` |
| `/ks/channels/probe` | exact | ✓ | `plugin/src/channels.js:209` |
| `/ks/channels` | prefix | ✓ | `plugin/src/channels.js:267` |
| `/ks/chat-mode` | exact | ✓ | `plugin/src/chatmode.js:1312` |
| `/ks/compliance/ping` | exact | ✗（写的是变量名） | `plugin/src/compliance-sentry.js:176` |
| `/ks/doc-image` | prefix | ✓ | `plugin/src/docimage.js:84` |
| `/ks/session` | exact | ✓ | `plugin/src/index.js:1464` |
| `/ks/bbox` | exact | ✓ | `plugin/src/index.js:1504` |
| `/ks/assets/pdf-wasm` | prefix | ✓ | `plugin/src/index.js:1603` |
| `/ks/assets/pdf.worker.min.mjs` | exact | ✓ | `plugin/src/index.js:1666` |
| `/ks/ingest/inbox-default` | exact | ✓ | `plugin/src/ingest.js:176` |
| `/ks/ingest/inbox` | exact | ✓ | `plugin/src/ingest.js:196` |
| `/ks/ingest/preview` | exact | ✓ | `plugin/src/ingest.js:236` |
| `/ks/ingest/preview/batch` | exact | ✓ | `plugin/src/ingest.js:279` |
| `/ks/ingest/preview/jobs` | prefix | ✓ | `plugin/src/ingest.js:697` |
| `/ks/inspection/run` | exact | ✓ | `plugin/src/inspection.js:695` |
| `/ks/inspection/summary` | exact | ✓ | `plugin/src/inspection.js:714` |
| `/ks/inspection/export` | exact | ✓ | `plugin/src/inspection.js:774` |
| `/ks/inspection/settings` | exact | ✓ | `plugin/src/inspection.js:842` |
| `/ks/report/effect` | exact | ✓ | `plugin/src/report.js:103` |
| `/ks/report/effect/docs` | exact | ✓ | `plugin/src/report.js:126` |
| `/ks/report/export` | exact | ✓ | `plugin/src/report.js:150` |
| `/ks/report/research` | exact | ✓ | `plugin/src/report.js:233` |
| `/ks/report/research/draft` | exact | ✓ | `plugin/src/report.js:290` |
| `/ks/settings/api-config` | exact | ✓ | `plugin/src/settings.js:152` |
| `/ks/settings/api-config/test` | exact | ✓ | `plugin/src/settings.js:202` |
| `/ks/turn/last` | exact | ✓ | `plugin/src/turn.js:42` |