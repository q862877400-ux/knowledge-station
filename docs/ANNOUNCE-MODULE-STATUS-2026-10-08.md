# 部委公告监控 / 法规标准动态抓取 —— 模块现状（2026-10-08 代码通读）

> 定位范围：`D:\AI\work space\zcode`（KnowledgeStation）的 **update 域**。
> 注意：`tools/gov-qa/` 是**另一件事**（部委公众问答采集），不在本文范围。

## 0. 一句话

盯住用户配置的部委「公告栏 / 通知公告」列表页，**逐页翻**抓新公告 → 零 LLM 启发式解析 →
按 URL 去重落库 → 把该入库的**正文**抓下来进知识库 → 从中提取「发布 / 修订 / 废止 / 征求意见」
四类**变更信号**供查询。护城河定位 = 「可核验的覆盖率」的执行层。

## 1. 两条**互相独立**的流程（别混）

| | 查号巡检 | 公告发现（本文重点） |
|---|---|---|
| 入口 | `src/core/update/inspector.py`（937 行） | `src/core/update/announce.py`（822 行） |
| 单元 | **标准号**（`doc_meta.standard_no`） | **源 URL**（用户配的列表页） |
| 问题 | 「这个号还有效吗」 | 「这个栏目有什么新公告」 |
| 手段 | 走渠道降级链 probe 单号 | 抓列表页 + 解析 + 去重 |
| 落库 | `update_change_event`（29 号表） | `announcement_observed`（32 号表） |
| 触发 | 手动 / 调度器建批 | 巡检 `finalizeBatch` 尾自动 + 手动按钮 |

调度器 `scheduler.py`：2s 轮询，按 `update.schedule_days`（默认 7 天）自动建 tier0/tier1 批次；
跨日只恢复 `pause_reason='budget'` 的批次，**验证码暂停（`captcha`）绝不自动恢复**（必须人工过点）。

## 2. 代码地图

```
src/core/update/
├── announce.py          # 公告发现主模块（源 CRUD + 翻页抓取 + 解析 + 去重落库 + Excel 导出）
├── discover.py          # 「找标」：口语描述 → CCS 分类 → 网络检索卡片（与公告发现不同）
├── web_ingest.py        # 公告正文入库 + 效力档/层级/范围/变更信号 四类判定（506 行）
├── inspector.py         # 查号巡检编排器（另一条流程）
├── scheduler.py         # 定时建批 / 恢复
├── subscriptions.py     # 领域订阅（app_config update.domain_subscriptions）
├── change_repo.py       # 变更事件仓储
├── channels/            # 13 个渠道适配器 + 基类 + 路由
│   ├── base.py          # ChannelResult(11 字段) / ChannelAdapter / default_transport / norm_no
│   ├── cssn.py          # ★ 全覆盖首选（GB/GB-T/GB-Z + 食品/工程/转换）
│   ├── govcn_announce.py# 中国政府网政策文件库公告检索 + PDF 存档
│   ├── official_gb / laws_db / web_fallback   # 硬 import
│   ├── mem_gov / std_samr_hb / hbba / dbba / ndls / mohurd / ttzb / mee / cssn  # _safe_import
│   └── routing.py / ledger_chain.py / question_router.py
└── ...

src/core/api/routes_update.py   # /api/v1/update/announce-* 全部端点
src/core/api/routes_law.py      # /api/v1/laws/change-signals
plugin/src/announce.js          # 宿主侧接线（巡检尾触发 → 轮询 → 自动入库）
plugin/client/KsSettingsSection.tsx  # 「公告发现」设置界面
```

## 3. announce.py —— 发现流程详解

### 3.1 源配置（app_config，配置语义）
- 键 `announce.sources`（JSON 数组）；`add_source / update_source / remove_source`。
- 校验：必填、`http/https`、**默认禁内网**（loopback/RFC1918/链路本地/云元数据/`.local` 一律 422，
  主机字面量与 DNS 解析结果都查；无豁免开关）；**源数量不设上限**（2026-10-08 删 `SOURCES_MAX`）；URL 归一化后去重。
- **改 URL ⇒ 重置 `first_scan_done`**（换页 = 重新基线）。

### 3.2 触发与并发控制（`request_scan`）
- 时间闸：`force=false` 时距上次完成 < `announce.min_interval_hours`（默认 6h）→ 返回 `skipped`。
- **409 双闸**：进程内 `_announce_runs` + DB `scan_state.status`；僵尸扫描（DB running 但进程内无登记）
  自愈开新扫（扫描幂等且便宜）。
- 执行：fire-and-forget daemon 线程；`transport` 参数仅测试注入用。

### 3.3 抓取与翻页（`_scan_one_source`）
- 预算：单页 15s / 2MB、每页条目上限 50、源间 1s、全程软上限 300s（超时剩余源标 `skipped_timeout`）。
- **逐页翻（2026-09-24 起）**：`PAGES_PER_SOURCE_MAX=50`、`SOURCE_TIME_BUDGET_S=90`、
  连续 `STOP_AFTER_BARREN_PAGES=3` 页无新条目则停（追上历史，二次起便宜）、逐页 `PAGE_GAP_S=0.4`。
  三种停法都如实标 `truncated`；后续页失败另记 `page_errors`，**不判整源失败**。
- `discover_next_pages()` 覆盖两种形态：① 真 `<a>` 翻页链（只收同目录同站）；
  ② **JS 拼的翻页**（`document.write("…index_"+i+".shtml")` + `var countPage=N`，部委站最常见）。

### 3.4 解析（零 LLM，`parse_list_page`）
- 候选 `<a>` → 滤噪音（`_NOISE_RE`）、静态资源、JS 模板片段（`_JS_NOISE_RE`）→ 绝对化。
- **栏目导航过滤**：`looks_like_article()` —— 路径以 `/` 结尾 = 目录/栏目，不是公告
  （真机 558 条里 22 条导航全是这种；刻意**没加**更严的「必须有 `.html` 后缀」判据，那会误杀真公告）。
- 日期取锚文本里**最后一个**合理年份；标准号用 `_STD_TOKEN_RE` 识别（可空）。
- `js_shell_suspected`：页面 >40KB 但 `<a>` <5 个 → 疑似 JS 渲染壳。

### 3.5 落库与去重
- 表 `announcement_observed`：`UNIQUE(source_id, url_hash)`；`url_hash` = 归一化 URL 的 SHA-256
  （去 fragment / 追踪参数 / 尾斜杠、host 小写、query 排序）。命中已有行只刷 `last_seen`。
- **首扫基线**：源第一次扫描全部记 `baseline`（不计「新」），避免加源当天被几十条「新」刷屏。
- 失败诚实：WAF/验证码（`waf_captcha`）、JS 壳、解析 0 条、超时 —— 每源 `status=failed + reason` 直达 UI，
  **绝不静默假装「0 新公告」**。

### 3.6 查询与导出
- `list_items()`：按**公告发布日期 DESC**（不是 first_seen —— 那是「我们何时见到它」）。
- `export_announce_xlsx()`：Sheet1 最近扫描逐源状态 + Sheet2 公告明细全量（发布日期 DESC）。

## 4. web_ingest.py —— 正文入库与信号提取

### 4.1 四类判定（全在这一个文件，各有单一所有者）
| 函数 | 作用 | 输出 |
|---|---|---|
| `classify_scope` | 该不该入库 | `normative` / `non_normative` |
| `classify_status` | 效力档 | `reference`（征求意见稿·仅参考）/ `withdrawn` / `effective` |
| `classify_hierarchy` | 法规树档位 | `部门规章` / `地方政府规章` / `规范性文件` / `征求意见稿` / `其他` |
| `classify_change_signal` | **变更信号** | `draft` / `repealed` / `revised` / `issued` / `None` |

- `classify_scope` 判序**不可颠倒**：强规范性线索（征求/草案/标准/规范/办法/规定/条例/细则/令/目录…）
  → 留；排除词（决算/预算/公示/挂牌督办/督察/整改/征集/人选/年度报告…）→ 不入；其余 **默认留**。
  `force=true` 是逃生口。
- `classify_change_signal` 只认**标题里明写**的措辞（可复算），且 `issued`/`revised` **必须有对象词**
  （标准/规范/目录/条例…），否则「发布预警」「批准建实验室」会被误标。**宁漏不猜**。

### 4.2 批量入库（`ingest_pending`）
- 只抓**还没入库**的，判据 = `doc_meta.source_url`（本 URL 入过）**或** 同标题的 `standard_no`
  （`store_standard_no` 折过的**存储形**）。**不另立标记表**（两份真值必然漂移）。
- 封顶：`INGEST_BATCH_MAX=20` 条 + `INGEST_BUDGET_S=45s`，到点停并如实回
  `stopped_early` / `stop_reason`（limit|budget）/ `pending_left`。
- `ingest_announcement`：抓详情页 → `extract_body_text` 抽正文（优先 `TRS_Editor/zoom/article-content…`
  容器，配对括号切 div）→ `<40` 字判 `empty_body` 跳过 → `ingest_law_text(...)` 入库。
- **如实区分三种「没插新文档」**：`duplicate`（正文哈希同）/ `standard_exists`（标准号同）→ `skipped`；
  只有真插了才 `ingested`（此前把所有非 error 都写成 `ingested`，真机把 372 篇报成 478 篇）。

## 5. API 与宿主接线

引擎端点（`routes_update.py`）：
`POST /update/announce-scan`（force 开关，409=UPD-2006）、`GET /update/announce-scan/last`、
`GET/POST /update/announce-sources`、`PUT/DELETE /update/announce-sources/{id}`、
`GET /update/announce-items`、`POST /update/announce-export`、
`GET /update/announce-ingest/pending`、`POST /update/announce-ingest`、`GET /update/announce-ingest/triage`。
变更信号：`GET /laws/change-signals`（`signal` 过滤，非法值 422，**不静默当全部**）。

宿主（`plugin/src/announce.js`）：
- 单向依赖：`inspection.js finalizeBatch` 尾部调 `triggerAfterInspection`（`force=false` 走 6h 闸）。
- 轮询引擎至终态（1.2s），快照落 `ks-announce.json`（与 `ks-inspection.json` 并列，互不覆盖）。
- 扫描成功后**自动入库**最多 `AUTO_INGEST_LIMIT=20` 条（**默认开**，界面可关；结果留痕 `last.ingest`）。
- 启动接管：上次扫描 running 遗留 → 引擎在跑则接管，否则标 `stale_run`。
- 源 CRUD 为**纯代理**（引擎 `app_config` 是唯一真值，host 不存副本）。

## 6. 现状与诚实边界

**已落地（开发史 §10.189–§10.202，2026-09-24）**
- 从「只提醒、只翻 1 页」→「逐页翻 + 正文入库」。
- 真机：已发现 558 条 → 按范围该入 432 条 → 实入 **411 行**（`doc_meta` 真实新增 380 篇，含 16 篇征求意见稿）。
- 变更信号回填真库 55 条（修订 7 / 征求 16 / 发布 28 / 废止 4），逐条可复算、可按 doc_id 还原。

**遗留 / 未做**
- 老页面条目日期取不到（`parse_list_page` 只从锚文本取日期）⇒ 部分条目 `published_date` 为空，在最近列表排最后。
- `ADAPTER_CLASSES` 有 9 个渠道走 `_safe_import` ⇒ 导入失败只记 WARN，**渠道会静默从表里消失**。
- 13 个渠道里**只有 3 条在降级链上**（`routing` 的字面量链与台账 `update_channel` 不是同一份真值，
  台账驱动版在 `ledger_chain` 里「只算不改」）。
- 部分部委站是 JS 渲染壳 / 强反爬（WAF、验证码），只能如实标 failed，抓不到。
- `triage`（Jev 分档）只处理「规则判不收」的那批，规则本身会漏放一批（含「决定/通知」类行政事务）。

## 7. 关键常量速查

| 常量 | 值 | 位置 |
|---|---|---|
| `SOURCES_MAX` | ~~50 源~~ **已删除**（不设上限） | announce.py |
| `announce.scan_soft_cap_s` | 1800 s（可配） | app_config |
| `ITEMS_PER_PAGE_MAX` | 50 条/页 | announce.py |
| `PAGES_PER_SOURCE_MAX` | 50 页/源 | announce.py |
| `SOURCE_TIME_BUDGET_S` | 90 s/源 | announce.py |
| `PAGE_GAP_S` / `SOURCE_GAP_S` | 0.4 / 1.0 s | announce.py |
| `STOP_AFTER_BARREN_PAGES` | 3 页 | announce.py |
| `MIN_INTERVAL_HOURS_DEFAULT` | 6 h | announce.py |
| `PAGE_TIMEOUT_S` / `SCAN_SOFT_CAP_S` | 15 / 300 s | announce.py |
| `INGEST_BATCH_MAX` / `INGEST_BUDGET_S` | 20 条 / 45 s | web_ingest.py |
| `AUTO_INGEST_LIMIT` | 20 条 | plugin/src/announce.js |
| `DEFAULT_DAILY_BUDGET` | 500（仅 tier1 消耗） | inspector.py |
