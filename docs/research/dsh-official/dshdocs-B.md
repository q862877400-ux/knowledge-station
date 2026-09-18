# DSH 插件作者摘要（Host + Client 两半）

> 范围：本摘要只依据 `docs/` 英文原文。注意：任务里写的 `docs/framework/` 不存在，3 个 framework 文件实际在 `docs/user/develop/framework/`（index/service/events）。

## 插件契约

**静态插件（由 `cordis.yml` 装载）的导出形状**
- > "In the loader configuration used here, a Cordis plugin module named-exports an `apply` function." — `cordis-tutorial/01-first-plugin.md:5`
- 契约签名：`apply(ctx: Context, config: T): any`（`cordis-api/registry.md:94`）；`name?: string` 只是诊断用显示名（`01-first-plugin.md:21`）。
- 三种形状：函数 / `{ name, apply(ctx, config) }` 对象 / `Service` 子类（`01-first-plugin.md:55-75`）；类型定义见 `cordis-api/registry.md:64-105`（`Plugin.Function | Plugin.Constructor | Plugin.Object`）。
- 可用元数据（`Plugin.Base`）：`name?`、`Config?: StandardSchemaV1<any,T>`、`inject?: Inject`、`provide?: string | string[]`、`intercept?: Dict<boolean>` — `cordis-api/registry.md:72-83`。
- `inject` 的确切类型：`type Inject<M = Dict> = (keyof M)[] | { [K in keyof M]?: M[K] }`（`cordis-api/registry.md:137`）；类形式用 `static inject = ['llm']`（`user/develop/framework/service.md:42`）。数组形式不支持 intercept config，对象形式才支持（`registry.md:130-137`）。
- 配置契约：同名 `export interface Config` + `export const Config: Schema<Config>`（Schemastery），`apply` 收到的是已校验且填好默认值的配置（`cordis-tutorial/05-config.md:22-34,51`）。
  > "Do not export a plain object as `Config`; it does not implement the Standard Schema interface required by Cordis." — `user/develop/basic/config.md:45`
- 提供服务的契约：`class X extends Service { constructor(ctx: Context) { super(ctx, 'name') } }`。
  > "The service is registered immediately and is automatically removed with the owning fiber." — `cordis-api/service.md:10`

**两半（Host Node / Client 浏览器）的打包契约**
- 同一个包里：Host 半在 `src/`，浏览器半在 `src/client/`，以 `./client` 导出，用 `dsh.client` 声明 — `cookbook/adding-a-settings-card.md:7`。
- 包加入客户端表的方式：package.json 声明 `dsh.client`（`platform:'web'`、可选 `inject` 边、可选 `immediately`）并在 `exports["./client"]` 导出构建产物 — `subsystems/client-modules.md:77`；JSON 形状见 `cookbook/adding-a-settings-card.md:84-92`。
- Client 半的 `apply` 同样是 Cordis 插件：`export const inject = ['slots','locale','connection','remote','settingsScope']` + `export function apply(ctx: ClientContext)` — `cookbook/adding-a-settings-card.md:58-60`。
- bundle 格式必须是 loader 的 lazy-CJS factory 产物；仓内用共享 tsdown preset，仓外要自己复现同格式 — `cookbook/adding-a-settings-card.md:94-102`。
- > "So the plugin appears on the page as soon as a `cordis.yml` mounts it — no rebuild of the web application." — `cookbook/adding-a-settings-card.md:82`

**`cordis.yml` 行契约**（`cordis-tutorial/06-composition-and-hmr.md:12-21`）：`id`（稳定身份）、`name`（模块 specifier）、`config`、`disabled`、`group`+`isolate`（`user/develop/framework/service.md:113-137`）。`!!js` 只允许出现在 `config` 与该行的 `disabled` 里（`05-config.md:80`）。
**分发契约**：bundle 包 `dsh.bundle.patch` → `cordis.patch.yml`；profile `dsh.profile.bundles`（`user/develop/basic/publish.md:33-43,92-99`）；`--patch` overlay 用 `insert:`（`basic/index.md:51-56`）。

**动态 Package（进程内、临时）**：`ctx.dynamicCordisRunner.define(request): DynamicCordisDefineReceipt`、`run(agent,pluginId,packageId,mode,signal?)`、`stop(...)`、`undefine(agent,pluginId)`、`inspectPackage(...)`；`ctx.cordisInspect.register/syncClientManifest/list/query` — `subsystems/extensions.md:79,107,153,87,222,27,33,39,51`。Host 事件 `cordis/dynamic-package`、`cordis/dynamic-retract`、`cordis/request-run` 等为 `emit` 模式（`extensions.md:293,310,361`）。

## 生命周期与副作用

- 一切注册都要可逆；effect 精确签名：`effect(execute: () => SyncEffect, label?: string): Disposable<Promise<void>>` / `effect(execute: () => Effect, label?: string): AsyncDisposable<Promise<void>>` — `cordis-api/fiber.md:24-25`。
  > "`execute` runs immediately; the disposers it produces are collected and run (in reverse order) either when the returned disposer is called or when the fiber unloads, whichever comes first. Calling the disposer twice is a no-op. Throws `CordisError('INACTIVE_EFFECT')` if the fiber is already disposed" — `cordis-api/fiber.md:30`
- > "Every registration should have a disposer, either by returning one from `ctx.effect()` or using a Cordis helper that does it for you." — `cordis-primer.md:44`
- 已经是 effect、不用自己包：`ctx.on`（`02-lifecycle-and-effects.md:88`）、`ctx.plugin(child)`（`:89`）、服务注册与 `ctx.tools.register(...)` 等 harness 注册表（`:90`；`user/develop/framework/index.md:59-61` 列出 `ctx.tools.register`/`ctx.llm.registerAdapter`）。`ctx.provide` 直接返回 disposer（`cordis-api/context.md:301`）；`ctx.accessor`/`ctx.mixin` "removed when the current fiber unloads"（`context.md:328,353`）。
- 不包会怎样：`02-lifecycle-and-effects.md:5`——由配置编辑/热重载/显式 dispose/依赖服务消失触发的卸载都会发生，但 "resources managed outside those APIs must be wrapped in `ctx.effect()`"；不包就没有 disposer，卸载与 HMR 时泄漏。
  > "Every registration made through `ctx` is undone when the plugin unloads" — `user/develop/framework/index.md:42`
- 顺序与并发陷阱：
  > "During unload, disposer invocation starts in reverse registration order, but multiple async disposers run concurrently and have no serial completion guarantee." — `user/develop/framework/index.md:63`
  > "If teardown order matters, keep the related work in one effect so disposal unwinds in the intended sequence." — `cordis-primer.md:45`
- 卸载保证：`fiber.dispose()` 返回的 promise 在全部清理（含异步）后 settle，并递归卸载子插件（`02-lifecycle-and-effects.md:66`；`framework/index.md:94-97`）。
- 状态机：`PENDING → LOADING → ACTIVE → UNLOADING → DISPOSED`，`LOADING → FAILED`（`02-lifecycle-and-effects.md:73`；`framework/index.md:9-15`）。
- 依赖是持续的，不是一次性启动检查：provider 消失时依赖方被卸载，回归时重新加载（`03-services.md:76`）。
- 配置热更新走 `fiber.update(config, noSave?)`（`internal/update` waterfall 可 veto）与 `fiber.restart()`（`cordis-api/fiber.md:239,262`）。

## 现成能力清单

| 能力 | 官方 API（精确签名） | 出处 |
|---|---|---|
| 注册模型工具 | `ctx.tools.register(defineTool({ name, description, parameters, output: { schema, render }, execute }))` | `cordis-tutorial/07-into-the-harness.md:21,25-33`；`user/develop/basic/tool.md:19` |
| 跑一次工具管线 | `ctx.tools.execute({ callId, name, arguments, signal })` | `cordis-tutorial/07-into-the-harness.md:39-44` |
| 观察工具结果 | `ctx.on('tools/result', (exec, result) => …)` | `07-into-the-harness.md:64`；`user/develop/framework/events.md:130` |
| 注册 LLM 适配器 | `ctx.llm.registerAdapter(names, adapter)` | `user/develop/framework/index.md:60` |
| 事件监听/派发 | `on(name, listener, options?: boolean \| EventOptions): () => boolean`；`once(...)`；`emit / parallel / serial / bail / waterfall` | `cordis-api/events.md:136,160,40,18,61,84,110` |
| 自定义副作用 | `ctx.effect(execute, label?): Disposable<Promise<void>>` | `cordis-api/fiber.md:24` |
| 提供服务 | `ctx.provide(name, value): () => void`；`class X extends Service { super(ctx, name) }` | `cordis-api/context.md:301`；`cordis-api/service.md:10` |
| 可选读取服务 | `ctx.get(name, strict?): undefined \| this[K]` | `cordis-api/context.md:248` |
| 覆盖服务值 | `ctx.set(name, value)`（仅提供者 fiber，未提供的名字抛错） | `cordis-api/context.md:273,279` |
| 计算属性 / 混入 | `ctx.accessor(name, { get, set })`；`ctx.mixin(name, mixins)` | `cordis-api/context.md:328,353` |
| 作用域派生 | `ctx.isolate(name, label?)`；`ctx.extend(meta?)`；`ctx.intercept(name, config)` | `cordis-api/context.md:54,26,83` |
| 装载子插件 / 依赖回调 | `ctx.plugin(plugin, ...args): Fiber & PromiseLike<Fiber>`；`ctx.inject(deps, callback)` | `cordis-api/registry.md:46,21` |
| 定时器 | `ctx.timer` + 混入的 `ctx.interval / timeout / throttle / debounce` | `cordis-api/inherited.md:19` |
| 日志 | `ctx.logger(name)` | `cordis-api/context.md:135` |
| 设置面板（Host 半） | `ctx.settings.installSection(ctx, ns, Config, config, { validate, setSource, onChange })` | `cookbook/adding-a-settings-card.md:36` |
| 浏览器 UI 插槽 | `ctx.slots.register({ name, id\|key, order, locale, inject }, Component)`；`ctx.slots.inject(key, cb)` | `subsystems/slots.md:5,35-40` |
| 客户端启动图 | `ctx.clientModules.graph()` / `clientPath(id)` / `rebuilt(id)` / `onRebuilt(l)` / `onGraphChanged(l)` | `subsystems/client-modules.md:124,131,158,165,173` |
| 系统提示词 | `ctx.systemPrompt`（工具经它贡献 schema） | `capability-seams.md:548`；`07-into-the-harness.md:84` |
| 人类命令 / 提问 | `ctx.commands`；`ctx.userQuestions` | `capability-seams.md:553,550` |
| 子代理 / 后台任务 | `ctx.subagents`；`ctx.jobs` | `capability-seams.md:573,576` |
| 持久存储 | `ctx.storage`；`ctx.storageDomain` | `capability-seams.md:539,540` |
| HTTP 路由 | `ctx.webServer` | `capability-seams.md:580` |
| 沙箱 / 审批 | `ctx.sandbox`；`ctx.approval` | `capability-seams.md:566,568` |
| 生命周期内省 | `ctx.registry.values()` → `fiber.state === FiberState.PENDING` | `cordis-tutorial/06-composition-and-hmr.md:74-79` |
| 框架内部事件 | `internal/plugin` `internal/status` `internal/update` `internal/get` `internal/set` `internal/listener` `internal/dispatch` | `cordis-api/inherited.md:25-32` |
| 动态包注册表 | `ctx.dynamicCordisRunner.define/run/stop/undefine`；`ctx.cordisInspect.register/list/query` | `subsystems/extensions.md:79,107,153,87,27,39,51` |

## 不许自己造的东西

- 手动 `removeListener` / `clearInterval` → `ctx.on` 本身是 effect、`ctx.effect` 管资源 → `02-lifecycle-and-effects.md:88`；`user/develop/basic/index.md:68`
- 自己解析/校验配置 JSON → 导出 `Config` schema（Standard Schema；仓内用 Schemastery）→ `05-config.md:22-34`；`basic/config.md:23-27`
  > "anything that two deployments may want to set differently to be a configuration field" — `basic/config.md:80`
- 手动安排加载顺序 / 自己写 boot 序列 → `inject` 依赖驱动，文件位置不保证顺序 → `01-first-plugin.md:31`；`03-services.md:59`
- 自造事件总线 / 手写 EventEmitter → `ctx.on/emit` + `interface Events` 声明合并 → `04-events.md:14-21`；`user/develop/framework/events.md:90`
- 自己探测 provider 是否存在 → 可选依赖用 `ctx.get('name')`，硬依赖才 `inject` → `03-services.md:82-90`；`framework/service.md:96`
- 自己往 DOM 里塞 UI / 自造挂载点 → `ctx.slots.inject` + `ctx.slots.register`；跨包只用 `import type` → `subsystems/slots.md:5,17,180`
- 自己起静态服务、手写 `<script>` 注入 → 声明 `dsh.client` + `exports["./client"]`，客户端模块系统自动组合 `__DSH_BOOT__` → `client-modules.md:77,11`
- 自己实现设置读写/持久化 → `ctx.settings.installSection`（namespace 是 Host/Client 两半的 join key）→ `cookbook/adding-a-settings-card.md:11,5`
- 自己把 tool 参数写成 JSON Schema、自己校验/渲染 → `defineTool` 负责转换、推断与校验，`output.render` 负责呈现 → `basic/tool.md:36`；`07-into-the-harness.md:50`
- 自己写 agent 循环 / 拼系统提示词 → `ctx.agentLoop`；`ctx.systemPrompt` → `capability-seams.md:559,548`
- 自己写 KV/持久化/JSON 文件 → `ctx.storage` / `ctx.storageDomain` → `capability-seams.md:539,540`
- 自己 `spawn` 子进程、杀进程树 → `ctx.subprocess`；命令执行用 `ctx.shell` → `capability-seams.md:562,563`
- 自己写路径限制/权限确认 → `ctx.sandbox` + `ctx.sandboxPolicy`；一次性许可走 `ctx.approval` 的 `approval/request` waterfall → `capability-seams.md:566,567,568`
- 自己写 HTTP server → `ctx.webServer` 的命名路由注册 → `capability-seams.md:580`
- 自己写文件监听做热重载 → `@deepseek-ai/cordis-plugin-hmr` → `06-composition-and-hmr.md:25`
- 自己写"临时插件"注册表/审批/版本指针 → `ctx.dynamicCordisRunner` + `ctx.cordisInspect` → `subsystems/extensions.md:69,17`
- 自己造跨插件调用协议 → 拦截/策略用 events，直接能力调用用 service 方法 → `cordis-primer.md:43`
- 自己造子代理/后台任务/技能目录 → `ctx.subagents`、`ctx.jobs`、`ctx.skills` → `capability-seams.md:573,576,556`

## 坑

- **模块名写错不崩溃**：解析失败只经 logger 上报，boot 早期可能还没人监听 console exporter。
  > "a config entry whose module cannot be **resolved** — a typo'd path or package name — is reported through the Cordis logger service instead of crashing the process, and at boot that report can be lost before a console exporter is watching." — `01-first-plugin.md:91`
- **PENDING 完全静默**：`inject` 的名字没人提供就永久等待、不报错。
  > "You can see the states directly." / "a plugin whose `inject` names a service nobody provides waits forever, printing nothing. No error — PENDING is a legitimate state" — `06-composition-and-hmr.md:61-63`；PENDING fiber 也不会维持事件循环，进程可能静默 exit 0（`03-services.md:72`）。
- **waterfall 监听器忘记 `next()` 会静默吞掉下游默认行为**：
  > "**a waterfall listener that only observes or annotates must call `next()`**; returning without it is a deliberate short-circuit. Forgetting `next()` in a logging listener silently swallows the default behavior for everyone downstream." — `04-events.md:138`
- **`apply` 抛错 ≠ 跳过**：插件加载失败是响亮失败，进程会带着你的错误死掉（`01-first-plugin.md:89`）；配置非法则 fiber 进 FAILED 并抛 `ValidationError`（`05-config.md:64-68`）。
- **`inject` 会让插件反复重启**：provider 一卸载，依赖方被卸载并在服务回归时重跑 `apply`——不要把跨重启的状态放在闭包外（`03-services.md:76-78`）。
- **配置行没有 `id` 就等于每次都被重挂**：
  > "an entry without one gets a generated id on every read, so after any config-file edit it counts as removed-plus-added and remounts even if its own lines did not change." — `06-composition-and-hmr.md:59`
- **服务名是全局扁平命名空间**："Prefix or namespace your own services distinctively (the harness claims plain names like `tools` and `llm`)"（`03-services.md:94`）。
- **`ctx.provide` 重复名抛错**：
  > "Throws if the name is already provided in this scope or declared as an accessor." — `cordis-api/context.md:307`
  `ctx.set` 只有提供者 fiber 能调，名字未提供时抛错（`context.md:279`）。
- **异步 disposer 无序**：多个 async disposer 并发、无串行保证；顺序敏感的清理放同一个 `ctx.effect()` 里串行 await（`framework/index.md:63`）。
- **动态插件源码是环境相关的字符串、不是普通模块**：`file` 只是提交源码，生命周期由 `define → run → update/stop/undefine` 与审批驱动（`extensions.md:79,107,153,87`）；客户端半的失败要经 `reportRenderFailure` / `reportClientGuardFailure` 上报，不自动重试（`extensions.md:232,242`）。
- **插槽必须先被声明**：
  > "Registering into an undeclared slot or declaring a child already owned elsewhere fails during plugin activation." — `subsystems/slots.md:13`
- **客户端半不能跨插件做值导入**：
  > "Import another feature package only for declarations with `import type`; never import or re-export its runtime values." — `subsystems/slots.md:180`；`cookbook/adding-a-settings-card.md:102` 明确 bundle-purity gate 会拒绝。
- **事件名撞车不是同一件事**：
  > "`turn/*`, `step/*`, `tool/call`, `tool/result`, and `compaction/*` are durable session-event types, not same-named Cordis events." — `user/develop/framework/events.md:106`（要听这些得听 `session/event` 再判 `event.type`）
- **patch 层不是深合并**：
  > "Later layers win per row, and a patch replaces a row's entire `config` value rather than deep-merging keys." — `basic/publish.md:123`（覆盖别人的行必须重述全部键）
- **`dsh.bundle` 缺失只警告不安层**：包会装上但只当普通依赖，`dsh plugin` 打 warning 不激活任何 layer（`basic/publish.md:64`）。
- **git 安装不带构建产物**：需要作者提供自包含 `prepare`，用户还要在 `pnpm-workspace.yaml` 里 `allowBuilds` 放行（`basic/publish.md:161-173`）。

## 未解答

- **动态 Package 的 Host↔Client 私有 RPC 面（`harness.handle` / `host.call`）在 `docs/` 里没有记载**：`extensions.md` 只给出 `ctx.dynamicCordisRunner` / `ctx.cordisInspect` 的服务方法与 `@Remote('invoke') invoke(pluginId, pluginRunId, method, args)`（`extensions.md:252`），没有写 Package 内如何注册可被对方调用。`code.host` / `code.client` / `packageId` 的源码形态也未出现在这些文档中。
- **静态 Client 半可用哪些注入服务**没有权威清单：`slots.md` 只给出 `slots` 与若干由适配器提供的标准 props/钩子（`slots.md:79-95`）；`['slots','locale','connection','remote','settingsScope']`（`adding-a-settings-card.md:58`）出自 cookbook 示例而非生成目录。`ctx.modules`（浏览器半的 lazy-CJS 表）明确"kernel machinery, documented in the package README"（`client-modules.md:5`），不在 docs 内。
- **`ctx.slots.register` / `ctx.slots.inject` 的精确签名**在 `docs/` 里没有 generated catalog 块，只有用法示例（`slots.md:35-40`）。
- **不包 `ctx.effect()` 的资源**文档只规定"必须包"（`02-lifecycle-and-effects.md:5`），但没有说明是否存在泄漏检测/告警。
- **静态（非动态）Client 插件渲染失败的错误面**没有记载：`reportRenderFailure` / `reportClientGuardFailure` 只挂在动态 runner 上（`extensions.md:232,242`）。
- **`provide?: string | string[]` 元数据何时该由普通插件显式声明**（相对 `Service` 子类自动注册）文档未说明（`registry.md:79`）。
- **`inject` 对象形式的 intercept config 具体语义/解析顺序**只有 `Service[symbols.resolveConfig]` 的引用（`context.md:83`），无展开说明。
- **`docs/framework/` 路径在仓库中不存在**，本摘要按 `docs/user/develop/framework/`（恰好 3 个文件）解读。
