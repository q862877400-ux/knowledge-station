# src/core 三个大文件事实地图

> 调查范围：`src/core/ingestion/pipeline.py`、`src/core/text_utils.py`、`src/core/update/inspector.py`。
> 方法：三个文件**逐行读完**（不是只看函数名）；跨模块结论一律给「函数名 + 可搜索文字 + grep 结果」。
> 只读调查：未改任何源码，未跑门禁 / pytest / npm。
>
> **结论先说**：三个文件都不是"写坏了"，而是**各自把 3～4 个子系统的职责收进了自己**。
> 结果不是 bug，是**同一件事出现两份实现时没有任何机器判据会响**（例：`pipeline.py` 的页眉判据
> 与 `text_utils.py` 的页眉判据是两套，代码注释自己写着"第二份实现"）。
> 三个文件里 **6 个超过 100 行的函数**、**2 个全仓零调用的函数**、**1 段不可达代码**、
> **3 个未使用的 import**、**7 处指向已漂移行号的注释**。

## 行数口径更正（先更正任务书里的数字）

任务书给的 2,254 / 1,844 / 845 是**非空行**，不是文件行数。实测（`[IO.File]::ReadAllText` 按 `\n` 切分）：

| 文件 | 物理行数 | 非空行（任务书数字） | 字节 |
|---|---|---|---|
| `src/core/ingestion/pipeline.py` | **2,443** | 2,254 | 108,832 |
| `src/core/text_utils.py` | **2,162** | 1,844 | 82,492 |
| `src/core/update/inspector.py` | **937** | 845 | 43,973 |

下文一切行号均指**物理行号**。

---

## 一、pipeline.py

### 1.1 它是什么

一份 PDF 从「路径」变成「库里可检索的条款」的**唯一编排者**。模块 docstring 第一句：
`T05 完整入库管线：MinerU 深度解析 → middle.json 结构化 → E1-E7 切分 → 三型分型 → 证据图抽取 → 单事务原子入库（R1）`。

### 1.2 分段结构（按函数名 / 分节注释标记）

分段**不是**统一的注释分节风格，而是三种混用：① 顶部一大段判据常量；② 各组函数按处理阶段排列；
③ 仅两处 `# ---` 分节线（`目录条目判据…`、空行分隔）。下表按**处理阶段**切，起止用可搜索的函数名/注释锚定：

| # | 段（锚点） | 干什么（一句话） |
|---|---|---|
| 1 | 模块 docstring：`坐标契约（2026-09-16 更正）` | 声明 bbox 底部原点、`source_span` 原样直存、前端 `convertToViewportPoint` 直接消费 |
| 2 | `from __future__` … `logger = logging` | 导入（不含任何 LLM 模块） |
| 3 | `_CLAUSE_GB` … `_RE_INDEX_ENTRY` | **模块级判据常量区**：条款号/章头/附录/目录条目/索引条目/表格数值闸门的全部正则 |
| 4 | `_frag_key`、`_own_key_of`、`_middle_cover_blocks`、`_is_index_entry`、`_is_toc_entry`、`_plausible_clause_head`、`_num_segments`、`_is_continuation_head`、`_is_leader_run`、`_plausible_appendix_head` | **条款头/目录/索引/附录的五道防误切闸门**（E8 族） |
| 5 | `_std_type`、`_hier_from_no` | 从标准号推断 `standard_type`（强制/推荐/指导）与效力层级 |
| 6 | `@dataclass MidItem` | middle.json 归一化条目（含行级 bbox、插图路径、OCR 置信度聚合） |
| 7 | `_spans_rows`、`_spans_rows_scored`、`_spans_text` | 从 middle.json 的 block/line/span 抽「行 + 行框 + span 置信度」 |
| 8 | `_is_figure_legend`、`_legend_follows_image` | 图例块判定 + 图例是否紧邻图（几何判据） |
| 9 | `load_middle_items` | middle.json → 阅读顺序条目 + 每页尺寸（走 `middle_schema.load_middle_json`） |
| 10 | 注释 `# 废弃说明（v5 实测修复 2026-08-23）` | 记录 `_flip_bbox` 已删除、禁止再做 H−y 翻转 |
| 11 | `@dataclass SplitClause`、`_rows_of`、`_strip_foreign_frag` | 切分产物模型 + 行级序列化 + 家具片段剥离 |
| 12 | `split_items_into_clauses` | **E1–E7 切分主逻辑**（全文最大的判定网） |
| 13 | `strip_figure_legend_segment`、`_strip_headerless_legend` | 从条款正文里切掉图例段（有头 / 无头两种） |
| 14 | `build_clause_models` | 切分结果 → `ClauseRevisionModel` + 证据图 raw 边（含页界、行级 span、fig_html、清洗链） |
| 15 | `resolve_edges` | raw 边 → 可落库元组；未解析项**留痕**而非静默丢弃 |
| 16 | `analyze_preview` | 老 dry-run 预览（冻结契约） |
| 17 | `load_middle_items_from_blocks` | PyMuPDF 文本层 blocks → 条目（拆行 + 页眉对剔除 + 章题拼回） |
| 18 | `_cell_html`、`_grid_html`、`_extract_vector_table_items`、`_merge_table_items` | **矢量框线表格重建**（文本层快路径） |
| 19 | `_cached_parse_result` | 复用既有解析产物（零 OCR 重导） |
| 20 | `_filing_confidence`、`_write_filing_state` | 入库时算识别率 + 写处理状态（入库侧唯一出口） |
| 21 | `run_full_ingest` | **入库主流程** |
| 22 | `main` | CLI 入口（`os._exit` 硬退出） |

### 1.3 函数/类数量

| 口径 | 数量 |
|---|---|
| 顶层 def/class 合计 | **38**（36 个函数 + 2 个 `@dataclass`） |
| 公开（不以下划线开头） | **11** — `MidItem`、`load_middle_items`、`SplitClause`、`split_items_into_clauses`、`strip_figure_legend_segment`、`build_clause_models`、`resolve_edges`、`analyze_preview`、`load_middle_items_from_blocks`、`run_full_ingest`、`main` |
| 内部私有 | **27** |
| 函数内嵌套函数 | **5** — `_cover_date`、`_idx`、`_n`、`_noise_span`、`_render` |

### 1.4 入库完整流程：从「一个 PDF 路径」到「库里有条款」

`run_full_ingest(pdf_path, standard_no, standard_name, …)` 内的实际步骤（按发生顺序）：

1. **前置**：`if not pdf_path.exists(): return {"status": "error"}`；`init_schema()`。（L2030–2032）
2. **查重**：`hashlib.sha256(pdf_path.read_bytes())` → 查 `doc_meta.file_hash`，命中且非 reingest → 返回
   `{"status": "duplicate"}`；再查 `standard_no`（用 `store_standard_no` 折形状），同号不同 hash 且非
   reingest → 返回 `{"status": "standard_exists"}`。（L2033–2048）
3. **身份**：`doc_id = f"doc_{ULID()}"`；`legal_hierarchy = _hier_from_no(standard_no, …)`。（L2051–2054）
4. **拿解析结果**，三条来源按优先级：
   - `reuse_parse=True` → `_cached_parse_result(parse_out/<既有 doc_id>)`（零 OCR）；
   - `product_dir=` → 直接把该目录当深度产物目录（OCR 循环产物入库用），页尺寸从源 PDF 用 fitz 补；
   - 都没有 → `run_parser_isolated(pdf_path, parse_out/<新 doc_id>, force_deep=force_deep)`。（L2060–2109）
5. **两路消费**（由 `_has_text_layer_ok = bool(result["blocks"])` 决定）：
   - 深度路（blocks 空且有 `deep_output`）：`find_middle_files` → `load_middle_items(middle_files[0])`；
   - 文本层路（blocks 非空）：`_extract_vector_table_items` 重建矢量表格 → 剔除表内文本块 →
     `load_middle_items_from_blocks` → `_merge_table_items` 落位。（L2110–2155）
   - 两路都不成立 → `{"status": "error", "message": "解析不可用…"}`。
6. **切分**：`split_items_into_clauses(items, standard_no=standard_no)` → `list[SplitClause]`。（L2159）
7. **建条 + 建边（raw）**：`build_clause_models(doc_id, standard_no, doc_type, clauses, page_sizes)`。
   内含 `clean_clause_text` 清洗链、`classify_clause` 分型、页界 `page_breaks`、行级 `SourceSpanModel`、
   插图 `fig_html`。（L2160）
8. **坐标校准**：`span_calibration.calibrate_new(...)` 写库前归一为底部原点（失败只告警）。（L2165–2174）
9. **边解析**：`resolve_edges(raw_edges, number_to_id, unresolved_refs)` → 可落库边 + 未解析清单。（L2176–2179）
10. **reingest 删旧文档**（**事务外**）：`folder_store.snapshot_filing_assets(旧 doc_id)` →
    `clause_repo.delete_document(旧 doc_id)`。（L2195–2200）
11. **单事务写入**（`with write_transaction() as txn`，L2249–2291）：
    `insert_document` → `insert_page_geometries` → `insert_clauses_in_txn(normal)` →
    `insert_clauses_in_txn(preface, "前置说明")` → `insert_clauses_in_txn(appendix, "附录")` →
    `insert_edges_in_txn` → `event_log('ingest_unresolved_refs')` → `doc_meta.catalog_hidden` 显式写 0/1。
    `insert_clauses_in_txn` 内部一并写 `clause_revision` + `source_span` + `clause_fts` + `clause_vec`
    （后者要求 `embedder.is_available()`）。
12. **事务提交之后**（均**不阻塞**入库）：CCS 台账（`ccs_store.apply_ccs_tag`/`record_ccs_lookup`）、
    处理状态 `_write_filing_state`、重导归属搬运 `restore_filing_assets`、`operation_log`、
    OCR 数字回填 `pypdf_backfill.backfill_document`、span 体检 `span_verify.verify_doc`。（L2297–2393）

返回值里带：`doc_id`、`total_clauses`、`preface_clauses`、`evidence_edges`、`unresolved_refs`、
`pages_parsed`、`span_warning`、`filing_stage`、`filing_confidence`、`filing_assets_carried`、
`catalog_hidden`。

### 1.5 它调了哪些其他子系统

| 子系统 | 具体被调的东西 |
|---|---|
| `ingestion` 内部 | `parser_worker.run_parser_isolated`、`middle_schema.load_middle_json`、`middle_locator.find_middle_files`、`span_calibration.calibrate_new`、`span_verify.verify_doc`、`pypdf_backfill.backfill_document`、`mineru_adapter.text_layer_pua_mangled` |
| `storage` | `clause_repo`（`insert_document` / `insert_page_geometries` / `insert_clauses_in_txn` / `insert_edges_in_txn` / `make_clause_key` / `delete_document`）、`sqlite_db`（`get_db_connection` / `init_schema` / `write_transaction`） |
| `knowledge` | `classifier`（`classify_clause` / `normalize_clause_number` / `strip_revision_marks` / `build_hierarchy_path`）、`ccs_fetcher.resolve_ccs` / `ccs_to_tag`、`ccs_store`、`folder_store`（`snapshot_filing_assets` / `restore_filing_assets` / `set_filing_state` / `FAILURE_KIND_ZERO_CLAUSES`） |
| `quality` | `recognition.clause_ocr_confidence`、`recognition.measure_skew`（在 `_filing_confidence` 里） |
| `text_utils` | `store_standard_no`、`standard_key`、`latex_to_text`、`glue_ocr_spaced_units`、`clean_eq_tags`、`normalize_pua_latin`、`normalize_pua_separators`、`clean_clause_text`、`pua_bond_dash_html`、`glue_spaced_formulas` |
| `domain` | `ClauseRevisionModel`、`SourceSpanModel` |
| `llm` | **不调用**。全文无 `llm` import（grep `llm` 只命中 `fullmatch`）。向量化不在这里，而在 `clause_repo.insert_clauses_in_txn` → `retrieval.embedder.embed_batch` |

### 1.6 失败分支，以及失败时库处于什么状态

`write_transaction` 的语义（`src/core/storage/sqlite_db.py`）：`BEGIN IMMEDIATE` → yield → `commit`；
`except BaseException: rollback; raise`。⇒ **事务内任一步失败，全回滚，不会留半截条款**。

| 失败点 | 返回/抛出 | 库里会怎样 |
|---|---|---|
| PDF 不存在 | `status=error` | 什么都没动 |
| hash 命中且非 reingest | `status=duplicate` | 什么都没动 |
| 同 `standard_no` 不同 hash 且非 reingest | `status=standard_exists` | 什么都没动 |
| `product_dir` 不是目录 | `status=error` | 什么都没动 |
| 有 `deep_output` 但 `find_middle_files` 空 | `status=error`「未找到 middle.json」 | 什么都没动 |
| blocks 空且无 deep | `status=error`「解析不可用」 | 什么都没动 |
| `run_parser_isolated` 抛 `ParserError`/`ParserTimeoutError` | **异常直接冒出本函数**（L2107–2109 无 try） | 什么都没动；上层 `bulk.parse_loop` 的 `except Exception` 记 `failed` |
| 入库事务内任一步抛 | 回滚 | 条款/几何/边/FTS/向量**一起回滚**；但 **reingest 的旧文档已在上一步被删**（见下） |
| 一条正文条款都没提出（`n_normal == 0`） | **仍返回 `status=ok`**，但 `catalog_hidden=1`、`filing_stage=failed` | 文档行在库、目录里隐藏、状态行标 failed |
| 事务后的 CCS 台账 / filing_state / 归属搬运 / 回填 / span 体检 失败 | 只记日志，`status` 仍 `ok` | 文档已提交，附属记录可能缺（`filing_state_written=False` 会如实带回） |
| `operation_log` 写入失败（L2352 第二个事务，**没有 try**） | 异常冒出 | **文档已经在库里**，但调用方收到异常 ⇒ 可能触发重复入库 |

**唯一会留下"半截数据"的路径是 reingest**：旧文档的删除（`clause_repo.delete_document`，它自己是
一个独立事务，L437–460）发生在入库事务**之前**。若入库事务失败或进程被杀，结果是
「旧文档已删、新文档没进来」。同一段还带一个**只在内存里**的 `_carried_assets` 快照
（`snapshot_filing_assets` 的返回值），进程一死，用户的目录归属也一起没了。
代码注释 L2325–2333 承认这个三段式，但没有把删除挪进同一个事务。

### 1.7 幂等性

- **同一份 PDF 入库两次（默认参数）**：第二次在 L2036 `SELECT doc_id FROM doc_meta WHERE file_hash=?`
  命中 → `{"status": "duplicate"}`，**不解析、不写库**。是幂等的。
- **同一份 PDF 入库两次（`reingest=True`）**：**不是幂等**。新开一个 `doc_id`（`doc_{ULID()}`）、
  新开一套 `clause_key`（`make_clause_key = sha256(doc_id + clause_no)[:24]`），旧文档被删。
  ⇒ 条款主键全变，收藏/批注靠 `clause_key` 重新关联（注释 L2185–2193 明说），
  目录归属靠 `snapshot_filing_assets` → `restore_filing_assets` 搬。
- **`reuse_parse=True` 重跑**：跳过 OCR，但**仍然新开 `doc_id`**，同上。
- 反向的一条：L772–779 只在 `status == "pending"` 时校正 `total`，重复 `run_batch` 不会重跑队列
  （那是 inspector 的幂等，不属于本节）。

### 1.8 与兄弟模块的重复实现

| 兄弟模块 | 关系 | 判断 |
|---|---|---|
| `docx_ingest.py`（95 行） | `run_docx_ingest` 把 docx 转 PDF 后**调 `run_full_ingest`**（L38）；另有降级直解入库分支 | **不是重复实现**，是薄封装。我只读了结构（2 个函数），降级分支体未逐行读 |
| `reingest.py`（173 行） | `start_reingest` 编排 + **调 `run_full_ingest(..., reingest=True)`**，再把 `out["total_clauses"]` 转出去（L103） | **不是重复实现**。它只是批量编排 + 状态查询 |
| `law_text.py`（397 行） | `ingest_law_text` 是**第二套完整入库路径**：自己 `classify_clause`、自己拼 `ClauseRevisionModel`（L258–275）、自己连边（L277–297）、自己拼 `doc_row`（L299–306）、自己写 `write_transaction`（L347–351）、自己查 CCS（L319–331） | **是重复实现**。它**不经过** `build_clause_models` / `resolve_edges` / 页界 / 行级 span / `catalog_hidden` / `_write_filing_state`。代码注释自己承认分叉：`pipeline.py 的 resolve_edges 一直有这道闸，这里漏了 ⇒ 两条入库路径行为不一致`（L291–293） |
| `dry_run.py`（521 行） | 反过来**复用** pipeline 的纯函数（L297–301 import 5 个），并明说「复用生产入库的建条实现」 | 方向是对的（pipeline 当库用）。但 `pipeline.analyze_preview` 与 `dry_run.analyze_preview_report` 是**同一件事的两代实现**，老的只剩测试在调（见 §四） |
| `bulk.py` / `smoke_ingest.py` / `material_ingest.py` | 均为编排/批量层 | 未见第二套建条实现（只按 grep 看过，未通读） |

### 1.9 最长函数

| 函数 | 行数 | 干什么 |
|---|---|---|
| `run_full_ingest` | **397**（L2021–L2417） | 整个入库编排：查重 → 解析 → 两路消费 → 切分 → 建条 → 校准 → 边 → 删旧 → 单事务写 → 6 个后置步骤 → 组装 18 个返回键 |
| `split_items_into_clauses` | **367**（L759–L1125） | E1–E7 切分：目录态/索引态/附录态三态机 + 条款头五道闸门 + 表格绑定 + 插图绑定 + 行级拆条 |
| `build_clause_models` | **201**（L1275–L1475） | 切分 → 模型：清洗链、页界、行级 span、插图 HTML、分型、OCR 置信度、证据边 |

超过 200 行的两个（`run_full_ingest`、`split_items_into_clauses`）都是「一个函数装了一个阶段的全部决策」。

### 1.10 读到的另外三个可疑点（静态读出，未运行验证）

1. **`total_clauses` 的算术可疑**（L2398）：`"total_clauses": n_normal - n_pre`。
   而 L2261–2263 是 `n_normal = insert_clauses_in_txn(txn, normal)`、
   `n_pre = insert_clauses_in_txn(txn, preface, "前置说明")`、
   `insert_clauses_in_txn(txn, appendix, "附录")`（返回值不计），
   且 `normal` 与 `preface` 由 L2203–2206 的 `startswith("前置")` 断言为**互斥集合**。
   `insert_clauses_in_txn` 的返回是 `len(clauses)`（`clause_repo` L415）。
   ⇒ 实际入库条数是 `n_normal + n_pre + n_appendix`，而报出去的 `total_clauses` 是「正文数 − 前置数」。
   这个值经 `reingest.py:103` 透传、`scripts/std_bulk_import.py:307` 与
   `plugin/client/KsIngestPanel.tsx:475` 显示。**我只做了静态推断，没有跑一次真入库对账**。
2. **`middle_files` 是分支局部变量，却在分支外被用**（L2121 赋值，L2246 使用
   `if deep_output: cover_blocks += _middle_cover_blocks(middle_files[0])`）。
   今天不会炸：`deep_output` 只在 `mineru_adapter.parse_pdf_with_mineru` 的「无文本层」分支被赋值
   （`mineru_adapter.py` L555–572 `if not blocks:`），因此 `deep_output` 为真 ⇒ `_has_text_layer_ok` 为假
   ⇒ L2116 那个分支必然执行过。**但这条不变量没有任何断言保护**，一旦上游改成「有文本层也给
   deep_output」，这里就是 `NameError`。
3. **`reuse_parse` 的深度分支不给页几何**：`_cached_parse_result` 深度分支返回 `"geometries": {}`
   （L1962），而 L2088–2091 的注释明确写着「空 dict 会让 `doc_page_geometry` 无行、
   `pages_parsed` 记 0，进而按页定位证据（原文跳页/高亮）对这批文档不可用」，
   并为此在 `product_dir` 路径补了 fitz 取页尺寸（L2096–2106）。**同一条警告没有覆盖
   `reuse_parse` 路径**。

---

## 二、text_utils.py

### 2.1 它是什么

模块 docstring 自述：`OCR 文本清洗公共模块（2026-08-23 整合）`，用途三条：入库管线清洗、显示层兜底、WPS 导出前。

### 2.2 分段结构

全文用 16 处 `# ----` / `# ====` 分节注释切成 16 段：

| 段（分节锚点） | 干什么 |
|---|---|
| `公式编号引导点线`（`_RE_FORMULA_DOTS` / `_RE_FORMULA_LEADER`） | 剥公式编号前的点线并补全括号 |
| `PUA 错位字体归一化`（`_PUA_LATIN_MAP`） | 形近 CJK→拉丁、`0x21-0x2A`→数字、NFKC |
| PUA 分隔符/装饰符（`_PUA_SEP_CHARS` / `_PUA_DECOR_CHARS`） | 私用区分隔符按上下文还原、装饰符→空格 |
| 行级噪音 + 根号重排 + 数学符号 | 删整行水印、`√` 套分式按数学读序重排、LaTeX 命令→Unicode |
| OCR / 文本层空格粘合族（`_RE_SPLIT_VALUE` …） | 数值劈开、2 字母单位白名单、逐字符空格粘合 |
| `式中` 说明行的 bar 织入（`_RE_MEAN_ENTRY`） | 给"平均值"量符号插组合 macron |
| 折行拼接（**已退役**） | `normalize_wraps` |
| LaTeX → 文本（`_find_brace_group` … `latex_to_text`） | `\frac`/`\tag`/`array` 语义还原 + 上下标 + 逐字符空格归并 |
| HTML 小工具 | `<eq>` 转换、实体解码、剥标签、正文里剔除重复表格文字 |
| `KaTeX 符号渲染` | 说明行的 `^Ci` / `C̄i` → `<span class="katex-sym" data-tex=…>` |
| `国标排版还原三件套` | PUA 键横线→—、单位负指数→`<sup>-n</sup>`/`⁻ⁿ`、段首编号补空格 |
| KaTeX 输入紧凑化 + 面积下标 | 去 token 边界空格；`A°`→`Aₑ` |
| 标准号 / 名称的归一与**存储形** | 4 个键 + 2 个存储形 + 2 个后缀剥离 + 名称清理 |
| FTS 分词与查询构造 | `segment_for_fts`（jieba）、`_porter_stem`（借 SQLite）、`fts_match_expr` |
| HTML → 纯文本 / 二进制嗅探 | 页面级转换（含 script/style 语义）+ 采集侧二进制判据 |
| 水印剥离 + 入库清洗链所有者 | `strip_watermark_lines`（三族水印）+ `clean_clause_text`（次序即契约） |

### 2.3 完整函数清单（61 个，按段分组）

顶层 **61 个函数，0 个类**；公开 **40**、私有 **21**；另有 **16 个函数内嵌套函数**。

**A. 公式点线（1）**
| 函数 | 一句话 |
|---|---|
| `strip_formula_leader` | 剥公式编号前导点线并归一为 `(N)`，补全缺右括号 |

**B. PUA 归一（2）**
| 函数 | 一句话 |
|---|---|
| `normalize_pua_latin` | 形近 CJK→拉丁、`0x21-0x2A`→`0-9`、`＾X`→组合帽、NFKC |
| `normalize_pua_separators` | 2 个分隔符类按左右上下文还原，6 个装饰类一律→空格 |

**C. 行级噪音 / 根号 / 符号（3）**
| 函数 | 一句话 |
|---|---|
| `strip_block_noise` | 整行即水印（URL±页码±点线）→删行，剥公式点线 |
| `reflow_sqrt_formulas` | `√` 悬尾的三行公式重排为 `左式√(分子/分母)` |
| `normalize_math_symbols` | 纯文本里的 LaTeX 泄漏（`\leqslant`/`≤slant`/`m^{2}`）→ Unicode |

**D. 空格粘合族（5）**
| 函数 | 一句话 |
|---|---|
| `_glue_formula_fragments` | 行级无歧义劈开：`1 . 0`→`1.0`、`(1 8`→`(18`、`P 1 E`→`P1E` |
| `_glue_split_values` | 数值劈开合并（单位锚定）：`6 10 g`→`610 g` |
| `_glue_two_letter_units` | 2 字母单位去空格（白名单：`m m`→`mm`） |
| `glue_ocr_spaced_units` | OCR 通道逐字符拉开的单位/数字保守粘合（不跨型） |
| `glue_spaced_formulas` | 文本层逐字符定位导致 `C a O`→`CaO`（按"格"处理，制表符是列边界） |

**E–F. 说明行织入 + 折行拼接（2）**
| 函数 | 一句话 |
|---|---|
| `weave_meaning_marks` | 「式中」说明段里描述含"平均"的量符号插入 macron |
| `normalize_wraps` | OCR 折行拼接（**docstring 已写退役**，见 §四） |

**G. LaTeX → 文本（7）**
| 函数 | 一句话 |
|---|---|
| `_find_brace_group` | 从 `{` 读平衡花括号组，返回内容 + 结束位置 |
| `_wrap_frac_operand` | `\frac` 分子/分母含运算符时加括号保语义 |
| `_convert_frac_tag` | `\frac{A}{B}`→`A/B`（递归 20 层）、`\tag{…}`→尾部编号 |
| `_strip_latex_arrays` | `\begin{array}{rl}` 的列格式/`&`/`\\` 还原为换行与空格 |
| `normalize_label_comma` | 标签逗号代点：`(D,8)`→`(D.8)`、`表B,4`→`表B.4` |
| `latex_to_text` | MinerU `<eq>` LaTeX → 可读 Unicode 文本（总入口） |
| `_collapse_latex_spacing` | LaTeX 转文本后的逐字符空格归并（`6 1 0`→`610`、`g / m`→`g/m`） |

**H. HTML 小工具（4）**
| 函数 | 一句话 |
|---|---|
| `clean_eq_tags` | 把 `<eq>LaTeX</eq>` 换成可读文本（其余标签保留） |
| `html_unescape` | 实体解码 |
| `strip_tags` | 剥标签 + 解实体 + strip |
| `strip_embedded_table_text` | 正文里与表格 cell 重复的行/句剔除（图题白名单） |

**I. KaTeX 符号（3）**
| 函数 | 一句话 |
|---|---|
| `_tex_alpha` | 单字符 → TeX 可用 ASCII（伪字区 `犃-犫` 映射） |
| `_katex_span` | 生成 `<span class="katex-sym" data-tex="…">` |
| `katex_sym_html` | 说明段内 `^C`/`C̄` token → KaTeX span（幂等） |

**J. 国标排版三件套（5）**
| 函数 | 一句话 |
|---|---|
| `pua_bond_dash_html` | PUA 键横线→`—`（出口与入库共用，等长替换） |
| `sup_unit_exponents_html` | `cm-1`→`cm<sup>-1</sup>`（出口） |
| `space_clause_numbers_html` | 段首条款号后补空格（出口） |
| `sup_unit_exponents_text` | `cm-1`→`cm⁻¹`（入库，Unicode 上标） |
| `space_clause_numbers_text` | 段首条款号后补空格（入库，`re.M`） |

**K. KaTeX 输入 / 面积下标（2）**
| 函数 | 一句话 |
|---|---|
| `clean_latex_for_katex` | MinerU 逐字符 OCR 的 LaTeX → KaTeX 可渲染的紧凑形 |
| `normalize_area_subscript` | `A°`（实为面积下标 `Aₑ`）在面积判据下归一 |

**L. 标准号 / 名称（10）**
| 函数 | 一句话 |
|---|---|
| `canon_standard_no` | **比较用**归一：全角→半角、折破折号、去空格去斜杠、大写 |
| `store_standard_no` | **存储形**：只折全角 `／`→`/`、`－`→`-`，其余一字不动 |
| `store_standard_name` | **名称存储形**：只折全角斜杠，**一个连字符都不动** |
| `_match_std` | 从页眉匹配重建标准号（**全仓零调用，见 §四**） |
| `standard_key` | 比较键 `号-年`（丢前缀族与 `/T`） |
| `standard_no_key` | 比较键（去空白、去斜杠、折连字符，**保留年份与部分号**） |
| `law_name_key` | 法规名比较键（**保留**括号里的修正年份） |
| `strip_duplicate_suffix` | 循环剥结尾 `(1)`/`（2）` 副本后缀 |
| `strip_ocr_source_suffix` | 循环剥结尾 `(OCR采集)` 来源后缀（只此一种） |
| `clean_standard_name` | 文件名 → 展示用干净名称（全角斜杠、副本后缀、开头标准号前缀） |

**M. FTS（5）**
| 函数 | 一句话 |
|---|---|
| `segment_for_fts` | **唯一**分词实现：jieba `cut_for_search` + 空格连接 |
| `_porter_stem` | 借 SQLite `porter` 分词器取词干（每线程一个 `:memory:` 连接 + 缓存） |
| `_plain_case` | 判「无内部大写」（放行首字母大写，挡 `RoHS`/`camelCase`） |
| `_latin_prefix_token` | 拉丁词 → `"词干"*`；不符合闸口返回 `None` |
| `fts_match_expr` | FTS5 `MATCH` 表达式**唯一**构造器（逐词加引号 + OR + 拉丁前缀扩写） |

**N. HTML→文本 + 二进制嗅探（6）**
| 函数 | 一句话 |
|---|---|
| `html_to_text` | 页面/表格通用 HTML→紧凑纯文本（声明为规范实现，另有 3 份未收口） |
| `_strip_script_style` | 丢 `script`/`style` 及内容（含未闭合、自闭合、注释、raw text 五条语义） |
| `_inside_unclosed_tag` | 判断位置是否落在**未闭合标签**内（属性值里的 `<script>` 不是标签） |
| `_inside_raw_text` | 判断是否落在 raw text / RCDATA 元素内（`xmp`/`plaintext`/`textarea`/`title`） |
| `looks_like_binary` | **文本入口**：ASCII 签名 + 前 4096 字符 NUL |
| `looks_like_binary_bytes` | **字节入口**：同一签名表的字节形态（能兑现 PNG/JPEG/ELF/OLE2） |

**O. 水印剥离（5）**
| 函数 | 一句话 |
|---|---|
| `strip_watermark_lines` | 整行删水印（URL 族 / 工具族 `Aspose` / 页眉「页码+标准号」族），正文行不动 |
| `_strip_wm_tokens` | 迭代剥一行里的全部水印 token（≤4 轮且每轮必须变短） |
| `_match_key` | 页眉匹配 → 比较键（`standard_key` 版） |
| `_std_matches` | 该匹配是否可视为「自家」页眉（`own_key=None`→不设限） |
| `_sub_own_header` | 只删「号+年 == 自家标准号」的行尾页眉 |

**P. 清洗链所有者（1）**
| 函数 | 一句话 |
|---|---|
| `clean_clause_text` | **入库文本清洗链的唯一所有者**：PUA→点线→标签逗号→单位指数→编号空格→（注入的）图例切除→水印 |

### 2.4 它到底是「文本工具集合」还是「塞了业务逻辑」

**判断：前 12 段是真正的文本工具；后 4 段（L/P 两族 + M/N 两段）是业务逻辑，塞错了地方。**

证据（可搜索）：

| 判据 | 结果 |
|---|---|
| 碰文件系统吗 | **不碰**。grep `open(|Path|read_text|write_text|os.` 在 `text_utils.py` 里 **0 命中**（唯一相近的是 docstring 里提到 `path.stem`） |
| 碰数据库吗 | **碰**。`_porter_stem` 内部 `import sqlite3` → `sqlite3.connect(":memory:")` → `CREATE VIRTUAL TABLE s USING fts5(w, tokenize='porter')`（L1428–1430）。虽然是内存库，但**一个"文本工具"模块为了给单词取词干而建了一张 FTS5 虚表** |
| 引入第三方依赖吗 | 引入 `jieba`（`segment_for_fts` 内延迟导入）。这是**检索子系统**的依赖，不是文本工具的 |
| 有跨子系统知识吗 | 有。① 标准号的**存储形 vs 比较键**（`store_standard_no` 的 docstring 直接写着「这是落库前的口径」）；② FTS5 的查询语法坑（`fts_match_expr` 的 docstring 写着 `'GB 30871-2022' → no such column: 2022`）；③ 浏览器 HTML 解析语义（`xmp`/`plaintext`/`textarea` 的可见性与 raw text 规则）；④ 采集侧 `resp.text` 与 `resp.content` 两条路径的字节可达性 |
| 有"生产库实测数字"吗 | 大量：`_latin_prefix_token` 里写着「全库 ≥4 字母的拉丁词 8,548 个、过闸 8,410 个」「候选池中位 1.098× / p90 20.5× / 最大 3144×」；`strip_ocr_source_suffix` 里写着「生产库 1,430 篇（占 8,983 篇的 15.9%）」。**这些是业务度量，不是文本工具的度量** |

> 一句话：这个文件的前半是「OCR 文本清洗」，后半是「**标准身份 + 检索口径 + 采集判据**」被塞进了同一个文件名下。

### 2.5 有没有函数该搬到别的子系统

按"现在归谁"给判断：

| 函数 | 该归谁 | 依据 |
|---|---|---|
| `segment_for_fts`、`_porter_stem`、`_plain_case`、`_latin_prefix_token`、`fts_match_expr` | **检索（`retrieval` / `storage` 的 FTS 口径）** | 它们服务的是 `clause_fts` 与 `material_fts` 两条检索线；`_porter_stem` 要 SQLite FTS5、`segment_for_fts` 要 jieba |
| `canon_standard_no`、`store_standard_no`、`store_standard_name`、`standard_key`、`standard_no_key`、`law_name_key`、`clean_standard_name`、`strip_duplicate_suffix`、`strip_ocr_source_suffix` | **领域身份（`domain` 或 `knowledge/standard_no`）** | 它们是「同一部标准的不同写法」「存储形 vs 比较键」的问题，与文本清洗无关 |
| `html_to_text`、`_strip_script_style`、`_inside_unclosed_tag`、`_inside_raw_text`、`strip_tags`、`html_unescape`、`looks_like_binary`、`looks_like_binary_bytes` | **采集（`materials` / `update.channels`）** | 判据来自浏览器渲染语义与 HTTP 传输语义，不是条款文本 |
| `clean_clause_text`、`strip_watermark_lines` | **入库清洗（`ingestion`）** | 它已经是「入库链的唯一所有者」，且为了不反向依赖 ingestion，把图例切除做成参数注入（`legend_stripper`）——**这个注入本身就是"放错层"的自证** |
| `space_clause_numbers_text/html`、`sup_unit_exponents_text/html`、`pua_bond_dash_html` | 展示/入库的**排版层** | 现在是"入库一份、出口一份"的成对实现，成对留在同一处是对的 |
| `_match_std`（零调用） | 应删 | 与 `_match_key` 同职，且没人用 |

### 2.6 真正被外部调用的有多少、只有自己用的有多少（61 个全量分类）

按引用位置分类（全仓 1,318 个 `.py` 文件，单遍标识符统计）：

| 分类 | 个数 | 说明 |
|---|---|---|
| ① `src/` 内被调用（生产用） | **33** | 真正的公共 API |
| ② 只有 `scripts/` / `eval/` / `var/` 调用 | **8** | `_glue_formula_fragments`(eval)、`normalize_label_comma`、`normalize_pua_separators`、`space_clause_numbers_text`、`strip_formula_leader`、`strip_ocr_source_suffix`、`strip_watermark_lines`、`sup_unit_exponents_text` |
| ③ 只有 `tests/` 调用 | **4** | `_inside_raw_text`、`_latin_prefix_token`、`_porter_stem`、`_strip_script_style` |
| ④ 文件外零引用（仅内部调用或真死） | **16** | 其中 15 个是纯内部 helper（`_glue_two_letter_units` 等），**1 个是真死**（`_match_std`） |

> 注意：③ 那 4 个虽然"只有测试调"，但它们是 ① 的**内部依赖**（`_latin_prefix_token`/`_porter_stem`
> 被 `fts_match_expr` 调、`_strip_script_style` 被 `html_to_text` 调、`_inside_raw_text` 被
> `_strip_script_style` 调）。这不是死代码，是"通过公共函数被间接使用"。

**抽查 10 个函数的真实调用点**（`grep` 结果，只列生产侧第一条）：

| 函数 | 生产调用点（例） |
|---|---|
| `clean_clause_text` | `src/core/ingestion/pipeline.py:1364`（`from src.core.text_utils import (clean_clause_text as _clean_text,`），另 `var/ocr-loop/evolve.py:309` |
| `strip_watermark_lines` | `scripts/repair_patch_watermarks.py:65`（`new = strip_watermark_lines(v, own_standard_no=std or None)`）；`src/` 内只经 `clean_clause_text` 间接调用 |
| `html_to_text` | `src/core/materials/harvest.py:78`、`:224` |
| `fts_match_expr` | `src/core/retrieval/hybrid_engine.py:159`、`src/core/retrieval/term_bridge.py:292`、`src/core/storage/material_repo.py:351` |
| `segment_for_fts` | `src/core/api/server.py:208`、`src/core/storage/clause_repo.py:287`、`src/core/storage/material_repo.py:315` |
| `canon_standard_no` | `src/core/retrieval/hybrid_engine.py:95`、`:106` |
| `store_standard_no` | `src/core/ingestion/bulk.py:225`、`:246`；`dry_run.py:126`；`law_text.py:225` |
| `standard_no_key` | `src/core/materials/track_l.py:79`、`:84` |
| `law_name_key` | `src/core/materials/track_l.py:98`、`:104`、`:106` |
| `latex_to_text` | `src/core/ingestion/pipeline.py:524`（`parts.append(latex_to_text(content))`） |
| `normalize_pua_latin` | `src/core/api/server.py:1152`、`ingestion/mineru_adapter.py:531`、`ingestion/pipeline.py:1666` |
| `glue_ocr_spaced_units` | `src/core/ingestion/pipeline.py:535` |

---

## 三、inspector.py

### 3.1 它是什么、是巡检的哪一环

模块 docstring 第 1 行：`巡检编排器（阶段六·批次2）：万级分层调度执行引擎`。

「更新巡检」这条线一共四个环节，inspector 是**第 3 环（执行 + 判定 + 落库）**：

```
① 定时/手动 → 建批      scheduler.py（定时建批） / routes_update.py（手动建批）
② 分派执行   → 跑批      inspector.run_batch
③ 单号探测   → 触网      channels/*（适配器降级链）
④ 判定+落库  → 事件      inspector._probe_number / judge_result / _commit_outcome
```

它**只问「这个标准号有没有新版 / 有没有被废止」**，不问「渠道站点还活着吗」（那是 `channel_probe.py`）。

### 3.2 分段结构

| # | 段（锚点） | 干什么 |
|---|---|---|
| 1 | 模块 docstring（`职责（pipeline/02 §1…`） | 9 条职责契约：建批/跑批/判定映射/防重/终态恒等式/暂停恢复/验证码/预算/并发一致性 |
| 2 | `MAX_ATTEMPTS` / `CONCURRENCY` / `DEFAULT_DAILY_BUDGET` / `_TIER0_SQL` / `_TIER1_SQL` | 编排常量 + 两个分层的圈号 SQL |
| 3 | `app_config 工具`：`get_config` / `set_config` / `_today` / `_utcnow` | 读/写 app_config KV |
| 4 | `日预算`：`daily_budget_limit` / `budget_used_today` / `budget_remaining` / `_consume_budget` | 按自然日滚动的 tier1 额度 |
| 5 | `数据访问`：`_load_batch` / `get_inspect_batch` / `_load_checkpoint` / `select_standard_nos` | 批次行与断点读取、按 layer 圈清单 |
| 6 | `创建/状态迁移`：`create_inspect_batch` / `_transition_status` | 建批（控制面 + 镜像锚行）+ 状态机 |
| 7 | `探测与判定`：`ProbeOutcome` / `judge_result` / `_probe_number` / `_classes_info` / `_classes_info_for_miss` / `_build_adapters` / `_FALLBACK_CHAIN` | 单号走降级链、把渠道结果映射成 change_type + 四色、五类归因 |
| 8 | `原子提交`：`_commit_outcome` / `_debt_from_events` / `_write_captcha_wait` | 单号一事务（事件+计数+断点+预算）+ 欠账回收 + 验证码告警 |
| 9 | `运行句柄（暂停协调）`：`_RunHandle` / `_RUNS` / `request_pause` / `pause_batch` / `_merged_checkpoint` / `resume_batch` | 阻塞式暂停、幂等恢复 |
| 10 | `主流程`：`run_batch` | 线程池分块、按清单序收敛、终态裁决 |
| 11 | `审计辅助`：`captcha_wait_events` | 前端任务卡片的数据源 |

| 口径 | 数量 |
|---|---|
| 顶层 def/class 合计 | **30**（28 个函数 + 2 个类：`ProbeOutcome`、`_RunHandle`） |
| 公开 | **15**（14 函数 + `ProbeOutcome`）— `get_config`、`set_config`、`daily_budget_limit`、`budget_used_today`、`budget_remaining`、`get_inspect_batch`、`select_standard_nos`、`create_inspect_batch`、`ProbeOutcome`、`judge_result`、`request_pause`、`pause_batch`、`resume_batch`、`run_batch`、`captcha_wait_events` |
| 内部私有 | **15**（14 函数 + `_RunHandle`） |
| 嵌套函数 | **0** |

### 3.3 入口是哪个、被谁调

- **对外入口（生产）**：`run_batch(batch_id)` —— 同步跑到终态并返回批次行。
- **谁调它**：
  | 调用方 | 位置 | 场景 |
  |---|---|---|
  | `src/core/api/routes_update.py:75` | `inspector.run_batch(batch["batch_id"])` | 用户点「开始巡检」 |
  | `src/core/update/scheduler_runner.py:65` | `res = inspector.run_batch(bid)` | 定时器建完批后自动跑 |
  | `src/core/update/scheduler.py:159` | 经 `inspector.resume_batch(...)` → `run_batch` | 「预算暂停」跨日自动恢复 |
  | `src/core/update/__init__.py` | re-export | 包级 API |
- **建批入口**：`create_inspect_batch(tier, trigger)` ← `routes_update.py:68`（manual）、`scheduler.py:129`（scheduled）。
- **其余 API**：`pause_batch`/`resume_batch`/`get_inspect_batch` 都由 `routes_update.py` 的 HTTP 端点调。
- `run_batch` 内部再分三块：`_probe_number`（**工作线程里只触网**）→ `judge_result`（纯函数）→
  `_commit_outcome`（**单事务落库**）。

### 3.4 与 channel_probe.py / scheduler.py / scheduler_runner.py 的关系

| 模块 | 与 inspector 的关系 | 证据 |
|---|---|---|
| `scheduler.py`（170 行） | **上位编排，不执行**。`tick()` 里只调 `inspector.create_inspect_batch(...)` 与 `inspector.resume_batch(...)`；自身 docstring 明说「调度器只负责「建批 / 恢复」，不直接执行批次——执行由 API 层或运维入口调用 `inspector.run_batch`」 | `scheduler.py:13–14`、`:129`、`:159` |
| `scheduler_runner.py`（177 行） | **把 scheduler 接上生产的线程壳**。`tick_and_run` → `_run_batches` → `inspector.run_batch`。它自己的 docstring 写着为什么需要单独一个文件：`UpdateScheduler.start()` **全仓无人调用**，且 `tick()` 只建批不执行，批会一直躺在 `pending` | `scheduler_runner.py:8–12`、`:65`、`:87` |
| `channel_probe.py`（356 行） | **完全不同的另一件事，只是都在「渠道」这个词上**。`channel_probe` 探「渠道站点本身还活着吗」（HTTP 状态 + 页面锚点 + `min_links`），写**渠道台账**（`channel_repo.record_probe`）；inspector 探「标准号有没有变化」，写**变更事件**。两者唯一交集是都用 `channels` 包的适配器与 transport | `channel_probe.py:1–14`（`与适配器能力的分工（两根轴，不许互相顶替）`）、`:348` |

补充一条我看清的边界：`inspector` 里 30 处 `upd_log(...)` 调用**不写表** —— `channels/base.py` 的
`upd_log` 只是拼一行文本交给 `LOGGER`。真正写 `event_log` 的只有 `create_inspect_batch`、
`_commit_outcome`、`_write_captcha_wait` 三处。

### 3.5 它写哪些表

| 表 | 写什么 | 在哪 |
|---|---|---|
| `bulk_import_batch` | INSERT 控制面批次行（`batch_kind='inspect'`）；UPDATE 状态/计数/断点/总数 | `create_inspect_batch`、`_transition_status`、`_commit_outcome`、`run_batch` |
| `update_check_batch` | INSERT 同值 `batch_id` 的**镜像锚行**（`update_change_event.batch_id` 的外键落点）；UPDATE 状态/计数/总数 | 同上 |
| `update_change_event` | INSERT 一条变更事件（`chg_` + ULID，含 `latest_info_json` 五类归因） | `_commit_outcome` |
| `event_log` | INSERT 四类：`update/batch_created`、`update/change_detected`、`update/probe_failed`、`update/captcha_wait` | 上述三处 |
| `app_config` | INSERT/UPDATE：`inspect.daily_full_sweep_budget`、`inspect.budget_date`、`inspect.budget_used` | `set_config`、`budget_used_today`、`_consume_budget` |

**只读不写**：`doc_meta`、`watch_list`、`user_doc_bookmark`（`_TIER0_SQL`/`_TIER1_SQL`/`select_standard_nos`）、
`channel*` 台账（经 `channel_repo.list_channels()` 一次读好传进工作线程）。

---

## 四、共同问题（重复实现 / 死代码 / 超长函数 / 过时注释）

### 4.1 「同一件事两个实现」

按证据强度排序。**第 1 条最硬：代码注释自己承认了。**

| # | 同一件事 | 实现 A | 实现 B | 证据 / 后果 |
|---|---|---|---|---|
| 1 | **「页码 + 标准号」页眉判据** | `pipeline.py` 的 `_STD_CODE_FRAG`、`_STD_CODE_LINE`、`_frag_key`、`_own_key_of`、`_strip_foreign_frag` | `text_utils.py` 的 `_WM_STD_CORE`、`_RE_WM_HEADER`、`_RE_WM_HEADER_TAIL`、`_match_key`、`_std_matches`、`_sub_own_header`、`_strip_wm_tokens`、`strip_watermark_lines` | `pipeline.py` 的注释原话：`⚠ 这两个判据是「页码 + 标准号」的**第二份实现**（第一份在 text_utils 的水印族）`。两边口径已经不同：pipeline 允许 `\d{1,6}` 号与任意 1–4 大写字母前缀，text_utils 要求 `\d{3,5}` 号 + 前缀白名单（`GB|DB|JGJ|…`）⇒ 一边认得的页眉另一边可能漏 |
| 2 | **图例（标引序号说明）判据** | `_is_figure_legend`（块级，`_RE_LEGEND_HEAD` + `_RE_LEGEND_ITEM`，条目只认数字型） | `strip_figure_legend_segment` / `_strip_headerless_legend`（文本级，`_RE_LEGEND_HEAD_ANY` + `_RE_LEGEND_ITEM_ANY`，条目含字母型、要求 `[—–]{2,}`） | 同一个文件里两套阈值。`_RE_LEGEND_ITEM` 是 `\d{1,2}\s*[—\-–~]{1,3}`，`_RE_LEGEND_ITEM_ANY` 是 `[0-9A-Za-zΑ-Ω…]{1,4}\s*[—–]{2,}` ⇒ 单破折号/字母型条目两边判定不一致 |
| 3 | **HTML → 纯文本** | `text_utils.html_to_text`（声明为规范实现） | `api/server.py:_html_to_text`、`llm/ks_answer.py:_html_to_text_compact`、`quality/clause_health.py:clause_health_html_to_text` | `text_utils` 的 docstring 原话：`此前同一算法在**三处**各有一份… **没有**顺手改那三处的调用点…登记为待办`。grep 确认三处仍在 |
| 4 | **标准号归一 / 比较键** | `text_utils` 4 个（`canon_standard_no` / `standard_key` / `standard_no_key` / `store_standard_no`） | `update/channels/base.py:norm_no`、`ccs_fetcher._seed_key`、`clause_repo._standard_body`、`pipeline._hier_from_no`、`pipeline._frag_key`、`docx short_code` | 各 docstring 都写了「口径不同」，但**没有任何机器判据**能证明它们在同一输入上不矛盾。`norm_no` 的注释自己记着一次真失配：`norm_no 原先**不折**它们，于是 GB/T－17098 与 GB/T-17098 在匹配侧归一出永不相等` |
| 5 | **完整入库流程** | `pipeline.run_full_ingest`（12 步） | `law_text.ingest_law_text`（自建 model / 自建边 / 自写 doc 行 / 自查 CCS） | `law_text.py` 注释原话：`pipeline.py 的 resolve_edges 一直有这道闸，这里漏了 ⇒ 两条入库路径行为不一致`。缺的还有：页几何、`catalog_hidden`、`_write_filing_state`、行级 span、页界 |
| 6 | **app_config KV 读写** | `inspector.get_config` / `set_config`（被 `discover`/`data_package`/`law_source.catalog` 引用） | `announce.py:185,198`、`discover.py:602,609,621,628`、`subscriptions.py:24,45` 各自直接写 SQL | 「工具函数存在，但有 3 个兄弟模块绕过它」 |
| 7 | **同一文件内的近重复** | `text_utils._match_key`（有人用，2 处） | `text_utils._match_std`（**零调用**） | 见 §4.2 |
| 8 | **已收口的正面对照** | `clause_repo._seg` → `from src.core.text_utils import segment_for_fts` | — | 这是**做对了的那一例**：注释写 `保留这个私有名只是为了不动既有调用点；实现只有一份` |

### 4.2 死代码（全仓 0 调用）

**A. 真死：定义了，全仓一次都没被调用**

| 位置 | 证据 |
|---|---|
| `inspector.py` 的 `_utcnow`（L112–113） | `grep '_utcnow'` 全仓 **1 处命中，就是 def 行本身**。它返回 `datetime.now(timezone.utc)`，但全文用的是 `sqlite datetime('now')` 与 `time.strftime` |
| `text_utils.py` 的 `_match_std`（L1341–1345） | `grep '_match_std'` 全仓 **1 处命中，就是 def 行本身**。同职的 `_match_key`（L1997）被 `_std_matches` 与 `_sub_own_header` 各调一次 |

**B. 生产零调用（只剩测试在调，代码注释有意保留）**

| 位置 | 证据 | 代码自己的说法 |
|---|---|---|
| `text_utils.normalize_wraps`（L635） | 引用了它的**生产文件全是注释**：`api/server.py:2588`、`api/server.py:2786`、`exports/office_roundtrip.py:232`、`ingestion/pipeline.py:1577`（都是"已退役"的注释），另有 `tests/test_text_utils.py` 10 处 | docstring 写 `函数保留：读时兜底与历史工具脚本仍可能引用` —— **"历史工具脚本"这一半没被任何 grep 证实**（`scripts/` 下 0 命中） |
| `pipeline.analyze_preview`（L1518） | 生产调用点 **0**：`src/` 内 2 处命中都是 `dry_run.py` 的注释，`scripts/`、`plugin/` 内 0；只有 `tests/test_dryrun.py`、`tests/test_dryrun_report.py` 在调 | docstring 写 `它是被冻结的老接口（tests/…::test_dry_analyze_preview_contract_frozen 钉住键集合）` —— 是**有意保留**，但真正的预览入口是 `dry_run.analyze_preview_report`（被 `routes_ingest_preview.py:83`、`preview_jobs.py:114` 调用） |

**C. 不可达代码**

| 位置 | 为什么不可达 |
|---|---|
| `inspector._probe_number` **L444–454** | L435–443 是一条**无条件 return**（`return ProbeOutcome(kind="failed", …)`）。其后的 `if miss_channel is not None:` 与末尾 `return ProbeOutcome(kind="failed", …)` 永远执行不到。判断依据：L423 的 `if miss_channel is not None and len(tried) == len(usable):` 之后就是那条无条件 return |
| `pipeline._extract_vector_table_items` **L1820–1821**（`if is_ocr: return [], set()`） | `is_ocr` 恒为 `False`：两个调用点（`pipeline.py:2135`、`dry_run.py:305`）都传 `bool(result.get("is_ocr"))`，而 `mineru_adapter.parse_pdf_with_mineru` 里是 `is_ocr = False`（硬编码，L552）后在返回值原样带出（L582） |

**D. 未使用的 import**

| 文件 | 名字 | 证据 |
|---|---|---|
| `inspector.py` | `UPD_CAPTCHA_BLOCKED`、`CHANGE_TYPES`、`LEGAL_STATUSES` | 从 `channels.base` 导入（L50–59），但 AST 去掉 docstring 后全文无引用。判定方法：`ast.unparse` 剥离 docstring 后正则匹配 ⇒ 三个名字 0 命中 |

### 4.3 超过 100 行的函数（该拆的信号）

| 文件 | 函数 | 行数 | 干什么 |
|---|---|---|---|
| `pipeline.py` | `run_full_ingest` | **397** | 12 步入库全编排 + 18 个返回键 |
| `pipeline.py` | `split_items_into_clauses` | **367** | E1–E7 切分（三态机 + 五道闸门 + 表格/插图绑定 + 行级拆条） |
| `pipeline.py` | `build_clause_models` | **201** | 切分 → 模型（清洗、页界、span、分型、边） |
| `inspector.py` | `run_batch` | **172** | 线程池分块 + 按序收敛 + 四类终态裁决 |
| `inspector.py` | `_probe_number` | **121** | 单号降级链 + 预算 + 未命中/失败判定 |
| `pipeline.py` | `_cell_html` | **116** | 单元格 HTML（基线聚类 + 上下标判定 + 水印 span 过滤） |
| `pipeline.py` | `load_middle_items` | **100**（刚好到线） | middle.json → 条目 |

`text_utils.py` **一个都没有**：最长的是 `glue_ocr_spaced_units`（91 行），其次 `strip_watermark_lines`（86）、
`_strip_script_style`（70）。⇒ 这个文件的问题是**职责过多**，不是"函数过长"。

### 4.4 过时注释（带 git 年龄；HEAD = `8555d140` 2026-10-24）

| # | 位置 | 现在写着什么 | 事实 | git 年龄 |
|---|---|---|---|---|
| 1 | `pipeline.py` L10 | `它与**同一个文件下方** :658-661 的废弃说明互相矛盾` | 废弃说明现在在 **L709–712**；L658–661 落在 `load_middle_items` 的 image 分支里（`for span in line.get("spans")` / `if img_rel:`）。**行号已漂移 51 行** | 2026-09-17 → **37 天** |
| 2 | `pipeline.py` L1573 | `与 split_items_into_clauses L156 同一正则` | L156 现在是 `_TOC_HEAD = re.compile(r"^目\s*次")`；那个"吞点合并"正则实际在 `split_items_into_clauses` 内的 `re.sub(r"(\d)\.\s*\n\s*(?=\d)", r"\1.", text)` | 2026-09-12 → **42 天** |
| 3 | `pipeline.py` L2083–2087 | `pipeline.py:2021 的封面块提取会**无条件**遍历 result["blocks"]` / `（pipeline.py:2037 insert_page_geometries …，2096 还取 len()）` | 封面块提取在 **L2244**；`insert_page_geometries` 在 **L2260**；`len(result["geometries"])` 在 **L2401**。三处行号全漂 | 2026-09-17 → **37 天** |
| 4 | `inspector.py` L10（模块 docstring） | `渠道降级链 official_gb→govcn` | 实际链是 `official_gb→ndls→govcn`（`ndls` 是 2026-09-18 插进去的，同文件 L523 的注释自己写着 `泛查兜底链（official_gb→ndls→govcn）`）。**模块开头那段是过时的** | 2026-09-18 → **36 天** |
| 5 | `text_utils.py` L1764–1765 | `**没有**顺手改那三处的调用点…登记为待办` | 三处（连新写的这份共 4 份）**一份都没收口**，grep 仍能逐个找到 def | 2026-09-17 → **37 天** |
| 6 | `text_utils.py` L954 | `**后端版** stripEmbeddedTable` | 全仓 `grep 'stripEmbeddedTable'` **只有这 1 处命中（就是这句 docstring）** ⇒ 它指向的前端实现已经不存在了 | — |
| 7 | `text_utils.py` L638–641 | `新入库/卡片出口/WPS 出口均不再调用本函数…函数保留：读时兜底与历史工具脚本仍可能引用` | 前半句**成立**（生产 0 调用）；后半句**没有证据**（`scripts/` 里 0 命中）。即"保留理由"这一半是没核过的 | 2026-09-01 起（blame 归到文件首见的 2026-09-12）→ **42 天** |

另记一条**不是过时、但值得知道**的：`pipeline.py` L2166–2174 的 `calibrate_new` 注释写「已正确则全
bottom 零改动，幂等」；L2088–2091 的注释写「空 dict 会让页几何无行…按页定位证据不可用」。
两条都仍然成立，但后者覆盖不到 `reuse_parse` 路径（见 §1.10 第 3 条）。

---

## 五、我没搞清楚的（如实登记）

1. **`docx_ingest.py` / `reingest.py` 只读了结构与入口**（函数名 + 顶部 docstring + 对
   `run_full_ingest` 的调用点），**没有逐行读函数体**。⇒ §1.8 里对这两个模块「不是重复实现」的判断
   只在**入口层面**成立，函数体级别是否另有重复（例如标准号派生、状态写入）**未核**。
2. **`law_text.py` 只读了 L1–120 与 L255–374**。L121–254（`split_law_text` / `split_law_enum_text` 的实现体）
   与 L375–397（`main`）**未读**。⇒ 「它是第二套入库」这个结论来自 L255–374，切分逻辑本身的重复度未评。
3. **`dry_run.py` 没有通读**（521 行），只按 grep 看了它与 pipeline 的 5 个 import 与调用点。
   ⇒ `pipeline.analyze_preview` 与 `dry_run.analyze_preview_report` 的**逐行重复比例**没算。
4. **§1.10 第 1 条（`total_clauses = n_normal - n_pre`）是纯静态推断**。我没有跑一次真入库，
   也没有查数据库里 ui 显示的实际数字。⇒ 它是「算术与口径不符」的**代码事实**，
   但「现场数字到底偏差多少」**未验证**。
5. **前端是否也有同类实现未核清**：`plugin/client/KsEvidenceTab.tsx:2509` 有 `escDupNoLocal`
   （与 `pipeline` 注释里提到的"老前端 `escDupNo`"同职），但我没有系统比过前端与
   `text_utils` 的清洗实现。`stripEmbeddedTable` 已确认前端 0 命中。
6. **`_rows_of` 在 `ccs_fetcher.py` / `ttzb.py` 里的同名命中是什么，没核**：标识符统计显示那两处
   各 2 次，但很可能是同名局部变量而非调用 `pipeline._rows_of`。⇒ 我没有把它们算作调用方。
7. **没有跑任何测试 / 门禁**（任务禁止）。⇒ 所有「不可达」「零调用」结论都是**静态**的；
   `_probe_number` L444–454 是否被某个动态调用（`getattr`/反射）用到，我按 grep 结果判断为否，
   但那是抽样，不是全量证明。
8. **`src/core` 还有多少同类大文件没摸底**：我只读了这三个 + `update/` 目录的尺寸表
   （`announce.py` 751 行、`discover.py` 559 行、`web_ingest.py` 439 行为次大的三个），
   **`query/`、`retrieval/`、`quality/`、`vision/` 下的最大文件完全没看**。
9. **`MAX_ATTEMPTS` / `CONCURRENCY` / 日预算 500 与 `pipeline/06` 设计文档的约定是否一致没核**：
   我只核了代码内部自洽（注释、常量、`app_config` 键名三者相符），没打开那份设计文档对账。
