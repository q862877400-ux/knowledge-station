/**
 * ks-dsh-plugin — scripts/lib/tool-contract.mjs
 *
 * 第 6 步 §1 的**离线工具契约**：把"宿主注册期 / 取值期会做的事"在普通 node 里
 * 复现成一条可红的流水线（(WK) `test/tools.test.mjs:24-30` 同款姿势）。
 *
 * ## 为什么**不抄** WeKnora 的 141 行自制校验器
 * (WK) `test/helpers/json-schema.mjs` 的文件头自陈是"照 (DSH)
 * `packages/core/tools/src/json-schema.ts` 的子集**手写的抄本**"——抄本会随官方升级
 * 漂移（`NOT-DOING #6`：通用层纯借鉴，有现成的就用现成的）。而 DSH **自己导出了权威版**
 * （(DSH) `packages/core/tools/src/index.ts:84-92`），`plugin/node_modules` 里就有
 * `@deepseek-ai/dsh-tools`，普通 node 直接 import 即可（不需要 tsx、不需要 DSH 检出）。
 * ⇒ 本文件**一行校验逻辑都不自己实现**，只做"调用 + 断言"。
 *
 * ## 宿主侧那三个真实消费点（都在 (DSH) `packages/core/tools/src/index.ts`）
 *   · 注册期 `assertSupportedJsonSchema(output.schema)`（`:1062`）——schema 用了子集外的
 *     关键字 ⇒ 抛错 ⇒ **整个插件挂不上**，而离线静默；
 *   · 取值期 `snapshotToolValue`（lossless 快照）+ `validateJsonSchemaValue`（`:1813-1816`）
 *     ——不符 ⇒ `ToolOutputError`（`INVALID_TOOL_OUTPUT`）⇒ **每次调用都 isError**；
 *   · `render(args, value)` 抛错 ⇒ `projectionError`（`:1819-1823`）⇒ 同样 isError。
 * `checkToolContract(tool, args, value)` 就是这三件事的合体。
 */

import { assertSupportedJsonSchema, validateJsonSchemaValue } from '@deepseek-ai/dsh-tools'

/**
 * Deep scan for `undefined` (DSH tool output is validated losslessly: one `undefined`
 * anywhere fails the whole call as `INVALID_TOOL_OUTPUT`).
 *
 * **搬迁说明（第 6 步 §1）**：本函数原住在 `scripts/smoke-effect-tool.mjs:72-88`，
 * 只服务 `ks_effect_report` 一个工具。契约门禁需要它，所以**搬进本 lib 由两边 import**
 * ——**不许**再抄第二份（抄第二份就是第二个漂移点，见该施工单 §1 风险 5）。
 *
 * @param {unknown} value 待扫描的值
 * @param {string} [path] 诊断路径（递归用）
 * @returns {string|null} 第一个 `undefined` 的路径；没有则 `null`
 */
export function findUndefined(value, path = '$') {
  if (value === undefined) return path
  if (Array.isArray(value)) {
    for (let i = 0; i < value.length; i += 1) {
      const hit = findUndefined(value[i], `${path}[${i}]`)
      if (hit) return hit
    }
    return null
  }
  if (value && typeof value === 'object') {
    for (const [k, v] of Object.entries(value)) {
      const hit = findUndefined(v, `${path}.${k}`)
      if (hit) return hit
    }
  }
  return null
}

/**
 * 跑一遍**官方** validator 并把违规数组原样交回。
 *
 * 为什么单独导出：`smoke-tool-contract.mjs` 的两条**反向对照**（A4 非空转 / A5 根类型错）
 * 必须在同一批值上换一份**故意错**的 schema 再验一次——那两条是"这套门禁不是假绿"的唯一证据。
 * 这里仍只调用官方实现，不自己判。
 *
 * @param {object} schema 受支持的 JSON Schema 子集节点
 * @param {unknown} value 待验值
 * @returns {string[]} 违规数组（空 = 通过）
 */
export function violationsOf(schema, value) {
  assertSupportedJsonSchema(schema)
  return validateJsonSchemaValue(schema, value)
}

/**
 * 一个工具返回值是否满足**它自己声明的** `output.schema` 以及宿主的三条硬约束。
 *
 * 早返回纪律：schema 自己就不合法时，后面的"值满足 schema"**无从谈起**——直接返回
 * `ok:false`，让调用方把整组判红（**不许**把"没验到"当成"没违规"）。
 *
 * @param {object} tool 工具定义（`name` / `output.schema` / `output.render`）
 * @param {unknown} args 本次调用的实参（喂给 `render`）
 * @param {unknown} value `execute` 的返回值
 * @returns {{ok: boolean, checks: Array<{name: string, ok: boolean, detail: string}>}}
 */
export function checkToolContract(tool, args, value) {
  const checks = []
  const add = (name, ok, detail) => { checks.push({ name, ok, detail: detail ?? '' }) }

  try {
    assertSupportedJsonSchema(tool?.output?.schema)
  } catch (error) {
    add('schema is in the supported subset', false, String(error?.message ?? error))
    return { ok: false, checks }
  }
  add('schema is in the supported subset', true)

  const undefinedPath = findUndefined(value)
  add('value has no undefined (lossless)', undefinedPath === null, undefinedPath ?? '')

  const violations = validateJsonSchemaValue(tool.output.schema, value)
  add('value satisfies its own output.schema', violations.length === 0, violations.join('; '))

  let content = null
  let renderError = null
  try {
    content = tool.output.render(args, value)
  } catch (error) {
    renderError = error
  }
  const renderOk = renderError === null && Array.isArray(content)
    && content.length > 0 && content[0]?.type === 'text'
  add('render returns a non-empty text block', renderOk,
    renderError !== null
      ? String(renderError?.message ?? renderError)
      : `${Array.isArray(content) ? content.length : 'n/a'} block(s)`)

  return { ok: checks.every((c) => c.ok), checks }
}
