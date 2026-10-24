# 运行时探测（真启动引擎，176 条端点实测）

> **由 `scripts/survey/03-render.py` 从 `data/*.json` 生成，勿手改。**
> 数字与 JSON 一一对应；要改数字请重跑生成器。

## 一、这是唯一真正跑起来的一层

前面 17 份文档全是**静态**的：看代码写了什么。
这一份是**真启动引擎、把每条端点都调了一遍** —— 静态检查验不了「跑起来会怎样」。

## 二、隔离边界（保证没碰生产数据）

| 项 | 值 |
|---|---|
| 数据目录 | 临时目录（种子库副本，13 MB） |
| 模型目录 | 临时空目录（模型不可用 ⇒ 降级） |
| 说明 | **绝不碰 var/data**；临时目录用完即删 |

每条端点用**空 body**（`{}`）探测；`422`/`400` 是**正常结果**（说明它要必填字段），不是失败。会触发云模型的端点在没有密钥时会失败 —— 如实记录。**只记实际返回了什么，不判断该返回什么。**路径里的 `{xxx}` 占位符统一替换成 `probe-nonexistent`。

## 三、总账

| 项 | 数 |
|---|---:|
| 探测端点 | **176** |
| 超时（12 秒） | 71 |
| 200 正常 | 37 |
| 422 缺必填字段（正常） | 36 |
| 404 占位 id 不存在（合理） | 29 |
| 400 | 1 |
| 409 冲突 | 1 |
| **500 未捕获异常** | 1 |

> ⚠ `422` 与 `404` 是**空 body + 占位 id** 的正常结果，不是缺陷。
> 真正的异常是 `500` 与 `timeout` —— 见 §五。

## 四、`/api/v1/health` 的真实响应

- HTTP **200**，**19.4 ms**，103 字节
- 顶层键：`db_status`, `parser_worker`, `status`, `uptime_seconds`, `vector_engine`

## 五、异常项逐条（**只记录，不判断**）

### 500（未捕获异常）

- `POST /api/v1/ingest/bulk/{batch_id}/resume` —— `bulk_ingest_resume` @ `src/core/api/routes_update.py:576`

### 超时的端点（按路径前缀归组）

| 前缀 | 超时条数 |
|---|---:|
| `/api/v1/documents` | 14 |
| `/api/v1/clauses` | 11 |
| `/api/v1/bookmark-folders` | 7 |
| `/api/v1/bookmarks` | 4 |
| `/api/v1/doc-bookmarks` | 4 |
| `/api/v1/projects` | 4 |
| `/api/v1/data` | 3 |
| `/api/v1/annotations` | 3 |
| `/api/v1/compliance` | 3 |
| `/api/v1/snapshots` | 3 |
| `/api/v1/export` | 2 |
| `/api/v1/egress` | 2 |
| `/api/v1/diagnostics` | 2 |
| `/api/v1/laws` | 1 |
| `/api/v1/ingest` | 1 |
| `/api/v1/health` | 1 |
| `/api/v1/compare` | 1 |
| `/api/v1/operation-log` | 1 |
| `/api/v1/aliases` | 1 |
| `/api/v1/chat` | 1 |
| `/api/v1/ks` | 1 |
| `/api/v1/vision` | 1 |

### 超时的 71 条：按**这一个 handler 的函数体**粗分

| handler 里碰到什么 | 条数 |
|---|---:|
| **handler 里看不出明确来源** | 41 |
| 查数据库 | 12 |
| 重入库/解析 + 查数据库 | 7 |
| 等云模型 | 3 |
| 重入库/解析 | 2 |
| 等云模型 + 查数据库 | 2 |
| 等云模型 + 重入库/解析 | 1 |
| 联网 | 1 |
| 等云模型 + 联网 | 1 |
| 等云模型 + 重入库/解析 + 查数据库 | 1 |

> ⚠ 这是**按关键词粗分**：只扫该 handler 自己的函数体（不含同文件其它函数），看有没有模型/联网/入库/数据库字样。
> **不能证明超时就是因为那个**；要定因得在超时时抓线程栈。**本检查没做。**

**⚠ 这一栏最重要的读数是第一行**：大多数超时的 handler **本身看不出会慢**
（没有模型、没有联网、没有重入库）。而它们在第 1 次跑里是**连续 70 条**
一起超时的（第 107–176 条）⇒ 更可能是**整体被卡住**，不是各自慢。
与 [`10-observed.md`](10-observed.md) §七 O-22 的间歇性卡死对应着看。

**逐条明细**（前 30 条）：

| 端点 | handler | 函数体行数 | 命中 |
|---|---|---:|---|
| `/api/v1/laws/catalog/refresh` | `law_catalog_refresh` | 10 | — |
| `/api/v1/ingest/bulk/{batch_id}/abort` | `bulk_ingest_abort` | 11 | 重入库/解析 |
| `/api/v1/data/package/export` | `data_package_export` | 15 | — |
| `/api/v1/data/package/import` | `data_package_import` | 15 | — |
| `/api/v1/health` | `health` | 22 | 重入库/解析、查数据库 |
| `/api/v1/clauses/patches` | `create_patch` | 52 | 查数据库 |
| `/api/v1/clauses/resolve` | `resolve_clause` | 59 | 等云模型 |
| `/api/v1/data/quality-issues` | `data_quality_issues` | 43 | 重入库/解析、查数据库 |
| `/api/v1/clauses/patches` | `get_patches` | 5 | — |
| `/api/v1/clauses/patches/{patch_id}` | `remove_patch` | 16 | — |
| `/api/v1/documents/{doc_id}/file` | `get_document_file` | 22 | 查数据库 |
| `/api/v1/documents/{doc_id}/figure/{fig_no}` | `get_document_figure` | 153 | 重入库/解析、查数据库 |
| `/api/v1/documents/{doc_id}/formula/{fno}` | `get_document_formula` | 61 | 重入库/解析、查数据库 |
| `/api/v1/documents/{doc_id}/table-image/{page_no}/{tbl_idx}` | `get_document_table_image` | 60 | 重入库/解析、查数据库 |
| `/api/v1/documents` | `doc_list` | 16 | 查数据库 |
| `/api/v1/documents/categories` | `doc_categories` | 45 | 查数据库 |
| `/api/v1/documents/batch-delete` | `documents_batch_delete` | 22 | — |
| `/api/v1/documents/{doc_id}/tree` | `document_tree` | 256 | 重入库/解析、查数据库 |
| `/api/v1/bookmarks` | `get_bookmarks` | 4 | — |
| `/api/v1/bookmarks` | `add_bookmark` | 11 | — |
| `/api/v1/bookmarks/by-clause/{clause_key}` | `del_bookmark_by_clause` | 6 | — |
| `/api/v1/bookmarks/{bookmark_id}` | `del_bookmark` | 8 | — |
| `/api/v1/doc-bookmarks` | `get_doc_bookmarks` | 4 | — |
| `/api/v1/doc-bookmarks` | `add_doc_bookmark` | 11 | — |
| `/api/v1/doc-bookmarks/by-doc/{doc_id}` | `del_doc_bookmark_by_doc` | 6 | — |
| `/api/v1/doc-bookmarks/{doc_bookmark_id}` | `del_doc_bookmark` | 9 | — |
| `/api/v1/bookmark-folders` | `get_bookmark_folders` | 4 | — |
| `/api/v1/bookmark-folders` | `create_bookmark_folder` | 11 | — |
| `/api/v1/bookmark-folders/{folder_id}` | `rename_bookmark_folder` | 11 | — |
| `/api/v1/bookmark-folders/{folder_id}` | `delete_bookmark_folder` | 9 | — |

## 六、全部端点实测结果

| 方法 | 路径 | 状态 | 耗时 | 处理函数 |
|---|:---:|---:|---|
| GET | `/api/v1/channels` | 200 | 2.4 ms | `list_channels` |
| GET | `/api/v1/channels/{channel_id}` | 404 | 24.4 ms | `get_channel` |
| POST | `/api/v1/channels` | 422 | 15.1 ms | `create_channel` |
| PATCH | `/api/v1/channels/{channel_id}` | 422 | 16.0 ms | `update_channel` |
| POST | `/api/v1/channels/{channel_id}/enabled` | 422 | 1.9 ms | `set_channel_enabled` |
| DELETE | `/api/v1/channels/{channel_id}` | 404 | 1.3 ms | `remove_channel` |
| POST | `/api/v1/channels/{channel_id}/test-case` | 422 | 1.0 ms | `set_channel_test_case` |
| GET | `/api/v1/channels/{channel_id}/test-case` | 200 | 2.0 ms | `get_channel_test_case` |
| POST | `/api/v1/channels/{channel_id}/test` | 200 | 1.0 ms | `run_channel_test` |
| POST | `/api/v1/channels/probe` | 200 | 0.5 ms | `probe_channels` |
| POST | `/api/v1/ingest/preview` | 422 | 6.6 ms | `ingest_preview` |
| POST | `/api/v1/ingest/preview/batch` | 422 | 2.0 ms | `ingest_preview_batch` |
| GET | `/api/v1/ingest/preview/inbox` | 422 | 1.0 ms | `ingest_preview_inbox` |
| POST | `/api/v1/ingest/preview/jobs` | 422 | 2.0 ms | `ingest_preview_job_start` |
| GET | `/api/v1/ingest/preview/jobs/{job_id}` | 404 | 1.5 ms | `ingest_preview_job_status` |
| POST | `/api/v1/ingest/preview/jobs/{job_id}/abort` | 404 | 1.0 ms | `ingest_preview_job_abort` |
| GET | `/api/v1/kb/folders` | 200 | 187.3 ms | `kb_list_folders` |
| GET | `/api/v1/kb/folders/flat` | 200 | 55.6 ms | `kb_flat_folders` |
| GET | `/api/v1/kb/folders/{folder_id}/items` | 404 | 2.0 ms | `kb_folder_items` |
| POST | `/api/v1/kb/folders` | 422 | 1.5 ms | `kb_create_folder` |
| PUT | `/api/v1/kb/folders/{folder_id}` | 422 | 1.8 ms | `kb_rename_folder` |
| POST | `/api/v1/kb/folders/{folder_id}/move` | 404 | 1.0 ms | `kb_move_folder` |
| POST | `/api/v1/kb/folders/{folder_id}/copy` | 404 | 23.3 ms | `kb_copy_folder` |
| GET | `/api/v1/kb/folders/{folder_id}/delete-preview` | 404 | 1.5 ms | `kb_describe_delete` |
| DELETE | `/api/v1/kb/folders/{folder_id}` | 404 | 1.0 ms | `kb_delete_folder` |
| POST | `/api/v1/kb/members` | 422 | 2.0 ms | `kb_add_members` |
| POST | `/api/v1/kb/members/remove` | 422 | 2.0 ms | `kb_remove_members` |
| POST | `/api/v1/kb/members/move` | 422 | 1.5 ms | `kb_move_members` |
| POST | `/api/v1/kb/members/copy` | 422 | 2.0 ms | `kb_copy_members` |
| GET | `/api/v1/kb/inbox` | 200 | 7.6 ms | `kb_inbox` |
| GET | `/api/v1/kb/stage-labels` | 200 | 12.5 ms | `kb_stage_labels` |
| POST | `/api/v1/kb/inbox/reingest` | 422 | 2.0 ms | `kb_inbox_reingest` |
| GET | `/api/v1/kb/inbox/reingest/status` | 200 | 1.5 ms | `kb_inbox_reingest_status` |
| GET | `/api/v1/kb/ccs/summary` | 200 | 12.3 ms | `kb_ccs_summary` |
| GET | `/api/v1/kb/ccs/plan` | 200 | 15.3 ms | `kb_ccs_plan` |
| POST | `/api/v1/kb/ccs/backfill` | 200 | 47.6 ms | `kb_ccs_backfill` |
| GET | `/api/v1/kb/ccs/backfill/status` | 200 | 1.0 ms | `kb_ccs_backfill_status` |
| POST | `/api/v1/kb/ccs/backfill/cancel` | 200 | 2.5 ms | `kb_ccs_backfill_cancel` |
| POST | `/api/v1/kb/inbox/confirm` | 422 | 1.5 ms | `kb_inbox_confirm` |
| POST | `/api/v1/kb/scope/resolve` | 422 | 1.3 ms | `kb_scope_resolve` |
| GET | `/api/v1/laws/sources` | 200 | 1.0 ms | `law_sources` |
| POST | `/api/v1/laws/search` | 422 | 2.0 ms | `law_search` |
| POST | `/api/v1/laws/ingest` | 400 | 18.9 ms | `law_ingest` |
| POST | `/api/v1/laws/check-updates` | 200 | 2.0 ms | `law_check_updates` |
| GET | `/api/v1/laws/catalog` | 200 | 13.9 ms | `law_catalog` |
| POST | `/api/v1/laws/catalog/refresh` | 超时 | 12020.7 ms | `law_catalog_refresh` |
| GET | `/api/v1/laws/verify` | 422 | 2.0 ms | `law_verify` |
| GET | `/api/v1/laws/history` | 422 | 2.0 ms | `law_history` |
| GET | `/api/v1/laws/change-signals` | 200 | 15.0 ms | `law_change_signals` |
| POST | `/api/v1/laws/compliance-guard` | 422 | 2.3 ms | `compliance_guard` |
| POST | `/api/v1/materials/projects` | 422 | 2.0 ms | `materials_create_project` |
| GET | `/api/v1/materials/projects` | 200 | 1.0 ms | `materials_list_projects` |
| GET | `/api/v1/materials/projects/{project_id}/inbox` | 404 | 1.0 ms | `materials_inbox` |
| POST | `/api/v1/materials/projects/{project_id}/scan` | 404 | 2.0 ms | `materials_scan` |
| POST | `/api/v1/materials/projects/{project_id}/collect` | 404 | 1.0 ms | `materials_collect` |
| GET | `/api/v1/materials/projects/{project_id}/materials` | 404 | 1.0 ms | `materials_list` |
| GET | `/api/v1/materials/projects/{project_id}/search` | 404 | 19.3 ms | `materials_search` |
| GET | `/api/v1/materials/tiers` | 200 | 1.5 ms | `materials_tiers` |
| GET | `/api/v1/materials/{material_id}` | 404 | 1.0 ms | `materials_get` |
| GET | `/api/v1/materials/{material_id}/chunks` | 404 | 25.5 ms | `materials_chunks` |
| POST | `/api/v1/materials/{material_id}/review` | 422 | 15.3 ms | `materials_review` |
| POST | `/api/v1/materials/{material_id}/tier` | 422 | 2.0 ms | `materials_set_tier` |
| POST | `/api/v1/materials/{material_id}/role` | 404 | 2.0 ms | `materials_set_role` |
| POST | `/api/v1/materials/{material_id}/lifecycle` | 422 | 11.5 ms | `materials_set_lifecycle` |
| DELETE | `/api/v1/materials/{material_id}` | 404 | 15.2 ms | `materials_delete` |
| GET | `/api/v1/materials/projects/{project_id}/locators` | 404 | 1.0 ms | `materials_locator_summary` |
| GET | `/api/v1/materials/{material_id}/locators` | 404 | 14.2 ms | `materials_locator_health` |
| POST | `/api/v1/materials/{material_id}/reverify` | 404 | 1.5 ms | `materials_reverify_locators` |
| GET | `/api/v1/report/effect` | 200 | 3.1 ms | `effect_report` |
| GET | `/api/v1/report/effect/docs` | 422 | 1.0 ms | `effect_report_docs` |
| GET | `/api/v1/report/effect/color` | 422 | 24.1 ms | `effect_report_by_color` |
| POST | `/api/v1/report/effect/export` | 200 | 17.9 ms | `effect_report_export` |
| POST | `/api/v1/report/research` | 422 | 1.0 ms | `research_report` |
| POST | `/api/v1/report/research/draft` | 422 | 2.0 ms | `research_report_draft` |
| GET | `/api/v1/settings/api-config` | 200 | 2.0 ms | `api_config_get` |
| PUT | `/api/v1/settings/api-config` | 200 | 2.0 ms | `api_config_put` |
| POST | `/api/v1/settings/api-config/test` | 422 | 1.0 ms | `api_config_test` |
| POST | `/api/v1/update/check` | 409 | 2.0 ms | `update_check` |
| GET | `/api/v1/update/batch/{batch_id}` | 404 | 17.3 ms | `update_batch_progress` |
| POST | `/api/v1/update/batch/{batch_id}/pause` | 404 | 1.0 ms | `update_batch_pause` |
| POST | `/api/v1/update/batch/{batch_id}/resume` | 404 | 2.0 ms | `update_batch_resume` |
| GET | `/api/v1/update/batches` | 200 | 1.5 ms | `update_batches` |
| GET | `/api/v1/update/changes` | 200 | 1.5 ms | `update_changes` |
| POST | `/api/v1/update/changes/{change_id}/ack` | 404 | 2.0 ms | `update_change_ack` |
| POST | `/api/v1/update/changes/{change_id}/manual` | 422 | 1.0 ms | `update_change_manual` |
| POST | `/api/v1/update/report-xlsx/{batch_id}` | 404 | 23.1 ms | `update_report_xlsx` |
| POST | `/api/v1/update/announce-scan` | 200 | 61.9 ms | `announce_scan` |
| GET | `/api/v1/update/announce-scan/last` | 200 | 2.9 ms | `announce_scan_last` |
| GET | `/api/v1/update/announce-sources` | 200 | 13.3 ms | `announce_sources_list` |
| POST | `/api/v1/update/announce-sources` | 422 | 2.0 ms | `announce_sources_add` |
| PUT | `/api/v1/update/announce-sources/{source_id}` | 404 | 1.5 ms | `announce_sources_update` |
| DELETE | `/api/v1/update/announce-sources/{source_id}` | 404 | 11.9 ms | `announce_sources_remove` |
| GET | `/api/v1/update/announce-items` | 200 | 1.6 ms | `announce_items` |
| POST | `/api/v1/update/announce-export` | 200 | 6.7 ms | `announce_export` |
| GET | `/api/v1/update/announce-ingest/pending` | 200 | 8.1 ms | `announce_ingest_pending` |
| POST | `/api/v1/update/announce-ingest` | 200 | 2.6 ms | `announce_ingest` |
| GET | `/api/v1/update/announce-ingest/triage` | 200 | 1.5 ms | `announce_ingest_triage` |
| POST | `/api/v1/discover/classify` | 200 | 3.1 ms | `discover_classify` |
| POST | `/api/v1/discover/search` | 422 | 1.5 ms | `discover_search` |
| GET | `/api/v1/discover/watchlist` | 200 | 1.0 ms | `watchlist_get` |
| POST | `/api/v1/discover/watchlist` | 422 | 19.2 ms | `watchlist_post` |
| GET | `/api/v1/update/subscriptions` | 200 | 1.0 ms | `subscriptions_get` |
| PUT | `/api/v1/update/subscriptions` | 422 | 2.0 ms | `subscriptions_put` |
| POST | `/api/v1/ingest/bulk` | 422 | 36.7 ms | `bulk_ingest_start` |
| GET | `/api/v1/ingest/bulk/{batch_id}` | 404 | 2.0 ms | `bulk_ingest_status` |
| POST | `/api/v1/ingest/bulk/{batch_id}/resume` | 500 | 12004.0 ms | `bulk_ingest_resume` |
| POST | `/api/v1/ingest/bulk/{batch_id}/abort` | 超时 | 12010.7 ms | `bulk_ingest_abort` |
| POST | `/api/v1/data/package/export` | 超时 | 12002.7 ms | `data_package_export` |
| POST | `/api/v1/data/package/import` | 超时 | 12017.1 ms | `data_package_import` |
| GET | `/api/v1/health` | 超时 | 12016.1 ms | `health` |
| POST | `/api/v1/clauses/patches` | 超时 | 12003.0 ms | `create_patch` |
| GET | `/api/v1/clauses/resolve` | 超时 | 12029.0 ms | `resolve_clause` |
| GET | `/api/v1/data/quality-issues` | 超时 | 12015.6 ms | `data_quality_issues` |
| GET | `/api/v1/clauses/patches` | 超时 | 12005.6 ms | `get_patches` |
| DELETE | `/api/v1/clauses/patches/{patch_id}` | 超时 | 12014.6 ms | `remove_patch` |
| GET | `/api/v1/documents/{doc_id}/file` | 超时 | 12007.2 ms | `get_document_file` |
| GET | `/api/v1/documents/{doc_id}/figure/{fig_no}` | 超时 | 12006.4 ms | `get_document_figure` |
| GET | `/api/v1/documents/{doc_id}/formula/{fno}` | 超时 | 12020.3 ms | `get_document_formula` |
| GET | `/api/v1/documents/{doc_id}/table-image/{page_no}/{tbl_idx}` | 超时 | 12011.6 ms | `get_document_table_image` |
| GET | `/api/v1/documents` | 超时 | 12023.7 ms | `doc_list` |
| GET | `/api/v1/documents/categories` | 超时 | 12011.0 ms | `doc_categories` |
| POST | `/api/v1/documents/batch-delete` | 超时 | 12003.2 ms | `documents_batch_delete` |
| GET | `/api/v1/documents/{doc_id}/tree` | 超时 | 12014.1 ms | `document_tree` |
| GET | `/api/v1/bookmarks` | 超时 | 12000.2 ms | `get_bookmarks` |
| POST | `/api/v1/bookmarks` | 超时 | 12022.0 ms | `add_bookmark` |
| DELETE | `/api/v1/bookmarks/by-clause/{clause_key}` | 超时 | 12004.4 ms | `del_bookmark_by_clause` |
| DELETE | `/api/v1/bookmarks/{bookmark_id}` | 超时 | 12010.9 ms | `del_bookmark` |
| GET | `/api/v1/doc-bookmarks` | 超时 | 12015.6 ms | `get_doc_bookmarks` |
| POST | `/api/v1/doc-bookmarks` | 超时 | 12008.8 ms | `add_doc_bookmark` |
| DELETE | `/api/v1/doc-bookmarks/by-doc/{doc_id}` | 超时 | 12014.0 ms | `del_doc_bookmark_by_doc` |
| DELETE | `/api/v1/doc-bookmarks/{doc_bookmark_id}` | 超时 | 12002.2 ms | `del_doc_bookmark` |
| GET | `/api/v1/bookmark-folders` | 超时 | 12008.6 ms | `get_bookmark_folders` |
| POST | `/api/v1/bookmark-folders` | 超时 | 12005.8 ms | `create_bookmark_folder` |
| PUT | `/api/v1/bookmark-folders/{folder_id}` | 超时 | 12025.6 ms | `rename_bookmark_folder` |
| DELETE | `/api/v1/bookmark-folders/{folder_id}` | 超时 | 12005.3 ms | `delete_bookmark_folder` |
| POST | `/api/v1/bookmark-folders/move-clause` | 超时 | 12010.6 ms | `move_clause_bookmark` |
| POST | `/api/v1/bookmark-folders/move-doc` | 超时 | 12004.1 ms | `move_doc_bookmark` |
| GET | `/api/v1/bookmark-folders/tree` | 超时 | 12002.3 ms | `bookmark_folders_tree` |
| GET | `/api/v1/annotations` | 超时 | 12017.2 ms | `get_annotations` |
| POST | `/api/v1/annotations` | 超时 | 12029.2 ms | `add_annotation` |
| DELETE | `/api/v1/annotations/{annotation_id}` | 超时 | 12011.6 ms | `del_annotation` |
| GET | `/api/v1/projects` | 超时 | 12011.5 ms | `get_projects` |
| POST | `/api/v1/projects` | 超时 | 12001.0 ms | `create_project` |
| POST | `/api/v1/projects/{project_id}/clauses` | 超时 | 12014.1 ms | `project_add_clause` |
| DELETE | `/api/v1/projects/{project_id}/clauses/{clause_revision_id}` | 超时 | 12000.1 ms | `project_remove_clause` |
| POST | `/api/v1/compliance/policies` | 超时 | 12004.4 ms | `import_policy` |
| GET | `/api/v1/compliance/policies` | 超时 | 12019.3 ms | `list_policies` |
| POST | `/api/v1/compliance/gap-analysis` | 超时 | 12014.8 ms | `run_gap` |
| GET | `/api/v1/documents/{doc_id}/versions` | 超时 | 12014.6 ms | `doc_versions` |
| GET | `/api/v1/documents/{doc_id}/clauses-by-prefix` | 超时 | 12002.4 ms | `clauses_by_prefix` |
| GET | `/api/v1/documents/{doc_id}/clauses` | 超时 | 12026.3 ms | `doc_full_clauses` |
| GET | `/api/v1/documents/{doc_id}/assets/{fname}` | 超时 | 12013.9 ms | `doc_asset` |
| POST | `/api/v1/compare` | 超时 | 12007.2 ms | `compare_docs_endpoint` |
| GET | `/api/v1/operation-log` | 超时 | 12007.3 ms | `operation_log` |
| POST | `/api/v1/aliases/extract` | 超时 | 12000.8 ms | `aliases_extract` |
| POST | `/api/v1/export/citations` | 超时 | 12015.6 ms | `export_citations` |
| GET | `/api/v1/export/download` | 超时 | 12010.3 ms | `download_export` |
| POST | `/api/v1/chat/completions` | 超时 | 12004.1 ms | `chat_completions` |
| POST | `/api/v1/ks/answer` | 超时 | 12006.8 ms | `ks_answer_endpoint` |
| GET | `/api/v1/egress/audit` | 超时 | 12005.4 ms | `egress_audit` |
| GET | `/api/v1/egress/audit/export` | 超时 | 12001.2 ms | `egress_audit_export` |
| POST | `/api/v1/documents/{old_doc_id}/migrate-patches` | 超时 | 12016.3 ms | `migrate_patches_api` |
| POST | `/api/v1/clauses/{clause_revision_id}/office-edit` | 超时 | 12007.0 ms | `office_edit_start` |
| GET | `/api/v1/clauses/office-edit/poll` | 超时 | 12004.3 ms | `office_edit_poll` |
| POST | `/api/v1/clauses/office-edit/commit` | 超时 | 12013.3 ms | `office_edit_commit` |
| DELETE | `/api/v1/clauses/office-edit/{session_id}` | 超时 | 12005.4 ms | `office_edit_cancel` |
| GET | `/api/v1/clauses/{clause_revision_id}/backlinks` | 超时 | 12014.3 ms | `clause_backlinks` |
| GET | `/api/v1/clauses/{clause_revision_id}/spans` | 超时 | 12026.5 ms | `clause_spans` |
| GET | `/api/v1/clauses/{clause_revision_id}/meta` | 超时 | 12008.9 ms | `clause_meta` |
| POST | `/api/v1/vision/locate` | 超时 | 12009.1 ms | `vision_locate` |
| POST | `/api/v1/snapshots` | 超时 | 12004.6 ms | `create_snapshot` |
| GET | `/api/v1/snapshots` | 超时 | 12007.6 ms | `list_snapshots` |
| POST | `/api/v1/snapshots/{snapshot_id}/restore` | 超时 | 12008.5 ms | `restore_snapshot` |
| POST | `/api/v1/documents/impact` | 超时 | 12007.6 ms | `impact_analysis` |
| GET | `/api/v1/diagnostics/health-board` | 超时 | 12003.3 ms | `health_board` |
| GET | `/api/v1/diagnostics/debug-dumps` | 超时 | 12025.9 ms | `debug_dumps` |