# plugin/ 事实地图

调查对象：`plugin/`（DSH 插件，宿主侧 + 浏览器侧 + 验证脚本）。本文件只陈述读过源码后能指回具体文字的事实。
统计口径一律写明命令；数不出来的写「未读」并给原因。

**本文件的取证方式**（全部只读，未跑任何冒烟/门禁/引擎）：

- `Get-ChildItem plugin/src -File` → 23 个文件（19 个 `.js` + 4 个 `.bak-*`）
- `Get-ChildItem plugin/client -File` → 33 个文件（19 `.tsx` + 12 `.ts` + 1 `.md` + 1 `.json`），其中 `.d.ts` 1 个
- `Get-ChildItem plugin/scripts -File` → 56 个 `.mjs`；另有 `scripts/lib/` 4 个 `.mjs`（合计 60）
- `Select-String -Path plugin/src/*.js -Pattern "webServer\.register\(\{"` → **49 处**路由注册
- `git ls-files` / `git status --short` / `Get-FileHash` 用于跟踪状态与备份判定

---

## 一、总览表

| 半边 | 规模 | 说明 |
|---|---|---|
| `plugin/src/` | 19 个 `.js`，483,245 字节，9,968 行 | 宿主侧：6 个模型工具 + 49 条 `/ks/*` 同源路由 + 2 段系统提示 + 3 条斜杠命令 + 引擎进程管理 |
| `plugin/src/*.bak-*` | 4 个，680 行 | 未跟踪的临时备份（见第七节） |
| `plugin/client/` | 31 个 `.ts/.tsx`，1,167,378 字节 | 浏览器侧：右侧栏 3 个 pane + 设置栏目 + 输入坞胶囊 + 开始页卡片 |
| `plugin/client.js` | 1,784,273 字节 | esbuild 单文件产物，**被 git 跟踪**，与源码整份比对是一条真断言 |
| `plugin/scripts/` | 56 个 `.mjs` + `lib/` 4 个 | 44 个进 `smoke-all.mjs` 链，12 个不进链 |
| `plugin/test/` | 1 个 fixture（`ks-engine-wire.json`，35,775 字节） | 6 个模型工具的出网请求契约回放 |

**总量分布**（字节占比，`Get-ChildItem client/*.ts,client/*.tsx` 合计 1,167,378）：

| 文件 | 字节 | 占比 | 行数 | 注释行 | 纯代码行 |
|---|---|---|---|---|---|
| `KsKnowledgePage.tsx` | 215,330 | 18.4% | 3,868 | 676 | 3,039 |
| `api.ts` | 206,812 | 17.7% | 5,011 | 795 | 3,930 |
| `KsEvidenceTab.tsx` | 139,311 | 11.9% | 2,834 | 573 | 2,122 |
| `ksGuideStyles.ts` | 101,355 | 8.7% | 1,135 | 181 | 932 |
| `KsSettingsSection.tsx` | 80,133 | 6.9% | 1,636 | 151 | 1,407 |
| `KsMaterialsPanel.tsx` | 73,759 | 6.3% | 1,409 | 293 | 1,051 |
| `KsChannelsPanel.tsx` | 50,743 | 4.3% | 905 | 81 | 782 |
| 其余 24 个文件合计 | 300,935 | 25.8% | — | — | — |

**前 7 个文件占 74.3%**（867,443 / 1,167,378 字节）。宿主侧同理：`index.js` 108,785 字节占 `src/` 的 22.5%，`chatmode.js` 80,029 占 16.6%，两者合计 39.1%。

---

## 二、plugin/src 逐文件

依赖关系（`Select-String -Pattern "^import .* from '\./(\w+)\.js'"`）：

```
engine.js  ← 被 12 个模块 import（announce/channels/chatmode/collect/docimage/ingest/
             inspection/materials/materials_routes/report/settings + index）
route_util.js ← channels / compliance-sentry / materials_routes / report / turn
trust.js    ← chatmode / settings / index
announce.js ← inspection（单向，防环，见 announce.js 头注）
```

`index.js` 是唯一入口（`package.json` 的 `"main": "src/index.js"`），import 了其余 13 个模块。

### 2.1 `index.js`（108,785 字节 / 1,891 行）— 入口

分段结构（全部用可搜索文字定位，行号只作辅助）：

| 段落 | 起始锚点文字 | 行 | 内容 |
|---|---|---|---|
| 文件头 | `DSH cordis plugin (host half). Registers three model-facing tools` | 1 | 说明（已过时：现在注册 6 个工具，不是 3 个） |
| import 区 | `import { createRequire } from 'node:module'` | 21–59 | 13 个本地模块 + `@deepseek-ai/schemastery` |
| 插件身份 | `export const name = 'ks-dsh-plugin'` | 62 | — |
| 硬依赖 | `export const inject = ['tools', 'webServer', 'systemPrompt']` | 75 | 只有三个（`agents`/`commands` 已改走 `ctx.get()`） |
| 配置 schema | `export const Config = Schema.object({` | 115 | 5 个键：`engineRoot` / `python` / `startupTimeoutMs` / `idleTimeoutMs` / `trustedHosts` |
| 配置键名单 | `export const CONFIG_KEYS = [` | 131 | 未知键当场报错的判据来源 |
| 路由常量 | `export const KS_SESSION_PATH = '/ks/session'` | 134–137 | 另有 `KS_PDF_WORKER_PATH` / `KS_PDF_WASM_PATH` / `KS_BBOX_PATH` |
| 证据锚点常量 | `export const KS_EVIDENCE_PATH = '/__ks_evidence__'` | 146–147 | 与 `client/ksEvidence.ts` 的 `EVIDENCE_PATH` 重复定义 |
| 锚点构造 | `export function evidenceAnchor(ev)` | 169 | 与 client 半 `evidenceUrlOf` 是**第二个** URL 构造者（头注自己承认这是"两个构造者分叉"的老坑） |
| query_mode 归一 | `function normalizeQueryMode(raw)` | 214 | 四值白名单 `['default','thorough','quick','guess']` |
| params 清洗 | `function sanitizeParams(raw)` | 225 | 白名单：`top_k` / `bookmarks_only` / `folder_id` / `material_project_id` / `max_evidence` / `kb_folder_ids` / `kb_doc_ids` |
| 证据裁剪 | `function trimEvidence(ev)` | 300 | 11 个键 |
| meta 摘要 | `function metaSummary(meta)` | 324 | — |
| 答案裁剪 | `export function trimAnswer(data)` | 352 | 调 `trimVerification` |
| 422 路径 | `function validationError(probe, query, queryMode)` | 380 | 与正常路径**共有 12 个键** |
| schema 常量 | `const EFFECT_COLOR_LIST = {` | 425 | 红/黄清单形状 |
| | `const ANSWER_EVIDENCE = {` | 454 | 证据条目形状 |
| | `const ANSWER_VERIFICATION = {` | 479 | 核验块形状 |
| 工具① | `export function makeEffectReportTool(manager)` | 628–843（216 行） | `ks_effect_report` |
| 工具② | `export function makePingTool(manager)` | 844–931（88 行） | `ks_ping` |
| 工具③ | `export function makeResolveTool(manager, chatModeOf)` | 932–1098（167 行） | `ks_resolve_clause` |
| 工具④ | `export function makeAnswerTool(manager, chatModeOf)` | 1099–1462（364 行） | `ks_answer`，本文件最大单块 |
| 路由① | `function registerKsSessionRoute(ctx, manager)` | 1463 | `GET /ks/session`（exact） |
| 路由② | `function registerKsBboxRoute(ctx, manager)` | 1503 | `GET /ks/bbox`（exact），含退化框过滤 `>= 5 && >= 3` pt |
| 路由③ | `function registerPdfWasmRoute(ctx)` | 1592 | `/ks/assets/pdf-wasm`（prefix） |
| 路由④ | `function registerPdfWorkerRoute(ctx)` | 1658 | `/ks/assets/pdf.worker.min.mjs`（exact） |
| 装配 | `export function apply(ctx, config = {})` | 1692–1891（200 行） | 未知键检查 → EngineManager → keepAlive → 6 个 `ctx.tools.register` → 2 个 `ctx.systemPrompt.section` → 3 条斜杠命令 → 15 个 `register*Routes` |

`apply` 里注册的**工具**（`ctx.tools.register` 共 6 处）：

| 工具名 | 定义文件 | 注册行 |
|---|---|---|
| `ks_ping` | index.js `makePingTool` | `ctx.tools.register(makePingTool(manager))` |
| `ks_resolve_clause` | index.js `makeResolveTool` | 同款 |
| `ks_answer` | index.js `makeAnswerTool` | 同款 |
| `ks_effect_report` | index.js `makeEffectReportTool` | 同款 |
| `ks_materials` | materials.js `makeMaterialsTool` | `ctx.tools.register(makeMaterialsTool(manager))` |
| `ks_collect` | collect.js `makeCollectTool` | `ctx.tools.register(makeCollectTool(manager, chatModeOf))` |

`apply` 里注册的**钩子**（`ctx.effect` 共 5 处，行 1718 / 1772 / 1776 / 1782 / 1817）：

1. `ctx.effect(() => { manager.armIdle(); return () => void manager.dispose() })` —— 空闲回收
2. `ctx.systemPrompt.section(makeChatModeSection({ parentSessionOf }))` —— 「📜 查法规模式」提示段（段名 `ks:forensic-mode`，order 199）
3. `ctx.systemPrompt.section(buildComplianceSection(...))` —— 合规哨句段（段名 `ks:compliance-sentry`，order 198）
4. `registerKsChatModeCommands(ctx, ...)` —— 3 条斜杠命令（`/forensic` `/bookmarks` `/materials`）
5. 15 个 `register*Routes(webCtx, manager)` —— 全部 `/ks/*` 路由，统一由 `guardWebServer` 套栅栏

`apply` 里注册的**路由**（15 个模块，49 条 `webServer.register`）：

`registerKsSessionRoute` / `registerPdfWorkerRoute` / `registerPdfWasmRoute` / `registerKsBboxRoute` / `registerKsInspectionRoutes` / `registerKsAnnounceRoutes` / `registerKsReportRoutes` / `registerKsChannelsRoutes` / `registerKsMaterialsRoutes` / `registerKsDocImageRoutes` / `registerKsSettingsRoutes` / `registerKsChatModeRoutes` / `registerKsTurnRoutes` / `registerKsComplianceRoutes` + `registerComplianceAskGate` / `registerKsIngestRoutes`。

### 2.2 其余 18 个文件

| 文件 | 字节 / 行 | 干什么 | 对外导出 | 谁在用 | 依赖的引擎端点 |
|---|---|---|---|---|---|
| `announce.js` | 39,008 / 927 | 公告发现：源 CRUD / 手动扫描 / 摘要 / 导出 / 入库 / 待清 / 变更信号 | 9 个 `KS_ANNOUNCE_*_PATH`、`announceFilePath`、`triggerAfterInspection`、`announceStartupCheck`、`registerKsAnnounceRoutes` | `index.js`（路由）、`inspection.js`（`finalizeBatch` 尾调 `triggerAfterInspection`） | `GET /api/v1/update/announce-scan/last`、`GET /api/v1/update/announce-items?limit=5`、`POST /api/v1/update/announce-scan`、`GET/POST /api/v1/update/announce-sources`、`PUT/DELETE /api/v1/update/announce-sources/{id}`、`POST /api/v1/update/announce-export`、`GET /api/v1/export/download`、`POST /api/v1/update/announce-ingest`、`GET /api/v1/update/announce-ingest/pending`、`POST /api/v1/update/announce-ingest/triage`、`GET /api/v1/laws/change-signals` |
| `channels.js` | 15,496 / 332 | 渠道台账：列表 / 新增 / 改 / 删 / 启停 / 立刻探一遍 / 已知文件测试 | `KS_CHANNELS_PATH`、`KS_CHANNELS_PROBE_PATH`、`KS_CHANNELS_ITEM_PREFIX`、`registerKsChannelsRoutes`（返回**数组** disposer） | `index.js` | `GET/POST /api/v1/channels`、`PATCH/DELETE /api/v1/channels/{id}`、`POST /api/v1/channels/{id}/enabled`、`POST /api/v1/channels/probe`、`GET/POST /api/v1/channels/{id}/test-case`、`POST /api/v1/channels/{id}/test` |
| `chatmode.js` | 80,029 / 1,391 | 会话级开关：查法规模式 / 仅收藏 / 收藏夹范围 / 参考资料项目；落盘 `ks-chatmode.json`（含跨进程文件锁） | `KS_CHAT_MODE_PATH`、4 段提示词常量、`FORENSIC_SECTION_NAME`/`ORDER`、`ensureLoaded`、`getMode`/`setMode`/`effectiveChatMode`、`hasActiveForensicSessions`、`makeChatModeSection`、`makeChatModeCommands`、`registerKsChatModeCommands`、`registerKsChatModeRoutes`、3 个 `__*ForTests` | `index.js`、`smoke-chatmode.mjs` | **零引擎端点**（纯 host 状态；只在 `client/api.ts` 侧看到它被读写） |
| `collect.js` | 16,523 / 300 | 模型工具 `ks_collect`（写：按 URL 采一份材料，只登记 pending） | `MAX_COLLECT_PER_SESSION`、`makeCollectTool` | `index.js` | `POST /api/v1/materials/projects/{id}/collect` |
| `compliance-sentry.js` | 15,690 / 273 | 合规护航：L0 哨句 + L1 按需段 + 技能正文 + 触发判据 + 采集审批门 | `KS_COMPLIANCE_SENTRY`、`STD_NO_PREFIXES`、`COMPLIANCE_SKILL_BODY`、`matchComplianceSentry`、`extractL1`、`buildComplianceSection`、`markComplianceTriggered`/`isComplianceTriggered`、`registerKsComplianceRoutes`、`registerComplianceAskGate`、`collectAskReason`、`buildComplianceNextStep`、`complianceNextStepMessage` | `index.js` | `POST /api/v1/laws/compliance-guard` |
| `docimage.js` | 7,658 / 171 | 文档图片同源代理（figure / formula / table-image），二进制 + `X-Frac-*` 头透传 | `KS_DOC_IMAGE_PATH`、`parseDocImagePath`、`registerKsDocImageRoutes` | `index.js` | `GET /api/v1/documents/{id}/figure/{no}`、`…/formula/{fno}?clause=…`、`…/table-image/{page}/{tbl}` |
| `engine.js` | 39,828 / 940 | 引擎进程管理：找仓根、venv 自愈、读 `engine.session.json`、懒启动、探活、空闲回收、只杀自己起的 | 24 个导出（`EngineManager`、`apiGet`/`apiGetBytes`/`apiPost`、`combineSignals`、`originUrl`、`HEALTH_PATH`、`KS_ANSWER_PATH`、`findEngineRoot`、`healVenvHome`、`resolvePythonPath` 等） | 12 个 src 模块 + 多个冒烟 | `GET /api/v1/health`、`POST /api/v1/ks/answer`（只作常量） |
| `ingest.js` | 30,317 / 761 | R27 入库预览 / 批量分桶 / 异步全量预览任务（状态文件 `ks-ingest.json` + adopt + 轮询） | 7 个 `KS_INGEST_*` 常量、`defaultInboxDir`、`ensureInboxDir`、`ingestJobFilePath`、`ingestJobStartupCheck`、`registerKsIngestRoutes` | `index.js` | `GET /api/v1/ingest/preview/inbox`、`POST /api/v1/ingest/preview`、`POST /api/v1/ingest/preview/batch`、`POST /api/v1/ingest/preview/jobs`、`GET /api/v1/ingest/preview/jobs/{id}`、`POST …/{id}/abort` |
| `inspection.js` | 44,338 / 1,077 | 每日巡检：手动触发 / 摘要 / 设置 / 导出 xlsx（状态文件 `ks-inspection.json` + adopt + 轮询 + 定时器） | 4 个 `KS_INSPECTION_*` 常量、`inspectionFilePath`、`emptyByClass`、`sanitizeLast`、`reduceOneClassRow`、`byClassEmpty`、`inspectionStartupCheck`、`registerKsInspectionRoutes`、`__resetInspectionForTests` | `index.js`、`smoke-class-summary.mjs`、`smoke-lifecycle.mjs` | `GET /api/v1/update/batch/{id}`、`GET /api/v1/update/changes?batch_id=…`、`POST /api/v1/update/check`、`POST /api/v1/update/report-xlsx/{batch_id}`、`GET /api/v1/export/download?name=…` |
| `materials_routes.js` | 20,418 / 470 | 界面用的 `/ks/materials/*` 同源**读写**通道（12 条路由） | `KS_MATERIALS_PATH`、`REVIEW_DECISIONS`、`registerKsMaterialsRoutes`、`KS_MATERIALS_PATHS`（12 条路径数组，只给冒烟用） | `index.js`、`smoke-materials-routes.mjs` | 见 2.3 |
| `materials.js` | 16,518 / 327 | 模型工具 `ks_materials`（**只读**：projects / materials / inbox） | `makeMaterialsTool` | `index.js` | 见 2.3 |
| `report.js` | 14,157 / 349 | 效力报告：即时聚合（零缓存零状态文件）+ 导出 xlsx + 研究报告 + 结论草稿 | 5 个 `KS_REPORT_*` 常量、`registerKsReportRoutes` | `index.js` | `GET /api/v1/report/effect`、`GET /api/v1/report/effect/docs`、`POST /api/v1/report/effect/export`、`POST /api/v1/report/research`、`POST /api/v1/report/research/draft`、`GET /api/v1/export/download` |
| `route_util.js` | 7,673 / 153 | `/ks/*` 共用小工具：JSON 响应 / 错误体 / 带上限 body 读取 / query 白名单 / 引擎结果映射 | `ROUTE_BODY_CAP`、`jsonResponse`、`errorBody`、`readJsonBody`、`pickQuery`、`mapProbe` | channels / compliance-sentry / materials_routes / report / turn | 无（纯函数） |
| `settings.js` | 8,700 / 235 | 「设置→API 配置」宿主代理：云 OCR / LLM 的 Key/BaseURL 管理 + 活体探测（纯代理零缓存） | `KS_API_CONFIG_PATH`、`KS_API_CONFIG_TEST_PATH`、`registerKsSettingsRoutes` | `index.js` | `GET/PUT /api/v1/settings/api-config`、`POST /api/v1/settings/api-config/test` |
| `tool-details.js` | 4,480 / 70 | 工具说明瘦身的"首次调用回执"侧（`exec.deferContext`） | `KS_ANSWER_DETAIL`、`firstUseReceipt` | `index.js`（`makeAnswerTool` 内） | 无 |
| `trim.js` | 4,755 / 103 | `ks_answer` 的纯函数裁剪层（核验块白名单） | `VERIFY_LIST_CAP`、`REASON_CAP`、`shortList`、`trimUnsupportedContext`、`trimVerification` | `index.js`、`smoke-trim.mjs` | 无 |
| `trust.js` | 5,663 / 134 | 同源信任栅栏（DNS rebinding / 跨站写入），由 `guardWebServer` 统一套住全部 `/ks` 路由 | `LOOPBACK_HOSTS`、`parseAuthority`、`trustedNames`、`requireJsonBody`、`guardRequest`、`guardRoute`、`guardWebServer` | `index.js`、`chatmode.js`、`settings.js` | 无 |
| `turn.js` | 3,209 / 64 | 「本轮」依据的暂存 + 只读口 | `KS_TURN_LAST_PATH`、`recordKsTurn`、`registerKsTurnRoutes` | `index.js` | 无（纯内存） |

### 2.3 `materials.js` 与 `materials_routes.js` 的引擎端点对照（回答问题 A）

| 引擎端点 | `materials.js`（模型工具，只读） | `materials_routes.js`（界面，可写） |
|---|---|---|
| `GET /api/v1/materials/projects` | ✅ 有 | ✅ 有 |
| `POST /api/v1/materials/projects` | — | ✅ 有 |
| `GET /api/v1/materials/projects/{id}/materials` | ✅ 有 | ✅ 有 |
| `GET /api/v1/materials/projects/{id}/inbox` | ✅ 有 | ✅ 有 |
| `POST /api/v1/materials/projects/{id}/scan` | — | ✅ 有 |
| `POST /api/v1/materials/projects/{id}/collect` | — | ✅ 有 |
| `POST /api/v1/materials/{id}/review` | — | ✅ 有 |
| `POST /api/v1/materials/{id}/tier` | — | ✅ 有 |
| `POST /api/v1/materials/{id}/role` | — | ✅ 有 |
| `GET /api/v1/materials/{id}/chunks` | — | ✅ 有 |
| `GET /api/v1/materials/tiers` | — | ✅ 有 |
| `GET /api/v1/materials/{id}/locators` | — | ✅ 有 |
| `GET /api/v1/materials/projects/{id}/locators` | — | ✅ 有 |
| `POST /api/v1/materials/{id}/reverify` | — | ✅ 有 |

**结论**：两模块的**权限边界是有意的、写在头注里的**（读一个工具、写一个工具；`materials.js` 头注「把 `review` 开成模型工具，等于让模型自己给自己发许可」）。但 **3 条只读端点被两边各写一遍**（projects / materials / inbox），且两边的**裁剪与错误处理各写一套**：

- `materials.js` 有 `trimMaterialRow`（13 键白名单），`materials_routes.js` 直接 `mapProbe` 透传引擎 `data`。
- 两边连**URL 拼法**都不同：`materials.js` 用 `const path = '/api/v1/materials/projects'` + 模板串；`materials_routes.js` 用 `const ENGINE_MATERIALS = '/api/v1/materials'` + `${ENGINE_MATERIALS}/projects`。

---

## 三、plugin/client 逐文件 + 为什么这么大

### 3.1 挂载关系（谁挂载谁）

入口只有一个：`client/entry.ts` 的 `export function apply(ctx: Ctx)`。

| 文件 | 干什么 | 谁挂载 | 字节 / 行 |
|---|---|---|---|
| `entry.ts` | 客户端 cordis 入口：注册设置栏目 / 输入坞胶囊 / 3 个右侧栏 tab 类型 + 3 个 pane body + 开始页卡片 + 证据链接兜底拦截 | DSH client loader（`/plugins/ks-dsh-plugin/client.js`） | 27,107 / 509 |
| `KsKnowledgePage.tsx` | 「知识库」pane body。四标签外壳（知识库 / 渠道库 / 办事台 / 预览器）+ 目录树 + 真表格 + 上传 + 范围提问 + CCS 补全 + 待分类处置 | `entry.ts`（`slots.register({name:'sidebar.right.pane.tab', key: KS_KB_IMPL_ID})`） | 215,330 / 3,868 |
| `KsEvidenceTab.tsx` | 「PDF 查看器」pane body：pdf.js 渲染 / 单页与连续两模式 / 红箭头 / 标题目录 / 收藏目录 / 文件目录 / 正文视图 / 底部工具栏 | `entry.ts` → `KsEvidenceHost` | 139,311 / 2,834 |
| `KsSettingsSection.tsx` | 设置栏目（`settings.section`）：巡检 / 公告源 / 待清 / API 配置 / 入库预览 / 箭头开关等，全部 `<details>` 折叠 | `entry.ts` 的 `registerKsSettingsSection` | 80,133 / 1,636 |
| `KsMaterialsPanel.tsx` | 备料面板：项目 / 材料评审 / 来源层级 / 任务效力 / 自采 / 研究报告 / 结论草稿 / 交付物 | `KsKnowledgePage`（`page === 'materials'`） | 73,759 / 1,409 |
| `KsChannelsPanel.tsx` | 渠道库面板：三列台账（接线 / 有效性 / 上次成功）+ 分类 + AI 修法提示词 | `KsKnowledgePage`（`page === 'channels'`） | 50,743 / 905 |
| `KsFilesTab.tsx` | PDF 查看器左列的「文件目录」视图（导出名 `KsFilesView`，与文件名不一致） | `KsEvidenceTab` | 30,405 / 805 |
| `KsTurnTab.tsx` | 「本轮」pane body：跟着当前回答走的依据行 + 核对结果 + 看原文 | `entry.ts` | 29,892 / 593 |
| `KsBookmarksTab.tsx` | PDF 查看器左列的「收藏目录」视图（导出名 `KsBookmarksView`） | `KsEvidenceTab` | 27,972 / 687 |
| `KsIngestPanel.tsx` | 入库预览面板（R27 dry-run 的人工确认界面） | `KsKnowledgePage` | 25,688 / 571 |
| `KsCapabilityPage.tsx` | 「办事台」：一列等高菜单行 + 各功能页（外发审计 / 差距分析 / 条款补丁等） | `KsKnowledgePage`（`page === 'capabilities'`） | 24,945 / 464 |
| `KsDocTextView.tsx` | 文档正文视图（`KsEvidenceTab` 的「正文」模式）：条款 HTML + 图片/公式/表格占位接线 | `KsEvidenceTab` | 16,677 / 393 |
| `KsEvidenceHost.tsx` | 官方 pane 座位 ↔ `KsEvidenceTab` 的**适配层**（两套 props 形状之间的映射） | `entry.ts` | 8,070 / 143 |
| `KsScopeChip.tsx` | 输入坞胶囊「🔖 夹名 · 仅在本收藏夹内提问 ✕」；也发 `POST /ks/compliance/ping` | `entry.ts` | 7,104 / 154 |
| `KsArrowOverlay.tsx` | 红色定位箭头覆盖层（单页/连续共用一份实现） | `KsEvidenceTab` | 3,519 / 69 |
| `KsKnowledgeGuide.tsx` | 右侧栏开始页那张卡（Button + ▾ Menu） | `entry.ts` | 3,012 / 62 |
| `kbListUi.tsx` | 面包屑 / 列表头共用件（`KsCrumb` / `KsListHead`） | `KsChannelsPanel` + `KsKnowledgePage` | 2,255 / 55 |
| `KsAnchorWarn.tsx` | 引文坐标缺失/失败的可见提示行 | `KsEvidenceTab` | 1,886 / 43 |
| `KsPdfGuideIcon.tsx` | 侧栏开始页图标（旧） | **无人 import**（见第七节） | 1,861 / 49 |
| `KsKnowledgeGuideIcon.tsx` | 「知识库」开始页卡片图标（书架） | `ksSidebar.ts` + `KsKnowledgeGuide.tsx` | 1,497 / 44 |
| `api.ts` | 全部取数：112 个 `export async function` + 60 个 interface/type | 11 个 tsx + `entry.ts` | 206,812 / 5,011 |
| `ksGuideStyles.ts` | 运行时注入的样式表 `KS_STYLES`（**不是** CSS module，理由见文件头） | 5 个组件调 `ensureKsStyles()` | 101,355 / 1,135 |
| `ksSidebar.ts` | 与官方右侧栏的唯一适配层：3 个 tab 定义 + 地址判据 + 标题函数 | `entry.ts` + 5 个组件 | 20,240 / 419 |
| `ksHostPrimitives.d.ts` | 宿主 `@deepseek-ai/dsh-client-ui-primitives` 的最小面声明（`declare module` 一块） | 编译期 | 17,122 / 286 |
| `pdfFit.ts` | PDF「默认铺满」缩放纯函数（规则三次修订） | `KsEvidenceTab` | 14,212 / 259 |
| `ksEvidence.ts` | 证据锚点 URL 契约与解析（`EVIDENCE_PATH` / `parseEvidence` / `evidenceUrlOf`） | `entry.ts` + 3 个组件 | 10,824 / 229 |
| `pdfPanel.ts` | 侧栏「让位 / 恢复」协调器（模块级 Map） | `KsEvidenceTab` | 9,411 / 188 |
| `ksPrefs.ts` | KS 自有偏好存储（本地持久化 + 可订阅） | `KsEvidenceHost` + `KsSettingsSection` | 4,377 / 110 |
| `ksSearchSyntax.ts` | 检索语法解析（`+` = AND、`-` = NOT） | **只有冒烟 import**（`smoke-client-entry.mjs` 动态 import） | 4,241 / 107 |
| `ks-evidence-props.ts` | 证据 tab 组件 props 契约 | `KsEvidenceHost` + `KsEvidenceTab` | 3,989 / 86 |
| `pdf-configure.ts` | pdf.js worker / wasm 接线 | `KsEvidenceTab` | 3,629 / 70 |
| `TASK-pdf-bottom-bar.md` | 一份任务交接书（见第七节） | — | 6,185 |
| `tsconfig.json` | `strict: true` / `jsx: react-jsx` / `noEmit: true` | 编译期 | 458 |

### 3.2 为什么这几个特别大

#### `KsKnowledgePage.tsx`（215,330 字节 / 3,868 行）

不是"一个页面"，是**四个页面 + 一个表格引擎 + 一个上传/入库流程**塞在一个函数里：

- `export function KsKnowledgePage({ useTabInfo }: ...)` 从 449 行一直到 3868 行——**单个函数体占 3,419 行**。
- 里面 **51 个 `useState`**（`Select-String -Pattern "useState<|useState\("`）、**38 个 `useCallback`**、7 个 `useMemo`、4 个 `useEffect`、3 个 `useRef`。
- 内部 `useCallback` 就 47 个（`loadLevel` / `toggleTree` / `goto` / `goUp` / `goPage` / `loadInbox` / `refreshInboxBadge` / `gotoInbox` / `ensureFlatFolders` / `loadAskCounts` / `openAsk` / `clearAsk` / `runAsk` / `togglePick` / `openAction` / `placeInto` / `placeIntoNew` / `acceptSuggestions` / `runReingest` / `removeDocs` / `runOps` / `afterAction` / `runMkdir` / `runRename` / `runMove` / `runCopy` / `runAdd` / `runRemove` / `runFolderDelete` / `loadCcsSummary` / `runCcsBackfill` / `runCcsBackfillAll` / `stopCcsBackfill` / `openUpload` / `runUpload` / `runCheck` …）。
- 页壳在文件里**手写了 4 遍**：`<div className="ks-page">` 出现 5 次、`<div className="ks-kb">` 5 次、`<KsTopTabs` 4 次、`className="ks-page-head"` 4 次、`className="ks-page-rule"` 4 次、`className="ks-page-title"` 4 次、`className="ks-page-sub"` 4 次。四处代码块（`page === 'capabilities'` / `'materials'` / `'channels'` / 知识库本页）逐字重复这 7 行外壳，只有标题与副标题不同（2048–2094 行可直接看到其中三段）。
- 面包屑也是**手写的一份**：`className="ks-crumb"` 从 3073 行到 3160 行（约 88 行），而同一份结构在 `kbListUi.tsx` 里已经被抽成 `KsCrumb`（55 行小文件）。`kbListUi.tsx` 头注自己写着「KsKnowledgePage 迁到本共用件 = 下一小批（登记）」——**没做**。`KsKnowledgePage.tsx:294` 只 import 了 `KsListHead`，没 import `KsCrumb`。

#### `api.ts`（206,812 字节 / 5,011 行）

不是"接口层"，是**112 个各自手写 fetch + 各自手写错误处理**的集合：

- `export async function` **112 个**，`await fetch(` **104 处**。
- **`if (!res.ok)` 出现 80 次**，其中 16 处的后续三行逐字相同：`let body: unknown = null / try { body = await res.json() } catch { /* non-JSON body */ } / const data = dataOf(body)`。
- 已有的统一解包器 `ksJson`（`async function ksJson<T>(res, what)`，第 2944 行）**只有 25 处使用**；另有 `engineErrorMessage` 27 处、`dataOf` 多处、`parseInspectionError`、`InspectionHttpError`、`KsIngestHttpError` 各自为政。
- **401 处理逐字重复 40 次**：`throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')` 共 40 处（`if (res.status === 401)` 共 42 处），每一处前面都手写 `clearSession()`。
- 引擎直连 URL `http://127.0.0.1:${port}/…` 出现 **46 处**，路径各自硬编码（见第八节）。
- 解包信封有三种并存：`{code,data}`（`dataOf`）、`{ok,data}`（`ksJson`）、`{ok,settings}` / `{ok,...rest}`（设置与巡检那几个手写）。

#### `KsEvidenceTab.tsx`（139,311 字节 / 2,834 行）

一个组件承担了整个 PDF 阅读器：**35 个 `useState`、35 个 `useCallback`、39 个 `useRef`、13 个 `useEffect`**。

- 35 个 `useCallback`：`renderPage` / `paintVisiblePages` / `refForPage` / `registerPageCanvas` / `measureNow` / `scheduleMeasure` / `applyAutoZoom` / `applyManualZoom` / `goTo` / `pushHistory` / `jumpHistory` / `syncTocAnchor` / `tocJump` / `toggleToc` / `loadEvidence` / `refreshMeta` / `loadFolders` / `openLeftCol` / `closeLeftCol` / `pickFolder` / `pickNewFolder` / `closeFolderPicker` / `clauseBookmark` / `confirmClauseBookmark` / `toggleDocBookmark` / `confirmDocBookmark` / `onBookmarkJump` / `jumpToBookmark` / `onFilesOpenDoc` / `freezeRender` / `paintSignature` / `retry` / `setPagingModeAndSync` / `toggleZoomMenu` / `applyAutoZoom`。
- **单页 / 连续两套 JSX 几乎逐字重复**：2107–2169（单页）与 2171–2226（连续）两段各有一份 `<KsArrowOverlay ref={bboxRef} />` + `<KsSiblingArrowsOverlay ref={siblingBoxesRef} />` + `{siblingArrowRects.map((r, i) => (<div key=… style={{ position:'absolute', left, top, width, height, pointerEvents:'none', backgroundImage: siblingArrowBg, backgroundRepeat:'no-repeat', backgroundSize:'100% 100%' }} />))}` —— 除 `key` 前缀（`sib-` vs `sib-c-`）外逐字相同。
- 组件内还内嵌了 `KsDocTextView` / `KsFilesView` / `KsBookmarksView` / 标题目录 / 缩放菜单 / 底部工具栏，等于 5 个界面合体。

#### `ksGuideStyles.ts`（101,355 字节 / 1,135 行）

**整份就是一个模板字符串**：`export const KS_STYLES = \`` 从 27 行到 1110 行（约 1,083 行 CSS）。

- 302 条 CSS 规则、270 个 `ks-` 类名。
- 单段最大：`/* ---------- 列表容器 + **真表格** ----------` 从 359 行到 940 行，**581 行**——一张表格的样式占了整个文件的一半。
- 有 6 个选择器**在同一份样式表里定义了两次**：`.ks-list`、`.ks-list-inbox`、`.ks-page-head`、`.ks-page .ks-page-sub`、`.ks-list .ks-cell.ks-col-date,.ks-list .ks-cell.ks-col-stage`、`.ks-list .ks-cell.ks-col-idest`。
- `smoke-ui-scale.mjs` 的棘轮**只扫这个文件**（`const stylesPath = join(pluginRoot, 'client', 'ksGuideStyles.ts')`），`tsx` 里的字面量完全不在射程内（见 D 节）。

#### `KsSettingsSection.tsx`（80,133 字节 / 1,636 行）

一个文件里装了 **7 个互不相关的面板组件**：`AnnounceTriageSection` / `ChangeSignalsSection` / `KsCategory` / `KsSettingsSection` / `KsInspectionPanel` / `KsAnnounceSourcesSection` / `KsApiConfigSection`，每个都自带 `useState` + `load` + 错误态。**48 个 `useState`** 在一个文件里，其中 8 组是 `[data, setData]` + `[err, setErr]` + `[loading, setLoading]` 三件套的复制。

#### `KsMaterialsPanel.tsx`（73,759 字节 / 1,409 行）/ `KsChannelsPanel.tsx`（50,743 字节 / 905 行）

- `KsMaterialsPanel` 里有 `AnchorMark` / `AnchorNoteLine` / `Deliverables` / `draftReducer`（5 个 action 纯函数）等 15 个导出，等于"面板 + 状态机 + 小组件库"合体；**24 个 `useState`**。
- `KsChannelsPanel` 里 13 个纯函数导出（`describeWhen` / `needsAttention` / `sortChannels` / `parseSegments` / `filterChannels` / `generateNewsLine` / `groupRowsBySite` / `groupRowsByOrgKind` / `buildChannelFixPrompt` / `copyTextToClipboard` …），这些是**可单测的纯逻辑**，却住在 `.tsx` 里。

---

## 四、plugin/scripts 分组与重复

### 4.1 按功能分组（56 个 `.mjs`）

**① 引擎守卫 / 生命周期（7）**
`smoke-engine-guard.mjs`、`smoke-lifecycle.mjs`、`smoke-cancel.mjs`、`smoke-build-purity.mjs`、`smoke-settings-guard.mjs`、`smoke-bbox-degenerate.mjs`、`smoke-compliance-sentry.mjs`

**② 界面渲染（jsdom / 真浏览器）（14）**
`smoke-settings.mjs`、`smoke-pdf-fit.mjs`、`smoke-pdf-panel.mjs`、`smoke-kb-page-render.mjs`、`smoke-kb-cols.mjs`、`smoke-kb-pad-pixels.mjs`、`ui-badge-pixels.mjs`、`ui-render-shot.mjs`、`smoke-anchor-mark.mjs`、`smoke-evidence-prefs.mjs`、`smoke-evidence-warn.mjs`、`smoke-turn-tab.mjs`、`smoke-materials-rows.mjs`、`smoke-icon-system.mjs`

**③ 路由契约（`/ks/*` 同源面）（10）**
`smoke-channels-routes.mjs`、`smoke-materials-routes.mjs`、`smoke-report-routes.mjs`、`smoke-turn-routes.mjs`、`smoke-ingest.mjs`、`smoke-docimage.mjs`、`smoke-collect-ui.mjs`、`smoke-report-ui.mjs`、`smoke-draft-ui.mjs`、`smoke-catalog-ui.mjs`

**④ 工具契约（6 个模型工具）（7）**
`smoke-tool-contract.mjs`、`smoke-effect-tool.mjs`、`smoke-wire-contract.mjs`、`smoke-tool-catalog.mjs`、`smoke-tool-concurrency.mjs`、`smoke-materials-tool.mjs`、`smoke-collect-tool.mjs`

**⑤ 端到端（真宿主 / CDP）（3）**
`e2e-install-compose.mjs`、`e2e-materials-panel.mjs`、`e2e-sidebar-pdf.mjs`

**⑥ 构建纯净性（2）**
`smoke-build-purity.mjs`、`build-client.mjs`

**⑦ 真机验证（需 DSH 检出根）（2）**
`verify-tools-real.mjs`、`verify-commands-real.mjs`（+ 包装器 `run-verify-commands.mjs`）

**⑧ 离线纯逻辑回归（9）**
`smoke-chatmode.mjs`、`smoke-trim.mjs`、`smoke-sanitize.mjs`、`smoke-class-summary.mjs`、`smoke-channels-ai.mjs`、`smoke-ui-scale.mjs`、`ui-audit.mjs`、`ui-token-check.mjs`、`smoke-settings-guard.mjs`

**⑨ 基础设施（3）**
`smoke-all.mjs`（唯一入口，44 套）、`gate-lock.mjs`（门禁锁）、`lib/` 4 个（`external-allowlist.mjs` / `ks-primitives-stub.mjs` / `tool-contract.mjs` / `cap-cards-check.mjs`）

### 4.2 同一件事有多个脚本在验（重复覆盖）

| 被验对象 | 在验的脚本 | 证据 |
|---|---|---|
| **`/ks/materials/*` 12 条路由** | `smoke-materials-routes.mjs`（56 处路径字面量）、`smoke-materials-rows.mjs`（7）、`smoke-kb-page-render.mjs`（6）、`e2e-materials-panel.mjs`（8） | `Select-String -Pattern '/ks/materials' -AllMatches` 计数 |
| **`/ks/channels*`** | `smoke-channels-routes.mjs`（8）、`ui-render-shot.mjs`（5）、`smoke-channels-ai.mjs`（1）、`smoke-kb-pad-pixels.mjs`（1） | 同上 |
| **6 个模型工具** | `smoke-tool-contract.mjs`、`smoke-effect-tool.mjs`、`smoke-wire-contract.mjs`、`verify-tools-real.mjs` **四个脚本都覆盖全部 6 个工具** | `Select-String -Pattern 'ks_ping|ks_resolve_clause|ks_answer|ks_effect_report|ks_materials|ks_collect'` 六个名字在四个文件里全出现 |
| **`/ks/session`** | `smoke-kb-page-render.mjs`、`smoke-settings-guard.mjs`、`ui-render-shot.mjs` | 各 1 处 |
| **`/ks/report/*`** | `smoke-report-routes.mjs`（11）、`smoke-report-ui.mjs`（5）、`smoke-kb-page-render.mjs`（2）、`smoke-materials-routes.mjs`（1） | 同上 |
| **`client.js` 产物新鲜度** | `smoke-client-entry.mjs`（整份逐字符比对）、`smoke-build-purity.mjs`（现构建 + 允许清单）、`e2e-materials-panel.mjs`（重构建后 reload） | `smoke-client-entry.mjs` 第 824 行段落的「整份一致」断言 |
| **图标体系** | `smoke-icon-system.mjs`（声明 ↔ 调用双向）、`ui-render-shot.mjs`（真渲染尺寸） | `smoke-icon-system.mjs:20` 注释自己写明分工 |
| **列对齐 / 像素留边** | `smoke-kb-cols.mjs` 与 `smoke-kb-pad-pixels.mjs` **都 spawn `ui-render-shot.mjs`** 再判 | `const shotScript = join(here, 'ui-render-shot.mjs')` 在两个文件里各出现一次 |
| **尺度 token 棘轮** | `smoke-ui-scale.mjs`（机械计数）、`ui-audit.mjs`（人工口径审计） | 两个都扫 `ksGuideStyles.ts` |

### 4.3 脚本里重复出现的辅助函数

**① `check()` —— 40 个脚本各定义一份，38 份**逐字相同**：**

```js
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}
```

计数：`Select-String -Path *.mjs -Pattern "function check\("` → **40 个文件**；其中含 `results.push({ name, ok })` 这一行的 → **38 个文件**。剩下 2 个是变体：

- `smoke-channels-ai.mjs`：`function check(name, cond, detail = '')`，用 `passed += 1` / `failed += 1` 计数而不是数组。
- `smoke-settings-guard.mjs`：`results.push({ name, ok, detail })`（多存了 `detail`）。

**② `const results = []` —— 41 个文件各声明一份**（`^const results = \[\]`）。其中 `e2e-materials-panel.mjs` / `e2e-sidebar-pdf.mjs` 声明了但没用 `check()`。

**③ 收尾模板 —— 39 个文件逐字相同：**

```js
const failed = results.filter((r) => !r.ok)
```

其中 26 个再跟 `process.exit(failed.length === 0 ? 0 : 1)`；另 2 个用 `const failedChecks = results.filter(...)`（`smoke-chatmode.mjs`、另一个）。

**④ 假引擎 HTTP server —— 8 处 `createServer`，散在 7 个文件：**

`e2e-install-compose.mjs`（engine + gateway 两个）、`smoke-channels-routes.mjs`、`smoke-collect-tool.mjs`、`smoke-materials-routes.mjs`、`smoke-materials-tool.mjs`、`smoke-report-routes.mjs`、`smoke-wire-contract.mjs`。每份都自己写 `createServer((req,res) => …)` + `await new Promise((r) => server.listen(0, '127.0.0.1', r))`。

**⑤ 假路由派发器（exact/prefix 两张表）—— 3 个文件各写一份：**

`smoke-channels-routes.mjs`（12 处 `exactRoutes`/`prefixRoutes`）、`smoke-turn-routes.mjs`（7 处）、`smoke-tool-contract.mjs`（3 处）。`smoke-turn-routes.mjs` 的注释直接写着「与真派发器同构的两张表 + 假 req/res（**同 smoke-channels-routes 的形状**）」——即作者知道这是抄的。

**⑥ `sleep()` —— 4 个文件各写一份：** `announce.js:229`、`engine.js:328`、`ingest.js:454`、`inspection.js:258`（宿主侧）；脚本侧另有几份（未逐个计数）。

---

## 五、重复实现清单

以下每条都能指回具体文件与可搜索文字。

### 5.1 宿主侧（`plugin/src/`）

| # | 重复的东西 | 副本数 | 位置（可搜索文字） |
|---|---|---|---|
| S1 | `jsonResponse(res, status, body)` 私有拷贝 | **5** | `announce.js:457` / `chatmode.js:1262` / `ingest.js:62` / `inspection.js:548` / `settings.js:35`；另有 `route_util.js:34` 的共享版与 `trust.js:51` 的同名不同形版 |
| S2 | `errorBody(code, message)` 私有拷贝 | **4** | `announce.js:462` / `ingest.js:67` / `inspection.js:553` / `settings.js:40`；共享版 `route_util.js:40` |
| S3 | `readJsonBody(req)` 私有拷贝 | **5** | `announce.js:466` / `chatmode.js:1271` / `ingest.js:71` / `inspection.js:558` / `settings.js:50`；共享版 `route_util.js:55`。**`BODY_CAP` 有三个取值**：4096（chatmode）/ 16384（settings）/ 65536（其余） |
| S4 | `pickQuery(reqUrl, allowed)` 私有拷贝 | **2** | `ingest.js:133` / `route_util.js:102`（共享版） |
| S5 | `engineRequest(method, base, path, opts)` 通用引擎请求 | **3** | `announce.js:502` / `channels.js:73` / `settings.js:85`（`channels.js:68` 注释自认「这是**第三份** `engineRequest`」） |
| S6 | `engineGetWithRetry(manager, path)` / `engineCall` / 401 自愈 | **5** | `ingest.js:95`、`ingest.js:108`（POST 版）、`report.js:64`、`materials_routes.js:48`（`engineCall`），加 `index.js` 内联的 `get`（`makeEffectReportTool`）与 `call`（`registerKsBboxRoute`） |
| S7 | `mapProbe` 私有拷贝 | **1** | `settings.js:113`（共享版 `route_util.js:132`；`route_util.js:126` 注释明写「`settings.js` 并不共用…这是同一判据的第二份实现」） |
| S8 | 「401 → 重读会话重试一次」 | **13 处** | `docimage.js:121/127`、`index.js:743/750/1021/1356/1363/1530/1536`、`ingest.js:98/110`、`materials_routes.js:54`、`report.js:68` |
| S9 | 状态文件 + 内存态 + `_persistChain` + `stale_run` + `defaultState` + `loadStateFile` + `sanitizeLast` + `update(fn)` + `stopPoll` + `sleep` + `adopt*` + `run*PollLoop` | **3 套近乎同构** | `announce.js`（`_persistChain:101`、`defaultState:105`、`loadStateFile:116`、`sanitizeLast:133`、`schedulePersist:196`、`update:211`、`stopPoll:224`、`sleep:229`、`adoptScanPoll:234`、`runScanPoll:241`）、`inspection.js`（`_persistChain:132`、`defaultState:134`、`loadStateFile:144`、`sanitizeLast:165`、`schedulePersist:217`、`update:231`、`stopPoll`、`sleep:258`、`adoptBatch`、`runPollLoop:265`）、`ingest.js`（`_jobPersistChain:365`、`defaultJobState:371`、`sanitizeJobLast:375`、`loadJobStateFile:391`、`persistJobState:415`、`updateJobState:422`、`stopJobPoll:429`、`sleep:454`、`adoptJob:434`、`runJobPollLoop:458`）。三套的 `while` 循环里都有 `manager.touchActivity()` + `stall` 计数 + `stale_run = true` 收尾 |
| S10 | 「引擎生成 xlsx → `/export/download` 取字节 → `Content-Disposition: attachment` 回传」 | **3 份** | `announce.js:727+740+751`、`report.js:177+197+208`、`inspection.js:800+820+833`（三处的 `Content-Disposition` 行逐字相同） |
| S11 | `fetchBinary(base, path, opts)` 私有拷贝 | **2** | `announce.js:531`、`inspection.js:738`（`announce.js:530` 注释自认「同 inspection.js fetchBinary 模式」） |
| S12 | `readBodyOr400(req, res)` 私有拷贝，**且返回哨兵值不一致** | **2** | `channels.js:136` 返回 `null`；`materials_routes.js:86` 返回 `undefined`。**`channels.js:295` 判的是 `if (raw === undefined) return`** —— 而该函数永远返回 `null`，所以 `POST /channels/{id}/test-case` 的**非法 JSON 分支不会 return**，会把 `null` 当 body 转给引擎 |
| S13 | `sanitizeLast` 同名不同义 | 2 | `inspection.js:165`（批次：batch_id/status/counts/by_type/by_class）vs `announce.js:133`（扫描：scan_id/per_source/recent） |
| S14 | 内联 405 响应体（不用 `errorBody`） | **3** | `index.js:1470`、`index.js:1510`、`index.js:1517` 手写 `res.writeHead(...); res.end(JSON.stringify({ ok:false, error:{code:'method_not_allowed'…}}))` |
| S15 | 证据锚点 URL 构造器 | **2** | `index.js:169 evidenceAnchor` vs `client/ksEvidence.ts:177 evidenceUrlOf`（`index.js:151` 注释自认「必须与 client 半同口径」） |
| S16 | 证据锚点路径常量 | **2** | `index.js:146 KS_EVIDENCE_PATH = '/__ks_evidence__'` vs `ksEvidence.ts:61 EVIDENCE_PATH = '/__ks_evidence__'` |
| S17 | pdf worker / wasm 路径常量 | **2 对** | `index.js:135/136 KS_PDF_WORKER_PATH / KS_PDF_WASM_PATH` vs `pdf-configure.ts:37/41 PDF_WORKER_PATH / PDF_WASM_DIR` |
| S18 | 可空 JSON schema 字面量 `{ oneOf: [{type:'string'},{type:'null'}] }` | **3 份定义** | `index.js:418 NULLABLE_STRING`、`materials.js:53 NULLABLE_STRING`、`collect.js` 内联同形 |

### 5.2 客户端（`plugin/client/`）

| # | 重复的东西 | 副本数 | 位置 |
|---|---|---|---|
| C1 | 「401 → 清会话 → 抛 `EngineAuthError`」 | **40 处逐字相同** | `api.ts` 内 `throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')` 40 次 |
| C2 | `withSession` 401 自愈包装器 | **2 份独立实现** | `KsKnowledgePage.tsx:601`、`KsBookmarksTab.tsx:153`（另 `KsFilesTab.tsx:82`、`KsEvidenceTab.tsx` 里 8 处内联同构） |
| C3 | `instanceof EngineAuthError` 重试分支 | **14 处** | `KsEvidenceTab`（8）、`KsBookmarksTab`（2）、`KsFilesTab`（2）、`KsDocTextView`（1）、`KsKnowledgePage`（1） |
| C4 | `fetchSession(...)` 调用点 | **39 处** | `KsEvidenceTab`（18）、`api.ts`（8）、`KsBookmarksTab`（5）、`KsFilesTab`（4）、`KsDocTextView`（2）、`KsKnowledgePage`（2） |
| C5 | 「`if (!res.ok)` + 手写 JSON 解包」 | **80 处** | `api.ts`；其中 16 处后续三行逐字相同 |
| C6 | `$center` 样式常量（`display:flex / alignItems:center / justifyContent:center / height:100% / minHeight:160`） | **3 份逐字相同** | `KsBookmarksTab.tsx:582`、`KsEvidenceTab.tsx:2534`、`KsFilesTab.tsx:522` |
| C7 | 按钮样式常量 | **3 份近似** | `KsEvidenceTab.tsx:2542 $btnStyle`、`KsBookmarksTab.tsx:590 $btn`、`KsMaterialsPanel.tsx:99 function btnStyle(disabled)` —— 前两个的 `border`/`background`/`color`/`borderRadius`/`cursor` 五行逐字相同，只有 `padding` 与 `fontSize` 不同 |
| C8 | 局部 `$xxx: React.CSSProperties` 样式常量 | **79 个** | `KsFilesTab.tsx`（32）、`KsEvidenceTab.tsx`（31）、`KsBookmarksTab.tsx`（10）、`KsChannelsPanel.tsx`（4）、`KsDocTextView.tsx`（2） |
| C9 | 跨文件逐字相同的内联 style 对象 | **15 组**（`count ≥ 2`） | `color: 'var(--dsw-alias-label-secondary, #666)'` 11 次跨 4 文件；`cursor: 'pointer'` 11 次跨 3 文件；`fontWeight: 600, color: 'var(--dsw-alias-label-primary, #111)'` 7 次跨 4 文件；`margin: '0 0 4px'` 5 次跨 2 文件 |
| C10 | 内联 `fontSize: <数字>` 字面量 | **230 处** | `KsSettingsSection`（65）、`KsMaterialsPanel`（51）、`KsCapabilityPage`（33）、`KsEvidenceTab`（23）、`KsFilesTab`（19）、`KsBookmarksTab`（18）、`KsTurnTab`（12）等 |
| C11 | 页壳（`.ks-page > .ks-kb > KsTopTabs + .ks-page-head + .ks-page-rule + 内容`） | **4 份手写** | `KsKnowledgePage.tsx` 2048 / 2069 / 2087 / 3021 附近 |
| C12 | 面包屑 JSX（`.ks-crumb` / `.ks-crumb-path` / `.ks-crumb-item` / `.ks-crumb-sep` / `.ks-crumb-go` / `.ks-crumb-here`） | **2 份** | `kbListUi.tsx:20 KsCrumb` vs `KsKnowledgePage.tsx:3073–3160` 手写版 |
| C13 | 单页 / 连续两套箭头覆盖 JSX | **2 份** | `KsEvidenceTab.tsx:2107–2169` 与 `2171–2226` |
| C14 | 「loading + error + 重试」三件套 | **至少 6 个组件各写一遍** | 见 D 节 |
| C15 | 偏好 key 常量 | **2 份逐字相同** | `ksPrefs.ts:31/32 KS_SETTINGS_PREFS_KEY='ks:settings' / KS_SHOW_ARROW_KEY='showArrow'` vs `KsSettingsSection.tsx:109/110` 同值 |
| C16 | 文件内嵌纯逻辑（本可单测） | `KsChannelsPanel` 10 个纯函数、`KsMaterialsPanel` 8 个（含 `draftReducer` 5 个 action） | 见第三节 |

---

## 六、命名不一致清单

| 类别 | 不一致 | 证据 |
|---|---|---|
| **工具名** | 前缀统一 `ks_`，但动词词性不齐：`ks_ping`（动作）/ `ks_answer`（动作）/ `ks_resolve_clause`（动作+名）/ `ks_effect_report`（名）/ `ks_materials`（名）/ `ks_collect`（动作） | `collect.js:99`、`index.js:630/846/934/1101`、`materials.js:85` |
| **工具 `description` 语言** | 5 个中文、1 个英文（`ks_answer` 的 `KS_ANSWER_DETAIL` 全英文 2156 字） | `tool-details.js:14` |
| **宿主路由前缀** | `/ks/*`（49 条）；但证据锚点是 `/__ks_evidence__`（双下划线，不是 `/ks/`） | `index.js:146` |
| **引擎路由前缀** | 绝大多数 `/api/v1/*`；但 `/api/v1` 内部又分 `update/` / `report/` / `materials/` / `kb/` / `laws/` / `settings/` / `channels/` / `documents/` / `clauses/` / `ingest/` 十个域，且 `update` 域里 `announce-*` 与 `batch/`、`check`、`changes`、`report-xlsx` 混排 | 第八节 |
| **返回信封** | **四种并存**：`{ok:true, data}`（route_util `mapProbe`、announce、channels、ingest、turn）、`{ok:true, <扁平键>}`（`settings.js:117 { ok:true, ...rest }`、`inspection.js:705 { ok:true, batch_id, status }`、`inspection.js:848 { ok:true, settings }`）、`{ok:true, found, spans}`（`index.js:1542/1572`）、`{ok:true, degraded, …}`（`ingest.js:219/224`） | `Select-String -Pattern "\{ ok: true, data|ok: true, \.\.\.|\{ ok: true, found|\{ ok: true, [a-z_]+:"` |
| **错误码风格** | `engine_unavailable` / `engine_error` / `engine_write_failed` / `engine_bad_response` / `download_failed` / `ks_engine_unavailable` / `ks_bbox_unavailable` / `batch_not_found` / `method_not_allowed` / `bad_request` / `not_found` / `invalid_params` —— 有 `ks_` 前缀的（2 个）与没有的混用 | `index.js:1486/1578`、`report.js`、`inspection.js:806`、`route_util.js:142` |
| **成功标志** | 宿主一律 `ok:true`；引擎信封用 `code:200`（`collect.js:245`、`compliance-sentry.js:211`、`index.js:765/805`、`materials.js:297`）；`chatmode.js` 的命令返回用 `kind:'success'`（8 处） | 三套并存 |
| **参数命名（引擎侧）** | `snake_case`：`project_id` / `material_id` / `folder_id` / `doc_id` / `standard_no` / `query_mode` / `kb_folder_ids` | `api.ts` 里 361 处 snake_case 字段 |
| **参数命名（TS 侧）** | `camelCase`：`projectId` / `materialId` / `folderId` / `docId` / `batchId` / `jobId` / `channelId` / `sessionId` | `api.ts` 里 934 处 camelCase 字段；同一文件两种并存 |
| **路由路径命名** | 名词单复数不齐：`/ks/materials/tier`（单）vs `/ks/materials/tiers`（复）——**两条都是真路由**，前者是"改一份的层级"，后者是"取层级定义清单"；`/ks/report/effect` vs `/ks/report/effect/docs` vs `/ks/report/export`（同一功能三种命名法） | `materials_routes.js:280/370`、`report.js:34/35/36` |
| **文件名 vs 导出名** | `KsFilesTab.tsx` 导出 `KsFilesView`；`KsBookmarksTab.tsx` 导出 `KsBookmarksView` —— 文件名说 Tab、导出说 View | `KsFilesTab.tsx:63`、`KsBookmarksTab.tsx:83` |
| **常量前缀** | 宿主侧 `KS_*_PATH`（49 个中的 36 个）+ `ENGINE_*_PATH`（16 个，其中 `materials_routes.js` 用 `ENGINE_MATERIALS` 不带 `_PATH` 后缀）；`engine.js` 用 `HEALTH_PATH` / `KS_ANSWER_PATH`（**无 `KS_` 前缀**） | `engine.js:69/71` |
| **disposer 契约** | 多数 `register*Routes` 返回单个函数；`channels.js:326 registerKsChannelsRoutes` 返回**数组**；`announce.js:619 registerSourcesRoutes` 返回单个但内部手动 for 循环释放数组 | `index.js:1880` 因此要写 `for (const d of disposeChannels) d()`，与其余 14 个不同 |
| **文件级常量命名** | `route_util.js` 用 `ROUTE_BODY_CAP`；`chatmode.js` 用 `BODY_CAP`（4096）；`settings.js` 用 `BODY_CAP`（16384） | 同名不同值 |
| **`stale_run` 语义** | 三个模块同名同形（`{ last, stale_run }`），但 `last` 的键完全不同 | `announce.js:108` / `inspection.js:139` / `ingest.js:372` |
| **状态文件名** | `ks-announce.json` / `ks-inspection.json` / `ks-ingest.json` / `ks-chatmode.json` —— 统一 `ks-<模块>.json`，但 `chatmode` 额外支持 `KS_CHATMODE_DIR` 与 `KS_DATA_DIR` 两个环境变量覆盖，其余三个没有 | `chatmode.js:92/93` vs `announce.js:80` / `inspection.js:59` / `ingest.js:361` |
| **`readBodyOr400` 哨兵值** | `channels.js` 返回 `null`，`materials_routes.js` 返回 `undefined` | 见 S12 |
| **斜杠命令命名** | `/forensic`（英文）/ `/bookmarks`（英文）/ `/materials`（英文）—— 与工具名 `ks_materials` 不同名 | `chatmode.js:1005/1007/1009` |

---

## 七、垃圾 / 死代码清单

### 7.1 `plugin/src/*.bak-*` 四个备份文件

| 文件 | 字节 / 行 | 与当前版本差异 | git 状态 | 被引用吗 |
|---|---|---|---|---|
| `compliance-sentry.js.bak-20260927-003328-before-v4-source` | 15,701 / 273 | 与 `compliance-sentry.js` 差 **1 行**：`source: { kind: 'plugin', plugin: 'ks-dsh-plugin' }` → `source: { kind: 'plugin:ks-dsh-plugin' }` | **未跟踪**（`git status --short` 显示 `??`） | 否（`Select-String -Pattern "\.bak-"` 在 src/scripts/client 全部 0 命中） |
| `compliance-sentry.js.bak-20260927-003346-before-v4-source` | 15,701 / 273 | 与上面**哈希完全相同**（`11FD39B8…AE3918`） | 未跟踪 | 否 |
| `tool-details.js.bak-20260927-003346-before-v4-source` | 4,234 / 67 | 与 `tool-details.js` 差 3 行注释 + 同一行 `source` 字段 | 未跟踪 | 否 |
| `tool-details.js.bak-20260927-003530-before-v4-source` | 4,234 / 67 | 与上面**哈希完全相同**（`7F43DCF7…D3005`） | 未跟踪 | 否 |

**结论**：它们是 2026-09-27 那次 "v4 source 字段" 迁移前的临时备份，**两两成对重复**（每对内容完全相同），没有被任何代码或脚本引用。`.gitignore` **没有**忽略它们（`git check-ignore` 退出码 1），所以它们会一直显示为未跟踪文件。

### 7.2 `plugin/client.js`（1,784,273 字节）

- **被 git 跟踪**：`git ls-files plugin/client.js` 有输出；HEAD 里的 blob 大小 1,784,273 与工作区一致；`git status --short plugin/client.js` 为空（干净）。
- **应该跟踪吗**：仓库自己的答案是"应该"，而且有**真断言**守着：`smoke-client-entry.mjs` 从源码现构建一份到临时文件（`KS_CLIENT_OUT`），与交付的 `client.js` **逐字符比对**（行尾归一化后），不一致就红。注释原文：「改了 `.tsx` 忘了重新构建 ⇒ 产物是旧的 ⇒ 也全绿…这里把**整份产物**与现构建逐字符对比…于是"忘重建"与"产物被手改"这两类都变成**一条真断言**」。
- **当前的陈旧风险**：`git log -1 -- plugin/client.js` = `dbfa7f74 Mon Oct 12 23:15:25 2026`；同一提交也改了 `KsEvidenceTab.tsx` / `KsScopeChip.tsx` / `KsTurnTab.tsx`。但 `KsKnowledgePage.tsx` 的**工作区 mtime 是 2026-10-21 22:16:44**，晚于 `client.js` 的 2026-10-21 12:10:17，而 `git diff --stat -- plugin/client/KsKnowledgePage.tsx` 为空（内容与 HEAD 一致）⇒ **mtime 新但内容没变**，不构成陈旧。工作区里真正被改的只有 `plugin/client/api.ts`（+1 行注释）和 `plugin/src/index.js`（超时 120s→300s），两处都不影响产物语义（前者是注释，后者是宿主侧）。**是否真的新鲜，本次未跑 `smoke-client-entry.mjs`，不宣称已验证。**

### 7.3 `plugin/.tmp-purity-probe/` 与 `plugin/.tmp/`

| 目录 | 内容 | git 状态 |
|---|---|---|
| `.tmp-purity-probe/` | 4 个文件：`probe.mjs`(3,078) / `backslash-error.mjs`(1,095) / `shape-reconcile.mjs`(1,197) / `legit.js`(23)。都是"纯度门禁"取证用的一次性探针（`probe.mjs` 头注：「一次性探针（复核 corr3 A1 的取证）」） | **被忽略**：`.gitignore:44` 的 `.tmp-*` 命中（`git check-ignore -v` 输出 `.gitignore:44:.tmp-*`） |
| `.tmp/` | **空目录**（`Get-ChildItem -Force -Recurse` → 0 项） | 未被跟踪；**也没有被忽略**（`git check-ignore plugin/.tmp/probe.mjs` 退出码 1）⇒ 谁往里放文件就会变成未跟踪垃圾 |

### 7.4 `plugin/client/TASK-pdf-bottom-bar.md`（6,185 字节）

一份**任务交接书**混进了源码目录：

- 标题「# 任务交接：PDF 阅读器 —— 默认瀑布式 + 底部常驻工具栏」，交接时间 2026-09-16。
- 里面写着「目标仓库：`D:\AI\work space\zcode`」——**旧绝对路径**，与当前工作目录不符。
- 内容包含 §5「待用户确认的一个问题」、§6「不要碰的东西（另一条线，正在运行）」（OCR 循环）——是给"下一个会话"看的，不是给仓库用的。
- **被 git 跟踪**：`git ls-files plugin/client/TASK-pdf-bottom-bar.md` 有输出；最后一次提交 2026-09-17。
- **同类东西还有多少**：`Get-ChildItem plugin,src,tests,scripts -Recurse -File -Include *.md`（排除 node_modules）→ 只有 4 个 `.md`：`plugin/client/TASK-pdf-bottom-bar.md`（这份）、`plugin/README.md`（正常）、`tests/fixtures/rental-contract.md`（测试夹具）、`scripts/verify-seeds/README.md`（正常）。**即：只有这一份是误入源码目录的交接书**。

### 7.5 无人引用的导出 / 文件

| 对象 | 判定 | 证据 |
|---|---|---|
| `client/KsPdfGuideIcon.tsx`（1,861 字节） | **完全孤立** | `Select-String -Pattern "from './KsPdfGuideIcon'"` → 0；脚本里 0 命中；只有 `KsKnowledgeGuideIcon.tsx:11` 的一句"约定照 `KsPdfGuideIcon`"提到它 |
| `client/ksSearchSyntax.ts`（4,241 字节） | 只被**冒烟**用 | `Select-String -Pattern 'ksSearchSyntax'` → 只有 `smoke-client-entry.mjs:944` 的动态 import |
| `src/KS_INGEST_JOB_STATUS_PREFIX` / `KS_INGEST_JOB_ABORT_PREFIX` | **导出但零引用** | `ingest.js:44/45` 定义；全仓 grep 各只有 1 处（定义行本身）。实际路由拼接在 `ingest.js:715` 用 `tail.endsWith('/abort')` 手写，没用这两个常量 |
| `client/api.ts` 的 `deleteBookmark` / `moveClauseBookmark` / `moveDocBookmark` / `fetchEffectReport` / `fetchEffectDocs` / `fetchKbCcsPlan` | **无任何调用者**（tsx 与 scripts 都是 0） | `Select-String` 在 `*.tsx`/`*.ts`（排除 api.ts 自身）与 `scripts/*.mjs` 全部 0 命中 |
| `src/index.js` 的 `KS_EVIDENCE_PATH` | 只在**同文件**内用一次（`evidenceAnchor` 里），导出但无人 import | 全仓 1 处使用 |
| `src/materials_routes.js` 的 `KS_MATERIALS_PATHS` | 只给冒烟用 | 全仓 3 处：定义 + `smoke-materials-routes.mjs` 的 import 与断言 |
| `src/inspection.js` 的 `__resetInspectionForTests` / `chatmode.js` 的 `__resetChatModeForTests` / `__writeStateFileAsPeerForTests` | 只给冒烟用 | 各自只在对应 `smoke-*.mjs` 里出现 |
| `src/engine.js` 的 `dataRoot` / `parseSession` | 只在本文件内用（`sessionFilePath` / `readSessionFile`） | 导出但无跨文件 import |
| `src/route_util.js` 的 `mapProbe` 第三/第四参数 | 只有 `materials_routes.js` 用默认值 | 无人传 `engineErrorStatus` 或 `pick` |

### 7.6 注释里的失效引用

- `src/tool-details.js:10`、`collect.js:101`、`index.js:848`、`materials.js:87` 共 4 处引用 `var/tmp/desc-before-*.txt` 作为"原文留档"。**这些文件不存在**：`Get-ChildItem -Recurse -Filter "desc-before-*"` 全仓 0 命中，`git ls-files "var/tmp/desc-before-*"` 也为空。
- `index.js:1-18` 的文件头仍写「Registers **three** model-facing tools」并只列 3 个，实际注册 6 个。
- `client/KsEvidenceTab.tsx` 文件头仍写「better-sidebar's link interception claims it」，而 `entry.ts` 头注说明 better-sidebar **已从 profile 移除**。
- `client/KsEvidenceHost.tsx` 头注写「`KsEvidenceTab` 是 1600+ 行的成熟实现」，实际 2,834 行。

---

## 八、引擎端点调用清单

### 8.1 宿主侧（`plugin/src/`）调用的引擎端点

统计口径：`Select-String -Pattern "'/api/v1[^']*'"` + 模板字符串 `\`/api/v1` 逐个读上下文，再按方法/路径组合去重。**共 56 行（不同方法+路径组合）；把同一路径的不同方法合并计，约 40 个路径。**

| # | 方法 | 路径 | 调用文件 |
|---|---|---|---|
| 1 | GET | `/api/v1/health` | `engine.js:69`（常量）、`index.js:897` |
| 2 | POST | `/api/v1/ks/answer` | `engine.js:71`（常量）、`index.js:1345` |
| 3 | GET | `/api/v1/clauses/resolve?standard_no=…` | `index.js:1012` |
| 4 | GET | `/api/v1/clauses/{rev}/spans` | `index.js:1524` |
| 5 | GET | `/api/v1/report/effect` | `index.js:760`、`report.js:41` |
| 6 | GET | `/api/v1/report/effect/color?color=red,yellow&…` | `index.js:804` |
| 7 | GET | `/api/v1/report/effect/docs` | `report.js:42` |
| 8 | POST | `/api/v1/report/effect/export` | `report.js:43`、`report.js:177` |
| 9 | POST | `/api/v1/report/research` | `report.js:44`、`report.js:270` |
| 10 | POST | `/api/v1/report/research/draft` | `report.js:45`、`report.js:330` |
| 11 | GET | `/api/v1/export/download?name=…` | `announce.js:74/740`、`report.js:46/197`、`inspection.js:822` |
| 12 | GET | `/api/v1/update/announce-scan/last` | `announce.js:69` |
| 13 | GET | `/api/v1/update/announce-items?limit=5` | `announce.js:298` |
| 14 | POST | `/api/v1/update/announce-scan` | `announce.js:68` |
| 15 | GET/POST | `/api/v1/update/announce-sources` | `announce.js:70` |
| 16 | PUT/DELETE | `/api/v1/update/announce-sources/{id}` | `announce.js:70` + `enginePath` |
| 17 | POST | `/api/v1/update/announce-export` | `announce.js:71` |
| 18 | POST | `/api/v1/update/announce-ingest` | `announce.js:72` |
| 19 | GET | `/api/v1/update/announce-ingest/pending` | `announce.js:73` |
| 20 | POST/GET | `/api/v1/update/announce-ingest/triage` | `announce.js:60` |
| 21 | GET | `/api/v1/laws/change-signals` | `announce.js:61` |
| 22 | GET/POST | `/api/v1/channels` | `channels.js:43` |
| 23 | PATCH/DELETE | `/api/v1/channels/{id}` | `channels.js:43` + `engineId` |
| 24 | POST | `/api/v1/channels/{id}/enabled` | `channels.js`（`engineId` + `/enabled`） |
| 25 | POST | `/api/v1/channels/probe` | `channels.js:44` |
| 26 | GET/POST | `/api/v1/channels/{id}/test-case` | `channels.js`（`engineId` + `/test-case`） |
| 27 | POST | `/api/v1/channels/{id}/test` | `channels.js`（`engineId` + `/test`） |
| 28 | POST | `/api/v1/laws/compliance-guard` | `compliance-sentry.js:209` |
| 29 | GET | `/api/v1/documents/{id}/figure/{no}` | `docimage.js:58` |
| 30 | GET | `/api/v1/documents/{id}/formula/{fno}?clause=…` | `docimage.js:65` |
| 31 | GET | `/api/v1/documents/{id}/table-image/{page}/{tbl}` | `docimage.js:73` |
| 32 | POST | `/api/v1/ingest/preview` | `ingest.js:48` |
| 33 | POST | `/api/v1/ingest/preview/batch` | `ingest.js:49` |
| 34 | GET | `/api/v1/ingest/preview/inbox` | `ingest.js:47` |
| 35 | POST | `/api/v1/ingest/preview/jobs` | `ingest.js:631` |
| 36 | GET | `/api/v1/ingest/preview/jobs/{id}` | `ingest.js:50` |
| 37 | POST | `/api/v1/ingest/preview/jobs/{id}/abort` | `ingest.js:721` |
| 38 | GET | `/api/v1/update/batch/{id}` | `inspection.js:315/1029` |
| 39 | GET | `/api/v1/update/changes?batch_id=…` | `inspection.js:386` |
| 40 | POST | `/api/v1/update/check` | `inspection.js:650` |
| 41 | POST | `/api/v1/update/report-xlsx/{batch_id}` | `inspection.js:802` |
| 42 | GET/POST | `/api/v1/materials/projects` | `materials.js:199`、`materials_routes.js:111/119` |
| 43 | GET | `/api/v1/materials/projects/{id}/materials` | `materials.js:240`、`materials_routes.js:138` |
| 44 | GET | `/api/v1/materials/projects/{id}/inbox` | `materials.js:217`、`materials_routes.js:156` |
| 45 | POST | `/api/v1/materials/projects/{id}/scan` | `materials_routes.js:176` |
| 46 | POST | `/api/v1/materials/projects/{id}/collect` | `materials_routes.js:229`、`collect.js:226` |
| 47 | POST | `/api/v1/materials/{id}/review` | `materials_routes.js:265` |
| 48 | POST | `/api/v1/materials/{id}/tier` | `materials_routes.js:304` |
| 49 | POST | `/api/v1/materials/{id}/role` | `materials_routes.js:342` |
| 50 | GET | `/api/v1/materials/{id}/chunks` | `materials_routes.js:361` |
| 51 | GET | `/api/v1/materials/tiers` | `materials_routes.js:373` |
| 52 | GET | `/api/v1/materials/{id}/locators` | `materials_routes.js:394` |
| 53 | GET | `/api/v1/materials/projects/{id}/locators` | `materials_routes.js:399` |
| 54 | POST | `/api/v1/materials/{id}/reverify` | `materials_routes.js:425` |
| 55 | GET/PUT | `/api/v1/settings/api-config` | `settings.js:32` |
| 56 | POST | `/api/v1/settings/api-config/test` | `settings.js:225` |

> 注：上表按"方法 + 引擎路径"计 56 行；把同一路径的不同方法合并计，约 40 个路径（`materials` 域 12 条、`update` 域 10 条、`channels` 域 6 条是主要来源）。

### 8.2 客户端（`plugin/client/api.ts`）**直连**的引擎端点

客户端持有 Bearer token，有 **46 处** `http://127.0.0.1:${port}/…` 直连（绕过宿主代理）。**不同路径 41 个**：

| 路径族 | 具体路径 |
|---|---|
| 文档 | `GET /api/v1/documents/{id}/file`、`GET /api/v1/documents/{id}/clauses`、`GET /api/v1/documents/{id}/tree`、`GET /api/v1/documents/categories`、`GET /api/v1/documents`、`POST /api/v1/documents/batch-delete` |
| 收藏（条款） | `GET/POST /api/v1/bookmarks`、`DELETE /api/v1/bookmarks/{id}`、`DELETE /api/v1/bookmarks/by-clause/{clauseKey}` |
| 收藏（文档） | `GET/POST /api/v1/doc-bookmarks`、`DELETE /api/v1/doc-bookmarks/by-doc/{docId}` |
| 收藏夹 | `GET/POST /api/v1/bookmark-folders`、`GET /api/v1/bookmark-folders/tree`、`PATCH/DELETE /api/v1/bookmark-folders/{id}`、`POST /api/v1/bookmark-folders/move-clause`、`POST /api/v1/bookmark-folders/move-doc` |
| 条款 | `GET /api/v1/clauses/{rev}/meta` |
| 条款补丁 | `GET/POST /api/v1/clauses/patches`、`DELETE /api/v1/clauses/patches/{patchId}` |
| 导出 | `GET /api/v1/export/download?name=…` |
| 外发审计 | `GET /api/v1/egress/audit` |
| 合规 | `POST /api/v1/compliance/policies`、`POST /api/v1/compliance/gap-analysis` |
| 问答 | `POST /api/v1/ks/answer` |
| 知识库 | `GET/POST /api/v1/kb/folders`、`GET /api/v1/kb/folders/{id}/items`、`GET /api/v1/kb/folders/flat`、`GET /api/v1/kb/folders/{id}/delete-preview`、`POST /api/v1/kb/members`、`GET /api/v1/kb/inbox`、`POST /api/v1/kb/inbox/confirm`、`POST /api/v1/kb/inbox/reingest`、`GET /api/v1/kb/inbox/reingest/status`、`GET /api/v1/kb/stage-labels`、`GET /api/v1/kb/ccs/summary`、`GET /api/v1/kb/ccs/plan`、`POST /api/v1/kb/ccs/backfill`、`GET /api/v1/kb/ccs/backfill/status`、`POST /api/v1/kb/ccs/backfill/cancel`、`POST /api/v1/kb/scope/resolve`（`resolveKbScope`） |
| 批量导入 | `POST /api/v1/ingest/bulk`、`POST /api/v1/ingest/bulk/{id}/resume`、`GET /api/v1/ingest/bulk/{id}` |

### 8.3 端点覆盖的三个问题

**（a）写了但没人调**（宿主侧）：本次统计**没有**发现"定义了 ENGINE_* 常量却完全不用"的情况——16 个 `ENGINE_*` 常量逐个查过 call site，全部 ≥1 处真实调用（见 S5 那张表）。

**（b）只有一边调、另一边没有**：客户端直连的 41 个路径里，**`/api/v1/kb/*`（16 条）、`/api/v1/bookmarks*`（6 条）、`/api/v1/doc-bookmarks*`（2 条）、`/api/v1/documents*`（6 条）、`/api/v1/clauses/patches*`（3 条）、`/api/v1/egress/audit`、`/api/v1/compliance/*`（2 条）、`/api/v1/ingest/bulk*`（3 条）全部是客户端直连**，宿主侧 `src/` 对这些路径的引用数为 **0**（`Select-String -Pattern 'kb/folders'|'doc-bookmarks'|'clauses/patches'|'ingest/bulk'|'kb/ccs'` 在 `src/*.js` 全 0 命中）。即：**40 个引擎端点走宿主代理，41 个走浏览器直连**，两套信任模型并存。

**（c）宿主有路由但客户端没消费者**：`/ks/compliance/ping` 的消费者是 `KsScopeChip.tsx:56`（一处）；`/ks/bbox` 消费者是 `api.ts:408`（一处）；`/ks/assets/pdf-wasm` 消费者是 `pdf-configure.ts:41`（一处）；`/ks/materials/*` 的 12 条里，`chunks` / `locators` / `reverify` 各只有 1–2 个消费者。**没有发现"宿主注册了路由但全仓无消费者"的情况**——45 个 `/ks/*` 路径逐个查过 `client/*.ts,*.tsx`，全部 ≥2 处命中。

---

## 九、我没搞清楚的

1. **`ksSearchSyntax.ts` 到底该不该存在**：它是纯函数（`+`=AND、`-`=NOT），但**只有冒烟 import 它**，没有任何界面组件用它。头注说「用户界面上要**当场显示解析结果**」——那个界面**没找到**。`KsKnowledgePage` 的搜索框（`needle` 状态）走的是 `kbListUi` 那套过滤，不是它。**未读**：没有逐行读 `KsKnowledgePage` 的 3,868 行全文，无法排除"某个条件分支里用了"（已用 grep 确认全仓只有 `smoke-client-entry.mjs` 一处引用，但那是动态 import 字符串，理论上运行时也可能被别处 eval——本仓无此机制）。

2. **`KsPdfGuideIcon.tsx` 是不是真的死文件**：全仓 grep 只在 `KsKnowledgeGuideIcon.tsx:11` 的一句注释里出现。但它是 2026-09-17 提交的，而 `ksSidebar.ts:292` 用的是 `KsKnowledgeGuideIcon`——可能是"旧图标被新图标取代但没删"。**未读**：没有查 git log 确认它是否曾被 import 后又被替换。

3. **`channels.js:295` 那个 `raw === undefined` 判据是不是真 bug**：`readBodyOr400`（`channels.js:136`）在失败时 `return null`，而 `channels.js:295` 判的是 `if (raw === undefined) return`。按静态阅读，非法 JSON 时会走 `proxyWrite(..., null)` 把 `null` 转给引擎。**但**：`proxyWrite` 里 `body: null` 会被 `JSON.stringify(null)` 成 `"null"` 发出去，引擎大概率 422 拒掉——所以"用户看不出区别"可能是真，也可能被引擎兜住。**未跑冒烟验证**（`smoke-channels-routes.mjs` 只覆盖了合法 body 的转发，第 224–233 行）。

4. **`client.js` 当前是否新鲜**：`smoke-client-entry.mjs` 有一条"整份逐字符一致"的真断言，但**本次没跑**（任务边界禁止跑冒烟）。静态线索是：工作区只改了 `api.ts` 一行注释与 `index.js` 两处超时，都不改产物；`KsKnowledgePage.tsx` mtime 新于 `client.js` 但 `git diff` 为空。**结论：未验证**。

5. **`ui-render-shot.mjs`（328,807 字节 / 4,517 行）的内部结构**：它是脚本里最大的一个（比 `smoke-kb-page-render.mjs` 还大），被 `smoke-kb-cols.mjs` 与 `smoke-kb-pad-pixels.mjs` 当子进程调用。**未读**：只读了文件头、`STUB` 段与 `createServer` 相关段落，没有逐段摸清它的场景矩阵与断言分组。原因：任务是"脚本不用逐个细读"，而它不属于任何一组的核心。

6. **`KsEvidenceTab` 的 2,834 行里还有多少可抽的纯函数**：只数了 hooks（35 useState / 35 useCallback / 39 useRef / 13 useEffect）与两处 JSX 重复，**没有**逐函数判断"哪些可以搬到 `.ts` 里单测"。原因：那需要读完全文并逐个评估副作用，超出本次"摸结构 + 找重复"的范围。

7. **`plugin/node_modules/` 里的实际依赖树**：按任务要求没看。所以"`@deepseek-ai/*` 到底装了哪些"只能从 `package.json` 的 `peerDependencies`（4 个）与 `dependencies`（2 个）推断，没有实测。

8. **`smoke-all.mjs` 名单之外的 12 个脚本谁在跑**：`build-client.mjs`（构建）、`gate-lock.mjs`（被 import）、`run-verify-commands.mjs`（包装器）、`smoke-all.mjs`（入口）、3 个 `e2e-*`、2 个 `verify-*`、`ui-audit.mjs`、`ui-token-check.mjs`、`ui-render-shot.mjs`（被 2 个冒烟 spawn）。其中 `ui-audit.mjs` / `ui-token-check.mjs` **没有任何脚本调用**，也没进链——它们靠人手跑。是否还有别的入口（如 `scripts/run-gates.ps1`）调用它们，**未读**（那个文件不在 `plugin/` 下，本次任务边界是 `plugin/`）。
