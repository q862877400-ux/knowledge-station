# DSH 官方文档精读（8 份分片）

> ## ⚠️ 版本口径（先读这一行）
> **下面的 8 份分片与 Hindsight 里的对应条目，都是按 `dsh-v0.1.6-alpha.1`（sha `0a15e36e7f`）写的。**
> 业主已于 **2026-09-19 升级到 `dsh-v0.1.6-alpha.2`**（sha `ddefc45fbc`，运行中的 harness 同此）。
> ⇒ **本次升级对每条结论的影响，逐条见 [`ERRATA-alpha.2.md`](ERRATA-alpha.2.md)**；
> 基线、跑法、逐分片判定清单见 [`REALIGN.md`](REALIGN.md)。
> 一句话摘要：**右栏槽位名与 key 规则、band 字面量、`data-plugin-css`、`ui-primitives` 的
> `Button`/`Menu` 签名、以及 `web-styling.md` 的样式硬规则（CSS Modules / tokens / 0.5px 边框 /
> elevation / corner-shape）全部未变**；变了的是 **Session 的 Provider-binding 语义、若干槽位增删、
> Document Preview 的 `loading: 'renderer'` 模式、以及两份逐字件各 1 行**。

**这是什么**：对 DSH 开源仓库（`D:\AI\DSH\deepseek-harness`）官方文档的**分片精读**，
覆盖 `docs/`（基线时 167 篇英文正本 / 现 171 篇）与相关 `.agents/notes/`（2056 篇决策记录）中**与插件开发相关的部分**。

**为什么在这里**：业主 2026-09-19 要求「**把 DSH 官方文档全部读一遍，免得以后开发的时候自己造轮子**」。
背景是同一轮里我们**已经造了两次轮子**（详见 `DEVELOPMENT-HISTORY.md` §10.126）：
① 用 HTML 手搓仿真界面（业主判定「啥呀这是」）；
② 手搓卡片/徽章/输入框，而官方 `ui-primitives` 早就有 `Tag`/`Pill`/`Input`。

**怎么用**：动手写插件代码**之前**，先按下面的索引找对应分片，再看它的
「不许自己造的东西」一节。**不要重新冷启动去读 2.8 MB 原文。**

⚠ **分片是二次加工**（含 file:line 出处）。**要改 DSH 侧的行为时，仍以原文为准**。
原文**已逐字入库**：171 篇 `docs/` 英文正本全部在 Hindsight 里（doc_id 前缀 `dsh-docs-`），
账本见 [`INGEST-LEDGER.md`](INGEST-LEDGER.md)，入库/复核脚本
`scripts/ingest-dsh-docs-into-memory.mjs`（**逐字级核对**：库里 `original_text` 的 sha256 = 磁盘文件 sha256）。

---

## ✅ 已入 Hindsight 记忆（2026-09-19，业主指令「把文档存入记忆」）

| 记忆条目 | doc_id | 内容 |
|---|---|---|
| DSH 官方开发：不许重复造的现成件 + 硬约束 + 静默失败陷阱 | `dsh` | 我汇总的**导航 + 提炼**层（先读这条） |
| DSH 分片 A — 客户端插件（右栏 UI） | `dsh-a-ui` | 现成能力 / 槽位目录 / 不许自己造 / 坑 |
| DSH 分片 B — 插件契约与生命周期 | `dsh-b-effect-26` | 导出形状 / effect 可逆性 / 26 条现成能力 / 坑 |
| DSH 分片 C — 官方菜谱 24 条 | `dsh-c-24` | 菜谱索引 / 生成物与门禁 / 现成能力 / 坑 |
| DSH 分片 D — 宿主半边 | `dsh-d-llm-projection` | 工具注册 / LLM 流式 / 会话与 projection / 子代理 |
| DSH 分片 E — 持久化三通道 / ctx.fs / 配置 / 事件 | `dsh-e-ctx-fs` | 三条持久化通道 + 三个目录类生成物的查法 |
| DSH 分片 F — 破坏性变更 / 事故复盘 / i18n | `dsh-f-i18n` | 变更时间线 / 复盘纪律 / 静默失败规定 |
| DSH 分片 G — 客户端 UI 决策记录 | `dsh-g-ui-inject-vs-external-peer` | 右栏契约 / 样式规定 / inject vs external / 被否决的做法 |
| DSH 分片 H — 官方技能与门禁 | `dsh-h-12` | 12 个技能 + 门禁清单 + 该复用而非自造的流程 |
| DSH 原文 `docs/web-styling.md` | `dsh-docs-web-styling-md-web-ui-style-reference` | **字节级**（2026-09-19 已由脚本原地覆盖旧手抄版） |
| DSH 原文 `docs/AGENTS.md` | `dsh-docs-agents-md-agents-md-the-documentation-standard` | **字节级**（同上；id 里 `agents-md-` 重复是历史遗留，见脚本注释） |
| Correction：手抄失真 + 「禁止手抄长文档入库」纪律 | `correction-dsh-docs-agents-md` | 更正与纪律（**仍然有效**，但"只能手抄"这一条已被脚本取代） |
| **171 篇官方原文（整批）** | `dsh-docs-*`（每篇一个 id，见账本） | **字节级逐字**，2026-09-19 由 `scripts/ingest-dsh-docs-into-memory.mjs` 灌入并逐篇核对哈希 |

**现在没进记忆的语料**（别再以为"都在库里"）：

| 语料 | **实测规模** | 状态 |
|---|---|---|
| `.agents/notes/` 决策记录（非 zh） | **1105 篇 / 7.6 MB** | ⚠ 只入了**与客户端/UI 有关的 10 篇**（`dsh-notes-client-ui`）；其余未入 |
| `docs/**/*.zh.md` 中文译本 | **166 篇 / 2.7 MB** | ✅ 已入（`dsh-official-docs-zh`，账本 `INGEST-LEDGER-docs-zh.md`） |

> ⚠ **更正**：本节此前写「2056 篇 / 14.3 MB」「约 158 篇」——两个数都是从分片转述里抄的、**没实测**。
> 现在的数是 `git ls-files` 实测出来的。教训同 §10.129：**转述的数字要回原始来源核**。
>
> 历史更正（留痕）：本 README 曾写「没进记忆的：其余 165 篇」，理由是
> ① Hindsight 插件故意对子代理关闭（`origin === "subagent"` 直接返回 undefined）；
> ② 手抄 77 行错 2 处（**2.6% 失真**）⇒ 逐字搬运不可信。
> **这两条只否掉了"手抄"这一条路**：2026-09-19 改为**直连 HTTP API、从磁盘按字节读**，
> 既不经子代理也不经我的上下文 ⇒ **171/171 已入且逐字核对通过**。
> 原文权威性仍以磁盘为准。

---

## 分片索引

| 分片 | 读的范围 | 回答什么问题 |
|---|---|---|
| `dshdocs-A.md` | `docs/subsystems/`：sidebar-right、web-client、client-modules、client-resources、slots（+ 一层 package README） | **客户端半边怎么写**：tab 类型/正文/标题/guide 槽位、资源地址、`useResource`、静默失败清单 |
| `dshdocs-B.md` | `extensions.md`、`cordis-primer.md`、`cordis-tutorial/`×8、`cordis-api/`×6、`capability-seams.md`、`user/develop/framework/`×3 | **插件契约与生命周期**：`Plugin.Base`、`Config` 必须是 Schemastery、`ctx.effect` 可逆性、`inject` 是持续的 |
| `dshdocs-C.md` | `cookbook/`×11、`user/guide/`×7、`user/develop/basic/`×4、`practice/`×3、`development.md`、`architecture.md`、`CONTRIBUTING.md` | **官方菜谱 24 条** + 生成物/门禁清单 + **CONTRIBUTING 明说不收外部 PR** |
| `dshdocs-D.md` | `subsystems/tools.md`、`skills.md`、`session.md`、`session-projection.md`、`subagent.md`、`llm-streaming.md`、`tool-catalog.md` | **宿主半边**：`defineTool` 注册、handler 只返回 JSON 且错误必须 throw、`ctx.llm.stream` 只有流式、`session.append`、`ctx.subagents` |
| `dshdocs-E.md` | `persistence.md`、`filesystem.md`、`workspace.md`、`settings.md`、`event-producer-consumer.md`、`module-graph.md`、`persistence-catalog.md`、`config-catalog.md` | **持久化/配置/事件/文件**三条互不替代的通道 + 三个"目录类生成物"怎么查 |
| `dshdocs-F.md` | `releases/`×27、`postmortem/`×5、`i18n/`×5、`persistence-changes/`×4、其余 subsystems | **破坏性变更 + 事故复盘给出的纪律 + 因"静默失败"而立的规定** |
| `dshdocs-G.md` | 12 篇客户端 UI **决策记录**（`sidebar-tab-types-and-navigation`、`client-resource-model`、`shared-client-control-primitives`、`client-plugin-loading-model`、`client-shells-and-dynamic-packages`、`desktop-bundled-runtime-and-external-plugins`、`right-sidebar-docking-infrastructure`、`sidebar-default-pages`、`plugin-owned-message-projections`、2 篇 rejected 等）+ `web-styling.md` + `packages/client/AGENTS.md` + `tsdown.client.ts` | **样式的权威规定**、`inject` vs `external`、**外置插件必须声明 peer**、`ctx.sidebarRight` 只管控制不管读、被否决的设计 |
| `dshdocs-H.md` | `.agents/skills/`×12（`dsh-code-review`、`dsh-doc`、`dsh-prose-standard`、`dsh-pre-push-checks`、`dsh-find-simplifications` 等）+ `development.md` 门禁 + `scripts/run-gates.ts` | **官方技能与门禁清单**：该复用哪套流程、每道门禁防哪类漂移 |

**未覆盖**（诚实标注）：`releases/` 里纯内核内部变更；`persistence-changes/historical-formats/`（归档旧格式，518 KB）；
`i18n/translation-prompt.md` 的全文；`user/` 面向终端用户的产品指南。

---

## 读完之后，已经指向我们自己的 6 条（摘要，逐条见对应分片）

1. **样式**：官方「Use CSS Modules + `clsx`」；我们的 esbuild 无 CSS loader ⇒ 运行时注入是被迫偏离，
   且 `ksGuideStyles.ts` 里 **1px 中性边框违反「中性边框统一 0.5px」**（`dshdocs-G.md` / `web-styling.md`）。
2. **文案**：官方「Locale dictionaries own all product-authored client UI copy」；
   我们**硬编码了中文**（「知识库」「文件导入」…）。门禁 `verify-client-ui-i18n` **管不到仓外**，所以它不报错——这是缺口。
3. **组件**：官方组件目录里有 `Tag`/`Pill`/`Input`/`DisclosureRow`/`StateDot`；我们手搓了徽章与芯片。
4. **PDF**：宿主 `ui-sidebar-documentpreview` **自带 pdf 预览**（`extensions:['pdf'], priority:'builtin'`）⇒
   我们的 `ks-evidence` 在"能看 PDF"这一层是**重叠**；差异化应明确写成**条款级证据导航**。
5. **外置插件合规**（⚠ **本条已被 alpha.2 推翻，见 `ERRATA-alpha.2.md` §I**）：旧文要求外置插件把共享宿主包
   声明为 **peerDependencies** 并拒绝嵌套/别名副本；alpha.2 把该套校验**有意移除**（理由是它重复了
   包管理器与 loader 的职责、且会拒掉 pnpm 支持的安装源）：「External plugins use normal Node package
   resolution…」⇒ 我们的 `plugin/package.json` 只声明了 cordis / dsh-tools / dsh-llm / ui-sidebar-right，
   **不补就是对的**，而不再是一条合规缺口。
6. **宿主半边合规**：工具注册官方口径是 `ctx.tools.register(defineTool({...}))`、handler 只返回 canonical JSON 且**错误必须 throw**；
   会话/插件状态官方通道是 `ctx.settings` / `ctx.storageDomain` / `session.append`——而我们把 chat-mode 开关写在 `.json` 文件里。

（第 6 条**尚未核实我们代码的实际写法**，属于"待核查项"，不是结论。
第 5 条已核实：`plugin/package.json` 只声明那 4 个依赖，且 alpha.2 之后**不需要**补 peer。）
