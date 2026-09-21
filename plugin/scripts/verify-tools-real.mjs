/**
 * verify-tools-real.mjs — 用**真** `@deepseek-ai/dsh-tools` 的 `ToolRuntime` 验证 6 个模型工具。
 *
 * ## 为什么不能只靠 `smoke-tool-contract.mjs`（那套是进程内假 ctx）
 * `smoke-tool-contract` 把 `ctx.tools.register` 换成一个 `Map.set` ⇒ 它**证明不了**
 * 宿主自己的注册期校验（`assertSupportedJsonSchema`，真源
 * `packages/core/tools/src/index.ts:1062`）会不会收下我们的定义。那条校验失败的症状是
 * **整个插件挂不上**（不是这一个工具不可用），而离线侧全静默。
 * 本脚本把真 `ToolRuntime` 挂起来，走真 `register()` / `schemas()` / `executionMode()` /
 * `execute()`，并**把 `output.schema` 原样喂回宿主的输出校验**（同一份 schema，正反两组）。
 *
 * ## 真包从哪来（**不从 `plugin/node_modules` 解析**）
 * 必须先找到 DSH 检出（`$env:KS_DSH_CHECKOUT`，缺省 `D:\AI\DSH\deepseek-harness`）——
 * 找不到**判红并明说**，不许静默退回本仓那份 peer 副本（与 `scripts/run-gates.ps1:154-168`
 * 的"命令不存在 ⇒ 判失败不是跳过"同一立论）。解析顺序：
 *   1. `<检出>/packages/core/tools/package.json` 的 `exports['.']` 指向的构建产物；
 *   2. 兜底 `<检出>/packages/core/tools/lib/index.js`。
 * 两条都不存在 ⇒ 红（说明检出没构建）。
 *
 * ## 断言（每条都打实测数字）
 *   A1 真包可解析且导出 `ToolRuntime`（打印检出路径 + 该包 version + 解析到的入口文件）
 *   A2 6/6 工具过宿主自己的 `register()`（用插件**真工厂**造定义，不手抄 schema）
 *   A3 `schemas()` 投影**正好**这 6 个名字（不多不少）
 *   A4 投影里**没有** `output / execute / timeoutMs / isConcurrencySafe`（非 wire 字段）
 *   A5 `executionMode`：ks_ping → parallel；ks_collect → exclusive（其余 4 个也打印实测值）
 *   A6 真 `execute('ks_ping')` 走通：`isError:false` 且值满足 `output.schema`
 *   A7 反向对照：同一份 schema 喂一个违反 `additionalProperties:false` 的值 ⇒ **必须违规**；
 *      根类型写错 ⇒ 必须违规（证明 A6 的"满足"不是空转）
 *
 * 跑法：`node plugin/scripts/verify-tools-real.mjs`（退出码 0 = 全通过；工作目录不限）
 */

import { existsSync, readFileSync } from 'node:fs'
import { mkdtemp } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

const REPO = resolve(import.meta.dirname, '..', '..')
const CHECKOUT = process.env.KS_DSH_CHECKOUT || 'D:\\AI\\DSH\\deepseek-harness'
const TOOLS_DIR = join(CHECKOUT, 'packages', 'core', 'tools')
const EXPECTED = ['ks_ping', 'ks_resolve_clause', 'ks_answer', 'ks_effect_report',
  'ks_materials', 'ks_collect']
/** 派生的非 wire 字段：`schemas()` 是**白名单**投影，这几个键一个都不许出现。 */
const HOST_ONLY_FIELDS = ['output', 'execute', 'timeoutMs', 'isConcurrencySafe']

const results = []
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}
function fatal(message) {
  console.error(`\n[fatal] ${message}`)
  process.exit(1)
}

/**
 * 从检出解析一个 `@deepseek-ai/*` 包的**构建产物**入口。
 *
 * ⚠ 为什么不用裸包名 import：本脚本的工作目录是**本仓**（`D:\AI\work space\zcode`），
 * 那里解析不到 `@deepseek-ai/*`（本仓根 node_modules 没装 DSH），而 `plugin/node_modules`
 * 里那份是**本仓自己的 peer 副本**——用真检出的那份才是这条门禁的意义。
 * 检出根也没有把这些包铺平到 `node_modules/@deepseek-ai`（pnpm 布局），所以走
 * `<检出>/packages/.../package.json` 的 `exports['.']` 逐个解析。
 * @param {string} pkgDir 相对检出根的包目录（如 `packages/core/tools`）
 * @param {string} label 报错时显示的名字
 * @returns {{ manifest: object, entry: string, candidates: string[] }}
 */
function resolveCheckoutPackage(pkgDir, label) {
  const dir = join(CHECKOUT, pkgDir)
  const manifestPath = join(dir, 'package.json')
  if (!existsSync(manifestPath)) fatal(`检出里没有 ${manifestPath} ⇒ 这个检出不是 DSH 检出？`)
  const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'))
  const entry = manifest?.exports?.['.']?.default ?? manifest?.main
  const candidates = [entry === undefined ? undefined : join(dir, entry),
    join(dir, 'lib', 'index.js')].filter(Boolean)
  const found = candidates.find((p) => existsSync(p))
  if (found === undefined) {
    fatal(`解析不到真包 ${label} 的构建产物（${manifestPath} 的 exports/main 与 lib/index.js 都不存在）`
      + ` ⇒ 这个检出没构建。\n  期望其中之一存在：${candidates.join(' ｜ ')}`)
  }
  return { manifest, entry: found, candidates }
}

/** 从检出解析真 `@deepseek-ai/dsh-tools` 的入口文件（找不到 ⇒ fatal，不退回本仓副本）。 */
function resolveRealTools() {
  if (!existsSync(CHECKOUT)) {
    fatal(`找不到 DSH 检出：${CHECKOUT}\n`
      + '  设 $env:KS_DSH_CHECKOUT 指向检出根，或把检出放到默认路径。\n'
      + '  （"检出不存在" ⇒ 判失败，不是跳过 —— 同 scripts/run-gates.ps1 里"找不到命令"那条。）')
  }
  return resolveCheckoutPackage(join('packages', 'core', 'tools'), '@deepseek-ai/dsh-tools')
}

/* ------------------------------------------------------------------ *
 * 假引擎（与 smoke-tool-contract 同口径：探活即 200 ⇒ 绝不 spawn 真 python）
 * ------------------------------------------------------------------ */

const HEALTH_OK = {
  status: 'healthy', uptime_seconds: 12.5, db_status: 'ok',
  vector_engine: 'unknown', parser_worker: 'ok',
}
let fetchCount = 0
globalThis.fetch = async (url) => {
  fetchCount += 1
  const path = String(url).replace(/^https?:\/\/[^/]+/, '')
  const body = path.startsWith('/api/v1/health') ? HEALTH_OK : { code: 200, status: 'success', data: {} }
  return { status: 200, ok: true, text: async () => JSON.stringify(body) }
}

async function main() {
  console.log('=== 真 @deepseek-ai/dsh-tools ToolRuntime × 6 个模型工具 ===\n')

  /* ------------------------------ A1 真包可解析 ------------------------------ */
  const real = resolveRealTools()
  const mod = await import(pathToFileURL(real.entry).href)
  const ToolRuntime = mod.default ?? mod.ToolRuntime
  check('A1 真 @deepseek-ai/dsh-tools 可解析且导出 ToolRuntime',
    typeof ToolRuntime === 'function' && mod.ToolRuntime === ToolRuntime,
    `checkout=${CHECKOUT} version=${real.manifest.version} entry=${real.entry}`)

  const { Context } = await import(pathToFileURL(resolveCheckoutPackage('vendor/cordis', '@deepseek-ai/cordis').entry).href)
  const SystemPrompt = (await import(pathToFileURL(
    resolveCheckoutPackage('packages/core/system-prompt', '@deepseek-ai/dsh-system-prompt').entry).href)).default
  const { ToolCallId } = await import(pathToFileURL(
    resolveCheckoutPackage('packages/llm/llm', '@deepseek-ai/dsh-llm').entry).href)
  const { validateJsonSchemaValue } = mod

  /* 状态隔离：`KS_DATA_DIR` 指向临时目录（代码树零运行产物）。 */
  process.env.KS_DATA_DIR = await mkdtemp(join(tmpdir(), 'ks-verify-tools-real-'))
  process.env.KS_CHATMODE_DIR = await mkdtemp(join(tmpdir(), 'ks-verify-tools-real-chatmode-'))

  const { makePingTool, makeResolveTool, makeAnswerTool, makeEffectReportTool } =
    await import(pathToFileURL(join(REPO, 'plugin', 'src', 'index.js')).href)
  const { makeMaterialsTool } = await import(pathToFileURL(join(REPO, 'plugin', 'src', 'materials.js')).href)
  const { makeCollectTool } = await import(pathToFileURL(join(REPO, 'plugin', 'src', 'collect.js')).href)

  /* 假 manager：`ensureLive()` 回来的会话满足 `parseSession` 的形状（pid 用本进程即可，
     复用路径不查进程存活 —— (engine.js) `_ensureLive`）。 */
  const session = { port: 45_777, pid: process.pid, token: 'tok_verify_tools_real', spawnedByUs: false }
  const manager = { ensureLive: async () => session }
  const chatModeOf = () => ({})

  const tools = [
    makePingTool(manager),
    makeResolveTool(manager, chatModeOf),
    makeAnswerTool(manager, chatModeOf),
    makeEffectReportTool(manager),
    makeMaterialsTool(manager),
    makeCollectTool(manager, chatModeOf),
  ]

  /* -------------------------------- A2 6/6 注册 -------------------------------- */
  const ctx = new Context()
  await ctx.plugin(SystemPrompt)
  await ctx.plugin(ToolRuntime)
  const registered = []
  for (const tool of tools) {
    try {
      ctx.tools.register(tool)
      registered.push(tool.name)
    } catch (error) {
      check(`A2 register('${tool.name}') 被宿主接受`, false, String(error?.message ?? error))
    }
  }
  check('A2 6/6 个工具都过了宿主自己的 register()（含 assertSupportedJsonSchema）',
    registered.length === EXPECTED.length,
    `${registered.length}/${EXPECTED.length}：${registered.join(',') || '(none)'}`)

  /* ------------------------------ A3 投影正好 6 个 ------------------------------ */
  const schemas = ctx.tools.schemas()
  const names = schemas.map((s) => s.name).sort()
  const extra = names.filter((n) => !EXPECTED.includes(n))
  const missing = EXPECTED.filter((n) => !names.includes(n))
  check('A3 schemas() 投影正好这 6 个名字（不多不少）',
    extra.length === 0 && missing.length === 0,
    `${names.length} 条：${names.join(',')}${extra.length ? ` ｜多出=${extra.join(',')}` : ''}`
      + `${missing.length ? ` ｜缺=${missing.join(',')}` : ''}`)

  /* ---------------------------- A4 不泄漏非 wire 字段 ---------------------------- */
  const leaked = []
  for (const schema of schemas) {
    for (const field of HOST_ONLY_FIELDS) {
      if (field in schema) leaked.push(`${schema.name}.${field}`)
    }
    const keys = Object.keys(schema).sort().join(',')
    if (keys !== 'description,name,parameters') leaked.push(`${schema.name} keys=[${keys}]`)
  }
  check('A4 schemas() 里没有 output/execute/timeoutMs/isConcurrencySafe（白名单投影）',
    leaked.length === 0, leaked.join(' ｜ ') || `每个投影的键恰为 name,description,parameters`)

  /* ------------------------------ A5 executionMode ------------------------------ */
  const modeOf = (name) => JSON.stringify(ctx.tools.executionMode({
    callId: ToolCallId(`mode-${name}`), name, arguments: {},
  }))
  const modes = Object.fromEntries(EXPECTED.map((n) => [n, modeOf(n)]))
  check('A5 executionMode(ks_ping) = parallel（只读探活，isConcurrencySafe 恰为 true）',
    modes.ks_ping === '{"kind":"parallel"}', `${modes.ks_ping}`)
  check('A5 executionMode(ks_collect) = exclusive（写工具故意不声明 classifier）',
    modes.ks_collect === '{"kind":"exclusive"}', `${modes.ks_collect}`)
  console.log(`      实测 6 个的 executionMode：${EXPECTED.map((n) => `${n}=${modes[n]}`).join('  ')}`)

  /* ------------------- A6 真 execute()：值必须过 output.schema ------------------- */
  const ping = tools.find((t) => t.name === 'ks_ping')
  const live = await ctx.tools.execute({
    signal: new AbortController().signal,
    callId: ToolCallId('verify-tools-real-ping'),
    name: 'ks_ping',
    arguments: {},
  })
  const liveViolations = live.isError ? ['(未走到校验)'] : validateJsonSchemaValue(ping.output.schema, live.value, 'value')
  check('A6 真 ToolRuntime.execute(ks_ping) 走通且值满足自己声明的 output.schema',
    live.isError === false && liveViolations.length === 0,
    live.isError
      ? `isError=true：${live.error?.message}`
      : `value=${JSON.stringify(live.value)?.slice(0, 120)} violations=${liveViolations.length}`
        + ` content=${JSON.stringify(live.content)?.slice(0, 80)}`)

  /* ------------------- A7 反向对照：同一份 schema 必须有牙 ------------------- */
  const violateExtraKey = live.isError ? null : { ...live.value, host_only_field: '不该被接受' }
  const extraViolations = violateExtraKey === null
    ? []
    : validateJsonSchemaValue(ping.output.schema, violateExtraKey, 'value')
  check('A7 反向：多一个 additionalProperties:false 之外的键 ⇒ 必须违规（A6 不是空转）',
    violateExtraKey !== null && extraViolations.length > 0,
    violateExtraKey === null
      ? 'A6 已红，反向对照无从判定'
      : `violations=${extraViolations.length}：${extraViolations.slice(0, 2).join('; ')}`)

  const wrongRoot = live.isError ? null : { ok: 'yes' }
  const rootViolations = wrongRoot === null
    ? []
    : validateJsonSchemaValue(ping.output.schema, wrongRoot, 'value')
  check('A7 反向：根类型/字段类型写错 ⇒ 必须违规',
    wrongRoot !== null && rootViolations.length > 0,
    wrongRoot === null ? 'A6 已红，反向对照无从判定'
      : `violations=${rootViolations.length}：${rootViolations.slice(0, 2).join('; ')}`)

  console.log(`      （假引擎探活命中 fetch ${fetchCount} 次；engine.session 复用，绝不 spawn python）`)

  const failed = results.filter((r) => !r.ok)
  console.log(`\n== verify-tools-real ${failed.length === 0 ? 'PASS' : 'FAIL'} `
    + `(${results.length - failed.length}/${results.length}) ==`)
  process.exit(failed.length === 0 ? 0 : 1)
}

main().catch((error) => {
  console.error(`[fatal] ${error && error.stack ? error.stack : error}`)
  process.exit(1)
})
