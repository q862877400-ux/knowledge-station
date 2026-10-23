# src/core 事实地图

调查日期：2026-10-20。范围：`src/core/` 全部 155 个 `.py` 文件（45,439 行 / 2,346 KB）。
只读调查，未运行任何测试或门禁，未启动引擎。

**统计口径说明**：本文所有行数用 `(Get-Content <file>).Count` 计（含空行与注释）。
`Measure-Object -Line` 会跳过空行，早期用它得出的数字偏小约 4–9%，已全部重算。

---

## 一、总览表

| 子系统 | 一句话职责 | 文件数 | 行数 | 写什么 |
|---|---|---|---|---|
| `update` | 去官网/部委站查某标准或法规有没有新版、废止、公告 | 36 | 8,811 | `update_check_batch` `update_change_event` `announcement_observed` `update_channel` `channel_test_case` `app_config` `bulk_import_batch` `event_log` `doc_meta`(更新) |
| `ingestion` | 把 PDF/docx/网页文本解析成条款，写进库 | 20 | 7,684 | `doc_meta` `clause_revision`(经 clause_repo) `bulk_import_batch` `clause_patch` `event_log` `operation_log` `source_span`(更新) `clause_fts`(更新) + 磁盘 `parse_out/` `preview_tmp/` `material_tmp/` `dryrun/` |
| `knowledge` | 给文档分类、打 CCS 分类号、建目录、管法规来源 | 22 | 6,769 | `folder` `folder_member` `doc_filing_state` `doc_ccs_state` `alias_store` `law_catalog` `doc_meta`(更新) + 磁盘 `law_source/` `law_manifest.json` `ccs_undo` 日志 |
| `api` | 176 条 HTTP 路由 + 鉴权 + 线程池闸门 + SSE 流式 | 10 | 6,086 | `debug_dump` + 磁盘 `engine.session.json` `parse_out/` `exports/` |
| `(root)` 9 个散文件 | 配置、异常、入口、看门狗、文本清洗、图/公式定位 | 10 | 3,821 | 磁盘 `database/knowledge.db`(仅路径定义) `exports/`(无) |
| `storage` | SQLite 连接池、schema、各仓储读写、备份、写队列 | 13 | 3,198 | 几乎全部业务表（见 §2.13）：`clause_revision` `source_span` `clause_fts` `clause_vec` `doc_meta` `doc_page_geometry` `evidence_edge` `user_*` `material*` `project_list` `obligation_list` `snapshot_meta` `write_queue` `update_channel` 等 |
| `llm` | 调 DeepSeek 出取证答案、外发审计、Jev 结构化判断 | 7 | 1,883 | `debug_dump` |
| `materials` | 参考资料项目：抓网页、查重、定位校验、转正入库 | 7 | 1,715 | 无直接 SQL（全部经 `storage/material_repo.py`） |
| `exports` | 效力报告、研究报告、引用导出、Office 往返编辑 | 7 | 1,505 | 无直接 SQL；磁盘 `exports/` |
| `retrieval` | 六路混合检索 + RRF 融合 + 重排 + 术语桥 | 5 | 1,270 | 无直接 SQL |
| `quality` | 条款体检、识别/版面度量、质量分级裁决、分歧检测 | 5 | 826 | 无直接 SQL |
| `settings` | API 凭据加密存取（DPAPI）、系统层清理、连通性自测 | 3 | 684 | 磁盘 `<data_dir>/secrets.json` |
| `verification` | 核验大模型输出有没有编造引用；纠错补丁防乱检测 | 3 | 427 | 无 |
| `query` | 判断用户问的是哪类问题、抽槽位、改写检索词 | 1 | 280 | 无 |
| `domain` | Pydantic 数据模型定义 | 2 | 186 | 无 |
| `compliance` | 内部制度 vs 法定义务的差距分析 | 2 | 177 | `internal_policy` `legal_obligation` `review_task` `gap_analysis` |
| `vision` | 本地 OCR 后反查条款 | 2 | 117 | 磁盘 `vision_tmp/` |
| **合计** | | **155** | **45,439** | |

---

## 二、逐子系统明细

### 2.1 api（10 文件 / 6,086 行）

**职责**：对外开 176 条 HTTP 端点，管 token 鉴权、把重活挡在有限的线程池后面、把答案流式推给前端。

**对外入口**
- `api/server.py:create_app(token)` —— 唯一装配入口，`main.py` 与 `supervisor.py` 都调它
- `api/server.py:run()` —— 进程入口，`main.py` 调
- `api/server.py:bind_random()` —— 随机端口 + token
- `api/server.py:bound_threadpool_once()` / `is_heavy_path()` / `warm_retrieval_stack()` —— 被 `tests/` 直接调用
- 8 个 `routes_*.py` 各暴露 `register(app, json_error)`，由 `server.py` 在 **3239–3270 行**依次调用

**依赖**：`compliance` `config` `exceptions` `exports` `figure_locator` `figure_redraw` `formula_locator` `ingestion` `knowledge` `llm` `materials` `middle_geo` `quality` `query` `retrieval` `settings` `storage` `text_utils` `update` `verification` `vision` —— **全部 21 个同级子系统，一个不落**。

**写什么**：`debug_dump` 表；磁盘 `<data_dir>/engine.session.json`（端口/token 握手）、`<data_dir>/parse_out/`、`<data_dir>/exports/`。

**文件清单**

| 文件 | 行数 | 负责什么 |
|---|---|---|
| `api/server.py` | 3,340 | 装配 + 67 条路由。分段见下 |
| `api/routes_update.py` | 644 | 32 条更新/找标/入库批量/数据包路由 |
| `api/routes_kb_folders.py` | 686 | 24 条知识库多级目录 + 收件箱 + CCS 补全路由 |
| `api/routes_materials.py` | 387 | 18 条参考资料项目路由 |
| `api/routes_channels.py` | 259 | 10 条渠道台账路由 |
| `api/routes_law.py` | 251 | 10 条官方法规来源路由 |
| `api/routes_ingest_preview.py` | 229 | 6 条入库预览（Dry-Run）路由 |
| `api/routes_report.py` | 213 | 6 条效力报告 / 研究报告路由 |
| `api/routes_settings.py` | 77 | 3 条 API 配置路由 |
| `api/__init__.py` | 0 | 空 |

**`api/server.py` 的分段结构**（这是本次调查的重点之一，按行号给出实际边界）

| 行段 | 内容 |
|---|---|
| 1–22 | 模块 docstring + import |
| 23–130 | 线程池常量 `THREADPOOL_TOKENS=16`、`HEAVY_TOKENS=4`、`HEAVY_PREFIXES`（20 条前缀）、`HEAVY_SKIP` |
| 132–212 | `_get_heavy_limiter()` `is_heavy_path()` `warm_retrieval_stack()` |
| 214–258 | `class _HeavyGateMiddleware` —— 纯 ASGI 重活闸门 |
| 267–277 | `_clause_number_sort_key()` |
| 278–3231 | `def create_app(token)` —— **整个应用，2,954 行** |
| ├ 278–337 | 初始化 schema、补列、CORS、加中间件、`_json_error` |
| ├ 338–360 | `/health` |
| ├ 359–537 | 纠错补丁 API（`/clauses/patches` 增删查） |
| ├ 539–840 | 文档文件 / 图 / 公式 / 表格截图（`/documents/{id}/file` `/figure` `/formula` `/table-image`）—— **含 PDF 渲染、坐标换算** |
| ├ 841–926 | 文档列表、分类、批量删除 |
| ├ 927–1183 | `/documents/{id}/tree` —— 文档树组装（**257 行**） |
| ├ 1184–1433 | 收藏（条款级 + 标准级 + 收藏夹 CRUD + 目录树） |
| ├ 1434–1515 | 批注、项目清单、合规策略与差距分析 |
| ├ 1516–1763 | 文档版本、条款前缀查、全文条款、资产、对比、操作日志、别名抽取、引用导出 |
| ├ 1764–2201 | `POST /chat/completions` —— **SSE 流式问答，438 行** |
| ├ 2202–2262 | `/ks/answer`、外发审计、补丁迁移 |
| ├ 2263–2321 | Office 往返编辑 4 条 |
| ├ 2322–2421 | 双向溯源、bbox、条款元信息、视觉定位、批量问答 |
| ├ 2422–2524 | 快照备份/恢复、影响面分析、健康看板、debug dump |
| └ 2525–3231 | **闭包内的业务辅助函数 707 行**：`_expand_title_clauses` `_fetch_clause` `_answer_confidence` `_html_to_text` `_content_html`（**2622–3141，520 行，把条款正文渲染成 HTML：图题/公式/表格注入**）、`_full_evidence` `_ev_dict` `_placeholder_answer` `_sse` |
| 3232–3326 | 8 个 `routes_*.register()` 接线 + 4 个后台线程启动（写队列、法规刷新、更新巡检） |
| 3276–3340 | `bind_random()` `run()` |

**这张表本身就是一条结论**：`server.py` 里 2,954 行在 `create_app` 闭包内，其中 707 行是纯业务逻辑（HTML 渲染、证据组装、置信度分级），和 HTTP 无关。

---

### 2.2 compliance（2 文件 / 177 行）

**职责**：拿一份公司内部制度，逐条比对法定义务，输出"符合/不符合/部分符合"和整改建议。

**对外入口**：`compliance/gap_analysis.py:import_internal_policy` `build_obligations` `run_gap_analysis` —— 只被 `api/server.py:1492/1499/1507` 三处调用。

**依赖**：`exceptions` `storage`。

**写什么**：`internal_policy` `legal_obligation` `review_task` `gap_analysis` 四张表。

| 文件 | 行数 | 负责什么 |
|---|---|---|
| `compliance/gap_analysis.py` | 177 | 导入内部制度、从法条生成义务清单、跑差距分析、写建议 |
| `compliance/__init__.py` | 0 | 空 |

---

### 2.3 domain（2 文件 / 186 行）

**职责**：定义全库共用的 Pydantic 数据模型（文档、条款、证据边、核验结果）。

**对外入口**：`domain/models.py` 的 8 个类 —— `PageGeometryModel` `SourceSpanModel` `ClauseRevisionModel` `DocumentMetaModel` `EvidenceEdgeModel` `ReviewPointModel` `ModalityViolation` `VerificationResult`。被 `ingestion` `knowledge` `llm` `retrieval` `storage` `verification` 六处 import。

**依赖**：**零**。整个 `src/core` 里唯一一个不 import 任何同级子系统的目录。

**写什么**：不写任何东西。

| 文件 | 行数 | 负责什么 |
|---|---|---|
| `domain/models.py` | 186 | 8 个 Pydantic 模型 |
| `domain/__init__.py` | 0 | 空 |

---

### 2.4 exports（7 文件 / 1,505 行）

**职责**：把库里的数据做成对外的成品——效力报告、研究报告、引用块、Office 编辑会话。

**对外入口**
- `exports/effect_report.py:collect_effect_report` `collect_effect_docs` `collect_effect_by_color` `export_effect_report_xlsx` —— `api/routes_report.py` 用
- `exports/research_report.py:build_research_report` `write_research_report` `build_report_blocks` `check_conclusion_citations` —— `api/routes_report.py` 用
- `exports/office_roundtrip.py:create_edit_session` `poll_edit_session` `commit_edit_session` `cancel_edit_session` —— `api/server.py:2266–2304` 用
- `exports/backlinks.py:query_backlinks` —— `api/server.py:2313` 用
- `exports/report_export.py:build_citation_block` —— `api/server.py:1722` 用
- `exports/research_draft.py:draft_conclusion` —— `api/routes_report.py` 用

**依赖**：`config` `exceptions` `knowledge` `llm` `materials` `storage` `text_utils`。

**写什么**：无直接 SQL；磁盘 `<data_dir>/exports/`（`report_export._exports_dir()`、`research_report._exports_dir()`、`egress_audit` 三处各自拼这个路径）。

| 文件 | 行数 | 负责什么 |
|---|---|---|
| `exports/research_report.py` | 507 | 研究报告：证据装配、引用核对、markdown/html 双格式落盘 |
| `exports/effect_report.py` | 400 | 效力报告：按目录分类聚合五色统计 + xlsx 导出 |
| `exports/office_roundtrip.py` | 351 | 条款 → docx → 打开 Office → 用户改 → 回读比对 → 提交补丁 |
| `exports/research_draft.py` | 135 | 只生成"结论草稿"段落 |
| `exports/backlinks.py` | 61 | 条款被谁引用（查 `evidence_edge`） |
| `exports/report_export.py` | 51 | 引用块格式化 + exports 目录命名 |
| `exports/__init__.py` | 0 | 空 |

---

### 2.5 ingestion（20 文件 / 7,684 行）

**职责**：把一份 PDF/docx/纯文本拆成条款、判类型、建引用边，写进数据库。

**对外入口**
- `ingestion/pipeline.py:run_full_ingest` —— **主入口**，`routes_update.py` `bulk.py` `reingest.py` 都调
- `ingestion/pipeline.py:split_items_into_clauses` `build_clause_models` `load_middle_items` —— `dry_run.py` `pypdf_backfill.py` 用
- `ingestion/law_text.py:ingest_law_text` `split_gb_text` `split_law_text` `split_law_enum_text` —— `update/web_ingest.py` `routes_law.py` 用
- `ingestion/bulk.py:create_bulk_batch` `fast_scan` `parse_loop` `pause_batch` `resume_batch` `abort_batch` —— `routes_update.py` 用
- `ingestion/dry_run.py:analyze_preview_report` `scan_preview_dir` `preview_batch` —— `routes_ingest_preview.py` 用
- `ingestion/preview_jobs.py:create_job` `get_job` `abort_job` —— `routes_ingest_preview.py` 用
- `ingestion/material_ingest.py:ingest_material_file` `ingest_project_dir` `chunk_text` `extract_pages` `file_hash` `text_hash` —— `routes_materials.py` 用
- `ingestion/mineru_adapter.py:parse_pdf_with_mineru` `extract_page_geometries` —— `pipeline.py` 用
- `ingestion/mineru_cloud.py:mineru_cloud_submit_and_wait` `mineru_cloud_available` —— `mineru_adapter.py` 用
- `ingestion/deep_server.py:deep_server_submit_and_wait` —— `mineru_adapter.py` 用
- `ingestion/reingest.py:plan_reingest` `start_reingest` `reingest_status` —— `routes_kb_folders.py` 用
- `ingestion/span_calibration.py:calibrate` `calibrate_new` —— `pipeline.py` 用
- `ingestion/middle_schema.py:normalize_middle` `load_middle_json` —— `pipeline.py` `middle_geo.py` 用
- `ingestion/middle_locator.py:iter_middle_files` `find_middle_files` —— `pipeline.py` `middle_geo.py` `figure_locator.py` 用

**依赖**：`config` `domain` `exceptions` `knowledge` `llm` `quality` `storage` `text_utils` `update`。

**写什么**：`doc_meta` `bulk_import_batch` `clause_patch` `event_log` `operation_log`；更新 `clause_fts` `source_span` `doc_meta`；磁盘 `parse_out/` `preview_tmp/` `material_tmp/` `dryrun/`。

| 文件 | 行数 | 负责什么 |
|---|---|---|
| `ingestion/pipeline.py` | 2,443 | **全库第二大文件**。MinerU 解析 → middle.json → E1–E7 条款切分 → 建模型 → 建边 → 入库。核心是 `split_items_into_clauses`（条款头识别 + 6 道闸门）与 `run_full_ingest`（2021 行起） |
| `ingestion/mineru_adapter.py` | 585 | 调 MinerU（本地/云/常驻服务三选一）+ PyMuPDF 提几何 |
| `ingestion/bulk.py` | 531 | 万级批量导入：扫描 → 解析循环 → 断点续跑 → 预算控制 |
| `ingestion/dry_run.py` | 521 | 入库前试算：这份 PDF 会切出多少条、有没有重复、质量如何 |
| `ingestion/mineru_cloud.py` | 435 | MinerU 官方云 API 客户端 |
| `ingestion/deep_server.py` | 490 | 常驻深度解析进程（GPU 攒批） |
| `ingestion/law_text.py` | 397 | 纯文本法规直接切条款入库（不走 PDF） |
| `ingestion/material_ingest.py` | 388 | 参考资料文件切片入库（带页码溯源） |
| `ingestion/span_calibration.py` | 324 | 自动判定 span 坐标系原点（左上/左下） |
| `ingestion/middle_schema.py` | 277 | middle.json 结构归一 + 未知形状大声报错 |
| `ingestion/pypdf_backfill.py` | 253 | 用 pypdf 给老文档补条款 |
| `ingestion/preview_jobs.py` | 235 | 异步预览任务的作业管理 |
| `ingestion/reingest.py` | 173 | 「重来一次」：库内文件重新解析 |
| `ingestion/smoke_ingest.py` | 164 | 冒烟入库脚本（第一阶段造数据用） |
| `ingestion/span_verify.py` | 122 | 校验 span 坐标对不对 |
| `ingestion/docx_adapter.py` | 127 | docx → PDF（走 Word COM）+ 直读 docx 文本 |
| `ingestion/docx_ingest.py` | 95 | docx 入库入口 |
| `ingestion/parser_worker.py` | 70 | MinerU 子进程隔离 |
| `ingestion/middle_locator.py` | 54 | 找 middle.json 文件的统一入口 |
| `ingestion/__init__.py` | 0 | 空 |

---

### 2.6 knowledge（22 文件 / 6,769 行）

**职责**：管文档的"身份与位置"——分类目录、CCS 分类号、法规官方来源、别名、自动标签。

**对外入口**
- `knowledge/legal_status.py:resolve_status` —— **使用面最广的一个**，被 `api/server.py` `exports/effect_report.py` `llm/ks_answer.py` 调
- `knowledge/doc_catalog.py:classify_document` —— `exports/effect_report.py` `folder_filing_plan.py` 用
- `knowledge/folder_store.py` 的 20 个公开函数（`create_folder` `rename_folder` `move_folder` `copy_folder` `delete_folder` `add_member` `remove_member` `move_member` `copy_member` `build_folder_tree` `list_folder` `folder_scope` `folder_tree_index` `list_all_folders` `suggest_folder_for_doc` `confirm_inbox_decisions` `set_filing_state` `get_filing_state` `mark_filed` `list_pending_filing` `list_document_states`）—— `api/routes_kb_folders.py` 全用
- `knowledge/ccs_fetcher.py:fetch_ccs` `resolve_ccs` —— `ccs_backfill.py` `auto_tag.py` 用
- `knowledge/ccs_backfill.py:start_ccs_backfill` `cancel_ccs_backfill` `ccs_backfill_status` `plan_ccs_backfill` `missing_ccs_count` `missing_ccs_split` —— `routes_kb_folders.py` 用
- `knowledge/ccs_store.py:record_ccs_lookup` `apply_ccs_tag` `get_ccs_state` `ccs_states_for` `counts_by_outcome` `ccs_tag_of` —— `ccs_backfill.py` `doc_catalog.py` 用
- `knowledge/ccs_undo.py:write_undo_journal` `latest_journal_path` `revert_ccs_backfill_journal` —— `routes_kb_folders.py` 用
- `knowledge/alias_extract.py:extract_terms_from_text` `expand_with_alias` —— `api/server.py:1694` 用
- `knowledge/auto_tag.py:auto_tag` `apply_tags_to_doc_meta` —— `storage/write_queue_bootstrap.py` 用
- `knowledge/classifier.py:classify_clause` `normalize_clause_number` —— `storage/clause_repo.py` 用
- `knowledge/law_source/catalog.py:refresh_catalog` `refresh_catalog_if_due` `query_catalog` `refresh_days` —— `routes_law.py` `law_refresh.py` 用
- `knowledge/law_source/ingest.py:ingest_law_from_flk` `ingest_law_from_govcn` `find_by_source` —— `routes_law.py` 用
- `knowledge/law_source/verify.py:verify_law` `evidence_url` —— `routes_law.py` 用
- `knowledge/law_source/update.py:check_law_updates` —— `routes_law.py` 用
- `knowledge/law_source/law_refresh.py:start_law_refresh` `stop_law_refresh` —— `api/server.py:3301` 用

**依赖**：`config` `domain` `exceptions` `exports` `ingestion` `storage` `text_utils` `update`。

**写什么**：`folder` `folder_member` `doc_filing_state` `doc_ccs_state` `alias_store` `law_catalog`；更新 `doc_meta` `doc_filing_state` `folder`；删 `doc_ccs_state` `doc_filing_state` `folder` `folder_member`；磁盘 `law_source/` `law_manifest.json` `ccs_undo` 日志目录。

| 文件 | 行数 | 负责什么 |
|---|---|---|
| `knowledge/folder_store.py` | 1,514 | **全库第三大**。知识库多级目录读写：建/改/移/拷/删目录、成员管理、子树查询、归位状态 |
| `knowledge/ccs_fetcher.py` | 798 | 查中国标准分类号：官方 API → 网页抓取 → 本地表 → 种子文件，四级降级 |
| `knowledge/ccs_backfill.py` | 596 | 「补全分类号」批量补：计划、分批跑、暂停取消、进度 |
| `knowledge/law_source/catalog.py` | 558 | 法规总目录：从 flk 拉全量清单落到本地 `law_catalog` 表 |
| `knowledge/folder_filing_plan.py` | 366 | 算「每篇文档该落到哪个目录」 |
| `knowledge/law_source/verify.py` | 367 | 点开即核验某部法规现在还是不是有效 |
| `knowledge/doc_catalog.py` | 315 | 按标准号/法规层级把文档分到 4 级目录 |
| `knowledge/ccs_undo.py` | 283 | 补分类号之前先备份，可回退 |
| `knowledge/alias_extract.py` | 275 | 从"术语和定义"章抽别名，反查扩词 |
| `knowledge/ccs_store.py` | 258 | CCS 查询台账读写 |
| `knowledge/law_source/ingest.py` | 234 | 法规入库编排：官方源 → docx → PDF → 现有管线 |
| `knowledge/law_source/http.py` | 223 | 法规来源共享 HTTP 层：域白名单、限速、重试、文件校验 |
| `knowledge/classifier.py` | 195 | 条款三型分型 + 法理要素抽取 |
| `knowledge/law_source/flk_client.py` | 177 | flk.npc.gov.cn 客户端 |
| `knowledge/law_source/govcn_client.py` | 148 | gov.cn 政策文件库客户端 |
| `knowledge/law_source/convert.py` | 127 | docx → PDF（LibreOffice → WPS/Word COM） |
| `knowledge/law_source/law_refresh.py` | 114 | 法规目录定时刷新线程 |
| `knowledge/auto_tag.py` | 109 | 入库自动标签（标准号/年份/替代/施行日期/领域） |
| `knowledge/law_source/update.py` | 52 | 比对库内法规与官方源现状 |
| `knowledge/legal_status.py` | 41 | 效力字符串归一 |
| `knowledge/law_source/__init__.py` | 19 | 包说明 |
| `knowledge/__init__.py` | 0 | 空 |

（22 个文件，上表 22 行。）

---

### 2.7 llm（7 文件 / 1,883 行）

**职责**：把检索到的条款拼成 prompt 发给 DeepSeek，拿回"依据/推导/结论"三段式答案，并记录每次外发。

**对外入口**
- `llm/ks_answer.py:answer` —— **主入口**，`api/server.py:2203` 与 `api/server.py:1765`(chat SSE) 调
- `llm/ks_answer.py:attach_bboxes` `parse_llm_answer` —— `api/server.py` 用
- `llm/deepseek_client.py:stream_chat_completion` `chat_complete` `build_messages` `build_evidence_prompt` —— `ks_answer.py` 用
- `llm/egress_audit.py:record_egress` `query_egress` `export_egress` —— `api/server.py:2236/2243` 用
- `llm/jev_client.py:system_one` `noul` `choice` `score` `breaker_open` —— `jev_guard.py` `update/jev_ingest.py` 用
- `llm/jev_guard.py:judge` —— `api/server.py` 用
- `llm/fewshot.py:collect_feedback_patterns` `inject_fewshot` —— `ks_answer.py` 用

**依赖**：`config` `domain` `exceptions` `knowledge` `materials` `quality` `query` `retrieval` `storage` `text_utils` `verification`。

**写什么**：`debug_dump` 表（问答调试快照）。

| 文件 | 行数 | 负责什么 |
|---|---|---|
| `llm/ks_answer.py` | 1,154 | 取证问答主流程：证据筛/去重/封顶 → 分档 → 拼 prompt → 流式生成 → 解析 → 核验 → 置信度分级 |
| `llm/jev_client.py` | 253 | Jev 结构化判断客户端（熔断 + 外发记录） |
| `llm/deepseek_client.py` | 154 | DeepSeek 流式客户端 |
| `llm/egress_audit.py` | 138 | 统一外发记录（谁把什么发给了谁） |
| `llm/jev_guard.py` | 114 | 合规护栏判定 |
| `llm/fewshot.py` | 70 | 负向反馈聚类 → few-shot 注入 |
| `llm/__init__.py` | 0 | 空 |

---

### 2.8 materials（7 文件 / 1,715 行）

**职责**：管理"参考资料项目"——用户丢进来的网页/文件先当材料存着，审核通过后转成正式文档。

**对外入口**
- `materials/collect.py:collect_text` `looks_like_standard` `looks_like_law` `domain_of` —— `api/routes_materials.py` 用
- `materials/harvest.py:collect_url` —— `api/routes_materials.py` 用
- `materials/dedup.py:similarity` `near_duplicate` `group_by_content` `independent_source_count` `normalize_text` —— `collect.py` `authority.py` 用
- `materials/authority.py:assemble_evidence` `render_evidence` `usable_hits` —— `exports/research_report.py` 用
- `materials/locator.py:reverify_material_locators` `project_locator_summary` `locator_health` `current_fingerprint_for` `source_bytes_match` —— `api/routes_materials.py` 用
- `materials/track_l.py:track_l_intent` `plan_import` `apply_link` `import_to_library` `reconcile` —— `api/routes_materials.py:_run_track_l` 用

**依赖**：`ingestion` `knowledge` `storage` `text_utils` `update`。

**写什么**：无直接 SQL —— 全部经 `storage/material_repo.py`（`material_project` `material` `material_chunk` `material_fts`）。

| 文件 | 行数 | 负责什么 |
|---|---|---|
| `materials/track_l.py` | 347 | 材料转正式文档：判断意图、查重、建关联、导入 |
| `materials/collect.py` | 330 | 收一条文本材料：算哈希、查近似重复、判是标准还是法规 |
| `materials/authority.py` | 305 | 按来源权威性给材料排优先级、装配证据 |
| `materials/locator.py` | 297 | 校验材料来源还在不在、内容变没变 |
| `materials/harvest.py` | 266 | 抓一个 URL 的正文存成材料 |
| `materials/dedup.py` | 168 | 文本相似度与近重复分组 |
| `materials/__init__.py` | 2 | 包说明 |

---

### 2.9 quality（5 文件 / 826 行）

**职责**：判断解析质量好不好——条款体检、版面/文字层度量、分级裁决、云本地识别分歧检测。

**对外入口**
- `quality/clause_health.py:clause_health` `clause_health_html_to_text` —— `api/server.py:484` `ingestion/dry_run.py:382` 用
- `quality/grading.py:verdict_document` `grade_document` `typing_quality` `legal_element_quality` `one_line_summary` —— `ingestion/dry_run.py` 用
- `quality/recognition.py:text_layer_metrics` `page_layout_metrics` `measure_skew` `clause_ocr_confidence` —— `ingestion/dry_run.py` `ingestion/pipeline.py:1979` 用
- `quality/disagreement.py:build_disagreement_report` —— **只有 `tests/test_disagreement.py` 用**

**依赖**：`ingestion` `text_utils` `verification`。

**写什么**：不写任何东西（`grading.py` 自称"纯函数，零 IO"，`recognition.py` 自称"纯函数 + 只读"，属实）。

| 文件 | 行数 | 负责什么 |
|---|---|---|
| `quality/grading.py` | 274 | 质量分级与裁决（阈值与规则的唯一所有者） |
| `quality/recognition.py` | 253 | 文字层度量、版面度量、倾斜测量、条款 OCR 置信度 |
| `quality/disagreement.py` | 154 | 本地识别 vs 云端识别的分歧检测 |
| `quality/clause_health.py` | 93 | 条款体检 6 标签 |
| `quality/__init__.py` | 52 | 包说明 + 导出 |

---

### 2.10 query（1 文件 / 280 行）

**职责**：判断用户这句话问的是哪类问题、涉及什么主题、带了什么限定条件，并把检索词改写。

**对外入口**：`query/understanding.py` 的 10 个函数 —— `classify_intent` `detect_theme` `parse_declared` `extract_slots` `apply_condition_filter` `rank_with_hierarchy` `hierarchy_label` `sufficiency_note` `refine_search_query` `detect_correction`。被 `api/server.py:1792/3173` 和 `llm/ks_answer.py:800` 调。

**依赖**：**零**。

**写什么**：不写。

| 文件 | 行数 | 负责什么 |
|---|---|---|
| `query/understanding.py` | 280 | 意图分类、主题识别、槽位抽取、检索词改写 |

---

### 2.11 retrieval（5 文件 / 1,270 行）

**职责**：把一句话变成一批相关条款——六路召回、融合排序、重排、术语桥。

**对外入口**
- `retrieval/hybrid_engine.py:perform_hybrid_search` `search_with_details` `expand_query_with_history` `expand_evidence_chain` `extract_modality_from_query` `set_db_override` —— `api/server.py` `llm/ks_answer.py` 用
- `retrieval/embedder.py:embed_query` `embed_batch` `is_available` `health` `offline_reason` —— `storage/clause_repo.py` `api/server.py:warm_retrieval_stack` 用
- `retrieval/reranker.py:rerank` `is_available` `offline_reason` —— `hybrid_engine.py` 用
- `retrieval/term_bridge.py:bridge_search` `TermIndex` `extract_term_entries` `merge_round_robin` `topk_by_cos` —— `hybrid_engine.py` 用

**依赖**：`config` `domain` `exceptions` `storage` `text_utils`。

**写什么**：不写。

| 文件 | 行数 | 负责什么 |
|---|---|---|
| `retrieval/hybrid_engine.py` | 751 | 六路召回（FTS/向量/标准号/别名/…）+ RRF 融合 + 条款链扩展 |
| `retrieval/term_bridge.py` | 311 | 术语桥：把口语词映射到标准术语再检索 |
| `retrieval/embedder.py` | 129 | fastembed bge-small-zh 向量模型封装 |
| `retrieval/reranker.py` | 79 | 重排 |
| `retrieval/__init__.py` | 0 | 空 |

---

### 2.12 settings（3 文件 / 684 行）

**职责**：安全地存 API Key（Windows DPAPI 加密），并清理旧的环境变量/注册表遗留。

**对外入口**
- `settings/api_credentials.py:set_credential` `get_status` `test_channel` `import_system_layer` `stored_channels` `legacy_status` `system_layer_status` `clean_system_layer` `adopt_legacy` `UnknownChannel` `InvalidModelVersion` —— `api/routes_settings.py` 用
- `settings/secret_store.py:read_value` `has_value` `write_values` `stored_names` `store_path` `protect` `unprotect` `SecretStoreError` —— `config.py:_read_secret` 用

**依赖**：`config` `ingestion`。

**写什么**：磁盘 `<data_dir>/secrets.json`（DPAPI 加密后的密文）。

| 文件 | 行数 | 负责什么 |
|---|---|---|
| `settings/api_credentials.py` | 397 | 凭据读写 + 系统层现状/清理/迁移 + 连通性自测 |
| `settings/secret_store.py` | 286 | DPAPI 加解密 + 文件锁 + 原子写 |
| `settings/__init__.py` | 1 | 一行说明 |

---

### 2.13 storage（13 文件 / 3,198 行）

**职责**：所有落库动作的落点——连接管理、schema 初始化、各业务表读写、备份、单写者队列。

**对外入口**
- `storage/sqlite_db.py:get_db_connection` —— **全仓最热的函数，400 处引用 / 97 个文件**；`write_transaction` `init_schema` `load_vec_extension` `list_tables` `close_thread_connection` `close_connections_under` `close_all_connections`
- `storage/clause_repo.py` 的 20 个公开函数 —— `ingestion` `llm` `retrieval` `knowledge` 用
- `storage/user_data.py` 的 33 个函数 —— `api/server.py` 用
- `storage/material_repo.py` 的 22 个函数 —— `materials` `exports` `api/routes_materials.py` 用
- `storage/channel_repo.py` 的 15 个函数 —— `api/routes_channels.py` `update` 用
- `storage/backup.py:create_snapshot` `list_snapshots` `restore_snapshot` —— `api/server.py:2425–2437` 用
- `storage/versioning.py:version_chain` `compare_docs` —— `api/server.py:1517/1662` 用
- `storage/doc_delete.py:delete_documents` —— `api/server.py:905` `knowledge/folder_store.py:693` 用
- `storage/impact.py:analyze_impact` —— `api/server.py:2448` 用
- `storage/debug_dump_retention.py:prune` —— `api/server.py` 用
- `storage/write_queue.py:WriteWorker` `enqueue` `wait_until_drained` + `write_queue_bootstrap.py:start_write_worker` `stop_write_worker` —— `api/server.py:3294` 用

**依赖**：`config` `domain` `exceptions` `ingestion` `knowledge` `retrieval` `settings` `text_utils`。

**写什么**：`clause_revision` `source_span` `clause_fts` `clause_vec` `doc_meta` `doc_page_geometry` `evidence_edge` `user_bookmark` `user_doc_bookmark` `user_bookmark_folder` `user_annotation` `project_list` `obligation_list` `material_project` `material` `material_chunk` `material_fts` `update_channel` `snapshot_meta` `write_queue` `remapping_queue` `clause_patch` `event_log`；删 `debug_dump` `legal_obligation` `watch_list` `update_change_event` `folder_member` `doc_filing_state`。

| 文件 | 行数 | 负责什么 |
|---|---|---|
| `storage/clause_repo.py` | 832 | 条款仓储：写 `clause_revision`/`source_span`/`clause_fts`/`clause_vec`、补列迁移、补丁、`fetch_full_clause`、`resolve_clause` |
| `storage/channel_repo.py` | 455 | 渠道台账读写 + 审计 |
| `storage/material_repo.py` | 410 | 材料项目/材料/切片读写 |
| `storage/user_data.py` | 409 | 收藏、批注、项目清单、义务清单、**收藏夹** |
| `storage/sqlite_db.py` | 357 | 连接管理（线程局部 + 注册表）、`init_schema`、补列 |
| `storage/backup.py` | 143 | 快照备份与回滚（含 secrets 快照） |
| `storage/write_queue.py` | 136 | 单写者队列 |
| `storage/versioning.py` | 126 | 版本替代链与文档对比 |
| `storage/doc_delete.py` | 108 | 批量删文档（含向量表清理） |
| `storage/debug_dump_retention.py` | 81 | debug_dump 保留策略 |
| `storage/impact.py` | 73 | 影响面分析 |
| `storage/write_queue_bootstrap.py` | 68 | 写队列消费端接线 |
| `storage/__init__.py` | 0 | 空 |

---

### 2.14 update（36 文件 / 8,811 行）

**职责**：回答"这个标准/法规现在还是不是最新、有没有被废止"——去 13 个官方站点查，把变化记下来。

**对外入口**
- `update/inspector.py:create_inspect_batch` `run_batch` `pause_batch` `resume_batch` `get_inspect_batch` `select_standard_nos` `daily_budget_limit` `budget_used_today` `budget_remaining` `captcha_wait_events` `request_pause` `judge_result` `ProbeOutcome` —— `api/routes_update.py` 用
- `update/change_repo.py:create_batch` `get_batch` `list_batches` `update_progress` `append_change` `mark_ack` `manual_status` —— `inspector.py` `routes_update.py` 用
- `update/announce.py:get_sources` `add_source` `update_source` `remove_source` `request_scan` `get_scan_state` `list_items` `export_announce_xlsx` `parse_list_page` `discover_next_pages` `is_private_url` `looks_like_article` `normalize_url` `url_hash` —— `routes_update.py` 用
- `update/discover.py:classify` `search` `download_later_list` `download_later_add` `download_later_remove` `load_seed` —— `routes_update.py` 用
- `update/web_ingest.py:ingest_pending` `ingest_summary` `triage_pending` `ingest_announcement` `classify_change_signal` `classify_status` `classify_hierarchy` `classify_scope` `extract_body_text` `page_title` —— `routes_update.py` 用
- `update/report.py:export_batch_report_xlsx` `collect_batch_report_data` `monthly_trend` —— `routes_update.py` 用
- `update/data_package.py:export_package` `import_package` `brief_counts` —— `routes_update.py` 用
- `update/channels/base.py` —— **被 5 个子系统跨目录引用**（`knowledge/ccs_fetcher.py` `materials/harvest.py` `ingestion/bulk.py` `api/routes_update.py` `update/*`）：`norm_no` `query_no` `strip_year` `derive_change_type` `map_state_text` `looks_like_captcha` `default_transport` `ChannelAdapter` `ChannelResult` `UpdateError` `upd_log` `recordable` `CurlCffiTransport` `HttpxTransport` `httpx_usable`
- `update/channels/__init__.py:ADAPTER_CLASSES` —— `inspector.py:48` 用
- `update/channels/routing.py:fallback_chain` `select_chain` `first_route` `segment_matches` —— `inspector.py` 用
- `update/channels/ledger_chain.py:chain_for_number` `ledger_fallback_chain` `segments_report` `ledger_chain_report` —— `inspector.py` 用
- `update/channels/question_router.py:channels_for` `route_report` `unanswerable_classes` —— `inspector.py` 用
- `update/channels/class_outcomes.py:conclusion_for` `build_classes` `build_classes_for_miss` —— `inspector.py` 用
- `update/channel_probe.py:probe_channel` `probe_channels` `load_targets` `failure_kind` —— `routes_channels.py` 用
- `update/channel_test.py:set_test_case` `get_test_case` `run_channel_test` `identify_standard_no` —— `routes_channels.py` 用
- `update/channel_answers.py:load_answers` `answers_of` `verdict_of` `channels_for` `coverage` —— `question_router.py` 用
- `update/download_gate.py:download_ask_reason` `handle_download` —— `routes_update.py` 用
- `update/jev_ingest.py:judge_one` `judge_many` —— `web_ingest.py` 用
- `update/subscriptions.py:get_subscriptions` `set_subscriptions` —— `routes_update.py` `inspector.py` 用
- `update/scheduler.py:UpdateScheduler` —— `scheduler_runner.py` 用
- `update/scheduler_runner.py:start_update_scheduler` `stop_update_scheduler` `tick_and_run` `is_running` —— `api/server.py:3311` 用

**依赖**：`config` `exceptions` `exports` `ingestion` `knowledge` `llm` `storage` `text_utils`。

**写什么**：`update_check_batch` `update_change_event` `announcement_observed` `update_channel` `channel_test_case` `app_config` `bulk_import_batch` `event_log`；更新 `doc_meta`。

| 文件 | 行数 | 负责什么 |
|---|---|---|
| `update/inspector.py` | 937 | 巡检编排器：分层选号、并发探测、预算控制、暂停恢复、验证码挂起 |
| `update/announce.py` | 841 | 公告发现：自定义公告源、扫描列表页、去重、xlsx 导出 |
| `update/discover.py` | 632 | 找标：口语 → CCS 分类映射（含 LLM 分类）、网络检索、待下载清单 |
| `update/web_ingest.py` | 506 | 部委公告正文入库（调 `ingestion/law_text.py`） |
| `update/channels/base.py` | 450 | 渠道适配器基座：错误类型、标准号归一、传输层、抽象基类 |
| `update/channel_probe.py` | 356 | 渠道健康探针 |
| `update/channels/ledger_chain.py` | 372 | 台账驱动的降级链 |
| `update/data_package.py` | 313 | 全量数据包导出/导入 |
| `update/channels/ndls.py` | 312 | ndls 渠道适配器 |
| `update/channels/proxy_rotate.py` | 267 | 代理轮换 |
| `update/report.py` | 268 | 更新检查结果 xlsx |
| `update/channels/ttzb.py` | 264 | ttzb 渠道适配器 |
| `update/change_repo.py` | 280 | 变更批次/事件仓储 |
| `update/channels/question_router.py` | 237 | 按问题选渠道 |
| `update/channels/cssn.py` | 209 | cssn 渠道适配器 |
| `update/channels/class_outcomes.py` | 183 | 五类结论组装 |
| `update/scheduler_runner.py` | 177 | 更新巡检定时线程 |
| `update/channels/govcn_announce.py` | 184 | gov.cn 公告检索 + PDF 存档 |
| `update/channels/mee.py` | 175 | mee 渠道适配器 |
| `update/channels/official_gb.py` | 161 | 国家标准全文公开系统适配器 |
| `update/scheduler.py` | 170 | 定时巡检调度器（`start()` 无人调用，见 §五） |
| `update/download_gate.py` | 146 | 下载新版附件的审批门 |
| `update/channels/hbba.py` | 149 | hbba 渠道适配器 |
| `update/channels/routing.py` | 138 | 渠道索引与路由 |
| `update/channels/mem_gov.py` | 130 | mem_gov 渠道适配器 |
| `update/channel_test.py` | 120 | 渠道连通性测试 |
| `update/jev_ingest.py` | 117 | 公告入库的 Jev 判层 |
| `update/channels/std_samr_hb.py` | 115 | std_samr_hb 渠道适配器 |
| `update/channel_answers.py` | 108 | 五类能力表 |
| `update/channels/mohurd.py` | 106 | mohurd 渠道适配器 |
| `update/channels/laws_db.py` | 94 | 国家法律法规数据库适配器 |
| `update/channels/web_fallback.py` | 91 | 网络逐号补漏搜索 |
| `update/subscriptions.py` | 56 | 领域订阅存取 |
| `update/__init__.py` | 54 | 包说明 + 导出 |
| `update/channels/__init__.py` | 66 | `ADAPTER_CLASSES` 注册表 |
| `update/channels/dbba.py` | 27 | dbba 渠道适配器 |

（36 个文件，上表 36 行。）

---

### 2.15 verification（3 文件 / 427 行）

**职责**：检查大模型答出来的东西有没有编——引用的条款号在证据里到底存不存在。

**对外入口**
- `verification/typed_verifier.py:verify_llm_output` —— `api/server.py:2064` `llm/ks_answer.py:627` 用
- `verification/patch_guard.py:check_patch` —— `api/server.py:370` `quality/recognition.py:63/227` 用

**依赖**：`domain` `knowledge`。

**写什么**：不写。

| 文件 | 行数 | 负责什么 |
|---|---|---|
| `verification/typed_verifier.py` | 328 | 核验 LLM 输出里的引用/数值是否在证据中 |
| `verification/patch_guard.py` | 99 | 纠错补丁防乱检测（CJK 比例、不可打印字符比例） |
| `verification/__init__.py` | 0 | 空 |

---

### 2.16 vision（2 文件 / 117 行）

**职责**：对一张图片做本地 OCR，拿识别出的文字去库里反查相关条款。

**对外入口**：`vision/local_vision.py:vision_locate` —— `api/server.py:2415` 用。

**依赖**：`config` `exceptions` `figure_redraw` `retrieval`。

**写什么**：磁盘 `<data_dir>/vision_tmp/<图片名>/`。

| 文件 | 行数 | 负责什么 |
|---|---|---|
| `vision/local_vision.py` | 117 | 图片 OCR + 检索反查 |
| `vision/__init__.py` | 0 | 空 |

---

### 2.17 `src/core/` 根下 9 个散文件（3,821 行）

| 文件 | 行数 | 负责什么 | 对外入口 | 依赖 | 写什么 |
|---|---|---|---|---|---|
| `config.py` | 341 | 读环境变量/注册表/加密存储，拼成 `Settings` 对象 | `get_settings` `reset_settings` `Settings` `MINERU_CLOUD_*` | `settings` | 无（只算路径） |
| `text_utils.py` | 2,162 | OCR 文本清洗 + 标准号归一 + 分词 + HTML 转文本 | 40 个公开函数（见 §2.17.1） | **零** | 无 |
| `middle_geo.py` | 319 | 读 MinerU middle.json，提供图片/表格坐标 | `load` `MiddleGeo` | `ingestion` | 内存缓存 |
| `figure_redraw.py` | 291 | 流程图结构化识别 + 矢量重绘 | `try_redraw` `get_ocr` | **零** | 无 |
| `formula_locator.py` | 241 | 在 PDF 里按公式号定位公式 | `locate_formula` `locate_eq_by_number` | `middle_geo` | 无 |
| `figure_locator.py` | 222 | 在 PDF 里按图号定位图 | `locate_figure` `locate_middle_figure` `locate_middle_figure_full` `locate_middle_caption` | `ingestion` `middle_geo` | 无 |
| `supervisor.py` | 134 | 看门狗：子进程崩了就重启，连崩 3 次熔断 | `EngineSupervisor` `main` | `api` `config` | 磁盘 `engine.session.json` |
| `exceptions.py` | 55 | 统一异常体系（1 基类 + 9 子类） | `KnowledgeStationError` + 9 子类 | **零** | 无 |
| `main.py` | 56 | 进程入口：修 `NO_PROXY`、预热 OCR、调 `run()` | `python -m src.core.main` | `api` `figure_redraw` | 无 |

#### 2.17.1 `text_utils.py` 到底装了什么

2,162 行，**61 个顶层函数，0 个类**。40 个公开、21 个私有。按功能分五块：

| 块 | 函数 | 干什么 |
|---|---|---|
| OCR 文本清洗（约 1,100 行） | `strip_formula_leader` `normalize_pua_latin` `normalize_pua_separators` `strip_block_noise` `reflow_sqrt_formulas` `normalize_math_symbols` `glue_ocr_spaced_units` `glue_spaced_formulas` `weave_meaning_marks` `normalize_wraps` `normalize_label_comma` `normalize_area_subscript` `strip_watermark_lines` `clean_clause_text` `strip_duplicate_suffix` `strip_ocr_source_suffix` | 修 OCR 出来的乱码、粘连、PUA 字符、水印行 |
| LaTeX / 公式（约 500 行） | `latex_to_text` `clean_latex_for_katex` `clean_eq_tags` `katex_sym_html` `pua_bond_dash_html` `sup_unit_exponents_html` `sup_unit_exponents_text` `space_clause_numbers_html` `space_clause_numbers_text` | 公式在 LaTeX/纯文本/HTML 三种形态间转换 |
| HTML（约 350 行） | `html_to_text` `html_unescape` `strip_tags` `strip_embedded_table_text` | HTML → 纯文本 |
| **标准号归一（约 150 行）** | `canon_standard_no` `store_standard_no` `store_standard_name` `standard_key` `standard_no_key` `law_name_key` `clean_standard_name` | **4 个不同名但同族的归一函数**，见 §四 |
| 分词 / FTS（约 200 行） | `segment_for_fts` `fts_match_expr` `_porter_stem` `_latin_prefix_token` | jieba 分词 + FTS5 查询表达式构造 |
| 杂项 | `looks_like_binary` `looks_like_binary_bytes` | 判断字节流是不是二进制 |

**实测：`text_utils.py` 的 40 个公开函数，全仓外部零引用的是 0 个**（全部至少被 1 个文件调用）。
但其中 8 个**只被 `text_utils.py` 自己或测试调用**，见 §五。

---

## 三、重复实现清单

共 **15 条**。

> 交叉核对说明：本仓已有机器尺子 `docs/uniformity/ast-dupes-gated.json`（AST 函数体同构检测，`min_stmts=4`，当前 13 组 / 31 处命中）。
> 其中落在 `src/core/` 的有 3 组，已并入本清单（§3.1、§3.14、§3.15）。其余 10 组在 `tests/` 与 `scripts/`，不属本次范围。

### 3.1 `_xlsx_header_style` —— 三份一模一样的 xlsx 表头样式函数

| 出现处 | 行数 |
|---|---|
| `exports/effect_report.py:_xlsx_header_style` | 400 行文件中 |
| `update/announce.py:_xlsx_header_style` | 841 行文件中 |
| `update/report.py:_xlsx_header_style` | 268 行文件中 |

三处签名完全相同：`def _xlsx_header_style(ws, row: int, cols: int) -> None:`。
**已由 AST 证据坐实为逐字相同**：`docs/uniformity/ast-dupes-gated.json` 的分组 `991db9f79b781cc2` 把这 3 处归为同一组，每处 6 条语句（`min_stmts=4`）。
**能否合一**：能，且证据充分 —— 抽到 `exports/` 下一个共用模块即可。

### 3.2 `_exports_dir` + `_safe_name` —— 两份完全同名同职的函数

| 出现处 |
|---|
| `exports/report_export.py:_exports_dir` / `_safe_name` |
| `exports/research_report.py:_exports_dir` / `_safe_name` |

两者都返回 `get_settings().data_dir / "exports"`。加上 `llm/egress_audit.py` 里直接拼 `get_settings().data_dir / "exports"`，**"exports 目录"这个路径一共在 3 个文件里各算了一遍**。
**能否合一**：能。这是一条硬重复。

### 3.3 `_expand_title_clauses` —— 两份，注释自己承认是复制

| 出现处 | 说明 |
|---|---|
| `api/server.py:2525` | 2539 行注释写「与 ks_answer._expand_title_clauses 同步放宽」 |
| `llm/ks_answer.py:1113` | 1110 行注释写「与 server._expand_title_clauses 同语义，但可直接被检索侧复用」 |

**差异**：`server.py` 版接收 `evidences` 列表对象并回写 `_fetch_clause`；`ks_answer.py` 版在 `ranked` 上跑。两者都用同一个正则 `r'[0-9A-Z]+(?:[.][0-9A-Z]+)*'` 判标题条款。
**能否合一**：能，且**应该合一** —— 注释已经明说"同步放宽"，意思是改一处必须记得改另一处。

### 3.4 标准号归一 —— 6 个模块各写了一套

| 函数 | 文件 |
|---|---|
| `canon_standard_no` | `text_utils.py` |
| `store_standard_no` | `text_utils.py` |
| `standard_key` | `text_utils.py` |
| `standard_no_key` | `text_utils.py` |
| `norm_no` | `update/channels/base.py` |
| `query_no` | `update/channels/base.py` |
| `strip_year` | `update/channels/base.py` |
| `_norm_no` | `update/channel_test.py` |
| `clean_standard_no` | `knowledge/ccs_fetcher.py` |
| `_canon` / `_core` | `update/channels/ttzb.py` |
| `_std_type` / `_hier_from_no` | `ingestion/pipeline.py` |

`text_utils.py:1283` 的注释**自己写着**：「与 `update.channels.base.norm_no` 同口径，额外抹平全角与多种破折号」。也就是说同一个概念，`text_utils` 有 4 个名字，`channels/base` 有 3 个名字，另有 4 个模块各写自己的。
**能否合一**：能。这是本次调查里**涉及面最广的一条**（`standard_no` 字段全仓 1,472 处引用 / 152 个文件）。

### 3.5 `html_to_text` —— 4 份

| 函数 | 文件 | 说明 |
|---|---|---|
| `html_to_text` | `text_utils.py:1752` | 完整实现 |
| `_html_to_text` | `api/server.py:2578` | **薄壳**，转调 `quality.clause_health_html_to_text` |
| `_html_to_text_compact` | `llm/ks_answer.py` | 独立实现（证据 prompt 用） |
| `clause_health_html_to_text` | `quality/clause_health.py` | 数据体检与入库预览共用 |

**差异**：`server.py` 版是明确的转发壳（注释写「唯一所有者…这里保留同名薄壳」）；`ks_answer.py` 版是独立实现，limit 默认值不同（`EVIDENCE_TABLE_MAX` vs `400` vs `TABLE_MD_LIMIT`）。
**能否合一**：`server.py` 的壳可以删。`ks_answer.py` 那份需要先比对输出是否等价。

### 3.6 `app_config` 读写 —— 5 个模块各写一遍

| 位置 | 函数 |
|---|---|
| `update/inspector.py:91/99` | `get_config` / `set_config` |
| `update/announce.py:182/195` | `_read_json_key` / `_write_json_key` |
| `update/subscriptions.py:21/36` | `get_subscriptions` / `set_subscriptions`（内联 SQL） |
| `update/discover.py:600/620` | 内联 SQL（两处各写一遍） |
| `knowledge/law_source/catalog.py:97` | `_read_config` / `_write_config` |

5 个模块、**9 处 `SELECT config_value FROM app_config`**、**6 处 `INSERT INTO app_config`**。
**能否合一**：能。应有一个 `storage/app_config.py`。

### 3.7 `text_hash` —— 两份同名同职

| 出现处 |
|---|
| `ingestion/material_ingest.py:text_hash` |
| `materials/collect.py:text_hash` |

**能否合一**：能（需先确认两处哈希算法是否一致 —— **未读**函数体）。

### 3.8 `page_title` —— 两份同名不同职

| 出现处 | 返回 |
|---|---|
| `materials/harvest.py:page_title` | `str \| None` |
| `update/web_ingest.py:page_title` | `str` |

**差异**：一个可能返回 None，一个保证返回字符串。
**能否合一**：能，但要注意 None 语义差异。

### 3.9 `domain_of` —— 两份

| 出现处 |
|---|
| `materials/authority.py:_domain_of` |
| `materials/collect.py:domain_of` |

**能否合一**：能，同一个目录内，最容易。

### 3.10 目录 CRUD —— `storage/user_data.py` 与 `knowledge/folder_store.py` 各一套

| 动作 | `user_data.py`（收藏夹） | `folder_store.py`（知识库目录） |
|---|---|---|
| 建 | `create_folder(folder_name)` | `create_folder(name, parent_id, sort)` |
| 改名 | `rename_folder(folder_id, new_name)` | `rename_folder(folder_id, new_name)` |
| 删 | `delete_folder(folder_id)` | `delete_folder(folder_id, mode)` |
| 列表 | `list_folders()` | `list_all_folders(q, limit, offset)` |
| 移动 | `move_bookmark_to_folder` / `move_doc_bookmark_to_folder` | `move_member` / `move_folder` |

**表不同**（`user_bookmark_folder` vs `folder` + `folder_member`），**ID 前缀不同**（`bmf_` vs `fld_`）。
`api/server.py:3267` 的注释明确写「⚠ 与收藏夹（/api/v1/bookmark-folders）**无关**」。
**能否合一**：**不能直接合一** —— 这是两个不同业务对象（单层收藏夹 vs 无限层级知识库目录）。但**命名完全撞车**（见 §四 第 1 条）。

### 3.11 条款切分 —— 4 套

| 函数 | 文件 | 输入 |
|---|---|---|
| `split_items_into_clauses` | `ingestion/pipeline.py` | MinerU middle item 列表 |
| `split_gb_text` | `ingestion/law_text.py` | 纯文本（国标） |
| `split_law_text` | `ingestion/law_text.py` | 纯文本（法规） |
| `split_law_enum_text` | `ingestion/law_text.py` | 纯文本（法规枚举） |
| `split_into_clauses` | `ingestion/smoke_ingest.py` | blocks 列表（**冒烟脚本用，已死**） |

**差异**：前 4 个输入形态确实不同（结构化 item vs 纯文本 vs 枚举），不算重复；`smoke_ingest.py` 的 `split_into_clauses` 是第一阶段遗留，全仓 0 外部引用。
**能否合一**：`smoke_ingest.py` 那份应删。

### 3.12 `_read_env_or_registry` 与 `_read_any_var` —— 同一取值的两套链

| 函数 | 文件 | 语义 |
|---|---|---|
| `_read_env_or_registry(name, default)` | `config.py:77` | env → HKCU\Environment → default |
| `_read_first(names, default)` | `config.py:91` | 按名字顺序走 `_read_env_or_registry` |
| `_read_any_var(name)` | `settings/api_credentials.py:177` | env → 注册表（**函数体就是 `os.environ.get(...) or _read_registry_var(name)`**） |
| `_read_registry_var(name)` | `settings/api_credentials.py` | 只读注册表 |

`api_credentials.py:178` 的注释自己写：「与 `src.core.config` 的同名语义一致」「两处语义不同，别当成同一个东西」。
**能否合一**：**部分能** —— 函数体确实等价，但注释解释了跨名字时的顺序语义不同（`config._read_first` 是"名字优先于来源"）。这是**可以合一但需要小心**的一条。

### 3.13 领域词表 —— `update/subscriptions.py` 与 `knowledge/auto_tag.py` 两份，注释声称同源

| 位置 | 内容 |
|---|---|
| `update/subscriptions.py:16` `DOMAIN_VOCAB` | 9 个领域名：建筑/消防/安全/环保/化工/合同/数据/劳动/卫生 |
| `knowledge/auto_tag.py:20` `_DOMAIN_KEYWORDS` | 同样 9 个领域名，每个后面挂关键词元组 |

`subscriptions.py:3` 注释写：「领域词表与入库自动标签同源（`src/core/knowledge/auto_tag.py` `_DOMAIN_KEYWORDS`）」；
`subscriptions.py:15` 又写：「单点同步：此处为唯一常量，`auto_tag` 引用该处避免漂移」。
**实测：`auto_tag.py` 全文没有 import `subscriptions`**（`auto_tag.py` 的 import 只有 `re` `dataclass` `storage.sqlite_db` `text_utils` `json`）。
**结论：注释声称的"单点同步"没有实现 —— 两份词表是硬编码的两份，靠人记着同步。**

### 3.14 文件 sha256 —— 两份，AST 判为逐字同构

| 出现处 | 函数名 |
|---|---|
| `storage/backup.py:43` | `_checksum` |
| `update/data_package.py:97` | `_file_sha256` |

**证据**：`docs/uniformity/ast-dupes-gated.json` 分组 `dc43e4b07728d24c`，两处各 5 条语句，函数体同构。
**差异**：只有名字不同。这是**名字不一致掩盖了同构实现**的典型例子。
**能否合一**：能。应抽成一个 `storage/` 或 `text_utils` 下的 `file_sha256(path)`。

### 3.15 `_fetch_text` —— 两个渠道适配器各写一份，AST 判为逐字同构

| 出现处 | 函数名 |
|---|---|
| `update/channels/mem_gov.py:103` | `_fetch_text` |
| `update/channels/mohurd.py:82` | `_fetch_text` |

**证据**：`docs/uniformity/ast-dupes-gated.json` 分组 `bbe2efd50c8020f5`，两处各 5 条语句。
**能否合一**：能。13 个渠道适配器里至少这两个的取文本逻辑完全一样，应上提到 `channels/base.py`（那里已经有 `ChannelAdapter` 基类和传输层）。

---

## 四、命名不一致清单

共 **9 条**。

### 4.1 "文件夹/目录" —— 同一个词指两个完全不同的东西

| 叫法 | 位置 | 实际含义 | 表 | ID 前缀 |
|---|---|---|---|---|
| `folder` / `folder_id` | `storage/user_data.py`（`create_folder` `rename_folder` `delete_folder` `list_folders` `get_folder`） | **单层收藏夹** | `user_bookmark_folder` | `bmf_` |
| `folder` / `folder_id` | `knowledge/folder_store.py`（`create_folder` `rename_folder` `delete_folder` `list_all_folders` `move_folder` `copy_folder`） | **无限层级知识库目录** | `folder` + `folder_member` | `fld_` |

两个模块有 **4 个完全同名的公开函数**：`create_folder` `rename_folder` `delete_folder`（`list_folders` vs `list_all_folders` 只差一个词）。
`api/server.py:3267` 靠注释提醒后来者"无关"。

### 4.2 标准号字段 —— 4 种叫法

| 叫法 | 出现次数 | 文件数 |
|---|---|---|
| `standard_no` | 1,472 | 152 |
| `std_no` | 26 | 7 |
| `standard_number` | 6 | 6 |
| `standardNo`（驼峰） | 8 | **1**（`update/channels/ttzb.py`） |

`ttzb.py` 是唯一用驼峰的文件，且用了 8 次。

### 4.3 标准号归一函数 —— 11 个不同名字（见 §3.4）

`canon_standard_no` / `store_standard_no` / `standard_key` / `standard_no_key` / `norm_no` / `query_no` / `strip_year` / `_norm_no` / `clean_standard_no` / `_canon` / `_core`

### 4.4 条款号字段 —— 3 种叫法

| 叫法 | 出现次数 | 文件数 |
|---|---|---|
| `clause_number` | 395 | 73 |
| `clause_no` | 22 | 10 |
| `clause_id` | 32 | 10 |

`clause_id` 与 `clause_number` 混用在 `api/server.py`（68 次 / 4 次）、`storage/clause_repo.py`（19 / 3）。

### 4.5 "取数据"的动词 —— 7 种前缀

| 前缀 | 出现次数 | 文件数 |
|---|---|---|
| `def get_` | 33 | 19 |
| `def _get_` | 4 | 4 |
| `def load_` | 10 | 9 |
| `def _load_` | 11 | 10 |
| `def fetch_` | 14 | 8 |
| `def _fetch_` | 4 | 4 |
| `def read_` | 1 | 1（`settings/secret_store.py`） |
| `def _read_` | 20 | 7（其中 13 个在 `config.py`） |

同一个"读一个值"的动作，`config.py` 用 `_read_*`，`update/*` 用 `get_config`/`_read_json_key`，`channel_probe.py` 用 `load_targets`，`channels/base.py` 用 `fetch_*`。

### 4.6 数据目录 —— 3 种取法

| 取法 | 出现次数 |
|---|---|
| `get_settings().data_dir` | 44 处 / 26 文件 |
| `os.environ.get("KS_DATA_DIR")` | 直接读（`config.py:52` 与 `settings/secret_store.py:_resolve_data_dir`） |
| `_default_data_dir()` | 4 处（`config.py` 3 次 + `secret_store.py` 4 次） |

**注意**：`settings/secret_store.py:_resolve_data_dir` 和 `config.py:_default_data_dir` 是**两份各自算数据目录**的实现（`_default_data_dir` 全仓 13 处引用，`_resolve_data_dir` 3 处，都在 `secret_store.py` 自己）。**未逐行比对两者是否等价** —— 这是 `tests/test_secret_store.py` 覆盖的区域。

### 4.7 数据库连接 —— 2 种写法

| 写法 | 出现 |
|---|---|
| `get_db_connection()` | 400 处 / 97 文件（主流） |
| `sqlite3.connect(str(get_settings().db_path))` | **`ingestion/span_calibration.py:calibrate`**、**`ingestion/span_verify.py:_db`** 两处绕过统一连接管理 |

绕过的那两处**不加载 sqlite-vec 扩展、不做 WAL/busy_timeout 配置**，与其余 97 个文件行为不一致。

### 4.8 环境变量 —— 30 个 `KS_*`，其中 10 个只在 `ingestion/` 里读

`KS_DATA_DIR` `KS_MODELS_DIR` `KS_BACKUP_DIR` `KS_SOFFICE` `KS_VERIFY_CACHE_OFF` `KS_CCS_SEED_FILE` `KS_LLM_*`(6) `KS_JEV_API_KEY` `KS_MINERU_*`(8) `KS_DEEP_*`(6) `KS_GPU_LOCK*`(3) `KS_VLM_ONLY`

**问题**：`config.py` 的 `Settings` 只收 12 个；`ingestion/deep_server.py`（5 个）、`ingestion/mineru_adapter.py`（8 个）、`ingestion/mineru_cloud.py`（1 个）里共 14 个 `KS_*` 是**在模块里直接 `os.environ.get()` 读的**，`config.py` 根本不知道它们存在。这与 `AGENTS.md` 的「No hardcoded tunables in plugins：deployment-varying choices are validated Config fields changeable from cordis.yml」口径不一致。

### 4.9 五色/效力 —— 叫法分散

`legal_status`（410 处 / 69 文件）是主流；但 `exports/effect_report.py` 里另有一套 `STATUS_COLOR` / `COLOR_ORDER` / `_normalize_colors` / `_colors_of`，`knowledge/folder_store.py:936` 又去 import 它们。同一个"五色"概念横跨 `knowledge`→`exports` 反向依赖（见 §六 第 3 条）。

---

## 五、死代码清单

### 5.1 整个模块死（全仓 0 处生产 import，仅测试引用）

| 模块 | 证据命令 | 结果 |
|---|---|---|
| `quality/disagreement.py`（154 行） | `Get-ChildItem src -Recurse -Filter *.py \| Select-String -Pattern 'quality\.disagreement'` | `src` 命中 **0** 处；`tests/test_disagreement.py` 是唯一消费者 |

**说明**：`quality/__init__.py` 也没有 re-export 它。这是一个**只有测试在用**的模块 —— 测试绿着，生产代码从没调过。

### 5.2 完全死符号（本文件内也不调用）

| 符号 | 文件 | 证据命令 | 结果 |
|---|---|---|---|
| `ConfigError` | `exceptions.py` | `Select-String -Pattern '\bConfigError\b'` | 仅 `exceptions.py` 1 处（就是定义行） |
| `AuthError` | `exceptions.py` | 同上 | 仅定义行 |
| `RetrievalError` | `exceptions.py` | 同上 | 仅定义行 |
| `DuplicateDocumentError` | `exceptions.py` | 同上 | 仅定义行 |
| `get_obligation_list` | `storage/user_data.py` | `\bget_obligation_list\b` | 仅 `user_data.py` 1 处（定义行） |
| `update_obligation_list` | `storage/user_data.py` | `\bupdate_obligation_list\b` | 仅定义行 |
| `subscriptions_as_tags` | `update/subscriptions.py` | `\bsubscriptions_as_tags\b` | 仅定义行。docstring 写「tier0 组装用…inspector 读取路径」，但 `inspector.py:205` 调的是 `get_subscriptions()`，**不是** `subscriptions_as_tags()` |
| `table_exists` | `knowledge/ccs_store.py` | `\btable_exists\b` | 仅定义行 |

**8 条，每条都是"定义了、注释说它有用、实际零调用"。**

`exceptions.py` 55 行里 10 个异常类，实测外部引用情况：

| 类 | 引用文件数 | 结论 |
|---|---|---|
| `KnowledgeStationError` | 36 | 活 |
| `LLMError` | 9 | 活 |
| `ParserError` | 3 | 活 |
| `StorageError` / `ParserTimeoutError` / `VectorEngineOfflineError` | 各 2 | 活（各自 1 个消费方） |
| **`ConfigError`** | **1**（仅定义处） | **死** |
| **`DuplicateDocumentError`** | **1** | **死** |
| **`RetrievalError`** | **1** | **死** |
| **`AuthError`** | **1** | **死** |

**10 个里 4 个是死的（40%）。**

### 5.3 只有自己文件在用（公开名字，跨文件零引用）

| 符号 | 文件 | 外部引用 | 文件内调用 |
|---|---|---|---|
| `verify_library` | `ingestion/span_verify.py` | 0 | 2 |
| `split_into_clauses` | `ingestion/smoke_ingest.py` | 0 | 1 |
| `build_fewshot_block` | `llm/fewshot.py` | 0 | 1 |
| `run_announce_scan` | `update/announce.py` | 0 | 1 |
| `default_fetcher` | `update/channel_test.py` | 0 | 1 |
| `clean_standard_no` | `knowledge/ccs_fetcher.py` | 0 | 2 |
| `empty_lookup` | `knowledge/ccs_fetcher.py` | 0 | 3 |
| `classify_backfill_exception` | `knowledge/ccs_backfill.py` | 0 | 2 |
| `load_undo_journal` | `knowledge/ccs_undo.py` | 0 | 1 |
| `system_layer_names` | `settings/api_credentials.py` | 0 | 2 |
| `word_com_available` | `ingestion/docx_adapter.py` | 0 | 1 |
| `ocr_image_text` | `vision/local_vision.py` | 0 | 1 |
| `ocr_image_locally` | `vision/local_vision.py` | 0 | 1 |
| `ccs_range_of` | `knowledge/doc_catalog.py` | 0 | 2 |
| `tree_lines` | `knowledge/folder_filing_plan.py` | 0 | 3 |
| `pipe_http` | `update/channels/proxy_rotate.py` | 0 | 3 |
| `schedule_tiers` | `update/scheduler.py` | 0 | 4 |
| `pending_rows` | `update/web_ingest.py` | 0 | 3 |

**18 条**。这些不一定是"该删"（有的是公开 API 留着给未来用），但它们**都没有被 `__all__` 之外的任何地方用到**，属于"公开但无人调"。

### 5.4 `UpdateScheduler.start()` —— 项目自己记录的已知死代码

`update/scheduler.py:70` 的 `UpdateScheduler` 有 `start()`/`stop()`/`tick()`。
`api/server.py:3298` 注释：「⚠ 不走 `src/core/update/scheduler.py` —— 那个调度器的 `start()` 全仓无人调用（死代码），接进去刷新永不执行。」
`knowledge/law_source/law_refresh.py:7` 注释同样记录：「`start()` **全仓无人调用**（`git grep UpdateScheduler -- src` 只命中类定义与…）」
`update/scheduler_runner.py:8` 注释同样记录：「**没人启动它**：`UpdateScheduler.start()` 全仓无人调用」。

**实测**：`UpdateScheduler` 类本身**没死** —— `scheduler_runner.py:95` 把它当工厂默认值（`_sched_factory: Any = UpdateScheduler`），`scheduler_runner.py:84` 用它构造实例并调 `tick()`。死的是**它的 `start()` 方法**。

### 5.5 可疑但未坐实

| 模块 | 状态 |
|---|---|
| `update/channels/dbba.py`（27 行）、`mee.py`、`mem_gov.py`、`mohurd.py`、`std_samr_hb.py` | 严格 import 扫描显示 0 处 `from ... import <module>`，但它们经 `channels/__init__.py:47-54` 的 `_safe_import("mem_gov", "MemGovAdapter")` **动态导入**，是活的。**已排除，不是死代码。** |
| `exports/office_roundtrip.py:EditSession` | 类本身外部零引用，但 `create_edit_session` 返回它，属正常。**不是死代码。** |
| `middle_geo.py:MiddleGeo` | 类外部零直接引用，但 `load()` 返回它。**不是死代码。** |

### 5.6 `__pycache__`

`src/core/__pycache__` 存在（`Get-ChildItem src/core -Directory` 列出，0 个 .py）。这是运行残留，不在本次范围。

---

## 六、边界不清清单

### 6.1 `api/server.py` —— 194 KB 里 707 行是业务逻辑

`create_app` 闭包内 2,954 行，其中 **2525–3231 共 707 行**是纯业务函数：

- `_content_html`（2622–3141，**520 行**）—— 把条款正文渲染成 HTML：图题注入、公式注入、表格截图、`middle_geo` 坐标换算、CSS 内联。这是**展示层逻辑**，和 HTTP 无关，却写在路由文件里。
- `_full_evidence` / `_ev_dict` / `_expand_title_clauses` / `_fetch_clause` —— **证据组装**，属于 `llm/` 或 `retrieval/` 的职责
- `_answer_confidence` —— **置信度分级**，与 `llm/ks_answer.py:_answer_confidence` **同职**
- `_html_to_text` —— 只是转发到 `quality`，是纯壳

另外 539–840 的四个端点（`/documents/{id}/file` `/figure` `/formula` `/table-image`）**各 100–250 行**，全是 PDF 渲染 + 坐标换算 + 图题识别 —— 这些逻辑在 `figure_locator.py` / `formula_locator.py` / `middle_geo.py` 里已经有对应实现，`server.py` 里又写了一遍组装。

### 6.2 `config.py` —— 341 行里业务判断不少

名字叫"配置"，但实际包含：

| 内容 | 行 | 是配置吗 |
|---|---|---|
| `_repo_root` `_default_data_dir` `_default_models_dir` | 26–70 | 是 |
| `_read_env_or_registry` `_read_first` `_read_secret` | 77–130 | 是 |
| `_read_api_key` `_read_llm_base_url` `_read_llm_model` `_read_llm_max_tokens` `_read_llm_reasoning_effort` `_read_llm_empty_retries` `_read_mineru_key` `_read_mineru_base_url` `_read_mineru_model_version` `_read_jev_key` | 133–260 | 是 |
| `MINERU_CLOUD_MODEL_VERSIONS` 校验 + `_read_mineru_model_version` 的**合法性判断** | 241–258 | **业务规则**（哪个模型版本合法） |
| `jev_guard_review_threshold` / `jev_guard_action_threshold` / `jev_guard_severity_block` / `jev_guard_enabled` | 289–294 | **业务阈值**，注释自认「不是协议常量，会随中文域实测调整」 |
| `Settings.ensure_dirs()` —— **有副作用（mkdir）** | 321–323 | 副作用藏在"配置"里 |
| `get_settings()` —— 单例 + 首次调用建目录 | 329–334 | 同上 |

`get_settings()` 全仓 26 个文件调用，其中 13 处在 `api/server.py`。**"取配置"和"建目录"绑在一起**，任何一次 `get_settings()` 都可能写磁盘。

### 6.3 跨子系统反向依赖：`knowledge` ← `exports`

`knowledge/folder_store.py:936-937`：
```
from src.core.exports.effect_report import COLOR_ORDER as _COLOR_ORDER
from src.core.exports.effect_report import STATUS_COLOR as _STATUS_COLOR
```
而 `exports/effect_report.py:33-34` 又：
```
from src.core.knowledge.doc_catalog import classify_document
from src.core.knowledge.legal_status import resolve_status
```
**这是 `knowledge` ↔ `exports` 双向依赖**。`folder_store.py` 为了拿两个颜色常量，反向依赖了"导出报告"模块。
`folder_store.py` 的 docstring 自称「只做「存」的那一层」，但它 import 了 `exports`（lazy）和 `storage/doc_delete`（lazy）。

### 6.4 三处环形依赖（跨子系统，靠 lazy import 续命）

| 环 | 证据 |
|---|---|
| `storage` ↔ `knowledge` | `storage/clause_repo.py:672/772` lazy import `knowledge.classifier`；`knowledge/alias_extract.py:10` **顶层** import `storage.sqlite_db` |
| `storage` ↔ `retrieval` | `storage/clause_repo.py:13` **顶层** `from src.core.retrieval import embedder`；`retrieval/hybrid_engine.py:12-13` **顶层** `from src.core.storage.clause_repo import fetch_full_clause` |
| `knowledge` ↔ `exports` | 见 §6.3 |

**`storage` ↔ `retrieval` 是双向顶层 import** —— 这个环能跑通说明至少有一侧是靠 `from __future__ import annotations` 或 import 顺序侥幸。这是脆弱点。

### 6.5 `ingestion` 里塞了 HTTP 客户端和子进程管理

`ingestion/mineru_cloud.py`（435 行）是 **MinerU 云 API 的 HTTP 客户端**（上传、轮询、下载 zip、解压、校验），和 `knowledge/law_source/http.py`（223 行，另一个 HTTP 层）、`update/channels/base.py`（450 行，第三个 HTTP 传输层）**三足鼎立**。
`ingestion/deep_server.py`（490 行）是**常驻进程管理器**（起进程、心跳、抢任务、攒批），不是"入库"。

### 6.6 `update/` 里塞了正文入库

`update/web_ingest.py`（506 行）职责是"把部委公告正文写进知识库" —— 这本质是 **ingestion**。它确实调了 `ingestion/law_text.py:ingest_law_text`，但自己也写了 `extract_body_text`（HTML 正文抽取）、`page_title`、`classify_status`、`classify_hierarchy`、`classify_scope`、`classify_change_signal` —— **6 个分类/抽取函数**，与 `knowledge/classifier.py`、`knowledge/doc_catalog.py`、`materials/collect.py` 的职责重叠。

### 6.7 `update/` 有 13 个渠道适配器，5 个是 27–149 行的薄壳

`dbba.py` 27 行、`mohurd.py` 106 行、`mem_gov.py` 130 行、`std_samr_hb.py` 115 行、`hbba.py` 149 行 —— 都继承 `_SacinfoQueryAdapter` 或 `ChannelAdapter`，主要工作是填 URL 和解析规则。这是合理的插件式设计，**但它们的注册方式是 `_safe_import`（try/except 静默降级）**：

```python
"mem_gov": _safe_import("mem_gov", "MemGovAdapter"),
```
`channels/__init__.py:29` 的 docstring 写「容错导入子代理正在实现的渠道（未完成/语法错不阻塞整体启动，记 warn）」。
**问题**：一个渠道如果因为语法错永远导入失败，系统只会打一条 warning，**巡检会静默地少查一个渠道**。这与 `AGENTS.md` 的「Misconfiguration fails loud」相悖。

### 6.8 `text_utils.py` —— 2,162 行装了三件不相关的事

名字叫"文本工具"，实际是：
1. OCR 后处理（约 1,100 行）
2. LaTeX/公式/Katex 转换（约 500 行）—— 这是**展示层**
3. 标准号归一 + 分词 + FTS 表达式（约 350 行）—— 这是**领域标识 + 检索**

第 3 块和 `update/channels/base.py`、`knowledge/ccs_fetcher.py` 是同一件事（见 §3.4）。

### 6.9 `quality/` 依赖 `ingestion/` 和 `verification/`，但 `ingestion/` 又依赖 `quality/`

`quality/recognition.py:63/227` 用 `verification/patch_guard.py:check_patch`；`quality/__init__.py` 依赖 `ingestion`；而 `ingestion/dry_run.py:382` 用 `quality.clause_health`、`ingestion/pipeline.py:1979` 用 `quality.recognition`。
**`quality` ↔ `ingestion` 也是一个环**（`quality` 自称"纯函数 + 只读"，却依赖了会写库的 `ingestion`）。

### 6.10 `storage/user_data.py` —— 名字最泛，内容最杂

409 行装了 **5 类业务对象**：收藏（条款级）、收藏（标准级）、收藏夹、批注、项目清单、义务清单。加上 `folder_scope`。
这是"用户数据"这个大口袋，实际是 5 个不同的仓储混在一个文件里。

---

## 七、我没搞清楚的

1. ~~**`_xlsx_header_style` 三份函数体是否逐字相同**~~ —— **已解决**：`docs/uniformity/ast-dupes-gated.json` 分组 `991db9f79b781cc2` 证实三处逐字同构（各 6 条语句）。

2. **`text_hash` 两处算法是否一致** —— `ingestion/material_ingest.py` 与 `materials/collect.py` 各有一份，没读函数体比对。

3. **`config._default_data_dir` 与 `settings/secret_store._resolve_data_dir` 是否等价** —— 两份各自算数据目录，前者 13 处引用、后者 3 处（都在 `secret_store.py`）。没逐行比对。这直接决定 `secrets.json` 会不会落到和数据库不同的盘上。

4. **`storage` ↔ `retrieval` 双向顶层 import 为什么没炸** —— `clause_repo.py:13` 和 `hybrid_engine.py:12` 都是顶层互 import。没验证实际 import 顺序，也没跑 Python 确认。这需要真跑一次才能定性。

5. **`api/server.py` 里 4 个图/公式/表格端点的实际逻辑与 `figure_locator.py`/`formula_locator.py`/`middle_geo.py` 有多少重复** —— 端点在 539–840 行（约 300 行），locator 模块合计 782 行。只看了路由装饰器和函数签名，**没逐行读这 300 行**。

6. **`_content_html`（520 行）的内部结构** —— 只知道它的边界（2622–3141）和它做什么（条款正文 → HTML），没读内容。

7. **176 条路由里有没有已经废弃但还留着的** —— 没做「前端是否还调这条路由」的交叉核对（`plugin/` 是 TS，没查）。

8. **`ingestion/pipeline.py` 2,443 行的内部分段** —— 只定位了 `run_full_ingest`（2021 行起）和 `split_items_into_clauses`，中间 2,000 行的结构没摸清。

9. **`update/` 36 个文件里 13 个渠道适配器的实际存活情况** —— 它们经 `_safe_import` 动态导入，**只有真跑一次巡检才知道哪个渠道导入失败**。静态扫描无法判定。

10. **`quality/disagreement.py` 是有意保留还是忘了删** —— 全仓只有测试用。没查开发史判断意图。

11. **AST 同构检测的下限之外还有多少重复** —— 团队的尺子 `min_stmts=4`（函数体至少 4 条语句才比），且只比"语句结构"，不比"同名但结构不同"的重复（如 §3.4 的 11 个标准号归一函数，结构各异，AST 抓不到）。**本清单 §3.2–§3.13 大多属于 AST 抓不到的那类**，靠人读出来的，不是机器穷举的。

12. **`pyscn` 克隆检测的 132 组没有逐组核对** —— `docs/uniformity/measure-01.json` 里有 `pyscn_clone_groups: 132`，团队口径把它列为 `info_only`（不判红）。这 132 组里有多少落在 `src/core/`、和我 §三 的 15 条重叠多少，**没核**。
