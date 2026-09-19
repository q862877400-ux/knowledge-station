# 第 6 步施工单 —— 插件侧借鉴 WeKnora 自带 DSH 插件的 6 条

> **这是什么**：[EXECUTION-PLAN.md](../EXECUTION-PLAN.md) 第 6 步（`:18`）的可施工任务书。
> 第 6 步原文：「json-schema 三件套+"返回值满足自己声明 schema" 门禁、`output.schema`+`render` 配对、
> `isConcurrencySafe`、`AbortSignal.any`、fixture 回放、e2e 三段式」；验收：「6 条各有冒烟/用例；
> e2e 在真宿主里断言"插件挂上 + 工具被 offer + 原文进上下文"」。
>
> **本文件是新建的，没有改动任何既有文件。** 未跑 `scripts/run-gates.ps1`、`plugin/scripts/smoke-all.mjs`、pytest。
> 只做了 grep / 读文件 / 有界的 `node --input-type=module -e` 探针（探针结果在下文标 **【实测】**；
> 其余一律标 **【读码】** —— 读码不是"跑过了"）。
>
> **路径口径**（全篇 `文件:行` 都按这三个根，可核）：
>
> | 代号 | 根 |
> |---|---|
> | **我们** | `D:\AI\work space\zcode\`（本仓） |
> | **(DSH)** | `D:\AI\DSH\deepseek-harness\`（官方检出，sha 见 [dsh-official/README.md](dsh-official/README.md) 的 `:4-5` 版本口径行） |
> | **(WK)** | `D:\AI\WeKnora\packages\dsh-weknora\`（WeKnora 自带插件，MIT） |
>
> **上游精读**：[03-dsh-plugin-reference.md](weknora-ui/03-dsh-plugin-reference.md)（575 行）。
> 本施工单**回原文核过**它引的每一处 WK 行号（实测该文行号准确；`Get-Content | Measure-Object -Line`
> 的"行数"会跳过空行，是本施工单第一次数错的原因，已改用 `(Get-Content f).Count`）。

---

## 0. 结论摘要（先看不该做的）

| # | 条目 | 判定 | 一句话理由 |
|---|---|---|---|
| 1 | json-schema 三件套 + 返回值满足自身 schema 门禁 | ✅ **该做，但形态改** | "门禁"宿主**已经自动做了**（(DSH) `packages/core/tools/src/index.ts:1813-1816`）；缺的是**离线可红的测试**+把 6 个 `additionalProperties:true` 收紧。三件套**不抄 WK**——DSH 自己导出了权威版，且我们普通 node 就能 import **【实测】** |
| 2 | `output.schema` + `render` 配对 | ⚠️ **半条不该做** | 配对**已经存在**（我们 6 个工具都有 `output:{schema,render}`）。只剩 render 一侧是 `JSON.stringify` 转储；而最大的工具 `ks_answer` 的价值层白名单**也已存在**（`plugin/src/index.js:851-869`）⇒ 独立成条收益不足，**并入第 1 条** |
| 3 | `isConcurrencySafe` | ✅ **该做** | 官方消费点真实存在且**真的会并行**（(DSH) `packages/core/agent-loop/src/tool-calls.ts:96-97`）；我们 6 个工具**一个都没声明** ⇒ 全走 exclusive。**但必须先处理第 4 条**（见 §4 风险） |
| 4 | `AbortSignal.any` | ❌ **"照抄 AbortSignal.any"不该做**；同节的**真实缺口该做** | DSH 自己在**同位点明确避免** `AbortSignal.any`（(DSH) `.../tools/src/index.ts:1905-1908` 注释："Fuse… **without nesting `AbortSignal.any`**"）。而我们**实测**到两件真缺陷：`combineSignals` **加监听不摘**（added=1 removed=0）、"调用方取消"与"内层超时"**文案完全相同**（都是 `This operation was aborted`） |
| 5 | wire fixture 回放 | ✅ **该做（投入产出比最高）** | 引擎路径有 37 个（`grep` 现数）；我们已有 5 个 `createServer` 假引擎冒烟（`plugin/scripts/smoke-collect-tool.mjs:33` 等）当**回放器**，只缺**fixture 文件**与"恰好这些调用"的断言。前例已因同类问题踩过（`plugin/scripts/smoke-lifecycle.mjs:131`） |
| 6 | e2e 三段式 | ✅ **该做（最贵，排最后）** | 我们**没有任何**脚本起真宿主（`dump-config`/`plugin add` 在 `plugin/scripts/` 里 **0 命中**）。现有两个 `e2e-*.mjs` 是**客户端 CDP 浏览器**测试，且没浏览器就 SKIP（`plugin/scripts/e2e-sidebar-pdf.mjs:33`） |

**一句话**：6 条里 **2 条要改形态（1、2）**、**1 条的处方是错的（4，但同一节有真缺陷）**、
**3 条照做（3、5、6）**。没有哪条是"DSH 已经全自动做了、纯属白做"。

**与 [NOT-DOING.md](../NOT-DOING.md) 的对账**：6 条都不在否决清单里；但 **`NOT-DOING #6`（通用层不许自己手搓）**
直接决定第 1 条的形态——**不许**照抄 WK 的 141 行自制校验器，因为 DSH 有现成的（下 §1）。

**与第 8 步的边界**：`EXECUTION-PLAN.md:20` 第 8 步已单列「`defineTool`（拿回 `presentCall/presentResult`）」。
⇒ **第 6 步的任何一条都不许顺手改成 `defineTool`**。好消息：下面 6 条**都不需要**它——
`output.schema` / `render` / `isConcurrencySafe` 在**裸对象**上就能写（WK 自己就是裸对象，(WK) `src/tools.ts:196,263,379`）。

---

## 1. json-schema 三件套 + "工具返回值必须满足它自己声明的 schema" 门禁

### 他们怎么做的

(WK) `src/tools.ts` 每个工具都声明**精确**的 `output.schema`（4 个工具分别在 `:197-218`、`:264-306`、
`:380-400`、`:476-501`），一律 `additionalProperties:false` + `required` 一个不缺；
`test/tools.test.mjs:23-32` 的 `call()` 助手把"注册表会做的事"在测试里复现成一条流水线：

```js
async function call(tool, args) {                              // (WK) test/tools.test.mjs:24
  const value = await tool.execute(args, exec)                 // :25
  assertLosslessJson(value, tool.name)                         // :26  拒绝 undefined/NaN/循环引用
  const violations = validate(tool.output.schema, value)       // :27
  assert.deepEqual(violations, [], `${tool.name} returned a value its output schema rejects`)  // :28
  const content = tool.output.render(args, value)              // :29  render 必须吃得下这个值
  assert.ok(Array.isArray(content) && content.length > 0 && content[0].type === 'text')         // :30
}
```

三件套本体在 (WK) `test/helpers/json-schema.mjs`（147 行，零依赖 ESM）：
`assertSupportedSchema`(`:16`)、`validate`(`:41`)、`assertLosslessJson`(`:121`)；
其文件头自陈是"照 `packages/core/tools/src/json-schema.ts` 的子集写的"。

### DSH 官方口径

**(a) "返回值必须满足自己声明的 schema" 是宿主自动门禁，不是我们要新加的功能。**

```ts
private createSuccessResult(exec, tool, candidate) {                            // (DSH) packages/core/tools/src/index.ts:1813
  const detached = snapshotToolValue(tool.name, candidate)                      // :1814  先做 lossless 快照
  const violations = validateJsonSchemaValue(tool.output.schema, detached, 'value')  // :1815
  if (violations.length > 0) throw new ToolOutputError(tool.name, violations)    // :1816  → isError
```

- 取值期：`dispatchToolBody` 每次 `await tool.execute(...)` 后都过 `createSuccessResult`（(DSH) `.../index.ts:1569-1570`）。
- 注册期：`register()` 还会 `assertSupportedJsonSchema(output.schema)`（(DSH) `.../index.ts:1062`）
  —— **schema 本身不合法 ⇒ 注册抛错 ⇒ 插件挂不上**。
- `ToolOutputError` 的定义与文案：(DSH) `.../index.ts:523-530`（`INVALID_TOOL_OUTPUT`，
  消息 `tool "<name>" returned invalid output: <violations>`）。
- 官方文档原话：「On success the registry snapshots and validates the body value, freezes it, and invokes the
  pure renderer…」((DSH) `docs/subsystems/tools.md:384`)；「an invalid body or post-policy value throws
  `ToolOutputError` (`INVALID_TOOL_OUTPUT`)」(`docs/subsystems/tools.md:149`)。

**(b) 三件套我们**不需要**抄——DSH 自己导出权威版，而且**普通 node 就能 import**。**

- 导出点：(DSH) `packages/core/tools/src/index.ts:84-92`（`assertSupportedJsonSchema`、`validateJsonSchemaValue`、
  `JsonSchemaError`、`assertObjectJsonSchema`）。
- 函数本体：(DSH) `packages/core/tools/src/json-schema.ts:385`（`assertSupportedJsonSchema`）、`:654`
  （`validateJsonSchemaValue`）。
- **【实测】** 在 `plugin/` 下（cwd = `D:\AI\work space\zcode\plugin`）：
  `node --input-type=module -e "import { assertSupportedJsonSchema, validateJsonSchemaValue } from '@deepseek-ai/dsh-tools'; …"`
  → `imported OK`。即 **`plugin/node_modules/@deepseek-ai/dsh-tools` 存在且可从普通 node 冒烟直接调用**，
  **不需要** `tsx`、**不需要** DSH 检出（与 `plugin/scripts/run-verify-commands.mjs:30-34` 那条 tsx 路不同）。
- **【实测】同一探针测出的子集边界**（写 schema 前必须知道，否则真机会 register 期炸）：

  | 输入 | 结果 |
  |---|---|
  | `{type:'object',additionalProperties:false,properties:{a:{type:'string'}},required:['a']}` vs `{a:'x',b:1}` | **VIOLATION** `"value.b" is not a declared property (additionalProperties: false)` |
  | 同上，值 `{a:undefined}` | **VIOLATION** `missing required property "value.a"` |
  | `{type:['string','null']}` | **schema 被拒**：`unsupported JSON schema: schema.type must be a single type string (type arrays are not supported)`；取值期还会 `THROW unreachable variant in JsonSchemaType: ["string","null"]` |
  | `{oneOf:[{type:'string'},{type:'null'}]}` vs `null` | **ok**（⇒ 可空字段只能用 `oneOf`） |
  | `{enum:['a',null]}` | **schema 被拒**：`schema.enum requires type or oneOf`（裸 enum 不被接受） |
  | `{type:'integer'}` vs `1.5` | **VIOLATION** `"value" must be an integer` |
  | `{type:'object',additionalProperties:false,properties:{a:{type:'string'}}}`（**不写** `additionalProperties`） | **schema 被接受**（裸 JSON Schema 走 `register()` 是"开放 by default"，与作者 DSL 的 `ValueSchemaSpec` 不同，见 `docs/subsystems/tools.md:100,423`） |

### 我们现状

- 6 个工具**都**有 `output`，但**6 个的 schema 完全相同且等于"什么都不承诺"**：

  | 工具 | schema 位置 | 内容 |
  |---|---|---|
  | `ks_effect_report` | `plugin/src/index.js:359-360` | `{ type:'object', additionalProperties: true }` |
  | `ks_ping` | `plugin/src/index.js:488-489` | 同上 |
  | `ks_resolve_clause` | `plugin/src/index.js:554-555` | 同上 |
  | `ks_answer` | `plugin/src/index.js:738-739` | 同上 |
  | `ks_materials` | `plugin/src/materials.js:87-88` | 同上 |
  | `ks_collect` | `plugin/src/collect.js:111-112` | 同上 |

  `additionalProperties:true` ⇒ 宿主那条门禁（上一节 (a)）**永远通过**，等于没门。
- 我们**没有**任何 schema 校验器：`plugin/package.json:73-79` 的依赖只有
  `@deepseek-ai/schemastery` + `pdfjs-dist`（devDep `esbuild`），**没有 zod、没有 ajv**；
  `plugin/scripts/` 里 grep `assertSupportedSchema|validateJsonSchema|additionalProperties` **0 命中**
  （只有 `plugin/src/*.js` 里 schema 字面量本身的命中）。
- 唯一的 lossless 检查是**手写在一条冒烟里**的 `findUndefined`（`plugin/scripts/smoke-effect-tool.mjs:72-88`），
  而且它只被用于 `ks_effect_report` 一个工具。
- 补充事实（决定第 1 条的**真实收益**）：`output.schema` 不只是"给门禁用"——它同时是 **PTC 模式**下
  `tools.<name>(args)` 的返回类型来源（(DSH) `docs/cookbook/adding-a-tool.md:63,65`：
  「the generated `ToolArgsMap` and `ToolOutputMap` derive exact argument and canonical-return types from the
  same schemas」「Design `output.schema` as a useful programmatic API」）。松散声明 ⇒ PTC 侧拿到 `JsonValue`。

### 怎么做

**只改 3 个文件的既有段落 + 新增 1 个脚本。不碰 `defineTool`（第 8 步的事）。**

1. **新增 `plugin/scripts/lib/tool-contract.mjs`**（~40 行），导出
   `checkToolContract(tool, args, value)`：
   - `assertSupportedJsonSchema(tool.output.schema)` —— 直接 import，**不抄** WK 的 `SUPPORTED_KEYS` 白名单；
   - `validateJsonSchemaValue(tool.output.schema, value)` —— 返回违规数组，非空即红；
   - `render` 必须返回非空 `ContentBlock[]` 且首块 `type === 'text'`（对齐 (WK) `tools.test.mjs:30`
     与官方 `render(args,value): ContentBlock[]`，(DSH) `docs/subsystems/tools.md:19`）；
   - lossless：沿用已有的 `findUndefined` 实现（`plugin/scripts/smoke-effect-tool.mjs:72-88`），
     把它搬进本 lib 再由两边 import（**不要**再抄一份).
2. **收紧 6 个 `output.schema`**（上表 6 处）：`additionalProperties:false` + 列全 `properties` + `required`；
   所有 `?? null` 的字段写成 `oneOf:[{type:'<T>'},{type:'null'}]`（**不能**用 `type:[...]`，见上表【实测】）。
   逐字段的形状**从 `execute` 的 `return {...}` 字面量抄**，不要凭印象：
   `plugin/src/index.js:411-467`（effect_report）、`:507-520`（ping）、`:854-869`（answer）、
   `plugin/src/materials.js:106-118,125-139,152-166`（materials 三种 action）、
   `plugin/src/collect.js:196-215`（collect）、`plugin/src/index.js` 的 resolve 段（`500-523` 之外，
   需现场读返回值字面量）。
   ⚠ 六个工具的返回**形状不一致**（`ks_materials` 三种 action 返回三套字段）⇒ 要么用
   `oneOf` 三支，要么把 schema 写成"包括全部可能键、全部 required 放宽为可选"（推荐后者：
   `required` 只留永远存在的 `ok/action`）。
3. **新增 `plugin/scripts/smoke-tool-contract.mjs`**：复用 `smoke-effect-tool.mjs:44-63` 的假 ctx
   （`_services.tools.register` 捕获定义）＋ 该文件已有的假引擎桩（同一模式，`globalThis.fetch` 打桩），
   对 6 个工具各跑 1–3 组 `(args, 桩响应)`，每组 `checkToolContract`。
4. **登记进名单**：`plugin/scripts/smoke-all.mjs:32-59` 的 `SUITES` 数组加一行
   （位置遵循该文件 `:21` 的"最快能发现破坏的排前面"⇒ 紧跟 `'scripts/smoke-effect-tool.mjs'` 之后）。
   `plugin/package.json:7-38` 加一条 `"smoke:tool-contract"`。

**会不会改变运行时行为**：**会，而且是 6 条里唯一有真实回归风险的**。
`assertSupportedJsonSchema` 失败 ⇒ **注册期抛错 ⇒ 整个插件挂不上**（(DSH) `.../index.ts:1062`）；
`schema` 与实现不符 ⇒ **每次调用都 isError**（(DSH) `.../index.ts:1813-1816`）。
⇒ 2 与 3 **必须同一次提交**，且提交前必须真在返回值上跑过 validator。

### 怎么验

`smoke-tool-contract.mjs`（新）断言：

| 断言名 | 断言 | 这条红了说明什么 |
|---|---|---|
| `A1 every output.schema is in the supported subset` | `assertSupportedJsonSchema(tool.output.schema)` 不抛，对 6 个工具逐一 | schema 用了 DSH 不支持的关键字（如 `type:[...]`、裸 `enum`）⇒ 真机**插件整体挂不上**，而离线静默 |
| `A2 <tool> returned a value its own schema accepts` | `validateJsonSchemaValue(...)` 违规数组为空 | schema 与实现漂移（少字段/多字段/类型不符）⇒ 真机**每次调用都 isError**，模型看到 `returned invalid output` |
| `A3 <tool> value has no undefined` | `findUndefined(value) === null` | `?? null` 漏写一处 ⇒ lossless 快照环节失败 |
| `A4 the gate is not vacuous`（**反向对照，最重要**） | 把该工具的 schema **临时换成** `{type:'object',additionalProperties:false,properties:{},required:[]}` 后再跑 A2，断言**必须出现违规** | A2 空转（值里明明有键却没判）⇒ 整个第 1 条是假绿。**没有 A4，A2 可能永远绿** |
| `A5 a wrong root type fails` | 用 `{type:'array'}` 跑一个对象返回值 ⇒ 必须红 | 校验器接反了/被短路 |
| `A6 render returns a non-empty text block` | `render(args, value)` 长度 > 0 且 `[0].type === 'text'` | render 会在真机上抛 ⇒ `projectionError` → isError（(DSH) `.../index.ts:1819-1823`） |

### 风险 / 边界

1. **为了过门禁把返回值裁成空对象/删字段（最危险，必须写进纪律）。**
   后果比不做更坏：模型看不到字段却仍收到 `ok:true`，正是本仓 P1 准确性红线反复打的"静默伪装"。
   ⇒ 纪律：**schema 描述真实形状；形状不符就抛错**。我们**已有**这套模式可直接照抄：
   `plugin/src/materials.js:190-197`（信封缺 data 即抛）、`:208-221`（`expectArray`/`expectObject`）、
   `plugin/src/collect.js:186-195`、`plugin/src/index.js:401-408, 844-849`。
   **禁止**任何形式的 `additionalProperties:true` 回退或 `try{validate}catch{}`。
2. **`required` ⊄ `properties` 会被拒**：WK 的对应检查在 (WK) `test/helpers/json-schema.mjs:27-31`；
   DSH 侧我**只实测了正例**（`required:['a']` + `properties.a` 通过），**反例未测** —— 见 §7 清单第 3 条。
3. **别把 `type` 数组当 nullable**：实测 schema 直接拒，且取值期会 `THROW`（不是返回违规，是**抛**）。
4. **不许照抄 WK 的 `SUPPORTED_KEYS`**：它是"照 DSH 子集写的抄本"，会随 DSH 升级漂移，
   而且 `NOT-DOING #6` 明令通用层纯借鉴（有现成的就用现成的）。
5. **不许把 `assertLosslessJson` 也抄一份**：我们已有 `findUndefined`；抄第二份就是第二个漂移点。

### 依赖顺序

- **第 2 条依赖本条**：render 的输出必须落在本条确定的规范值形状上；本条新增的
  `checkToolContract` 就是第 2 条的判据（(WK) `tools.test.mjs:27-30` 把两件事串在一条流水线里）。
- **第 5 条应在条之前或同时**（见 §5 依赖）：wire fixture 会在本条改动时先红一次，
  挡掉"改 schema 时顺手改坏了出网形状"。
- 与第 3 条**无依赖**（`isConcurrencySafe` 是工具定义上的另一个键）。

---

## 2. `output.schema` + `render` 配对

### 他们怎么做的

配对（WK 的**规范值 → 模型文本**两层分离）：

```ts
// (WK) src/render.ts:21-25  —— 投影，而不是转储
export function describeScope(ids: string[]): string {
  if (ids.length === 0) return '(deployment default)'
  if (ids.length <= 3) return ids.join(', ')
  return `${ids.length} knowledge bases`
}
```

`render.ts:1` 自陈定位：「Pure projections from a tool's canonical value to model-facing text.」；
`render.ts:15-20` 的注释解释为什么只报数量：「spelling out every id on every search costs far more than the
count is worth; the ids stay in the tool's canonical value for anything that needs them.」
测试钉住这件事：(WK) `test/tools.test.mjs:111-117` —— 文本里是 `searched: 4 knowledge bases`
且 `doesNotMatch /kb-a/`，但**规范值里 4 个 id 全在**。
检索命中的呈现形状在 (WK) `src/tools.ts:322-326`（`[rank] 文档名 · score · chunk N · knowledge_id:` + 正文）。

### DSH 官方口径

- **`output` 三件套里 `schema` 与 `render` 都必填**，register 期就检查形状：
  「`throw new TypeError('tool "<name>" must declare output { schema, render, presentationMeta? }')`」
  (DSH) `packages/core/tools/src/index.ts:1057-1061`。
- **渲染物就是模型看到的东西；规范值不进模型**：`createSuccessResult` 把 `render` 的结果当 `content`，
  规范值 `value` 只做 execution-local（(DSH) `.../index.ts:1818-1824`）；
  `docs/subsystems/tools.md:382`：「The canonical `value` is execution-local: the loop persists only `content`,
  `error`, and `meta`」。
- **官方明确要求 render 承担"人话"**：`docs/cookbook/adding-a-tool.md:65`
  「keep human explanation in `output.render`」；`:88`「`output.render` owns model-facing prose」。
- **官方没有**规定 render 必须多短，也没有"必须与 schema 不同"的硬约束 —— 即
  `render = JSON.stringify(value)` **不违规**，只是放弃了这一层。

### 我们现状

- 配对**已存在**：6 个工具都有 `output:{schema, render}`：
  `plugin/src/index.js:359-362`、`:488-491`、`:554-557`、`:738-741`、
  `plugin/src/materials.js:87-90`、`plugin/src/collect.js:111-114`。
- 缺的是 **render 一侧**：6 处**逐字节同款**
  `render: (_args, value) => [{ type: 'text', text: JSON.stringify(value, null, 2) }]`
  （同上述 6 处行）。⇒ 模型看到的是规范值的**两空格缩进 JSON 转储**。
- **但**"规范值 ↔ 模型可见字段"这层分离我们**已经做了**，而且做在最贵的地方：
  `ks_answer` 的价值层已过白名单 `trimVerification`（`plugin/src/index.js:37` import、`:293` 使用）
  与 `trimAnswer`（`:851`，返回值在 `:854-869` 逐字段列出），`trim.js` 共 96 行；
  `plugin/src/index.js:278` 的注释自陈「白名单纪律（与 `trimVerification` 同一条）」。
  ⇒ 对 `ks_answer` 而言，render 即使是 JSON dump，**dump 的也已经是裁剪过的值**。

### 怎么做

**结论：不独立成条，作为第 1 条的第二步（同一次提交或紧接一次提交）。**
真正有收益的只有 2–3 处，按收益排序：

1. `ks_materials`（`plugin/src/materials.js:87-90`）：`materials` action 每行 13 个字段
   （`trimMaterialRow`，`plugin/src/materials.js:26-44`）、`projects` action 每行 3 个，
   数量随项目增长而线性膨胀。**收益最大、风险最小** —— 规范值不动，只把 `render` 换成
   `项目名 (prj_id) · approved N / pending M` 一类的投影（照 (WK) `render.ts:21-25` 的"范围只报数量"纪律）。
2. `ks_effect_report`（`plugin/src/index.js:359-362`）：`trees[].categories` 与
   `red_list.docs[]`（每行 8 字段，`plugin/src/index.js:450-460`）在 JSON 缩进下很占预算。
   不过它已经自带上限（`limit ≤ 20`，`:433`），收益中等。
3. `ks_answer`、`ks_ping`、`ks_resolve_clause`、`ks_collect`：**不动**。前者已裁剪；
   后三者本身就是小对象，改成散文反而丢结构化信息。
4. **纪律**：规范值（`output.schema` 描述的那份）**不许因为 render 而改**——(DSH) `finding
   adding-a-tool.md:88`：「UI-only formatting stays out of the model result」；反过来同理，
   "给模型省钱"不许以删掉规范值里的 id/字段为代价（那会砍掉 `evidence_url` 这类可点锚点）。

**会不会改变运行时行为**：**会，但只改模型看到的文本**（`content`），规范值、落盘事件里的
`content` 字段内容会变（`tool/result` 持久化的是 `content`，`docs/subsystems/tools.md:382`），
UI 卡片不受影响（那走 `presentCall/presentResult`，我们没声明）。**不影响任何既有断言**，
因为现有冒烟断言的是 `execute` 的返回值（规范值），不是 render 的文本
（抽查：`plugin/scripts/smoke-materials-tool.mjs`、`smoke-collect-tool.mjs` 走 `execute`）。

### 怎么验

在第 1 条的 `smoke-tool-contract.mjs` 里加：

| 断言名 | 断言 | 能证伪什么 |
|---|---|---|
| `B1 render is a projection, not the canonical dump` | 对 `ks_materials(projects)` 造 12 个项目，断言 render 文本长度 < 规范值 JSON 长度，且文本**不含**全部 12 个 `prj_` id（照 (WK) `tools.test.mjs:111-117` 的 `doesNotMatch`） | render 没改（还是 dump）⇒ 这条白做 |
| `B2 render still surfaces the count` | 文本里出现 `12`（数量），且规范值里 12 个 id 全在 | 为了缩短把 id 从**规范值**里也删了（比 B1 更坏的错法） |
| `B3 render is total` | 对**空数组**、`null` 字段、缺字段三种值都调用 `render` 不抛 | render 里写了 `value.materials.map` 之类会因空值抛 ⇒ 真机 isError |

### 风险 / 边界

1. **把 render 改成"美化过的 JSON"**（换行/制表）——那是白做，断言 B1 会红。
2. **为了缩短在 render 里删掉规范值字段** —— 直接违反 (DSH) `adding-a-tool.md:88`，
   且会让 `ks_materials` 的 `project_id` 到不了模型，工具就失去存在意义。
3. **顺手把 6 个工具的规范值也重构** —— 超出本条范围；规范值形状是第 1 条 schema 的输入，
   两条同时改会互相掩盖回归。
4. **顺手改成 `defineTool`** —— 属第 8 步，见开头边界。

### 依赖顺序

**必须在第 1 条之后**（schema 先定形状，render 再投影同一份值）。
可与第 1 条**同一次提交**，但断言编号分开（A*/B*），出了问题能一眼看出是哪一侧。

---

## 3. `isConcurrencySafe`

### 他们怎么做的

(WK) `src/tools.ts`：三个**只读**工具显式 `isConcurrencySafe: () => true`
（`:196`、`:263`、`:379`），第 4 个工具 `ask` **故意不声明**（它的 `output:` 在 `:476`，
整段 `:456-551` 里没有这个键）—— 因为 `ask` 会在服务端再跑一个模型、会写会话。

### DSH 官方口径

- **声明位置与语义**（原文）：`isConcurrencySafe?(args): boolean`，
  「Pure synchronous classifier for overlap with sibling tool calls. **Only `true` opts in**; omission,
  exceptions, non-`true` returns, and invalid `defineTool` arguments are exclusive.」
  (DSH) `docs/subsystems/tools.md:61-74`。
- **契约**（同处 `:66-70`）：「Opted-in executions **must not mutate parent-owned state**. Shared state must
  tolerate concurrent dispatch; recorder races are permitted only when they commute or fail closed.」
- **消费点（真实且会并行）**：(DSH) `packages/core/tools/src/index.ts:1293-1302` 的 `executionMode()`
  ——「Only an exact `true` is parallel; unknown, hidden, undeclared, invalid, or throwing classifiers are
  exclusive」；`packages/core/agent-loop/src/tool-calls.ts:96-97`
  「`const mode = ctx.tools.executionMode(first.exec).kind` / `const group = mode === 'parallel' ?
  planned.slice(next) : [first]`」，`:220-221` 在启动过程中**再次分类**。
- **`defineTool` 会替你做一层防护**（我们用裸对象 ⇒ **没有**这层）：
  (DSH) `packages/core/tools/src/schema.ts:610-615`
  「`if (validate(args).length > 0) return false`」——参数非法 ⇒ 强制 exclusive。

### 我们现状

- **6 个工具的 register 调用全是裸对象，一个都没声明 `isConcurrencySafe`**：
  `plugin/src/index.js:1149-1159`（6 次 `ctx.tools.register(...)`）。
  grep `plugin/src/` 的 `isConcurrencySafe` = **0 命中**。
- ⇒ 按 (DSH) `.../index.ts:1295`（`if (!tool?.isConcurrencySafe) return { kind: 'exclusive' }`），
  **我们 6 个工具全部走 exclusive**：模型在同一轮里同时发 `ks_ping` + `ks_resolve_clause` +
  `ks_materials` 时被**串行化**。
- 我们**已有**的并发合并不在工具层，而在引擎管理层：
  `EngineManager.ensureLive`（`plugin/src/engine.js:382-395`）用 `this._spawning` 把并发调用
  **合并成同一段探活/spawn**，注释 `:376-381` 自陈理由是"多工具同轮齐发"——即
  **我们的代码早就假设了会齐发**，只是调度层被 exclusive 挡住了。

### 怎么做

在 `plugin/src/index.js:1149-1159` 的 6 次 `register` 之前，给**工具定义对象**加上
`isConcurrencySafe: () => true`（写在 `makeXxxTool()` 的返回字面量里，与 `timeoutMs` 同级）：

| 工具 | 文件:行（返回字面量） | 加不加 | 依据 |
|---|---|---|---|
| `ks_ping` | `plugin/src/index.js:472-523` | ✅ 加 | 只读：`ensureLive` + `GET /api/v1/health`，不写任何父级状态 |
| `ks_resolve_clause` | `plugin/src/index.js:526-…` | ✅ 加 | 只读 GET；`:559-575` 只做参数拼接与读 chatmode |
| `ks_effect_report` | `plugin/src/index.js:332-470` | ✅ 加 | 只读聚合，`:411-467` 只在**局部**建对象 |
| `ks_answer` | `plugin/src/index.js:662-871` | ⚠️ **加，但见风险 2** | 只读（`POST /api/v1/ks/answer` 是查询语义），但**最慢**（`timeoutMs: 120_000`，`:742`） |
| `ks_materials` | `plugin/src/materials.js:51-169` | ✅ 加 | 只读 GET；`:106-166` 全局部变量 |
| `ks_collect` | `plugin/src/collect.js:69-…` | ❌ **不加** | **写**工具：`:172-184` `POST …/collect` 会让引擎**登记**一条 pending 材料；且 `:45` `const _collectedBySession = new Map()`、`:160-166` 读限额、`:210` 写限额 —— **父级共享可变状态**，正是官方 `docs/subsystems/tools.md:66-68` 点名的"must not mutate parent-owned state" |

**会不会改变运行时行为**：**会，而且是本步唯一"提升吞吐"的改动**——
声明 `true` 后模型同一轮里的多个只读调用会被放进同一个 parallel group
（(DSH) `tool-calls.ts:97`），受 `ctx.agentLoop.config.maxParallelToolCalls` 限流（`tool-calls.ts:148`）。
⇒ 这会让 `EngineManager.ensureLive` 的"并发合并"路径**第一次真正被走到**（见风险 1）。

### 怎么验

| 断言名 | 断言 | 能证伪什么 |
|---|---|---|
| `C1 read-only tools declare concurrency safety` | 从假 ctx 捕获的 6 个定义里，除 `ks_collect` 外 5 个 `typeof t.isConcurrencySafe === 'function' && t.isConcurrencySafe({}) === true` | 漏声明 ⇒ 又回到全串行；或把 `true` 写成恒假 |
| `C2 the write tool stays exclusive` | `ks_collect` 的定义上**没有** `isConcurrencySafe`（`undefined`，不是 `() => false`） | 有人"顺手统一"给写工具也加上 ⇒ 并发登记材料的 TOCTOU |
| `C3 classifier never throws on any args` | 对 `{}` / `null` / 乱类型 `{x:1}` 三种输入调用 classifier，断言不抛且返回 `true` | 官方语义是"throwing classifier ⇒ exclusive"（(DSH) `.../index.ts:1299-1301`），抛错会静默降级成串行（不红但白做） |
| `C4（真宿主，属第 6 条 e2e）` | 在真 `ToolRuntime` 里 `executionMode({name:'ks_ping',arguments:{}})` 返回 `{kind:'parallel'}` | 单测桩与真宿主语义不一致（桩里 `true`、真机因参数校验被降级） |

### 风险 / 边界

1. **`ensureLive` 的信号连坐（必须在本条之前处理，或至少写进提交说明）。**
   `plugin/src/engine.js:387-389`：`if (this._spawning) return this._spawning` —— 并发调用
   **共享同一个 in-flight promise，而这个 promise 是用"第一个调用方"的 signal 造的**
   （`:388` `const run = this._ensureLive(signal)`）。若第一个调用方被取消，
   `_ensureLive` 里的 `/health` 探活会以 abort 结束（`apiGet` 返回 `status:0`），
   而 `:400-432` 把 `probe.status === 200` 失败**一律解释成"没有健康实例"** ⇒ 继续 `spawnEngine(signal)`
   （`:432`），带着已 abort 的 signal。⇒ **声明并行后，"一个工具被取消拖垮同轮其它工具"从罕见变成常态。**
   ⇒ 本条的前置处理（第 4 条一起做）：`ensureLive` 的共享 promise 要么用**内部独立 signal**，
   要么在 `signal.aborted` 时**区分"取消"与"引擎不健康"**（不要落到 spawn 分支）。
2. **`ks_answer` 加不加要单独判断。** 它 `timeoutMs: 120_000`（`plugin/src/index.js:742`），
   且内部有自己的 80s deadline 段（`ks_effect_report` 在 `:371`；`ks_answer` 用 `:807-816` 的 401 自愈）。
   与 `maxParallelToolCalls`（默认值我**未查**，见 §7）叠加会同时占多个引擎请求；
   而引擎是**单进程 FastAPI**（`plugin/src/engine.js:441` 只 spawn 一个 `python -m …`）——
   并行是否真的更快**取决于引擎是否并发处理**，这**不是我们这一侧能断言的**。
   ⇒ 建议：先给 3 个**明确廉价**的（`ks_ping`/`ks_resolve_clause`/`ks_materials`）声明，
   `ks_effect_report`/`ks_answer` 留到有实测数据（e2e 里的墙钟对比）再加。
3. **给写工具加**（`ks_collect`）：直接违反官方契约（`docs/subsystems/tools.md:66-68`），
   且 `_collectedBySession`（`plugin/src/collect.js:45,160-166,210`）的读-改-写不是原子的
   —— 两个并发 `collect` 会**同时通过限额判断**。
4. **以为"加了 `true` 就一定并行"**：`schemas()` 会把 `isConcurrencySafe` 从模型可见面剔除
   （(DSH) `docs/subsystems/tools.md:11`）⇒ 模型不知道，调度器知道；这没错，但别在描述里向模型承诺。

### 依赖顺序

**必须在第 4 条之后**（理由：风险 1）。第 4 条的"取消可分辨 + 不泄漏监听器"是并行化的前提。
与第 1/2 条无依赖；与第 5 条无依赖。

---

## 4. `AbortSignal.any`

### 他们怎么做的

```ts
function deadline(signal: AbortSignal, timeoutMs: number): AbortSignal {   // (WK) src/client.ts:108
  return AbortSignal.any([signal, AbortSignal.timeout(timeoutMs)])         // :109
}
```

配上 `describeTransportFailure`（(WK) `src/client.ts:331-337`）把 abort 翻成两种人话：
`callerSignal.aborted ? 'the call was cancelled' : 'the request timed out'`。

### DSH 官方口径

- 官方**没有**任何"必须用 `AbortSignal.any`"的规定。官方对工具的要求只有：
  「**Honor `exec.signal`.** Cancel in-flight work when it fires.」(DSH) `docs/cookbook/adding-a-tool.md:47`；
  「Async work must observe or forward `exec.signal` and settle only after its owned work reaches quiescence.」
  (DSH) `docs/subsystems/tools.md:32-35`。
- **DSH 自己在同位点明确避开它**：

  ```ts
  /**
   * Fuse caller and wrapper cancellation without nesting `AbortSignal.any`.   // (DSH) packages/core/tools/src/index.ts:1906
   * Keeping the relay dispatch-scoped also removes listeners when work settles. // :1907
   */
  function fuseToolSignals(caller, wrapper) {                                   // :1909
    if (caller === wrapper) return { signal: caller, dispose() {} }              // :1910
    const controller = new AbortController()                                     // :1912
    … caller.addEventListener('abort', abortFromCaller, { once: true })          // :1932
    return { signal: controller.signal, dispose }                                // :1935
  }
  ```

  ⇒ 官方手搓的**理由恰恰是** `AbortSignal.any` 不解决"工作结束时移除监听器"这件事，而
  `dispose` 解决了（`:1914-1919` 的 `removeEventListener`）。
- DSH 也**用**它（别处）：(DSH) `packages/core/agent-loop/src/index.ts:882` `AbortSignal.any([…])`。
  ⇒ 结论是"两种都能用，看要不要显式 dispose"，**不是**"必须换"。

### 我们现状

- `plugin/src/engine.js:116-137` 的 `combineSignals(...signals)` 是自实现的多 signal 合并，
  注释 `:116-117` 给的理由是「**自己实现而不依赖 `AbortSignal.any`（Node 20.3+ 才有），
  保持插件对 DSH 各 Node 版本可用**」。
- **这条理由已经过期**：(DSH) 根 `package.json:9` 写 `"node": "^22.19.0 || >=24.0.0"`；
  本机 **【实测】** `node v26.7.0`，`typeof AbortSignal.any === 'function'`、
  `typeof AbortSignal.timeout === 'function'`。
  （我们自己 `plugin/package.json:45-47` 声明 `"engines": { "node": ">=20" }` —— 那是"插件独立可用"的
  自我声明；真跑它的宿主是 DSH，宿主的下限才是下限。**这句注释该更正，但改它本身不是目的**。）
- **【实测】两个真缺陷**（cwd = `plugin/`）：

  ```
  combineSignals: added=1 removed=0           ← 对假 signal 加监听后从不摘
  CALLER-CANCEL -> status=0 error="This operation was aborted"   ← 调用方 abort
  INNER-TIMEOUT -> status=0 error="This operation was aborted"   ← 我们自己的 setTimeout abort
  ```

  探针原文：`combineSignals(ctrl.signal, fake)`（fake 只实现 `addEventListener`/`removeEventListener` 计数）
  + 两次 `apiGet('http://10.255.255.1', '/x', …)`（一次带 `signal: 已 abort 的 caller`、`timeoutMs: 5000`；
  一次不带 caller signal、`timeoutMs: 200`）。
- 代码根据：`combineSignals`（`plugin/src/engine.js:128-135`）`addEventListener(..., { once: true })`
  但**从不 remove**；`apiGet`（`:140-174`）给自己的 `controller` 摘监听（`:172` `signal.removeEventListener`），
  摘的是"别人加到**我们**身上的"，**不是**"我们加到 caller 身上的"。同一个模式在
  `apiGetBytes`（`:187-224`，摘在 `:222`）与 `apiPost`（`:233-273`，摘在 `:271`）重复三遍。
- 错误文案三条路径都一样：`apiGet` `:162-169`、`apiGetBytes` `:212-219`、`apiPost` `:261-268`
  —— 一律 `error.message`，而 `AbortError` 的 message 就是 `This operation was aborted`。
- **另一件必须知道的事**：**宿主自己已经有一层可分辨的超时**。
  (DSH) `packages/guard/timeout-policy/src/index.ts:41-42`
  「`const message = 'tool call timed out after ${timeoutMs}ms'`」+ `error.info.code = TOOL_TIMEOUT`；
  它是 `tools/execute` 包装器（`:53-77`，`using d = deadline(exec.signal, timeoutMs, TOOL_TIMEOUT)`），
  并在 (DSH) `packages/bundle/base/cordis.patch.yml:387-388` 被 `dsh-base` 挂上。
  我们的 profile 组合了 `@deepseek-ai/dsh-base`（`C:\Users\Zegel\.dsh\profiles\web\package.json`
  的 `dsh.profile.bundles` 第一项），且该 profile 的 `cordis.patch.yml` 里 grep
  `timeout-policy` = **0 命中**（没被 disable）。⇒ **我们工具的 `timeoutMs` 确实生效**，
  且"整个工具超时"这件事**已经**是 `tool call timed out after Nms`（可分辨）。
  剩下的不可分辨只发生在**我们内层的 per-call 超时**（`timeoutMs: 15_000/12_000/120_000` 那些）。

### 怎么做

**拆成"不该做的"和"该做的"两半。**

**4A（不该做）**：**不要**为了"用上 `AbortSignal.any`"去重写 `combineSignals`。
理由见官方口径：DSH 自己在同位点避开它，我们的自实现**功能上没错**（任一 abort 即 abort）。
唯一该做的文字更正是把 `plugin/src/engine.js:116-117` 那句
"不依赖 `AbortSignal.any`（Node 20.3+ 才有）"改成事实（宿主下限 Node 22.19，(DSH) `package.json:9`），
或直接删掉这句过期理由 —— **这是注释更正，不是行为改动**。

**4B（该做）**：把两件**实测到的**真缺陷修掉。

1. **监听器泄漏** → 改成 `dispose` 形态（**照 DSH 自己的 `fuseToolSignals` 写**，
   (DSH) `packages/core/tools/src/index.ts:1909-1936`）：
   `combineSignals` 返回 `{ signal, dispose }` 而不是裸 signal；
   调用点（`plugin/src/index.js:372`、`plugin/src/materials.js:99`、`plugin/src/collect.js:167`）
   用 `try/finally` 调 `dispose()`。
   ⚠ 这是**签名变更**，`combineSignals` 的 3 个调用点必须同时改（grep 确认共 3 处：
   `plugin/src/index.js:372`、`plugin/src/materials.js:99`、`plugin/src/collect.js:167`）。
2. **取消 vs 超时可分辨** → 在 `plugin/src/engine.js` 里加一个
   `describeTransportFailure(error, callerSignal, timedOut)`（名字自定），三条调用路径
   （`:162-169`、`:212-219`、`:261-268`）改用它，文案照 (WK) `src/client.ts:331-337` 的两种人话。
   实现要点：三个函数里各自的 `setTimeout(() => controller.abort(), timeoutMs)`
   （`:147`、`:197`、`:240`）要**记下"这次是我超时的"**（一个局部 boolean），
   否则无法区分（现在两条路都只是 `controller.abort()`，**无 reason**）。
   更省事的等价做法：`controller.abort(new DOMException('timeout','TimeoutError'))` 之类带 reason，
   再由 `error.name` 分流 —— 具体形态在实现时定，但**判据必须来自本函数的局部状态，不能靠 `error.message`**。
3. **（可选，与第 3 条一起）** `ensureLive` 的共享 promise 信号问题（见 §3 风险 1）：
   把 `plugin/src/engine.js:388` 的 `this._ensureLive(signal)` 改成用**内部** signal（`new AbortController()`），
   调用方的取消只影响"等不等结果"，不影响"引擎起不起来"。
   这条**同时修掉** `:400-432` 那个"探活被 abort ⇒ 当成不健康 ⇒ 去 spawn"的误判。

**会不会改变运行时行为**：4A 不改；4B-1 不改（只多摘监听）；**4B-2 会改错误文案**——
`status:0` 的 `error` 字符串会从 `This operation was aborted` 变成
`the call was cancelled` / `the request timed out`；而 `ks_effect_report` 的判据是
`probe.status === 0 && deadline.aborted`（`plugin/src/index.js:391`），**不依赖文案**，所以不受影响。
（需 grep 一遍所有对 `probe.error` 做正则匹配的地方；`plugin/src/index.js:406,442` 只是把 error 拼进消息。）

### 怎么验

新增 `plugin/scripts/smoke-cancel.mjs`（或并入 `smoke-engine-guard.mjs`，后者已经在测 `ensureLive` 的并发合并，
`plugin/scripts/smoke-engine-guard.mjs:14`）：

| 断言名 | 断言 | 能证伪什么 |
|---|---|---|
| `D1 combineSignals removes what it added` | 对假 signal 调 `combineSignals(...)` 后 `dispose()`，断言 `added === removed`（并断言 `dispose` 幂等） | 沿用实测探针：`added=1 removed=0` ⇒ 泄漏仍在 |
| `D2 caller cancel is reported as cancelled` | 调用方 abort ⇒ `error` 文本含 `cancel`（且**不含** `timed out`） | 两条路仍同文案（本条的**核心**判据） |
| `D3 inner deadline is reported as timed out` | `timeoutMs` 到点、调用方未 abort ⇒ `error` 文本含 `timed out`（且不含 `cancel`） | 同上 |
| `D4 a real abort reaches the engine call` | 用打桩 `fetch` 断言传进 `fetch` 的 `signal` 在调用方 abort 后 `aborted === true` | 合并出来的 signal 没接上（改了签名忘了接） |
| `D5 no listener survives a settled call` | 用假 signal 做 3 次完整的 `apiGet` 周期，断言净增监听 = 0 | 只修了 `combineSignals` 但 `apiGet` 的 `finally` 摘错对象 |
| `D6（对照）pre-aborted caller short-circuits` | `signal` 已 abort ⇒ `fetch` **一次都不被调**（或立刻返回 status 0） | 合并逻辑把已 abort 的当"没 abort"（`plugin/src/engine.js:130-133` 的既有分支） |

**能证伪什么（一句话）**：D2+D3 一起把"排障时到底谁取消了"这件事钉住——
它红了就说明我们仍然分不清"用户点了停止"和"引擎太慢"。

### 风险 / 边界

1. **为了"完成任务"把 `combineSignals` 换成 `AbortSignal.any` 一行了事** ——
   这会**绕开** `dispose` 的需求但**回避**了"DSH 自己都不这么做"的证据；更要紧的是它**不解决 D2/D3**
   （`AbortSignal.timeout` 的 abort reason 是 `TimeoutError`，但 `AbortSignal.any` 的合成 signal
   在 caller 先 abort 时 reason 是 caller 的 reason —— 具体分流语义**我未实测**，见 §7 第 8 条）。
   ⇒ 纪律：先写 D2/D3 的**红断言**，改到绿；**不许**先改实现再补断言。
2. **改三处 `setTimeout` 时把 `clearTimeout` 漏掉**（`plugin/src/engine.js:171`、`:221`、`:270` 的 `finally`）
   ⇒ 计时器泄漏 + 进程不退出。
3. **改 `combineSignals` 签名而漏改调用点**：共 3 处
   （`plugin/src/index.js:372`、`plugin/src/materials.js:99`、`plugin/src/collect.js:167`），
   `plugin/src/index.js:29-33` 的 import 也要同步。漏改 ⇒ 把 `{signal}` 对象当 signal 传，
   变成"取消永不生效"的**静默失效**（最坏的一种）。⇒ 断言 D4 就是防它的。
4. **顺手把宿主那层超时也绕掉**：我们内层 `AbortSignal.timeout(80_000)`
   （`plugin/src/index.js:371`）是"比宿主 `timeoutMs` 更早、文案更准"的**有意重叠**，
   `:363-370` 的注释解释了理由（401 自愈最坏 150s > 外层 90s）。**别删它**。
5. **在 4B-3 里给 `ensureLive` 造一个"永不取消"的内部 signal** —— 会让"用户点停止"后
   引擎冷启动（最长 60s，`plugin/src/index.js:115` 的默认值）**继续跑完**。
   这是有意的取舍（否则一次取消会连带杀掉同轮其它调用），但**必须在注释里写明**，
   否则下次复核会当成"取消失效"的 bug。

### 依赖顺序

**第 3 条依赖本条**（并行化会把 `ensureLive` 的信号连坐从罕见变常态）。
本条与第 1/2/5/6 条无依赖。

---

## 5. wire fixture 回放

### 他们怎么做的

(WK) `test/fixtures/api-contract.json`（119 行）是一份**三合一清单**：
`calls[]`（每次线调用的 `tool`/`method`/`path`/`query`/`body`/`goRequestType`）+ `responseFieldsRead{}`
（读到的响应字段）+ `streamResponseTypes[]`（SSE 事件名）。
JS 侧的用法（(WK) `test/contract.test.mjs`）：

```js
/** Order-insensitive key: a tool that fires two calls at once may land either way round. */  // :53
const callKey = call => `${call.method} ${call.path} ${JSON.stringify(call.query)} ${JSON.stringify(call.body)}`  // :54
test('the plugin makes exactly the documented WeKnora calls', () => {   // :56
  const expected = fixture.calls.map(call => ({ method: call.method, path: call.path, query: call.query, body: call.body }))  // :57-62
  assert.deepEqual(observed.map(callKey).sort(), …)                     // :63-…
```

两侧夹逼：Go 侧 `contract/contract_test.go` 读**同一份 fixture**，用
`decoder.DisallowUnknownFields()` 把每个 body 解进真 handler 结构体 ⇒ **任一侧改名都会在 CI 红**
（(WK) `contract/contract_test.go:6-9` 的定调）。

### DSH 官方口径

**未找到**——DSH 官方文档里**没有** wire fixture / 契约回放 / cassette 这一套的规范：
grep `docs/**/*.md` 的 `dump-config`（只有 (DSH) `docs/architecture.md:36`、
`docs/user/develop/basic/publish.md:106`）与 `cassette|record and replay`（**0 命中**）。
⇒ 这条是**我们自建的测试纪律**，不是官方契约，因此**没有"官方口径"可引**，
判据只能来自我们自己的事实（下"我们现状"）。

### 我们现状

- **没有任何 fixture 文件**：`plugin/test/` **不存在**；grep `plugin/scripts/*.mjs` 的 `fixture|contract`
  只命中注释（`plugin/scripts/smoke-lifecycle.mjs:131`、`plugin/scripts/smoke-ingest.mjs:202`、
  `plugin/scripts/smoke-chatmode.mjs:964`），不是文件。
- **但我们已经有"回放器"**：5 个冒烟各自起一个假引擎 HTTP 服务器并接住插件的出网请求：
  `plugin/scripts/smoke-collect-tool.mjs:18,33`、`plugin/scripts/smoke-materials-tool.mjs:18,36`、
  `plugin/scripts/smoke-materials-routes.mjs:27,46`、`plugin/scripts/smoke-report-routes.mjs:21,43`、
  `plugin/scripts/smoke-channels-routes.mjs:13,31`；`smoke-effect-tool.mjs` 用 `globalThis.fetch` 打桩
  （30 处赋值）。⇒ **缺的不是机制，是"把观察到的调用固化下来当契约"这一步。**
- **我们出网面比 WK 大**：`plugin/src/` 里 `/api/v1/...` 路径片段 **37 个**（`grep -o "/api/v1/[A-Za-z0-9_/:{}.\-]*"` 现数，
  含模板串在 `${` 处被截断的片段，例如 `/api/v1/documents/${enc`）⇒ 写 fixture 时**要现数、不要抄这个 37**。
- **我们已经因同类问题踩过一次**：`plugin/scripts/smoke-lifecycle.mjs:131-132`
  「⚠ 先复位模块内存态：状态是**模块级缓存**的，A 段/上一次运行留下的 `_state` 会让这里的
  fixture **完全不生效**（B4 第一版就踩了这个：fixture 写了，`reached=false`）」；
  同一坑在 `plugin/src/inspection.js:965` 又记了一次。
  ⇒ "fixture 写了但不生效"是**本仓的已知复发模式**，这条施工单必须自带防它的断言。

### 怎么做

**新增 2 个文件，不改既有冒烟。**

1. **新增 `plugin/test/fixtures/ks-engine-contract.json`**，形状照 (WK) 的三合一来但按我们的面裁剪：
   ```jsonc
   {
     "calls": [ { "tool": "ks_ping", "method": "GET", "path": "/api/v1/health", "query": null, "body": null } ],
     "responseFieldsRead": { "health": ["status","uptime_seconds","db_status","vector_engine","parser_worker"] },
     "envelopes": ["{code,status,data}", "flat"]
   }
   ```
   `calls[]` 的**唯一来源**：`plugin/src/index.js` / `materials.js` / `collect.js` / `engine.js` 里
   那些 `apiGet(...)/apiPost(...)` 的实参 —— 写的时候逐个 grep 定位（`grep -n "apiGet(\|apiPost(\|apiGetBytes(" plugin/src`），
   **不许**从 37 那个数字反推。
   建议**只收"模型工具会发的调用"**（`ks_ping`/`ks_resolve_clause`/`ks_answer`/`ks_effect_report`/
   `ks_materials`/`ks_collect` 六条链上的端点），把 `/ks/*` **宿主路由**（给浏览器用的那批）留给
   `plugin/scripts/smoke-*-routes.mjs` 现有的断言 —— 一次收全 37 个会把 fixture 变成文档而不是契约。
2. **新增 `plugin/scripts/smoke-wire-contract.mjs`**（照 `plugin/scripts/smoke-materials-tool.mjs`
   的 `createServer` 写法起假引擎，`:33`），跑一遍 6 个工具的 `execute`，
   把假服务器收到的**每次**请求记成 `{tool, method, path, query, body}`，然后：
   - 断言 `observed.map(callKey).sort()` **恰好等于** fixture（照 (WK) `contract.test.mjs:53-63` 的排序理由：
     并发请求顺序不定；**这条正是第 3 条并行化后的必要保护**）；
   - 断言"**只回 fixture 里声明的字段**"的极简信封回放时，工具仍产出**完整**结果
     （照 (WK) `test/contract.test.mjs:102-108` 的语义 —— 该测试名原文即
     `the plugin only reads response fields the fixture declares`，`:107-108` 的注释是
     "A backend that serves nothing but the declared fields must still produce a complete tool result"；
     我们的对应要求是"信封 `data` 只给声明字段时不出现 `undefined` 字段"）；
   - 断言 fixture 里的每个 `calls[i]` **都被观察到过**（反向：防止 fixture 里留了永不发生的条目，
     即"文档化了的假契约"）。
3. **登记**：`plugin/scripts/smoke-all.mjs:32-59` 的 `SUITES` 加一行（放在 `smoke-effect-tool.mjs` 之后）；
   `plugin/package.json` 加 `"smoke:wire-contract"`。

**会不会改变运行时行为**：**不会**（纯新增测试）。它是第 1/2/3 条的**安全网**。

### 怎么验

| 断言名 | 断言 | 能证伪什么 |
|---|---|---|
| `E1 the plugin makes exactly the documented engine calls` | `observed` 排序后与 fixture 逐条相等 | 有人改了引擎端点/加了新出网调用却没更新 fixture ⇒ 真机才炸 |
| `E2 the fixture is not stale` | fixture 里每条 `calls[i]` 至少在 `observed` 里出现一次 | fixture 是"文档"不是"契约"（写了永不发生的条目，看着很完整） |
| `E3（防复发，最重要）the fixture is actually loaded` | 断言 `fixture.calls.length > 0` **且**假服务器实际收到 > 0 次请求 **且** `observed.length === fixture.calls.length` | 直接命中本仓已知复发模式（`plugin/scripts/smoke-lifecycle.mjs:131` 的"fixture 写了但完全不生效"）：模块缓存/import 路径错 ⇒ 假服务器 0 请求，E1/E2 会**双双空转通过** |
| `E4 minimal envelope replay still yields a complete result` | 假引擎只回 fixture 声明字段 ⇒ `execute` 的返回值通过第 1 条的 `validateJsonSchemaValue` 且无 `undefined` | 我们偷偷依赖了未声明字段（改天引擎少给一个字段 ⇒ 模型看到"没有材料"这类静默伪装） |
| `E5 the write tool's body carries no source_tier` | `ks_collect` 的 `body` **不含** `source_tier` | 回归 `plugin/src/collect.js:170-171` 的纪律（采集者不得自 claim 可信度） |

### 风险 / 边界

1. **fixture 写成"现状的快照"而不是"我们承诺的契约"**：如果生成方式是"跑一遍把观察到的写下来"，
   那么任何错误都会被一起固化。⇒ 纪律：fixture **手写**、每一条都能指到源码行
   （`calls[i].tool` 必须对应一个真实的 `apiGet/apiPost` 实参），冒烟只做**比对**不做**生成**。
2. **把 37 个端点全收**（含 `/ks/*` 宿主路由与客户端调用）⇒ fixture 变成"文档"，
   改一次 UI 就红一次，最后没人看它。
3. **`E3` 不能省**：没有它，`E1`/`E2` 在"假服务器根本没被调用"时会**空转通过**——
   这正是本仓复发过的形态。
4. **顺序敏感**：`E1` 必须排序比较（(WK) `contract.test.mjs:53`）；第 3 条并行化之后
   并发请求顺序**确实不定**，不排序会变成随机红。
5. **别把它接进 `run-gates.ps1` 之外的路径**：它必须走 `smoke-all.mjs`（那个 runner 才拿门禁锁，
   `plugin/scripts/smoke-all.mjs:64-68`）。AGENTS.md 已把"绕过 `run-gates.ps1` 直接跑冒烟"
   记成假红来源。

### 依赖顺序

**建议本条先做**：它是第 1/2/3 条改动的安全网（改 schema / 改 render / 开并行都可能顺手改坏出网形状）。
与其余 5 条**均无前置依赖**。

---

## 6. e2e 三段式

### 他们怎么做的

(WK) `test/e2e/run-in-dsh.mjs`（270 行）+ `test/e2e/fake-model.mjs`（126 行）：

```js
const dump = await run(dsh, ['--profile', 'headless', '--dump-config'], { env })          // :132
assert.equal(dump.code, 0, `--dump-config must succeed:\n${dump.stderr}`)                 // :133
assert.match(dump.stdout, /name: ["']?@wxg-prc-cpg\/dsh-weknora/, 'the composed tree must mount the plugin')  // :134
…
const offered = (model.requests.at(0)?.offeredTools ?? []).filter(name => name.startsWith(`${prefix}_`))  // :143
for (const suffix of ['search','read_document','ask','list_knowledge_bases']) {           // :145
  assert.ok(offered.includes(`${prefix}_${suffix}`), `${prefix}_${suffix} must appear in the model's tool schemas`)  // :146
}
…
const toolResults = model.requests.flatMap(request => request.toolResults).join('\n')      // :176
assert.match(toolResults, /vector_threshold 是 0\.5/, 'the model must see the retrieved passage verbatim')  // :177
```

即三段：**① 组合树挂了插件（`--dump-config`）→ ② 模型被 offer 到哪些工具（假模型记录 `offeredTools`）
→ ③ 工具返回的原文确实进了模型上下文（假模型记录 `toolResults` + 最终 stdout）**。
假模型是确定性的 OpenAI 兼容网关（(WK) `test/e2e/fake-model.mjs:1-10` 自陈"被 llm-pi-ai 适配器
当普通 `openai-completions` 网关"）。

### DSH 官方口径

- `--dump-config` 是官方承认的"不启动就验证组合层"手段：

  > Verify the layer without booting, then boot:
  > ```sh
  > dsh --profile demo --dump-config   # shows a "# == dsh-hello-plugin" layer
  > dsh --profile demo
  > ```

  (DSH) `docs/user/develop/basic/publish.md:103-108`；加载顺序（bundle patch → profile patch →
  `$DSH_HOME/cordis.patch.yml` → `--patch` 覆盖）在同文件 `:110-118`，`docs/architecture.md:19-29,45`。
- headless 一次性运行器是官方 bundle，且**提供机读事件流**：
  「`dsh-headless` runs one dsh task from the command line and prints the final answer, then exits —
  no GUI, no server, no browser. Type `dsh --profile headless "run the tests"`…」
  「It also offers a JSON event stream (`--json`)… Exit code 0 means the task completed; 1 means it
  aborted or errored.」 (DSH) `packages/bundle/headless/README.md:12`；
  `--json` 事件清单在同文件（`session` / `status` / `text` / `thinking` / `tool_call` / `tool_result` / `final`）。
- **"模型被 offer 到哪些工具"官方没有直接的口子** —— 官方只有 `schemas()`（内存投影，
  (DSH) `packages/core/tools/src/index.ts:1251-1253`「Project visible definitions onto the allowlisted
  model-facing schema fields」）。⇒ 要断言"模型真的看到了"，只能像 WK 那样**从请求侧记录**。
- 假的 OpenAI 兼容 provider 的官方接线点：(DSH) `packages/bundle/base/cordis.patch.yml:107-115`
  ——`llm-pi-ai` **"mounted dormant: zero routes (and no extra models in the picker) until a
  `llm-pi-ai:` settings section supplies provider…"**（我**只读了这段注释**，未核 provider 条目的具体字段名，
  见 §7 第 7 条）。

### 我们现状

- **没有任何脚本起过真宿主**：`grep -n "dump-config|plugin add|--dump-config|offeredTools|headless"` 于
  `plugin/scripts/*.mjs` = **0 命中**。
- 现有两个 `e2e-*.mjs` **不是**这一条：
  `plugin/scripts/e2e-sidebar-pdf.mjs`（178 行）与 `plugin/scripts/e2e-materials-panel.mjs`（236 行）
  是 **CDP 驱动浏览器**测客户端半边，且连不上浏览器就 `SKIP` 并以 0 退出
  （`plugin/scripts/e2e-sidebar-pdf.mjs:33` `const skip = (why) => { console.log('SKIP…'); process.exit(0) }`），
  **不进 `npm run smoke`**（两个文件头都写明）。⇒ 名字叫 e2e，其实只覆盖客户端渲染。
- 我们**已有**一条"挂真 DSH 运行时"的先例：`plugin/scripts/verify-commands-real.mjs`（170 行）
  用 `tsx` + DSH 检出，`new Context()` 后 `await ctx.plugin(CommandRuntime)`，
  挂**真实** `ctx.commands` 并断言定义被接受（`:51-69`）；
  包装器 `plugin/scripts/run-verify-commands.mjs:19-34`（cwd 必须是检出根、tsx 必须存在、
  检出不存在就 exit 2），且**已经在 `run-gates.ps1` 的快档里**（`scripts/run-gates.ps1:137`
  `Add-Step 'verify:commands' 'npm' @('run','verify:commands')`）。
- **一个必须知道的事实**：**线上 `web` profile 装的不是我们这个工作区**。
  `C:\Users\Zegel\.dsh\profiles\web\package.json` 的依赖是
  `"ks-dsh-plugin": "link:C:/Users/Zegel/dsh-ks-src/ks-dsh-plugin"`。
  ⇒ **任何"在 web profile 里断言"的 e2e 测的都是另一个目录**；必须像 (WK) `run-in-dsh.mjs:210-219`
  那样 `dsh plugin --profile <临时> add <本地目录>` 装进**临时 profile**，才能测到本仓。
- 引擎是 Python 进程（`plugin/src/engine.js:441` `spawn(this.python, ['-m', MODULE_ARG], …)`）——
  e2e 若真拉起它，就要有真库；若用假引擎，`_ensureLive`（`plugin/src/engine.js:397-413`）
  会**复用**一个 healthy 的外部实例且**永不杀它**（`:407-410` `spawnedByUs=false`）——
  **这是让 e2e 保持离线可行的现成口子**（写一份 `engine.session.json` 指向假服务器即可）。

### 怎么做

**分 6a / 6b 两段，6a 先做（便宜、且能马上红）。**

**6a（无 LLM，离线）——"插件挂上 + 定义被真注册表接受 + 工具会被 offer"**

1. 新增 `plugin/scripts/verify-tools-real.mjs`（**照 `verify-commands-real.mjs` 的骨架**，
   跑法复用 `plugin/scripts/run-verify-commands.mjs` 的 tsx 包装器）：
   - `new Context()` → `await ctx.plugin(ToolRuntime)`（真 `@deepseek-ai/dsh-tools` 注册表）；
   - 走插件**真正的那段**注册代码（把 `plugin/src/index.js:1149-1159` 那段抽成可调用的
     `registerKsTools(ctx, manager, chatModeOf)` 是**最干净的做法**，但**这会改动 `apply`**
     ——若不想动，就按 `smoke-effect-tool.mjs:44-63` 的假 ctx 捕获定义后再手工 `ctx.tools.register(def)`
     喂给真注册表）；
   - 断言 **`register()` 对 6 个定义全部接受**（`assertSupportedJsonSchema` 通过——
     这正是第 1 条 A1 的真宿主复现）；
   - 断言 `ctx.tools.schemas(scope)`（(DSH) `.../index.ts:1251-1253`）里
     **6 个名字一个不少**，且**投影里不含** `output`/`execute`/`timeoutMs`/`isConcurrencySafe`
     （官方允许列表，(DSH) `docs/subsystems/tools.md:11` 明说这些"must never leak into a model request"）；
   - 断言 `ctx.tools.executionMode({name:'ks_ping',arguments:{}})` 返回 `{kind:'parallel'}`
     而 `ks_collect` 返回 `{kind:'exclusive'}`（第 3 条 C4 的真宿主版）。
2. 新增 `plugin/scripts/e2e-install-compose.mjs`（**不需要 tsx**）：在**临时 profile** 里
   `dsh plugin --profile <tmp> add "<本仓 plugin 目录>"`，然后
   `dsh --profile <tmp> --dump-config`，断言 stdout 里有 `ks-dsh-plugin` 的层
   （照 (WK) `run-in-dsh.mjs:132-134` 与 (DSH) `publish.md:106`）。
   收尾必须删临时 profile（`dsh plugin --profile <tmp> remove …`）——**不许碰 `web` profile**。

**6b（带假模型）——"原文进上下文"**

3. 新增 `plugin/test/e2e/fake-model.mjs`（照 (WK) `fake-model.mjs` 的定位：确定性 OpenAI 兼容网关，
   记录每次请求的 `offeredTools` 与 `toolResults`）+ `plugin/scripts/e2e-tool-context.mjs`：
   - 临时 profile 里用 `llm-pi-ai:` settings 段把 provider 指到假模型（接线点见上"官方口径"，
     **具体字段名待核**，见 §7 第 7 条）；
   - 用预置的 `engine.session.json`（`KS_DATA_DIR` 指向临时目录）让插件**复用**一个假引擎
     （`plugin/src/engine.js:397-413`），**不 spawn Python**；
   - `dsh --profile <tmp> headless --json "<一句会让模型调 ks_ping 的任务>"`；
   - 断言三段：① dump-config 挂了插件（同 6a）；② `model.requests[0].offeredTools` 含
     `ks_ping`/`ks_answer`/… 六个（照 (WK) `run-in-dsh.mjs:143-147`）；
     ③ `model.requests.flatMap(r => r.toolResults)` 里含**引擎桩发回的那串独特字节**
     （照 (WK) `run-in-dsh.mjs:176-179`）。
4. 两者都**不放进 `smoke-all.mjs`**（它们需要 DSH 检出/pnpm/临时 profile，属真机依赖——
   与现有两个 CDP e2e 同款定位，`plugin/scripts/e2e-sidebar-pdf.mjs:35-37` 的理由），
   但**要放进 `run-gates.ps1` 的 `-Full` 档**（`scripts/run-gates.ps1:140-141` 那种
   "全量才跑"的段），否则永远没人跑。

**会不会改变运行时行为**：**不会**（纯新增测试与临时 profile）。唯一的"行为"是
`dsh plugin add` 会往**临时** profile 写文件 —— 必须用 `mkdtemp`（照
`plugin/scripts/e2e-materials-panel.mjs` 的隔离口径与 `smoke-effect-tool.mjs:31` 的 `KS_CHATMODE_DIR` 隔离）。

### 怎么验

见上"怎么做"里的四组断言。判据表：

| 断言名 | 断言 | 能证伪什么 |
|---|---|---|
| `F1 the composed tree mounts the plugin` | `--dump-config` stdout 匹配 `ks-dsh-plugin` | "装了但没挂上"（(WK) 这条抓的就是它） |
| `F2 the real registry accepts every definition` | 真 `ToolRuntime.register()` 对 6 个定义全部返回 disposer 且不抛 | A1 的桩测漏掉的注册期语义（例如真注册表的 `assertSupportedJsonSchema` 与桩不一致） |
| `F3 the model-facing projection offers exactly our 6 tools` | `ctx.tools.schemas()` 的 name 集合 ⊇ 6 个；且投影对象**没有** `output`/`execute`/`timeoutMs`/`isConcurrencySafe` 键 | 有人把 `isConcurrencySafe` 或 `output` 混进模型面（官方明令禁止） |
| `F4（真机）the model is offered the tools` | 假模型记录的 `offeredTools` 含 6 个名字（照 (WK) `run-in-dsh.mjs:143-147`） | "挂了但模型看不见工具"（提示段/工具面不一致） |
| `F5（真机）tool output bytes reach the model context` | 假模型记录的 `toolResults` 含假引擎发回的独特字节；且最终 stdout 含其中之一（照 (WK) `:176-179`） | "看见了但返回值没进上下文"——**本仓最贵的一类失败**（工具对了、模型没看到） |
| `F6（反向，防假绿）the task actually called a tool` | headless `--json` 事件流里**至少有一条 `tool_call` + `tool_result`** | 只断言"退出码 0"会被"模型没调工具也退出 0"骗过（**最典型的假绿**） |
| `F7 no write to the实 profile` | 临时 profile 目录被删；`web` profile 的 `package.json` 与 `cordis.patch.yml` mtime/hash 未变 | e2e 污染线上组合 |

### 风险 / 边界

1. **只断言退出码 0**：headless 一次没调工具也会 0。⇒ `F6` 是必须的。
2. **在 `web` profile 里断言**：线上装的是 `link:C:/Users/Zegel/dsh-ks-src/ks-dsh-plugin`
   （`C:\Users\Zegel\.dsh\profiles\web\package.json`），**不是本工作区** ⇒ 会得到
   "改了半天没生效"或"测的是别人"的结论。⇒ 必须临时 profile + `dsh plugin add <本仓目录>`。
3. **e2e 真拉起 Python 引擎**：会把 e2e 变成"需要一个装满国标的真库"的测试，
   在 CI/离线下不可能绿。⇒ 用预置 `engine.session.json` + 假引擎服务器
   （`plugin/src/engine.js:397-413` 的复用分支）。**这条设计我未实跑**，见 §7 第 6 条。
4. **假模型接线写错**：`llm-pi-ai` 是"dormant until a settings section supplies provider"
   （(DSH) `packages/bundle/base/cordis.patch.yml:107-115`）——写错字段名 ⇒ 该路由不存在 ⇒
   headless 直接失败在"没有可用模型"，而不是失败在我们的断言上（**错误信号指错地方**）。
5. **`--json` 输出被 8 KiB 截断**（(DSH) `packages/bundle/headless/README.md` 的机读输出段：
   「every other string and object key is capped at 8 KiB and flagged with `truncated`」）
   ⇒ `F5` 别依赖长字节，用**短的独特串**。
6. **把 6a/6b 塞进 `smoke-all.mjs`**：会让门禁依赖 DSH 检出 + pnpm（AGENTS.md 的"一次只跑一个"
   与提取树复核都会被拖慢/污染）。⇒ 放 `-Full` 段。
7. **临时 profile 没清理** ⇒ `.dsh/profiles/` 下留一堆垃圾，下次有人误读。

### 依赖顺序

**最后做**（最贵；且它的价值是"把前 5 条的结果端到端证明一次"）。
其中 **6a 的第 1 项（`verify-tools-real.mjs`）可以提前**到第 1、3 条之后立刻做——
它就是第 1 条 A1 与第 3 条 C4 的真宿主版。

---

## 7. 执行顺序表（按依赖排序）

| 序 | 做哪条 | 为什么排这里 | 是否改运行时行为 | 阻断关系 |
|---|---|---|---|---|
| 0 | **5 · wire fixture 回放** | 新增测试、零依赖、最便宜；同时是 1/2/3 的安全网 | 否 | 不被任何条阻断 |
| 1 | **1 · schema 收紧 + 契约门禁** | 2 的形状来源；3 无关；PTC 类型受益 | **是**（register 期炸 / 每次调用 isError） | 需要 0 已就位 |
| 2 | **2 · render 投影（并入 1）** | 依赖 1 决定的规范值形状 | 是（只改模型可见文本） | 阻断于 1 |
| 3 | **4B · 取消/超时可分辨 + 不泄漏监听器** | 3 的前提（并行化会放大信号连坐） | 是（`status:0` 的 error 文案变） | 不被阻断；阻断 3 |
| 4 | **3 · `isConcurrencySafe`** | 真实吞吐改动；必须先有 4B | **是**（并行调度） | 阻断于 4B |
| 5 | **6 · e2e 三段式** | 最贵；用来端到端证明 1–5 | 否 | 建议 1/3 完成后先落 6a-① |
| ✂ | **4A · "改写成 `AbortSignal.any`"** | **不做**（DSH 自己避开它）；只做 `plugin/src/engine.js:116-117` 的过期注释更正 | 否 | — |

**可并行的两对**：(0 与 3/4) 无交集；(1 与 4B) 无交集 —— 若只有一个人做，就按上表串行。

**每步的收尾（沿用 `EXECUTION-PLAN.md:6-7` 的纪律，本施工单不替代它）**：
小提交 + `snapshot-project.ps1` + `run-gates.ps1 -Full` 退出码为准 + 独立复核（冻结 tag + 提取树）。
**新增冒烟必须登记进 `plugin/scripts/smoke-all.mjs:32-59` 的 `SUITES`**，不许往 `package.json` 拼 `&&`
（该文件 `:6-23` 给了理由与代价）。

---

## 8. 我不确定、需要先验证的清单

> 每条格式：「**问题** —— 我读的是什么 / 我实测过什么 / **未做**什么」。

1. **`defineTool` 是否支持 `output.schema`，与裸对象有何差异** —— 我读的是
   (DSH) `packages/core/tools/src/schema.ts:545-616`（`defineTool` 包装 `timeoutMs` 校验 `:563-565`、
   `isConcurrencySafe` 软校验 `:610-615`、`render/presentationMeta` 透传 `:573-583`）与
   `docs/subsystems/tools.md:149`。**未实跑**。
   影响：第 6 步**不依赖**它（WK 自己就是裸对象，`(WK) src/tools.ts:196`），
   但第 1 条的"参数校验由谁负责"取决于它 —— 官方口径是
   「Raw JSON-Schema tools registered directly **own their input validation**」
   (DSH) `docs/cookbook/adding-a-tool.md:42` ⇒ 我们**自己**负责（现有手检在
   `plugin/src/index.js:744-745`、`plugin/src/materials.js:95-98`、`plugin/src/collect.js:117-118`）。
2. **`@deepseek-ai/dsh-tools` 在我们普通 node 冒烟里能否稳定导入** —— **【实测】**可以
   （`plugin/node_modules/@deepseek-ai/dsh-tools` 存在，`import { assertSupportedJsonSchema,
   validateJsonSchemaValue }` 成功）。**未核**：AGENTS.md 说的"复核用**真拷贝** `node_modules`"
   的提取树里是否同样存在（若提取树里 `node_modules` 是 junction，esbuild 那次的教训表明
   路径解析会变；但本 import 不经 esbuild，风险较低）。**未核** CI 是否总有该目录。
3. **`required` 里的键不在 `properties` 里，DSH 会不会拒** —— 我实测的是**正例**
   （`required:['a']` + `properties:{a:…}` → `assertSupportedJsonSchema` 接受）。
   **反例未测**；WK 的对应检查在 (WK) `test/helpers/json-schema.mjs:27-31`。
4. **6 个工具的真实返回形状点数** —— 我**只抽样读了** `ks_ping`（`plugin/src/index.js:507-520`）、
   `ks_effect_report`（`:411-467`）、`ks_answer`（`:854-869`）、`ks_materials`（`:106-166`）、
   `ks_collect`（`:196-215` 起）。**`ks_resolve_clause` 的返回值字面量我没读完**（在
   `plugin/src/index.js:580-660` 之间）。
   ⇒ "要写多少个 `oneOf`-null 字段"这个数字**未定**；写施工单时不要引用任何具体个数。
5. **`isConcurrencySafe` 在真宿主里的并行效果与上限** —— 我读的是消费点
   (DSH) `packages/core/tools/src/index.ts:1293-1302` 与
   `packages/core/agent-loop/src/tool-calls.ts:96-97,220-221`、限流参数
   `maxParallelToolCalls`（`tool-calls.ts:148`）。**未实跑**，**未查 `maxParallelToolCalls` 的默认值**。
6. **真宿主 e2e 里"让插件复用假引擎而不 spawn Python"是否真的可行** ——
   我读的是 `plugin/src/engine.js:397-413`（会话文件存在 + `/health` 200 ⇒ 复用，
   `spawnedByUs=false`）与 `:382-395`（并发合并）。**未实跑**；
   也**未核** `engine.session.json` 的确切字段名与校验（`readSessionFile` 的实现我没读）。
7. **假 LLM provider 的确切配置键** —— 我读的是 (DSH) `packages/bundle/base/cordis.patch.yml:107-115`
   的注释（`llm-pi-ai` dormant，等一个 `llm-pi-ai:` **settings** 段提供 provider，含
   `apiKeyEnv` 之类引用）。**未核** provider 条目的字段名（baseUrl / models / 路由名）与
   settings 的落点（`$DSH_HOME/settings.yaml` 还是 profile 内）。
8. **`AbortSignal.any` 合成 signal 的 abort reason 分流语义** —— 我**未实测**：
   caller 先 abort 与 `AbortSignal.timeout` 先到点时，合成 signal 的 `reason` 分别是什么。
   ⇒ 4B-2 的判据**必须来自我们自己的局部状态**（哪个 `setTimeout` 先响），不能只看 `signal.reason`。
9. **`combineSignals` 的监听器泄漏在真会话信号上会不会触发 Node 的
   `MaxListenersExceededWarning`（默认 11）** —— **【实测】**只到"对假 signal 加 1 不摘"这一层；
   **未测**真 `exec.signal` 上的累计与是否告警。⇒ 施工单不写"一定会告警"。
10. **第 6 条 e2e 里"工具被 offer"是否非要用假模型** —— 官方只有 `schemas()`（内存投影，
    (DSH) `.../index.ts:1251-1253`）；**未核** `--json` 事件流里是否有任何"本轮可用工具清单"事件
    （headless README 的事件清单里**没有**）。
    ⇒ 结论：`schemas()` 只能证明"我们会 offer 这些"，**不能**证明"请求体里真的带了"——
    要后者必须假模型。这是我建议 6a/6b 分段的全部理由。
11. **WK 的测试我一条都没跑过** —— (WK) 检出**没有 `dist/`**（`npm test` 先 `npm run build`；
    见 (WK) `package.json:53` 的 `"test": "npm run build && node --test \"test/*.test.mjs\""`，
    以及 `:54` 的 `"e2e"`），构造它要 `npm install` + `tsc` + 联网。
    本施工单引 WK 的部分**全部是源码原文阅读**，行号已逐处回原文核对过。
12. **`plugin/scripts/smoke-ui-scale.mjs` / `ui-audit.mjs` / `ui-render-shot.mjs` / `ui-token-check.mjs`
    是工作区里未跟踪的新文件**（`git status --short` 显示 `??`）—— 若父代理本轮要把新冒烟登记进
    `smoke-all.mjs:32-59`，**注意别与这些并存的未跟踪文件撞名**。

---

## 9. 我认为最容易做错的地方（按危害排序）

1. **为了过 schema 门禁，把返回值裁成空对象 / 丢掉字段 / `try{validate}catch{}` 静默吞。**
   这是唯一会让"做完了"比"不做"更坏的做法：模型拿到 `ok:true` 却看不到证据字段，
   正是本仓 P1 准确性红线（"把读不到伪装成没有"）的翻版。我们**已有**正确的姿势可抄：
   `plugin/src/materials.js:190-197, 208-221`、`plugin/src/collect.js:186-195`、
   `plugin/src/index.js:401-408, 844-849` —— **形状不符就抛错**。
2. **收紧 schema 时漏掉 `oneOf`-null**。`type:['string','null']` 在本机**实测被拒**
   （schema 期 `unsupported JSON schema`、取值期 `THROW`），而我们六个工具里到处是
   `?? null`（例：`plugin/src/index.js:413-420, 450-460, 515-519`）。
   写错的后果不是"少报一个字段"，而是**插件注册期就炸**（(DSH) `.../index.ts:1062`）
   或**每次调用都 isError**（`:1813-1816`）。⇒ 必须与"在返回值上跑 validator"同一次提交。
3. **把 WeKnora 的三件套整块搬过来**（`03-dsh-plugin-reference.md` 的"可抄第 2 条"就是这么建议的）。
   DSH 自己导出了权威版且**普通 node 就能 import**【实测】；
   `NOT-DOING #6`（通用层纯借鉴）与"抄本必然漂移"两条都指向**不抄**。
   这是本仓有过返工记录的模式（HTML 手搓仿真界面、手搓徽章）。
4. **第 4 条照处方做**（把 `combineSignals` 换成 `AbortSignal.any` 了事）。
   处方本身与 DSH 自己的做法相反（(DSH) `.../index.ts:1905-1908` 明说"without nesting
   `AbortSignal.any`"），而且换掉它**不解决**我们实测到的那两个真缺陷。
   ⇒ 症状是"这条做完了、绿灯，但排障时依旧分不清是取消还是超时"。
5. **给 `ks_collect` 也加 `isConcurrencySafe: () => true`**（"统一一下好看"）。
   它是写工具且持父级可变状态（`plugin/src/collect.js:45,160-166,210`），
   直接违反 (DSH) `docs/subsystems/tools.md:66-68`，后果是限额判断的 TOCTOU。
6. **e2e 只断言退出码 0**。headless 一次没调工具也会 0 ⇒ 假绿。必须断言事件流里有
   `tool_call`/`tool_result`（对应 `F6`）。
7. **在 `web` profile 里跑 e2e**。线上 profile 的 `ks-dsh-plugin` 是
   `link:C:/Users/Zegel/dsh-ks-src/ks-dsh-plugin`（另见 §6"我们现状"），
   不是本工作区 ⇒ 会得出"改了没生效"的错误结论，或把别人的代码当成自己的测过。
8. **fixture 用"跑一遍自动生成"**而不是手写。那会把现状的**错误**一起固化成契约；
   而且本仓有过"fixture 写了但完全不生效"的复发坑（`plugin/scripts/smoke-lifecycle.mjs:131`）
   ⇒ 第 5 条的 `E3`（断言 fixture 真被加载、假服务器真收到请求）**不能省**。
9. **顺手改成 `defineTool`**。那是 `EXECUTION_PLAN.md:20` 第 8 步的范围；
   混进来会让第 6 步的改动面从"3 个文件的段落"变成"整个工具层重写"，复核无法冻结区间。
