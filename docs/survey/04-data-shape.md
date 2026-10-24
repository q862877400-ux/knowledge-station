# 数据形状（表 / 列 / 索引）

> **由 `scripts/survey/03-render.py` 从 `data/*.json` 生成，勿手改。**
> 数字与 JSON 一一对应；要改数字请重跑生成器。

## 一、来源与口径

- 反射来源：`tests\fixtures\seed\knowledge-seed.db`（**随仓的种子库**，不是生产库）
- 口径说明：本仓的 schema 定义在 `schema.sql`（冻结），但**行数与真实形态**以随仓的种子库为准 —— 种子库是生产库的真子集（含全部表结构）。用种子库反射而不是读 `.sql`，是因为 `.sql` 可能与实际库漂移。

## 二、总账

| 项 | 数 |
|---|---:|
| 表 | **59** |
| 列 | **470** |
| 索引 | 42 |
| 触发器 | 0 |
| 视图 | 0 |
| 种子库总行数 | 38,925 |

## 三、全部表（按种子库行数降序）

| 表 | 列 | 种子行数 | FTS |
|---|---:|---:|:--:|
| `source_span` | 6 | 16,198 |  |
| `clause_fts` | 8 | 4,809 |  |
| `clause_fts_content` | 9 | 4,809 |  |
| `clause_fts_docsize` | 2 | 4,809 |  |
| `clause_revision` | 38 | 4,809 |  |
| `folder` | 5 | 1,127 |  |
| `doc_page_geometry` | 7 | 892 |  |
| `clause_fts_data` | 2 | 354 |  |
| `clause_fts_idx` | 3 | 334 |  |
| `evidence_edge` | 7 | 286 |  |
| `clause_patch` | 8 | 152 |  |
| `doc_meta` | 30 | 82 |  |
| `review_point` | 11 | 79 |  |
| `gap_analysis` | 9 | 77 |  |
| `alias_store` | 7 | 32 |  |
| `review_task` | 15 | 22 |  |
| `doc_filing_state` | 11 | 21 |  |
| `obligation_list` | 5 | 12 |  |
| `snapshot_meta` | 6 | 8 |  |
| `app_config` | 4 | 7 |  |
| `doc_ccs_state` | 11 | 3 |  |
| `clause_fts_config` | 2 | 1 |  |
| `internal_policy` | 5 | 1 |  |
| `user_bookmark_folder` | 3 | 1 |  |
| `announcement_observed` | 12 | 0 |  |
| `audit_log` | 7 | 0 |  |
| `bulk_import_batch` | 15 | 0 |  |
| `channel_test_case` | 9 | 0 |  |
| `clause_vec_chunks` | 4 | 0 |  |
| `clause_vec_info` | 2 | 0 |  |
| `clause_vec_metadatachunks00` | 2 | 0 |  |
| `clause_vec_metadatatext00` | 2 | 0 |  |
| `clause_vec_rowids` | 4 | 0 |  |
| `clause_vec_vector_chunks00` | 2 | 0 |  |
| `debug_dump` | 10 | 0 |  |
| `event_log` | 9 | 0 |  |
| `feedback_log` | 6 | 0 |  |
| `folder_member` | 4 | 0 |  |
| `law_catalog` | 8 | 0 |  |
| `legal_obligation` | 4 | 0 |  |
| `material` | 26 | 0 |  |
| `material_chunk` | 8 | 0 |  |
| `material_fts_config` | 2 | 0 |  |
| `material_fts_content` | 5 | 0 |  |
| `material_fts_data` | 2 | 0 |  |
| `material_fts_docsize` | 2 | 0 |  |
| `material_fts_idx` | 3 | 0 |  |
| `material_project` | 6 | 0 |  |
| `operation_log` | 6 | 0 |  |
| `project_list` | 6 | 0 |  |
| `remapping_queue` | 8 | 0 |  |
| `update_change_event` | 13 | 0 |  |
| `update_channel` | 29 | 0 |  |
| `update_check_batch` | 12 | 0 |  |
| `user_annotation` | 6 | 0 |  |
| `user_bookmark` | 7 | 0 |  |
| `user_doc_bookmark` | 5 | 0 |  |
| `watch_list` | 3 | 0 |  |
| `write_queue` | 7 | 0 |  |

## 四、每张表的列（全集）

### `alias_store`（7 列 / 种子 32 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `alias_id` | TEXT |  |  | ✓ |
| `term` | TEXT | ✓ |  |  |
| `alias` | TEXT | ✓ |  |  |
| `source_type` | TEXT |  | 'auto_extract' |  |
| `source_doc_id` | TEXT |  |  |  |
| `confidence` | REAL |  | 1.0 |  |
| `status` | TEXT |  | 'active' |  |

### `announcement_observed`（12 列 / 种子 0 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `observed_id` | TEXT |  |  | ✓ |
| `source_id` | TEXT | ✓ |  |  |
| `source_name` | TEXT |  |  |  |
| `title` | TEXT | ✓ |  |  |
| `url` | TEXT | ✓ |  |  |
| `url_hash` | TEXT | ✓ |  |  |
| `standard_no` | TEXT |  |  |  |
| `published_date` | TEXT |  |  |  |
| `first_seen` | TEXT |  | datetime('now') |  |
| `last_seen` | TEXT |  | datetime('now') |  |
| `scan_id` | TEXT |  |  |  |
| `user_ack` | INTEGER |  | 0 |  |

### `app_config`（4 列 / 种子 7 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `config_key` | TEXT |  |  | ✓ |
| `config_value` | TEXT | ✓ |  |  |
| `is_encrypted` | INTEGER |  | 0 |  |
| `updated_at` | TEXT |  | datetime('now') |  |

### `audit_log`（7 列 / 种子 0 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `log_id` | INTEGER |  |  | ✓ |
| `event_type` | TEXT | ✓ |  |  |
| `user_action` | TEXT |  |  |  |
| `target_type` | TEXT |  |  |  |
| `target_id` | TEXT |  |  |  |
| `detail` | TEXT |  |  |  |
| `created_at` | TEXT |  | datetime('now') |  |

### `bulk_import_batch`（15 列 / 种子 0 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `batch_id` | TEXT |  |  | ✓ |
| `batch_kind` | TEXT |  |  |  |
| `trigger_type` | TEXT |  |  |  |
| `status` | TEXT |  | 'pending' |  |
| `total` | INTEGER |  | 0 |  |
| `checked` | INTEGER |  | 0 |  |
| `red_count` | INTEGER |  | 0 |  |
| `yellow_count` | INTEGER |  | 0 |  |
| `green_count` | INTEGER |  | 0 |  |
| `gray_count` | INTEGER |  | 0 |  |
| `tier` | TEXT |  | 'tier1' |  |
| `checkpoint_json` | TEXT |  |  |  |
| `started_at` | TEXT |  |  |  |
| `finished_at` | TEXT |  |  |  |
| `created_at` | TEXT |  | datetime('now') |  |

### `channel_test_case`（9 列 / 种子 0 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `channel_id` | TEXT |  |  | ✓ |
| `sample_url` | TEXT | ✓ |  |  |
| `expect_no` | TEXT | ✓ |  |  |
| `note` | TEXT |  |  |  |
| `last_result` | TEXT |  |  |  |
| `last_detail` | TEXT |  |  |  |
| `last_run_at` | TEXT |  |  |  |
| `created_at` | TEXT | ✓ | datetime('now') |  |
| `updated_at` | TEXT | ✓ | datetime('now') |  |

### `clause_fts`（8 列 / 种子 4,809 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `clause_revision_id` |  |  |  |  |
| `clause_number` |  |  |  |  |
| `standard_no` |  |  |  |  |
| `title` |  |  |  |  |
| `content_segmented` |  |  |  |  |
| `modality` |  |  |  |  |
| `subject` |  |  |  |  |
| `behavior_scope_segmented` |  |  |  |  |

### `clause_fts_config`（2 列 / 种子 1 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `k` |  | ✓ |  | ✓ |
| `v` |  |  |  |  |

### `clause_fts_content`（9 列 / 种子 4,809 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `id` | INTEGER |  |  | ✓ |
| `c0` |  |  |  |  |
| `c1` |  |  |  |  |
| `c2` |  |  |  |  |
| `c3` |  |  |  |  |
| `c4` |  |  |  |  |
| `c5` |  |  |  |  |
| `c6` |  |  |  |  |
| `c7` |  |  |  |  |

### `clause_fts_data`（2 列 / 种子 354 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `id` | INTEGER |  |  | ✓ |
| `block` | BLOB |  |  |  |

### `clause_fts_docsize`（2 列 / 种子 4,809 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `id` | INTEGER |  |  | ✓ |
| `sz` | BLOB |  |  |  |

### `clause_fts_idx`（3 列 / 种子 334 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `segid` |  | ✓ |  | ✓ |
| `term` |  | ✓ |  | ✓ |
| `pgno` |  |  |  |  |

### `clause_patch`（8 列 / 种子 152 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `patch_id` | TEXT |  |  | ✓ |
| `clause_revision_id` | TEXT | ✓ |  |  |
| `field_name` | TEXT | ✓ |  |  |
| `patched_value` | TEXT | ✓ |  |  |
| `patch_reason` | TEXT |  |  |  |
| `created_by` | TEXT | ✓ | 'local-user' |  |
| `created_at` | TEXT |  | datetime('now') |  |
| `updated_at` | TEXT |  | datetime('now') |  |

外键：`clause_revision_id` → `clause_revision.clause_revision_id`

### `clause_revision`（38 列 / 种子 4,809 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `clause_revision_id` | TEXT |  |  | ✓ |
| `doc_revision_id` | TEXT | ✓ |  |  |
| `doc_id` | TEXT | ✓ |  |  |
| `clause_key` | TEXT | ✓ |  |  |
| `clause_number` | TEXT | ✓ |  |  |
| `title` | TEXT |  |  |  |
| `content_text` | TEXT | ✓ |  |  |
| `content_markdown` | TEXT |  |  |  |
| `table_summary` | TEXT |  |  |  |
| `formula_number` | TEXT |  |  |  |
| `formula_desc` | TEXT |  |  |  |
| `image_text` | TEXT |  |  |  |
| `hierarchy_path` | TEXT |  |  |  |
| `knowledge_type` | TEXT |  | 'rule' |  |
| `type_confidence` | REAL |  | 1.0 |  |
| `modality` | TEXT |  |  |  |
| `modality_strength` | INTEGER |  |  |  |
| `modality_confidence` | REAL |  |  |  |
| `behavior_scope` | TEXT |  |  |  |
| `subject` | TEXT |  |  |  |
| `object` | TEXT |  |  |  |
| `behavior` | TEXT |  |  |  |
| `applicability_condition` | TEXT |  |  |  |
| `restriction` | TEXT |  |  |  |
| `exception` | TEXT |  |  |  |
| `legal_refs` | TEXT |  |  |  |
| `is_mandatory` | INTEGER |  | 0 |  |
| `is_suspicious` | INTEGER |  | 0 |  |
| `ocr_confidence` | REAL |  | 1.0 |  |
| `content_type` | TEXT |  | 'normal' |  |
| `page_start` | INTEGER | ✓ |  |  |
| `page_end` | INTEGER | ✓ |  |  |
| `cross_refs` | TEXT |  |  |  |
| `explanation_ref` | TEXT |  |  |  |
| `created_at` | TEXT |  | datetime('now') |  |
| `content_hash` | TEXT |  |  |  |
| `page_breaks` | TEXT |  |  |  |
| `figure_html` | TEXT |  |  |  |

外键：`doc_id` → `doc_meta.doc_id`

### `clause_vec_chunks`（4 列 / 种子 0 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `chunk_id` | INTEGER |  |  | ✓ |
| `size` | INTEGER | ✓ |  |  |
| `validity` | BLOB | ✓ |  |  |
| `rowids` | BLOB | ✓ |  |  |

### `clause_vec_info`（2 列 / 种子 0 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `key` | TEXT |  |  | ✓ |
| `value` | ANY |  |  |  |

### `clause_vec_metadatachunks00`（2 列 / 种子 0 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `rowid` |  |  |  | ✓ |
| `data` | BLOB | ✓ |  |  |

### `clause_vec_metadatatext00`（2 列 / 种子 0 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `rowid` |  |  |  | ✓ |
| `data` | TEXT |  |  |  |

### `clause_vec_rowids`（4 列 / 种子 0 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `rowid` | INTEGER |  |  | ✓ |
| `id` | TEXT | ✓ |  |  |
| `chunk_id` | INTEGER |  |  |  |
| `chunk_offset` | INTEGER |  |  |  |

### `clause_vec_vector_chunks00`（2 列 / 种子 0 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `rowid` |  |  |  | ✓ |
| `vectors` | BLOB | ✓ |  |  |

### `debug_dump`（10 列 / 种子 0 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `dump_id` | TEXT |  |  | ✓ |
| `trigger_type` | TEXT | ✓ |  |  |
| `query` | TEXT |  |  |  |
| `retrieval_result` | TEXT |  |  |  |
| `prompt` | TEXT |  |  |  |
| `llm_output` | TEXT |  |  |  |
| `claim_parsed` | TEXT |  |  |  |
| `verification_result` | TEXT |  |  |  |
| `logs` | TEXT |  |  |  |
| `created_at` | TEXT |  | datetime('now') |  |

### `doc_ccs_state`（11 列 / 种子 3 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `doc_id` | TEXT |  |  | ✓ |
| `outcome` | TEXT | ✓ |  |  |
| `source` | TEXT |  |  |  |
| `keyword_form` | TEXT |  |  |  |
| `matched_no` | TEXT |  |  |  |
| `ccs_code` | TEXT |  |  |  |
| `ccs_name` | TEXT |  |  |  |
| `reason` | TEXT |  |  |  |
| `attempts_json` | TEXT |  |  |  |
| `checked_at` | TEXT |  | datetime('now') |  |
| `applied_at` | TEXT |  |  |  |

### `doc_filing_state`（11 列 / 种子 21 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `doc_id` | TEXT |  |  | ✓ |
| `stage` | TEXT | ✓ | 'queued' |  |
| `confidence` | REAL |  |  |  |
| `failure_kind` | TEXT |  |  |  |
| `suggested_folder_id` | TEXT |  |  |  |
| `suggest_new_path` | TEXT |  |  |  |
| `placed_folder_id` | TEXT |  |  |  |
| `placed_by` | TEXT |  |  |  |
| `placed_at` | TEXT |  |  |  |
| `last_error` | TEXT |  |  |  |
| `updated_at` | TEXT |  | datetime('now') |  |

### `doc_meta`（30 列 / 种子 82 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `doc_id` | TEXT |  |  | ✓ |
| `standard_no` | TEXT | ✓ |  |  |
| `standard_name` | TEXT | ✓ |  |  |
| `short_code` | TEXT | ✓ |  |  |
| `current_revision_id` | TEXT | ✓ |  |  |
| `legal_status` | TEXT |  |  |  |
| `legal_hierarchy` | TEXT |  | 'GB' |  |
| `standard_type` | TEXT |  | 'mandatory' |  |
| `doc_type` | TEXT |  | 'standard' |  |
| `quality_grade` | TEXT |  | 'A' |  |
| `domain_tags` | TEXT | ✓ |  |  |
| `effective_from` | TEXT |  |  |  |
| `superseded_by` | TEXT |  |  |  |
| `normative_refs` | TEXT |  |  |  |
| `file_path` | TEXT | ✓ |  |  |
| `file_hash` | TEXT | ✓ |  |  |
| `created_at` | TEXT |  | datetime('now') |  |
| `updated_at` | TEXT |  | datetime('now') |  |
| `source` | TEXT |  |  |  |
| `source_id` | TEXT |  |  |  |
| `source_url` | TEXT |  |  |  |
| `downloaded_at` | TEXT |  |  |  |
| `source_status` | TEXT |  |  |  |
| `published_at` | TEXT |  |  |  |
| `ccs_code` | TEXT |  |  |  |
| `ccs_name` | TEXT |  |  |  |
| `ics` | TEXT |  |  |  |
| `withdrawn_date` | TEXT |  |  |  |
| `catalog_hidden` | INTEGER | ✓ | 0 |  |
| `change_signal` | TEXT |  |  |  |

### `doc_page_geometry`（7 列 / 种子 892 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `doc_id` | TEXT | ✓ |  | ✓ |
| `page_number` | INTEGER | ✓ |  | ✓ |
| `width` | REAL | ✓ |  |  |
| `height` | REAL | ✓ |  |  |
| `rotation` | INTEGER |  | 0 |  |
| `crop_box` | TEXT |  |  |  |
| `media_box` | TEXT |  |  |  |

外键：`doc_id` → `doc_meta.doc_id`

### `event_log`（9 列 / 种子 0 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `event_id` | TEXT |  |  | ✓ |
| `event_type` | TEXT | ✓ |  |  |
| `actor` | TEXT |  |  |  |
| `target_type` | TEXT |  |  |  |
| `target_id` | TEXT |  |  |  |
| `before_state` | TEXT |  |  |  |
| `after_state` | TEXT |  |  |  |
| `metadata` | TEXT |  |  |  |
| `created_at` | TEXT |  | datetime('now') |  |

### `evidence_edge`（7 列 / 种子 286 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `edge_id` | TEXT |  |  | ✓ |
| `edge_type` | TEXT | ✓ |  |  |
| `source_clause_id` | TEXT | ✓ |  |  |
| `target_clause_id` | TEXT | ✓ |  |  |
| `confidence` | REAL |  | 1.0 |  |
| `status` | TEXT |  | 'active' |  |
| `created_at` | TEXT |  | datetime('now') |  |

外键：`target_clause_id` → `clause_revision.clause_revision_id`、`source_clause_id` → `clause_revision.clause_revision_id`

### `feedback_log`（6 列 / 种子 0 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `feedback_id` | TEXT |  |  | ✓ |
| `clause_revision_ids` | TEXT |  |  |  |
| `feedback_type` | TEXT |  |  |  |
| `feedback_content` | TEXT |  |  |  |
| `rating` | INTEGER |  |  |  |
| `created_at` | TEXT |  | datetime('now') |  |

### `folder`（5 列 / 种子 1,127 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `folder_id` | TEXT |  |  | ✓ |
| `parent_id` | TEXT |  |  |  |
| `name` | TEXT | ✓ |  |  |
| `sort` | INTEGER |  | 0 |  |
| `created_at` | TEXT |  | datetime('now') |  |

### `folder_member`（4 列 / 种子 0 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `folder_id` | TEXT | ✓ |  | ✓ |
| `item_kind` | TEXT | ✓ |  | ✓ |
| `item_id` | TEXT | ✓ |  | ✓ |
| `added_at` | TEXT |  | datetime('now') |  |

### `gap_analysis`（9 列 / 种子 77 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `gap_id` | TEXT |  |  | ✓ |
| `task_id` | TEXT | ✓ |  |  |
| `legal_obligation_id` | TEXT | ✓ |  |  |
| `legal_obligation_text` | TEXT | ✓ |  |  |
| `internal_policy_section` | TEXT |  |  |  |
| `verdict` | TEXT |  |  |  |
| `gap_description` | TEXT |  |  |  |
| `remediation_suggestion` | TEXT |  |  |  |
| `created_at` | TEXT |  | datetime('now') |  |

外键：`task_id` → `review_task.task_id`

### `internal_policy`（5 列 / 种子 1 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `policy_id` | TEXT |  |  | ✓ |
| `policy_name` | TEXT | ✓ |  |  |
| `file_path` | TEXT | ✓ |  |  |
| `sections` | TEXT | ✓ |  |  |
| `created_at` | TEXT |  | datetime('now') |  |

### `law_catalog`（8 列 / 种子 0 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `title` | TEXT |  |  |  |
| `bbbs` | TEXT | ✓ |  |  |
| `flxz` | TEXT |  |  |  |
| `sxx` | INTEGER |  |  |  |
| `category` | TEXT |  |  |  |
| `gbrq` | TEXT |  |  |  |
| `sxrq` | TEXT |  |  |  |
| `updated_at` | TEXT |  | datetime('now') |  |

### `legal_obligation`（4 列 / 种子 0 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `obligation_id` | TEXT |  |  | ✓ |
| `clause_revision_id` | TEXT | ✓ |  |  |
| `obligation_text` | TEXT | ✓ |  |  |
| `domain_tag` | TEXT |  |  |  |

外键：`clause_revision_id` → `clause_revision.clause_revision_id`

### `material`（26 列 / 种子 0 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `material_id` | TEXT |  |  | ✓ |
| `project_id` | TEXT | ✓ |  |  |
| `origin` | TEXT | ✓ |  |  |
| `kind` | TEXT | ✓ | 'other' |  |
| `title` | TEXT | ✓ |  |  |
| `url` | TEXT |  |  |  |
| `domain` | TEXT |  |  |  |
| `fetched_at` | TEXT |  |  |  |
| `published_at` | TEXT |  |  |  |
| `content_hash` | TEXT |  |  |  |
| `raw_path` | TEXT |  |  |  |
| `mime` | TEXT |  |  |  |
| `source_tier` | TEXT | ✓ | 'T1' |  |
| `tier_source` | TEXT | ✓ | 'system' |  |
| `tier_reason` | TEXT |  |  |  |
| `tier_evidence` | TEXT |  |  |  |
| `task_role` | TEXT |  |  |  |
| `review_status` | TEXT | ✓ | 'pending' |  |
| `review_note` | TEXT |  |  |  |
| `reviewed_at` | TEXT |  |  |  |
| `lifecycle` | TEXT | ✓ | 'ephemeral' |  |
| `doc_id` | TEXT |  |  |  |
| `derived_text_hash` | TEXT |  |  |  |
| `parser_fingerprint` | TEXT |  |  |  |
| `created_at` | TEXT |  | datetime('now') |  |
| `updated_at` | TEXT |  | datetime('now') |  |

外键：`project_id` → `material_project.project_id`

### `material_chunk`（8 列 / 种子 0 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `chunk_id` | TEXT |  |  | ✓ |
| `material_id` | TEXT | ✓ |  |  |
| `ord` | INTEGER | ✓ |  |  |
| `text` | TEXT | ✓ |  |  |
| `char_start` | INTEGER | ✓ |  |  |
| `char_end` | INTEGER | ✓ |  |  |
| `page` | INTEGER |  |  |  |
| `created_at` | TEXT |  | datetime('now') |  |

外键：`material_id` → `material.material_id`

### `material_fts_config`（2 列 / 种子 0 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `k` |  | ✓ |  | ✓ |
| `v` |  |  |  |  |

### `material_fts_content`（5 列 / 种子 0 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `id` | INTEGER |  |  | ✓ |
| `c0` |  |  |  |  |
| `c1` |  |  |  |  |
| `c2` |  |  |  |  |
| `c3` |  |  |  |  |

### `material_fts_data`（2 列 / 种子 0 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `id` | INTEGER |  |  | ✓ |
| `block` | BLOB |  |  |  |

### `material_fts_docsize`（2 列 / 种子 0 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `id` | INTEGER |  |  | ✓ |
| `sz` | BLOB |  |  |  |

### `material_fts_idx`（3 列 / 种子 0 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `segid` |  | ✓ |  | ✓ |
| `term` |  | ✓ |  | ✓ |
| `pgno` |  |  |  |  |

### `material_project`（6 列 / 种子 0 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `project_id` | TEXT |  |  | ✓ |
| `name` | TEXT | ✓ |  |  |
| `authority_policy` | TEXT |  |  |  |
| `note` | TEXT |  |  |  |
| `created_at` | TEXT |  | datetime('now') |  |
| `updated_at` | TEXT |  | datetime('now') |  |

### `obligation_list`（5 列 / 种子 12 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `list_id` | TEXT |  |  | ✓ |
| `business_description` | TEXT | ✓ |  |  |
| `mode` | TEXT |  | 'list' |  |
| `items` | TEXT | ✓ |  |  |
| `created_at` | TEXT |  | datetime('now') |  |

### `operation_log`（6 列 / 种子 0 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `log_id` | INTEGER |  |  | ✓ |
| `operation` | TEXT | ✓ |  |  |
| `target_type` | TEXT |  |  |  |
| `target_id` | TEXT |  |  |  |
| `detail` | TEXT |  |  |  |
| `created_at` | TEXT |  | datetime('now') |  |

### `project_list`（6 列 / 种子 0 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `project_id` | TEXT |  |  | ✓ |
| `project_name` | TEXT | ✓ |  |  |
| `project_type` | TEXT |  | 'engineering' |  |
| `clause_revision_ids` | TEXT | ✓ |  |  |
| `created_at` | TEXT |  | datetime('now') |  |
| `updated_at` | TEXT |  | datetime('now') |  |

### `remapping_queue`（8 列 / 种子 0 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `queue_id` | TEXT |  |  | ✓ |
| `old_clause_key` | TEXT | ✓ |  |  |
| `new_clause_key` | TEXT | ✓ |  |  |
| `old_doc_id` | TEXT | ✓ |  |  |
| `new_doc_id` | TEXT | ✓ |  |  |
| `status` | TEXT |  | 'pending' |  |
| `user_id` | TEXT |  |  |  |
| `created_at` | TEXT |  | datetime('now') |  |

### `review_point`（11 列 / 种子 79 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `point_id` | TEXT |  |  | ✓ |
| `task_id` | TEXT | ✓ |  |  |
| `point_type` | TEXT | ✓ |  |  |
| `point_content` | TEXT | ✓ |  |  |
| `matched_clause_ids` | TEXT |  |  |  |
| `match_scores` | TEXT |  |  |  |
| `verdict` | TEXT |  |  |  |
| `verdict_reason` | TEXT |  |  |  |
| `modality_comparison` | TEXT |  |  |  |
| `suggestion` | TEXT |  |  |  |
| `created_at` | TEXT |  | datetime('now') |  |

外键：`task_id` → `review_task.task_id`

### `review_task`（15 列 / 种子 22 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `task_id` | TEXT |  |  | ✓ |
| `project_id` | TEXT |  |  |  |
| `review_type` | TEXT | ✓ |  |  |
| `object_name` | TEXT |  |  |  |
| `object_content` | TEXT |  |  |  |
| `object_file_path` | TEXT |  |  |  |
| `status` | TEXT |  | 'pending' |  |
| `total_points` | INTEGER |  | 0 |  |
| `red_count` | INTEGER |  | 0 |  |
| `yellow_count` | INTEGER |  | 0 |  |
| `green_count` | INTEGER |  | 0 |  |
| `report_data` | TEXT |  |  |  |
| `report_path` | TEXT |  |  |  |
| `created_at` | TEXT |  | datetime('now') |  |
| `completed_at` | TEXT |  |  |  |

外键：`project_id` → `project_list.project_id`

### `snapshot_meta`（6 列 / 种子 8 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `snapshot_id` | TEXT |  |  | ✓ |
| `snapshot_type` | TEXT | ✓ |  |  |
| `db_checksum` | TEXT | ✓ |  |  |
| `file_count` | INTEGER | ✓ |  |  |
| `clause_count` | INTEGER | ✓ |  |  |
| `created_at` | TEXT |  | datetime('now') |  |

### `source_span`（6 列 / 种子 16,198 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `span_id` | TEXT |  |  | ✓ |
| `clause_revision_id` | TEXT | ✓ |  |  |
| `page_number` | INTEGER | ✓ |  |  |
| `bbox_json` | TEXT | ✓ |  |  |
| `span_type` | TEXT |  | 'text' |  |
| `sort_order` | INTEGER |  | 0 |  |

外键：`clause_revision_id` → `clause_revision.clause_revision_id`

### `update_change_event`（13 列 / 种子 0 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `change_id` | TEXT |  |  | ✓ |
| `batch_id` | TEXT | ✓ |  |  |
| `doc_id` | TEXT |  |  |  |
| `standard_no` | TEXT | ✓ |  |  |
| `standard_name` | TEXT |  |  |  |
| `change_type` | TEXT | ✓ |  |  |
| `current_legal_status` | TEXT |  |  |  |
| `latest_info_json` | TEXT |  |  |  |
| `source_channel` | TEXT | ✓ |  |  |
| `evidence_url` | TEXT |  |  |  |
| `archived_pdf_path` | TEXT |  |  |  |
| `user_ack` | INTEGER |  | 0 |  |
| `detected_at` | TEXT |  | datetime('now') |  |

外键：`batch_id` → `update_check_batch.batch_id`

### `update_channel`（29 列 / 种子 0 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `channel_id` | TEXT |  |  | ✓ |
| `name` | TEXT | ✓ |  |  |
| `category` | TEXT | ✓ |  |  |
| `category_raw` | TEXT |  |  |  |
| `url` | TEXT |  |  |  |
| `fetch_kind` | TEXT |  |  |  |
| `list_endpoint` | TEXT |  |  |  |
| `params_json` | TEXT |  |  |  |
| `answers_json` | TEXT |  |  |  |
| `covers` | TEXT |  |  |  |
| `gaps` | TEXT |  |  |  |
| `wiring` | TEXT | ✓ | 'seed_only' |  |
| `verification` | TEXT | ✓ | 'unverified' |  |
| `state` | TEXT | ✓ | 'unknown' |  |
| `probe_url` | TEXT |  |  |  |
| `probe_expect` | TEXT |  |  |  |
| `enabled` | INTEGER | ✓ | 1 |  |
| `last_try_at` | TEXT |  |  |  |
| `last_ok_at` | TEXT |  |  |  |
| `last_error` | TEXT |  |  |  |
| `last_error_code` | TEXT |  |  |  |
| `consecutive_failures` | INTEGER | ✓ | 0 |  |
| `latency_ms` | INTEGER |  |  |  |
| `source_file` | TEXT |  |  |  |
| `note` | TEXT |  |  |  |
| `created_at` | TEXT | ✓ | datetime('now') |  |
| `updated_at` | TEXT | ✓ | datetime('now') |  |
| `segments_json` | TEXT |  |  |  |
| `org_kind` | TEXT |  |  |  |

### `update_check_batch`（12 列 / 种子 0 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `batch_id` | TEXT |  |  | ✓ |
| `trigger_type` | TEXT |  |  |  |
| `status` | TEXT |  | 'pending' |  |
| `total` | INTEGER |  | 0 |  |
| `checked` | INTEGER |  | 0 |  |
| `red_count` | INTEGER |  | 0 |  |
| `yellow_count` | INTEGER |  | 0 |  |
| `green_count` | INTEGER |  | 0 |  |
| `gray_count` | INTEGER |  | 0 |  |
| `started_at` | TEXT |  |  |  |
| `finished_at` | TEXT |  |  |  |
| `created_at` | TEXT |  | datetime('now') |  |

### `user_annotation`（6 列 / 种子 0 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `annotation_id` | TEXT |  |  | ✓ |
| `clause_key` | TEXT | ✓ |  |  |
| `content` | TEXT | ✓ |  |  |
| `annotation_type` | TEXT |  | 'personal' |  |
| `created_at` | TEXT |  | datetime('now') |  |
| `updated_at` | TEXT |  | datetime('now') |  |

### `user_bookmark`（7 列 / 种子 0 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `bookmark_id` | TEXT |  |  | ✓ |
| `clause_key` | TEXT | ✓ |  |  |
| `fixed_revision_id` | TEXT |  |  |  |
| `remark` | TEXT |  |  |  |
| `tags` | TEXT |  |  |  |
| `created_at` | TEXT |  | datetime('now') |  |
| `folder_id` | TEXT |  |  |  |

### `user_bookmark_folder`（3 列 / 种子 1 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `folder_id` | TEXT |  |  | ✓ |
| `folder_name` | TEXT | ✓ |  |  |
| `created_at` | TEXT |  | datetime('now') |  |

### `user_doc_bookmark`（5 列 / 种子 0 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `doc_bookmark_id` | TEXT |  |  | ✓ |
| `doc_id` | TEXT | ✓ |  |  |
| `remark` | TEXT |  |  |  |
| `created_at` | TEXT |  | datetime('now') |  |
| `folder_id` | TEXT |  |  |  |

外键：`doc_id` → `doc_meta.doc_id`

### `watch_list`（3 列 / 种子 0 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `watch_id` | TEXT |  |  | ✓ |
| `doc_id` | TEXT | ✓ |  |  |
| `created_at` | TEXT |  | datetime('now') |  |

外键：`doc_id` → `doc_meta.doc_id`

### `write_queue`（7 列 / 种子 0 行）

| 列 | 类型 | 非空 | 默认 | 主键 |
|---|:--:|:--:|---|:--:|
| `queue_id` | INTEGER |  |  | ✓ |
| `operation_type` | TEXT | ✓ |  |  |
| `payload` | TEXT | ✓ |  |  |
| `status` | TEXT |  | 'pending' |  |
| `result` | TEXT |  |  |  |
| `created_at` | TEXT |  | datetime('now') |  |
| `processed_at` | TEXT |  |  |  |
