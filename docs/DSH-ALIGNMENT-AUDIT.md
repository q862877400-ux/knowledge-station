# DSH 适配审计与整改清单（2026-09-19）

**怎么做的**：DSH 全量文档（3465 篇 `.md`）入库后，派 **3 个独立子代理**分别审
「客户端半边 / 宿主半边 / 工程与流程」，每条都要**两侧 `file:line` + 官方原文引用**，
并要求单列「我不确定 / 没查到」。三份报告都读完，本节是结论与去向。

> 一句话：**没有一个"结构性走错"**（bundle 形态、槽位契约、工具错误语义、注册可逆性、
> `inject` 持续语义都经得起对照）；问题是**一批具体违规与缺护栏**，其中 7 条已在本轮修掉。

---

## 一、本轮已修（每条都有断言/证伪）

| # | 问题 | 官方依据 | 修法与证据 |
|---|---|---|---|
| 1 | **插件完全没有 `Config`** —— 5 个配置键只在 `cordis.patch.yml` 注释里，传错无任何校验 | 官方：`Config` 必须是标准 schema，「导普通对象不会校验」 | 加 `export const Config = Schema.object({...})`（`@deepseek-ai/schemastery`）。**并实测**：本地 schemastery **没有 `.strict()`**（加上去 ⇒ 插件加载即失败）、`.loose(false)` 也**照旧保留未知键** ⇒ 键名拼错仍静默，故另加 `apply` 里的未知键**当场报错** + `CONFIG_KEYS` 单一所有者。4 条冒烟断言 |
| 2 | 引入 #1 时**没声明依赖** `@deepseek-ai/schemastery`（靠 npm 扁平提升才活着） | — | 写进 `plugin/package.json` 的 `dependencies`（**不是** peer：ERRATA §I 那套 peer 校验已被官方移除） |
| 3 | **7 个不存在的 `--dsw-alias-*` token、32 处**，全落到 `#b8860b`/`#c62828`/`#ccc` 等**写死兜底**；其中 `--dsw-alias-state-error-tertiary` **没写兜底** ⇒ 声明非法 ⇒「已废止」徽章底色**整个不存在** | `docs/web-styling.md`：只用存在的语义 token、**不许写死色值** | 全部换成真实 token（`state-warn-primary`/`state-error-primary`/`border-l2`/`bg-layer-2`/`bg-base`/`state-error-secondary`）**并删掉兜底色值**；新增**护栏**：渲染级冒烟断言"我们引用的每个 `--dsw-*` 都必须在主题里定义"（实测 24 个全部存在）+ **证伪过**（塞一个假的即红） |
| 4 | 注入的 `<style>` **没标 `data-plugin`/`data-plugin-css`** ⇒ ①宿主 HMR 的 `removeOwnedStyles` 找不到我们的标签、而 `ensureKsStyles` 按 `#id` 去重直接 return ⇒ **改 CSS 必须整页刷新**（我们自找的例外）②别的插件 `claimStyles` 会把我们的标签认领走、卸载时删掉 | 宿主 `system.ts`/`entry-lifecycle.ts`/`manifest.ts` 的所有权规则（官方 preset 同形） | 两个属性都写；去重键改为 `style[data-plugin-css=…]`；**首次注入移到模块顶层**（落在 `claimStyles` 窗口内）；冒烟加断言钉住两个属性 |
| 5 | `.ks-dot{border-radius:50%}` 缺 `corner-shape:round` ⇒ 支持 superellipse 的 Chromium 上圆点被压成方角 | `docs/web-styling.md`：full-round 半径必须配 `corner-shape:round` | 补上（官方那张同款卡用 24px 胶囊且**不**需要，故只改这一处） |
| 6 | **`inject` 把"可缺省的服务"声明成硬依赖** ⇒ 为它们写的兜底是**死代码**；真缺服务时插件**永远 PENDING 且不打任何日志** | `cordis-tutorial/03-services.md`：「`inject` is for hard requirements…otherwise the consumer stays PENDING and prints nothing」；`postmortem/0001`：「use `ctx.get(name)`, never `ctx.<name>`」 | `agents`/`commands` 从 `inject` 移出、改走 **`ctx.get()`**；`webServer` 确认为**硬依赖**（没有它整个 `/ks/*` 消失）故留在 `inject`，但**删掉那层死兜底**、换成**当场抛错**。冒烟的假 `ctx` 同步实现 `get()`（桩与真契约一致，避免假红） |
| 7 | **我们全仓没有 `AGENTS.md`** —— 官方那层"每会话必读的站立指令"完全缺失，纪律散落在**史书**与**施工计划**里（归属错层） | `docs/AGENTS.md`：standing orders 住根 `AGENTS.md`（≤1950 字），"一个事实一个归属层" | 新建根 [`AGENTS.md`](../AGENTS.md)；把 `DEVELOPMENT-HISTORY` §五 与 `CHANNEL-COVERAGE-PLAN` §5 的**正文收敛过去**、原处只留**来历**（并指出 §五第 6 条原先自我重复，正是官方 slop 清单的 "duplicated rules"） |
| 8 | **"门禁只涨不跌"是散文** —— 每轮靠人记得手敲 5–6 条命令、手抄数字 | `docs/development.md`：门禁即代码 | 新增 [`scripts/run-gates.ps1`](../scripts/run-gates.ps1)：`-Quick`/`-Full` 两档 + **锁文件**（并发跑门禁 ⇒ 当场退出码 3，因为并发会造假红）+ **读基线文件判"只涨不跌"**。基线已记：**pytest 2143 passed / 3 skipped**。锁的两个方向都实测过 |
| 9 | 复核任务书写在 **gitignored 的 `var/tmp/`** ⇒ 任务书与结论**都不在版本控制里** | 官方把证据放进 PR body 的 `<details>Proof</summary>` | 新增 [`docs/verify-briefs/`](../docs/verify-briefs/README.md)（含约定：冻结端点、提取树验证、首尾各记 `rev-parse`+`status`）；方案 §6 里的路径改过去 |
| 10 | 权威导航层 `dshdocs-C.md` 里**留着一条已被 alpha.2 放宽的规则**，且没有反向指针 ⇒ 会被再引用一次 | 一个事实一个归属层 | 就地加反向指针指向 `ERRATA-alpha.2 §A2` |

**门禁**：`run-gates.ps1 -Quick` **4/4**、`-Full` **6/6**（含 pytest 2143/3 与引擎 4/4）；
`kb-page-render` 冒烟 **23/23**（⚠ 首次写下的是 22/22，实为 23 —— 就地更正，数字要回实测核）；
`tool` 冒烟 **69/69**。

---

## 二、积压（按性价比排序；#4 已于第二轮修掉，见 §三）

| 优先级 | 项 | 性质 | 量 |
|---|---|---|---|
| **1** | **客户端文案 locale 化**：216 个 JSX 中文文本 + 86 个散文属性（aria/title/placeholder），**0 处 `ctx.locale`**。官方门禁 `verify-client-ui-i18n` 只 glob DSH 仓内路径 ⇒ **扫不到我们**；运行时也不崩（查不到 key 回退成 key），真正坏的是英文 locale 下宿主英文、我们整片中文（混排） | **违规** | **L**（做法已给全：`LocaleNamespaceMap` 声明合并 + `ctx.locale.register/bind` + 槽位注册加 `locale:` + `entry.ts` 的 `inject` 加 `'locale'`） |
| **2** | **持久化归属**：`chatmode.js`/`inspection.js`/`announce.js`/`ingest.js` 四处**自造 JSON 状态文件**（直写、无 schema、无版本），绕开 `ctx.settings`/`ctx.storageDomain`。本仓自己的证据：状态只在进程启动读一次 ⇒ **别的进程改了要重启才生效** | **违规 + 会坏** | S/M/L 分三档；⚠ 诚实边界：`domain/changed` **仅进程内**，迁移**换不到**我们现手搓的跨进程锁 |
| 3 | 6 个工具用**裸对象字面量**注册、没用官方 `defineTool({...})` | 不违规（官方承认 raw JSON-Schema 这条路），代价是自己扛参数校验 | M |
| ~~4~~ | ~~启动检查的清理竞态~~ | —— | ✅ 已修，见 §三 |
| 5 | 构建把 `@deepseek-ai/*` **整片 external**，没有官方那种 **purity 门禁**（引到不该引的包不报错） | 缺护栏 | S（收窄为 9 个基线模块 + 显式白名单，其余 `onResolve` 抛错） |
| 6 | `S6` 的默认值双份（`DEFAULTS` vs schema）、`S1` 的 `sidebar.right.pane.tab.title` **从未注册**但注释声称注册了、`S2` 该用未用的原语（`Tooltip`/`StateDot`/`RiskConfirmation`/`Toast`/`MarkdownText`/`FileTypeIcon`…） | 清理 | S–M |
| 7 | **binary 交付物**（`.docx`/`.pptx`）在客户端只能"下载一份"，而官方 `loading:'renderer'` + office-to-pdf 正是为它设计的 | 不违规（概念重叠） | M |
| 8 | 官方 `record-browser-gif`：**产品可见的 GUI 改动必须有真机 GIF**。我们只有 jsdom 渲染级用例，**没有真浏览器证据** | **缺证据** | M（需真机 + 真模型轮次） |
| 9 | 流程侧：**零 git hook / 零 CI**（官方 pre-commit 只做 `git diff --cached --check` + 尾换行）；文档结构规则（历史不进 prose、状态标注、实现叙事、相对链接）无护栏 | 缺护栏 | M（hook/CI）+ L（文档拆分） |

### 特别注意（避免误判）

- **官方没有"单文件最大行数"规定**（预算清单是**白名单式**的 8 个文件）⇒ `DEVELOPMENT-HISTORY.md`
  的 6600+ 行**不是"超预算"**，它违反的是**结构规则**（历史/实现叙事不进 prose）。别按"删到某字数"整改。
- **官方没有 commit message 格式规定**，也**没有**要求"每改动派独立 agent 复核"。我们的**每轮独立
  verifier 是超官方要求**，应**保留**而不是照官方裁掉。
- **`ui-sidebar-documentpreview` 不构成"重复实现"**：官方 PDF 渲染器只挂在 `text` tab 下、而 `text` 只
  claim `dsh-resource://file/**` ⇒ 我们的引擎鉴权 PDF **不可达**；且官方那个**没有跳页/高亮/目录**。
  官方确实给了外部插件注册文档预览的扩展点（`DocumentPreviewDefinition` + 两段注册）。
- **单文件 `client.js` 与 chunk 支持不冲突**（chunk 缺席就是 entry 的合法形态）；只有将来用
  `import()` 才会冲突（官方靠 preset 改写成 `require.async`，esbuild 不会）。
- 三份报告各自列了「我不确定/没查到」，**未验证的推论都没有当成结论**（例如"样式会被别的插件
  认领后误删"是源码必然推论但**未实测**；`storageDomain` 的多进程强弱**未实测**）。

---

## 三、第二轮已修（2026-09-19）：积压 #4 + 施工中**新发现**的两条

详细记录在[开发史 §10.135](DEVELOPMENT-HISTORY.md)（含修复前 0/5 的失败输出）；此处只留结论。

| 项 | 性质 | 结果 |
|---|---|---|
| 积压 #4 启动收尾竞态 | 会坏 | ✅ 确证（B1 断言 `setInterval=1`）并修：三处同形加**卸载代数** `_xxxEpoch`——disposer 递增它，启动收尾在**装任何句柄之前**比对，不一致整段作废。新增 `smoke-lifecycle.mjs` 双向断言（竞态不许装 / 干净路径必须装 / 卸载必须清 / 跨模块回装也不许） |
| **新发现**：`adoptJob` 少传 `manager` | **会坏（静默）** | ✅ 修 `runJobPollLoop(manager, jobId, initialStatus)` + 两处调用点。修复前：入库任务接管**整条死掉**（`ensureLive=0`、镜像停在 running），**不抛错** |
| **新发现**：卸载不停入库轮询 | 会坏（潜伏·**无界**） | ✅ `registerKsIngestRoutes` 的 disposer 补 `stopJobPoll()`；`void runJobPollLoop` 挂 `.catch`，别让后台轮询的 rejection 终止宿主 |
| **复核打回**：`finalizeBatch` 尾巴无代数比对 | 会坏（跨模块回装） | ✅ 复核拿可复现脚本证明：卸载落在拉 changes 的窗口里，尾巴仍会 `triggerAfterInspection` → `announce.adoptScanPoll`，**装起持有已死 ctx 的活轮询**（3 次扫描轮询 + 4 次 ensureLive）。修法：进入时记代数、**尾巴调用前**比对（放在调用方太晚）；`smoke-lifecycle` 的 **B4** 用"卡住 changes 那次 fetch"把它做成确定性用例（修前 `afterDispose=1`，修后 6/6） |

**⚠ 就地更正审计自己的一句话（第二次更正）**：积压 #4 原文写「同类**三处**（announce/ingest）」；
我第一轮把它更正成"只有 inspection 泄漏活句柄、announce/ingest 是下一 tick 自终止型"——
**这个更正错了一半**（独立复核用变异体实测推翻）：`inspection` 泄漏 30s 定时器；
`announce` 靠 disposer 的 `stopPoll()` 至多**多跑一格**（读源码 + 复核确认，未单独端到端实测）；
**`ingest` 是潜伏的无界泄漏**——它的循环 `while (!jobTick(jobId))` **只在 `_jobPoll` 被清空后**
才为真，而基线 disposer 从不清它（复核变异体：卸载后 3.5s 内又 `ensureLive` 2 次，上限 6h）。
⇒ 原始审计在**方向上是部分对的**，错的是我那半句更正。逐条证据在
[开发史 §10.135 六](DEVELOPMENT-HISTORY.md)。


**施工中被修复"当场"暴露的两个问题**（都属"桩不真 / 污染真数据"）：
`smoke-ingest` 的假 manager 缺 `touchActivity()`（轮询死着时够不着，修好即刻崩 ⇒ 假崩不是真缺陷）；
同一个 smoke 不设 `KS_DATA_DIR` ⇒ 把 `ks-ingest.json` 写进**真实**数据区 ⇒ **真产品下次启动会去
接管烟测造的假任务**。两处均已修，理由写进文件头。
