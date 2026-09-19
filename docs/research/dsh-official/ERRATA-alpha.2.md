# 勘误：`alpha.1 → alpha.2` 对 8 份分片与记忆条目的影响

**写给谁**：以后读 `dshdocs-*.md` 或从 Hindsight 取 `DSH 分片 …` 条目的人。
**一句话**：那些分片与条目是按 **`dsh-v0.1.6-alpha.1`**（sha `0a15e36e7f`）写的；
**当前基线是 `dsh-v0.1.6-alpha.2`**（sha `ddefc45fbc`，业主 2026-09-19 升级完成）。
下面逐条列**哪句话过期了、现在是什么**。没列到的，就是**核过没变**。

> **核过没变、可继续照用的**：`docs/web-styling.md` 的 **CSS Modules / `--dsw-alias-*` token /
> 中性边框 0.5px / elevation / corner-shape** 全部未改（该文件这次只改了第 27 条「可点击链接」那一行）。
> 右栏的**槽位名与 key 规则**（`sidebar.right.pane.tab`、`…pane.tab.title`、`guide`、`guide.entry`、
> `menu.item`、`key` 用**定义 id**）、**band 字面量 `'extension'`**、**`data-plugin-css` 注入标记**、
> `ui-primitives` 的 `Button`/`Menu` **签名与导出写法**——全部未变（已用脚本逐条探过）。

---

## A. 两份逐字件：各改了 1 行（**旧的已过期**）

### A1 `docs/web-styling.md` 第 27 条

**旧（我们入库的那版）**
> …Text-leading anchors also lead with the ui-primitives `LinkIcon` category glyph riding `currentColor`; workflow member links…

**新（alpha.2）**
> …Compact Thinking Markdown keeps tertiary text color and a resting dotted underline ([compact presentation](…2026-09-17-thinking-markdown.md)). Text-leading anchors also lead with the ui-primitives `LinkIcon` category glyph riding `currentColor`, **which for a well-known external host is that site's own mark instead of the globe**; workflow member links…

⇒ 影响：分片 G 引用的该条要补这两点（紧凑 Thinking Markdown 的下划线、知名站点用站点自己的图标）。

### A2 `docs/AGENTS.md` 第 41 条

**旧**
> - **Every non-trivial change includes at least one Agent Note in the same PR.** Update the owning note or add one; only mechanical/local edits are exempt.

**新**
> - **Apply the Agent Note creation criteria.** Mechanical/local edits are exempt, **including local UI changes**; keep existing owning notes accurate.

⇒ 影响：我记忆里"**非平凡改动必须同 PR 带 Agent Note**"要改口径：**改为"适用创建判据"，且局部 UI 改动明确豁免**。这是**放宽**，不是收紧。

---

## B. 右栏契约：**语义与选项有增改**（分片 A / G 的命根子）

| # | 变化 | 新内容（原文要点） | 对我们 |
|---|---|---|---|
| B1 | **出货 tab 类型多了 `browser`** | 出货类型表由 `text` / `files` 变为 `text` / `files` / **`browser`** | 分片 A 的"出货类型"清单要加一项 |
| B2 | **多了一个打开入口** | `openTab` 的触发者里新增「**Assistant Markdown 里的 HTTP(S) 链接**」 | 助手回复里的链接会开浏览器页；我们若也想接管链接要留意先后 |
| B3 | **新选项 `preferNewPane`** | 「Prefer a new docked pane under the normal pane budget and room rule; fall back to the target pane when it cannot split. **Ignored with `replaceTab`**.」 | 我们的 `openTab` 可考虑用它（想并排时） |
| B4 | **Document Preview 新增 `loading: 'renderer'`** | 三种取值：`text-pages` / `bytes-complete` / **`renderer`**。renderer 收到 `{ kind: 'renderer', revision, loaded, reload }` **而不是文件字节**；body 用自己注入的回调加载、在 revision 变化与卸载时取消、用 `loaded(version)` 上报已显示的源版本；父级忽略过期上报并保留共享的 reload/换源控件。**Office 用它请求宿主渲染的 PDF** | ⚠ **与我们自建的 PDF 查看器直接相关**：官方现在有一条"渲染器自己管加载"的正规通道，且 Office→PDF 走的就是它 |
| B5 | `binaryExtensions` 语义补全 | 「Suffixes declared in `binaryExtensions` **suppress the plain-text alternative**」 | 若要注册 pdf 渲染器，纯文本备选不会再抢 |
| B6 | **两个新页面类型** | `browser`：多实例 `builtin`，`openTab('browser', { params: { url? } })`，接受公网与 loopback HTTP(S)、**拒本地文件**（让给 Document Preview）、自带应用内 iframe 历史。<br>`subagentchat`：`builtin`，地址形如 `dsh-resource://subagentchat/session/<child>?parent=<parent>&mode=<mode>`，由资源 provider 持有并渲染 | 分片 A 的"页面类型"节要补 |
| B7 | deferred 措辞 | 由「用户可撤销 + 内容导航栈 + tab 图标」改为「用户可撤销 + **通用跨类型内容导航栈**；**Browser 只拥有自己的页历史**」 | 分片 A 的"未解答/deferred"要更新 |

---

## C. Session 与 Slot：**从"当前选择"改成"Provider 绑定"**（分片 A / B 受影响）

| # | 变化 | 新内容 |
|---|---|---|
| C1 | **scope 语义** | `session-maybe`：由「Follows current selection but stays renderable without a Session」改为「**Inherits the surrounding Provider binding** but stays renderable without one」。`session`：由「Requires a resolved Session binding」改为「**Requires a resolved surrounding Provider binding**」 |
| C2 | **`SessionProvider` 覆盖面变大** | 以前只在 entry 声明**严格 `session`** 子项时出现；现在 **`session` 或 `session-maybe`** 都有。无 `session` prop 时**继承外层绑定**；显式 `SessionReference` 或 `undefined` **只覆盖那棵子树**。**Provider 不 key 整个 body**。严格 `session` 在 **binding generation 变化**时 remount；空的 `session-maybe` **采用首个绑定且不 remount**，之后 generation 变化或回到缺失态才 remount |
| C3 | **标准 props 增删** | 「every scope」行：`useSessions`、`useSessionPendingInteraction` → **`useSessions`、`useSessionStatus`、`useSessionRetainInfo`**（**`useSessionPendingInteraction` 被移出该行**） |
| C4 | **不再有"全局当前 Session"** | Web Client 里 `ClientSessions`：由「owns Session scopes and stable `SessionBinding` objects, and projects the selected list state」改为「owns **references, source counts**, Session scopes, and stable `SessionBinding` objects, and projects **catalog** state **without selecting a global current Session**」；`ui-session` 发布 `useSessions`、**`useSessionStatus`**、**`useSessionRetainInfo`**、`useSession`、`sessionId`、`useProjection`，且 **`SessionProvider` 可继承外层绑定或绑定显式 `SessionReference`** ⇒ **并发子树可指向不同 Session** |
| C5 | **槽位树新增/移位** | 新增 **`plugins.item`**、**`plugins.bundle.config`**、**`plugins.row.config`**（原 `settings.plugin.item` **不在该位置**）、**`conversation.session.header.leading`**、**`conversation.plan-review.actions`** |

⇒ 影响：分片 A 的「会话/工作区数据」行（列了一串 hook）与「槽位目录」表都要按上表改；
分片 B/C 里凡引用 `settings.plugin.item` 的（来自 settings-card cookbook）要核到新的 `plugins.*` 家族。

---

## D. 客户端模块加载：**文案与两处 API 变了**（分片 A）

| # | 旧 | 新 |
|---|---|---|
| D1 | "content-addressed combo script" / "Content-addressed combo script endpoint" | **"revisioned combo script"** / "Revisioned combo script endpoint" |
| D2 | 「Startup combo revisions hash the combined plugin script bytes and indexed source map」；组合期会拼接 | 「…URLs contain only the ordered package-resource list and a revision **derived from those row revisions**」；组合**不拼接脚本、不读 map**；**首个 `GET` 才拼接一次并缓存**；map 由**首个 map `GET`** 读取校验并缓存 |
| D3 | `fetchBundle(request: Request): Response` | **`async fetchBundle(request: Request): Promise<Response>`** |
| D4 | `rebuilt(id)` = "Re-hash one bundle" | = "**Publish one completed bundle generation**" |
| D5 | HMR 段：「在开发中…**生产环境的图完全不含 HMR 行；module host 自身从不监视文件**」 | 「`dsh-client-hmr` **在出货的 Web 组合里**提供实时图快照。Host 立即转发已有的图变化通知，**重连时发当前完整图**。图描述的是"期望的浏览器入口"，**不保证 Host 侧清理已完成**。**它的 artifact poll 单独上报 rebuilt revisions**。…Client Modules 负责校验快照、串行化与重建的对账，并拥有 boot 建立的入口表、单资源到达、**异步移除**、**未用模块/样式清理**与页内重试状态。静态平台模块与 bootstrap 保留整个页面生命周期；**Electron 安装是另一条流程**」 |

### ⚠ D5 推翻了我此前反复说的「必须重启宿主才能看到插件改动」

- 我那条说法所依据的，是 **alpha.1 文档里那句"生产环境的图完全不含 HMR 行"**。
- 实测：**`@deepseek-ai/dsh-client-hmr` 在 alpha.1 就已经在出货组合里**
  （`packages/bundle/web-app/cordis.patch.yml` 的 `client-hmr` 行：alpha.1 `:166-167`、alpha.2 `:167-168`）。
  ⇒ 那句话与出货组合**不一致**，我据此下的结论**不成立或至少未经证实**。
- alpha.2 的措辞则明确：出货组合里有 HMR 行 + 有 **artifact poll** + 浏览器侧做 **reconciliation/cleanup**。
  ⇒ **插件 bundle 变化很可能不需要重启宿主**（改完 `client.js`，刷新页面即可）。
- **诚实边界**：这是**文档口径**的结论，我没有在浏览器里实测过（我看不到 GUI）。
  **正确的判定方式**：改一处可见文案 → `npm run build:client` → **刷新页面**看变没变；没变再重启宿主。

---

## E. 新增 4 篇文档（**新子系统**，分片里没有）

| 新文档 | 行数 | 是什么 |
|---|---|---|
| `docs/subsystems/boot.md` | 159 | **boot** 子系统（配新包 `packages/boot/hmr`、`packages/boot/plugin-manager`） |
| `docs/subsystems/deliverables.md` | 150 | **deliverables**（配 `packages/deliverables/tool-present`、`workspace-changes`）——把一轮的工具结果/工作区变更做成可评审产物 |
| `docs/subsystems/office-to-pdf.md` | 60 | **Office → PDF**（配 `packages/document/office-to-pdf`、`packages/skill/skill-office`），宿主渲染 PDF 供 Document Preview 的 `renderer` 模式消费 |
| `docs/persistence-changes/2026-09-14-workspace-changes-event.md` | 34 | 新的持久化事件 **workspace-changes** |

⇒ 这 4 篇**没进任何分片**。要不要补进记忆，取决于我们是否会碰这三块（**office-to-pdf 与我们相关**——它决定"台账式预览"要不要自建）。

---

## F. 升级本身在检出里留下的**本地补丁**（**必须知道，否则会丢**）

业主这次升级"废了好大劲"，成果一部分是 **6 个文件、+19/−6 的未提交改动**：

| 文件 | 改了什么 | 为什么 |
|---|---|---|
| `packages/api/session-controller/src/client/sessions/manager.ts` | `baseline.jobs` → `baseline?.jobs ?? {}`、`baseline.projections` → `baseline?.projections ?? {}` | baseline 可能为 undefined 的**空安全** |
| `packages/api/session-controller/src/control.ts` | `Object.create(null)` → `{}`（两处） | 估计是序列化/克隆口径 |
| `packages/boot/app-boot/src/profile-resolution/resolver.ts` | fallback 路由用 `canonicalPath(route.entry.declarer)` | **profile 插件解析**的路径规范化 |
| `packages/core/tools/src/index.ts` | `TOOL_RUNTIME_SCHEDULER` 由 `Symbol('…')` 改为 **`Symbol.for('@deepseek-ai/dsh-tools.scheduler')`**，并新增调度器缺失时的显式报错 | 见下 |
| `packages/core/tools/src/ptc.ts` | 引入 `TOOL_OUTCOME_UNKNOWN` + 注释 | 未配对的 `tool_use` 会让会话后续请求全被拒 |
| `packages/ptc-runtime/ptc-runtime/src/index.ts` | 1 行 | 同上 |

**`Symbol.for` 那条是本轮最有价值的教训**（补丁注释原文）：
> 「Registered with `Symbol.for`, NOT `Symbol`: this module is reached through **more than one specifier URL** at runtime
> （the workspace copy, **the profile junction copy**, and the `lib/` vs `lib/types/` build artifacts）.
> A fresh `Symbol()` per copy means the registry's key and the consumer's key are two distinct symbols with the same
> description, so `registry[TOOL_RUNTIME_SCHEDULER]` resolves to `undefined` and **every tool call dies with
> "Cannot read properties of undefined (reading 'prepare')"**.」

⇒ **三条结论**：
1. **alpha.2 在本机是需要补丁才能跑的**（至少这几处），别以为升级完就是"纯 alpha.2"；
2. 这些补丁**没有提交**（`git status` 里是 `M`），**下次升级/`git checkout` 会丢**——要么落成正式提交、要么记档；
3. 它暴露的**"同一模块经多个 specifier URL 到达 ⇒ 模块级单例（Symbol/WeakMap/缓存）身份分裂"**，
   **与我们同构**：我们的插件也是**经 junction**（`C:\Users\Zegel\dsh-ks-src\ks-dsh-plugin` → 本仓 `plugin/`）被加载的。
   ⇒ 我们代码里若用模块级 `Symbol()`/`WeakMap`/单例缓存，要留意同样会分裂；**优先 `Symbol.for`**。
   （另有一个未跟踪的 `resolver.ts.bak-2026-09-19T03-59-45-176Z`，是手工编辑的残留，建议清理。）

---

## G. 我们插件的当前状态

| 项 | 值 |
|---|---|
| 加载路径 | `ks-dsh-plugin` → Junction → 本仓 `plugin/`（升级**未改动**它） |
| `client.js` sha256（前 16） | `14BB55F7DABCC970`（与升级前**一致**） |
| 门禁 | 见本仓 `DEVELOPMENT-HISTORY.md` 的对应条目（升级后已重跑） |

---

## H. 还**没有**核到的（诚实边界）

- `referenced-files.txt` 是**抽取下限**：分片里用相对路径写的引用抓不到，所以「没列进勘误」≠「没变」。
  要更全：按每份分片自己声明的"读取范围"，用 `git diff <alpha.1> <alpha.2> -- <目录>` 逐个复核。
- `docs/persistence-changes/` 整目录这次的变化未逐条读（只知新增 1 篇）。
- `.agents/notes/` 这次 **366 条**变化（新增 240 / 修改 241 全仓计），我**没有**逐条读；
  分片 G 依赖的那 12 篇决策记录是否被改，**待查**（命令：`git diff --name-status alpha.1 alpha.2 -- .agents/notes`）。
- `ui-primitives` 改了 **+1394/−81**，我只核了**我们用到的** `Button`/`Menu`/`IconChevronDownOutline14`
  与计划采用的 `Tag`/`Pill`/`Input`/`Checkbox` 等的**存在性与签名写法**，**没读它们的 prop 细节**。
  真要改用它们时，必须按 **alpha.2 的 README** 逐项核。
