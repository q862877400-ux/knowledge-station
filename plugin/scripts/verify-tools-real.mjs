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
 * ### ⚠ 口径更正（2026-09-21 复核打回）：**"同一份文件"这句不成立**
 * 本文件原来把上面解析到的入口写成"真包"，读者容易顺推成"这就是宿主加载的那一份"。**不是**：
 * 实测（复核用 `import.meta.resolve` 做的）宿主是
 * `node --import tsx/esm apps/cli/src/bin.ts`，经 **tsx + `tsconfig.base.json` 的 paths** 加载
 * **`packages/core/tools/src/index.ts`（源码）**；本脚本解析的是 `exports['.']` 的
 * **`lib/index.js`（构建产物）** ⇒ **陈旧构建风险**：检出改过源码但没重建时，这里验的是旧行为。
 * 复核只抽样对照过（导出键集、`ToolRuntime` 原型名、6 工具 × parameters/output 共 12 次
 * `assertSupportedJsonSchema`、`validateJsonSchemaValue` 4 样例 ⇒ 一致；**抽样 ≠ 全部**）。
 * ⇒ 现在**把两条路径都打印出来**（A1 的 `entry`=本脚本解析到的、`hostEntry`=宿主实际加载的），
 *    注释里写清风险；**不许**再把这个入口说成"宿主加载的那一份"。
 *
 * ### ⚠ 覆盖缺口更正（2026-09-21 复核打回）：A2/A3 **不覆盖 `apply()` 的真注册表**
 * 复核实测：删掉 `plugin/src/index.js:1518` 的 `ctx.tools.register(makePingTool(manager))`
 * ⇒ e2e **红**（5/6），而**本脚本仍 9/9 PASS** —— 因为本脚本是**自己**造 6 个定义再注册的，
 * 它验的是"**用插件真工厂造出的这 6 个定义**在真 `ToolRuntime` 上的契约"
 * （`register()` 收下 / `schemas()` 投影 / `executionMode` / `execute()` / 输出 schema 正反），
 * **不是**"`apply()` 真的把 6 个注册进了真注册表"。那条由 **e2e 的 offer 断言**兜
 * （`e2e-install-compose.mjs` 第 8 条：宿主真请求里 6 个 ks_ 工具全在）。
 * ⇒ A3 的名字与宣称已按此收紧，别再读成"注册路径被验过"。
 *
 * ## 断言（每条都打实测数字）
 *   A1 真包可解析且导出 `ToolRuntime`（打印检出路径 + 该包 version + **两条入口**：
 *      本脚本解析到的构建产物、宿主经 tsx+paths 实际加载的源码 + 各自的 mtime）
 *   A2 6/6 工具过宿主自己的 `register()`（用插件**真工厂**造定义，不手抄 schema）
 *   A3 `schemas()` 投影**正好**这 6 个名字（不多不少）——
 *      **范围仅限"本脚本用真工厂造出的这 6 个定义"**；`apply()` 的真注册路径由 e2e 的
 *      offer 断言兜（见上面的⚠口径更正）
 *   A4 投影里**没有** `output / execute / timeoutMs / isConcurrencySafe`（非 wire 字段）
 *   A5 `executionMode`：ks_ping → parallel；ks_collect → exclusive（其余 4 个也打印实测值）
 *   A6 真 `execute('ks_ping')` 走通：`isError:false` 且值满足 `output.schema`
 *   A7 反向对照：同一份 schema 喂一个违反 `additionalProperties:false` 的值 ⇒ **必须违规**；
 *      根类型写错 ⇒ 必须违规（证明 A6 的"满足"不是空转）
 *
 * 跑法：`node plugin/scripts/verify-tools-real.mjs`（退出码 0 = 全通过；工作目录不限）
 */

import { existsSync, readFileSync, rmSync, statSync } from 'node:fs'
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
/** 本跑建出来的临时目录：**跑完必删**（删不掉要打出来，绝不静默 —— 见文件头/注释里的更正留痕）。 */
const tempDirs = []
/**
 * ⚠⚠ 必须**同步**删（`rmSync`），不能 `await rm(...)`：
 * 实测第一版写成 `await fs.rm()` 之后紧跟 `process.exit()` —— `process.exit` 会把
 * **还没跑完的异步 rm** 一起带走，于是目录照样留着（我连跑 3 次数出的正是这个假修）。
 * 证据：改成 `rmSync` 前 AFTER verify 每跑 +2；改成 `rmSync` 后 +0。
 */
function cleanupTempDirs() {
  for (const dir of tempDirs) {
    try {
      rmSync(dir, { recursive: true, force: true, maxRetries: 3 })
    } catch (error) {
      console.log(`FAIL  清理临时目录 ${dir} — ${error?.message ?? error}（删不掉，请手工清）`)
      results.push({ name: `清理临时目录 ${dir}`, ok: false })
    }
  }
}
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
  return { manifest, entry: found, candidates, mtimeMs: mtimeOf(found) }
}

/** 文件的 mtime（毫秒）；读不到给 null（不当成错误 —— 它只是诊断信号）。 */
function mtimeOf(path) {
  try { return statSync(path).mtimeMs } catch { return null }
}

/** mtime 的显示形式（诊断用；读不到就打 `(未知)`）。 */
function fmtTime(mtimeMs) {
  return mtimeMs === null ? '(未知)' : new Date(mtimeMs).toISOString()
}

/**
 * 解析**宿主实际加载的入口**（2026-09-21 复核打回新增，只为把口径说清）。
 *
 * 宿主是 `node --import tsx/esm apps/cli/src/bin.ts` ⇒ tsx 认 `tsconfig.base.json` 的
 * `paths`（实测 `:484 "@deepseek-ai/dsh-tools": ["./packages/core/tools/src"]`）⇒ 加载的是
 * **源码** `packages/core/tools/src/index.ts`，而本脚本解析的是**构建产物**
 * `packages/core/tools/lib/index.js`。⇒ 两者**不是同一份文件**（陈旧构建风险）。
 *
 * 本函数**只做读**：读 tsconfig 的 paths → 拼出候选 →挑第一个存在的（目录 → `index.ts`）。
 * 解析不到就返回 `{ entry: null, note: '…' }`，**不判红**——它不是本脚本的被验物，
 * 只是让读报告的人一眼看见"验的不是宿主那份"。
 * @param {string} specifier 包名（如 `@deepseek-ai/dsh-tools`）
 * @returns {{ entry: string|null, mtimeMs: number|null, note: string }}
 */
function resolveHostLoadedEntry(specifier) {
  const tsconfigPath = join(CHECKOUT, 'tsconfig.base.json')
  if (!existsSync(tsconfigPath)) return { entry: null, mtimeMs: null, note: `（读不到 ${tsconfigPath}）` }
  // ⚠ 实测（2026-09-21）：`tsconfig.base.json` 是 **JSONC**（第 2 行就是 `//` 注释）⇒
  // `JSON.parse` 必抛（我第一版就是这么写的，于是这条静默退化成"(未解析到)"）。
  // 不引 JSONC 解析依赖：只**正则抽** `"<specifier>": [ … ]` 的第一个字符串即可 ——
  // 这是诊断信息，够了；抽不到就如实说"抽不到"，不猜。
  let mapped = null
  try {
    const raw = readFileSync(tsconfigPath, 'utf8')
    const escaped = specifier.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const hit = new RegExp(`"${escaped}"\\s*:\\s*\\[\\s*"([^"]+)"`).exec(raw)
    mapped = hit === null ? null : [hit[1]]
  } catch { mapped = null }
  if (mapped === null) {
    return { entry: null, mtimeMs: null,
      note: `（在 ${tsconfigPath}（JSONC）里抽不到 "${specifier}" 的 paths 映射）` }
  }
  const candidates = []
  for (const target of mapped) {
    const base = resolve(CHECKOUT, target)
    candidates.push(base, `${base}.ts`, join(base, 'index.ts'))
  }
  const found = candidates.find((p) => existsSync(p))
  if (found === undefined) {
    return { entry: null, mtimeMs: null, note: `（paths=${JSON.stringify(mapped)} 都解析不到）` }
  }
  // 目录形式的映射（`"./packages/core/tools/src"`）落到 `index.ts` 才算入口文件。
  const entry = statSync(found).isDirectory() ? join(found, 'index.ts') : found
  return { entry, mtimeMs: mtimeOf(entry), note: '' }
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
  /* ★ A1 的两条路径（2026-09-21 复核打回）：**本脚本解析到的入口** ≠ **宿主实际加载的入口**。
     宿主经 tsx + `tsconfig.base.json` 的 paths 加载 `packages/core/tools/src/index.ts`（源码），
     本脚本解析 package.json 的 `exports['.']` ⇒ `lib/index.js`（构建产物）。
     下面把两者都解析出来、并做一次 mtime 对比当作**陈旧构建风险的可见信号**。 */
  const hostEntry = resolveHostLoadedEntry('@deepseek-ai/dsh-tools')
  const staleBuild = hostEntry.mtimeMs !== null && real.mtimeMs !== null && hostEntry.mtimeMs > real.mtimeMs
  check('A1 真 @deepseek-ai/dsh-tools 可解析且导出 ToolRuntime',
    typeof ToolRuntime === 'function' && mod.ToolRuntime === ToolRuntime,
    `checkout=${CHECKOUT} version=${real.manifest.version}`
      + `\n            本脚本解析到的入口（package.json exports['.'] / main / lib）= ${real.entry}`
      + `（mtime=${fmtTime(real.mtimeMs)}）`
      + `\n            宿主实际加载的入口（tsx + tsconfig paths）= ${hostEntry.entry ?? '(未解析到)'}`
      + `${hostEntry.note === '' ? '' : ` ${hostEntry.note}`}`
      + `（mtime=${fmtTime(hostEntry.mtimeMs)}）`
      + `\n            ⚠ 这是**两份不同的产物**（源码 vs 构建产物）⇒ 陈旧构建风险；`
      + `本脚本**只**在解析到的那份上验，不宣称"与宿主同一份"（口径见文件头）`
      + `${staleBuild ? '\n            ⚠⚠ 源码 mtime **晚于**构建产物 ⇒ 这份 lib/ 可能已陈旧，'
        + '先重建检出再读本脚本的结果' : ''}`)
  const { Context } = await import(pathToFileURL(resolveCheckoutPackage('vendor/cordis', '@deepseek-ai/cordis').entry).href)
  const SystemPrompt = (await import(pathToFileURL(
    resolveCheckoutPackage('packages/core/system-prompt', '@deepseek-ai/dsh-system-prompt').entry).href)).default
  const { ToolCallId } = await import(pathToFileURL(
    resolveCheckoutPackage('packages/llm/llm', '@deepseek-ai/dsh-llm').entry).href)
  const { validateJsonSchemaValue } = mod

  /* 状态隔离：插件会把状态落到 `KS_DATA_DIR` / `KS_CHATMODE_DIR`，两个都指向**临时目录**。
     ⚠ **更正（2026-09-21，复核实测打回）**：本文件第一版只写了"代码树零运行产物"就完了，
     没有删这两个目录，于是在 `%TEMP%` 里**每跑一次泄漏 2 个** `ks-verify-tools-real*`
     （复核数出 6 个 = 我连跑 3 次；而同批的 `e2e-install-compose.mjs` 是**自己删干净**的，
     0 个 `ks-e2e-*`）。我当时的报告还反过来说"e2e 的临时目录不自动删"——**那句是错的**，
     留在这里当留痕：真正漏目录的是本脚本，不是 e2e。下面改成登记 + `finally` 删。 */
  async function makeTempDir(prefix) {
    const dir = await mkdtemp(join(tmpdir(), prefix))
    tempDirs.push(dir)
    return dir
  }
  process.env.KS_DATA_DIR = await makeTempDir('ks-verify-tools-real-data-')
  process.env.KS_CHATMODE_DIR = await makeTempDir('ks-verify-tools-real-chatmode-')

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

  /* ------------------------------ A3 投影正好 6 个 ------------------------------
   * ⚠ **口径收紧（2026-09-21 复核打回）**：这里验的是**本脚本自己用插件真工厂造出的这 6 个
   * 定义**在真 `ToolRuntime` 上的投影，**不是** "`apply()` 的真注册表里正好这 6 个"。
   * 复核实测：删掉 `plugin/src/index.js:1518` 的 `register(makePingTool(manager))` ⇒
   * **本脚本仍 9/9 PASS**，而 e2e 红（5/6）⇒ 注册路径那一段**不归本脚本管**，由 e2e 第 8 条
   * （宿主真请求里 6 个 ks_ 工具全在）兜。断言名已按此收紧，别再读成覆盖了注册路径。 */
  const schemas = ctx.tools.schemas()
  const names = schemas.map((s) => s.name).sort()
  const extra = names.filter((n) => !EXPECTED.includes(n))
  const missing = EXPECTED.filter((n) => !names.includes(n))
  check('A3 schemas() 投影正好这 6 个名字（**本脚本自建的 6 个定义**；不含 apply() 的注册路径）',
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
  return failed.length === 0 ? 0 : 1
}

main()
  .then((code) => {
    cleanupTempDirs()
    // 清理本身就是一条判据：删不掉 ⇒ 红（`code` 与"清理后仍全绿"取与）。
    process.exit(code === 0 && results.every((r) => r.ok) ? 0 : 1)
  })
  .catch((error) => {
    console.error(`[fatal] ${error && error.stack ? error.stack : error}`)
    cleanupTempDirs()
    process.exit(1)
  })
