# 代码地图（AST 级符号清单）

> **由 `scripts/survey/03-render.py` 从 `data/*.json` 生成，勿手改。**
> 数字与 JSON 一一对应；要改数字请重跑生成器。

## 一、总账

| 项 | 数 |
|---|---:|
| 扫描面 | `src`, `tests`, `scripts`, `tools/gov-qa`, `eval` |
| `.py` 文件 | **1,275** |
| 解析成功模块 | **1,275** |
| 解析失败 | **0**（判据：成功 + 失败 == 总数）|
| 符号总数 | **7,044** |
| 类 | 386 |
| 函数（含方法） | 6,658 |
| 无 docstring 的符号 | 3,324 |

## 二、按目录看规模

| 目录 | 模块 | 符号 | 函数 | 类 | 无 docstring |
|---|---:|---:|---:|---:|---:|
| `tools/gov-qa` | 682 | 1,581 | 1,561 | 20 | 848 |
| `src/core` | 157 | 1,341 | 1,265 | 76 | 333 |
| `eval/recall-funnel` | 135 | 293 | 293 | 0 | 225 |
| `scripts/survey` | 13 | 78 | 78 | 0 | 62 |
| `tests/test_ccs_chain.py` | 1 | 77 | 76 | 1 | 5 |
| `tests/test_material_harvest.py` | 1 | 72 | 61 | 11 | 27 |
| `tests/test_update_inspector.py` | 1 | 69 | 68 | 1 | 17 |
| `tests/test_material_api.py` | 1 | 66 | 58 | 8 | 28 |
| `tests/test_channel_repo.py` | 1 | 62 | 53 | 9 | 39 |
| `tests/test_ledger_chain.py` | 1 | 58 | 50 | 8 | 25 |
| `tests/test_update_channels.py` | 1 | 57 | 47 | 10 | 23 |
| `tests/test_dryrun_report.py` | 1 | 56 | 56 | 0 | 14 |
| `eval/lay-phrasing` | 24 | 55 | 55 | 0 | 51 |
| `tests/test_credentials_namespace.py` | 1 | 51 | 49 | 2 | 38 |
| `scripts/loop2` | 4 | 49 | 48 | 1 | 29 |
| `tests/test_material_track_l.py` | 1 | 49 | 42 | 7 | 22 |
| `tests/test_material_repo.py` | 1 | 46 | 37 | 9 | 30 |
| `tests/test_material_collect.py` | 1 | 43 | 35 | 8 | 17 |
| `tests/test_material_authority.py` | 1 | 42 | 34 | 8 | 22 |
| `tests/test_material_ingest.py` | 1 | 42 | 37 | 5 | 25 |

## 三、最大的 20 个函数（**按行数，不是按重要性**）

| 函数 | 文件:行 | 行数 |
|---|---|---:|
| `create_app` | `src/core/api/server.py:278` | **2997** |
| `register` | `src/core/api/routes_kb_folders.py:78` | **609** |
| `register` | `src/core/api/routes_update.py:37` | **608** |
| `run_full_ingest` | `src/core/ingestion/pipeline.py:2021` | **397** |
| `split_items_into_clauses` | `src/core/ingestion/pipeline.py:759` | **367** |
| `answer` | `src/core/llm/ks_answer.py:810` | **351** |
| `perform_hybrid_search` | `src/core/retrieval/hybrid_engine.py:213` | **343** |
| `register` | `src/core/api/routes_materials.py:63` | **325** |
| `main` | `scripts/survey/04-reconcile.py:41` | **302** |
| `main` | `eval/recall-funnel/exp-12-long-clause-tail/measure.py:111` | **256** |
| `main` | `eval/recall-funnel/build-v2.py:63` | **255** |
| `analyze_preview_report` | `src/core/ingestion/dry_run.py:163` | **246** |
| `main` | `scripts/measure-cross-language-fts.py:166` | **242** |
| `register` | `src/core/api/routes_law.py:29` | **223** |
| `main` | `eval/real-question-ruler/build.py:130` | **219** |
| `ingest_law_text` | `src/core/ingestion/law_text.py:167` | **206** |
| `build_clause_models` | `src/core/ingestion/pipeline.py:1275` | **201** |
| `main` | `scripts/std_bulk_import.py:201` | **198** |
| `register` | `src/core/api/routes_channels.py:62` | **198** |
| `main` | `eval/lay-phrasing/analyze-gen.py:79` | **194** |

## 四、超过 100 行的函数（逐个列，共 121 个）

| 行数 | 函数 | 位置 |
|---:|---|---|
| 2997 | `create_app` | `src/core/api/server.py:278` |
| 609 | `register` | `src/core/api/routes_kb_folders.py:78` |
| 608 | `register` | `src/core/api/routes_update.py:37` |
| 397 | `run_full_ingest` | `src/core/ingestion/pipeline.py:2021` |
| 367 | `split_items_into_clauses` | `src/core/ingestion/pipeline.py:759` |
| 351 | `answer` | `src/core/llm/ks_answer.py:810` |
| 343 | `perform_hybrid_search` | `src/core/retrieval/hybrid_engine.py:213` |
| 325 | `register` | `src/core/api/routes_materials.py:63` |
| 302 | `main` | `scripts/survey/04-reconcile.py:41` |
| 256 | `main` | `eval/recall-funnel/exp-12-long-clause-tail/measure.py:111` |
| 255 | `main` | `eval/recall-funnel/build-v2.py:63` |
| 246 | `analyze_preview_report` | `src/core/ingestion/dry_run.py:163` |
| 242 | `main` | `scripts/measure-cross-language-fts.py:166` |
| 223 | `register` | `src/core/api/routes_law.py:29` |
| 219 | `main` | `eval/real-question-ruler/build.py:130` |
| 206 | `ingest_law_text` | `src/core/ingestion/law_text.py:167` |
| 201 | `build_clause_models` | `src/core/ingestion/pipeline.py:1275` |
| 198 | `main` | `scripts/std_bulk_import.py:201` |
| 198 | `register` | `src/core/api/routes_channels.py:62` |
| 194 | `main` | `eval/lay-phrasing/analyze-gen.py:79` |
| 189 | `main` | `eval/recall-funnel/summarize.py:41` |
| 187 | `main` | `eval/lay-phrasing/check-lay-50.py:41` |
| 187 | `main` | `scripts/survey/07-runtime-probe.py:158` |
| 186 | `_main` | `scripts/apply-folder-filing.py:1145` |
| 179 | `register` | `src/core/api/routes_report.py:35` |
| 177 | `main` | `eval/recall-funnel/funnel.py:178` |
| 172 | `register` | `src/core/api/routes_ingest_preview.py:58` |
| 172 | `run_batch` | `src/core/update/inspector.py:746` |
| 167 | `main` | `eval/recall-funnel/exp-7-rrm/run.py:152` |
| 166 | `try_redraw` | `src/core/figure_redraw.py:54` |
| 165 | `main` | `eval/recall-funnel/exp-9-col-prior/measure.py:107` |
| 164 | `main` | `scripts/measure-term-bridge.py:61` |
| 164 | `main` | `tools/gov-qa/recon/igi-chunked.py:65` |
| 163 | `main` | `scripts/measure-term-aggregation.py:90` |
| 159 | `main` | `eval/recall-funnel/exp-13-query-rewrite/run.py:196` |
| 158 | `main` | `eval/recall-funnel/exp-5-real-questions/06-build-real-bench.py:71` |
| 156 | `main` | `tools/gov-qa/coverage-report.py:96` |
| 154 | `main` | `scripts/measure-classical-chinese-segmentation.py:236` |
| 148 | `main` | `eval/recall-funnel/exp-4c-embedding-1024/21-ab-1024.py:42` |
| 148 | `build_report_blocks` | `src/core/exports/research_report.py:245` |
| 143 | `main` | `eval/lay-phrasing/probe-rerank-two-stage.py:55` |
| 143 | `main` | `scripts/verify-engine-uvicorn.py:117` |
| 142 | `main` | `eval/lay-phrasing/probe-rerank-control.py:54` |
| 141 | `main` | `eval/recall-funnel/exp-4b-embedding-round2/10-latency.py:64` |
| 139 | `step5_tests` | `scripts/survey/02-surface.py:223` |
| 138 | `main` | `scripts/std_status_check.py:165` |
| 135 | `main` | `eval/recall-funnel/exp-1-contextual/04-ab-eval.py:56` |
| 135 | `_convert_40_to_34` | `src/core/ingestion/middle_schema.py:115` |
| 134 | `main` | `eval/real-question-ruler/verify.py:59` |
| 134 | `refresh_catalog` | `src/core/knowledge/law_source/catalog.py:329` |
| 134 | `poll_one` | `tools/gov-qa/poll.py:107` |
| 131 | `main` | `eval/recall-funnel/exp-4-embedding-shadow/03-verdict-e4.py:53` |
| 131 | `main` | `scripts/pick-domain-terms.py:88` |
| 130 | `main` | `eval/recall-funnel/exp-3-query-side/03-run-e3.py:35` |
| 130 | `step_requirements` | `scripts/survey/09-requirements.py:154` |
| 130 | `assemble_evidence` | `src/core/materials/authority.py:116` |
| 129 | `main` | `scripts/measure-material-bridge.py:112` |
| 129 | `gen_runtime_probe` | `scripts/survey/03-render.py:863` |
| 128 | `main` | `scripts/migrate-clause-vec-doc-id.py:107` |
| 128 | `_scan_one_source` | `src/core/update/announce.py:605` |
| 127 | `main` | `eval/recall-funnel/exp-5-real-questions/34-ingest-full.py:123` |
| 127 | `read_back` | `scripts/apply-folder-filing.py:847` |
| 127 | `delete_folder` | `src/core/knowledge/folder_store.py:576` |
| 125 | `main` | `eval/recall-funnel/exp-1-contextual/06-verdict.py:87` |
| 124 | `main` | `eval/recall-funnel/exp-5-real-questions/04-trial-scrape.py:59` |
| 124 | `main` | `scripts/survey/01-symbols.py:236` |
| 123 | `attach_bboxes` | `src/core/llm/ks_answer.py:151` |
| 121 | `_probe_number` | `src/core/update/inspector.py:334` |
| 120 | `main` | `eval/recall-funnel/exp-1-contextual/08-mechanism-diagnostic.py:45` |
| 120 | `main` | `eval/recall-funnel/exp-4b-embedding-round2/11-prefix-ab.py:45` |
| 120 | `harvest` | `tools/gov-qa/adapters/gs_tianshui.py:110` |
| 119 | `main` | `scripts/measure-material-recall.py:85` |
| 119 | `harvest_liuyan` | `tools/gov-qa/adapters/_liuyan_common.py:109` |
| 118 | `main` | `eval/recall-funnel/exp-11-rerank-fix/measure-rerank-ab.py:88` |
| 118 | `main` | `eval/recall-funnel/exp-5-real-questions/24-ingest-sample.py:49` |
| 118 | `main` | `scripts/measure-term-victim-side.py:69` |
| 118 | `_run` | `src/core/knowledge/ccs_backfill.py:309` |
| 116 | `main` | `scripts/survey/08-repro-resume-hang.py:105` |
| 116 | `_cell_html` | `src/core/ingestion/pipeline.py:1621` |
| 115 | `build_snapshot` | `scripts/loop2/oracle_snapshot.py:194` |
| 115 | `harvest` | `tools/gov-qa/adapters/sc_yaan.py:116` |
| 115 | `main` | `tools/gov-qa/recon/probe-province-city-links.py:77` |
| 114 | `main` | `scripts/preview-folder-filing.py:125` |
| 114 | `resolve_clause` | `src/core/storage/clause_repo.py:822` |
| 114 | `export_batch_report_xlsx` | `src/core/update/report.py:148` |
| 114 | `verify_llm_output` | `src/core/verification/typed_verifier.py:215` |
| 113 | `main` | `eval/recall-funnel/exp-4-embedding-shadow/02-ab-eval.py:38` |
| 113 | `main` | `scripts/make-seed-db.py:187` |
| 113 | `harvest` | `tools/gov-qa/adapters/xz_lasa.py:145` |
| 111 | `main` | `eval/recall-funnel/exp-1-contextual/05-human-check.py:31` |
| 111 | `main` | `eval/recall-funnel/exp-3b-query-side-loo/01-run-e3b.py:31` |
| 111 | `build_payload` | `scripts/apply-folder-filing.py:644` |
| 111 | `harvest_igi` | `tools/gov-qa/adapters/_igi_common.py:102` |
| 110 | `list_folder` | `src/core/knowledge/folder_store.py:890` |
| 110 | `main` | `tools/gov-qa/measure-locate-rate.py:89` |
| 110 | `collect` | `tools/gov-qa/recon/gate-quality.py:211` |
| 109 | `harvest` | `tools/gov-qa/adapters/zk_zxsq.py:124` |
| 109 | `main` | `tools/gov-qa/recon/city-sc-probe31.py:41` |
| 108 | `_run` | `eval/recall-funnel/exp-15-pool-depth-fusion/run.py:291` |
| 108 | `main` | `eval/recall-funnel/exp-3-query-side/04-verdict-e3.py:50` |
| 108 | `main` | `eval/recall-funnel/exp-5-real-questions/16-compare-lawrefbook.py:67` |
| 108 | `main` | `scripts/measure-term-selection.py:56` |
| 108 | `fetch_full_clause` | `src/core/storage/clause_repo.py:712` |
| 108 | `harvest` | `tools/gov-qa/adapters/gd_huizhou.py:107` |
| 107 | `main` | `eval/recall-funnel/exp-4c-embedding-1024/23-verdict.py:25` |
| 106 | `main` | `tools/gov-qa/recon/audit-coverage.py:410` |
| 105 | `main` | `eval/recall-funnel/regression-ingest/verdict.py:47` |
| 105 | `collect_text` | `src/core/materials/collect.py:226` |
| 105 | `test_vec_channel_is_restricted_without_the_model` | `tests/test_kb_scope_retrieval.py:262` |
| 104 | `main` | `eval/recall-funnel/exp-3b-query-side-loo/02-verdict-e3b.py:50` |
| 104 | `main` | `scripts/fix-standard-no-ocr-suffix.py:131` |
| 104 | `load` | `src/core/middle_geo.py:216` |
| 103 | `main` | `eval/recall-funnel/exp-5-real-questions/17-compare-strict.py:65` |
| 103 | `main` | `eval/recall-funnel/exp-5-real-questions/18-extract-to-standards.py:52` |
| 103 | `_run_batch` | `src/core/ingestion/deep_server.py:382` |
| 103 | `harvest_jact` | `tools/gov-qa/adapters/_jact_common.py:224` |
| 103 | `harvest` | `tools/gov-qa/adapters/wh_hdjl.py:272` |
| 101 | `main` | `scripts/survey/00-inventory.py:247` |
| 101 | `mineru_cloud_submit_and_wait` | `src/core/ingestion/mineru_cloud.py:335` |
| 101 | `TestSlowEndpointsAreDeclaredSync.test_名单里的_async_端点要么量过要么写明不可量` | `tests/test_material_api.py:886` |
| 101 | `show_answers` | `tools/gov-qa/recon/audit-coverage.py:117` |

## 五、模块 docstring 覆盖

**16 / 1275 个模块没有模块级 docstring。**

- `eval/lay-phrasing/validate-gen.py`
- `src/__init__.py`
- `src/core/__init__.py`
- `src/core/api/__init__.py`
- `src/core/compliance/__init__.py`
- `src/core/domain/__init__.py`
- `src/core/exports/__init__.py`
- `src/core/ingestion/__init__.py`
- `src/core/knowledge/__init__.py`
- `src/core/llm/__init__.py`
- `src/core/retrieval/__init__.py`
- `src/core/storage/__init__.py`
- `src/core/verification/__init__.py`
- `src/core/vision/__init__.py`
- `tools/gov-qa/recon/gs-lx-direct.py`
- `tools/gov-qa/recon/probe-ah-wuhu.py`