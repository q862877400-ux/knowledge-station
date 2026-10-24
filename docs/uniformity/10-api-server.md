# api/server.py 事实地图

> 调查对象：`src/core/api/server.py`。**只读**调查（未改任何源码、未跑 pytest / 门禁）。
> **观测时间**：2026-10-24，工作树。
> **引用约定**：行号是本次实测的 AST 边界（`ast.end_lineno`），同一条结论都给可搜索文字
> （函数名 / docstring 片段 / 端点路径），行号漂移时按文字定位。

---

## 0. 先更正任务书里的两个数字（实测，不是估算）

| 任务书说法 | 实测 | 复现命令 |
|---|---|---|
| `server.py` 3,115 行 | **3,341 行**（其中空行 228） | `.venv\Scripts\python.exe -c "print(len(open('src/core/api/server.py',encoding='utf-8').readlines()))"` → `3341`；PowerShell `Get-Content \| Measure-Object -Line` 得 **3113**，因为它**不计空行** —— 任务书里的 3,115 就是从这条命令来的 |
| 176 条端点里它占 107 条 | **67 条**（method×path 装饰器）；`src/core/api/` 8 个模块合计 **176** | `Select-String -Path src/core/api/*.py -Pattern '@router\.(get\|post\|put\|delete\|patch\|api_route)\|@app\.(get\|post\|put\|delete\|patch)'` → 每文件：routes_update 32 · routes_kb_folders 24 · routes_materials 18 · routes_channels 10 · routes_law 10 · routes_ingest_preview 6 · routes_report 6 · routes_settings 3 · **server.py 67** · 合计 **176** |

**67 条占 176 的 38%，不是 61%。** 按唯一路径算是 **58 条**（9 条路径挂了两个方法：8 条 GET+POST，`/bookmark-folders/{folder_id}` 是 PUT+DELETE —— `methods: 67 unique paths: 58` 实测）。
`docs/uniformity/01-core.md` 与 `docs/DEVELOPMENT-HISTORY.md` 里出现过的「127 个端点」是**另一次口径**
（当时只 AST 扫了 6 个模块，materials / kb_folders / channels 三个文件还没并进来）—— 两个数都不假，
但分母不同，引用时必须说清是哪一次的口径。

---

## 一、create_app 闭包结构 + 不可测清单

### 1.1 边界与规模（AST 实测）

| 项 | 实测值 |
|---|---|
| `create_app` 起止 | **L278 – L3274**（签名 `def create_app(token: str) -> FastAPI:` 到 `return app`） |
| 长度 | **2,997 行**，占全文件 **89.7%** |
| 闭包内嵌套函数 | **103 个**（含 `create_app` 自身；`ast.walk` 全深度） |
| ├ 第 1 层 | 81 个 = **67 个路由处理器** + **14 个非路由辅助函数** |
| ├ 第 2 层 | 16 个（`_frac_headers` `_appendix_items` `_with_appendix` `_split_chapter_title` `sort_key` `classify` `build_folder` `event_stream` `_inject_figs` `_inject_formulas` `_ptext` `_p_lead` `_p_formula` `_p_tail` `_p_join` `_mrg_col`） |
| └ 第 3 层 | 5 个（`_fig_sub` `_norm_eq` `_pick_fno` `_f_sub` `_next_chunk`） |
| **非路由函数合计** | **35 个**（14 + 16 + 5）—— 这些全部拿不到模块外，只能通过 HTTP 端点或源码静态扫描触达 |

补充事实：`_HeavyGateMiddleware`（L214–257）和 `bound_threadpool_once` / `is_heavy_path` /
`warm_retrieval_stack` / `_clause_number_sort_key` 是**模块级**的（可 import、可单测），
闭包只管路由与业务辅助。

### 1.2 14 个第 1 层辅助函数 + 测试状态

「tests 命中」= `Select-String -Path tests/*.py -Pattern <函数名>` 的条数（含注释/文档字符串；
所以**命中 ≠ 被测**，见右列判读）。

| # | 函数 | 行 | 干什么 | tests 命中 | 判读（有没有被独立测过） |
|---|---|---|---|---|---|
| 1 | `auth_middleware` | 312–324 | token 鉴权中间件；`/api/v1/health` 与 `OPTIONS` 放行 | 0（按名字） | **行为级覆盖**：多条用例断言未带 token → 401（`test_backup.py:64`、`test_vision.py:65`、`test_phase12.py:117`）。但**放行名单本身没有一条用例逐条钉住**（`/health` 与 OPTIONS 各一条断言都没有定向用例） |
| 2 | `_json_error` | 332–336 | 统一错误信封 `{code:HTTP状态, status:"error", error:<字符串码>, message}` | 0 | 只被端点用例间接覆盖；**没有一条用例直接断言信封字段**（字段名 `code` 装 HTTP 状态、字符串码进 `error` —— 这个反直觉映射没有任何测试钉住） |
| 3 | `_write_debug_dump` | 2094–2144 | 把一次提问的全链路（trace / 证据 / history[-4:] / 答案前 4000 字 / 核验）写 `debug_dump` | 1（`test_egress.py:111` 的 docstring） | **间接覆盖**（`test_egress.py` 断言写完能查到），但 dict/模型三形态分支只有注释说明，无对应用例名 |
| 4 | `_write_ks_answer_dump` | 2146–2192 | 把 `/ks/answer` 的答案落 `debug_dump`（D2 外发审计补课） | **0** | **无独立测试**；只靠 `test_egress.py:101/119/162` 走端点时顺带写一次 |
| 5 | `_safe_count` | 2195–2200 | `SELECT COUNT(*)` 失败降级 0 | 0 | 无；只在 `health_board` 里被间接执行 |
| 6 | `_expand_title_clauses` | 2525–2553 | 命中标题条款（正文 <80 字）时自动带上子条款，上限 8 条 | 3（全是 `test_appendix_split.py` 里的**本地重写正则**，不碰本函数） | **实际未测**，且**与 `llm/ks_answer.py:1167` 是第二份实现**（见 §三.3） |
| 7 | `_fetch_clause` | 2555–2557 | 薄壳 → `clause_repo.fetch_full_clause` | 0 | 无（薄壳，风险低） |
| 8 | `_answer_confidence` | 2559–2577 | **转发**到 `llm.ks_answer.answer_confidence` | 6（`test_answer_confidence.py`） | **有专门的防分叉用例**（AST 静态扫描：剥 docstring 后必须只剩一行转发）。这是全闭包里**唯一**被静态钉住的辅助函数 |
| 9 | `_html_to_text` | 2579–2586 | 薄壳 → `quality.clause_health_html_to_text` | 17（但打的是**被转发的那份**） | 实现侧测得充分（`test_quality_rules.py` 逐字符等价），薄壳本身无测试 |
| 10 | `_content_html` | **2623–3140** | 条款正文 → 展示 HTML（518 行，见 §三.2） | 11 条 `content_html` 字样，其中 `test_patches.py:180/208` 是**在测试里本地复刻一份语义**，`test_table_position_render.py` 走端点 | **部分行为覆盖**（端点级断言页位/表格归位），**函数本体无单测**；且有第三份"复刻"跟着漂 |
| 11 | `_full_evidence` | 3143–3169 | 核验前从 DB 回填全量正文（ev_dict 的正文截断到 800 字） | 0 | 无；只在 SSE 核验分支间接跑 |
| 12 | `_ev_dict` | 3172–3218 | 证据对象 → 前端/LLM 用的 dict（收藏、批注、补丁、置信度富化） | 1（`test_patches.py:152` 注释） | **无直接用例**；它是 `/clauses/resolve` 与 SSE 两条路径的公共出口 |
| 13 | `_placeholder_answer` | 3220–3228 | 无 Key / LLM 失败时的规则拼装答案 | 0 | 无（只在降级分支） |
| 14 | `_sse` | 3230–3231 | 拼 `event: …\ndata: …\n\n` | 5（全是 `test_sse_*` 用例名，不是本函数名） | 行为级覆盖（`test_contract.py:11` 冻结事件顺序） |

**结论（本次摸底的核心关切）**：`_answer_confidence` 那次分叉被发现了，靠的是事后补了一条
**静态检查**用例。但**同一个坑还有一个活口没堵**：`_expand_title_clauses` 仍是两份实现，
`_content_html` 的语义在测试里还有一份复刻，`_ev_dict` / `_write_ks_answer_dump` / `_safe_count`
/ `_full_evidence` 连一条定向用例都没有。**它们全都拿不到模块外**，所以任何一条分叉都只能靠
"有人记得同时改两处"（`server.py:2538` 的注释原话：*"与 ks_answer._expand_title_clauses 同步放宽"*）。

### 1.3 第 2/3 层嵌套函数（20 个，全部不可测）

`_frac_headers`（X-Frac-* 三个响应头）· `_appendix_items` / `_with_appendix`（附录进目录）·
`_split_chapter_title`（章标题截断，正则 + 重复单元检测）· `sort_key`（目录自然排序）·
`classify`（收藏树里的文档分类）· `build_folder`（55 行，收藏夹树装配）· `event_stream`
（**171 行**，SSE 事件生成器）· `_inject_figs` / `_fig_sub`（图题 → 内嵌截图占位）·
`_inject_formulas` / `_norm_eq` / `_pick_fno` / `_f_sub`（公式 → KaTeX span + 全局序匹配）·
`_ptext` / `_p_lead` / `_p_formula` / `_p_tail` / `_p_join` / `_mrg_col`（段落合并且双栏分列）·
`_next_chunk`（把生成器包成线程池可调用）。

其中 `_pick_fno`（LaTeX 归一化相似度匹配，阈值 0.35）和 `_split_chapter_title` 都是**纯函数、
零依赖、最容易单测**的两个 —— 却都埋在闭包里。

### 1.4 闭包捕获了什么

从外层（模块）解析的名字（`create_app` 内引用、但不在函数内赋值）：

- **参数**：`token`（只被 `auth_middleware` 用，`secrets.compare_digest` 比对）。
- **局部对象**：`app`（被 67 个 `@app.*` 装饰器捕获；处理器体里不再使用 `app`）、
  `_json_error`（被 ~25 个处理器捕获，也是 8 个 `routes_*.register(app, _json_error)` 的入参）。
- **模块级常量/函数**：`get_settings` `get_db_connection` `init_schema` `resolve_status`
  `logger` `secrets` `json` `time` `asyncio` `Path` `os` `datetime` `weakref`
  `_STARTED_AT` `_clause_number_sort_key` `_TBL_CAPTION_LINE` `_FIG_CAPTION_SEG` `_FORMULA_SEG`。
- **跨处理器的闭包内互调**（这是不可测的关键）：`_content_html` ← `doc_full_clauses` / `_ev_dict`；
  `_ev_dict` ← `resolve_clause` / SSE；`_full_evidence` / `_expand_title_clauses` /
  `_answer_confidence` / `_placeholder_answer` / `_sse` ← `event_stream`；
  `_write_ks_answer_dump` ← `ks_answer_endpoint`；`_write_debug_dump` ← SSE + `_write_ks_answer_dump`。

---

## 二、67 条端点归类 + 可疑项

### 2.1 分组（合计 67）

| 组 | 条数 | 端点 |
|---|---|---|
| **问答** | 2 | `POST /chat/completions`（SSE，L1765–2092，328 行）｜`POST /ks/answer`（L2202–2233） |
| **证据/条款元数据** | 3 | `GET /clauses/resolve`｜`GET /clauses/{clause_revision_id}/spans`｜`GET /clauses/{clause_revision_id}/meta` |
| **纠错补丁** | 3 | `GET/POST /clauses/patches`｜`DELETE /clauses/patches/{patch_id}` |
| **收藏（条款 + 标准）** | 8 | `GET/POST /bookmarks`｜`DELETE /bookmarks/by-clause/{clause_key}`｜`DELETE /bookmarks/{bookmark_id}`｜`GET/POST /doc-bookmarks`｜`DELETE /doc-bookmarks/by-doc/{doc_id}`｜`DELETE /doc-bookmarks/{doc_bookmark_id}` |
| **收藏夹（单层）** | 7 | `GET/POST /bookmark-folders`｜`PUT/DELETE /bookmark-folders/{folder_id}`｜`POST /bookmark-folders/move-clause`｜`POST /bookmark-folders/move-doc`｜`GET /bookmark-folders/tree`（114 行） |
| **批注 + 项目** | 7 | `GET/POST /annotations`｜`DELETE /annotations/{annotation_id}`｜`GET/POST /projects`｜`POST /projects/{project_id}/clauses`｜`DELETE /projects/{project_id}/clauses/{clause_revision_id}` |
| **文档** | 12 | `GET /documents`｜`GET /documents/categories`｜`POST /documents/batch-delete`｜`GET /documents/{doc_id}/file`｜`/tree`（255 行）｜`/versions`｜`/clauses`｜`/clauses-by-prefix`｜`/assets/{fname}`｜`/figure/{fig_no}`（152 行）｜`/formula/{fno}`｜`/table-image/{page_no}/{tbl_idx}` |
| **Office 往返** | 4 | `POST /clauses/{clause_revision_id}/office-edit`｜`GET /clauses/office-edit/poll`｜`POST /clauses/office-edit/commit`｜`DELETE /clauses/office-edit/{session_id}` |
| **合规** | 3 | `POST/GET /compliance/policies`｜`POST /compliance/gap-analysis` |
| **对比 / 影响面** | 2 | `POST /compare`｜`POST /documents/impact` |
| **导出** | 2 | `POST /export/citations`｜`GET /export/download` |
| **别名 / 数据质量** | 2 | `POST /aliases/extract`｜`GET /data/quality-issues` |
| **补丁迁移 / 视觉 / 反向溯源** | 3 | `POST /documents/{old_doc_id}/migrate-patches`｜`POST /vision/locate`｜`GET /clauses/{clause_revision_id}/backlinks` |
| **审计** | 3 | `GET /egress/audit`｜`GET /egress/audit/export`｜`GET /operation-log` |
| **快照** | 3 | `POST /snapshots`｜`GET /snapshots`｜`POST /snapshots/{snapshot_id}/restore` |
| **诊断** | 3 | `GET /health`｜`GET /diagnostics/health-board`｜`GET /diagnostics/debug-dumps` |

> 设置类（`/settings/api-config` 等 3 条）在 `routes_settings.py`，**不在本文件**。

### 2.2 可疑项 A：没有调用方的端点（11 条，全仓零调用）

判据：`plugin/**/*.{js,ts,tsx}`（排除 node_modules）与 `tests/*.py` 里都搜不到路径字面或等价的
模板串。⚠ 注意两个**假 ZERO 陷阱**（`docs/DEVELOPMENT-HISTORY.md` 的「方法论警告」已记过）：
host 会把引擎路径改写成同源前缀（`/ks/doc-image/<doc>/figure/<no>` → `/api/v1/documents/<doc>/figure/<no>`），
以及 `from __future__ import annotations` 会让 `/annotations` 看似在用 —— 所以下表是**路径级**核对，
不是词级。

| 端点 | plugin | tests | 备注 |
|---|---|---|---|
| `GET /api/v1/annotations` | 0 | 0 | 批注只在证据里随 `_ev_dict` 带出（`annotations_by_clause_keys`），CRUD 三条没人用 |
| `POST /api/v1/annotations` | 0 | 0 | 同上 |
| `DELETE /api/v1/annotations/{annotation_id}` | 0 | 0 | 同上 |
| `GET /api/v1/projects` | 0 | 0 | 项目清单四条全无人用 |
| `POST /api/v1/projects` | 0 | 0 | |
| `POST /api/v1/projects/{project_id}/clauses` | 0 | 0 | |
| `DELETE /api/v1/projects/{project_id}/clauses/{clause_revision_id}` | 0 | 0 | |
| `GET /api/v1/documents/{doc_id}/versions` | 0 | 0 | `docs/ENCYCLOPEDIA.md` 早已标 ZERO |
| `POST /api/v1/compare` | 0 | 0 | 同上，标 ZERO |
| `POST /api/v1/documents/impact` | 0 | 0（只有 `test_phase6.py:101` 的 docstring 提过） | 影响面分析，标 R49 |
| `DELETE /api/v1/doc-bookmarks/{doc_bookmark_id}` | 0（plugin 只用 `by-doc` 那条） | 0 | 与条款收藏 `DELETE /bookmarks/{id}` **不对称**：那条有调用方 |

另有 **20 条「只有测试、没有产品调用方」**（plugin 0 / tests ≥1）：`/data/quality-issues`、
`/documents/{id}/assets/{fname}`（`KsDocTextView.tsx:156` 明说不接线：*"asset-embed 等暂不接线"*）、
`/documents/{id}/clauses-by-prefix`、`/operation-log`、`/aliases/extract`、`/export/citations`、
`/chat/completions`、`/egress/audit/export`、`/documents/{old}/migrate-patches`、
`/clauses/{id}/office-edit` + `poll` + `commit` + `cancel`（4 条）、`/clauses/{id}/backlinks`、
`/vision/locate`、`/snapshots` + `list` + `restore`（3 条）、`/diagnostics/health-board`、
`/diagnostics/debug-dumps`。

**11 条零调用 + 20 条只有测试 = 31 条没有产品调用方**，剩 36 条是插件真在用的
（我逐条核过的 live 清单：`/health`、`/clauses/patches`×3、`/clauses/resolve`、`/documents`、
`/documents/categories`、`/documents/batch-delete`、`/documents/{id}/file|figure|formula|table-image|tree|clauses`、
`/bookmarks`×4、`/doc-bookmarks`×3、`/bookmark-folders`×7、`/compliance/policies`×2、
`/compliance/gap-analysis`、`/export/download`、`/ks/answer`、`/egress/audit`、
`/clauses/{id}/spans`、`/clauses/{id}/meta`；其中 `/spans` 与 `/meta` 的调用点在
`plugin/src/index.js` 与 `plugin/client/api.ts`，`figure|formula|table-image` 走
`plugin/src/docimage.js` 的同源代理 —— 这三类**字面搜 `/api/v1` 会假 ZERO**）。

**最扎眼的一条**：`POST /api/v1/chat/completions`（SSE，328 行，本文件最长的端点）**没有任何产品调用方**
—— 插件问的是 `POST /api/v1/ks/answer`（`plugin/client/api.ts` 的 `askKsAnswer`、`plugin/src/index.js`
的 `KS_ANSWER_PATH`）。`docs/research/ks-fixes/03-waiting-feedback.md:233` 已独立记过同一事实。
它被 11 个测试文件当接口测着，但生产路径上没人走它。

### 2.3 可疑项 B：两条端点做几乎一样的事

| 重复对 | 证据 | 差异 |
|---|---|---|
| `add_bookmark` / `add_doc_bookmark` | L1190–1199 与 L1223–1232 **逐行同构**，只差 `user_data.add_bookmark` / `add_doc_bookmark` | 错误码字面不同（`folder_not_found` 判定相同） |
| `del_bookmark_by_clause` / `del_doc_bookmark_by_doc` | L1202–1206 / L1235–1239 | 同上 |
| `del_bookmark` / `del_doc_bookmark` | L1209–1213 / L1242–1247 | 错误码 `bookmark_not_found` vs `doc_bookmark_not_found` |
| `move_clause_bookmark` / `move_doc_bookmark` | L1291–1316，函数体同构 | 只差 `user_data.move_bookmark_by_clause_key` / `move_doc_bookmark_by_doc` |
| `create_bookmark_folder` / `rename_bookmark_folder` | L1257–1278，除 `folder_id` 外同构 | 错误码映射三元式**抄了两遍** |
| `get_document_file` / `get_document_figure` / `get_document_formula` / `get_document_table_image` | 每个端点开头 10–15 行完全相同：`SELECT file_path FROM doc_meta WHERE doc_id=?` + `p.exists()` + `.endswith(".pdf")` + 两档 404 | **这条 SQL 在本文件出现 4 次**（AST 统计：`SELECT file_path FROM doc_meta WHERE doc_id=?` ×4） |
| `_frac_headers` 那三个头 | `/figure`（用 `_frac_headers`）、`/formula`（手写 f-string）、`/table-image`（手写 f-string）、`/assets`（手写 f-string） | 同一份 X-Frac-X0/W/H 拼装**写了 4 遍**，只有一处抽了函数 |
| `/documents/{doc_id}/clauses` 与 `/documents/{doc_id}/clauses-by-prefix` | L1544 / L1526 | 后者是前者的**前缀过滤子集**；前者返回全量再让前端筛，后者专供目录懒加载（且产品侧无人调用） |
| `/health` 与 `/diagnostics/health-board` | L339 / L2464 | 都报 `db ok + vector 三态`；看板多 7 个 `COUNT(*)` 与 6 引擎状态 |
| `doc_asset` / `export/download` / `get_document_file` | 三个"防路径穿越"实现各不相同：正则白名单 + `resolve()`+`parents` / `resolve()`+`parents` / 直接 `Path()`+后缀判定 | 同一安全意图三种写法 |
| `/clauses/{id}/meta` 与 `/clauses/resolve` | L2366 / L415 | 前者按 `clause_revision_id` 反查 `clause_key`+收藏态，后者按标准号+条款号定位；字段有重叠（`clause_key` `doc_id` `page_start` `standard_number` `title`） |

### 2.4 可疑项 C：返回结构不一致

| 形状 | 条数 | 例 |
|---|---|---|
| `{"code": 200, "data": …}` | 61 处 `return {"code": 200` | 绝大多数 |
| `{"code": 200, "status": "success", "data": …}` | 6 处 | `create_patch` `data_quality_issues` `get_patches` `remove_patch` `documents_batch_delete` `ks_answer_endpoint` |
| `{"code": 466, "status": "warning", …}` **而 HTTP 是 200** | 1 处 | `create_patch` 的 patch-guard warning 分支（L400–404）—— 业务码 466 与 HTTP 200 不同步，**全文件唯一**。前端必须同时判 HTTP 与 body.code |
| 裸 dict / 二进制 | `health()` 返回 `{"status","uptime_seconds","db_status","vector_engine","parser_worker"}`，**没有 `code` 字段**；另有 7 条返回 `FileResponse`/`Response`/`StreamingResponse`（`/file` `/figure` `/formula` `/table-image` `/assets` `/export/download` `/chat/completions`） | `/health` 是唯一不带信封的 JSON |
| `data` 里再包一层 | `doc_full_clauses` → `data:{doc_id, clauses:[…]}`；`clause_spans`/`clause_meta`/`doc_versions`/`ks_answer` 同理 | 多数只是 `data:[…]`，所以前端得逐端点记形状 |
| 额外顶层字段 | `"total"` 全文件只出现 **1 次**（`data_quality_issues`） | 分页/计数口径不统一 |

### 2.5 鉴权：除 `/health` 与 `OPTIONS` 还有没有免 token 的？

**没有。** 唯一放行点在 `auth_middleware`（L317–320）两条：

```python
if request.url.path == "/api/v1/health": return await call_next(request)
if request.method == "OPTIONS":        return await call_next(request)
```

要注意的三点（都不是漏洞，但都是行为事实）：
1. 判定是**精确字符串**：`/api/v1/health/`（多一个斜杠）**要 token**。
2. 放行对**所有路径**生效（不限 `/health`）：任何路径的 `OPTIONS` 都免 token —— 但 FastAPI 对
   不存在的路径仍返回 405/404，不会执行处理器。
3. **中间件顺序**：`add_middleware(CORS)` → `@app.middleware("http") auth` →
   `add_middleware(_HeavyGateMiddleware)`。Starlette 每次 `add_middleware` 都插到最外层，所以实际
   链路是 **重活闸门 → auth → CORS → 路由**。即：**先扣线程池令牌，再校验 token** ——
   未授权请求也会占用重活令牌（`is_heavy_path` 命中的路径）。不构成越权，但反了常理。
4. `routes_*.register(app, _json_error)` 的 8 个模块注册在 `create_app` 尾部（L3240–3271），
   全部走同一条 auth 中间件 —— **没有第二条免 token 的路由族**。

---

## 三、超长函数与重复

### 3.1 超过 100 行的函数（AST 实测，含闭包内）

| 函数 | 行数 | 起止 | 干什么 |
|---|---|---|---|
| `create_app` 本身 | **2,997** | 278–3274 | 建 app、注册中间件、67 个路由、35 个辅助函数、8 个模块接线 |
| `_content_html` | **518** | 2623–3140 | 条款正文 → 展示 HTML（见 §3.2） |
| `chat_completions` | **328** | 1765–2092 | SSE 问答：查询理解 → 检索 → 富化 → LLM 流式 → 追问解析 → 尾部标注 → 核验 → 落 dump。内含 171 行的 `event_stream` |
| `document_tree` | **255** | 928–1182 | 目录树：PDF 书签 → 法规「第X章」→ 术语表 → 库内 N.M 小节 + PDF 文本层猜章标题（4 条策略级联） |
| `get_document_figure` | **152** | 565–716 | 图：MinerU chart 块 → 文字层锚定 → middle 裁剪图 → OCR 题注锚定，四条兜底 + 坐标换算 |
| `bookmark_folders_tree` | **114** | 1319–1432 | 收藏夹树：夹 → 文档 → 条款三段平铺，带分类路径缓存 |

（次一级：`doc_full_clauses` 72 / `_inject_formulas` 70 / `get_document_formula` 61 /
`get_document_table_image` 59 / `resolve_clause` 58 / `create_patch` 51 / `build_folder` 55 /
`_write_debug_dump` 51。）

### 3.2 `_content_html` 确认：**518 行**（L2623–3140，AST `end_lineno` 实测；不是 520 也不是 438）

内部**至少做了 9 件事**，全是「同一条输出串上的先后变换」，且**顺序本身是语义**
（源码 L3129–3140 的注释明说嵌套执行序有意义）：

1. **两种入口判定**：`md` 里有 `<p[ >]` → 视为编辑保存的完整富文本，直接注入后就返回（L2782–2784）；否则走"正文转段落 + 表格"的旧路径。
2. **图题注入**（`_inject_figs` + `_fig_sub`）：按 `_FIG_CAPTION_SEG` 把「图N 标题」换成 `<img class="fig-embed" data-fig=…>`；**并且**先用 `middle_geo.figures()` 排除"版面里已有的图号"，防引用句被误注入。
3. **公式注入**（`_inject_formulas` + `_norm_eq`/`_pick_fno`/`_f_sub`）：把独立公式行用 LaTeX 归一化相似度（阈值 0.35）匹配到 `middle.json` 的 `interline_equation` 块，产出 `<span class="katex-formula" data-fno data-clause data-tex>`；找不到就**保留原文**。
4. **页界还原（B3）**：解 `page_breaks`（`[[行号, 页码], …]` run-start 编码），页号切换处插 `<div class="page-break" data-page>`；行数与页映射对不上就**放弃分隔**（宁可不分不可错页）。
5. **表格归位**：把 `content_markdown` 里的 `<table>` 按 `table_pages`（span 页号）插回原文页位，替代"全部堆在末尾"；前提是 `<table>` 数与页号数相等且正文只由表格构成。
6. **带图表格整表转图**：`middle_geo.image_hit_tables(page)` 命中的表 → `<img class="table-embed" data-page data-tbl>`（走 `/table-image`）。
7. **插图/曲线图按页位归位**：`figure_html` 里的 `asset-embed` 按 `image_bbox_by_path` 反查物理页，页推进时插入；再加 `middle_geo.assets()` 补"孤儿图"（`asset_done` 跨条款去重、按 `page_start/page_end` 归属），以及 `figures()` 里 `kind=="chart"` 的曲线图（`chart_done` 去重）。
8. **正文一串文本修复**：`strip_embedded_table_text` → `normalize_math_symbols` → `reflow_sqrt_formulas(glue_spaced_formulas())` → `normalize_area_subscript` → 两条 OCR 空格正则 → `weave_meaning_marks` → `html_unescape` → 只白名单保留 `<sup>/<sub>`（其余 `< > &` 转义）→ 表题行加 `class="tbl-cap"`。
9. **双栏版面判定与两列渲染**：`row_boxes` x0 排序找最大间隙（>40 且两侧各 ≥2 行）→ 左右栏 `<div class="cols">`；有表格的条款**不判双栏**（否则丢表）。
10. **段落合并**：句子尾标点 + 「其中：/式中：」+ 公式段三类相邻段合并（`_ptext`/`_p_lead`/`_p_formula`/`_p_tail`/`_p_join`/`_mrg_col` 六个内部函数，`_mrg_col` 与主循环**是同一段合并逻辑写了两遍**）。
11. **收尾三件套**：`pua_bond_dash_html`（PUA 键横线）→ `sup_unit_exponents_html`（单位负指数上标）→ `space_clause_numbers_html`（段首编号补空格）→ 最外层 `katex_sym_html`（`式中` 的 hat/bar → KaTeX span）。

**风险**：这 11 件事里，只有 4 件（图题、公式、页界、表格归位）有端点级用例；双栏判定、
孤儿图归属、段落合并、三件套顺序**没有任何针对性用例**，且整段逻辑**不可 import**。

### 3.3 还有一处和 `_answer_confidence` 同型的**活分叉**

`_expand_title_clauses` 有两份实现：

| | `api/server.py:2525`（闭包内） | `llm/ks_answer.py:1167`（模块级，可单测） |
|---|---|---|
| 长度阈值 | 硬编码 `len(...) < 80` | 常量 `TITLE_CLAUSE_MAXLEN = 80` |
| 子条款查询 | **无 try/except**，DB 异常直接冒到端点 | 包了 `try/except: subs = []` |
| 注释自述 | L2538「与 ks_answer._expand_title_clauses 同步放宽」 | L1164「与 server._expand_title_clauses 同语义」 |

**唯一的"测试"**（`tests/test_appendix_split.py:218`）在自己文件里**重新写了一遍正则**
`re.compile(r'[0-9A-Z]+(?:[.][0-9A-Z]+)*')`，**两份实现一个字都不执行**。改任何一份都不会红。
这正是 `_answer_confidence` 分叉的同款形状 —— 区别只是这次还没人写"两份一致"的用例。

### 3.4 SQL 拼字符串

AST 统计：本文件含 SQL 的字符串字面量 **44 条**，其中 **f-string 形态 7 条**：

| 行 | 语句 | 拼进去的是什么 | 判读 |
|---|---|---|---|
| 1574 | `…FROM source_span WHERE clause_revision_id IN ({ph})…` | `ph = ",".join("?"*n)` | 安全（占位符） |
| 1584 | `…bbox_json IS NOT NULL… IN ({ph})` | 同上 | 安全 |
| 1745 | `SELECT … WHERE cr.clause_revision_id IN ({ph})` | 同上 | 安全 |
| 1891 | `…FROM clause_patch WHERE clause_revision_id IN ({_ph})…` | 同上 | 安全 |
| 3153 | `…FROM clause_revision WHERE clause_revision_id IN ({ph})` | 同上 | 安全 |
| **1708** | `f"SELECT content_text FROM clause_revision{cond} ORDER BY rowid LIMIT ? OFFSET ?"` | `cond = " WHERE doc_id = ? " if doc_id else ""` | **安全但脆**：`cond` 是两选一的字面量，不含用户输入；一旦有人改成拼 `doc_id` 就是注入 |
| **2198** | `f"SELECT COUNT(*) FROM {table}"` | 表名 `table` | **安全但脆**：唯一调用点传字面量 `"clause_vec"`（`_safe_count(conn, "clause_vec")`），但函数签名接受任意字符串 —— 这是全文件唯一把**标识符**拼进 SQL 的地方 |

**结论：现在没有可利用的注入点**（4 条用户输入路径全部走 `?` 占位）。维护性风险集中在
`_safe_count` —— 它把"表名可拼接"这件事做成了公共 API。

### 3.5 同一查询写了多遍（AST 精确重复）

| SQL | 次数 | 位置 |
|---|---|---|
| `SELECT file_path FROM doc_meta WHERE doc_id=?` | **4** | `get_document_file`(554) `get_document_figure`(575) `get_document_formula`(732) `get_document_table_image`(794) |
| `SELECT 1` | 2 | `health`(343) `health_board`(2481) |
| `SELECT COUNT(*) FROM alias_store` | 2 | `aliases_extract`(1718) `health_board`(2503) |

近似重复（不是完全同串，但语义同）：`SELECT * FROM clause_revision WHERE doc_id=? AND content_type='normal'` 在
`document_tree`(988) 与 `clauses_by_prefix`(1535) 各写一遍；
`SELECT clause_revision_id FROM clause_revision WHERE doc_id=? AND clause_number LIKE ?` 在
`_expand_title_clauses`(2542) 与 `ks_answer.py:1187` 各写一遍。

---

## 四、错误处理一致性

### 4.1 `_json_error` 用了多少次 / 有没有绕过

- **73 处调用**（`Select-String -Pattern "_json_error\("` 计数），其中 **72 处是 `return _json_error(...)`**，
  另 1 处是定义本身。
- **没有端点直接 `raise`**（`Select-String -Pattern "^\s+raise "` → **0**）—— 所有错误都靠返回值，风格统一。
- **绕过它直接 `return {...}` 的**：**1 处**，就是 `create_patch` 的 warning 分支
  `return {"code": 466, "status": "warning", "data": {...}, "message": ...}`（L400–404）。它是全文件
  唯一"手工构造错误响应"的地方，代价是 HTTP 状态码（200）与业务码（466）不同步。
- **错误码词汇有三套并存**（AST 提取 53 处字面量码，另有 19 处传 `e.code`）：
  - snake_case（主流 27 个：`doc_not_found` ×7、`file_not_found` ×8、`clause_not_found` ×4 …）
  - 大写下划线（**4 处**：`DOC-3001` ×3、`DOC-3002` ×1 —— 都在 `documents_batch_delete`）
  - `KnowledgeStationError.code` 原样透传（`e.code`），具体取值由各 repo 决定，**本文件不知道词汇表**
- 信封字段名也反直觉：`_json_error(status, code, message)` 的第 2 个参数 **名叫 `code`，却写进响应的
  `error` 字段**，而响应的 `code` 字段装的是 **HTTP 状态码**。所以 `{"code":422,"error":"DOC-3001"}`
  与 `{"code":466}` 里的两个 `code` 根本不是一个东西。

### 4.2 `except Exception: pass` / 吞错清单（逐个）

`pass` 行共 **15 处，全部在 except 块里**（`Select-String -Pattern "^\s+pass\s*$"` → 15）。
`except Exception` 共 **40 处**，`except Exception:`（裸）**0 处**（全都带 `as e` 或注释）。

**真·吞掉（什么都不做、不记日志）**：

| 行 | 位置 | 吞掉了什么 | 后果 |
|---|---|---|---|
| 76 | `bound_threadpool_once` | 拿不到 limiter | 请求照跑（有注释说明，可接受） |
| 204 / 209 | `warm_retrieval_stack` | 预热失败 | 首次提问变慢，不报错 |
| 611 | `get_document_figure` 的 chart 定位 | 深度产物解析异常 | 静默走兜底 |
| **1166** | `document_tree` 猜章标题 | PDF 文本层异常 | **目录少章标题，无日志** |
| 1657 | `doc_asset` 的 X-Frac 头 | bbox 反查失败 | 图能出但位置还原失效 |
| **1993 / 2025** | `event_stream` 追问 JSON 解析 | `json.loads` 失败 | 按正文流输出（有兜底语义） |
| **2952** | `_content_html` 孤儿图补齐 | middle 解析失败 | 少图 |
| 3296 / 3304 / 3313 / 3325 / 3335 / 3340 | `run()` 的启动/关停 | 写队列、法规刷新、巡检线程、session 文件、两次 stop | 启动继续（有注释说明，可接受） |

**改值型吞错（比 pass 更值得注意：把异常变成"正常的空数据"）**：

| 行 | 表达式 | 为什么危险 |
|---|---|---|
| **1867** | `except Exception: _bm_keys, _ann_cache = set(), {}` | 收藏/批注富化整块消失 —— 回答照出，但"这条你收藏过/有批注"全丢，**无日志** |
| **1896** | `except Exception: _patch_cache = {}` | 补丁记录整块丢失（`user_confirmed` 因此恒 False，置信度被静默降级） |
| 2199 | `_safe_count` → `return 0` | 健康看板显示 0 条向量，看不出是"没扩展"还是"真空" |
| 3157 | `_full_evidence` → `return ev_dicts` | 核验退化成截断文本（注释说明了这是有意降级，但没日志） |
| 2460 | `impact_analysis` 把**任意异常**包成 `404 impact_error` | **真崩溃伪装成"没找到"**，HTTP 语义被改写 |
| 2143 | `_write_debug_dump` 失败 → `logger.warning` | 审计写不进去只留一行 warning，**不影响响应** |

### 4.3 HTTP 状态码与业务 `code` 不一致

1. **`create_patch` 的 466 / 200**（唯一，见 §4.1）。
2. **缺字段的三种不同处理**（同一类输入错误，三种响应）：
   - 显式校验 → **422**：`documents_batch_delete`（`doc_ids` 非空、`confirm is not True`）、
     `migrate_patches_api`（`missing_target`）、`clause_spans` 之外的分支、`ks_answer_endpoint`（`query_required`）
   - 直接 `body["key"]` → **KeyError → 500**：`add_bookmark` `add_doc_bookmark` `move_clause_bookmark`
     `move_doc_bookmark` `add_annotation` `create_project` `project_add_clause` `import_policy`
     `run_gap` `compare_docs_endpoint` `office_edit_commit` `impact_analysis` —— **12 处**
     （`Select-String -Pattern 'body\["'` 实测 12 行）。`compare` 与 `impact` 的 docstring 还**明知故犯**地写着
     "缺字段仍是 KeyError → 500，与改前一致"。
   - 干脆不校验、继续跑：`chat_completions` 用 `body.get("query", "")`，空 query 也往下走并起一次
     云调用；而 `ks_answer_endpoint` 对同样的空 query 直接 422。
3. **破坏性操作的保护不对称**：`DELETE /documents/batch-delete` 要求 `confirm: true`（不给就 422
   `DOC-3002`）；而 `POST /snapshots/{snapshot_id}/restore` **会覆盖整个库**却**没有任何确认参数**。
4. **两处 `try/except` 是死代码**：`documents_batch_delete` 的 `try: body = body or {} except: return 422`
   （L911–914）与 `office_edit_start` 的 `try: body = body or {} …`（L2270–2274）—— 此时 body 已由
   FastAPI 解析完，`body or {}` 不可能抛异常，所以"坏 JSON → 422"这条路径**永远走不到**（坏 JSON 在
   进函数前就被 FastAPI 拦了）。两处注释/文档暗示的错误契约与代码不符。

---

## 五、调试 / 转储端点

**性质上属于「调试/转储」的，本文件里有 6 个函数 + 3 条端点**（`Select-String -Pattern "debug|dump"`
在 `src/core/api/*.py` 里只命中 `server.py`；其它 7 个路由文件**没有** debug 端点）：

| 名 | 类型 | 写/读什么 | 产品调用方 |
|---|---|---|---|
| `_write_debug_dump` | 函数（L2094–2144） | 写 `debug_dump`：`query`、`retrieval_result`（命中的标准号+条款号）、`prompt`（`history[-4:]`）、`llm_output`（答案前 **4000 字**）、`verification_result`、`logs`（trace + 置信度 + clarify） | SSE 路径每次提问默认写（`dump_enabled = bool(body.get("dump", True))`） |
| `_write_ks_answer_dump` | 函数（L2146–2192） | 同一张表，`trigger_type='user_export'`，装 `/ks/answer` 的三段式答案 + `_meta` | 每次 `/ks/answer` 都写（无开关） |
| `GET /api/v1/diagnostics/debug-dumps` | 端点（L2512–2523） | **读** `dump_id, trigger_type, query, created_at, llm_output, logs` 最近 N 条 | **0（产品无人调用）** |
| `GET /api/v1/egress/audit` | 端点（L2235–2240） | 按 `trigger_type ∈ ("user_export","egress")` 聚合 | plugin `api.ts:2585` / `client.js:1516`（**在用**） |
| `GET /api/v1/egress/audit/export` | 端点（L2242–2250） | 把全部外发记录写进 `exports/` 再走 `/export/download` | **0** |
| `GET /api/v1/operation-log` | 端点（L1679–1691） | `operation_log` ∪ `event_log`（排除 `write_queue%`）时间线 | **0** |
| `POST /api/v1/vision/locate` | 端点（L2408–2420） | 收客户端给的**服务器本地路径** `image_path`，OCR 后返回条款定位 | **0** |
| `_safe_count` | 函数（L2195–2200） | 不写；只读统计 | （看板） |

### 5.1 生产里该不该存在 / 有没有泄漏

**结论：有泄漏面，但都在"token 即全权"这个既有前提下；真正该改的是两条。**

1. **`GET /diagnostics/debug-dumps` 是"历史问答全量出口"，且产品侧没有任何界面在用它。**
   返回字段里 `llm_output` 是完整答案（截 4000 字）、`logs` 里的 `trace` 含 `query`/`slots`/
   `raw_results`（命中了哪些标准号+条款号）、`prompt` 含最近 4 轮 `history`（原样存用户过去的问话）。
   **它有端点、有数据、没有消费者** —— 这正是"该删或该收进本地调试开关"的形状。
   token 只保证"本机 + 拿到 token 的进程"；而 token 写在 `<data_dir>/engine.session.json`
   （`run()` 的 `session.write_text({... "token": token ...})`），本机任何能读该文件的程序都能读光历史问答。
2. **`dump=false` 可以让调用方自己关掉这条链路的审计记录。**
   `egress_audit.py` 模块头自己写着：*"现阶段 LLM 问答链路已由 server.py `_write_debug_dump` 全量落库"*；
   而 `_AUDIT_TRIGGER_TYPES = ("user_export", "egress")` —— SSE 路径写的就是 `user_export`。
   `deepseek_client.py` **全文没有 `record_egress`/`audit` 字样**（实测 0 命中），所以 **`dump=false`
   等于这次云端 LLM 调用在审计面板与导出里彻底不可见**。对外承诺是"每次云调用的完整 payload 落库"
   （`ENCYCLOPEDIA §1.5` 承诺 4 / `INTRODUCTION §三.10`）—— 这条与"调用方可自关"直接冲突。
   `/ks/answer` 侧没这个开关（`_write_ks_answer_dump` 无条件调用），**两条链的审计强度不一样**。
3. `POST /vision/locate` 接受任意本地路径并 OCR —— 语义上"你把路径给我，我还你文件里的字"。
   不是路径穿越（它没限制在数据目录内），但它是**唯一一条能把引擎可读文件内容变成返回值**的端点。
   产品侧 0 调用方。要么删，要么把 `image_path` 限制在 `data_dir` 内。
4. `_write_debug_dump` 的痕迹泄漏面已被单独治理过：`debug_dump_retention.py` 按类型各自裁剪
   （审计 1000 / 提问证据 5000），源码注释 L2133–2137 记了"全表裁 1000 会把提问证据挤掉"那次真缺陷。
5. 存储是明文 SQLite（`debug_dump`），没有加密或脱敏字段。

---

## 六、我没搞清楚的

1. **「107 条端点」的出处没查到。** 我实测 server.py 是 67 条装饰器 / 58 条唯一路径，全库 176 条；
   127 那个数是"只扫 6 个模块"时的旧数。107 既不是 67、也不是 127，**可能在任务书写下之后
   有一次没进仓的统计**，也可能是把 `plugin/` 的 `/ks/*` 路由算进来了（插件侧 49 条，67+49=116，
   也对不上）。**未确认，不猜。**
2. **`POST /chat/completions` 是否该删。** 产品走 `/ks/answer`，但 SSE 那条被 11 个测试文件当契约测着
   （`test_contract.py:11` 冻结事件顺序）。它是"已建的备用通路"还是"该拆的死代码"，是产品决定，
   不是我能从代码判的。**我读到的证据只到"当前无产品调用方"。**
3. **11 条零调用端点是否真的全死。** 我只静态搜了 `plugin/` 与 `tests/`。没搜：DSH 宿主侧的
   overlay/其它仓外插件、`eval/` 与 `scripts/` 里的临时脚本（那里面确实有直接打 HTTP 的脚本，
   例如 `scripts/measure-endpoint-blocking.py` 会打 `/diagnostics/health-board` 与 `/snapshots`）。
   **所以"零调用"的准确说法是"产品与测试都没有调用方"，不是"全仓零引用"。**
4. **`_content_html` 的双栏分支与孤儿图归属没验过真机效果**（只读代码）。它的正确性依赖
   `middle_geo` 的三个方法（`figures()` `assets()` `image_hit_tables()`）的返回语义，那几个文件
   **本次未读**。
5. **`_ev_dict` 的 `type_confidence = max(c.type_confidence or 0, 0.9) if user_confirmed`**
   （L3211）—— 我确认了这行存在，但**没查 `user_confirmed` 之外还有哪些路径会改置信度**，
   也没验这条会与 `ks_answer.answer_confidence` 的判据互相印证到什么程度。**未读关联模块。**
6. **`_HeavyGateMiddleware` 的 20 条前缀表（`HEAVY_PREFIXES`）与 67 条端点的对应关系没逐条核**
   —— 只确认了它跑在 auth 之前（§2.5 第 3 点）。
7. **`routes_*.register(app, _json_error)` 那 8 个模块的 109 条端点**（176−67）是否与本文件的
   信封/错误码风格一致，**本次完全未读** —— 如果那边各有一套包装，§2.4/§4.1 的"不一致"会更大。

---

### 附：本次用到的可复现命令

```powershell
# 行数（真值 vs 不计空行）
.venv\Scripts\python.exe -c "print(len(open('src/core/api/server.py',encoding='utf-8').readlines()))"   # 3341
(Get-Content src/core/api/server.py | Measure-Object -Line).Lines                                        # 3113（不计空行）
# 端点底数
Select-String -Path src/core/api/*.py -Pattern '@router\.(get|post|put|delete|patch|api_route)|@app\.(get|post|put|delete|patch)'
# 错误包装 / 吞错 / 死代码
Select-String -Path src/core/api/server.py -Pattern "_json_error\("    # 73
Select-String -Path src/core/api/server.py -Pattern "except Exception"  # 40
Select-String -Path src/core/api/server.py -Pattern "^\s+pass\s*$"      # 15（全在 except）
Select-String -Path src/core/api/server.py -Pattern 'body\["'            # 12 处直接索引
# 函数边界与嵌套深度：ast.walk + end_lineno（本次用 .venv 的 python 跑，未写任何文件）
```
