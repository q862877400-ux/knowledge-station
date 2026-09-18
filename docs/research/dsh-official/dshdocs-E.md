# DSH 官方设施速查（插件作者版）

来源：`D:\AI\DSH\deepseek-harness\docs\`。只读英文原本，跳过 `*.zh.md` / `*.i18n.yaml` / `persistence-changes/historical-formats/*`。

## 持久化

三条官方持久化通道，按“存什么”选，不要新造：

1. **会话事件日志（对话历史/可回放状态）** — `ctx.sessionPersistence`（抽象 seam，`subsystems/persistence.md:5`、`:341`）。契约：`create`/`open`/`stat`/`list` + 每会话 `SessionHandle`（`read`/`append`/`flush`/`close`），源码 [`packages/session/session-persistence/src/index.ts`]。引用语：
   > "one abstract service (`ctx.sessionPersistence`) exposing `create`/`open`/`stat`/`list` over the existing `SessionEvent` — **no parallel persisted event type**"（`persistence.md:7`）
   - 写入不保证落盘：> "Persistence is best-effort: on resolution the batch is accepted, ordered, and visible to reads on this backend instance, but only a resolved `flush` promises it survives a crash"（`persistence.md:70-75`）。要活过崩溃必须 `flush`（`:81`）。
   - 单写者：> "in-process single-writer ownership makes a second `open(id, 'write')` reject with `SessionAlreadyOwnedError` while an owner is active"（`persistence.md:11`）。
   - 增量判定用 revision：> "equal revisions may be treated as an unchanged log; unequal revisions promise nothing"（`persistence.md:296`；签名 `:403`）。
   - 插件贡献自己的持久事件：declaration-merge `SessionEventMap`，且**只能 log-only**：> "These are **log-only**: NOT `SurfaceEventType`s (they carry no `surfaceOp` and contribute nothing to derived history)."（`subsystems/session.md:722-724`）。写入口 `Session.append(type, data, ...opts)`（`session.md:599`）；> "All `event.data` must be JSON-serializable; `Session.append` enforces this at the source (throwing on non-serializable data)"（`session.md:732`）。
   - 崩溃恢复语义：不截断未完成 turn，> "Persistence does **not** truncate or repair it … only the incomplete fragment of a torn physical tail … is discarded"（`persistence.md:110`）；`interrupted` 是唯一循环不产生的 `TurnEndReason`（`:110`）。
   - 会话元数据走 header 而非日志：> "Per-session metadata travels **separately** from the event log"（`persistence.md:139`，`SessionHeader` `:147`）。

2. **结构化键值数据（非会话日志的一切）** — `ctx.storage` 中枢 + `ctx.storageDomain`（数据形式），`subsystems/storage.md:5`、`:128`。
   > "The storage subsystem persists everything that is not a session event log (session logs have their own seam)"（`storage.md:5`）
   - 自己声明 domain：`defineDomain(spec)`（`storage.md:95`），spec 含 name/version/layout(`single`|`per-record`)/compatibleVersions/tables（`:55-92`）；打开 `ctx.storageDomain.open(spec)`（`:215`）。
   - 读是同步内存快照，写才异步：> "Every write — `put`, `delete`, `update`, `global.set` — queues on one per-domain chain and reaches backend durability first, then mutates memory, then emits `domain/changed`"（`storage.md:126`）。
   - 变更通知：`domain/changed`（emit，`storage.md:245`）；> "The event is in-process only; cross-process change push is a recorded limitation"（`storage.md:153`）。
   - 后端自带：`dsh-storage-json`（注册名 `json`）/ `dsh-storage-sqlite`（`sqlite`）（`storage.md:5`）；hub 不做 IO（`:5`）。

3. **用户可编辑配置（settings 文档）** — `ctx.settings`（`subsystems/settings.md:5`、`:178`），见下“配置”。

## 文件系统与工作区

- **用 `ctx.fs`，不要 `fs`/`process`。** `FileSystem` 抽象 seam 拥有 `resolve`/`processPath`/`processPathFromHostPath`/`fileUrl`/`contains`/`stat`/`lstat`/`readText`/`streamText`/`readBytes`/`readByteRange`/`listDir`/`writeText`/`editText`（`subsystems/filesystem.md:278`，签名 `:290-451`）。
  > "Consumers may display `displayPath`, but must not parse `targetKey` (a branded opaque id) or assume it is a local absolute path."（`filesystem.md:13`）
  > "Consumers MUST NOT parse it or assume it is a local absolute path."（`fs` 的 `FsTargetKey` JSDoc，`filesystem.md:39`）
- 跨能力（子进程）取路径必须走 provider：`processPath(target)` / `processPathFromHostPath(hostPath)`（`filesystem.md:15`、`:314`、`:324`）；`fileUrl` 由后端编码 URI（`:333`）。
- 写/改是**原子 + 可选版本守卫**：`writeText(target, content, expected?, signal?, sandboxPolicy?)`（`filesystem.md:435`），`editText(target, edit, expected?, ...)`（`:450`）。
  - `FsWriteIntent = {kind:'createIfAbsent'} | {kind:'replaceIfVersion'; version}`（`:125`）；省略 = 无条件 create-or-overwrite（`:116`）。
  - > "`editText` is a provider-level mutation, not a `read` plus `write` composed elsewhere."（`filesystem.md:151`）；守卫先于文本匹配，否则报 `FS_STALE_VERSION`（`:151`）。
  - 失败码是稳定的 `FsErrorCode`（13 个，`filesystem.md:254-268`），工具注册表保留 `{name, code}`，不要解析文本（`:246`）。
  - 读之前用 `lstat` 做信任边界检查（`filesystem.md:74`、`:352-366`）。
  - > "`read`/`write`/`edit` take **no** `timeoutMs`, and the provider contract arms no deadline"（`filesystem.md:274`）。取消走 tool-execution signal。
- **观察策略是插件不是服务**：`dsh-fs-observation-policy` 注册 0 个服务，只通过 `fs/write-intent`、`fs/edit-intent`（waterfall，单槽决策）与 `fs/observed`（emit，监听者必须同步）改行为（`filesystem.md:185`、`:242`、`:278`）；默认行为是 read-before-write/edit（`:7`）。事件是 provider 契约词汇，由 `dsh-tool-fs` 派发（`:183`）。
- **工作区/目录身份**：`ctx.workspaceRegistry`（`subsystems/workspace.md:118`、`:424`）— `create(path,title?)`（`:440`）、同步 `get`/`list`（`:447`/`:455`）、`resolveByPath`、`delete`（`:120`，只删登记不删目录/文件/日志）。
  > "`realpathNormalize` (`fs.realpath`; trailing slashes, `..`, and symlinks resolved) is the one uniqueness canon"（`workspace.md:19`）
- 面板/客户端读文件走已封装的 Remote 面：`ctx.workspaceFiles` 的 `read`/`readBytes`/`readAll`/`readRelated`/`stat`/`list`/`changes`（`workspace.md:345-417`）；`changes` 只报被 instrument 的 `fs/observed`，> "Only instrumented filesystem operations report here; the OS is not watched."（`workspace.md:409-411`）
- 工作区能力对模型不可见、无工具无 prompt 文本无会话事件（`workspace.md:5`）。

## 配置

**两个机制，别混：**

1. **声明式部署配置（`cordis.yml` 的 `config:`）** — 导出同名 `Config` 接口 + Schemastery schema：
   > "Export a `Config` type and a same-named Schemastery schema. Put defaults directly on the schema fields"（`user/develop/basic/config.md:9-12`，示例 `:17-31`）
   - > "When loading the plugin, Cordis uses the exported schema to validate configuration and fill defaults. Do not export a plain object as `Config`; it does not implement the Standard Schema interface required by Cordis."（`config.md:45`）
   - 非法配置让加载失败：> "The schema runs while the plugin loads. Invalid configuration fails the load with an actionable error."（`config.md:74`）；fiber 变 FAILED（`cordis-tutorial/05-config.md:68`）。
   - 设计律：> "anything that two deployments may want to set differently to be a configuration field"（`config.md:80`）；> "The test is whether `cordis.yml` can change the value without a code edit."（`config.md:92`）
   - `!!js` 只允许出现在 `config` 与 `disabled` 里，其余元数据保持字面量（`05-config.md:80`、`cordis-primer.md:39`）。
   - 配置变更 = 热替换插件（`config.md:99-100`）。
   - 目录查询：`config-catalog.md`（见下节）。`cordis.yml` 的编排本身不在本 digset 范围。

2. **用户可编辑设置（带 UI/热改）** — `ctx.settings.register(ns, schema, options?)` 返回 `SettingsScope`（`settings.md:202`）。分层：schema default → 注册者的 composition `base` → 用户段（`settings.md:5`、`:68`）。
   - `SettingsScope`：`get()` / `watch(next,prev)` / `update(patch)` / `replace(section)`（`settings.md:69-92`）；`replace({})` 是重置路径（`:88`）。
   - `validate` 是 schema 之外的跨字段校验，> "Throwing here refuses the *write* that produced the value"（`settings.md:31-34`）。
   - `applies: 'live' | 'restart'` 是 UI 提示不是机制（`settings.md:54`）。
   - 注册绑在调用插件的 fiber 上：> "disposing that fiber removes the namespace and its observers"（`settings.md:20`）。
   - 变更事件：`settings/updated(ns,next,prev,source)`，> "never emitted when the resolved value is deep-equal"（`settings.md:157`、`:383`）；另有 `settings/document-updated(ns,revision)` 供配置界面（`:360`）。
   - 线上面必须 `redactSecrets: true`：> "Every wire surface MUST pass this"（`settings.md:148`）；持有脱敏视图的调用方只能走路径写 `mutate(ns, ops[])`，> "cannot delete fields it never saw"（`settings.md:263-267`）。
   - 存储后端示例 `@deepseek-ai/dsh-settings-file`：`path`/`dshHome`/`watch`/`debounceMs`（`config-catalog.md:2271-2287`）。

## 事件

- 监听/派发：`ctx.on(name, handler)` / `ctx.emit` / `ctx.waterfall` / `ctx.serial` / `ctx.parallel` / `ctx.bail`（`user/develop/framework/events.md:12-77`）。
- **模式是事件公开契约的一部分**，决定是否 await、顺序与有无返回值（`cordis-primer.md:15-27`）：

  | Mode | 是否 await | 顺序 | 有返回值 |
  |---|---|---|---|
  | `emit` | 否 | 注册顺序观察 | 否 |
  | `waterfall` | 否 | 注册顺序 | 是 |
  | `parallel` | 是 | 全部并行 | 否 |
  | `serial` | 是 | 注册顺序 | 是 |
  | `bail` | 否 | 注册顺序直到有人 bail | 是 |

  > "The dispatch mode is part of the event's public contract. New harness events document it with an `@mode` tag"（`cordis-primer.md:27`）
- waterfall 是 around-middleware：> "A listener **must call `next()` to delegate downstream**; omitting the call short-circuits the pipeline"（`events.md:66`，`cordis-primer.md:31`）。单决策事件里短路就是设计（`cordis-primer.md:35`）。
- 命名：Harness Cordis 事件用 `namespace/action`（`events.md:104`）。类型靠 declaration merging（`events.md:85-100`）。
- **不要混两套事件**：> "`turn/*`, `step/*`, `tool/call`, `tool/result`, and `compaction/*` are durable session-event types, not same-named Cordis events. To observe them, listen to `session/event` and inspect `event.type`."（`events.md:106`）。
- 监听器是 effect，卸载自动移除：> "A listener registered with `ctx.on()` is removed automatically when its plugin unloads"（`events.md:108-117`）。所有注册都要有 disposer（`cordis-primer.md:45`）。
- 谁派发/谁监听某事件：查 `event-producer-consumer.md` 的表（Event | Mode | Declared in | Dispatchers | Listeners）。
- 会话事件 append 后的顺序/包含：observer 失败被包含，> "Once the event enters the log, the append is committed: observer failures are logged and contained per listener"（`session.md:565-568`）。`domain/changed` 则在持久化之后才 emit，> "a synchronously throwing listener is contained with a logged warning rather than rejecting the already-durable write"（`storage.md:153`）。
- 诊断/日志：`ctx.logger(name)`（`cordis-api/context.md:131-138`）。

## 目录类文档怎么查

- **`module-graph.md`（109 KB，生成物，勿手改）**：它就是“**peer dependency 图**”，不是模块依赖全集。读法：`module-graph.md:6` 定义 —— > "A peer means the consumer requires a shared instance; ordinary runtime dependencies and development-only relationships are not shown." 结构 = ① 一份 mermaid `flowchart TD`（按 `packages/<group>/<pkg>` 分组，`a --> b` 表示 a 把 b 当 peer，名字省略 `@deepseek-ai/dsh-` 前缀；`:6-1271`）② 一张 `| Package | Group | Peer dependencies |` 表（`:1274`–文件末，可 grep 单行）。查法：想给插件加依赖 → 在表里 grep 目标包名，看它是否要求“同一实例”；是则你的包也要声明 peer 而不是另起实例。注意：**这张图不告诉你某包能不能两个实例共存**——文档没说，属未解答。
- **`persistence-catalog.md`（228 KB，生成物，勿手改）**：会话持久化事件的机器目录。结构固定 5 块：① 头部声明（`:6-16`：覆盖 logical/physical header、envelope、每个插件 declaration merge；外部插件类型不在此目录内，> "external plugin types require their own declarations and are outside this catalog"`:10`）② `## Persistence type fingerprints`（`:12`）根类型 SHA-256 表 ③ `## Event envelope`（`:81`，`SessionEvent`/`SurfaceOp`/`ignorable` 定义）④ `## Events`（`:157`，**按事件名首段分类**：`### agent/*`、`approval/*`、`session/*`、`tool/*`、`turn/*` … 共 30+ 个分类，每个条目形如 `#### <event> — log-only|surface` + `ts persistence-catalog` 码块 + `Source:` 行）⑤ `## Resolved persistence types`（`:1243`，每个可达类型一次，带 SHA-256 与属性表）。查法：先 grep `^### \`<ns>/\*\`` 定位分类，再 grep `#### \`<event>\`` 取准确定义与 `Source:`（例子：`persistence-catalog.md:758-796` 的 `session/end-seed`）。改类型前看指纹规则：> "Comments, source locations, alias names, erased brands, readonly markers, and harmless field, union, or intersection reordering do not affect these fingerprints. Tuple order, property names, value types, and optionality do."（`:14`）；并走 `cookbook/reviewing-persistence-type-changes.md`（`:16`）。
- **`config-catalog.md`（160 KB，生成物，勿手改）**：`cordis.yml` 每个 `config:` 能设什么。结构：① 声明（`:6-10`：本文件是**部署轴**参考；字段若被运行时 schema 故意排除即为 runtime-only seam，不能在 yml 里设）② 每个可加载包一节 `## \`@deepseek-ai/dsh-<pkg>\``，内为 `Requires: <注入的服务键>`（可能省略）+ `ts config-catalog` 原样声明 + `Depends on:` + `Source: \`packages/.../src/index.ts:<line>\``（例：`config-catalog.md:14-34`）③ `## Loadable plugins with no config`（`:3586`）④ `## Seam packages (not directly loadable)`（`:3684`）⑤ `## Library packages (no plugin entry)`（`:3705`）。查法：grep `^## \`@deepseek-ai/dsh-<包名>\`` 或直接 grep 字段名；要写自己的声明就照 `:18-30` 的 `export interface Config` 形状。

## 不许自己造的东西

- 自己 `fs.writeFile` / `readFile` 存状态 → **`ctx.fs` 的 `writeText`/`editText`/`readText`/`streamText`/`listDir`（含守卫与沙箱策略）** → `subsystems/filesystem.md:278`、`:435`、`:450`
- 自己拼绝对路径 / 解析 `targetKey` 当本地路径 → **`FsTarget` + `displayPath`（展示）+ `processPath(target)`（给子进程）** → `filesystem.md:13`、`:15`、`:314`
- 自己算“文件是否变过”再覆盖 → **`FsWriteIntent` + `FsVersion` 守卫** → `filesystem.md:116`、`:125`
- 自己 try/catch 文件错误做分支 → **`FsErrorCode` 稳定码** → `filesystem.md:246-268`
- 给文件 IO 加超时 → **不加**，只传 cancellation signal → `filesystem.md:272-274`
- 自己造“工作区/目录身份” → **`ctx.workspaceRegistry`（`WorkspaceId` + realpath canon）** → `subsystems/workspace.md:16`、`:118`、`:440`
- 自己写 `.dsh` JSON 存档做结构化数据 → **`ctx.storage` + `defineDomain`/`ctx.storageDomain`（后端 json/sqlite 可换）** → `subsystems/storage.md:5`、`:95`、`:215`
- 自己写会话历史/回放文件 → **`ctx.sessionPersistence` + `SessionHandle`（日志是唯一真相，`create/open` 只此一门）** → `subsystems/persistence.md:7`、`:11`
- 自己给会话存元数据文件 → **`SessionHeader`（随日志侧存）** → `persistence.md:139`、`:147`
- 自己发明持久事件类型/平行事件模型 → **declaration-merge `SessionEventMap`（仅 log-only）** → `subsystems/session.md:722-724`
- 自己读环境变量当配置 / 硬编码可调值 → **导出 `Config` 接口 + 同名 Schemastery schema** → `user/develop/basic/config.md:9`、`:80`
- 自己解析 `cordis.yml` / 读 YAML → **`apply(ctx, config)` 的第二参数（已校验、已填默认）** → `config.md:29-31`、`cordis-tutorial/05-config.md:51`
- 自己写 `settings.json` 给用户改 → **`ctx.settings.register(ns, schema)` + `SettingsScope.update/replace/watch`** → `subsystems/settings.md:202`、`:69-92`
- 自己轮询配置变化 → **`scope.watch()` / `settings/updated`** → `settings.md:79`、`:383`
- 自己 `console.log` 当诊断 → **`ctx.logger(name)`** → `cordis-api/context.md:131-138`
- 自己写事件总线/发布订阅 → **`ctx.emit`/`ctx.on` + 正确 dispatch mode** → `user/develop/framework/events.md:12-77`、`cordis-primer.md:15`
- 自己实现中间件/拦截链 → **`ctx.waterfall`（必须 `next()`）** → `cordis-primer.md:29-35`
- 自己管插件卸载时的清理 → **`ctx.effect()` / `ctx.on()` 返回 disposer** → `cordis-primer.md:13`、`:45`
- 自己处理崩溃后“修好”日志 → **持久化不修；reader 侧补 `interruptedTurnClosers`** → `persistence.md:108-112`
- 自己判定日志是否有变 → **`stat().revision` 变更令牌** → `persistence.md:294-296`

## 坑

- `append` ≠ 落盘。只有 `flush` 是持久化屏障；`session/disposed` 与 `close()` 才会最终 drain（`persistence.md:70-75`、`:81`、`:106`）。
- 一个会话同一时刻只能有一个 write handle，否则 `SessionAlreadyOwnedError`（`persistence.md:11`）；`open(id,'read')` 不取所有权（`:364`）。
- 忘记 `ignorable: true` 会让未来 reader 直接拒绝重建日志，而默认是“必须认识”：> "Absent means required … MUST refuse to reconstruct the session instead of silently dropping the event"（`persistence.md`/`persistence-catalog.md:137-147`）。写者只在纯信息记录上标 `true`（`:143-146`）。
- 插件自造事件只能是 log-only；想进模型历史（surface）不行（`session.md:724`）。
- `Session.append` 对 data 做严格 JSON 可序列化校验，BigInt/undefined/Map/Set/Date/类实例/NaN 都会抛（`session.md:584-597`）。
- 事件日志里的内容改动是**破坏性格式变更**：> "Adding an event type that carries non-serializable data, corrupts core execution nesting, or violates its owner's declared relation is a breaking change to the on-disk format."（`session.md:732`）
- `fs/observed` 的监听者必须**同步且只记录**：工具不守护这次 emit，抛异常会顶掉读错误或让已成功的改动变成 isError 结果（`filesystem.md:185`、`:484`）。`fs/*` 的 actor 是不透明 `object`，只能当身份键，别读它的字段（`filesystem.md:210-212`、`:242`）。
- 去掉 `dsh-fs-observation-policy` 后 write/edit 变成无条件覆盖/替换，read-before-write 消失（`filesystem.md:7`）。
- `FS_SANDBOX_DENIED`（策略拒绝）与 `FS_PERMISSION_DENIED`（内核拒绝）是两回事（`filesystem.md:270`）。
- 工作区 `delete(id)` 只删登记：> "the directory, user files, live sessions, and persisted logs are never touched"（`workspace.md:120`）。
- 工作区 session 成员资格要**双条件**（记录里的 id + header 的 canonical cwd 相等），不是只按 cwd 推导（`workspace.md:116`、`:5`）。
- settings 的 `update` 只合并用户层，永远不写 `base`；想删除字段必须用 `replace`/`mutate`（`settings.md:63`、`:88`、`:263`）。
- 线上面必须 `redactSecrets: true`，否则 `role('secret')` 字段会随响应出去（`settings.md:98`、`:148`）。
- `validate` 失败会拒绝**那次写入**；注册时已存段不合规则直接拒绝注册本身（`settings.md:31-45`）。
- 配置里 `do not` 导出普通对象当 `Config`（`config.md:45`）；`!!js` 只限 `config`/`disabled`（`05-config.md:80`）。
- 会话事件与同名 Cordis 事件不是一回事（`events.md:106`）。
- waterfall 忘记 `next()` 会静默短路下游（`events.md:79-81`）。
- 持久化/存储事件在提交**之后**发出，监听者抛错不会回滚已durable的写（`storage.md:153`）。
- `domain/changed` 只在本进程；跨进程推送是已知限制（`storage.md:153`）。
- domain 记录返回的是**存储对象本身不是副本**：> "replace via `put`/`update`, never mutate in place"（`storage.md:126`）。
- 目录类文档都是生成物，手改会被 freshness 门禁打回；改行为要改源码再 `pnpm run gen-*`（`config-catalog.md:8`、`persistence-catalog.md:8`、`module-graph.md:1-2`）。

## 未解答

- 插件事件名是否强制使用某个固定前缀/命名空间（例如必须用自己包名），文档只给 `namespace/action` 的形状，没规定怎么取 namespace（`events.md:104`）。
- 两套事件之间的**跨进程/跨插件**顺序保证：除 `session/event` 与 `domain/changed` 各自的顺序外，不同事件彼此的顺序未规定。
- `module-graph.md` 只表达 peer（共享实例）关系，未说明**哪些包允许同进程多实例**、以及违反 peer 会怎样失败——文档没说。
- 官方日志（`ctx.logger`）的落盘位置/保留策略，本批文档未涉及。
- 插件自己是否被允许直接 `import` Node `fs`（例如在非沙箱 host 插件里）；文档只规定“用 `ctx.fs`”（`filesystem.md`）与“沙箱策略”（`filesystem.md:270`），没给禁止条款。
- `ctx.settings` 的 namespace 与 `apply` 配置的**同一个包同时用两者**时的推荐划分，只在 `settings.md:5` 说“composition config stays in `cordis.yml` — a namespace carries only the user-editable subset”，更细的分界未展开。
