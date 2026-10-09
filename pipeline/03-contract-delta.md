# 契约增量 03 · 更新模块数据契约落地

> 日期：2026-08-24 ｜ 依据：pipeline/02-architecture-contract.md §2 数据契约 ｜ 红线流程：contract.md → test_contract.py → schema.sql（本次三件套同步落地）

## 1. 变更内容

schema.sql 追加两张新表（序号延续既有注释风格，落在索引区之前）：

| 序号 | 表 | 主键 | 关键约束 |
|---|---|---|---|
| 29 | `update_check_batch` 更新巡检批次表 | `batch_id TEXT PRIMARY KEY`（ULID 前缀 `upd_`，DDL 注释声明） | `trigger_type` CHECK 二枚举 manual/scheduled；`status` 缺省 pending，CHECK 五枚举 pending/running/paused/done/failed |
| 30 | `update_change_event` 标准变更事件表 | `change_id TEXT PRIMARY KEY`（ULID 前缀 `chg_`，DDL 注释声明） | `change_type` NOT NULL CHECK 五枚举 new_version/superseded/withdrawn/not_found/no_change；`current_legal_status` 可空 + 四枚举 effective/upcoming/superseded/withdrawn；`doc_id` 可空（公告命中但库内无此文档）；`batch_id` NOT NULL 外键 → update_check_batch ON DELETE CASCADE |

索引区追加两条（随表同生共死）：

```sql
CREATE INDEX IF NOT EXISTS idx_change_batch ON update_change_event(batch_id, change_type);
CREATE INDEX IF NOT EXISTS idx_change_doc ON update_change_event(doc_id);
```

tests/test_contract.py 追加 6 个契约用例：两表存在性、ULID 主键风格（TEXT PK + DDL 注释）、批次 trigger_type/status 枚举、事件 change_type 五枚举、legal_status 四枚举与 doc_id 双路径（NULL/回填）、batch_id 外键拒绝孤儿写入 + 删批次级联删事件。

## 2. 影响面

- **改动文件仅 3 个**：`src/core/storage/schema.sql`（+30 行 DDL/注释）、`tests/test_contract.py`（+6 用例）、本文档。其余一概未碰（server.py / App.tsx / sqlite_db.py 均原样——`init_schema` 走 executescript 全量执行，无需注册变更）。
- **存量零侵入**：全部 `IF NOT EXISTS` 幂等；不动既有 1~28 号表、FTS/VEC 虚拟表、SSE 事件与 API 契约。
- **解锁后续实现**：`src/core/update/change_repo.py`、`inspector.py` 的读写落点已就位；巡检写路径仍走 `write_queue`（operation_type=`'update_check'`），审计走 `event_log`（event_type=`'update/change_detected'`），本增量不引入新写通道。
- **复用项确认**：`doc_meta.doc_type` 无 CHECK → `'announcement'` 直接可用；`watch_list` 直接服务 F-14。
- **测试基线**：test_contract.py 由 7 → 13 个用例全绿；全量套件不低于基线 173 passed + 2 skipped。

## 3. 回滚方式

外键存在方向依赖，必须**先子后父**顺序执行：

```sql
DROP TABLE IF EXISTS update_change_event;   -- 子表先删，其两条 idx_change_* 索引随之消失
DROP TABLE IF EXISTS update_check_batch;    -- 父表后删
```

随后还原 `tests/test_contract.py` 的「更新模块数据契约」6 个用例区块即可回到本增量前状态；schema.sql 中删除 29/30 号表注释块与索引区两行等价于上述 DROP 的静态回滚。回滚不影响任何存量表数据。

## 4. 验证记录

- `.venv\Scripts\python.exe -m pytest tests/test_contract.py -q` → **13 passed**（7 存量 + 6 新增）
- 全量 `.venv\Scripts\python.exe -m pytest -q` → **189 passed, 2 skipped**，高于基线 173 passed + 2 skipped

---

# 契约增量 · 阶段六批次2 · 批量导入批次表（巡检侧最小版）

> 日期：2026-08-24 ｜ 依据：pipeline/06-bulk-ingest-design.md §4「落点与契约增量」｜ 红线流程：本文档 → test_contract.py → schema.sql

## 5. 变更内容

schema.sql 追加第 31 号表 `bulk_import_batch`（本批只建巡检侧需要的最小版）：

| 列 | 类型 | 约束/默认 |
|---|---|---|
| batch_id | TEXT PRIMARY KEY | ULID 前缀 `bul_`（DDL 注释声明） |
| batch_kind | TEXT | CHECK 二枚举 inspect/bulk_ingest（bulk_ingest 为批量导入编排预留） |
| trigger_type | TEXT | CHECK 二枚举 manual/scheduled |
| status | TEXT | DEFAULT 'pending'，CHECK 五枚举 pending/running/paused/done/failed |
| total/checked/red_count/yellow_count/green_count/gray_count | INTEGER | DEFAULT 0 |
| tier | TEXT | DEFAULT 'tier1'，CHECK 二枚举 tier0/tier1 |
| checkpoint_json | TEXT | 可空；断点续扫 {queue,done,captcha_pending,pause_reason} |
| started_at / finished_at / created_at | TEXT | 同本体风格（created_at DEFAULT datetime('now')） |

无新索引（最小版原则）；不动既有 1~30 号表与索引区。

## 6. 与 update_check_batch 的镜像锚行约定（inspector 落地语义）

- 巡检编排器（inspector.py）以 `bulk_import_batch(batch_kind='inspect')` 行为控制面记录
  （tier 分层 + checkpoint_json 断点 + 暂停原因）；
- 因 update_change_event.batch_id 外键冻结指向 update_check_batch（29 号表），巡检批次创建时
  在同一写事务内以**同值 batch_id** 在 update_check_batch 插入镜像锚行并同步进度/状态，
  保证 `update_change_event.batch_id == bul_ 批次 id` 直查可用、外键零改动；
- bulk_ingest 类批次不建锚行（其事件落点由后续批量导入批次定义）。

## 7. 影响面与回滚

- 改动文件仅 3 个：schema.sql（+20 行 DDL）、tests/test_contract.py（+3 用例）、本文档。
- 回滚：`DROP TABLE IF EXISTS bulk_import_batch;`（该表无子表引用，可独立删除），随后移除
  test_contract.py 的「批量导入批次表契约」3 个用例区块即回到本增量前状态。
- 测试基线：test_contract.py 由 13 → 16 个用例全绿；全量不低于 214 passed + 2 skipped。

## 8. 验证记录（批次2收口）

- `.venv\Scripts\python.exe -m pytest tests/test_contract.py -q` → **16 passed**（13 存量 + 3 新增）
- 全量 `.venv\Scripts\python.exe -m pytest -q` → **247 passed, 2 skipped**
  （批次2前基线 214 passed + 2 skipped；增量 = 契约 +3 与
  `tests/test_update_inspector.py` +30，只涨不跌达标）

---

# 契约增量 · 阶段六批次3 · 找标子模块（discover）

> 2026-08-24 ｜ 零 DDL、零既有端点/表改动：新增 `src/core/update/ccs_seed.json`（CCS 二级种子树，24 大类 × 3~8 子类，source=seed 待权威本体入库扩充）与 `src/core/update/discover.py`（classify 口语→CCS 路径/一轮追问 ≤3 问、search 经 transport 注入查网络渠道 drill_level≤3 否则 UPD-3002、download_later 待下载清单存 app_config 键 `'discover.download_later'`）；网络查询 mock 表驱动落 `tests/fixtures/discover_web.json`。验证：`tests/test_update_discover.py` 11 passed；全量 **258 passed + 2 skipped**（批次3前基线 247+2，只涨不跌）。

---

# 契约增量 · 排版还原批次1 · clause_revision.page_breaks 页界列 + source_span 行级化

> 2026-09-01 ｜ 依据：用户排版需求「原文哪里换页我就哪里换页，哪里换行我就哪里换行，且不强加回车」 ｜ 红线流程：本文档 → test_contract.py → schema.sql（三件套同步落地）

## 变更内容

**① clause_revision 增量列（B3 页界入库）**：

| 列 | 类型 | 语义 |
|---|---|---|
| `page_breaks` | TEXT（JSON，可空） | 页界 run-start 编码 `[[行号, PDF页码], ...]`；行号 = content_text 内 0-based 行索引，首个条目恒为 `[0, 首行所在页]`。语义：行号 i 起（含）到下一页界前，正文行位于该 PDF 物理页。NULL = 存量未采集，渲染层跳过分隔。 |

- 纯增量列、**无回填**（快照不可变红线：绝不给存量编造页界）；迁移 `clause_repo.ensure_page_breaks_column()`（PRAGMA 缺列才 ALTER，幂等），随 `_ensure_content_hash_once()` 与 `migrate_patches()` 触发。
- 渲染面：server `_content_html` 按 run-start 展开每行页号，页号切换处在段间插 `<div class="page-break" data-page="N">`（CSS 虚线 + 页码角标），不增删任何正文行（「证据卡片文字不连贯」约束）。
- 采集面：pipeline `SplitClause.rows`（(行文本, 0-based 页号, 行bbox) 行级权威序列）在 build 阶段产码；家具剥离 / [:4000] 截断 / 三件套清洗全部在 rows 上重排或行内改写（不改行数），保证 content_text 行号 ↔ 页界编码不漂移。

**② source_span 行级化（B5 行级 bbox 全量入库）**：零 DDL 变更——`span_type TEXT` 自由语义 + `sort_order` 已可承载。行为变化：文本块证据 span 从「块级 bbox × 每条款至多 8 条（旧 `[:8]` 封顶，第 9 块起高亮全灭）」改为「行级 bbox × 全量（每折行行一条）」；表格块保留块级；行框整体缺失（旧 middle.json 无 line.bbox / 编号合并失配）时回退块级（宁粗不高灭）。坐标契约不变（middle.json bbox 直存，前端 convertToViewportPoint 直消费）。

## 影响面与回滚

- 改动文件：`schema.sql`（1 列 DDL）、`tests/test_contract.py`（1 用例）、本文档；管线 `pipeline.py`、存储 `clause_repo.py`、渲染 `server.py` + `styles.css` 为实现落点。
- 存量零影响：page_breaks NULL → 渲染零行为变化；source_span 存量行不动（span_calibration 按 rowid 修复逻辑照旧）。
- 回滚：`ALTER TABLE clause_revision DROP COLUMN page_breaks`（SQLite 3.35+）等价静态回滚；渲染/采集代码随 git 还原。测试基线只涨不跌（test_contract 16 → 17）。

---

# 契约增量 · 排版还原批次1补充 · clause_revision.figure_html 插图通道列

> 2026-09-01 ｜ 依据：C2 插图入库（MinerU image 块此前被管线整体跳过，深度解析文档插图在全文视图消失） ｜ 红线流程：本文档 → test_contract.py → schema.sql（三件套同步落地）

## 变更内容

| 列 | 类型 | 语义 |
|---|---|---|
| `figure_html` | TEXT（可空） | build 阶段组装的插图占位通道：`<p class="fig-strip"><img class="asset-embed" data-asset="<sha256>.jpg" alt="…"/></p>` 串。独立于 content_markdown——md 路径判定（`<p[ >]` 即视为编辑保存片段）不受插图标记干扰，页界分隔逻辑保持完整。 |

- 纯增量列、**无回填**（快照不可变）；迁移 `clause_repo.ensure_figure_html_column()` 幂等，随 `_ensure_content_hash_once()` 触发。
- 采集面：pipeline `load_middle_items` 新增 image 分支（image_body.image_path + image_caption 题注 → MidItem kind="image"）；split 按「图N 题注引用优先 → 物理就近 → 独立"图"条款」绑定；build 组装 figure_html（图名白名单 `^[0-9a-f]{64}\.(jpg|jpeg|png)$` 与 /assets 端点同款正则，不合规不渲染）。
- 渲染面：server `_content_html` 两条返回路径（md 片段路径 / 正文段落路径）末尾追加 figure_html；前端 `img.asset-embed[data-asset]:not([src])` 由 C2 effect 经 `/api/v1/documents/{doc_id}/assets/{fname}`（C1）带 token 拉 blob 填 src，失败隐藏。
- 插图不产 source_span（高亮/跳页只对文本与表格）。

## 影响面与回滚

- 改动文件：`schema.sql`（1 列 DDL）、`tests/test_contract.py`（1 用例）、本文档；实现落点 `pipeline.py` / `clause_repo.py` / `server.py` / `App.tsx` / `styles.css` / `figure_locator.py`（C3 兜底另见代码注释）。
- 存量零影响：figure_html NULL → 渲染零行为变化。
- 回滚：`ALTER TABLE clause_revision DROP COLUMN figure_html` 等价静态回滚；测试基线只涨不跌（test_contract 17 → 18）。

---

# 契约增量 · 公告发现 · announcement_observed 已见公告表（32 号表）

> 2026-09-06 ｜ 依据：KS×DSH 决策 19 延伸——用户语义 C「手动添加公告列表页 URL，引擎随巡检定期看新公告并轻通知（与库内有无该号无关）」；设计经 verify_rollout 三路择优（0.512）+ 用户拍板（首扫算基线 / 默认禁内网） ｜ 红线流程：本文档 → test_contract.py → schema.sql（三件套同步落地）

## 变更内容

**新表 announcement_observed（公告源已见公告）**——公告发现流程的"见过"记录，与查号巡检（update_change_event，外键绑批次）是两条独立流程：

| 列 | 类型 | 语义 |
|---|---|---|
| `observed_id` | TEXT PK | ULID 前缀 `ann_` |
| `source_id` | TEXT NOT NULL | 来源源 id（`app_config` 键 `announce.sources[].id`；**配置语义不建外键**——删源不删记录，历史公告留档） |
| `source_name` | TEXT | 源名快照（源改名/删除后列表仍可读） |
| `title` | TEXT NOT NULL | 公告标题（列表页 `<a>` 文本） |
| `url` | TEXT NOT NULL | 公告详情页绝对 URL |
| `url_hash` | TEXT NOT NULL | 归一化 URL 的 SHA-256 小写 hex（去 fragment/追踪参数/尾斜杠，host 小写、query 排序） |
| `standard_no` | TEXT | 标题中正则识别出的标准号（可空；零 LLM，识别不出留空） |
| `published_date` | TEXT | 列表页解析日期 YYYY-MM-DD（解析失败留空，不猜测） |
| `first_seen` | TEXT | 首次发现时间（datetime('now')） |
| `last_seen` | TEXT | 最近一次扫描仍在列表上（刷新不插行） |
| `scan_id` | TEXT | 首次发现所在扫描 id（`asc_` 前缀；审计回溯） |
| `user_ack` | INTEGER DEFAULT 0 | P1 已读标记（P0 不暴露 UI；列先行避免二次契约周期） |

**索引**：`UNIQUE(source_id, url_hash)`（去重键，按源隔离——同 URL 配在两个源下是两条记录，"在该源上新出现"才是语义）+ `idx_announce_first_seen(first_seen)` + `idx_announce_scan(scan_id)`。

**配套配置（非 DDL）**：`app_config` 键 `announce.sources`（JSON 数组，源清单）与 `announce.scan_state`（最近一次扫描快照，含 per_source 状态）——均为配置/快照语义，走既有 app_config 表，无 DDL。

**配套错误码（非 DDL）**：`UPD-2005 announce_source_not_found`(404)、`UPD-2006 announce_scan_already_running`(409)、`UPD-3008 illegal_source_payload`(422)——追加至 `channels/base.py` 错误码头注表与 pipeline/05 §2。

## 影响面与回滚

- 改动文件：`schema.sql`（32 号表 + 3 索引 DDL）、`tests/test_contract.py`（4 用例：表存在/列集完备/去重唯一索引与重复拒绝/ULID 前缀注释）、本文档；实现落点 `src/core/update/announce.py`（新）+ `src/core/api/routes_update.py` + 插件 host/client。
- 存量零影响：新表无外键、不进既有任何流程；巡检/检索/收藏零行为变化。
- 回滚：`DROP TABLE IF EXISTS announcement_observed;` 及索引（无外键无方向依赖，等价静态回滚）；测试基线只涨不跌（test_contract 31 → 35）。

---

## 33 号变更：`verification` SSE 事件新增 `unsupported_context` 字段（2026-09-16）

**性质**：**纯增量字段**，不改事件顺序、不改既有字段名与语义、不改任何表。
`SSE_EVENT_ORDER`（`evidence` → `status` → `delta` → `verification` → `done`）**零变化**。

**动机（D 线"资格声明"）**：`unsupported_clauses` 记的是"模型引用了**证据集之外**的
条款号"——这是**提示词级硬约束的违反**（SYSTEM_PROMPT 规则 2），故它就该拦。
但它只给一串裸条款号，用户无法区分三种**后果完全不同**的情形：

| 情形 | 后果 | 该做什么 |
|---|---|---|
| 该条属于**本轮证据内同一部标准**，只是没被检索出来 | 检索召回问题 | 扩大检索/补该条 |
| 该条指向**本轮完全没讨论**的标准号 | 提示词违规，或编造 | 不接受该引用 |
| 条款号形状可疑（如 `9.9.9`） | 更可能是编造 | 不接受该引用 |

**字段形状**（`unsupported_context: Array<{clause_number, standard_no, verdict, reason}>`）：
- `verdict` 取 `same_standard_not_retrieved` / `outside_evidence_standard` / `unknown`；
- 判据**只用文本内证据**（条款号附近是否出现标准号、该标准号是否在本轮证据里），
  **不查库**——核验器保持纯函数、毫秒级、零 IO；
- 附近找不到标准号时明确记 `unknown`，**不猜**。

**兼容性**：既有消费方（前端 `verification` 渲染、`debug_dump`、测试断言）读
`unsupported_clauses` 不变；新字段为附加项，未消费者零影响。

**影响面**：`src/core/domain/models.py`（`VerificationResult` 加字段）、
`src/core/verification/typed_verifier.py`（`_describe_unsupported` + 组装）、
`src/core/llm/ks_answer.py`（组装置透传）、`src/core/api/server.py`（SSE 体检事件透传）、
`tests/test_unsupported_context.py`（新）。

**回滚**：删该字段的三处透传即可（无 DDL、无状态、无迁移）。

---

# 契约增量 · 知识库多级目录 · folder / folder_member / doc_filing_state（33~35 号表）

> 2026-09-21 ｜ 依据：**docs/KB-FOLDER-PLAN.md**（业主定案，本文件是该功能的唯一方案真源）§3「数据形状（决定一切，先定死）」｜ 红线流程：本文档 → test_contract.py → schema.sql（三件套同步落地）

## 变更内容

三张**新表**（不改 `doc_meta` 一个字段：它是取证链承重墙，方案 §七也只允许"归属表整表清掉重来"）。

| 表 | 主键 | 关键约束 |
|---|---|---|
| `folder` 知识库目录 | `folder_id TEXT PRIMARY KEY`（DDL 注释声明 ULID 前缀 `fld_`，与 30/32 号表同款风格） | `parent_id` 可空（NULL ⇒ 在顶层出现）；`name NOT NULL`；`sort INTEGER DEFAULT 0`；`created_at` 默认 `datetime('now')` |
| `folder_member` 归属（**多对多**） | `PRIMARY KEY (folder_id, item_kind, item_id)` 三列 | `item_kind` CHECK 二枚举 `folder`/`file`；**无外键**（`item_id` 多态） |
| `doc_filing_state` 处理状态 | `doc_id TEXT PRIMARY KEY` | `stage` 缺省 `queued`，CHECK 五枚举 `queued`/`recognizing`/`confirming`/`filed`/`failed`（= 排队/识别中/待确认/已归位/识别失败）；`confidence`/`failure_kind`/`suggested_folder_id`/`suggest_new_path`/`placed_folder_id`/`placed_by`/`placed_at`/`last_error` 均可空 |

**索引**：`idx_folder_root_name`（`UNIQUE(name) WHERE parent_id IS NULL`）+ `idx_folder_child_name`（`UNIQUE(parent_id,name) WHERE parent_id IS NOT NULL`）—— 同名同层拒绝必须**含根层**：`UNIQUE(parent_id,name)` 对 NULL 无效（NULL 互不相等），只靠表级 UNIQUE 拦不住一级重名；`idx_folder_parent`；`idx_folder_member_item(item_kind,item_id)`；`idx_filing_stage(stage,updated_at)` + `idx_filing_placed_folder(placed_folder_id)`。

**两级父子关系的语义分工**（方案 §3 同时给了 `parent_id` 与 `item_kind='folder'`，两者都照写）：
`folder.parent_id` = **主位置**（唯一，决定 `parent_id IS NULL` 的顶层归属）；`folder_member(item_kind='folder')` = **全部**父子边（可多条 ⇒ 复制出来的子目录是"同一份挂两处"）。不变式：`F.parent_id=P` ⇒ 必有成员行 `(P,'folder',F)`。环的禁止由 `folder_store` 在写事务内判定，**不只靠**这个不变式。

**与 9c `user_bookmark_folder` 的关系**：**无关**。那张表是单层收藏夹（`UNIQUE(folder_name)` 全库同名拒绝、无 parent_id、夹内只装收藏），装不下无限层级；两张表的 `folder_id` 同形但各自表内引用，**任何查询不得跨表 join**。

## 影响面与回滚

- 改动文件（数据层这一步）：`src/core/storage/schema.sql`（33~35 号表 + 6 索引）、`tests/test_contract.py`（7 用例：三表存在/列集/ULID 前缀注释/三列主键/item_kind 枚举/根层同名拒绝且异层同名放行/stage 五枚举）、本文档。**`sqlite_db.py` 未改**——`init_schema` 走 `executescript` 全量执行，新表即新库与老库都自动落地；本次**不需要** `_ensure_*_columns` 那类补列迁移（那是给**既有表加列**用的）。
- 存量零侵入：全部 `IF NOT EXISTS` 幂等；不动既有 1~32 号表、FTS/VEC 虚拟表、SSE 事件与 API 契约。
- 实现落点：`src/core/knowledge/folder_store.py`（读写函数）、`scripts/preview-folder-filing.py`（只对真库副本的归位预览）。界面与 HTTP 接口**不在本增量**（方案 §五第 2/3 步）。
- 回滚：`DROP TABLE IF EXISTS doc_filing_state; DROP TABLE IF EXISTS folder_member; DROP TABLE IF EXISTS folder;`（三表互无外键、无方向依赖）；索引随表消失。不动 `doc_meta` 的任何行，也不动磁盘文件。
- 测试基线只涨不跌（test_contract +6）。

---

# 契约增量 · 知识库多级目录 · 第 2 步 HTTP 接口（`/api/v1/kb/*`，共 15 条）

> 2026-09-21 ｜ 依据：**docs/KB-FOLDER-PLAN.md**（唯一方案真源）§四「要做的能力」/§五第 2 步 ｜ 红线流程：本文档 → 用例 → 实现

## 新增端点（**全是新增**：不改任何既有端点的既有字段、不改任何既有表）

| 方法 | 路径 | 作用 | 关键入参 |
|---|---|---|---|
| GET | `/api/v1/kb/folders` | 列**某一级**的下级目录（带"含更深层的文件数"） | `parent_id`（省略/空=顶层）、`limit`（默认 200，上限 500）、`offset` |
| GET | `/api/v1/kb/folders/{id}/items` | 该级**直接**放的文件 | `limit`（默认 **50**，上限 200）、`offset`；`id` 可为 `root` |
| POST | `/api/v1/kb/folders` | 建目录 | `{parent_id?, name, sort?}` |
| PUT | `/api/v1/kb/folders/{id}` | 改名（**只改库里的名字**，不动磁盘文件） | `{name}` |
| POST | `/api/v1/kb/folders/{id}/move` | 挪目录 | `{from_parent_id?, to_parent_id}` |
| POST | `/api/v1/kb/folders/{id}/copy` | 复制目录（新目录**共享成员**，不拷文件） | `{to_parent_id?, name?}` |
| GET | `/api/v1/kb/folders/{id}/delete-preview` | 删前"先问一句"的数字（只读） | — |
| DELETE | `/api/v1/kb/folders/{id}` | 删目录 | `?mode=reparent\|purge` |
| POST | `/api/v1/kb/members` | 批量加成员 | `{folder_id, items:[{kind,id}]}` |
| POST | `/api/v1/kb/members/remove` | 从**这一处**拿掉（不删文件） | `{folder_id, items}` |
| POST | `/api/v1/kb/members/move` | 批量挪 | `{items, from_folder_id, to_folder_id}` |
| POST | `/api/v1/kb/members/copy` | 批量复制 | `{items, to_folder_id}` |
| GET | `/api/v1/kb/inbox` | 「待分类」列表（带状态与建议） | `limit`（默认 50）、`offset` |
| POST | `/api/v1/kb/inbox/confirm` | 批量确认归位 | `{decisions:[{doc_id, action, …}]}` |
| POST | `/api/v1/kb/scope/resolve` | 范围集合（含所有下级 + 并集） | `{folder_ids:[]}` |

`item_kind`（= 请求体里的 `kind`）二枚举 **`folder` / `file`**；`action` 三枚举
**`accept` / `existing` / `new`**。

## 出参形状

统一外壳 `{"code":200,"status":"success","data":{…}}`（错误见下表）。

- **GET /folders** → `data`: `{folder, breadcrumb, subfolders[], total, offset, limit, has_more}`。
  `folder` 顶层为 `null`；`breadcrumb` 从顶层到本级（顶层为 `[]`）。
  每个 `subfolders[i]` = `{folder_id, parent_id, name, sort, created_at, file_count_direct, file_count_deep, folder_count_deep}`
  （`*_deep` 含所有下级，去重：一个文件挂多处只算一次）。**空目录 ⇒ `subfolders: []`、`total: 0`**。
- **GET /folders/{id}/items** → `{folder, breadcrumb, items[], total, offset, limit, has_more}`。
  `items[i]` = `doc_meta` 的既有列 + `stage` / `confidence` / `failure_kind` / `suggested_folder_id`。
  顶层（`root`）给的是"还没进任何目录"的文件。**空目录 ⇒ `items: []`、`total: 0`（不是 404）**。
- **POST /folders** → 建出来的那一行：`{folder_id, parent_id, name, sort}`。
- **PUT /folders/{id}** → `{folder_id, name, parent_id}`。
- **POST /folders/{id}/move** → `{folder_id, parent_id, name, from_parent_id, to_parent_id, updated_main_position, moved}`。
  `updated_main_position=false` ⇔ 这一次**没有**动目录本体（`parent_id`）：从"复制出来的那一处"
  挪到另一个**目录**时，只删源边 **+ 补新边**（`to_parent_id` 是目录 ⇒ 它在那儿出现），
  `parent_id` 原样（补边不改"主位置"）；`true` ⇔ `parent_id` 真的变了 —— 从主位置挪走，
  或**挪到顶层**（`to_parent_id=null` ⇒ `parent_id` 置 NULL，库里"在顶层"的判定口径就是它；
  同时删掉源边与旧主位置那条边 ⇒ 它进顶层、旧父目录里不再有它）。
  `moved=false` ⇔ 已经在那一处（幂等空操作）。
- **POST /folders/{id}/copy** → `{folder_id, parent_id, name, sort, copied_members, copied_from}`。
- **GET /folders/{id}/delete-preview** → `{folder, is_empty, direct_subfolder_count, direct_file_count,
  subtree_folder_count, subtree_file_count, reparent_available, files_kept_elsewhere, files_would_be_deleted}`。
  `reparent_available=false` ⇔ 一级目录（没有上一层）。`files_would_be_deleted` = purge 后**在任何目录里都不再出现**的文件数。
- **DELETE /folders/{id}** → `{folder_id, mode, removed, reparented_subfolders, reparented_files,
  purged_folders, unfiled_docs[, deleted_docs, new_parent_id]}`；`mode` 取 `empty` / `reparent` / `purge`
  （空目录走 `empty`，此时 `mode` 参数被忽略、`deleted_docs` 不出现）。
- **POST /members** → `{folder_id, added, skipped, total}`（**已在该目录里 ⇒ `skipped`，幂等不报错**）。
- **POST /members/remove** → `{folder_id, removed, total}`（`removed` 是真正删掉的归属行数）。
- **POST /members/move** → `{from_folder_id, to_folder_id, moved, total}`。
- **POST /members/copy** → `{to_folder_id, added, skipped, total}`。
- **GET /inbox** → `{items[], total, offset, limit, has_more}`；`items[i]` =
  `{doc_id, standard_no, standard_name, stage, confidence, failure_kind,
  suggested_folder_id, suggested_path, suggest_new_path}`。
  `stage` 五枚举 `queued/recognizing/confirming/filed/failed`；
  `suggested_folder_id` **现算**（库里存着的建议优先；否则按现有分类口径算出路径、**再映射成
  真树路径**（真树跳过了标准树那层重复的 L1，见 `folder_filing_plan.tree_path_of`），在**已有目录**
  里逐级退到最近一层（L4→L3→L2，**不退到顶层**））
  —— **只匹配现有目录，绝不自行新建**；两个**兜底桶**（`其他标准` / `未定级`）**一律不给建议**
  （`null`：它们要的是识别或人工选，不该被塞进某个分支；真库那 379 篇全是这一类）。
  `suggest_new_path` 恒为 `null`（第 4 步给）。
- **POST /inbox/confirm** → `{confirmed, targets[{doc_id, folder_id, action}], created[], removed_from_pending}`。
  **一个事务，整批全成或全败**；确认后 `stage='filed'` **并自动从「待分类」那一处拿掉**归属。
- **POST /scope/resolve** → `{folder_ids[], doc_ids[], folder_count, doc_count, roots[]}`
  （两个 id 数组**已排序**、去重：一个文件挂多处只算一次）。

## 错误码（`{"code":<status>,"status":"error","error":"<码>","message":"<中文>"}`）

| 码 | HTTP | 何时 |
|---|---|---|
| `folder_not_found` / `doc_not_found` | 404 | 目录 / 文档 id 不存在 |
| `folder_name_conflict` | 409 | 同名同层（**含根层**） |
| `folder_not_in_parent` | 409 | `from_parent_id` 那一处其实没有这个目录 |
| `folder_delete_mode_required` | 409 | 删非空目录但没给 `mode`（**不替调用方选**） |
| `folder_top_level_no_parent` | 409 | 一级目录做 `reparent`（**不静默降级成 purge**） |
| `folder_cycle` | 422 | 挪/复制进它自己或它的任何下级 |
| `folder_depth_exceeded` / `invalid_folder_name` | 422 | 超层数/路径/名字非法 |
| `invalid_delete_mode` / `invalid_item_kind` / `invalid_pagination` / `invalid_stage` /
  `invalid_state_field` / `invalid_scope` / `invalid_decision` / `no_suggestion` | 422 | 入参不合法 |
| `unauthorized` | 401 | 缺 token（与全站一致） |

## 分页与空态口径（写死，界面照这个做）

- 参数名一律 **`limit` / `offset`**（**不叫** `page_size` / `page`）；`limit<=0` 或超上限 ⇒
  `invalid_pagination`（422），`offset<0` 同。目录列表默认 200/上限 500，文件与「待分类」默认 **50**/上限 200。
- `has_more` = `offset + 本页条数 < total`。
- **空目录不是错误**：`subfolders: []` / `items: []`，HTTP 200。
- **未知 id 一律 404**，绝不静默返回空（空范围会让"在此范围内提问"悄悄变成全库提问）。
- 「待分类」列表按 `catalog_hidden=0` 过滤 ⇒ 被隐藏的那几篇只在目录里看得见（方案 §十，第 4 步修）。

## 影响面与回滚

- 改动文件：`src/core/api/routes_kb_folders.py`（新）、`src/core/api/server.py`（**只加一处 register**）、
  `src/core/knowledge/folder_store.py`（加 `PREBUILT_TOP_NAMES` / `folder_tree_index` /
  `suggest_folder_for_doc` / `confirm_inbox_decisions`，并修准挪动语义与排序）、
  `src/core/knowledge/folder_filing_plan.py`（**加「分类口径 ↔ 真树」的唯一所有者**：
  `tree_path_of` / `SKIPPED_PLAN_TOP` / `STANDARD_TOP_NAME`；建议去向与落库脚本都走它）、
  `src/core/knowledge/doc_catalog.py`（L1 名字收成 `STD_LEVEL1_NAME` 一个常量）、
  `scripts/apply-folder-filing.py`（加 schema 对账；顶层名与"跳过哪一段"改从上面那个所有者取）、
  `tests/test_kb_folder_api.py`（新）、`tests/_kb_folder_api_fixtures.py`（新）、
  `tests/test_folder_store.py` / `tests/test_apply_folder_filing.py`、本文档。
- **与收藏夹 `/api/v1/bookmark-folders` 无关**：那是单层收藏夹（`folder_id` 前缀 `bmf_`，
  `user_bookmark_folder` 表），本族是无限层级知识库目录（前缀 `fld_`）；两张表的 `folder_id`
  同形但各自表内引用，**任何查询不得跨表 join**。
- 存量零侵入：新端点只读写 33~35 号表；不改 `doc_meta` 一个字段；删目录走既有 `doc_delete`（含审计与级联）。
- 回滚：删 `routes_kb_folders.py` + `server.py` 里那 3 行 register 即回到本增量前（数据层不动、界面未接）。
- 测试基线只涨不跌（本步 **+44**：`test_kb_folder_api.py` **31**（新）+ `test_folder_store.py`
  **+7**（第 1 步 24 → 31）+ `test_apply_folder_filing.py` **+6**（第 1 步 15 → 21）；
  `tests/_kb_folder_api_fixtures.py` 是夹具，**不算用例**）。
  ⚠ 原写 "+52" 与本行自列的 31+7+6 不符（2026-09-21 复核机械数过：批次内 `+def test_` 共 **44** 条）。

---

# 契约增量 · 向量表加 `doc_id` 元数据列（范围下推修复）

> 2026-10-09 ｜ 依据：**`specs/003-vec-scope-pushdown/`**（spec-kit 立项；唯一方案真源）｜
> 红线流程：本文档 → `tests/test_contract.py` → `schema.sql`

## 变更内容

`clause_vec` 由

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS clause_vec USING vec0(
    clause_revision_id TEXT PRIMARY KEY,
    embedding FLOAT[512]
);
```

改为

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS clause_vec USING vec0(
    clause_revision_id TEXT PRIMARY KEY,
    doc_id TEXT,                       -- 元数据列：参与 KNN 前置过滤
    embedding FLOAT[512]
);
```

## 为什么必须改（一手证据）

**缺陷**：范围提问时，向量通道的过滤写成
`clause_revision_id IN (SELECT clause_revision_id FROM clause_revision WHERE doc_id IN (…))`。

⚠ **2026-10-09 就地更正**（本增量初版写的"范围子查询返回 ≥2 个 id 就返回 `[]`"**不准确**，已作废）。
判决性实验（`specs/003-vec-scope-pushdown/probes/probe-mechanism.py`）给出的**真正失效条件**：

| 范围里的条款**有向量的比例** | 旧写法 |
|---|---|
| **全部都有向量**（真库今天的常态） | ✅ 正常 |
| **只有一部分有向量** | ❌ **返回 `[]`**（退化成"先 KNN 再筛"） |

**与表大小无关**（近邻 25 → 100,000 条，行为一样）。

**真库现状（实测）**：`clause_vec` = `clause_revision` = **663,634** 行、
**"有条款却没有向量"的文档 = 0 篇** ⇒ **旧写法现在工作正常**。
⇒ 本项修的是**潜在脆弱点**，**不是当前正在发生的故障**。触发路径是可达的：
① 入库时嵌入模型不可用会**跳过向量写入**（`vec_ok=False`，设计如此）；
② 部分重建（影子表只跑一部分就换表）；③ 删向量后未回填。
一旦发生，症状**静默**（用户看到"这个目录里没有"）。

**修法**：改用**元数据列** `doc_id`。实测（`specs/003-vec-scope-pushdown/probes/`）：

| 写法 | 结果 |
|---|---|
| `clause_revision_id IN (子查询)` | ❌ 0 行 |
| **`doc_id IN (SELECT value FROM json_each(?))`** | ✅ **下推成功**（范围 100 篇也成立） |
| `doc_id IN (?, ?)` 字面量 | ❌ **返回范围外的行**（比现状更糟） |
| `doc_id = ? OR doc_id = ?` | ❌ 同上 |
| `rowid IN (…)` | ❌ `no such column: rowid` |

⇒ **`doc_id` 必须是普通元数据列**（不是 `+doc_id` aux、不是 PRIMARY KEY）；
**范围过滤只许用 `json_each` 子查询这一种写法**。

## 影响面

- **改动文件**：`schema.sql`（1 张虚拟表加 1 列）、`tests/test_contract.py`（+1 用例）、本文档；
  实现落点 `src/core/storage/clause_repo.py`（**两处** INSERT 带 `doc_id`）+
  `src/core/retrieval/hybrid_engine.py`（向量通道范围片段改走 `doc_id`）。
- **写入侧必须同步**：`clause_repo` 的两处 INSERT 若不带 `doc_id`，新条款会**静默地**在范围提问里查不到
  （`doc_id` 可空 ⇒ **不报错**，且**没有任何下游读数能发现**）。
- **⚠ 虚拟表不支持 `ALTER TABLE`** ⇒ 存量库**必须走迁移**（建新表 → 纯 SQL 拷贝 → 改名）；
  `CREATE VIRTUAL TABLE IF NOT EXISTS` 对**已存在**的表**不会**升级形状。
  迁移脚本：`scripts/migrate-clause-vec-doc-id.py`（`--dry-run` / `--apply` / `--db-copy`）。
- **迁移不重算向量**：`doc_id` 从 `clause_revision.doc_id` 关联取得，`embedding` 原样搬运 ——
  实测**逐字节一致**（`probes/probe-vec-scope-fix2.py` Q7）。
- **连带**：`tests/test_embedding_rebuild_resume.py::test_shadow_dim_matches_production_schema`
  用**严格正则**钉住 DDL 形状 ⇒ 同步改；`eval/recall-funnel/exp-17-…/rebuild-shadow.py`
  的影子表自称"与生产同形" ⇒ 同步加列。
- **零回归**：不加范围的主路径 **top-20 逐条不变**（探针 Q6）；KNN 耗时 0.96 → 0.97 ms/次（Q9）。
- **不动**：`doc_delete.py`（按 `clause_revision_id` 删）、其余五条通道的范围写法、API/SSE/通道枚举。

## 回滚

**代码**：`git revert` 本增量（`schema.sql` / `clause_repo.py` / `hybrid_engine.py` / `test_contract.py`）。

**数据**（若已跑迁移）：

```sql
-- ① 删掉新表，② 把备份表改回原名（备份表名由迁移脚本打印）
DROP TABLE IF EXISTS clause_vec;
ALTER TABLE clause_vec_pre003 RENAME TO clause_vec;
```

迁移脚本 `--apply` 时**自动**留下 `clause_vec_pre003`（旧表改名保留，**不删**）+ 全库副本，
且把上面两条命令打印出来 ⇒ 回滚是**可执行命令**，不是"理论上可以"。

## 验证记录

- `pytest tests/test_contract.py -q` ⇒ 见收工读数
- `pytest tests/test_kb_scope_retrieval.py -q` ⇒ **那条真缺陷用例转绿**（断言一字未改）
- 迁移后自检：行数相同 / 向量逐字节相同 / `doc_id` 与 `clause_revision` 全表一致

