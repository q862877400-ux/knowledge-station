# 测试面

> **由 `scripts/survey/03-render.py` 从 `data/*.json` 生成，勿手改。**
> 数字与 JSON 一一对应；要改数字请重跑生成器。

## 一、口径

测试文件数 == tests/ 下 test_*.py + *_test.py 的实际数量。「引用了哪些源码模块」靠文件内出现的 `src.core.x.y` 字符串判定 —— **是文本引用，不是运行期覆盖**。运行期真覆盖要 coverage 数据，本检查没取。`src_modules_referenced` 为空的测试文件不代表它没用源码（可能靠 fixture 间接用）。

## 二、总账

| 项 | 数 |
|---|---:|
| 测试文件 | **184** |
| 测试函数（静态数 def，未算 parametrize 展开） | 2,567 |
| `src/core` 模块 | 157 |
| 没被任何 `.py` 提到的模块 | **0**（其中 18 个是 `__init__`）|

> ⚠ **静态 def 数 ≠ pytest 收集数。** parametrize 会把一个 def 展开成多个节点，
> 所以 pytest 报的节点数会比这里多。要真数字跑 `pytest --collect-only -q`。

## 三、测试文件清单

| 文件 | 测试函数 | 引用源码模块数 | xfail | skip |
|---|---:|---:|---:|---:|
| `tests/test_ccs_chain.py` | 58 | 7 | 0 | 0 |
| `tests/test_material_harvest.py` | 57 | 5 | 0 | 0 |
| `tests/test_channel_repo.py` | 49 | 6 | 0 | 0 |
| `tests/test_material_api.py` | 48 | 8 | 0 | 0 |
| `tests/test_update_inspector.py` | 47 | 4 | 0 | 0 |
| `tests/test_ledger_chain.py` | 46 | 2 | 0 | 0 |
| `tests/test_dryrun_report.py` | 43 | 7 | 0 | 0 |
| `tests/test_text_utils.py` | 41 | 2 | 0 | 0 |
| `tests/test_material_track_l.py` | 37 | 7 | 0 | 0 |
| `tests/test_material_repo.py` | 35 | 2 | 0 | 0 |
| `tests/test_update_channels.py` | 35 | 4 | 0 | 1 |
| `tests/test_contract.py` | 34 | 6 | 0 | 0 |
| `tests/test_credentials_namespace.py` | 34 | 3 | 0 | 0 |
| `tests/test_kb_folder_api.py` | 34 | 1 | 0 | 0 |
| `tests/test_material_collect.py` | 33 | 4 | 0 | 0 |
| `tests/test_material_ingest.py` | 33 | 3 | 0 | 0 |
| `tests/test_folder_store.py` | 32 | 3 | 0 | 0 |
| `tests/test_material_authority.py` | 32 | 2 | 0 | 0 |
| `tests/test_middle_schema.py` | 30 | 3 | 0 | 0 |
| `tests/test_research_report.py` | 30 | 4 | 0 | 0 |
| `tests/test_clause_head_gates.py` | 28 | 1 | 0 | 0 |
| `tests/test_ks_answer.py` | 28 | 7 | 0 | 0 |
| `tests/test_channel_probe.py` | 27 | 2 | 0 | 0 |
| `tests/test_glue_ocr_units.py` | 27 | 1 | 0 | 0 |
| `tests/test_material_dedup.py` | 27 | 1 | 0 | 0 |
| `tests/test_filing_state_pipeline.py` | 26 | 8 | 0 | 0 |
| `tests/test_mineru_cloud.py` | 26 | 5 | 0 | 0 |
| `tests/test_question_router.py` | 26 | 3 | 0 | 0 |
| `tests/test_answer_materials.py` | 25 | 6 | 0 | 0 |
| `tests/test_channel_system_wiring.py` | 25 | 5 | 0 | 0 |
| `tests/test_real_question_ruler.py` | 25 | 0 | 0 | 0 |
| `tests/test_term_bridge.py` | 24 | 1 | 0 | 0 |
| `tests/test_material_locator.py` | 23 | 6 | 0 | 0 |
| `tests/test_ocr_regression_fixtures.py` | 23 | 2 | 0 | 0 |
| `tests/test_standard_no_ocr_suffix.py` | 23 | 1 | 0 | 0 |
| `tests/test_apply_folder_filing.py` | 22 | 3 | 0 | 0 |
| `tests/test_dryrun_batch.py` | 21 | 2 | 0 | 0 |
| `tests/test_govqa_label_review.py` | 21 | 0 | 0 | 0 |
| `tests/test_jev_guard.py` | 21 | 3 | 0 | 0 |
| `tests/test_ks_answer_bbox.py` | 21 | 2 | 0 | 0 |
| `tests/test_pool_depth_ruler.py` | 21 | 0 | 0 | 0 |
| `tests/test_update_announce.py` | 21 | 4 | 0 | 0 |
| `tests/test_watermark_own_standard.py` | 19 | 2 | 1 | 0 |
| `tests/test_disagreement.py` | 18 | 1 | 0 | 0 |
| `tests/test_pipeline.py` | 18 | 6 | 0 | 1 |
| `tests/test_secret_store.py` | 18 | 3 | 0 | 0 |
| `tests/test_class_outcomes.py` | 17 | 2 | 0 | 0 |
| `tests/test_embedding_rebuild_resume.py` | 17 | 1 | 0 | 0 |
| `tests/test_fts_latin_prefix.py` | 17 | 1 | 5 | 0 |
| `tests/test_law_verify.py` | 17 | 2 | 0 | 0 |
| `tests/test_phase6.py` | 17 | 7 | 0 | 0 |
| `tests/test_query_rewrite_ruler.py` | 17 | 0 | 0 | 0 |
| `tests/test_research_draft.py` | 17 | 5 | 0 | 0 |
| `tests/test_understanding.py` | 17 | 5 | 0 | 0 |
| `tests/test_update_discover.py` | 17 | 6 | 0 | 0 |
| `tests/test_effect_report.py` | 16 | 4 | 0 | 0 |
| `tests/test_formula_fragment_glue.py` | 16 | 1 | 0 | 0 |
| `tests/test_golden_criterion.py` | 16 | 3 | 0 | 0 |
| `tests/test_latex_spacing.py` | 16 | 1 | 0 | 0 |
| `tests/test_store_standard_no.py` | 16 | 6 | 0 | 0 |
| `tests/test_figure_legend.py` | 15 | 1 | 0 | 0 |
| `tests/test_law_catalog_refresh.py` | 15 | 3 | 0 | 0 |
| `tests/test_middle_locator.py` | 15 | 1 | 0 | 0 |
| `tests/test_retrieval.py` | 15 | 5 | 0 | 0 |
| `tests/test_threadpool_bound.py` | 15 | 2 | 0 | 0 |
| `tests/test_toc_ingest.py` | 15 | 1 | 0 | 0 |
| `tests/test_index_guard.py` | 14 | 1 | 0 | 0 |
| `tests/test_kb_scope_retrieval.py` | 14 | 7 | 0 | 0 |
| `tests/test_law_source.py` | 14 | 3 | 0 | 0 |
| `tests/test_layout_fidelity.py` | 14 | 6 | 0 | 0 |
| `tests/test_preview_jobs.py` | 14 | 1 | 0 | 0 |
| `tests/test_catalog_hidden_retrieval.py` | 13 | 3 | 0 | 0 |
| `tests/test_channel_answers.py` | 13 | 2 | 0 | 0 |
| `tests/test_credentials_migrate_script.py` | 13 | 3 | 0 | 0 |
| `tests/test_fused_rewrite_ruler.py` | 13 | 0 | 0 | 0 |
| `tests/test_head_unit_fragment_gate.py` | 13 | 1 | 0 | 0 |
| `tests/test_run_gates_ratchet_wiring.py` | 13 | 0 | 0 | 0 |
| `tests/test_t06.py` | 13 | 2 | 0 | 0 |
| `tests/test_update_api.py` | 13 | 1 | 0 | 0 |
| `tests/test_update_routing.py` | 13 | 2 | 0 | 0 |
| `tests/test_latex_frac_tag.py` | 12 | 1 | 0 | 0 |
| `tests/test_law_catalog.py` | 12 | 2 | 0 | 0 |
| `tests/test_law_enum_split.py` | 12 | 1 | 0 | 0 |
| `tests/test_law_source_http_antibot.py` | 12 | 1 | 0 | 0 |
| `tests/test_mineru_cloud_mode.py` | 12 | 3 | 0 | 0 |
| `tests/test_bookmark_folders.py` | 11 | 7 | 0 | 0 |
| `tests/test_formula_leader.py` | 11 | 1 | 0 | 0 |
| `tests/test_law_history.py` | 11 | 1 | 0 | 0 |
| `tests/test_law_split_quality.py` | 11 | 2 | 0 | 0 |
| `tests/test_legal_status.py` | 11 | 1 | 0 | 0 |
| `tests/test_loop2_oracle.py` | 11 | 0 | 0 | 0 |
| `tests/test_patches.py` | 11 | 5 | 0 | 0 |
| `tests/test_appendix_split.py` | 10 | 3 | 0 | 0 |
| `tests/test_bulk_import.py` | 10 | 4 | 0 | 0 |
| `tests/test_change_signal.py` | 10 | 4 | 0 | 0 |
| `tests/test_embedder_health.py` | 10 | 1 | 0 | 0 |
| `tests/test_law_source_api.py` | 10 | 3 | 0 | 0 |
| `tests/test_mineru_channel.py` | 10 | 3 | 0 | 0 |
| `tests/test_resolve_clause_normalization.py` | 10 | 2 | 0 | 0 |
| `tests/test_batch7_security_hardening.py` | 9 | 5 | 0 | 0 |
| `tests/test_channels_write_api.py` | 9 | 1 | 0 | 0 |
| `tests/test_cover_dates.py` | 9 | 1 | 0 | 0 |
| `tests/test_debug_dump_retention.py` | 9 | 3 | 0 | 0 |
| `tests/test_doc_render_api.py` | 9 | 2 | 0 | 0 |
| `tests/test_folder_filing_plan.py` | 9 | 2 | 0 | 0 |
| `tests/test_latex_array.py` | 9 | 1 | 0 | 0 |
| `tests/test_middle_bbox_units.py` | 9 | 1 | 0 | 0 |
| `tests/test_naming_convention_scanner.py` | 9 | 0 | 0 | 0 |
| `tests/test_phase4.py` | 9 | 7 | 0 | 0 |
| `tests/test_pypdf_backfill.py` | 9 | 2 | 0 | 0 |
| `tests/test_reingest_keeps_filing.py` | 9 | 7 | 0 | 0 |
| `tests/test_span_calibration.py` | 9 | 2 | 0 | 0 |
| `tests/test_announce_ingest.py` | 8 | 3 | 0 | 0 |
| `tests/test_answer_confidence.py` | 8 | 1 | 0 | 0 |
| `tests/test_api_config.py` | 8 | 3 | 0 | 0 |
| `tests/test_deep_server.py` | 8 | 1 | 0 | 0 |
| `tests/test_figure_legend_strip.py` | 8 | 1 | 0 | 0 |
| `tests/test_jev_ingest.py` | 8 | 6 | 0 | 0 |
| `tests/test_normalize_std_slash.py` | 8 | 1 | 0 | 0 |
| `tests/test_pua_separators.py` | 8 | 1 | 0 | 0 |
| `tests/test_backup.py` | 7 | 5 | 0 | 0 |
| `tests/test_egress.py` | 7 | 3 | 0 | 0 |
| `tests/test_formula_leader_appendix.py` | 7 | 1 | 0 | 0 |
| `tests/test_long_clause_tail_ruler.py` | 7 | 0 | 0 | 0 |
| `tests/test_patch_guard.py` | 7 | 1 | 0 | 0 |
| `tests/test_phase5.py` | 7 | 4 | 0 | 0 |
| `tests/test_quality_rules.py` | 7 | 5 | 0 | 0 |
| `tests/test_real_corpus_retrieval.py` | 7 | 2 | 0 | 0 |
| `tests/test_reranker.py` | 7 | 3 | 0 | 0 |
| `tests/test_update_package.py` | 7 | 6 | 0 | 0 |
| `tests/test_api.py` | 6 | 4 | 0 | 0 |
| `tests/test_credential_readers_scan.py` | 6 | 0 | 0 | 0 |
| `tests/test_loop2_driver.py` | 6 | 0 | 0 | 0 |
| `tests/test_phase10_blindspots.py` | 6 | 4 | 0 | 0 |
| `tests/test_phase7.py` | 6 | 4 | 0 | 0 |
| `tests/test_seed_db_guard.py` | 6 | 2 | 0 | 0 |
| `tests/test_unsupported_context.py` | 6 | 1 | 0 | 0 |
| `tests/test_change_ack.py` | 5 | 2 | 0 | 0 |
| `tests/test_classical_segmentation_ruler.py` | 5 | 1 | 0 | 0 |
| `tests/test_file_digest.py` | 5 | 3 | 0 | 0 |
| `tests/test_gates_tracked_total.py` | 5 | 0 | 0 | 0 |
| `tests/test_models_dir_override.py` | 5 | 1 | 0 | 0 |
| `tests/test_scnet_readchain.py` | 5 | 1 | 0 | 0 |
| `tests/test_standard_body.py` | 5 | 1 | 0 | 0 |
| `tests/test_table_binding.py` | 5 | 1 | 0 | 0 |
| `tests/test_web_ingest.py` | 5 | 2 | 0 | 0 |
| `tests/test_api_cold_start.py` | 4 | 3 | 0 | 0 |
| `tests/test_assets_endpoint.py` | 4 | 1 | 0 | 0 |
| `tests/test_ccs_fetcher.py` | 4 | 2 | 0 | 0 |
| `tests/test_credential_reconcile.py` | 4 | 2 | 0 | 0 |
| `tests/test_doc_batch_delete.py` | 4 | 1 | 0 | 0 |
| `tests/test_jev_cn_baseline.py` | 4 | 0 | 0 | 0 |
| `tests/test_loop2_vlm.py` | 4 | 0 | 0 | 0 |
| `tests/test_patch_migration.py` | 4 | 3 | 0 | 0 |
| `tests/test_phase13_blindspots.py` | 4 | 4 | 0 | 0 |
| `tests/test_phase8.py` | 4 | 2 | 0 | 0 |
| `tests/test_selfcheck_fixes.py` | 4 | 3 | 0 | 0 |
| `tests/test_storage.py` | 4 | 2 | 0 | 0 |
| `tests/test_update_report.py` | 4 | 4 | 0 | 0 |
| `tests/test_vision.py` | 4 | 5 | 0 | 0 |
| `tests/test_auto_tag.py` | 3 | 3 | 0 | 0 |
| `tests/test_doc_catalog_std_no.py` | 3 | 2 | 0 | 0 |
| `tests/test_docx_ingest.py` | 3 | 3 | 0 | 0 |
| `tests/test_golden_gate.py` | 3 | 1 | 0 | 0 |
| `tests/test_govcn_archive.py` | 3 | 1 | 0 | 0 |
| `tests/test_label_gap_not_jev.py` | 3 | 0 | 0 | 0 |
| `tests/test_law_text_edges.py` | 3 | 2 | 0 | 0 |
| `tests/test_llm_empty_retry.py` | 3 | 3 | 0 | 0 |
| `tests/test_measure_harness.py` | 3 | 0 | 0 | 0 |
| `tests/test_mineru_gpu_lock.py` | 3 | 1 | 0 | 0 |
| `tests/test_modality_window_false_positive.py` | 3 | 1 | 0 | 0 |
| `tests/test_phase12.py` | 3 | 4 | 0 | 0 |
| `tests/test_r5a.py` | 3 | 5 | 0 | 0 |
| `tests/test_sqlite_conn_registry.py` | 3 | 1 | 0 | 0 |
| `tests/test_supervisor.py` | 3 | 1 | 0 | 0 |
| `tests/test_table_position_render.py` | 3 | 2 | 0 | 0 |
| `tests/test_dry_run_concurrency.py` | 2 | 4 | 0 | 0 |
| `tests/test_dryrun.py` | 2 | 2 | 0 | 0 |
| `tests/test_fewshot.py` | 2 | 1 | 0 | 0 |
| `tests/test_gate_baseline_whitelist.py` | 2 | 0 | 0 | 0 |
| `tests/test_golden_set.py` | 2 | 2 | 0 | 1 |
| `tests/test_legal_status_reference.py` | 2 | 1 | 0 | 0 |
| `tests/test_rag_gate_not_adopted.py` | 2 | 0 | 0 | 0 |
| `tests/test_write_queue_bootstrap.py` | 2 | 3 | 0 | 0 |