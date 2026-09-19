# dsh-weknora 精读：同宿主现成插件参考实现

> **被读对象**：`D:\AI\WeKnora\packages\dsh-weknora`（下称 `dsh-weknora/`），MIT，npm 包名 `@wxg-prc-cpg/dsh-weknora`。
> **读法**：只读源码，未改动 `D:\AI\WeKnora` 下任何文件。文中 `dsh-weknora/x.ts:NN` 的行号是源码原文行号。
> 唯一一处"跑过"的东西是 §2 末尾的未知键探针：把 `config.ts` **复制到 `%TEMP%`** 后用 `node --experimental-strip-types` 运行，WeKnora 树未被触碰。
> **对照物**：我们的插件 [plugin/src/index.js](../../../plugin/src/index.js)（宿主侧）、[plugin/client/](../../../plugin/client/)（客户端）、[plugin/cordis.patch.yml](../../../plugin/cordis.patch.yml)。

---

## 结论（一句话）

**它没有界面**——这是一个纯宿主侧（headless）插件：只有一个 `apply(ctx, config)` 导出，往 `ctx.tools` 注册 4 个模型工具，全包没有客户端半边（无 `dsh.client` 字段、无 client 入口、无 `.tsx`/界面代码），它唯一与 UI 发生关系的方式是**让回复里能渲染出图片**（把引用中的 `resource://` 换成 http(s) 直链，见 §5）。对我们而言，它是"宿主侧工具 + 配置 + 契约测试"的现成参考，**不是**客户端 UI 的参考。

---

## 1. 插件形态

### 1.1 入口导出什么

`dsh-weknora/src/index.ts` 只有三个导出有契约意义：

```ts
export const name = 'dsh-weknora'                    // :12
export const inject = ['tools'] as const             // :15
export function apply(ctx: HarnessContext, config: unknown): void   // :28
```

`apply` 的正文（`index.ts:29-36`）就是全部：校验配置 → 造 client → `createTools()` → 循环 `ctx.tools.register()`：

```ts
const resolved = resolveConfig(config as never)      // :29
const client = new WeknoraClient(resolved)           // :30
for (const definition of createTools(client, resolved)) {
  ctx.tools.register(definition)                     // :33
}
ctx.logger?.info(`dsh-weknora: registered …`)        // :36
```

**没有 `export default`**——与我方 [plugin/src/index.js:18](../../../plugin/src/index.js#L18) 注释里写的契约（`name` / `inject` / `apply(ctx, config)`）完全一致。另外 `index.ts:17-20` 额外 re-export 了 `Config` 类型、`ConfigError`、`WeknoraClient`、`createTools` 供库用户使用。

### 1.2 怎么挂载

`dsh-weknora/package.json`：

| 行 | 内容 |
|---|---|
| `:2` | `"name": "@wxg-prc-cpg/dsh-weknora"` |
| `:30-32` | `"type": "module"`；`main: ./dist/index.js`；`types: ./dist/index.d.ts` |
| `:33-39` | `exports` **只有** `"."` → `dist/index.js` 与 `"./package.json"` |
| `:40-45` | `files: ["dist", "cordis.patch.yml", "README.md", "README_CN.md"]` |
| `:53` | `"test": "npm run build && node --test \"test/*.test.mjs\""` |
| `:56-60` | `"dsh": { "bundle": { "patch": "./cordis.patch.yml" } }` |
| `:61-64` | `devDependencies` 只有 `@types/node` + `typescript` ——**没有 `dependencies` 字段，零运行时依赖** |

`dsh-weknora/cordis.patch.yml:4-14` 是整份文件（14 行），一个 `insert` 行：

```yaml
- insert:
    - id: weknora
      name: "@wxg-prc-cpg/dsh-weknora"   # :8 必须是发布包名，loader 按此 import
      config:
        baseUrl: !!js process.env.WEKNORA_BASE_URL ?? 'http://localhost:8080/api/v1'
        apiKey: !!js process.env.WEKNORA_API_KEY
        knowledgeBaseIds: !!js (process.env.WEKNORA_KNOWLEDGE_BASE_IDS ?? '').split(',').filter(Boolean)
```

注意 `:6-7` 的注释原文：「Must be the published package name — the loader imports this specifier. / Quoted because YAML reserves a leading `@` in plain scalars.」——与我方 [plugin/cordis.patch.yml:17-18](../../../plugin/cordis.patch.yml#L17-L18) 的注释同款结论。它的"出厂 config 层"**全部走环境变量**（`config` 块里没有一个硬编码值）。

### 1.3 有没有客户端半边 —— 明确结论：没有

证据（四条，互相独立）：

1. `package.json:56-60` 的 `dsh` 字段**只有** `bundle.patch`，没有 `dsh.client`（或任何 client 入口声明）。
2. `package.json:40-45` 的 `files` 只发布 `dist` + patch + 两份 README，没有任何前端资源目录。
3. `package.json:33-39` 的 `exports` 只暴露 `./dist/index.js`，无子路径。
4. 全包（含 test/）grep `dsh.client`、`.tsx`、client 入口：**0 命中**。`src/client.ts` 是**后端 HTTP 客户端**（WeKnora REST/SSE），不是"客户端半边"——名字容易误读，它跑在宿主进程里（`index.ts:7` 起 `import { WeknoraClient } from './client.ts'`）。

它唯一与 DSH 网页端的接触点是**文本约定**：`README_CN.md:109-111`

> 默认 `resourceUrls: public` 时，WeKnora 会把片段里的 `resource://` 图改写成可直接加载的 http(s) 直链——把这些 Markdown 图片写进回复，dsh 网页端就会把图画出来。

即：它不写 UI 代码，而是**让模型把 Markdown 图片写进回复**，由 dsh 网页端渲染。这条对我们（PDF/证据图呈现）比它的工具代码更值得注意。

---

## 2. 配置声明

### 2.1 用什么声明：**手写**

- 全包 grep `zod` / `schemastery`：**0 命中**。
- `dsh-weknora/src/config.ts:12-41` 的 `Config` 是一个 **TypeScript `interface`**——运行时被擦除，**没有任何运行时 schema 交给 Cordis**。
- 唯一的运行时校验是 `resolveConfig(raw)`（`config.ts:133-192`），在 `apply` 里第一件事调用（`index.ts:29`）。`index.ts:26` 的注释写明意图：「validated here so a typo fails the load」。

### 2.2 配置键、默认值、必填/可选

键清单见 `config.ts:12-41`，解析后的形态见 `config.ts:44-57`，默认值集中在 `config.ts:59-67`：

| 键 | 类型（config.ts 行） | 默认值（:59-67） | 必填？ |
|---|---|---|---|
| `baseUrl` | `?: string` (:14) | `http://localhost:8080/api/v1` | 否（缺省即此值） |
| `apiKey` | `?: string` (:16) | 未设 | 否（不设 = 部署无鉴权） |
| `tenantId` | `?: string` (:18) | 未设 | 否（仅平台级 key 需要，运行时后果） |
| `knowledgeBaseIds` | `?: string[]` (:20) | `[]` | 否 |
| `agentId` | `?: string` (:22) | 未设 | 否（不设 = 走 RAG） |
| `maxResults` | `?: number` (:24) | `8` | 否 |
| `maxChunkChars` | `?: number` (:26) | `1200` | 否 |
| `requestTimeoutMs` | `?: number` (:28) | `30000` | 否 |
| `chatTimeoutMs` | `?: number` (:30) | `300000` | 否 |
| `resourceUrls` | `?: 'handle' \| 'public'` (:36) | `public` | 否 |
| `toolPrefix` | `?: string` (:38) | `weknora` | 否 |
| `tools.*` | `?: ToolToggles` (:3-9, :40) | 四项全 `true` (:180-183) | 否 |

**必填/可选怎么表达**：全部写成 TS 可选（`?:`）；"必填"语义不靠声明，靠运行时兜底。`config.ts:144-146` 只在**给了值**时校验协议：

```ts
if (url.protocol !== 'http:' && url.protocol !== 'https:') {
  violations.push(`baseUrl must use http or https, received ${url.protocol}`)
}
```

### 2.3 校验器的四个可抄细节

1. **逐字段小函数**：`positiveInt` / `stringList` / `optionalString` / `toggle`（`config.ts:90-125`），每个都把违规文案推进 `violations` 数组而不是抛。
2. **空白坍缩**：`optionalString`（`config.ts:108-116`）把 `''`、`null`、`'   '` 统一变成 `undefined`——`config.test.mjs:48-53` 钉住了这件事（"blank strings collapse to unset rather than empty headers"）。
3. **聚合报错**：`ConfigError` 把所有违规拼成一条（`config.ts:70-75`），最后一次性抛（`config.ts:190`）：
   ```ts
   super(`dsh-weknora configuration is invalid:\n  - ${violations.join('\n  - ')}`)
   ```
   `config.test.mjs:27-39` 一次传入 4 个坏值，断言 4 条文案**同时**出现。
4. **交叉约束**：四个工具开关不能全关（`config.ts:187-189`），文案原文：`at least one tool must stay enabled; remove the plugin row instead of disabling all of them`（`config.test.mjs:41-46`）。

### 2.4 未知键会不会被拒 —— **不会**（我实测过）

`resolveConfig` 只读已知键，**没有任何"扫描未知键"的代码**。我把它复制到 `%TEMP%` 后用 `node --experimental-strip-types` 实测（`v26.7.0`，WeKnora 树未改动）：

| 输入 | 结果 |
|---|---|
| `{ baseURL: 'https://kb.example.com' }`（键名拼错） | **OK**，静默回落 `http://localhost:8080/api/v1` |
| `{ tools: { serach: false } }`（嵌套拼错） | **OK**，静默忽略，四项仍全 `true` |
| `{ baseUrl: 'https://kb.example.com', bogus: 1 }` | **OK**，`bogus` 被丢弃 |

⇒ `index.ts:26` 说的 "a typo fails the load" **只对值的类型/取值错误成立，对键名拼错不成立**。这一点上它的手写校验**弱于**我们现有的 [plugin/src/index.js:1096-1102](../../../plugin/src/index.js#L1096-L1102)（我们那 6 行会当场抛错）。见 §"不该抄的" 第 1 条。

---

## 3. 工具注册

### 3.1 用 `defineTool` 还是裸对象 —— **裸对象**

- 全包 grep `defineTool`：**0 命中**。四个工具都是普通对象字面量（`tools.ts:189-240`、`:244-360`、`:364-451`、`:456-551`），由 `createTools()` 返回 `ToolDefinition[]`（`tools.ts:156`）。
- 它**自己声明**了一份结构类型 `dsh-weknora/src/harness.ts`，理由写在 `harness.ts:1-10`：

  > Declaring them here keeps the package free of runtime dependencies on harness internals: the shipped code only ever hands `ctx.tools.register()` a plain object, so a harness release that adds optional definition fields does not require a republish of this plugin.

  `harness.ts:8-9` 注明对齐对象：「The shapes mirror `@deepseek-ai/dsh-tools` (`ToolDefinition`) and `@deepseek-ai/dsh-llm` (`ContentBlock`, `ToolSchema`) as of dsh 0.1.0-rc.8.」

它声明的 `ToolDefinition`（`harness.ts:37-48`）：`name` / `description` / `parameters` / `output{schema,render}` / `execute(args, exec)` / `timeoutMs?` / `isConcurrencySafe?`。
`ToolRegistry.register` 返回 disposer（`harness.ts:51-53`），注册是 effect（`index.ts:23-24` 注释：「Each registration is an effect, so unloading or reconfiguring the plugin withdraws the tools without a restart.」）。

**与官方 `defineTool` 的关系（在 DSH 检出里核过，不是猜的）**：官方确实有 `defineTool`——`D:\AI\DSH\deepseek-harness\packages\core\tools\src\schema.ts:545`（`export function defineTool<...>`），且官方自家工具几乎全用它（如 `packages/core/tools/src/index.ts`、`packages/fs/tool-fs/src/read.ts:77`、`packages/web/tool-web/src/search.ts:325` 等 100+ 处）。`defineTool` 会替你做两件它手写时没做的事：校验 `timeoutMs`（`schema.ts:564`：`timeoutMs must be a positive finite number`）和包装 `isConcurrencySafe` 的返回值（`schema.ts:611`）。同时官方 `ToolDefinition` 还多出它这份影子类型里没有的字段：`finalizeContent?` / `presentCall?` / `presentResult?`（见 `packages/extensions/tool-cordis/src/api-catalog.ts:6709` 的声明原文）。
⇒ 结论：**它的裸对象是"发布给陌生人的 npm 包不想锁版本"这一具体处境的取舍**，不是官方常态；我们是仓内 bundle，处境不同（见 §"不该抄的" 第 2 条）。

### 3.2 输入 schema 与参数读取

输入 schema 是**手写 JSON Schema 字面量**（`tools.ts:251-261`），一律 `additionalProperties: false`：

```ts
parameters: {
  type: 'object',
  properties: {
    query: { type: 'string', description: 'Natural-language query; a full question retrieves better than keywords.' },
    knowledge_base_ids: { ...STRING_ARRAY, description: 'Restrict the search to these knowledge base ids.' },
    ...
  },
  required: ['query'],
  additionalProperties: false,
},
```

`STRING_ARRAY` 在 `tools.ts:64` 复用：`{ type: 'array', items: { type: 'string' } }`。
harness 交给 `execute` 的参数是 `unknown`（`harness.ts:45`），所以它自己写取参助手（`tools.ts:66-94`）：`argRecord` / `requiredString` / `optionalStringArg` / `stringArrayArg` / `boundedIntArg`。`boundedIntArg`（`:90-94`）把非法值**静默换成 fallback 并 clamp 到 max**——不抛。

### 3.3 错误怎么返回 —— **抛异常**，错误码就是 HTTP status

- 参数错误：`throw new Error(\`${toolName}: "${field}" is required and must be a non-empty string\`)`（`tools.ts:71-77`）。工具名 + 字段名 + 可通过的取值，三件套。
- 前置业务错误：宁可自己抛也不让后端答 400，`tools.ts:340-343`：
  ```ts
  throw new Error(`${toolName}: this WeKnora credential can see no knowledge base, so there is `
    + 'nothing to search. Check the deployment\'s API key scope.')
  ```
  注释（`:338-339`）说明理由：「the model can act on a message naming the argument to supply, not on a transport error.」
- 传输层：`WeknoraApiError extends Error`，字段 `status`（`client.ts:64-72`），消息形如 `` `${method} ${path} failed with HTTP ${status}: ${reasonOf(text)}` ``（`client.ts:185-187`）。**没有自造错误码枚举**——错误码就是 HTTP status。
- **没有**返回 `{ ok:false, error:{code} }` 这类结构化错误；成功路径才走 `output.schema` 的规范值。

### 3.4 超时 / 重试 / 降级

- **超时**：per-tool `timeoutMs`，检索类用 `config.requestTimeoutMs`（`tools.ts:195`、`:262`、`:378`），`ask` 用 `config.chatTimeoutMs`（`tools.ts:475`）。HTTP 层再把调用方 signal 与本次截止合并（§6.5）。
- **重试**：**只有一处**，且是语义降级而非通用重试——`resourceUrls: public` 被 403 拒绝时改 handle 重发一次，此后常驻 handle（`client.ts:153-165`、`:311-318`）。
- **降级**（两处，都带注释说明"丢了不能伤主载荷"）：
  - `client.findDocuments(...).catch(() => [])`（`tools.ts:349`，注释 `:347-348`：「Losing it must not cost the model its passages.」）
  - 文档元数据 `.catch(() => ({}) as DocumentRecord)`（`tools.ts:429`，注释 `:424-427`：「Metadata is context, not the payload, so a deployment that cannot serve it must still hand over the text.」）

### 3.5 `isConcurrencySafe`

三个只读工具显式声明 `isConcurrencySafe: () => true`（`tools.ts:196`、`:263`、`:379`）；**`ask` 不声明**（`tools.ts:456-551` 里没有这个字段）。官方语义是"未声明 ⇒ exclusive"（`D:\AI\DSH\deepseek-harness\packages\core\tools\src\index.ts:1295-1297`）。

### 3.6 工具名与描述的写法

- 名字：`const name = (suffix: string): string => \`${config.toolPrefix}_${suffix}\``（`tools.ts:157`）。四个名字：`weknora_list_knowledge_bases` / `weknora_search` / `weknora_read_document` / `weknora_ask`。`tools.test.mjs:39` 断言 `^[a-z][a-z0-9_]*$`。
- 描述：**"做什么 + 什么时候用它 + 什么时候不用它、该用哪个"**，并把**兄弟工具名写进描述**（`tools.ts:246-250`）：
  ```
  … Use this to ground an answer in the organization's own documents, and also to locate a document
  by name … Every hit carries a knowledge_id you can pass to weknora_read_document for the full document.
  ```
  `ask` 的描述干脆劝退（`tools.ts:458-462`）：「Reserve it for broad or synthesis questions … For anything you can answer from specific passages, prefer weknora_search: it is far faster and leaves you the evidence to reason over rather than another model's conclusion.」
- 描述还会**随配置变化**：`scopeNote`（`tools.ts:158-160`）按 `knowledgeBaseIds` 是否配置拼出两种文案，`tools.test.mjs:106`、`:142` 分别断言两种。测试还要求 `description.length > 40`（`tools.test.mjs:40`）。

---

## 4. 服务读取方式

- **`ctx.<name>` 直接取，不用 `ctx.get()`**：`ctx.tools.register(...)`（`index.ts:33`）；全包 grep `ctx.get(` = 0 命中。
- **`static inject` / `inject` 声明了哪些**：只有数组形式的 `inject`，**没有 `static inject`**（`index.ts:15`）：
  ```ts
  export const inject = ['tools'] as const
  ```
  注释（`index.ts:14`）：「Cordis waits for the tool registry before applying this plugin.」
- **可缺省服务的兜底写法：只有 `logger` 一处**，用可选链（`index.ts:36`）：`ctx.logger?.info(...)`；对应类型声明 `harness.ts:56-61` 里 `readonly logger?: { info(...); warn(...) }`。
  `tools` 是**硬依赖**（在 `inject` 里），所以它在 `apply` 里从不检查 `ctx.tools` 是否存在。
- **它连 harness 的包都不 import**：`harness.ts:1-10` 自陈的理由是"不要锁 harness 版本"；所有 harness 类型都是本地复刻的（`harness.ts:13-23` 的 `JsonSchemaNode` 支持子集、`:26-29` 的 `TextContentBlock`、`:32-34` 的 `ToolRunContext{readonly signal}`）。

> 对照我方：[plugin/src/index.js:72](../../../plugin/src/index.js#L72) `inject = ['tools', 'webServer', 'systemPrompt']`，可缺省的 `agents` 走 `ctx.get('agents')`（[plugin/src/index.js:1140-1147](../../../plugin/src/index.js#L1140-L1147)）。**两边结论一致**（硬依赖进 inject、可缺省探针），差别只在它只有 1 个硬依赖、我们 3 个。

---

## 5. 引用 / 来源怎么呈现

### 5.1 `render.ts` 只有三个纯函数（共 25 行）

| 函数 | 行 | 行为 |
|---|---|---|
| `clip(text, maxChars)` | `:4-8` | 先 `\r\n`→`\n` + `trim()`；超预算则 `slice(0,max).trimEnd() + '…'`，并返回 `truncated: true` |
| `formatScore(score)` | `:11-13` | `Number.isFinite ? score.toFixed(3) : 'n/a'` |
| `describeScope(ids)` | `:21-25` | `0 → '(deployment default)'`；`≤3 → ids.join(', ')`；`>3 → `${ids.length} knowledge bases`` |

`render.ts:1` 的定位说明：「Pure projections from a tool's canonical value to model-facing text.」——**规范值（进 `output.schema`）与呈现文本（进模型上下文）分开**，`describeScope` 的注释（`:15-20`）解释为什么只报数量：「spelling out every id on every search costs far more than the count is worth; the ids stay in the tool's canonical value for anything that needs them.」（`tools.test.mjs:111-117` 钉住：文本里 `searched: 4 knowledge bases` 且 `doesNotMatch /kb-a/`，但规范值里 4 个 id 全在。）

### 5.2 检索命中的形状（`tools.ts:322-326`）

```ts
const blocks = result.results.map(hit =>
  `[${hit.rank}] ${hit.document} · score ${formatScore(hit.score)} · chunk ${hit.chunk_index} `
  + `· knowledge_id: ${hit.knowledge_id}\n${hit.content}${hit.truncated ? '\n(passage truncated)' : ''}`)
return text(`${result.count} passage(s) for "${result.query}" `
  + `(searched: ${describeScope(result.knowledge_base_ids)}):\n\n${blocks.join('\n\n')}${named}`)
```

即每条命中是：**编号 + 文档名 + `score 0.830` + `chunk N` + `knowledge_id:` + 正文**，外加 `(passage truncated)` 标记。外部契约字段（约定）就是这几个：`document` / `score` / `chunk_index` / `knowledge_id` / `truncated` —— 全部在 `output.schema` 里有声明（`tools.ts:265-306`），`required` 一个不缺。

文档名怎么取（`tools.ts:96-103`）：`knowledge_title` → `knowledge_filename` → `knowledge_id` → `'(untitled)'`。

**按名命中的文档**另起一段（`tools.ts:309-313`）：

```
Documents named "灰度发布检查单" (read them with weknora_read_document):
- <标题> · knowledge_id: doc-release-checklist · in Ops runbooks
```

**空结果给下一步**（`tools.ts:314-320`）：`Nothing in WeKnora matched "…" (searched: …). Try a differently worded query, or widen the knowledge base scope.`；若只有按名命中则：`No passage matched "…", but its name matches document(s).`

### 5.3 `ask` 的引用区（`tools.ts:508-515`）

```ts
const cited = result.references.map((reference, index) =>
  `[${index + 1}] ${reference.document} · chunk ${reference.chunk_index} · knowledge_id: ${reference.knowledge_id}`)
parts.push(`Citations:\n${cited.join('\n')}`)
...
parts.push(`WeKnora session: ${result.session_id} (pass session_id to ask a follow-up in context)`)
```

即：**答案正文 → `Citations:` 编号列表 → `WeKnora tools used: …` → `WeKnora session: <id>`（可续聊）**。引用条目被截到 `config.maxResults` 条（`tools.ts:543`），每条内容按 `maxChunkChars` 截断（`:547`）。空答案不返回空串，而是 `WeKnora returned an empty answer. Retry with a more specific question, or retrieve passages instead.`（`:505-507`）。

### 5.4 分页与截断都要"说出来"

`read_document` 的 render（`tools.ts:401-415`）：开头 `Document <标题> (<id>), passages N of M (page P):`，可选 `Summary: …`（仅第 1 页）、`(content truncated)`、`(more passages available: request page N+1)`。
README 侧的原话（`README_CN.md:106-107`）：

> 片段内容在进入模型前会按 `maxChunkChars` 截断，避免一份超大文档吃掉整个上下文窗口；截断这件事会明确告知模型（`truncated: true`），而不是悄悄丢文本。

### 5.5 图片/资源怎么变成"能显示的东西"

- 发送侧：所有请求都带 `resource_urls=public`（`client.ts:136-143`），除非配置 `handle` 或已被 403 降级。
- 呈现侧：不改写内容——WeKnora 服务端已把片段里的 `resource://` 换成 http(s) 直链，插件只负责**把原文交给模型**，README 教用户「把这些 Markdown 图片写进回复，dsh 网页端就会把图画出来」（`README_CN.md:109-111`）。
- 失败路径：限定知识库的 key 会 403 ⇒ `publicModeBlocked = true` 后**此后一直用 handle**（`client.ts:118`、`:132-134`、`:145-151`），测试 `client.test.mjs:65-73` 断言"后续调用不再重试 public"。
- **没有页码字段**：WeKnora 侧只有 `chunk_index`（`tools.ts:112`、`api-contract.json:90-98`）；`read_document` 的分页是"第几页分块"（`page`/`page_size`），不是 PDF 页码。我们证据 PDF 锚点那套（`evidence_url` 带页码）在这份参考里**没有对应物**。

---

## 6. 与后端的接口

`dsh-weknora/src/client.ts` 是原生 `fetch` 手写的 REST/SSE 客户端（零依赖）。全部线调用被 `test/fixtures/api-contract.json` 钉住，端点集合由 `contract.test.mjs:69-81` 断言为恰好这 8 个：

| 方法 + 路径 | client.ts | 用途 | 请求要点 |
|---|---|---|---|
| `GET /knowledge-bases` | `:196-199` | 列出该凭据可见的知识库 | 也是"无范围时解析全集"的数据源（`tools.ts:169-178`） |
| `POST /knowledge-search` | `:202-215` | 混合（向量+关键词）检索 | body `{query, knowledge_base_ids?, knowledge_ids?}`，空数组**整键省略**（`:210-211`） |
| `GET /knowledge/search` | `:222-231` | 按标题/文件名找文档（跨全租户，无需范围） | query `keyword` + `limit` |
| `GET /knowledge/:id` | `:234-241` | 文档元数据（摘要存在 `description` 里） | `encodeURIComponent(id)` |
| `GET /chunks/:id` | `:244-259` | 一页分块 | query `page` + `page_size` |
| `POST /sessions` | `:262-272` | 建会话拿 `session_id` | body `{title}`；`data.id` 非字符串即抛（`:268-270`） |
| `POST /knowledge-chat/:id` | `:289-290` | RAG 成稿答案 | body `{query, channel:'api', knowledge_base_ids?}` |
| `POST /agent-chat/:id` | `:289-297` | ReAct 成稿答案 | 额外 `agent_id` + `agent_enabled:true`（`:295`），可选 `web_search_enabled`（`:296`） |

### 6.1 鉴权怎么带

`client.ts:122-130`——只在配置存在时才加头，**没有 `Authorization: Bearer`**：

```ts
if (this.config.apiKey !== undefined) headers['X-API-Key'] = this.config.apiKey
if (this.config.tenantId !== undefined) headers['X-Tenant-ID'] = this.config.tenantId
```

README 的承诺（`README_CN.md:103-104`）：「Key 通过 `X-API-Key` 发送。… 报错信息只包含 HTTP 状态码和 WeKnora 自己给出的原因，不会带上 Key。」`client.test.mjs:18-23` 断言真的发出 `x-api-key`。

### 6.2 分页

统一信封类型（`client.ts:74-82`）：`{success?, data?, error?, message?, total?, page?, page_size?}`。
`listChunks` 是唯一分页读（`client.ts:252-258`）：`total`/`page`/`pageSize` **缺字段就回退到入参**（`total` 回退成 `chunks.length`），所以后端不返回信封也不会得到 `undefined`（DSH 的 lossless 校验会拒 `undefined`）。

### 6.3 错误码怎么处理

- 非 2xx ⇒ `WeknoraApiError(msg, response.status)`（`client.ts:185-187`）；非 JSON body 也抛（`:188-192`）。
- 服务端原因提取 `reasonOf`（`:91-101`）：`error` 是字符串 → 用它；`error.message` → 用它；`message` → 用它；都失败（例如代理返回 HTML）→ 300 字截断的原文（`:85-88, 100`）。**没有把 body 整页塞进错误消息**。
- 传输失败 ⇒ `describeTransportFailure`（`:331-337`）把 `AbortError` 分成两种人话：`callerSignal.aborted ? 'the call was cancelled' : 'the request timed out'`；`TimeoutError` ⇒ `'the request timed out'`。
- 测试钉住的错误行为：401 带状态与原因（`client.test.mjs:25-33`）、404 变失败调用（`tools.test.mjs:246-252`）、SSE `error` 事件变失败（`client.test.mjs:111-117`）、**流没收到 `complete` 就变失败**（`client.test.mjs:121-130`）。

### 6.4 SSE 处理（`client.ts:354-433`）

手写按行解析 `data:` 前缀（`consumeLine`，`:369-401`），`response_type` 只认五种，且五种都被 fixture 声明（`api-contract.json:118`、`contract_test.go:226-245` 核常量拼写）：`answer` / `references` / `tool_call` / `error` / `complete`。

```ts
case 'error':
  throw new WeknoraApiError(`POST ${path} streamed an error: ${event.content ?? 'unknown error'}`)   // :393-394
```

**流完整性当硬条件**（`:424-430`）：注释「WeKnora ends every answer with a `complete` event. Without it the stream was cut short, and handing the model the partial text would present a truncated answer as a whole one.」——没 `complete` 就抛，并报出已收到的字符数。

### 6.5 超时/取消的合并写法（`client.ts:103-110`）

```ts
function deadline(signal: AbortSignal, timeoutMs: number): AbortSignal {
  return AbortSignal.any([signal, AbortSignal.timeout(timeoutMs)])
}
```

调用方取消与本次截止**同时生效**，两者在 `describeTransportFailure` 里被区分成人话（§6.3）。

---

## 7. 测试与契约

### 7.1 测试布局与"测产物"

- `package.json:53`：`npm test` = **先 `npm run build`**，再 `node --test "test/*.test.mjs"`。
- 四个测试文件一律 `import ... from '../dist/…js'`（如 `config.test.mjs:4`、`tools.test.mjs:4-6`）⇒ **测的是发布物本身**，不是 src。
- `npm run e2e` 单独一条（`package.json:54`）。

### 7.2 `test/config.test.mjs`（53 行）钉住的行为

| 测试 | 行 | 钉住什么 |
|---|---|---|
| base URL 归一化 | `:6-11` | 裸域 / 带尾斜杠 → 补 `/api/v1`；`/api/v2/` → 保留 v2 |
| 空配置 = 文档默认值 | `:13-21` | `baseUrl` / `maxResults=8` / `toolPrefix=weknora` / `resourceUrls=public` / 四个开关全 true |
| `handle` 是显式退出 | `:23-25` | 显式给 `handle` 不被默认值覆盖 |
| 坏行在**加载期**失败且列全违规 | `:27-39` | 4 个坏值 → 4 条文案同时出现 |
| 全关工具被拒 | `:41-46` | `at least one tool must stay enabled` |
| 空白坍缩 | `:48-53` | `'   '`、`''` → `undefined` |

### 7.3 `test/tools.test.mjs`（361 行）钉住的行为

**最值得抄的一条**是它的 `call()` 助手（`:23-32`）：把"工具注册表会做的事"在测试里复现成一条流水线——

```js
const value = await tool.execute(args, exec)
assertLosslessJson(value, tool.name)                                  // :26 规范值必须是 lossless JSON
const violations = validate(tool.output.schema, value)                // :27 必须满足自己声明的 output.schema
assert.deepEqual(violations, [], `${tool.name} returned a value its output schema rejects`)
const content = tool.output.render(args, value)                       // :29 render 必须能吃这个值
assert.ok(Array.isArray(content) && content.length > 0 && content[0].type === 'text')
```

其余契约：所有 schema 落在 harness 支持子集内 + 工具名匹配 + 描述 >40 字符（`:34-42`）；默认组合恰好四个工具（`:44-52`）；`max_results` 与配置上限（`:71-77`）；空结果文案（`:85-90`）；缺 query 时**在碰网络之前**拒绝（`:92-95`）；无范围时扇出到全部可见库（`:100-107`）；宽范围只报数量（`:111-117`）；全集只解析一次（`:119-125`）；按名命中不越范围（`:156-160`）；长片段截断并标记（`:169-175`）；分页（`:177-194`）；元数据调用失败仍给正文（`:211-218`）；`apply` 的注册/前缀/开关（`:319-333`）；非法配置在加载期抛（`:335-338`）。**`apply` 是用假 ctx 测的**——`{ tools: { register(d){…; return disposer} } }`（`:322-330`），不启真宿主。

### 7.4 `test/helpers/json-schema.mjs`（147 行）：自制校验器三件套

| 导出 | 行 | 作用 |
|---|---|---|
| `assertSupportedSchema(schema, path)` | `:16-38` | 白名单 `SUPPORTED_KEYS`（`:8-11`：type/oneOf/properties/required/additionalProperties/items/enum/const/description/title/default/examples）+ 类型白名单（`:13`）+ **"`required` 里的属性必须出现在 `properties` 里"**（`:27-31`）。注释 `:1-6` 说是照 `packages/core/tools/src/json-schema.ts` 的子集写的 |
| `validate(schema, value)` | `:41-118` | 返回**所有**违规（空数组 = 通过），支持 `const`/`enum`/`oneOf`/`additionalProperties:false`/integer-vs-number 区分 |
| `assertLosslessJson(value, label)` | `:121-142` | 拒绝 `undefined` / `NaN` / `Infinity` / 循环引用；注释 `:120`：「as the registry requires」 |

### 7.5 `contract/`：两侧夹逼（这份设计最完整）

**fixture** `test/fixtures/api-contract.json`（119 行）是三合一清单：
`calls[]`（每次线调用的 `tool`/`method`/`path`/`query`/`body`/`goRequestType`，`:8-88`）+ `responseFieldsRead{}`（读到的响应字段，逐 Go 类型，`:89-117`）+ `streamResponseTypes[]`（`:118`）。

**JS 侧** `test/contract.test.mjs`（136 行）：先在 mock 上把四个工具真跑一遍并记录全部出网请求（`:24-49`），然后
- `:56-67` 断言"**恰好**等于 fixture"（两边都按 `method path query body` 序列化后排序比较，注释 `:53` 说明为什么排序：一个工具会并发发两个请求，顺序不定）；
- `:69-81` 断言端点集合恰好是那 8 条；
- `:83-100` 断言五个 SSE 事件名都在 fixture 里；
- `:102-135` 拿"**只保留 fixture 声明字段**"的样本回放，证明插件不多依赖任何字段——注释 `:106-108`：「A backend that serves nothing but the declared fields must still produce a complete tool result, which is what "these are the fields we depend on" means.」

**Go 侧** `contract/contract_test.go`（245 行）在 WeKnora 服务端里读**同一份 fixture**：
- `:75-95` 用 `decoder.DisallowUnknownFields()` 把每个 body 解进**真 handler 请求结构体**（`session.SearchKnowledgeRequest` 等，`:56-71`）⇒ 服务端删/改字段名就红；
- `:100-119` 校验检索请求必带非空 `query` **且**必须指定范围（否则 handler 400）；
- `:124-154` 校验 RAG 与 agent 两条路由都在 fixture 里、`channel` 必须是 `"api"`、给了 `agent_id` 就必须 `agent_enabled=true`；
- `:159-222` 把真 `types.SearchResult` / `types.Knowledge` / `types.Chunk` / `types.StreamResponse` marshal 成 JSON，核每个读到的字段名还在；
- `:226-245` 核 SSE 事件名与服务端常量拼写一致。

注释定调（`contract_test.go:6-9`）：「Together the two sides catch a rename on either side at CI time instead of inside a user's agent.」

### 7.6 `test/e2e/run-in-dsh.mjs`（270 行）：真 dsh 里跑

流程：`dsh plugin add <本地目录>` 装进临时 profile（`:210-219`，并断言包名进了 `manifest.dsh.profile.bundles`）→ `--dump-config` 断言**组合树确实挂了插件**（`:132-134`，`assert.match(dump.stdout, /name: ["']?@wxg-prc-cpg\/dsh-weknora/)`）→ headless 起一轮（`:138`），断言四件事：
1. **模型被 offer 到哪些工具**（`:143-147`，从假模型记录的 `offeredTools` 里取，四个后缀一个不少）；
2. WeKnora 真收到哪些路径（`:149-168`，无范围场景还断言"先列库、后检索"的**顺序**，`:157-161`）；
3. 每个请求都带配置的 key（`:170-174`）；
4. **工具返回的原文确实进了模型上下文**（`:176-179`，断言 `toolResults` 含 `vector_threshold 是 0.5`，且最终 stdout 含 `0.5`）。

配套 `test/e2e/fake-model.mjs`（141 行）是一个**确定性的 OpenAI 兼容假模型**：`llm-pi-ai` 适配器把它当普通 `openai-completions` 网关（`:1-10` 注释），脚本化策略"先 search → 拿 `knowledge_id` 再 read_document → 只用工具返回的内容作答"（`:112-128`），并记录每次请求的 `offeredTools`（`:95`）。三个场景分别覆盖：A 出厂 patch 仅靠环境变量 / B profile 覆盖并改前缀 / C 无范围由插件自解析（`:9-15`、`:221-259`）。

---

## 8. `README_CN.md` 承诺了什么（原文摘录）

**定位与边界（`:7-11`）**

> 一个 [DeepSeek Harness](…)（`dsh`）插件，让 harness 里的 Agent 直接用上 [WeKnora](…) 知识库：混合检索、按文档通读、以及 WeKnora 自己带引用的成稿答案。
>
> dsh 本身没有任何检索、向量或知识库能力——它的 `grep`、`glob` 只看工作区文件，`web_search` 只看互联网。这个插件把缺的这一块换成你自己的文档。

**安装方式（`:15-21`）**

> ```sh
> # 从 npm 安装（推荐：装到的是构建产物，用户无需授权执行构建脚本）
> dsh plugin --profile web add @wxg-prc-cpg/dsh-weknora
>
> # 或者从本仓库的检出目录安装
> dsh plugin --profile web add ./packages/dsh-weknora
> ```

**环境变量起步（`:23-31`）**：`WEKNORA_BASE_URL` / `WEKNORA_API_KEY`（「需要 `retrieve` 能力（用 ask 还需要 `chat`）」）/ `WEKNORA_KNOWLEDGE_BASE_IDS` / `WEKNORA_RESOURCE_URLS`，然后 `dsh web`。

**覆盖配置与加载期失败（`:33`、`:56-57`）** —— 配置示例见 `:35-54`（逐字段注释，含 `toolPrefix: weknora    # 重命名工具，例如同时挂两个部署时`）：

> patch 是整块替换该行的 `config`，所以要保留的字段需要一并写出。配置不合法会在插件加载阶段失败，并逐条列出问题，而不是等到模型第一次调用工具时才报错。

**双部署（`:59-69`）**：两行 `insert` + 两个 `toolPrefix`（`internal_kb` / `public_kb`）。

**工具表（`:73-78`）**：四行，逐行给出「工具 → WeKnora 接口 → 模型拿到什么」（接口列与本报告 §6 一一对应）。

**能力边界 / 取舍（`:84-90`）**

> 范围不需要配置。没有指定知识库的调用，检索接口会直接拒绝，RAG 接口则会在什么都没检索到的情况下作答，因此当 `knowledgeBaseIds` 为空时，插件会自己解析出该凭据可见的全部知识库并一并使用；这份清单每个进程只解析一次，且由 `weknora_search` 与 `weknora_ask` 共用。让模型先去挑反而更糟：知识库的命名往往糟糕到无从选择。
>
> `weknora_ask` 把整个问题委派给 WeKnora。它适合跨多篇文档、需要综合的宽泛问题…它在服务端再跑一个模型，所以慢，而且返回的是结论而非支撑结论的证据。配了 `agentId` 时它不会自己填范围…

**权限与数据流（`:100-104`）**

> 插件只读。它不会写 WeKnora：不入库、不改分块、不删除。四个工具里有三个只需要 `retrieve` 能力的 API Key；`weknora_ask` 额外需要 `chat`，因为它要创建会话并流式取回答案。
>
> Key 通过 `X-API-Key` 发送。如果用的是平台级 API Key，还需要配 `tenantId`，它会作为 `X-Tenant-ID` 选择工作空间。报错信息只包含 HTTP 状态码和 WeKnora 自己给出的原因，不会带上 Key。

**截断与图片（`:106-113`）**

> 片段内容在进入模型前会按 `maxChunkChars` 截断…截断这件事会明确告知模型（`truncated: true`），而不是悄悄丢文本。
>
> 默认 `resourceUrls: public` 时，WeKnora 会把片段里的 `resource://` 图改写成可直接加载的 http(s) 直链——把这些 Markdown 图片写进回复，dsh 网页端就会把图画出来。限定知识库的 API Key 拿不到直链（WeKnora 会 403），插件会把这次调用改回 handle 模式，之后也一直用 handle。

**配置表（`:117-130`）**：12 行，与本报告 §2.2 表逐项一致（含 `toolPrefix` 的 `^[a-z][a-z0-9_]*$`、「`tools.*` 全部 `true`，少注册几个工具就少占几分 prompt」）。

**兼容性与版本承诺（`:156-160`）**

> 已针对 dsh `0.1.0-rc.8` 与 WeKnora `0.8.0` 验证。dsh 处于 developer preview 并明确会有破坏性变更；本包因此**没有任何运行时依赖**，交给 `ctx.tools.register()` 的只是一个普通对象，不锁定任何 harness 包版本。如果 harness 的工具定义契约发生变化，请在本仓库提 issue。

**跑测试的前提（`:149-150`）**

> dsh 的会话持久化需要带 zstd 的 Node（≥ 22.15 或 ≥ 24），并且 `PATH` 上要有 pnpm ≥ 10——`dsh plugin add` 通过 pnpm 装进 profile，而它写出的 profile 把设置放在 `pnpm-workspace.yaml` 里。插件自身只要求 Node ≥ 20.11，两者都不需要。

**已知限制**：README_CN **没有"已知限制"专章**。散落的边界是：`ask` 慢且返回结论而非证据（`:88-90`）；按名检索跨全租户、靠 scope 过滤（代码注释 `tools.ts:120-125` + `client.ts:217-221`）；限定库的 key 拿不到直链（`:110-111`）；截断（`:106-107`）。**没有**对它自己不覆盖的场景（写入、分块管理、PDF 页码级引用）开单子。

---

## 我们可以直接抄的（10 条）

> 许可前提（AGENTS.md 已核）：WeKnora 是 MIT，`docs/research/weknora-assessment.md:113-118` 记录的条件是**随附版权与许可声明**。凡直接搬代码（第 2 条最典型），在我们仓库留出处 + 许可证说明，并在文档里逐处记出处。

1. **工具的 `output.schema` + `render` 配对，并把"返回值 ↔ 声明 schema"变成门禁。**
   抄什么：`dsh-weknora/tools.ts:264-306` 的形状（每个工具声明精确 `output.schema`，`additionalProperties:false` + `required` 一个不缺，`render` 只做投影）。
   抄到哪：[plugin/src/index.js](../../../plugin/src/index.js) 六个 `make*Tool` 的 `output` 块——现在 `ks_ping` 是 `{ type:'object', additionalProperties:true }`（[:491-494](../../../plugin/src/index.js#L491-L494)），`materials.js:87`、`collect.js:111` 同类；松散声明等于"什么都不承诺"。
   省掉：模型看到的字段与我们在文档里宣称的字段漂移后，靠人工比对发现。

2. **整块搬 `test/helpers/json-schema.mjs`（147 行，纯 ESM 零依赖）。**
   抄什么：`assertSupportedSchema`（`:16-38`，含"`required` 的属性必须在 `properties` 里"）、`validate`（`:41-118`，返回全部违规）、`assertLosslessJson`（`:121-142`，拒 `undefined`/NaN/循环引用）。
   抄到哪：新建 `plugin/scripts/lib/schema-check.mjs`，在 [plugin/scripts/run-verify-commands.mjs](../../../plugin/scripts/run-verify-commands.mjs) 或各 smoke 里对每个工具跑一遍（参数与输出两处 schema + 真实返回值）。
   省掉：自己写这三件套；以及"工具返回值不满足自己声明的 schema、NaN/undefined 混进规范值"这类只在运行期炸的问题。**这是投入产出比最高的一条。**

3. **`isConcurrencySafe` 的用法：只读工具显式 `() => true`，写工具不声明。**
   抄什么：`tools.ts:196`、`:263`、`:379`（三处都写，`ask` 故意不写）。
   抄到哪：[plugin/src/index.js:1152-1162](../../../plugin/src/index.js#L1152-L1162) 六个 register 的裸对象里（`ks_ping`/`ks_resolve_clause`/`ks_answer`/`ks_effect_report`/`ks_materials` 可并行；`ks_collect` 是写，按官方默认 exclusive 不声明）。
   省掉：一串只读工具调用被串行化成多次往返（当前全部走"未声明 ⇒ exclusive"，见 DSH 检出 `packages/core/tools/src/index.ts:1295-1297`）。

4. **"调用方取消 + 本次截止"合并成一个 signal，并把错误翻成人话。**
   抄什么：`client.ts:108-110` 的 `AbortSignal.any([signal, AbortSignal.timeout(ms)])` 与 `:331-337` 的 `describeTransportFailure`（`'the call was cancelled'` vs `'the request timed out'`）。
   抄到哪：[plugin/src/engine.js:140-250](../../../plugin/src/engine.js#L140-L250) 的 `apiGet`/`apiPost`（现在是自己 `setTimeout` + 手搓 `AbortController`，且调用方取消与超时在错误文案上分不开）。
   省掉：多写一遍计时/清理代码，以及"到底是超时还是用户点了停止"这种排障问题。

5. **线调用 fixture + "只发这些调用"的契约测试。**
   抄什么：`test/fixtures/api-contract.json` 三合一清单（方法/路径/查询/body + 读到的响应字段 + SSE 事件名）+ `contract.test.mjs:56-81` 的回放比对（含"排序去序"这个细节：并发请求顺序不定，`contract.test.mjs:53`）。
   抄到哪：我们仓库新增 `plugin/test/fixtures/ks-api-contract.json` + 一条 `plugin/scripts/` 里的回放测试，钉住引擎 REST 路径与 `/ks/*` 路由的入参形状。
   省掉：引擎或路由改名后要真起引擎跑 smoke 才发现（我们已经因"fixture 写了但不生效"踩过一次，见 [plugin/scripts/smoke-lifecycle.mjs:131](../../../plugin/scripts/smoke-lifecycle.mjs#L131) 的注释）。

6. **"无范围 ⇒ 解析全集、每进程只解一次、多工具共享、失败要能重试"的缓存写法。**
   抄什么：`tools.ts:168-184`（`everyId ??= client.listKnowledgeBases(...)` + `then` 成功缓存 / `catch` 里 `everyId = undefined` 后重抛；`resolveScope` 三档优先级）；测试 `tools.test.mjs:119-125`（只列一次）、`:285-291`（search 与 ask 共用）。
   抄到哪：[plugin/src/engine.js](../../../plugin/src/engine.js) 的会话/预热缓存处（同类语义：冷启动只做一次，但失败不能把缓存永久毒住）。
   省掉：每个工具各自重复一次昂贵解析，或错误地把失败结果缓存住。

7. **错误消息三件套：工具名前缀 + 参数名 + 可行动的下一步。**
   抄什么：`tools.ts:71-77`、`:340-343`（`${toolName}: this WeKnora credential can see no knowledge base, so there is nothing to search. Check the deployment's API key scope.`）+ `client.ts:185-187`（一律 `HTTP <status>: <服务端自己的原因>`）。
   抄到哪：[plugin/src/*.js](../../../plugin/src/) 里的 `throw new Error(...)` 文案（我们已经是这个风格，如 [plugin/src/index.js:503-505](../../../plugin/src/index.js#L503-L505)；补的是"把该改哪个参数/去哪看"写进去"）。
   省掉：模型拿到"失败"却不知道下一步，转而乱试参数。

8. **配置校验的两件小事：一次列全违规 + 空白坍缩成未设置。**
   抄什么：`config.ts:70-75`+`:190`（聚合后一次抛，逐条 `-` 列出）、`:108-116`（`''`/空白/`null` → `undefined`）、`:187-189`（交叉约束"不能全关"）。
   抄到哪：[plugin/src/index.js:1093-1110](../../../plugin/src/index.js#L1093-L1110) 的配置块（现在只抛未知键，缺"5 个键的问题一次说完"和 blank→unset 两步）。
   省掉：部署方修一个键、重启一次、再发现下一个键也错。

9. **e2e 三段式：装进临时 profile → `--dump-config` 断言组合树挂了插件 → 起一轮断言"模型被 offer 到哪些工具 + 工具返回的原文进了模型上下文"。**
   抄什么：`run-in-dsh.mjs:132-147`（`/name: ["']?…/` 匹配组合树 + 从假模型记录里取 `offeredTools`）、`:176-179`（断言工具返回的字节出现在模型上下文与最终回答里）、`fake-model.mjs` 整个确定性假模型（141 行）。
   抄到哪：`plugin/scripts/` 新增一条 e2e（复用我们自己的假模型端点）。
   省掉："装了但没挂上 / 挂了但模型看不见工具 / 看见了但返回值没进上下文"这三类只在用户处暴露的失败。

10. **呈现层的三条纪律：范围只报数量、截断要明说、每条命中带可续查的 id。**
    抄什么：`render.ts:21-25`（`describeScope`：≤3 列 id，>3 只报数量，id 留在规范值里）+ `tools.ts:322-326`（`[N] 文档名 · score · chunk N · knowledge_id:` 形状）+ `tools.ts:411-412`（`(content truncated)` / `(more passages available: request page N+1)`）。
    抄到哪：[plugin/src/index.js](../../../plugin/src/index.js) 的 `ks_answer`/`ks_materials` render，以及 [plugin/src/report.js](../../../plugin/src/report.js)、[plugin/src/inspection.js](../../../plugin/src/inspection.js) 里把范围/id 列表整段塞进文本的地方。
    省掉：context 预算被 id 列表吃掉、模型不知道内容被截断而当成全文。

---

## 不该抄的（5 条）

1. **手写配置校验不能替代严格键检查。** 它不拒未知键（我实测：`baseURL` 拼错静默回落默认值、`tools.serach` 静默忽略，见 §2.4）；照抄等于放弃我们 [plugin/src/index.js:1096-1102](../../../plugin/src/index.js#L1096-L1102) 现有的"拼错即报错"防线，正是 README 自己点名的静默失效。

2. **不要为了"不锁版本"再复刻一份 harness 结构类型。** `harness.ts:1-10` 对它是合理取舍（npm 发布给陌生环境、不能保证宿主版本）；我们是仓外 bundle、宿主版本随部署走，再手写一份 `ToolDefinition` 影子类型只会多一处会漂移的抄本，还会顺手丢掉官方字段（`presentCall`/`presentResult`/`finalizeContent`，见 DSH 检出 `packages/extensions/tool-cordis/src/api-catalog.ts:6709`）——而那恰好是工具结果做界面呈现的口子。

3. **不要抄它的"全部可选、无必填"配置风格。** 它的"必填"靠运行时后果兜（缺 `baseUrl` 有默认、缺 `apiKey` 就是无鉴权），对"连错本地部署也无所谓"的场景够了；我们的 `engineRoot`/`python`/`trustedHosts` 有真实部署后果，值得保留"必须写出来"的形态。

4. **不要抄 `weknora_ask` 那条产品取向。** 它把整个问题委派给服务端另一个模型，README 自陈"慢，而且返回的是结论而非支撑结论的证据"（`README_CN.md:88-90`）；我们做的是取证与可审计依据，结论型工具只能是补充而不是主路径。

5. **不要把它"工具即全部交付面"当成边界结论。** 它的前提是"dsh 本身没有任何检索/向量/知识库能力"（`README_CN.md:10-11`），所以做到工具为止；我们的差异化恰好在客户端（知识库页/PDF 侧栏/证据页），把它的形态当上限会砍掉我们自己那一半。

---

## 我没查到 / 不确定

1. **没跑过它的测试。** `dsh-weknora/` 检出里**没有 `dist/`**（`npm test` 会先 `npm run build`），构造它需要 `npm install` + `tsc`（还会联网）。本报告的测试部分**全部是源码原文阅读**，不是"测试通过"的结论。
2. **唯一实测是 §2.4 的未知键探针**：把 `config.ts` 复制到 `%TEMP%`、用 `node --experimental-strip-types`（Node v26.7.0）运行。WeKnora 树未改动，但它**不是**在它的 `dist` 产物上跑的。
3. **`!!js` 标签的求值语义不确定**：`cordis.patch.yml:10-14` 用 `!!js process.env.X`，我只确认它读环境变量，**没核** loader 侧何时求值、是否沙箱、失败会怎样。
4. **宿主是否会拿 `Config` 做前置校验，不确定。** 它只有 TS `interface`（运行时被擦除），没有导出运行时 schema；我只能断定"`resolveConfig` 本身不拒未知键"，**不能断定**宿主一定没有额外校验。
5. **`isConcurrencySafe` 的实际调度效果未验证。** 我只在 DSH 检出里看到消费点（`packages/core/tools/src/index.ts:1295-1297`、`packages/core/agent-loop/tests/tool-calls.spec.ts`），没在本机跑真宿主确认"真并发"及其上限。
6. **`output.render` 除 `text` 外能否返回别的 block 类型未核。** 它只声明 `TextContentBlock`（`harness.ts:26-29`），我没在 DSH 侧核 `ContentBlock` 全集。
7. **`resource_urls=public` 的服务端改写行为未在真机验证。** 插件侧只负责发这个 query（`client.ts:136-143`），改写发生在 WeKnora 服务端；我看到的"改写"证据只有它的 mock（`tools.test.mjs:340-361` 用 `ARCH_PUBLIC`/`ARCH_HANDLE` 两个常量）。**因此"引用里的图能直接显示"这句话，我只复核到它的 README 承诺与 mock，不是真机证据。**
8. **`README_CN.md` 没有"已知限制"专章**，§8 末尾那份边界清单是我从正文（中英两版）散点归纳的，**可能不全**。
9. **WeKnora 侧没有"页码"级引用**，只有 `chunk_index`；我们证据 PDF 的 `evidence_url` 页码锚点在它这里**找不到可抄的对应实现**。
10. **它没有客户端半边，所以"我们的 client/*.tsx 能否抄它"这个问题没有可抄对象**——这不是不确定项，是结论（§1.3 给了四条证据）。
