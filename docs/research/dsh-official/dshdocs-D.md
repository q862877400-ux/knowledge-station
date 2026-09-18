# DSH 官方文档消化：工具 / LLM / 会话 / 子代理

> 引用相对 docs 根 `D:\AI\DSH\deepseek-harness\docs`；行号为本次阅读所得。只读英文原版。

## 注册一个模型工具

- 唯一入口 `ctx.tools.register(definition: ToolDefinition): () => void`：
  > "Register globally or in the calling agent scope. Scoped tools shadow globals; duplicates within one layer and the reserved `run_code` name fail." `subsystems/tools.md:513`
  > "@returns the exact disposer that unregisters the tool." `subsystems/tools.md:519`
- 插件需 `export const inject = ['tools']`，在 `apply(ctx)` 内注册；`defineTool` 来自 `@deepseek-ai/dsh-tools`。`cookbook/adding-a-tool.md:12-18`
- 官方最小形状（`cookbook/adding-a-tool.md:14-36`，省略 import）：
```ts
export const name = 'my-tool'
export const inject = ['tools']
export function apply(ctx: Context) {
  ctx.tools.register(defineTool({
    name: 'read_file',
    description: 'Read a file from disk.',          // 模型唯一看到的说明
    parameters: {
      path: { type: 'string', required: true, description: 'Absolute path' },
      limit: { type: 'number' },                     // 默认可选
    },
    output: {
      schema: { type: 'string' },
      render: (_args, value) => [{ type: 'text', text: value }],
    },
    async execute(args, exec) { return readFile(args.path, { encoding: 'utf8', signal: exec.signal }) },
  }))
}
```
- `ToolDefinition = ToolSchema + { output(必填), execute, finalizeContent?, timeoutMs?, isConcurrencySafe?, presentCall?, presentResult? }`；`output = { schema: JsonSchemaNode, render(args,value): ContentBlock[], presentationMeta? }` `subsystems/tools.md:15-22,27-93`
- handler `execute(args: unknown, exec: ToolRunContext): Promise<unknown>`；经 `defineTool` 后 args 被校验/推断，exec 带 `signal/agent/token/callId` 与 `deferContext()`、`concludeTurn()`。`subsystems/tools.md:40,96,225-242`
- 返回值：**只**返回 `output.schema` 声明的 canonical lossless-JSON 值（不返回 content blocks）；registry 快照/校验/冻结后调 `output.render` 产出模型内容。`cookbook/adding-a-tool.md:45`
- 错误：**throw**。"Throwing or returning an invalid value means `isError`."；入参不合法 → `ToolArgsError(INVALID_ARGS)`，输出不合法 → `ToolOutputError(INVALID_TOOL_OUTPUT)`，未知工具 → `ToolNotFoundError`→`UNKNOWN_TOOL`；结构化失败 `ToolErrorInfo{name,code,reason?}`。`cookbook/adding-a-tool.md:46`、`subsystems/tools.md:149,374-379,419`
- schema DSL：`string|number|integer|boolean|null|array|object|json|oneOf`；参数根是隐式开放对象，必填靠逐属性 `required: true`；"> An explicit object node always declares `additionalProperties: true | false`." `subsystems/tools.md:100,119-132`
- 权限不要写进 definition：按 scope 收窄用 `ctx.tools.restrict({allow?,deny?})`；审批用 `tools/pre-execute` 返回 `{kind:'ask'}`（非授权/无审批通道即拒）；最终单调拒绝用 `ctx.tools.guard()`。`subsystems/tools.md:399-404,417,521-540`
- 注册即 effect：disposer 挂 fiber，卸载即注销；热替换须先 dispose 再 register。`cookbook/adding-a-tool.md:38,43`

## 调用 LLM

- 官方只有流式：**`ctx.llm.stream(options: GenerateOptions): AsyncIterable<StreamChunk>`**；"> The abstract `llm` service: an adapter registry plus a streaming model-call API, interceptable via the `llm/stream` waterfall." —— **文档中没有 `complete()`**。`subsystems/llm-streaming.md:894-896,1043`
- 入参 `GenerateOptions`：`provider`、`model`、`messages`、可选 `system`（"> System prompt text for one-shot callers"）、`tools?: ToolSchema[]`、`temperature`、`maxTokens`、`stop`、`signal`、`sessionId`、`purpose?: 'compaction'|'session-title'`。`subsystems/llm-streaming.md:581-622`
- 出参不是成品文本：7 种 `StreamChunk`（block-start / text-delta / reasoning-delta / tool-call-delta / block-end / usage / finish）`subsystems/llm-streaming.md:196-218`；用共享 `BlockAssembler`（`push()`/`blocks()`/`usage`/`finish`/`message()`）折叠——"> A consumer that needs the assembled result without re-implementing the fold uses this." `subsystems/llm-streaming.md:366-422`
- 要保证 call config 与日志/能力一致时用 `ctx.llm.prepareCall(config, signal?)` → `PreparedLlmCall.stream(options)`；"> The request's call-config fields must match `config`; reuse or mismatch fails with `INVALID_PREPARED_CALL`." `subsystems/llm-streaming.md:775-780,1030`
- 直接调用是官方承认的用法（"> `GenerateOptions.system` serves direct one-shot callers such as title providers."），但**不重试**："> One adapter call is one provider attempt. Adapters disable library retries. Agent-level recovery opens another durable numbered turn; direct `ctx.llm.stream()` callers remain single-attempt." `subsystems/llm-streaming.md:716,303`
- 取消走 `options.signal`；失败被规范化为终止 `finish{kind:'error'|'aborted', failure}` 而不是抛给消费者。`subsystems/llm-streaming.md:610,201-203,636-637`
- 会话当前 provider/model 来自日志里的 request header，可经 `agent/request` waterfall 替换（`LlmCallConfig{provider,model,reasoningEffort?,temperature?,maxTokens?,stop?}`）。`subsystems/llm-streaming.md:710-735`
- 只有**新增供应商**才写 adapter：`ctx.llm.registerAdapter(providers, adapter)`（路由重复原子失败）。`subsystems/llm-streaming.md:907`、`user/develop/practice/llm-adapter.md:121`

## 会话与状态

- 模型：session 是 append-only 事件日志，是唯一真源；消息历史是派生出来的、不另存。`subsystems/session.md:5`
- 读：`ctx.sessions.get(id)` / `list()`；`session.header`、`seq`、`surface`、`requestHeader()`、**`deriveMessages(): Message[]`**（模型历史用它，别自己 fold）；跨会话/全文检索用 `ctx.sessionQuery`。`subsystems/session.md:1011-1022,435-646`
- ⚠ `session.eventAt()` / `snapshotEvents()` / `ownEvents()` 已 `@deprecated` —— "new calls are prohibited." `subsystems/session.md:527,537,549`
- 写：唯一官方路径是追加事件 `session.append(type, data, ...opts)`；surface 类型（`system/message|user/message|assistant/message|tool/result`）必须给 `SurfaceIntent{surfaceOp:'append'|{op:'replace',startSeq,endSeq}}`。`subsystems/session.md:599-603,318-343`
- 插件自己的会话状态：declaration-merge `SessionEventMap` 增自己的 **log-only** 事件（无 `surfaceOp`、不进模型历史），再 `append`；关系校验归自己的 invariant companion。`subsystems/session.md:722-724,708-710`
- 非 session-log 的持久数据走 `ctx.storageDomain.open(spec)`（"> product packages never touch backends directly."），handle 由调用方 `close()` 释放。`subsystems/storage.md:5,194-215`
- **projection vs storage**：projection = 对已提交事件做纯同步 fold 得到的当前值 —— "> The framework drives, the domain computes: the registry subscribes to `session/event` once and folds every committed event through every unit; domains hold no subscriptions and clients never fold domain events."；storage = 持久介质（session log 走 `sessionPersistence` handle，其它走 `ctx.storage` 域）。`subsystems/session-projection.md:5`
- 注册 projection 单元 `ctx.sessionProjections.register(definition)`：`key`、`stateSchema`、`init(header,inheritedEventCount)`、`apply(state,event)`、可选 `wire.view`、`stateVersion`；"> All functions MUST be synchronous ... and `state` MUST be plain JSON"；"> A unit uninterested in an event MUST return the same state reference". `subsystems/session-projection.md:18-22,22-67,216`
- 读 projection：`ctx.sessionProjections.stateOf(session,key)`、`.snapshot(session,keys?)`（同步一致切面），订阅 `.onChanged(listener)`；`ctx.sessionProjectionCache.cachedSnapshot(...)` 只是提示（"> Values may trail the live Session and are therefore hints, not a complete baseline."）。`subsystems/session-projection.md:232-253,255-263`
- 生命周期事件：`session/event`（emit, post-commit）、`session/flush`（parallel；显式耐久屏障 `await ctx.sessions.flush(session)`）、`session/created`、`session/disposed`。`subsystems/session.md:1199-1237,1009`
- 所有权/清理：所有 `register*` 返回 disposer 且挂 fiber；`ctx.sessions.create()` 的 session 由 fiber 拥有（卸载即出 store）；要与 loop 顺序一致时用 `prepare`+`enter`+`announce`。`subsystems/session.md:919-940,942-994`

## 子代理

- 官方入口 `ctx.subagents`（`SubagentRuntime`），**没有 `run()`**。一次性：`await ctx.subagents.start(name, request): Promise<SubagentRun>`。`subsystems/subagent.md:685,492-496`
- `SubagentStartRequest`：必填 `prompt: ContentBlock[]`、`parent: Agent`、`signal: AbortSignal`（"> the canonical cancellation channel both before and after startup"）；可选 `label`、`agentOptions?: AgentOptions`（模型覆盖）、`outputSchema?: ObjectJsonSchema`、`maxDepth`、`toolFilter?: ToolRestriction`、`persona`。`subsystems/subagent.md:50-106,60,68`
- 返回 `SubagentRun{ id, localAgent, result: Promise<SubagentResult>, dispose() }`："> Consumers await that result and always dispose the run to reach quiescence."；`result` 不因子级模型失败而 reject（变为 `stopReason:'error'`）。`subsystems/subagent.md:350,362-388`
- `SubagentResult{ output: ContentBlock[], structured?, diagnostic?, stopReason }`；只有请求了 `outputSchema` 才可能有 `structured`，且不保证。`subsystems/subagent.md:288-322`
- 后台/继续型：`startContinuable(spec): Promise<{childId, messageId}>`（"> resolves ... without waiting for the turn to start"）；随后 `sendMessage(sender,targetId,content,options)`（仅直接父子）、`interrupt(targetSessionId,authority)`、`listChildren` / `listDescendants`。`subsystems/subagent.md:506,136,522,539,582,599`
- 后端注册 `registerProvider(provider: SubagentProvider)`（effect-scoped、HMR 安全）；"> The continuation manager owns identity reservation, composition, Agent creation, prompt delivery, cold resume, ownership, and disposal, so a provider never sees the child's Agent, handle, turns, or teardown." `subsystems/subagent.md:658,444-447`

## 不许自己造的东西

先查 `tool-catalog.md`（**生成物**：`scripts/gen-tool-catalog.ts`，`pnpm run gen-tool-catalog` 再生成，"> do not edit by hand"；它真的 boot 每个工具插件再读 `ctx.tools.schemas()`）。结构 = `## Tool Package Map` 一张表（列：Tool package / Model-visible names / Requires / Writes-affects / Shipped aliases / Deployment note，约 28 行，`tool-catalog.md:12-45`）+ 每包一个 `## @deepseek-ai/dsh-...` 段，段内每工具一个 `### <tool_name>`，给 description + parameters JSON Schema + `Source:` 源文件指针（`tool-catalog.md:47-2614`）。**查法**：Package Map 找名字 → `grep "^### \`?"` 定位段 → 读该段 Schema 与 Source。顶层分类即那六列；工具簇：fs/搜索、shell/PTY/terminal、jobs、subagent 及控制、agent-team、session-query、goal/todo/plan、schedule、workflow/ralph、skill、cordis、MCP 资源、web、LSP、browser-use。

- 入参校验 / 输出校验+冻结+物化 → `defineTool` + registry → `cookbook/adding-a-tool.md:42`、`subsystems/tools.md:149,384`
- throw→isError 与结构化错误身份 → registry → `cookbook/adding-a-tool.md:46`、`subsystems/tools.md:419`
- 超时 → `timeoutMs` + `tools/execute` wrapper（`dsh-tool-call-timeout-policy`）→ `subsystems/tools.md:55-60`
- 重试 / 指标 → `tools/execute` around-dispatch（别写进工具）→ `cookbook/adding-a-tool.md:59`、`subsystems/tools.md:620`
- 并发调度判定 → `isConcurrencySafe` → `subsystems/tools.md:74`
- 大结果截断/溢出落盘 → 输出上限 + spill pipeline → `cookbook/adding-a-tool.md:65`、`subsystems/tools.md:693`
- 审批门 → `tools/pre-execute` 的 `ask` + `ctx.approval`（别在 execute 里问用户）→ `subsystems/tools.md:399-404`、`tool-execution-pipeline.md:16`
- 长任务后台/进度/取消/完成通知 → `ctx.jobs.start({ kind, label, owner: exec.agent, run })` + `job_*` 工具 → `cookbook/adding-a-tool.md:53`
- 给下一轮模型请求追加上下文 → `exec.deferContext()` / `agent.inject({content, source:{kind:'plugin',plugin}})` → `subsystems/tools.md:232`、`cookbook/adding-a-tool.md:49`
- UI 卡片 → `presentCall`/`presentResult` 的 `card` 词表（注意内置 Web Client 不吃这两个，走 `tool.call.toolview` slot）→ `cookbook/adding-a-tool.md:69-91,95`
- 自己拼 HTTP/SSE 调模型 → `ctx.llm.stream()` + `BlockAssembler` → `subsystems/llm-streaming.md:1043,368`
- 自己 fold 消息历史 → `session.deriveMessages()` → `subsystems/session.md:637,648-657`
- 自己写旁路状态文件存会话状态 → `session.append`（log-only 事件）或 `ctx.storageDomain` → `subsystems/session.md:724`、`subsystems/storage.md:5`
- 自己维护每会话派生状态缓存 → `ctx.sessionProjections.register` + `ctx.sessionProjectionCache` → `subsystems/session-projection.md:216,118-120`
- 自己 spawn 子 Agent/子进程跑子任务 → `ctx.subagents.start` / `startContinuable` → `subsystems/subagent.md:685,506`
- 自己注入技能 prompt → `ctx.skills.register` / `registerProvider`（本地目录约定 `<project>/.dsh/skills`(100)、`<project>/.agents/skills`(200)、`<dshHome>/skills`(400)；名必须 kebab-case）→ `subsystems/skills.md:295,284,66-77,85`
- 自己 dispatch 耐久屏障 → `await ctx.sessions.flush(session)` → `subsystems/session.md:996-1003`

## 坑

- `output`/`execute`/`timeoutMs`/`presentCall` 等宿主字段 "> must never leak into a model request"；模型只看到 name/description/parameters。`subsystems/tools.md:11,56`
- handler 用 throw，不要 `return {error}`（文档无此约定）；"不理想但成功"要放进 canonical value。`cookbook/adding-a-tool.md:45-46`
- args / call identity 对工具只读："> Arguments cannot be rewritten because history, audit, UI, and execution must agree."；"> Treat `args` as readonly input." `subsystems/tools.md:417`、`cookbook/adding-a-tool.md:44`
- 注册后别改 schema 或换回调（定义是 borrowed readonly）："> do not mutate its schema or replace callbacks after registration." `cookbook/adding-a-tool.md:43`
- 事件 data 必须无损 JSON：Map/Set/Date/class 实例/BigInt/undefined/NaN/循环引用会在 `append` 处抛——"> the durable source of truth, so a bad event fails at the append site". `subsystems/session.md:584-597,732`
- projection 的 `init`/`apply`/`view` 必须同步且纯（async 会撕裂 carrier 的一致性切面）；无关事件必须返回同一引用（`Object.is`）。`subsystems/session-projection.md:18-20,38-45`
- projection 借出的值是 live 的："> callers must not mutate it."；缓存切面只是提示、可能落后。`subsystems/session-projection.md:102,237,255-258`
- `session/event` 是 post-commit fire-and-forget：监听器抛错不会让 append 失败、也不回滚。`subsystems/session.md:1199-1201`
- 直接 `ctx.llm.stream()` 单次尝试，无重试、无限流处理；重试只有 agent loop 的 `agent/request-error`→`{kind:'retry'}`。`subsystems/llm-streaming.md:302-303`
- `ctx.llm.stream()` 的失败是终止 `finish{kind:'error'}` 而非抛出，别只靠 try/catch。`subsystems/llm-streaming.md:201-203`
- 子代理 run 必须 `dispose()`；非 `completed` 的 `stopReason` 意味着 output 可能是残的，要映射成 `isError`。`subsystems/subagent.md:350,290`
- 子代理的 caller `signal` 只在 inbox 接收前有效："> later caller cancellation neither cancels the accepted turn nor disposes the child." `subsystems/subagent.md:152`
- `sendMessage` 只允许直接父子；兄弟、隔代、自己、一次性子级都被拒。`subsystems/subagent.md:150`
- 别在会合入主干的新代码里用 `eventAt/snapshotEvents/ownEvents`。`subsystems/session.md:527`
- 写了 `presentCall/presentResult` ≠ 有 Web 卡片。`cookbook/adding-a-tool.md:95`

## 未解答

- 没有 `ctx.llm.complete()` 之类"取一条消息"的官方便捷函数；只给了 `stream()` + `BlockAssembler`。
- 直接 `ctx.llm.stream()` 调用者的重试/退避/限流官方做法（`providerRetryAfterMs` 明确 "> not a retry decision"）。
- 工具名是否有字符/正则规则或推荐命名空间前缀（只写了同层重名失败 + 保留 `run_code`）。
- 工具输出的默认上限数值与单位。
- 一个工具能否注册进"别的 agent 的 scope"（只有带 `scope` 参数的读接口与 scope 内注册）。
- 插件能否自己缓存会话状态或写旁路文件：四篇文档没有一句禁止（只有"日志是真源""domains 不持有订阅""产品包不直连 backend"）。
- `ContinuableStartSpec` 的字段清单（正文只说 provider / delegation request / caller cancellation），以及各 backend 的 `AgentOptions` 合并细则。
- 子代理是否有流式/部分输出 API（`SubagentRun` 无该成员；只有 `subagent/start|end` 观测事件）。
- 除 `agent/request` waterfall 外，插件"读取当前会话模型"的官方 API 未在本次范围内给出。
