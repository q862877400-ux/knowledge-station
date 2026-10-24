# plugin/client 事实地图

调查对象：`D:\Agent-Studio\Deepseek-Harness\DSH-Data\workspace\zcode\plugin\client\`。
目录里共 **33 个文件**：31 个代码文件（`.ts` / `.tsx`）+ `TASK-pdf-bottom-bar.md` + `tsconfig.json`。
本轮只读，未修改任何源文件。
（`git status` 里 `plugin/client/api.ts` 显示为已修改：那是**本轮之前**就存在的未提交改动——mtime `2026-10-08 18:10`，内容只是 `api.ts:2178` 一行 JSDoc 把"上限 50"改成"数量不设上限"，与本次调查无关，也没影响下文任何计数。）

## 统计口径（先对齐，否则数字对不上）

任务书给的行数我逐文件核对过，它们是**非空行数**（`Get-Content | Measure-Object -Line` 不数空行）：

```
cd plugin/client
foreach ($f in 'api.ts','KsKnowledgePage.tsx','KsEvidenceTab.tsx','ksGuideStyles.ts') {
  (Get-Content $f | Measure-Object -Line).Lines }
=> api.ts 4725 / KsKnowledgePage.tsx 3715 / KsEvidenceTab.tsx 2695 / ksGuideStyles.ts 1113
```

同一批文件的**实际行数**（`\n` 计数，`read` 工具报的就是它）分别是 5011 / 3868 / 2834 / 1135。
下文表格两列都给：`非空/实际`。31 个文件合计：**21,926 非空行 / 23,193 实际行**（空行 1,267）。

读的深度（诚实分档，详见 §七）：

- **整份读完**：`entry.ts`、`kbListUi.tsx`、`ksEvidence.ts`、`ks-evidence-props.ts`、`KsEvidenceHost.tsx`、`KsArrowOverlay.tsx`、`KsKnowledgeGuide.tsx`、`KsAnchorWarn.tsx`、`pdf-configure.ts`（共 9 个）。
- **读了关键窗口 + 机械枚举全部导出/端点**：`api.ts`（约 1,100 行窗口 + 全量导出/端点/重复统计算）、`KsKnowledgePage.tsx`（约 600 行窗口 + 全量 hook/页壳/面包屑统计）、`KsEvidenceTab.tsx`（约 1,000 行窗口 + 全量纯函数枚举）、其余 5 个中文件读了文件头 + 挂载点 + 结构 grep。
- 未逐行读的都在 §七 点名。

---

## 一、31 个文件逐个职责（表格）

按非空行数从大到小。列「测试」用四档（与 §6.2 同一套判定）：**行为**（脚本真打包/真渲染该模块并断言它自己的导出）、**结构**（只在源码文本上 grep 或被计数）、**间接**（没有直接断言，只被别的模块 import 进去打包）、**零接触**（连包都不进）。

| # | 文件 | 行数 非空/实际 | 这个界面是干什么的（用户视角） | 谁挂载它 | 调哪些后端 | 测试 |
|---|---|---|---|---|---|---|
| 1 | `api.ts` | 4725 / 5011 | **不是界面**，是全前端的取数层：117 个导出函数 = 知识库/材料/渠道/巡检/公告/收藏/证据/办事台九大块的 HTTP 调用 | 被 11 个组件 import（见二） | 同源 `/ks/*` + 跨源 `127.0.0.1:<port>/api/v1/*`（见二） | **间接**（`smoke-kb-page-render` 等把它打包进去做桩，无自己的断言） |
| 2 | `KsKnowledgePage.tsx` | 3715 / 3868 | **知识库主页面**：左边目录树逐级展开、右边列目录/文件、勾选后批量挪/复制/删、上传文件、「待分类」层处置、在此目录内提问、补全分类号 | `entry.ts`（`sidebar.right.pane.tab` key=`ks-knowledge`）；页内 `params.page` 分发 manage/capabilities/ingest/materials/channels | `/api/v1/kb/*`（folders/items/members/inbox/ccs/stage-labels/scope/resolve）、`/api/v1/ingest/bulk*`、`/api/v1/ks/answer`、`/api/v1/documents*`、`/ks/ingest/preview/batch` | **行为**（`smoke-kb-page-render.mjs`：jsdom 真挂载，文件名 90 处引用） |
| 3 | `KsEvidenceTab.tsx` | 2695 / 2834 | **PDF 证据查看器**：渲染原文页、画红色定位箭头（含同轮其他条款的半透明箭头）、左侧三模式目录列（标题/文件/收藏）、翻页缩放、收藏条款/文档 | `KsEvidenceHost.tsx` ← `entry.ts`（key=`ks-evidence`） | `/ks/session`、`127.0.0.1/api/v1/documents/{id}/file`、`/bookmarks`、`/doc-bookmarks`、`/clauses/{rev}/meta`、`/documents/{id}/tree`、`/bookmark-folders`、`/ks/bbox` | **行为**（`smoke-evidence-prefs` 打包宿主+tab 链路）；另有 `smoke-catalog-ui` 结构判据 |
| 4 | `KsSettingsSection.tsx` | 1558 / 1636 | **设置栏目**（DSH 设置里的一级栏目）：红箭头开关 + API 配置（云 OCR / LLM 凭据）+ 每日巡检 / 公告发现 / 公告入库 / 变更信号 等折叠组（原「入库预览」组已撤，见 `KsSettingsSection.tsx:409-419`） | `entry.ts`（`settings.section`，order 101） | `/ks/inspection/*`、`/ks/announce/*`、`/ks/settings/api-config*` | **行为**（`smoke-settings.mjs`：esbuild 打包 + `react-dom/server` SSR，三份类目集合互比） |
| 5 | `KsMaterialsPanel.tsx` | 1344 / 1409 | **备料（参考资料）面板**：建项目、扫收件箱、逐份看正文切片、批准/拒绝、设来源层级与任务内效力、锚点健康度、导出研究报告 | `KsKnowledgePage`（`page='materials'`，传 `embedded`）；也能单独挂 | `/ks/materials/*`、`/ks/report/research*`、`/api/v1/export/download` | **行为**（`smoke-catalog-ui` 打包并钉 `deliverableKind`/`folderOf` 纯函数；`smoke-materials-rows`） |
| 6 | `ksGuideStyles.ts` | 1113 / 1135 | **不是界面**：一整段 `KS_STYLES` CSS 模板串（`:root` 的 `--ks-*` 尺度 token + 551 处 `.ks-*` 类）由 `ensureKsStyles()` 注入 `<style>`；宿主只加载 `client.js`，故样式必须由 JS 带进去 | 各面板 `import { ensureKsStyles }` 后调用 | 无（纯 CSS 字符串） | **行为**（`smoke-ui-scale.mjs` 棘轮 + `smoke-client-entry`） |
| 7 | `KsChannelsPanel.tsx` | 863 / 905 | **渠道台账**：一个来源一行，显示「接线/有效性/上次成功」三列（**刻意不合并**），可探测、可试抓、可启停删除；顶部常驻最新动态与巡检摘要 | `KsKnowledgePage`（`page='channels'`） | `/ks/channels*`、`/ks/announce/summary`、`/ks/inspection/summary` | **行为**（`smoke-catalog-ui` 打包；`smoke-channels-ai`） |
| 8 | `KsFilesTab.tsx` | 739 / 805 | **文件目录视图**（PDF 查看器左列第二模式）：4 级缩进树 + 搜索 + 多选批量删除 | `KsEvidenceTab`（`leftMode==='files'`） | `/api/v1/documents/categories`、`/documents`（平铺）、`/documents/batch-delete` | **行为**（`smoke-catalog-ui` 钉 `countDocs`） |
| 9 | `KsBookmarksTab.tsx` | 641 / 687 | **收藏目录视图**（左列第三模式）：收藏夹树 → 收藏文档 → 条款级收藏；每夹可「💡 夹内提问」、改名、删除、新建 | `KsEvidenceTab`（`leftMode==='bookmarks'`） | `/api/v1/bookmark-folders/tree`、`/bookmark-folders*`、`/ks/chat-mode` | **结构**（只在 `smoke-client-entry` 的"写死颜色基线表"里被计数，无行为断言） |
| 10 | `KsTurnTab.tsx` | 568 / 593 | **「本轮」依据页**：这轮回答引用了哪几条、核对结果、点「看原文」跳到 PDF 对应页+箭头 | `entry.ts`（key=`ks-turn`）；回答完成后由 `entry.ts` 的 3s 轮询自动切达 | `GET /ks/turn/last?session=…` | **行为**（`smoke-turn-tab` 打包并 SSR `KsTurnEvidenceRow`/`KsTurnEmptyState`） |
| 11 | `KsIngestPanel.tsx` | 540 / 571 | **逐篇只读体检面板**：列待入库 PDF、抽样预览出 ✅/⚠️/❌ 三桶、点一行看该文件的分级/裁决/样例/版面指标 | `KsKnowledgePage` 上传区的「逐篇看」（`KsKnowledgePage.tsx:3272`）；`ui-render-shot` 独立渲染 | `/ks/ingest/*`（inbox / preview / preview/batch / jobs） | **结构**（`smoke-settings` 反向钉它**不在**设置源码里）+ `ui-render-shot`（未进门禁） |
| 12 | `entry.ts` | 475 / 509 | **客户端入口**（cordis `apply/inject`）：注册设置栏目、输入坞胶囊、右侧栏三类 tab（证据/知识库/本轮）+ 开始页卡；装两条 document 级点击拦截 | DSH client loader（`/plugins/ks-dsh-plugin/client.js`） | `/ks/session`（经 api）、`/ks/turn/last` 轮询（3s，`setInterval`） | **行为**（`smoke-client-entry` 打包 + 用假 ctx 跑 `apply`，39 处引用） |
| 13 | `KsCapabilityPage.tsx` | 432 / 464 | **办事台**：三行菜单（制度差距分析 / 纠错修订 / 外发审计），点进各自专门页面；未接线的一律灰+「还没有」 | `KsKnowledgePage`（`page='capabilities'`，传 `embedded`） | `/api/v1/egress/audit`、`/api/v1/compliance/*`、`/api/v1/clauses/patches*` | **间接**（被 `smoke-kb-page-render` 经 KsKnowledgePage 打包并点到；`ui-render-shot` 独立截图） |
| 14 | `ksSidebar.ts` | 381 / 419 | **不是界面**：KS 与官方右侧栏的唯一适配层——tab 类型定义（kind/地址/标题）、`params.page` 分发类型、`toNavParams` 换算 | `entry.ts` | 无 | **间接**（脚本从不点名它，只经 `entry.ts` 进包） |
| 15 | `KsDocTextView.tsx` | 374 / 393 | **正文视图**（证据查看器的「📄 正文」模式）：条款富文本 + 图/表/公式经同源代理回填；渲染前过结构白名单消毒 | `KsEvidenceTab`（`viewMode==='text'`） | `/api/v1/documents/{id}/clauses`、`/ks/doc-image/*` | **结构**（`smoke-sanitize` **复刻**了同一算法，不 import 真模块） |
| 16 | `ksHostPrimitives.d.ts` | 272 / 286 | **不是界面**：宿主 `@deepseek-ai/dsh-client-ui-primitives` 的 `declare module` 最小面声明（运行时是真货，类型上自持） | 各组件类型检查 | 无 | **零接触**（环境声明，编译期擦除） |
| 17 | `pdfFit.ts` | 242 / 259 | **不是界面**：PDF 缩放规则纯函数（宽度铺满、10%~500% 钳制、滑块档位、后备位图 dpr 预算） | `KsEvidenceTab` | 无 | **行为**（`smoke-pdf-fit.mjs` 单独打包逐个断言） |
| 18 | `ksEvidence.ts` | 210 / 229 | **不是界面**：证据锚点 URL 契约——`parseEvidence` / `evidenceUrlOf` / `isBbox`（编解码 doc/page/bbox/bboxPage/rev/also） | `entry.ts`、`KsEvidenceTab`、`KsBookmarksTab`、`KsTurnTab` | 无 | **间接**（`smoke-turn-tab` 经 `turnEvidenceHref` 断言同一契约；`smoke-effect-tool` 只在注释里对照） |
| 19 | `pdfPanel.ts` | 173 / 188 | **不是界面**：打开 PDF 时把侧栏拉宽、关闭时恢复的协调器（模块级 Map 按会话记账；端口缺席即静默降级） | `KsEvidenceTab` | 无 | **行为**（`smoke-pdf-panel.mjs` 打包 `client/pdfPanel.ts` 断言） |
| 20 | `KsScopeChip.tsx` | 146 / 154 | **输入框上方的范围胶囊**：「🔖 夹名 · 仅在本收藏夹内提问 ✕」；未激活时不占行；另发合规哨兵 ping（不显示任何东西） | `entry.ts`（`conversation.input.dock`） | `GET/PUT /ks/chat-mode`、`POST /ks/compliance/ping` | **结构**（`smoke-compliance-sentry` 读源码钉"界面不显示徽章"+"ping 仍在"） |
| 21 | `KsEvidenceHost.tsx` | 133 / 143 | **不是界面**：官方 `sidebar.right.pane.tab` 座位与 `KsEvidenceTab` 之间的适配层（`useTabInfo()`+`navigation.params` → 旧 props；`prefs.showArrow` 走 `ksPrefs` 订阅） | `entry.ts`（key=`ks-evidence`） | 无（只转发） | **行为**（`smoke-evidence-prefs` 打包它 + 桩 tab，判 `data-showarrow`） |
| 22 | `ksPrefs.ts` | 98 / 110 | **不是界面**：`localStorage` 里的偏好（当前只有 `showArrow`），可订阅 + 跟 `storage` 事件同步 | `KsSettingsSection`、`KsEvidenceHost` | 无（本地存储） | **行为**（`smoke-evidence-prefs` 打包真模块，改值重渲染必须跟着变） |
| 23 | `ksSearchSyntax.ts` | 98 / 107 | **不是界面**：检索语法纯函数——`+`=与、`-`=屏蔽；标准号里的 `-`（`GB 30871-2022`）不拆；全角符号先归一化 | `KsKnowledgePage`（`smoke-client-entry` 也打包） | 无 | **行为**（`smoke-client-entry` 打包 `parseKsQuery`/`describeKsQuery` 逐例断言） |
| 24 | `ks-evidence-props.ts` | 80 / 86 | **不是界面**：证据 tab 的 props 契约（`KsEvidenceProps`）与**可选**的面板宽度端口 `KsPanelWidthPort` | `KsEvidenceHost`、`KsEvidenceTab` | 无 | **零接触**（`import type`，编译期擦除） |
| 25 | `pdf-configure.ts` | 66 / 70 | **不是界面**：pdf.js worker 接线（`GlobalWorkerOptions.workerSrc` → `/ks/assets/pdf.worker.min.mjs`），幂等 | `KsEvidenceTab` | `/ks/assets/pdf.worker.min.mjs`、`/ks/assets/pdf-wasm/` | **间接**（脚本零引用，只随 `KsEvidenceTab` 进包） |
| 26 | `KsArrowOverlay.tsx` | 62 / 69 | 红箭头覆盖层本体（主箭头 + 同轮其他条款的半透明箭头 0.35），几何由 `renderPage` 每帧写 style | `KsEvidenceTab` | 无 | **行为**（`smoke-turn-tab` 打包 `arrowBackground`；`smoke-evidence-warn` 3 处） |
| 27 | `KsKnowledgeGuide.tsx` | 55 / 62 | 右侧栏**开始页**上「知识库」那张卡（整卡点一下直进知识库管理） | `entry.ts`（`sidebar.right.tab.guide.entry`） | 无 | **结构**（`smoke-kb-page-render.mjs:2629` 读源码，但路径写死成 `D:/AI/...`） |
| 28 | `kbListUi.tsx` | 52 / 55 | **不是界面**：知识库列表机制的共用件——`KsCrumb`（面包屑）+ `KsListHead`（题头行）+ `KbListCol` | `KsChannelsPanel` 两个都用；`KsKnowledgePage` **只用 `KsListHead`** | 无 | **间接**（进包，但任何脚本都不点名 `KsCrumb`/`KsListHead`） |
| 29 | `KsPdfGuideIcon.tsx` | 47 / 49 | 开始页卡的 PDF 图标 SVG 组件 | **无人 import**（`plugin/client` 里没有 `from './KsPdfGuideIcon'`，见 §七） | 无 | **零接触** |
| 30 | `KsKnowledgeGuideIcon.tsx` | 41 / 44 | 开始页卡的知识库图标 SVG 组件 | `KsKnowledgeGuide`、`ksSidebar` | 无 | **间接** |
| 31 | `KsAnchorWarn.tsx` | 40 / 43 | 「引文位置没取到，这次只跳页不画箭头」的可见警示行（`role="alert"`），样式 token 与 `entry.ts` 的提示条共用 | `KsEvidenceTab` | 无 | **行为**（`smoke-evidence-warn` SSR 断言原因原文逐字出现 + 颜色走 token） |

---

## 二、`api.ts` 的组织结构 + 重复统计

### 2.1 按什么分段

**先按域，域内再按资源。** 文件里 20 条横线 banner 就是分段边界（`grep '^/\* -{5,}'`）。

| 行 | banner 标题 |
|---|---|
| 174 | 渠道台账（§11.0 R4b） |
| 448 | 端点接线：文档富文本 + 三图片端点 |
| 581 | Bookmarks（条款级收藏） |
| 822 | Doc bookmarks（标准级书签） |
| 938 | 收藏夹目录 |
| 1219 | 会话开关（查法规/仅收藏/收藏夹内提问） |
| 1298 | 文件目录（分类树 / 批量删除 / 平铺 / 标题树） |
| 1521 | 每日巡检 |
| 1602 | R27 入库预览 + 批量分桶 |
| 2035 | 公告发现 |
| 2239 | 公告正文入库 |
| 2307 | 两条只读出口（triage / change-signals） |
| 2475 | 效力报告 |
| 2624 | 义务清单 / 差距分析 |
| 2672 | 纠错修订（条款补丁） |
| 2789 | API 配置 |
| 2870 | 材料平面（Phase B） |
| 3177 | 引用锚点稳定性 |
| 3263 | 产出（Phase D-3b） |
| 3396 | 知识库多级目录（KB-FOLDER-PLAN） |

**分段是历史叠加的，不是一张设计过的表**：banner 从 2026-09-08 到 2026-10 陆续加；同一件事的两个面向被分到相隔 2000 行的两段（例如收藏在 581、收藏夹目录在 938；材料在 2870、产出在 3263）；`kbWrite`（3786）与 `ksJson`（2944）两个解包器都**长在中间**而不是文件头。

### 2.2 一共暴露多少函数、各调什么端点

- `export (async) function`：**117** 个（116 个在行首 + 1 个挤在 JSDoc 尾巴同一行：`api.ts:2422 */export async function ingestAnnouncements(`）。
  命令：`grep -c 'export (async )?function'` 会给 116，漏的就是这一条。
- `export interface|type`：105 个；`export class` 2 个（`EngineAuthError:441`、`InspectionHttpError:1916`）；`export const` 1 个（`DOC_IMAGE_NOT_FOUND:537`）。
- 非导出本地 helper：33 个（`normalize*` 16 个、`parse*Error` 2 个、`str/num/objOf/dataOf/intOf/qsOf` 6 个、`unwrapList`/`filenameFromDisposition`/`memberResult`/`reportBody`/`postReport`/`compliancePost`/`ksJson`/`kbWrite`/`engineErrorMessage` 9 个）。

端点分两族（这是全文件最重要的结构事实）：

| 族 | 宿主/引擎 | 鉴权 | 谁在用 | 端点形态 |
|---|---|---|---|---|
| A | 同源宿主路由 `/ks/*` | 宿主代持 token，前端从不经手 | 渠道、巡检、公告、效力报告、设置、材料、入库预览、会话开关、bbox、doc-image、产物下载 | `fetch('/ks/…')` |
| B | 跨源引擎 `http://127.0.0.1:<port>/api/v1/*` | 前端拿 `Bearer` 直连 | 收藏/书签/文档/知识库目录/CCS/合规/条款补丁/回答 | `fetch(\`http://127.0.0.1:${port}/api/v1/…\`)` |

B 族存在的原因是模板里写明的（`api.ts:4-21` 的 `SECURITY / TRUST` 段、`api.ts:176-182` 的渠道段注释）：探针会对外发请求必须留宿主；而文档字节、kb 目录这类高频只读走直连省一跳。

端点数量（对 `/api/v1/` 与 `/ks/` 两个字面量做 grep 后按路径去重）：

- A 族端点约 **24 个**：`/ks/session`、`/ks/bbox`、`/ks/doc-image/…`、`/ks/channels`(+`/:id`、`/enabled`、`/test-case`、`/test`、`/probe`)、`/ks/chat-mode`、`/ks/ingest/{inbox-default,inbox,preview,preview/batch,preview/jobs,preview/jobs/:id/abort}`、`/ks/inspection/{summary,run,settings,export}`、`/ks/announce/{summary,auto-ingest,scan,sources,sources/:id,export,ingest/pending,ingest/triage,ingest,change-signals}`、`/ks/report/{effect,effect/docs,export,research,research/draft}`、`/ks/settings/api-config`(+`/test`)、`/ks/materials/{projects,list,inbox,scan,collect,review,tier,role,chunks,tiers,locators,reverify}`。
- B 族端点约 **26 个**：`/api/v1/documents`(+`/categories`、`/batch-delete`、`/:id/tree`、`/:id/file`、`/:id/clauses`)、`/api/v1/clauses/:rev/meta`、`/api/v1/clauses/patches`(+`/:id`)、`/api/v1/bookmarks`(+`/:id`、`/by-clause/:key`)、`/api/v1/doc-bookmarks`(+`/by-doc/:id`)、`/api/v1/bookmark-folders`(+`/tree`、`/:id`、`/:id/move`、`/:id/copy`、`/move-clause`、`/move-doc`)、`/api/v1/export/download`、`/api/v1/egress/audit`、`/api/v1/compliance/{policies,gap-analysis,obligations}`、`/api/v1/kb/folders`(+`/:id/items`、`/:id/move`、`/:id/copy`、`/:id/delete-preview`、`/flat`)、`/api/v1/kb/members`(+`/remove`、`/move`、`/copy`)、`/api/v1/kb/inbox`(+`/confirm`、`/reingest`、`/reingest/status`)、`/api/v1/kb/ccs/{summary,plan,backfill,backfill/status,backfill/cancel}`、`/api/v1/kb/stage-labels`、`/api/v1/kb/scope/resolve`、`/api/v1/ks/answer`、`/api/v1/ingest/bulk`(+`/:id`、`/:id/resume`)。

### 2.3 `throw new EngineAuthError('引擎校验失败(401)，会话已轮换，请重试')` 出现几次

**40 处**，逐字相同（消息串、前置的 `clearSession()`、整个 `if (res.status === 401) { … }` 块都一样）：

```
Select-String plugin\client\api.ts -Pattern "throw new EngineAuthError\('引擎校验失败" | Measure-Object
=> Count : 40
```

行号（40 个）：

```
506  666  702  746  805  872  907  931 1064 1087
1112 1144 1172 1193 1214 1411 1440 1468 1509 3576
3619 3668 3800 3888 4084 4125 4161 4203 4452 4501
4559 4608 4627 4671 4706 4751 4841 4944 4970 4989
```

同一个字符串还有**第 41 处**，但抛的是普通 `Error`：

- `api.ts:113` `throw new Error('引擎校验失败(401)，会话已轮换，请重试')`（`fetchPdf`，唯一一处不是 `EngineAuthError` 的）。

401 分支总数：

```
grep -c 'if (res.status === 401)' => 42
```

42 = 40（抛 EngineAuthError）+ 1（`fetchPdf:111` 抛普通 Error）+ 1（`fetchExportBlob:164` **不抛**，清 session 后重试一次再判其他状态码）。

### 2.4 `if (!res.ok)` 出现几次、其中多少逐字相同

**80 处。** 逐处分类（`for` 循环把每处 `if (!res.ok)` 与它的下一行配对，再归类）：

| 后续处理 | 处数 | 是否逐字相同 |
|---|---|---|
| `throw await parseInspectionError(res)` | 23 | **全等** |
| `throw await parseIngestError(res)` | 7 | **全等** |
| `throw new Error(await engineErrorMessage(res, \`引擎返回 HTTP ${res.status}\`))` | 20 | **全等** |
| `throw new Error(\`引擎返回 HTTP ${res.status}\`)` | 8 | **全等** |
| `throw new Error(await engineErrorMessage(res, \`<各域自己的文案>\`))` | 5 | 各不同（2590/2653/2705/2730/2742） |
| `throw new Error(\`<各域自己的文案>(HTTP ${res.status})\`)` | 14 | 各不同（560/704/807/877/909/933/1066/1089/1117/1147/1174/1195/1216/1239） |
| 块状自定义逻辑（读 body 再抛） | 3 | 各不同（1272 `patchChatMode`、1470 `batchDeleteDocs`、4843 `askKsAnswer`） |

**逐字相同的 = 23+7+20+8 = 58 处 / 80（72.5%）**。
换句话说：这个文件里"HTTP 非 2xx 怎么处理"被**独立写了 6 种策略、80 次**，其中只有 58 次是复制粘贴。

### 2.5 有没有统一解包器（`ksJson`）？用了几次？哪些地方没用

**有一个，但它只管一族。** `ksJson` 定义在 `api.ts:2944`：

```ts
async function ksJson<T>(res: Response, what: string): Promise<T> {
  if (!res.ok) throw await parseInspectionError(res)
  const body = (await res.json().catch(() => null)) as { ok?: boolean; data?: T } | null
  if (body === null || body.ok !== true || body.data === undefined) throw new Error(`${what}响应异常`)
  return body.data
}
```

- 调用点 **24 处**（`grep -c 'ksJson<'` 给 25，含定义行；另有 2 行是注释里提到它）。
- 覆盖范围只有两族：`/ks/channels/*`（9 处：256/279/291/303/312/330/344/357/386）+ `/ks/materials/*`（14 处：2958/2978/2992/3005/3022/3079/3106/3128/3148/3164/3173/3229/3240/3260）+ `testApiChannel`（2945 附近）。
- **它自己是长在材料段中间的**（2944），而最早使用它的渠道段在 256 行 —— 靠函数声明提升才成立。

**没用它的地方**（这些函数各自手写 `res.ok` + `body.ok !== true` 检查）：

| 族 | 函数 | 手写判据 |
|---|---|---|
| `/ks/session` | `fetchSession` | `res.status === 200 && parsed.ok === true`（65） |
| `/ks/bbox` | `fetchBbox` | 同上（420） |
| `/ks/ingest/*`（7 个） | 全部 | `throw await parseIngestError(res)` + `body?.ok !== true`（1766…1911） |
| `/ks/inspection/*`（4 个） | 全部 | `throw await parseInspectionError(res)` + `body.ok !== true`（1947…2017） |
| `/ks/announce/*`（12 个） | 全部 | 同上（2115…2435） |
| `/ks/report/*`（3 个）+ `exportInspectionResult`（走 `/ks/inspection/export`） | `fetchEffectReport`/`fetchEffectDocs`/`exportEffectReport`/`exportInspectionResult` | 同上（2547/2755/2773/2017） |
| `/ks/settings/api-config`（2 个） | `fetchApiConfig`/`saveApiConfig` | 同上（2817/2841） |
| `/ks/chat-mode` | `patchChatMode` | 自带块状解析（1272） |
| B 族引擎直连（约 45 个） | 收藏/书签/文档/kb/ccs/ingest-bulk/answer | `throw new Error(await engineErrorMessage(...))` + `dataOf(body)`（19 处 `dataOf(body)`） |

`body.ok !== true` 手写 **19 次**（`grep -c 'body.ok !== true'`），`dataOf(body)` **19 次** —— 两组数字撞在一起不是巧合：它们就是 `ksJson` 应该统一掉的两件事。

**另外两处该合并没合并的**：

- `KsIngestHttpError`（`api.ts:1733`，未导出）与 `InspectionHttpError`（1916，导出）是**同一个类写了两遍**：字段、构造函数、`parse*Error` 逐行同构（1748-1759 vs 1927-1938）。
- 因为 `ksJson` 在 2945 行把错误解析委托给 `parseInspectionError`，**`/ks/channels/*` 与 `/ks/materials/*` 失败时抛出来的类名是 `InspectionHttpError`** —— 类名与调用方域不符（调用方 `KsMaterialsPanel` 捕获它时读的是 `.message`，功能没问题，但类型名在撒谎）。

---

## 三、`KsKnowledgePage` 的结构 + 手写了几遍页壳

### 3.1 页壳（`.ks-page` / `KsTopTabs` / `ks-page-head`）手写了几遍

**这个文件里手写了 5 遍 `.ks-page`，其中 4 遍是完整页壳**（标签条 + 页头 + 分隔线 + 内容）：

| 行 | 分支 | 有 `KsTopTabs` | 有 `ks-page-head` | 有 `ks-page-rule` | 内容 |
|---|---|---|---|---|---|
| 2049 | `page === 'capabilities'` | ✓（2051） | ✓（2052） | ✓（2056） | `<KsCapabilityPage embedded />` |
| 2070 | `page === 'materials'` | ✓（2072） | ✓（2073） | ✓（2077） | `<KsMaterialsPanel visible embedded />` |
| 2088 | `page === 'channels'` | ✓（2090） | ✓（2091） | ✓（2095） | `<KsChannelsPanel visible />` |
| 2110 | 其余未实现页 → 诚实占位 | ✗ | ✗ | ✗ | 「这一页尚未实现」 |
| 3022 | `manage`/`ingest`（主页面） | ✓（3024） | ✓（3025） | ✓（3042） | 目录树 + 列表 + 上传面板 |

`KsTopTabs` 自身定义在 219-245（4 个标签：知识库 / 渠道库 / 办事台 / 预览器），**被调用 4 次**（2051/2072/2090/3024），每次都是同一行字面值：

```jsx
<KsTopTabs page={page} onGo={(pp) => { setPageOverride(pp) }} onPdf={() => { tab.actions.openTab(KS_EVIDENCE_KIND) }} />
```

跨文件再算一遍更严重 —— 同一套外壳在**别的文件里还有 3 份**：

| 文件:行 | 形态 |
|---|---|
| `KsCapabilityPage.tsx:448` | `props.embedded === true` 时不渲染；否则自带 `.ks-page > .ks-kb > .ks-page-head > .ks-page-rule` |
| `KsMaterialsPanel.tsx:1247` | `if (props.embedded === true) return mat` 否则 `<div className="ks-page">{mat}</div>` |
| `KsIngestPanel.tsx:367` | **无条件**自带 `.ks-page > .ks-ing` |

合计：`className="ks-page"` **8 处 / 5 个文件**；`className="ks-page-head"` **5 处 / 2 个文件**；`ks-page-rule` **5 处 / 2 个文件**（第 6 处在 `ksGuideStyles.ts:154` 的 CSS 里）。命令：`grep -n 'className="ks-page"' plugin/client/*.tsx`。

**一处遗留的不一致（只报事实，不宣称可见后果）**：`KsKnowledgePage.tsx:3272` 把 `KsIngestPanel` 挂在自己的 `.ks-page > .ks-kb` 里面，而 `KsIngestPanel.tsx:367` 又无条件渲染一层 `.ks-page` ⇒ 真机 DOM 是 `.ks-page > .ks-kb > .ks-page > .ks-ing`。这正是 `KsKnowledgePage.tsx:2036-2047`（办事台）与 `2065-2068`（备料）两段注释里明确修掉的那种"两层 `.ks-page` 嵌套"，ingest 分支没跟着改。`ui-render-shot.mjs` 的 `#face` 断言只数四个面，所以没人报红。是否造成可见缩进差异我**没量**（不跑浏览器），只登记。

### 3.2 面包屑实现了多长？`KsCrumb` 已有，为什么没迁

- `KsKnowledgePage.tsx` 的面包屑：**3072-3160，共 89 行**（`<span className="ks-crumb">` 到 `</span>`），内含 `ks-crumb-path` / `ks-crumb-item` / `ks-crumb-sep` / `ks-crumb-here` / `ks-crumb-go` / `ks-crumb-n` 六种类名、3 个分支（最外层 / 「待分类」伪层 / 目录层逐段）。
- 共用件**已经存在**：`kbListUi.tsx:20-42` 的 `KsCrumb`，**23 行**，做的是同一件事（`items.map` + 兄弟分隔符 + `here`/`go` + 可选 `n`）。
- 已经有迁移先例：`KsChannelsPanel.tsx:31` `import { KsCrumb, KsListHead } from './kbListUi'`，`KsChannelsPanel.tsx:700` 用它渲染渠道台账的面包屑。`KsKnowledgePage.tsx:294` **只 import 了 `KsListHead`**，没用 `KsCrumb`。

为什么没迁过去 —— 文件里自己写着答案（`kbListUi.tsx:9`）：

> `KsKnowledgePage 迁到本共用件 = 下一小批（登记）。`

即**登记过、没做**。而 `KsCrumb` 缺的正是 `KsKnowledgePage` 那 89 行里多出来的三样东西（对照两处实现逐项核过）：

1. 每段的 `title` / `aria-label`（`"回到「X」这一级"`）—— `KsCrumb` 的 `onGo` 只给回调，不收文案；
2. 「待分类」这个**不属于库目录的伪层**（`KsKnowledgePage.tsx:3102-3116`）—— `KsCrumb` 的 `items` 是平铺数组，插一个伪层只能靠调用方拼假数据；
3. 计数文案带单位（`还没归位 N 篇` / `你在最外层` / `${subs.length} 个子目录 · ${filesTotal} 篇文件`）—— `KsCrumb` 只有 `${n} 条`（`kbListUi.tsx:39`）。

所以真实原因是"共用件只覆盖了 60% 的形态"，迁移要先给 `KsCrumb` 加 3 个能力（而不是简单替换）。另外 `KsKnowledgePage.tsx:3119-3121` 写明分隔符必须是条目的**兄弟**、`textContent` 只能是那一级的名字 —— 共用件已经是这个结构，这点不构成障碍。

### 3.3 hook 数量与最长函数

```
grep/正则计数（不含 import 行）：useState 51 / useEffect 4 / useCallback 38 / useMemo 7 / useRef 3
（把 import 语句一起数的朴素 grep 是 52 / 5 / 39 / 9 / 4）
```

最长函数：**`KsKnowledgePage` 组件本身 = 449→3868，3,419 行**（一个函数占了文件 88%）。
内部最长的是 `const runUpload = useCallback(...)`，**1830→1977，147 行**；其次 `loadLevel`（621-670，49 行）、`openAction`（1039-1086，47 行）。

---

## 四、`KsEvidenceTab` 的可抽纯函数

### 4.1 它渲染什么、几个子视图

`KsEvidenceTab`（`KsEvidenceTab.tsx:152-2498`，组件本体 2,346 行）是一个**三轴叠加**的界面：

| 轴 | 取值 | 状态变量 | 行 |
|---|---|---|---|
| 主视图 | `'pdf'`（原页渲染） / `'text'`（条款富文本） | `viewMode` | 1911 |
| 左列模式 | `'toc'`（标题目录，默认） / `'files'`（文件目录） / `'bookmarks'`（收藏目录） | `leftMode` | 328 |
| 翻页模式 | `'single'`（单页） / `'continuous'`（连续瀑布） | `pagingMode` | 2229-2240 |

再加一层开合：左列是 `document.body` 上的 `position:fixed` portal，`showLeftCol = tocOpen && visible && paneOnScreen`（`KsEvidenceTab.tsx:973`）。

内部状态量（正则 `useX(<|\()`，不含 import 行）：`useState` 35、`useEffect` 13、`useCallback` 35、`useMemo` 2、`useRef` 39。

### 4.2 有多少纯函数可以抽出来单独测

**已经天然纯、只是放在这个文件里（模块级，5 个）**：

| # | 函数 | 行 | 它做什么 |
|---|---|---|---|
| 1 | `readSlowTransitionMs()` | 117-129 | 从 `--ds-transition-duration-slow` 解析 `0.3s`/`300ms` → 毫秒；读不到回退 300；`Number.isFinite` 钳制 |
| 2 | `tocNoClause(t: KsClause)` | 2503-2507 | 取条款号：优先 `clause_number`，否则用 `/^(\d{1,2}(?:\.\d{1,2})?)(?:\s+|(?=[\u4e00-\u9fff（(《]))/` 从标题头抓 |
| 3 | `escDupNoLocal(no)` | 2509-2514 | 把编号逐字符转义成正则片段，字符间插 `\s*`（容忍 `1.2` 与 `1. 2`） |
| 4 | `dupNoMatchesLocal(text, no)` | 2517-2520 | 判 `text` 是否以编号 `no` 开头，返回 match（带 `(?![\d.])` 防 `1` 命中 `12`） |
| 5 | `tocTitleSplitClause(t)` | 2524-2530 | 标题去重：编号已被编号徽章渲染 → 返回 `{hidden, rest}`（渲染时 `display:none`，不硬删字符） |

这四个 TOC 函数（2-5）是**纯字符串函数**，零 DOM、零 React、零依赖，`smoke-catalog-ui` 那种"打包三行 export 就能测"的路子完全够用 —— 现在它们一条断言都没有。

**语义纯、但写在组件里（只能靠渲染间接测，7 个）**：

| # | 函数 | 行 | 它做什么 |
|---|---|---|---|
| 6 | `historyLabel(h)` | 1783-1786 | `HistoryEntry` → `第N页` |
| 7 | `bookmarkOptionLabel(b)` | 1803-1807 | `KsBookmark` → `§编号 · 第N页`（缺字段退 `?`） |
| 8 | `sliderPercent` | 1775-1776 | `Math.max(10, Math.min(500, zoomView.percent))` 钳制 |
| 9 | `onInput(raw)` | 1463-1470 | 页码输入串 → 判合法后 `goTo` |
| 10 | `tocFiltered`（`useMemo`） | 977-983 | 目录按编号/标题/页码三路 `includes` 过滤 |
| 11 | `historyOptions` | 1780-1782 | 过滤"同 doc、非当前页"的历史条目 |
| 12 | `paneLeftEdge(el)` | 141-149 | 向上找第一个宽度 >1px 的祖先的左缘（纯 DOM 查询，可用假 el 测） |

结论口径：**可脱离 React 单独测的纯函数 5 个（上表 1-5）+ 需要一层壳但逻辑纯的 7 个**。现在真正被单独钉住的一个都没有 —— `smoke-turn-tab` 测的是 `KsTurnTab` 里的纯组件，不是这里的。

---

## 五、内联样式重复（统一化靶子）

### 5.1 `fontSize: <数字>` 内联字面量

```
正则 fontSize:\s*[0-9.]+ 扫 plugin/client/*.tsx
命中 230 处；剥掉注释行后 **代码里 229 处** + 1 处在注释里（KsChannelsPanel.tsx:498 记录"改前写死 fontSize: 12"）
```

| 文件 | 处数 | 文件 | 处数 |
|---|---|---|---|
| `KsSettingsSection.tsx` | 65 | `KsTurnTab.tsx` | 12 |
| `KsMaterialsPanel.tsx` | 51 | `KsDocTextView.tsx` | 2 |
| `KsCapabilityPage.tsx` | 33 | `KsKnowledgePage.tsx` | 2 |
| `KsEvidenceTab.tsx` | 23 | `KsScopeChip.tsx` | 2 |
| `KsFilesTab.tsx` | 19 | `KsChannelsPanel.tsx` | 1 |
| `KsBookmarksTab.tsx` | 18 | `KsAnchorWarn.tsx` | 1 |

按值分布（`Group-Object` 后排序）：

```
9 x2 / 10 x7 / 10.5 x6 / 11 x41 / 11.5 x15 / 12 x135 / 12.5 x1 / 13 x17 / 14 x2 / 15 x4
```

对照 `ksGuideStyles.ts:49-55` 立的受限字号表（`--ks-fs-2xs:10 / xs:11 / sm:12 / base:13 / md:14 / lg:16 / title:20 / hero:24`）：
**有 5 个值在表上根本不存在 —— 9 / 10.5 / 11.5 / 12.5 / 15，合计 28 处**。这 28 处不是"忘了用 token"，是"现有 token 表表达不了"，所以迁移前必须先决定这 5 档怎么办。

### 5.2 局部 `const $xxx: React.CSSProperties`

```
grep -c ': React\.CSSProperties'  => 83 处注解
其中 const $xxx = {...} 字面量 78 个（块解析器逐块解析出 78 个完整块，用于下面的重复比对）
另外 5 处不是这个形态：3 个函数返回类型（KsArrowOverlay.tsx:39、KsMaterialsPanel.tsx:99、
KsSettingsSection.tsx:1384）、1 个箭头函数（KsDocTextView.tsx:360 $pageBtn）、
1 个非 $ 命名的常量（KsSettingsSection.tsx:122 SUMMARY_HINT）
```

| 文件 | `const $xxx` | 文件 | `const $xxx` |
|---|---|---|---|
| `KsFilesTab.tsx` | 32 | `KsChannelsPanel.tsx` | 4 |
| `KsEvidenceTab.tsx` | 31 | `KsSettingsSection.tsx` | 1（`SUMMARY_HINT`，非 `$` 命名） |
| `KsBookmarksTab.tsx` | 10 | `KsDocTextView.tsx` | 1（`$pageNav`） |

（`KsMaterialsPanel.tsx`、`KsArrowOverlay.tsx` 的那 1 处是函数返回类型注解，没有 `$` 常量。）

### 5.3 跨文件逐字相同的内联 style

两组分开算，因为它们的修法不同。

**(a) `const $xxx: React.CSSProperties` 里逐字相同的 —— 4 组**（块解析器逐块比较，共 78 个块）：

| 组 | 内容 | 位置 |
|---|---|---|
| **3 份** | `display:'flex', alignItems:'center', justifyContent:'center', height:'100%', minHeight:160` | `KsBookmarksTab.tsx:582 $center`、`KsEvidenceTab.tsx:2534 $center`、`KsFilesTab.tsx:522 $center` |
| 2 份 | `background:'var(--dsw-alias-bg-layer-1,#eef4ff)', color:'var(--dsw-alias-link,#1565c0)', fontWeight:600` | `KsEvidenceTab.tsx:2590 $segBtnOn`、`KsEvidenceTab.tsx:2619 $zoomMenuItemOn`（同文件内） |
| 2 份 | `border:'1px solid var(--dsw-alias-border-l2,#ccc)', background:'var(--dsw-alias-bg-layer-2,#fff)', color:'var(--dsw-alias-label-primary,#111)', …` | `KsEvidenceTab.tsx:2641 $btnPrimary`、`KsFilesTab.tsx:530 $btnPrimary` |
| 2 份 | `display:'inline-flex', alignItems:'center', justifyContent:'center', width:14, height:14, marginRight:1, color:'var(--dsw-alias-link,#1565c0)'` | `KsBookmarksTab.tsx:665 $caret`、`KsFilesTab.tsx:658 $caret` |

**任务书的线索核实：`$center` 确实在三个文件里逐字出现**，行号见上表第一组。

**(b) 内联 `style={{…}}` 字面量（不带 `...` 展开）里逐字相同的 —— 17 组**（407 个内联字面量里跨文件重复的）：

| 处数 | 内容（截断） | 文件:行 |
|---|---|---|
| 11 | `color:'var(--dsw-alias-label-secondary,#666)'` | Bookmarks 346/359/367、Evidence 1930/2087、Files 429/442/447、Settings 1061/1085/1580 |
| 11 | `cursor:'pointer'` | Bookmarks 382/512/534、Channels 521/525/865、Settings 156/237/1151/1273/1297 |
| 7 | `fontWeight:600, color:'var(--dsw-alias-label-primary,#111)'` | Bookmarks 311、Evidence 1862/2011、Files 343、Settings 617/1047/1482 |
| 5 | `margin:'0 0 4px'` | Materials 1055、Settings 165/169/245/246 |
| **3** | **整块容器外壳**：`display:'flex', flexDirection:'column', height:'100%', minHeight:0, fontSize:12` | **`KsBookmarksTab.tsx:308`、`KsEvidenceTab.tsx:1859`、`KsFilesTab.tsx:340`** |
| **3** | **整块 header 行**：`display:'flex', alignItems:'center', gap:8, padding:'6px 10px', borderBottom:'1px solid var(--dsw-alias-border-l1,#eee)', flexWrap:'wrap'` | **`KsBookmarksTab.tsx:310`、`KsEvidenceTab.tsx:1861`、`KsFilesTab.tsx:342`** |
| 3 | `color:'var(--dsw-alias-label-secondary,#666)', maxWidth:480, textAlign:'center', wordBreak:'break-word'` | Bookmarks 351、Evidence 2092、Files 434 |
| 3 | `color:'var(--dsw-alias-label-tertiary,#999)', fontSize:11` | Evidence 2223、Files 346/348 |
| 3 | `display:'flex', alignItems:'center', gap:8` | Capability 123/187、Turn 376 |
| 3 | `color:'var(--dsw-alias-label-tertiary)', fontSize:12, lineHeight:1.6` | Capability 301、Turn 345/587 |
| 3 | `fontWeight:600` | Capability 395、ScopeChip 130、Turn 390 |
| 2 | `flex:1, minHeight:0, overflow:'auto', padding:4` | Bookmarks 343、Files 426 |
| 2 | `flex:1, minWidth:0` | Capability 91、Channels 510 |
| 2 | `margin:0, color:GRAY` | Channels 601、Materials 1046 |
| 2 | `margin:'6px 0 0', fontSize:12, color:'var(--dsw-alias-label-secondary,#666)'` | Materials 773、Settings 1620 |
| 3 | `flex:1` | Evidence 2275、Settings 380/776 |
| 2 | `marginTop:6` | KnowledgePage 2118、Materials 1092 |

**最值钱的一组不是 `$center`，是上面加粗的那两块**：`KsFilesTab` / `KsBookmarksTab` / `KsEvidenceTab` 三个左列视图把"竖排列容器 + header 行"整块抄了三遍（连 `fontSize:12`、`padding:'6px 10px'`、`#eee` 兜底色都逐字一样）。这就是"同一个界面骨架三份实现"的直接证据。

### 5.4 `smoke-ui-scale.mjs` 只扫一个文件 —— 确认，并算射程外

确认（一手）：

```
plugin/scripts/smoke-ui-scale.mjs:38  const stylesPath = join(pluginRoot, 'client', 'ksGuideStyles.ts')
plugin/scripts/smoke-ui-scale.mjs:82  const src = await readFile(stylesPath, 'utf8')
```

全文只有这一处读文件；它做的事是 `KS_STYLES` 模板串里 **CSS 声明**的两条棘轮：spacing 不在 4px 网格的数、`font-size` 不走 `var(--ks-fs-*)` 的数，基线都是 **0**（`BASELINE_OFF_GRID_SPACING = 0`、`BASELINE_RAW_FONT_SIZE = 0`，第 47/54 行）。

实测该文件当前是干净的：`font-size` 78 处，**78 处全部是 `var(--ks-fs-*)`**。
也就是说这条棘轮守住的只是 `ksGuideStyles.ts` 里那一族 CSS 类。

**射程外（脚本完全看不见的）**：

| 项 | 数量 | 说明 |
|---|---|---|
| 内联 `fontSize: <数字>` | **229 处 / 12 个文件**（+1 处在注释） | 是 React 驼峰属性，`smoke-ui-scale` 只匹配 CSS 的 `font-size:`，正则层面就碰不到 |
| 内联 `style={{…}}` 对象 | **455 处**（407 不带展开 + 48 带 `...`） | 无任何门禁扫描 |
| `const $xxx: React.CSSProperties` | **78 个** | 同上 |
| 跨文件逐字重复 | **21 组**（4 组 `$` 常量 + 17 组内联） | 无重复检测器（`docs/uniformity/ast-dupes.json` 那套 TS 克隆检测见 §七，未见覆盖这些） |

补一条旁证：另有**主题债棘轮**在 `smoke-client-entry.mjs:1138-1147`（`THEME_DEBT_BASELINE`），它按文件数"写死颜色"的行数，8 个文件合计基线 **77**（Bookmarks 3 / Channels 3 / Evidence 12 / Files 1 / Ingest 0 / Materials 5 / ScopeChip 5 / Settings 48）。这是唯一覆盖到"内联样式里的硬编码色值"的门禁 —— 但它只管颜色，且是**只减不增的计数**，不管字号/间距/重复。

---

## 六、前端测试覆盖现状

### 6.1 测试形态（先讲清"测试"在这个仓是什么）

- 没有单测框架：`plugin/test/` 里只有一个 `ks-engine-wire.json`，没有 vitest/jest。
- 全部靠 `plugin/scripts/*.mjs`（**56 个**），三种做法：
  1. **打包 + 断言纯函数**：esbuild 把某模块打成一个临时 ESM（`smoke-pdf-fit`、`smoke-pdf-panel`、`smoke-client-entry` 对 `ksSearchSyntax`）；
  2. **打包 + `react-dom/server` SSR 断言字符串**（`smoke-evidence-warn`、`smoke-turn-tab`、`smoke-settings`），或 **jsdom 真挂载 + 事件**（`smoke-kb-page-render`、`smoke-catalog-ui`）；
  3. **只读源码 grep**（`smoke-evidence-warn` 读 `entry.ts`、`smoke-compliance-sentry` 读 `KsScopeChip.tsx`）。
- 门禁链（`scripts/run-gates.ps1` → `npm run smoke` → `plugin/scripts/smoke-all.mjs`）跑的是 `SUITES` 数组里的 **44 条**（`smoke-all.mjs:67-161`，静态数组、无条件分支）；其余 12 个 `.mjs` 只能手工跑。

### 6.2 逐个：31 个文件谁有覆盖（四档，合计 31）

| 档 | 判定 | 文件（数量） |
|---|---|---|
| **行为** | 脚本真打包/真渲染该模块**自己的导出**并断言 | `entry.ts`、`KsKnowledgePage.tsx`、`KsEvidenceTab.tsx`、`KsSettingsSection.tsx`、`KsMaterialsPanel.tsx`、`KsChannelsPanel.tsx`、`KsFilesTab.tsx`、`KsTurnTab.tsx`、`KsEvidenceHost.tsx`、`KsAnchorWarn.tsx`、`KsArrowOverlay.tsx`、`ksPrefs.ts`、`ksSearchSyntax.ts`、`ksGuideStyles.ts`、`pdfFit.ts`、`pdfPanel.ts`（**16**） |
| **结构** | 只被 grep 源码文本或被计数，没有行为断言 | `KsBookmarksTab.tsx`（只进"写死颜色基线表"）、`KsIngestPanel.tsx`（被反向断言"不在设置里"）、`KsDocTextView.tsx`（`smoke-sanitize` **复刻**算法）、`KsScopeChip.tsx`（读源码判"界面不显示徽章"）、`KsKnowledgeGuide.tsx`（读源码判菜单文案，**路径写死**）（**5**） |
| **仅间接** | 没有任何直接断言，只随别的模块进包 | `api.ts`、`ksEvidence.ts`、`KsCapabilityPage.tsx`、`ksSidebar.ts`、`KsKnowledgeGuideIcon.tsx`、`pdf-configure.ts`、`kbListUi.tsx`（**7**） |
| **零接触** | 连包都不进（类型擦除 / 无人 import） | `ksHostPrimitives.d.ts`、`ks-evidence-props.ts`、`KsPdfGuideIcon.tsx`（**3**） |

命令（把每个模块名拿去 `plugin/scripts/*.mjs` 里逐个 grep，再剔掉"只在注释里出现"的）：

```
foreach ($f in client/*.ts,*.tsx) { $base=$f.BaseName; 在 scripts/*.mjs 里 grep -F $base }
=> NONE 或纯注释命中：kbListUi / ks-evidence-props / ksHostPrimitives / KsKnowledgeGuideIcon /
   KsPdfGuideIcon / pdf-configure / ksSidebar
=> 导出符号 KS_EVIDENCE_KIND / ksKbDefinition / toNavParams / KsCrumb / KsListHead /
   configurePdfWorker / PDF_WASM_DIR 在脚本里各 0 次点名
```

`KsPdfGuideIcon.tsx` 的"零接触"是**结构上**成立的：`plugin/client` 里没有任何文件 `from './KsPdfGuideIcon'`（import 图实测），所以它既没判据也没入口 —— 见 §七第 2 条。

### 6.3 三个具体的覆盖缺口（都已核到行）

1. **`kbListUi.tsx` 的共用件零引用**：`KsCrumb` / `KsListHead` 在 `plugin/scripts/*.mjs` 里 **0 次**出现。渠道台账（`KsChannelsPanel.tsx:700` 用 `KsCrumb`）与知识库页（`KsKnowledgePage.tsx:2965/3507/3671` 用 `KsListHead`）三个面全靠渲染断言**碰巧**覆盖，共用件本身没有一条判据。`kbListUi.tsx:9` 还写着"KsKnowledgePage 迁过来 = 下一小批"，也就是说这个文件还要被改，而现在改错了没人拦。
2. **`smoke-sanitize.mjs` 不测真模块**：`smoke-sanitize.mjs:112` 注释写 `消毒器复刻（与 client/KsDocTextView.tsx 同算法）`，然后把白名单、属性表、清理逻辑**抄了一遍**。它能锁"用例矩阵里的行为"，但**测不出实现漂移**——`KsDocTextView` 里的消毒器改了，这条冒烟照样绿。XSS 是这里最要紧的属性，这一步值得单独补一条"打包真模块"的判据。
3. **`smoke-kb-page-render.mjs:2629` 里的绝对路径**：
   ```js
   const guideSrc = readFileSync('D:/AI/work space/zcode/plugin/client/KsKnowledgeGuide.tsx', 'utf8')
   ```
   同一文件 162 行与 2746 行用的都是 `join(pluginRoot, 'client', …)`，只有这一处写死盘符+空格路径。后果：换机器/换盘符/在提取树里跑，这条要么抛 ENOENT 要么读到别人机器上的文件 —— 与本仓"代码里不许写死绝对路径"的硬约束直接冲突。

### 6.4 还有一条不在门禁里的渲染证据

`plugin/scripts/ui-render-shot.mjs`（jsdom 真挂载 + 宿主真 CSS + 无头浏览器截图，`PAGES` 表在 149-172 行）对 5 个页面做的是**独立挂载的整页渲染 + 截图**。对 `KsCapabilityPage`（§6.2 属"仅间接"）与 `KsIngestPanel`（属"结构"）来说，它是**唯一**的整页渲染证据；`KsMaterialsPanel`/`KsSettingsSection`/`KsTurnTab` 另有行为级断言。但：

```
grep 'ui-render-shot' scripts/  => 只命中一个 scripts/b6-faceswitch.patch.py 和 README
grep 'ui-render' plugin/package.json => 无
```

**它不在 `run-gates.ps1` 里，也不是任何 npm script** ⇒ 这些页面的"渲染级"结论目前只能手工复现。`scripts/b6-faceswitch.patch.py` 自己也写着"建议优先接进门禁"。

---

## 七、我没搞清楚的

1. **`api.ts` 与三个大组件没有逐行读完**。读了约 1,100 + 600 + 1,000 行窗口（具体窗口见 §一引言），其余靠"枚举全部导出/端点/重复"覆盖。具体没读的区域：`api.ts` 310-390、530-650、1520-1740、2040-2510、2620-2870、3010-3170、3260-3470、3590-3780、3860-4450、4900-5011；`KsKnowledgePage` 557-2020、2140-3060、3190-3240、3290-3868；`KsEvidenceTab` 500-660、850-950、1010-1470、1830-1890、2010-2490、2670-2834。**结论层用到的每个数字都有对应命令**，但这些区域里可能还有别的重复没被我数到。
2. **（原以为不清楚，已查实）`KsPdfGuideIcon.tsx` 是死组件**。全仓（含 `plugin/**/*.ts,*.tsx,*.mjs,*.js`）搜 `KsPdfGuideIcon` 只有三处命中：它自己的文件头（:2）、自己的导出（:25）、以及 `KsKnowledgeGuideIcon.tsx:11` 的一句注释（"约定照 `KsPdfGuideIcon`"）—— **没有任何 import**。所以它既不渲染、也没判据。是留是删需要业主/维护者定，本轮只登记。
3. **两层 `.ks-page` 嵌套（ingest 分支）有没有可见后果**。要量 DOM 几何才能说，本轮不许跑浏览器。只登记事实：`KsKnowledgePage.tsx:3272` → `KsIngestPanel.tsx:367`。
4. **`KsSettingsSection.tsx` 的文件头（1-36 行）与实现脱节**。头里仍写偏好走 `pluginSettings['ks:settings']` 与 `/sidebar/api/settings.update`，而 `ksPrefs.ts:1-28` 明确说那条路已随 better-sidebar 一起消失、改 localStorage。同理 `KsIngestPanel.tsx:14-15` 写"由 KsSettingsSection 的「入库预览」类目承载"，而 `KsSettingsSection.tsx:409-419` 写它已被撤掉、`KsKnowledgePage.tsx:3252` 写它已复活到上传区。**三处注释互相矛盾**，我确认了代码事实（谁 import 谁），但没确认这三段注释里哪一段是"最后一次真实"。
5. **`docs/uniformity/ast-dupes.json`（32KB）、`measure-01.json`、`baseline.json` 里有没有已经统计过前端重复**，本轮没读。如果那边已经有一份"跨文件同函数体"清单，§五 的 21 组很可能与它部分重叠（也可能完全不重叠，因为那边是 TS AST 级、我这边是 style 字面量级）。**未读，原因：超出任务书范围，且需要先确认那批 JSON 的生成口径。**
6. **`KsMaterialsPanel` 的 `Deliverables` 子组件（1298-1409）与 `AnchorMark`（139-174）** 只看了行号与冒烟里的点名，没读实现，所以表格里"导出研究报告"那段描述是从文件头（`KsMaterialsPanel.tsx:1-24`）与 import 列表推的，不是读出来的。
7. **`KsTurnTab` 的 80-568 没读**：只读了文件头 1-80 与冒烟断言的组件名（`KsTurnEvidenceRow` / `KsTurnEmptyState` / `KsTurnModeChip` / `turnEvidenceHref`）。"三个子状态"的具体渲染分支未核。

---

## 附：本报告用到的命令（可复现）

```powershell
# 行数（非空 vs 实际）
Get-ChildItem plugin\client -File | ? { $_.Extension -in '.ts','.tsx' } | % {
  $t=[IO.File]::ReadAllText($_.FullName)
  [pscustomobject]@{File=$_.Name; Real=($t.ToCharArray()|?{$_ -eq "`n"}).Count; NonBlank=(Get-Content $_.FullName|Measure-Object -Line).Lines} }

# api.ts 重复统计
Select-String plugin\client\api.ts -Pattern "throw new EngineAuthError\('引擎校验失败" | Measure-Object   # 40
Select-String plugin\client\api.ts -Pattern 'if \(!res\.ok\)' | Measure-Object                             # 80
Select-String plugin\client\api.ts -Pattern 'res.status === 401' | Measure-Object                          # 42
Select-String plugin\client\api.ts -Pattern '\bksJson\b' | Measure-Object                                  # 27（1 定义 + 24 调用 + 2 注释）
Select-String plugin\client\api.ts -Pattern 'export (async )?function' | Measure-Object                     # 116（真实 117，漏 api.ts:2422）

# 页壳 / 面包屑
Select-String plugin\client\*.tsx -Pattern 'className="ks-page"'        # 8 处
Select-String plugin\client\*.tsx -Pattern 'className="ks-page-head"'   # 5 处
Select-String plugin\client\KsKnowledgePage.tsx -Pattern 'ks-crumb'     # 3072-3160

# 样式
(Select-String plugin\client\*.tsx -Pattern 'fontSize:\s*[0-9.]+' -AllMatches | % { $_.Matches.Count } | Measure-Object -Sum).Sum   # 230
Select-String plugin\client\*.ts -Pattern 'const (\$\w+): React\.CSSProperties'                                                    # 78
Select-String plugin\client\*.tsx -Pattern 'style=\{\{'                                                                             # 455

# 覆盖
Get-ChildItem plugin\scripts\*.mjs | % { Select-String $_ -Pattern '<模块名>' -SimpleMatch }   # 逐模块
Select-String plugin\scripts\smoke-ui-scale.mjs -Pattern 'ksGuideStyles|readFile'              # 只扫一个文件
```
