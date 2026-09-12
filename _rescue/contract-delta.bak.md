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
