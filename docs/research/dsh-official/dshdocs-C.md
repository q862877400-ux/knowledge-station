# DSH 文档消化 · 面向「在 DSH 内做功能」的插件作者

> 已读：`docs/cookbook/*`(11) · `docs/user/guide/*`(7) · `docs/user/develop/basic/*`(4) · `docs/user/develop/practice/*`(3) · `docs/development.md` · `docs/architecture.md` · `CONTRIBUTING.md`。少数处补引这些文件自己点名的权威文件（`AGENTS.md`、`docs/testing.md`、`package.json`、`docs/AGENTS.md`），均标真实路径。

## 官方菜谱索引

| 想做的事 | 官方菜谱（文件 + 关键步骤要点） | 出处 file:line |
|---|---|---|
| 跑起第一个本地插件 | `basic/index.md`：`scratch-plugin/src/*.ts` 导出 `name`+`apply` → `cordis.yml` 用 `- insert:` 挂 → `pnpm dsh web --patch ./scratch-plugin/cordis.yml`。> "The plugin path must be absolute." | docs/user/develop/basic/index.md:33,46,56,61 |
| 加一个 model-facing 工具 | `adding-a-tool.md`：`ctx.tools.register(defineTool({name,description,parameters,output:{schema,render},execute}))`；再读 execute 契约、`ctx.jobs.start` 长任务、`presentCall/presentResult` 卡片 | docs/cookbook/adding-a-tool.md:9,17,40,51,67 |
| 工具放进 PTC / 免集成 | 注册即可：> "every visible registered tool is available as `await tools.<name>(args)` without extra integration" | docs/cookbook/adding-a-tool.md:61 |
| 插件配置 | `basic/config.md`：导出 `interface Config` + 同名 Schemastery `Config` schema，默认值写字段上 → `cordis.yml` 的 `config:` | docs/user/develop/basic/config.md:11,23,34 |
| 打包 / 安装插件 | `basic/publish.md`：**bundle**（`dsh.bundle` → `cordis.patch.yml`）vs **profile**（`dsh.profile` → 有序 `bundles`）；`dsh plugin --profile demo add ./hello-plugin`；`--dump-config` 验证层 | docs/user/develop/basic/publish.md:13,42,80,106 |
| 从 git 装插件 | 作者必须给 `prepare` 脚本（自包含）；用户必须在 `pnpm-workspace.yaml` 写 `allowBuilds` | docs/user/develop/basic/publish.md:161-173 |
| 给 surface bundle 自己的命令行 | 挂 provider 插件，`inject=['cmdlineArgs']` + `parseCmdline`，行配置用 `!!js ctx.myAppStartup.port ?? 8080` | docs/user/develop/basic/publish.md:130-151 |
| 加设置卡（Web 设置页） | `adding-a-settings-card.md`：Host `ctx.settings.installSection(...)`；Client 注册进 `settings.plugin.item` 键槽；`ctx.settingsScope.bind({namespace})` 读写 | docs/cookbook/adding-a-settings-card.md:11,36,50,62 |
| 加 Remote API（Host↔Client） | `adding-a-remote-api.md` 五步：`extends TypertRemoteService`+`@Remote('list')` → 合并 `RemoteErrorDetailsMap` → manifest `./typert`+`./remote` → Client `inject:['remote','remote.notes']` 直接 `ctx.remote.notes.list()` → 双方 spec | docs/cookbook/adding-a-remote-api.md:9,38,53,92,109,150 |
| 加 LLM adapter | `adding-an-llm-adapter.md` + `practice/llm-adapter.md`：`extends LlmAdapter` 实现 `stream()`，`ctx.llm.registerAdapter(['my-provider'], adapter)` | docs/cookbook/adding-an-llm-adapter.md:10,19 / docs/user/develop/practice/llm-adapter.md:46 |
| 加一个 workspace 包 | `adding-a-package.md` 五步：建目录（package.json/tsconfig/src/README）→ 注册进 `tsconfig.host.json` **或** `tsconfig.client.json` → 定 topology 命名 → README Model Experience + Known Limitations → verify | docs/cookbook/adding-a-package.md:9,31,40,72,108 |
| vendor 一个上游 Cordis 包 | `adding-a-vendored-package.md`：拷到 `vendor/`、rescope name、`paths`+`references`、**同步** `vendor/README.md` 清单 | docs/cookbook/adding-a-vendored-package.md:7,36,42 |
| 加 Session 日志格式版本 N+1 | `adding-a-session-format-version.md` 六步：选版本/release 基 → identity edge 包（`dsh.sessionFormatMigration {from,to}`）→ Stage 接口 → 更新 current-version 消费者 → snapshot successor → validate | docs/cookbook/adding-a-session-format-version.md:20,33,50,86 |
| 改持久化类型 | `reviewing-persistence-type-changes.md`：`.artifacts/persistence-change.prose.json`（en+zh 各 summary/compatibility/verification）→ `pnpm --silent run persistence-changes --record <date-slug> --prose … --json` → `pnpm run doc-sync` | docs/cookbook/reviewing-persistence-type-changes.md:39,61,74 |
| 三角色能力（Definition/Provider/Consumer） | `practice/index.md`：三步照抄（abstract Service → provider `ctx.plugin` → consumer tool）+ `cordis.yml` 两行 | docs/user/develop/practice/index.md:60,90,111,140 |
| 运行时动态挂载插件 | `practice/dynamic-cordis.md`：`pnpm dsh web --patch apps/cli/config/examples/cordis/cordis.yml` | docs/user/develop/practice/dynamic-cordis.md:12 |
| 拦截/放行工具调用 | `extension-cookbook.md` hook 例：`ctx.on('tools/pre-execute', async (exec,next)=> next() 或 {kind:'deny',reason}` | docs/cookbook/extension-cookbook.md:13,23 |
| 给单个会话不同能力集 | compose an agent preset；服务行需要 `isolate` realm | docs/architecture.md:143 |
| 挂 MCP server | `guide/mcp-memory.md`：一行 `@deepseek-ai/dsh-mcp-client`，`transport: stdio`+`command/args/env/cwd`；工具暴露为 `mcp__<serverName>__<tool>` | docs/user/guide/mcp-memory.md:11,88 |
| 定时提醒 | `guide/schedule.md`：`schedule_create/list/delete`，overlay 开启；或 `extension-cookbook.md` 的 cron 行 | docs/user/guide/schedule.md:11 / docs/cookbook/extension-cookbook.md:127 |
| webhook 起 review Session | `guide/github-review.md`：`ctx.webhookRuntime` 规则 + `POST /github` 隔离 realm | docs/user/guide/github-review.md:38,42,68 |
| Web Client 业务节点 | 注册 `ConversationNodeDefinition` + `conversation.chat.node` 键渲染器 | docs/cookbook/extension-cookbook.md:129 / docs/architecture.md:154 |
| Python SDK 安装插件 | `dsh --profile sdk-minimal --dump-default-config` → `dsh plugin add file:…` → 或从 Python 传 `patches=` | docs/user/guide/python-sdk.md:110,117,128 |
| 想给仓库提 PR | **不行**：> "we cannot accept external pull requests at the moment."；改走生态：插件 + `dsh-plugin` topic | CONTRIBUTING.md:9,14-15 |

## 开发流程规范

- 命令权威在 root `AGENTS.md#commands`（`development.md:137` 指向它）：`pnpm install` · `pnpm run typecheck` · `pnpm run lint` · `pnpm run test`（unit） · `pnpm run test:coverage`（**CI 覆盖门**，不是 `test`） · `pnpm run test:e2e` · `pnpm run test:snapshot` · `pnpm run build` · `pnpm run hygiene` · `pnpm run doc-sync` · `pnpm run test:docs` · `pnpm run constraints` · `pnpm run check:all`（可选）。AGENTS.md:83-103 / package.json:20-181
- 首次克隆：> "Setup is complete when `pnpm run typecheck` exits successfully." development.md:48
- `typecheck` = `build:lib:host` 后再 `tsc -b tsconfig.client.json`；`build` = 按依赖序 host tsc→tsdown→client tsc→tsdown→`build:web`。development.md:74-84 / package.json:45-46
- > "Select the smallest checks that cover the changed surface." development.md:137
- > "Never default to the full suite or repeat a passing check for commit or push. CI owns exhaustive coverage and the platform matrix." AGENTS.md:114
- **自动查 drift 的生成文件（绝不手改）**：`config-catalog.md`、`tool-catalog.md`、`cordis-api/{context,events,fiber,inherited,registry,service}.md`、`persistence-catalog.md`、`module-graph.md`、`capability-seams.md`/`agent-lifecycle.md`/`event-producer-consumer.md`/`graph-atlas.md`/`tool-execution-pipeline.md`、以及每个 `subsystems/*.md` 的 `cordis-surface` 区块。典型措辞：
  - > "This file is GENERATED from source (`scripts/gen-config-catalog.ts`) and verified fresh by `pnpm run verify-config-catalog` (part of `doc-sync`) — do not edit it by hand." docs/config-catalog.md:8
  - > "This file is GENERATED and verified fresh by `pnpm run verify-tool-catalog` (part of `doc-sync`) — do not edit it by hand." … `tool-catalog.md:8` 还带**完整性守卫**：glob `packages/*/tool-*`，任何包漏进 boot manifest 即失败，> "so a new tool cannot be silently undocumented."
  - > "verified fresh by `pnpm run verify-cordis-catalog` (part of `doc-sync`) — do not edit it by hand." docs/cordis-api/inherited.md:8
- 生成命令：`pnpm run gen-config-catalog` / `gen-tool-catalog` / `gen-cordis-catalog` / `gen-doc-graphs` / `gen-persistence-catalog` / `gen-module-graph` / `gen-session-format-catalog`；对应 `verify-*` 是 `--check`。package.json:146-178
- `ts type-equiv` / `ts public-api` fence：> "To keep a paste from drifting when source changes, fence it as ` ```ts type-equiv ` … and register it in `scripts/type-equiv.manifest.json`"；`pnpm run verify-type-equiv`（doc-sync 内）> "fails until you update the paste"。development.md:171-177
- Git hooks（`pnpm install` 自动装 lefthook）：`pre-commit` 校验 pairing / `.oxlintrc.staged.json` + 一次自动修 / 重新生成 `THIRD_PARTY_NOTICES.md` / whitespace / **vendor manifest guard**；`pre-push` 跑 typecheck。> "the hooks intentionally do not run tests, snapshots, documentation checks, builds, or hygiene." development.md:117-125
- vendor guard：> "`scripts/check-vendor-manifest.sh` (a pre-commit hook) fails if anything under `vendor/*/src` is staged without `vendor/README.md` also staged." docs/cookbook/adding-a-vendored-package.md:49
- 文档写作门（`docs/AGENTS.md`）：一行一段（`verify-md-wrap`）；改文档化类型必须**同一改动内**更新 owning subsystem page（`verify-type-equiv` 只抓 drift，不抓从未文档化的新类型）；`scripts/doc-budgets.manifest.json` + `verify-doc-budgets` 有字数上限。docs/AGENTS.md:41,43,50,58
- 双语：`pnpm run verify-translation-pairing --write <doc>`；`git merge` 由 `dsh-translation-pairing` merge driver 处理配对记录；冲突后 `pnpm run resolve-translation-pairing-conflicts`。adding-a-session-format-version.md:101 / development.md:32,113
- 非机械改动：> "Non-trivial changes MUST include an Agent Note in the same PR; only mechanical/local edits are exempt." AGENTS.md:146
  > ⚠ **本条已被 alpha.2 放宽**（官方 `docs/AGENTS.md` 改成了「**Apply the Agent Note creation
  > criteria. Mechanical/local edits are exempt, including local UI changes**」）⇒ 见
  > [ERRATA-alpha.2 §A2](ERRATA-alpha.2.md)。**引用本条时请以 ERRATA 为准。**
  > （2026-09-19 加这个反向指针：本分片是"动手前的权威导航层"，过期规则留在这里会被再引用一次。）
- 快照义务：> "Every non-trivial model-, protocol-, or human-visible change adds or updates a keyless recorded-session scenario in the same PR"（`pnpm run test:snapshot`；改模型转录用 `test:snapshot:record`，replay 输入不变用 `:refresh`）。AGENTS.md:148 / testing.md:14,55
- 产品可见插件要真组合测试：> "Product-visible plugins require a non-unit REAL-composition test. Hand-built `ctx.plugin(...)` suites are insufficient"；每个 registry 都要 HMR 安全测试（dispose 贡献 fiber、断言清理）。testing.md:39,9

## 现成能力清单

| 能力 | 官方 API | 出处 |
|---|---|---|
| 工具注册（schema 自动进 system prompt 组装） | `ctx.tools.register(defineTool({…}))` | adding-a-tool.md:18,38 |
| 工具参数校验 + 类型推导 | `defineTool` 统一 `ParameterSchemaSpec` 校验，`execute` 内 args 即 `InferArgs` | adding-a-tool.md:42 |
| 工具 canonical 返回值 / 渲染 / 展示元数据 | `output.schema` + `output.render` + `output.presentationMeta` | adding-a-tool.md:45,48 |
| 长任务后台作业 | `ctx.jobs.start({kind,label,owner:exec.agent,run})`（cancel/done/readOutput） | adding-a-tool.md:51-55 |
| 可扩展策略门（allow/deny/ask） | `tools/pre-execute` waterfall，返回 `PreToolDecision` | extension-cookbook.md:24 / architecture.md:107 |
| 不可撤销的最终拒绝 | `ctx.tools.guard()`（monotonic） | adding-a-tool.md:59 / extension-cookbook.md:33 |
| 包装 dispatch（超时/重试/指标） | `tools/execute`（只能替换/恢复 `exec.signal`） | adding-a-tool.md:44,59 |
| 结果变换 / 只读观察 | `tools/post-execute` / `tools/result`（不可变最终结果） | adding-a-tool.md:59 |
| 工具集合按上下文收窄 | `ctx.tools.restrict()`（presentation/lookup/execution 对齐） | extension-cookbook.md:102,116 |
| 工具卡（pending/completed） | `presentCall`→`ToolCallView`；`presentResult`→generic/terminal/diff/read/search/web | adding-a-tool.md:73-83 |
| Web Client 工具卡 | `tool.call.toolview` 键槽（Client 插件注册 wire tool name） | adding-a-tool.md:95 |
| 设置页命名空间 + 卡片 | `ctx.settings.installSection()` / `settings.plugin.item` / `ctx.settingsScope` | adding-a-settings-card.md:36,62,72 |
| 密钥字段与凭据 | 字段 `role('secret')`；`credentials` 域；`$DSH_HOME/.credentials.yaml` | adding-a-settings-card.md:46 / providers.md:13 |
| Remote（Host↔Client）方法 | `TypertRemoteService` + `@Remote('name')`；Client `ctx.remote.<ns>.<method>()` → `RemoteResult<T>` | adding-a-remote-api.md:9,38,109 |
| Remote 失败词汇 | 单一 `RemoteError` + `RemoteErrorDetailsMap` 声明合并；`remoteErrorOf` / `isRemoteFailure` | adding-a-remote-api.md:53,151,109 |
| Host 固定事实 | `ctx.remote.$host`（`home`/`isLoopback`），重连用 `ctx.on('connection/reset')` | adding-a-remote-api.md:111 |
| LLM provider | `ctx.llm.registerAdapter(routes, adapter)`；`resolveModel()` / `listModels()` | adding-an-llm-adapter.md:19 / practice/llm-adapter.md:121,116 |
| HTTP 请求归因头 | `attributionHeaders()` | practice/llm-adapter.md:156 |
| 定时/提醒 | Schedule overlay（`schedule_*` 工具；到期在 agent 空闲后 `followup()`） | user/guide/schedule.md:11,17 |
| webhook 入口 | `ctx.webhookRuntime` + 可信规则（`run()` 是普通受信 JS） | architecture.md:148 / github-review.md:76 |
| 子代理委派 | `ctx.subagents` provider 注册表 + `dsh-tool-subagent` | extension-cookbook.md:123 |
| 目标（/goal） | `ctx.goals`（持久状态）+ round driver | extension-cookbook.md:107 |
| 上下文压缩 | `ctx.compaction` seam（自动压力在 `agent/pre-step`，溢出恢复在 `agent/request-error`） | extension-cookbook.md:111 |
| system prompt 分节 | `ctx.systemPrompt.section()`（有序 + scope 局部遮蔽） | extension-cookbook.md:112 |
| 向下一轮注入上下文 | `agent.inject({content, source:{kind:'plugin', plugin}})`（不是唤醒） | architecture.md:152 / adding-a-tool.md:49 |
| 会话事件扩展 | 扩展 `SessionEventMap`；durable + `session/event` 广播 | architecture.md:155 / architecture.md:74 |
| 消息内容变换 | 注册「纯消息投影」`dsh-session-projection` | architecture.md:123 |
| 人工命令（不消耗 turn） | `ctx.commands` | architecture.md:146 |
| 文件系统/策略 | `ctx.fs` provider 或 `fs/*` 事件 | architecture.md:149 |
| 进程约束 | `ctx.sandbox` backend（消费者 spawn 前包 argv） | architecture.md:150 |
| 会话标题 | 注册唯一 `ctx.sessionTitle` provider | architecture.md:156 |
| 持久化后端 | 实现 `SessionPersistence`（create/open/stat/list/export） | architecture.md:159 |
| 作用域限定注册 | `agent.ctx` | architecture.md:160 |
| 品牌化跨边界 id | `dsh-brand` 的 `Branded<B>` / `brandString` | AGENTS.md:137 / extension-cookbook.md:41 |
| 配置热替换（HMR） | 一切注册都是 `ctx.effect`；vendor HMR 自动生效 | extension-cookbook.md:132 / basic/config.md:98 |
| MCP 工具接入 | `@deepseek-ai/dsh-mcp-client`（stdio / streamable-http） | user/guide/mcp-memory.md:11 |

## 不许自己造的东西

- 手写注册/清理记账 → `ctx.effect()` 返回 disposer，`ctx.on()`/注册即 effect：> "You do not need to call removeListener or clearInterval manually." → basic/index.md:66-85；AGENTS.md:125
- 手搓配置校验/默认值 → 导出同名 Schemastery `Config`：> "Do not export a plain object as `Config`; it does not implement the Standard Schema interface required by Cordis." → basic/config.md:45,74
- 把可调参数写死 → > "Harness requires **anything that two deployments may want to set differently to be a configuration field**." → basic/config.md:80,92
- 自己校验工具参数 → `defineTool` 已校验（> "**Args are validated for you.**"），只需补非空/正数/跨字段等 DSL 无法表达的约束 → adding-a-tool.md:42
- 手工把工具 schema 塞进 prompt / PTC 桥接 → 注册即自动进 assembly 与 `await tools.<name>()` → adding-a-tool.md:38,61
- 自己写后台作业框架（轮询/取消/通知/清理） → `ctx.jobs.start()` 提供 id、session fence、通用控制工具、notices、owner 清理 → adding-a-tool.md:51-55
- 把权限逻辑写进工具体 → `tools/pre-execute`（可扩展策略）/ `ctx.tools.guard()`（monotonic 终局拒绝） → adding-a-tool.md:59
- 自建 Web 卡片注册表 / 存 React props 到 metadata / 从浏览器 import Host 工具 → > "Do not store React props or a selected card in metadata, import a Host tool implementation into a browser bundle, or create another Client presenter registry." → adding-a-tool.md:97
- 在 `presentCall` 里读文件/时钟/会话状态 → presenter 必须纯函数（replay 也会跑）：> "**Purity.** These run on live streaming AND on session-log REPLAY" → adding-a-tool.md:85-87
- 自己写 Host↔Client 传输/中继对象或手写方法签名 → > "no `Pick<ClientRemote, …>` narrowing, no hand-written method signature, no wire relay object" → adding-a-remote-api.md:109
- 造一族 domain error 类 / exit-mapping 函数 → > "Do not build a family of domain error classes, and do not write an exit-mapping function" → 用 `RemoteError` + 码表 → adding-a-remote-api.md:53,59
- 自己拼 Remote 失败断言 → `remoteErrorOf(...).toMatchObject({code, details})`，> "never deep-compare the error object with `toEqual`, and never assert `instanceof`" → adding-a-remote-api.md:151
- 自己定义 LLM 流分片协议（usage/finish 顺序、arguments 字符串化、index 分配） → 遵守 `StreamChunk`：> "Emit `usage` BEFORE `finish`; emit NOTHING after `finish`." → adding-an-llm-adapter.md:27-33
- 静默丢弃 provider 不支持的 `GenerateOptions` 字段 → 抛 `LlmError(..., 'UNSUPPORTED_OPTION')` → adding-an-llm-adapter.md:32
- 自己造 HTTP 代理支持 → DSH 原生读 `HTTP_PROXY`/`HTTPS_PROXY`/`NO_PROXY`/`ALL_PROXY`：> "DSH routes its outbound requests — model calls, web search, page fetches, and MCP servers over HTTP — through the proxy named by the standard proxy environment variables." → user/guide/network-proxy.md:5
- 自己写 MCP JSON-RPC stdio/HTTP 客户端 → `@deepseek-ai/dsh-mcp-client` 负责启动/停止/发现/重连 → user/guide/mcp-memory.md:11,82
- 自己造 cron/定时器 + 唤醒 agent → Schedule/`schedule_*`；到期时 > "A live root Agent waits until it is fully idle, then queues a normal follow-up turn in that conversation. It never steers current work" → user/guide/schedule.md:17
- 自己写 webhook 验签/规则引擎 → `ctx.webhookRuntime` + 规则；注意 > "The webhook runtime stores no delivery or execution state." → github-review.md:100
- 自己造「一个直接跑起的 Node 应用/新可执行入口」 → 只有 `dsh` profile 能启动受支持应用；`verify-application-entrypoints` 会拒绝绕过 `dsh` 的路径 → architecture.md:43,45
- 自己造 capability 的单一角色 → > "A **seam** is a swappable capability with three roles … one role alone is not a seam" → architecture.md:129；> "**Do not split preemptively**" → practice/index.md:149
- 自己定默认值散落在实现里 → > "Explicit > implicit at package boundaries"：`resolve(request): Spec` 显式步骤 → practice/index.md:151 / AGENTS.md:134
- 改 loop 来实现新行为 → > "**Plugins, not loop changes**: new behavior goes on documented extension points" → AGENTS.md:131；> "There is no privileged core to patch" → architecture.md:13
- 为已由静态类型保证的同进程值加运行时校验/兜底 → > "Trust TypeScript at typed same-process boundaries." → AGENTS.md:138
- 自己造包清单/工作区注册 → `adding-a-package.md` 清单 + `pnpm run constraints`（自动覆盖 root package.json workspaces、publint-all、tsdown.config、.oxlintrc、check-workspace-constraints） → adding-a-package.md:25,38
- 手改生成目录文件 → 见「开发流程规范」的 verify-* 列表；session-format 目录：> "Fix the declarations rather than hand-editing `generated.ts`." → adding-a-session-format-version.md:45
- 迁移写成整篇 array→array 转换器 / 跨 Session 共享可变 stage → 用 `SessionFormatMigration` + `createStage`（每个源 artifact 独立状态） → adding-a-session-format-version.md:50-52

## 坑

- `--patch` 覆盖层里插件路径必须绝对；> "A patch file contributes configuration but does not change the profile directory from which the loader resolves module paths." basic/index.md:56
- 补丁不深合并：> "Later layers win per row, and a patch replaces a row's entire `config` value rather than deep-merging keys." → 覆盖别人的行时必须重述所有键。publish.md:123-126
- 层级顺序固定：profile 的 bundles（列表序）→ profile `cordis.patch.yml` → `$DSH_HOME/cordis.patch.yml` → `--patch`（argv 序）。publish.md:114-119
- 忘了 `dsh.bundle` → 只当普通依赖装上，> "`dsh plugin` prints a warning and activates no layer"。publish.md:64
- git 安装不跑 build：TypeScript 包会因缺 `lib/` 加载失败；`prepare` 必须自包含。publish.md:161-163
- `allowBuilds` 是**在安装时在你机器上执行该包代码**的许可，> "Only allow packages whose source you trust, and pin a commit"。publish.md:173
- 一个包只能进一个聚合：> "an ordinary package belongs to exactly one aggregate, never both"；两个聚合合成一个 `ts.Program` 会让 `Context` 声明合并冲突。adding-a-package.md:34 / development.md:64-68
- 静态分析/测试走 `paths`→`src`，**绝不**通过 package `exports` 走 `lib/`（会加载第二份单例） → testing.md:45；生成 Host-for-Client Remote 声明是唯一例外。development.md:88
- `cordis.yml` 只允许 `!!js`（不是 `!js`），且只在 plugin `config` 与 entry `disabled` 下；其他元数据保持字面量。AGENTS.md:119
- 裸插件名必须出现在其 resolver manifest 的 `dependencies`：> "`verify-cordis-config` enforces it." AGENTS.md:124
- waterfall 监听器不调 `next()` 会短路整条链：> "**Waterfall listeners MUST call `next()`** to delegate"。AGENTS.md:129 / architecture.md:107
- `agent/turn-stopping` 是 serial，没有 `next()`。architecture.md:107
- Client 插件 bundle 纯净度门禁：> "The bundle-purity gate also rejects value imports across plugins"（卡片不能 import 本 section 的 card chrome；跨插件协作走 cordis service + type-only import）。adding-a-settings-card.md:102
- 出仓客户端包没有公开 preset：> "No published preset exposes this package, so a package outside this repository has to reproduce the same output format itself." adding-a-settings-card.md:102
- `presentCall/presentResult` 在 replay 上跑，且 `defineTool` 会**软校验**显示路径——参数畸形时返回 `undefined` 走 generic 兜底，> "display must never crash a replay"。adding-a-tool.md:87-89
- `system-prompt/assemble` 是专家协作点，返回值即权威：监听者要自己保住 active PTC 模式与结构化输出协议的贡献；工具过滤优先 `ctx.tools.restrict()`。extension-cookbook.md:102
- 已发布 codec 与迁移语义冻结：> "Released codecs and migration semantics remain frozen. Do not amend a released edge to implement a new structural feature."；只有 N→N+1 边能在发布前合并改动。adding-a-session-format-version.md:26
- 不要用旧边兜住新的不支持变换，也不要照搬旧边的准入策略；每个新接受的情形都要有**拒绝反例**。adding-a-session-format-version.md:56
- 未发布的 N+1 测试必须用一次性隔离 Harness home：> "An interim N+1 file already has the target writer version, so a later edit to N→N+1 will not migrate that file again."；绝不用真实用户 home 修。adding-a-session-format-version.md:28
- 持久化类型改动后生成物陈旧也会让校验失败：> "A stale generated inventory also fails verification; the recording command refreshes it." reviewing-persistence-type-changes.md:34
- 记录里的版本推断不能放宽：> "it never changes source or relaxes them"；变更要求 header bump 时必须先走格式版本 cookbook，且 > "an unrelated historical bump cannot authorize it"。reviewing-persistence-type-changes.md:64-66
- `ok: true` 的录制命令**不能**替代 `doc-sync` 与拥有者的行为/迁移测试。reviewing-persistence-type-changes.md:77
- 生成物与 doc fence 有 1:1 对应关系；新增/删除 primary block 必须同改 manifest，否则 `verify-type-equiv` 失败。development.md:171-177
- CJK/换行/空白：文件以恰好一个尾随换行结束，`git diff --cached --check`（pre-commit）把门。AGENTS.md:155
- Client UI 文案由 locale 拥有：> "`verify-client-ui-i18n` rejects hardcoded copy"。AGENTS.md:147
- 不要把 `pnpm run check:all` 当 agent 日常指令：> "The command is independent of the Git hooks and is not an agent instruction." development.md:127
- Host sandbox 挡住 `gh`/`pnpm`/构建/生成器时，用**最窄**的主机提权重试原命令，> "Require sandbox evidence; never bypass test failures or the product sandbox." AGENTS.md:107
- 自定义 profile 默认 live patch reload，但 `headless`/`sdk`/`sdk-minimal`/`acp` 只在启动时应用一次所有层。architecture.md:29
- Python SDK minimal profile 钉死 `danger-full-access` 且 shell 不限制目录 → 用一次性 checkout/容器。python-sdk.md:147,160
- MCP：stdio 桥会**剥离**凭据类环境变量与所有 `DSH_*`；需要别的密钥就写进该行的 `config.env`，别写进 YAML 明文。mcp-memory.md:13
- 代理密码在 URL 里会被 DSH 启动的每个子进程读到（包括模型写的命令），> "a command that prints its environment puts the password in output that is kept"；另外 `socks5://` 不支持、CIDR 不生效、`web_fetch` 到字面私网地址仍被拒。network-proxy.md:48,42,62,71

## 未解答

- `doc-sync` / `hygiene` 到底展开成哪些 gate：正文只说 > "The root contributor instructions summarize common commands, while `package.json` and `scripts/run-gates.ts` own the current script and gate inventories."——没有逐一列出（需读 `scripts/run-gates.ts`）。development.md:137,131
- 出仓（repo 外）插件的**完整**发布/注册表路径：只说了 git / npm / tarball 三种安装方式，没有任何 DSH 官方插件注册表或其审核流程。publish.md:155-178
- 出仓客户端插件如何产出合法的 lazy-CJS factory bundle：文档只承认 > "has to reproduce the same output format itself"，没给可执行的配方。adding-a-settings-card.md:102
- 出仓插件 README 是否也需要 Model Experience / Known Limitations 模板与双语配对：那些校验器是仓库内的（`scripts/verify-package-readme-*.ts`），是否适用于仓库外包未说明。adding-a-package.md:74,106
- 一个插件同时需要 Host 与 Client half 时，仓库外的 Client 类型/契约如何生成（`build:lib` 生成链属于仓库内 Typert 管线）未给出外部路径。adding-a-remote-api.md:92,194
- 自定义 agent preset 的编写细节（本任务读的 7 篇里只在 architecture.md 出现一行；`editing-cordis-compositions` 之类正文不在本次阅读范围）。
- 定时/提醒、webhook 等 overlay 的**跨会话**持久化语义只到「session-local / 无投递状态」这一层；多 profile 共享、审计等未提。schedule.md:11 / github-review.md:100
- 插件对 `NO_PROXY`、以及 ptc-runtime / workflow worker 不走代理的处理是内建行为，但插件作者若自己起 child process（非 bash/MCP 路径）是否继承代理变量，文档只覆盖了 bash tool、`git`、`gh`、MCP children。network-proxy.md:60,69
- Node 版本下限（22.19+/24+，CI 覆盖 22.19/24/26）对出仓插件的 peer/engine 声明是否强制，未写。development.md:11
