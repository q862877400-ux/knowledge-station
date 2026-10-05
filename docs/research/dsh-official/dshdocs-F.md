# DSH 文档消化：插件作者防重复踩坑（F）

覆盖范围：`docs/postmortem/`(5)、`docs/i18n/`(5)、`docs/persistence-changes/`(4，不含 `historical-formats/`)、`docs/persistence-changes/releases/`(27)、`docs/subsystems/` 中除 17 篇已读页之外的 41 篇（仅英文 `.md`，跳过全部 `.zh.md` / `.i18n.yaml`）。release 记录中 12 篇声明 0 个变更根（如 `dsh-v0.1.0-rc.1.md:59`），只有“摘要/摘要无变化”样板，对插件作者无信息，故跳过。

## 破坏性变更时间线

| 版本/日期 | 改了什么 | 旧写法为什么坏了 | 新写法 | 出处 |
|---|---|---|---|---|
| dsh-v0.0.1-rc.3 / 2026-08-12 | 4 个 `compact/*` 事件改名为 `compaction/*`；`hook/invoked.dialect` 的 `claude` 改为 `claude-code`；user-message `source.kind` 的 `workspace-instructions` 改为 `agent-instructions` | 旧字面量与事件键不再被识别（文档只声明结构差异与 `version-bump`，未写旧值解析行为） | 用新事件键与新字面量 | `persistence-changes/releases/dsh-v0.0.1-rc.3.md:99-110`；摘要 :12 |
| dsh-v0.1.0-rc.7 / 2026-08-17 | `assistant/chunk.data.chunk.replayState` 由 `unknown` 变为带必填 `response`／可选 `blocks` 的对象 | 未类型化的值无法再被当作 replay 状态 | 写结构化 `replayState` | `.../dsh-v0.1.0-rc.7.md:66` |
| dsh-v0.1.0-rc.8 / 2026-08-19 | `assistant/message` 新增可选 `interrupted`；`agent/inbox/spliced`、`session/title-llm-request`、`user/message` 的 `source` **union 变体变化** | 联合类型新增/改变变体属 `version-bump`（同版本不得忽略） | 同步更新生产者与读取器 | `.../dsh-v0.1.0-rc.8.md:87-94` |
| dsh-v0.1.1-rc.1 / 2026-08-21 | `permission/preset` 新增可选 `origin` | 可选新增，`same-version` | 可省略 | `.../dsh-v0.1.1-rc.1.md:66` |
| dsh-v0.1.1-rc.2 / 2026-08-21 | **同日回退**：`permission/preset.data.origin` 被删除；同时 10 处 payload 的 `attachment` 新增可选 `originalDimensions` | `property-removed` 是 `version-bump`；不要依赖上一 RC 刚加的可选字段 | 不写 `origin` | `.../dsh-v0.1.1-rc.2.md:93-103`；摘要 :12 |
| dsh-v0.1.2-alpha.1 / 2026-08-27 | 信封 **移除** `ignorable`，并波及 50+ 个事件的 `ignorable`；`request/header` 新增可选 `startsSeries` 与 series `reason`；新增 model-selection / subagent model-policy / delivery-accepted 事件 | 61 处结构差异，全为 `version-bump` | 不要再发 `ignorable` | `.../dsh-v0.1.2-alpha.1.md:219-279`；摘要 :12 |
| dsh-v0.1.2-alpha.2 / 2026-08-30 | **恢复**可选 `ignorable`（信封 + 52 个根） | 与上一版完全相反：连续两个 alpha 对同一字段做相反变更 | 以当前源码为准，勿缓存 alpha 结论 | `.../dsh-v0.1.2-alpha.2.md:220-270`；摘要 :12 |
| dsh-v0.1.2-alpha.4 / 2026-09-01 | 逻辑 `SessionHeader` 用必填 `isSeeded` 替换可选 `seedLength`（物理 JSONL header 仍声明 `seedLength`）；user-message 的 `subagent-report`／`coordinator` 变体合为 `agent-message` | `required-property-added` / `property-removed` 均 `version-bump` | 逻辑层只读 `isSeeded` | `.../dsh-v0.1.2-alpha.4.md:75-79` |
| dsh-v0.1.3-alpha.1 / 2026-09-04（writer 0→**2**） | `JsonlHeaderLine.seedLength` 删除、必填 `isSeeded` 加入；`SessionHeader.version` 类型变化；**`assistant/chunk` 整个事件被删除**，新增 `assistant/attempt`；`assistant/message` 新增**必填** `stream`；team 事件 `version` 由 1 升 2 | `root-removed` + `required-property-added`，旧写入者产出的日志不再完整 | 改用 `assistant/attempt`＋`message.stream`；按 0→2 走格式迁移流程 | `.../dsh-v0.1.3-alpha.1.md:114-138`；摘要 :12 |
| dsh-v0.1.5-alpha.1 / 2026-09-08（writer 2→**3**） | 新增 `system/message`；`EpochHeader` 移除 `system`；`surfaceOp.start/end` 改为**必填** `startSeq/endSeq`（`user/message`、`assistant/message`、`tool/result` 三处，且 `surfaceOp` 本身变为必填）；`tool/code-dispatch*` 改为 `tool/ptc-dispatch*` | 旧 `start/end` 字段被删除、新序号字段必填 | 读 `request/context.data.systemPromptUpdate`，写 `startSeq/endSeq` | `.../dsh-v0.1.5-alpha.1.md:99-123`；摘要 :12 |
| 2026-09-14 image-offload | 新增 `image/offload` 事件，并要求为其提供 message projection | **“The new event is required on read: older builds that do not recognize image/offload refuse those logs”** ——旧构建读到不认识的事件会直接拒绝整份日志 | 新事件必须同时交付投影；未标记的旧 occurrence 保持保留 | `persistence-changes/2026-09-14-image-offload.md:86` |
| 现行规则（2026-09-11 基线起） | 变更分级固定表：可选 event-body 属性（含整棵子树）新增 / 必填改可选 / 新增普通事件类型 = `same-version`；可选改必填、新增必填属性、改类型、删/改名属性或事件、改 Session header 或 event envelope = `version-bump` | —— | 改持久化类型必须落一条记录；规则作用于**整个**变更，不得用一处 allowed 变更掩盖同时存在的破坏性变更 | `persistence-changes/README.md:47-55` |

补充（同为作者陷阱）：`persistence-changes/releases/README.md:68` 明确 “**historical version 0 did contain structural changes without version increases**”，且 “A backfilled record cannot authorize a current PR to omit acknowledgement or a required version increase.”——历史上 writer version 0 期间发生过未升版本的结构性变更（上表前 8 行），所以**不要以 version 号未变来推断类型没变**。

## 事故复盘给出的纪律

- **0001 ACP 崩溃**：插件模块里多写一行 `export default apply` → 根因：cordis Loader 的 `unwrapExports` 执行 `exports.default ?? exports`，优先取 `.default`，于是把 `name`/`inject`/`Config` 这些兄弟命名导出**整个丢掉**，fiber 以空 `inject` 构建，`apply` 第一行 `ctx.agents` 直接抛 `cannot get property "agents" without inject` → **可复用纪律**：> “A namespace plugin and a default export are mutually exclusive under the cordis Loader. Pick the namespace form (`name`/`inject`/`Config`/`apply`) and do not add `export default`” → `postmortem/0001-...md:110`（根因 :39-54，修法 :102）
- **0001 第二个 bug**：`session/load` 仍抛 `... without inject` → 根因：`AgentLoop` 故意不把 `sessionPersistence` 放进 `static inject`，而 `ctx.<name>` 的属性代理是**只向祖先走**的 fiber 遍历，跨影子（shadow）边界时既不在自身 store 也不在任一祖先，走到 root 就抛；直接 `ctx.agents.resume(...)` 的测试在插件 fiber 之外运行，走了 `if (!ctx.fiber.runtime)` 的旁路所以掩盖了问题 → **可复用纪律**：> “For a service a plugin reads opportunistically but does NOT declare in `static inject`, use `ctx.get(name)`, never `ctx.<name>`.” → `postmortem/0001-...md:111`（机制 :62-87）
- **0001 测试教训**：178 个绿测试 + 100% 行覆盖仍然没抓到，因为所有测试都手工 `ctx.plugin({ name, inject, apply })`，而 `unwrapExports` **只由 Loader 调用** → **可复用纪律**：> “A test that constructs a plugin by hand cannot validate how the plugin loads. At least one test must drive the real Loader/export path end-to-end.”（且不应挂在 key gate 后面，因为该操作不调用模型）→ `postmortem/0001-...md:112`；并附 > “Trust the trace, not the theory.” → :113
- **0002 文件系统工具被永久禁用**：用 `disabled: !!js ...` 条件启用插件 → 根因：> “It applies only to `entry.options.config`: `Entry._resolveConfig()` interpolates that field, while `Entry.disabled` tests `entry.options.disabled` without interpolation.” 表达式对象恒为真 → 所有文件系统 fiber 在**任何模式**下都缺席，且 YAML 语法合法、**加载期零诊断** → **可复用纪律**：> “A syntactically accepted configuration value is not necessarily evaluated at that location; document and verify exactly which fields are interpolated.” → `postmortem/0002-...md:32,45`；条件化组合改用显式 overlay（:38）
- **0002 快照教训**：snapshot 测试把任何确定性 transcript 当正确行为，refresh 把 `UNKNOWN_TOOL` 写进预期输出后仍然全绿 → **可复用纪律**：> “A snapshot refresh is fixture production, not correctness review. Semantic impossibilities such as a missing registered tool need assertions independent of the expected output.” → `postmortem/0002-...md:46`
- **0002 权限教训**：> “Permission controls must describe only the capabilities they actually govern. Composition-time filesystem access cannot follow a runtime bash-only preset safely.” → `postmortem/0002-...md:47`
- **0003 Web agent 验证了替代服务器**：改了 GUI 源码却不知道哪个 URL/进程承载自己的会话；把 `apps/web` 裸 Vite 的 HTTP 200 当成功（白屏，浏览器报 `client-modules: window.__DSH_BOOT__ is missing or not an object`）；随后另起 3334 验证替代服务器，而用户真正在用的 3081 早已生效 → 根因：`window.__DSH_BOOT__` **只由完整 host 注入**，传输就绪 ≠ 应用就绪；且用 shell `&` 起进程绕过了托管任务生命周期 → **可复用纪律**：> “HTTP readiness, build success, and a boot manifest are different facts. Acceptance names the exact origin and externally observes the requested change there.” / > “A replacement service cannot prove that an existing page changed. Long-running processes use managed task lifecycles when they are actually requested.” → `postmortem/0003-...md:51-52`（根因 :36-38，护栏 :42-44）
- **0003 回归测试教训**：> “A regression test must be able to fail for the reported mechanism. Process timeout is not equivalent to fail-fast, and post-exit port availability does not prove the port was never bound.” → `postmortem/0003-...md:53`
- **0004 Landlock 误判子进程失败**：把 `landlock-run:` 前缀 + 任意非零退出码判为 launcher 失败，于是 ripgrep 的“无匹配退出 1”被报成 `SANDBOX_UNAVAILABLE` → 根因：> “The public sandbox result type could express only a bag of substrings.” 且文件搜索适配层把下层结构化错误替换成自己的泛化 `SEARCH_FAILED` → **可复用纪律**：> “Process attribution requires a conjunction of independent evidence; a shared prefix is not a protocol.” / > “An adapter must preserve structured failures owned by the seam below it instead of replacing them with its own nearest generic category.” → `postmortem/0004-...md:52,54`
- **0004 排除项与平台**：> “Informational and fatal diagnostics can share a namespace, so exclusions must be exact and narrow while unknown fatal lines stay fail-closed.” / > “Platform-dependent behavior needs a deterministic fake at the native boundary plus one assembled product path; a self-skipping real-kernel test cannot carry that regression alone.” → `postmortem/0004-...md:53,55`
- **复盘本身的写作纪律**（对“写事故记录”的人）：只有同时 **subtle / systemic / costly to rediscover** 才写；每篇必须以 Executive summary 开头 → `postmortem/README.md:9,11`

## 因“静默失败”而立的规定

- **注册被静默吞掉（最典型）**：`!!js` 放在 entry metadata 上不会插值，插件**静默禁用**且无任何诊断 → 规定：配置条件化只用显式 overlay，并新增 `verify-cordis-config` **静态拒绝** Loader entry metadata 中的表达式节点，`dsh-session-snapshot` **拒绝** `UNKNOWN_TOOL` 结果进入 fixture → `postmortem/0002-...md:39-41`
- **同名注册被静默抢占**：> “The reservation holds even when filters keep the installer inactive, so two plugins can never silently claim the same package name; a duplicate, blank, or whitespace-containing name throws.” 且配套 `pnpm run verify-package-invariants` 机械拒绝生成占位、未解释的空 installer、漏用 reporter、错误注册名 → `subsystems/invariants.md:55,59`
- **挂载顺序导致的“暂时没有”**：> “`form(form)` resolves a mounted facility and throws `form-not-mounted` until the owning plugin loads — assemblies order plugins accordingly rather than silently deferring.” → `subsystems/storage.md:24`；`defineDomain` 在**模块加载期**就 fail loud，`null` schema 直接抛 → :95
- **白屏/未注册 UI**：裸 Vite 只回 HTTP 200，浏览器才抛 `window.__DSH_BOOT__ is missing or not an object` → 规定：`apps/web` 独立 Vite serve 模式在配置阶段就被拒绝，且测试插桩 `Server.listen()` 使“瞬时绑定”无法蒙混；验收必须外部观测**同一 origin** → `postmortem/0003-...md:44,50-52`
- **HTTP 路由注册顺序**：> “Registration order carries no request-facing semantics — named routes are composed to be disjoint, and the fallback seat answers anything no named route claims; one owner only, a second registration throws.” 同时文档承认：fallback handler 在 owner 注册前对未认领请求一律回 404 —— 启动期顺序错就是**静默 404**，故必须显式注册而非依赖顺序 → `subsystems/web-server.md:27,67,86-94`
- **读日志时不要静默归一化**：> “Seed, append, and current persistence reads reject noncanonical headers rather than silently normalizing them”；> “The API rejects a prefix that ends inside an open turn instead of clipping silently.” → `subsystems/session.md:192,665`
- **计划模式不得静默退出**：> “a missing interaction channel and a service reload during review also fail the call rather than silently leaving plan mode” → `subsystems/plan.md:33`
- **投影缺键必须显式失败**：> “A missing projection key fails explicitly.” → `subsystems/permission-presets.md:55`
- **宽容并不总是美德（一处有意的静默降级，作者需知边界）**：subagent 列表的投影折叠 > “folds to a serializable `null` sentinel, treated as no value”，即 malformed / unknown-version 描述符被**故意不加区分**地当作“无值”，只产出 `corrupt` 诊断 → `subsystems/subagent.md:269`
- **可选服务读取的“静默 undefined”**：`ctx.get(name)` 严格，非活动后端读成 `undefined` 而不是把正在拆除的实现交回来 → `postmortem/0001-...md:111`

## i18n / 翻译相关约束

- 配对是**三个同目录兄弟文件**：`foo.md` + `foo.zh.md` + `foo.i18n.yaml`；> “No locale directories, no separate translation repo, no interleaved bilingual files. Pairs merge whole: a PR never lands one language without the other two files.” → `i18n/README.md:10`
- `foo.i18n.yaml` 记的是**两侧的 git blob hash**（不是 commit hash），`--write` 才代表“我确认这一对一致”，且必须点名 pair（`--write --all` 是显式全量形式）→ `i18n/README.md:11-18`
- 语言切换行固定：中文侧 H1 后 ``[English](foo.md)` | 中文`，作者手写的英文侧反向写 `English | `[中文](foo.zh.md)``；**生成**的英文源省略该行以保持与生成器字节一致 → `i18n/README.md:21`
- 结构必须一一对应：标题层级与顺序、列表种类、有序列表起始、列表项数、表格行列数、语义链接目标（含精确 query/fragment）、代码块逐字节一致；相对文档链接在语料内必须按侧选 `.md` / `.zh.md`，**缺对侧是错误而不是回退** → `i18n/README.md:22`；`translation-rules.md:24-31`
- > “fenced code blocks — **byte-identical, including comments**”；inline code（命令、flag、配置键、文件路径、事件名、API 名、版本号）**verbatim，绝不翻译或重排** → `i18n/translation-rules.md:29-30`
- 术语必须服从真源：> “every listed term MUST follow its row and its ‘不要译作’ prohibitions”；未列入的术语若无权威先例，中文侧**保留英文**并登记「待定术语」，不得自行创造译名 → `i18n/translation-rules.md:37-39`；术语表见 `i18n/terminology.md`（例如 `seam`、`slot`、`fiber`、`subagent`、`Typert`、`spill`、`Cordis 插件` vs `Cordis 配置项` 全部**保留英文**；`plugin`→插件、`tool`→工具、`skill`→技能、`waterfall`→waterfall（瀑布式事件）→ `i18n/terminology.md:59-70,119-120`）
- RFC 2119 强度不得削弱：MUST/MUST NOT/SHOULD/MAY → 必须/禁止/应当/可以，且**保留源文强调跨度**（源码粗体则译文粗体）→ `i18n/translation-prompt.md:106`
- 中文排版硬性规则（`.zh.md` 才受约束）：中英/中文数字间一个半角空格、中文正文用全角标点、并列项用顿号、禁止全角数字与全角拉丁字母、专有名词保持大小写（GitHub、TypeScript、DeepSeek）、第二人称用“你”→ `i18n/translation-rules.md:45-52`
- **排除清单里对本任务最重要的两条**：`docs/AGENTS.md` 与各类 agent 指令文件**永不配对**（仅英文维护）；`i18n/translation-prompt.md` 因“its body is machine-consumed verbatim”而不配对，改它会改变流水线行为 → `i18n/README.md:55-57`
- 门禁能力的诚实边界（不要拿绿灯当质量证据）：> “**a green gate means the pair was confirmed consistent at these exact contents, not that the confirmation was sound.**” / “A re-recorded pair with a sloppy counterpart passes the gate; it must not pass review.” → `i18n/README.md:40`
- 插件若带客户端 UI，则本地化走**注册项的 locale namespace**（由注册声明推导出 `t`），不是全局字典；`permission-presets` 即为例证：> “the shipped client locale dictionaries own Auto's label and description, while configured preset presentation remains Host-owned.” → `subsystems/permission-presets.md:49`

## 不许自己造的东西

- **不要自己声明 invariant 注册名**：每个包只能以自己的**完整 npm 包名**注册，且 `./invariant` companion 是发布/装配强制的；没有可观察事件或可变数据关系的包必须导出空 installer，首行注释固定以 `No runtime invariant:` 开头并解释为什么无可检查项；`pnpm run verify-package-invariants` 会机械拒绝生成占位与未解释的空 installer；检查只能断言**权威事件流或可变数据，绝不 service/method 是否在场** → `subsystems/invariants.md:5,59`
- **不要自己造 storage/domain 机制**：数据面走 `mount(form, facility)` + `defineDomain(spec)` + `domainTable`，重复 mount 抛 `duplicate-mount`，未挂载抛 `form-not-mounted`；`ctx.storage.domain` 与 `ctx.storageDomain` 是同一个对象，不要另建一层 → `subsystems/storage.md:24,95`
- **不要自己起 HTTP 载体**：浏览器流量走 `ctx.webServer`，`register(route)` 的重复 `(kind, path)` 直接抛，fallback seat **只允许一个 owner**（第二个注册抛），upgrade 路由同一 path 也只能有一个协议 owner，index 注入用 `webserver/index-inject` 结构化行而不是自己改 index.html → `subsystems/web-server.md:27,51,71-94`
- **不要自己发布权限预设**：> “Callers cannot publish another preset through a generic contribution API.”；`custom` 是**只读派生值**，> “it is never a switch target or an event payload”，也不得进入 `permission.defaultPreset` schema；配置项名为 `custom`/`auto` 会在插件加载期抛错 → `subsystems/permission-presets.md:45,49,55`
- **不要自己攒工具输出落盘/后台任务/进程**：走 `spill`、`ctx.jobs`、`ctx.subprocess`、shell/subprocess seam，而不是自己写文件或 `child_process`（间接证据：`postmortem/0004` 的修法即把文件搜索改走 `ctx.subprocess` 并保持“在 sandboxed bash 之外”；`postmortem/0003` 禁止用 shell `&` 绕过托管任务生命周期）→ `postmortem/0004-...md:46`、`postmortem/0003-...md:52`
- **不要在下层 seam 之外重造错误分类**：> “An adapter must preserve structured failures owned by the seam below it instead of replacing them with its own nearest generic category.” → `postmortem/0004-...md:54`
- **不要发明注册/顺序语义**：注册本身要么生效要么抛错（`duplicate-mount`、`form-not-mounted`、`WEB_DUPLICATE_PROVIDER`、duplicate `(kind,path)`、fallback 二号 owner、重复 package 名），不要依赖“后注册覆盖”或“按顺序生效” → `subsystems/storage.md:24`、`subsystems/web-server.md:27`、`subsystems/invariants.md:55`、`subsystems/web.md:139`

## 未解答

- `subsystems/subagent.md:269` 明确说 malformed / unknown-version 描述符“deliberately undistinguished”，但同一句被截断（`(line truncated)`），文档未给出作者侧应如何区分“无值”与“损坏”的正面做法。
- `postmortem/0001` 的修法是 `ctx.get('sessionPersistence')`；文档未说明**声明在 `inject` 里的服务**在 `ctx.<name>`、`ctx.get(name)` 与影子边界下的完整等价/差异矩阵（只给了“声明过可直读、未声明必须 get”这一条经验规则）。
- 破坏性变更表（`persistence-changes/README.md:47-55`）只说“minimum decision”，未列出 `union-variants-changed`、`index-signature-changed` 的完整判定理由（表中出现但规则表未逐条命名）。
- 12 篇 0 变更的 release 记录（`dsh-v0.0.1-rc.4/rc.5`、`dsh-v0.1.0-rc.1..rc.6`、`dsh-v0.1.2-alpha.3/alpha.5`、`dsh-v0.1.2-rc.1`、`dsh-v0.1.5-rc.1/rc.2`）除“digests unchanged”外无内容——**不能**据此推断这些版本没有影响插件的行为变更（该档案只覆盖持久化类型，见 `releases/README.md:11,79`）。
- `docs/subsystems/` 中被本任务排除的 17 篇（尤其 `extensions.md`、`slots.md`、`client-modules.md`、`client-resources.md`、`sidebar-right.md`、`web-client.md`）才是动态 Cordis 插件与 Client slot／localization 的正面契约；本摘要中相关结论只能从旁证给出。
