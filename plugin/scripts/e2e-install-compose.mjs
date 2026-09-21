/**
 * e2e-install-compose.mjs — **真宿主 e2e**：临时 `$DSH_HOME` 起一次 DSH，装我们的插件，
 * 看它挂得上、6 个工具真的被 offer 给模型、`ks_ping` 真的执行到我们自己的假引擎。
 *
 * ## 为什么必须是"真宿主"（现有 34 套冒烟都补不上这一环）
 * 它们全在**进程内**加载插件模块（直接 import `plugin/src/index.js` + 手搓 cordis ctx）⇒
 * 证明不了三件事：① bundle 层装配（profile 的 `dsh.profile.bundles` + `package.json` 依赖）
 * ② 插件能不能过宿主自己的激活/校验（`webServer` 是硬 inject，缺它整个插件 **PENDING**、
 *   6 个工具**一个都不注册**）③ 模型请求里到底收了哪些工具。⇒ 这条 e2e 起真 CLI。
 *
 * ## 每一步都用真命令 + 真断言（照抄任务书 §3.2）
 *   1. 建临时 `$DSH_HOME`（`%TEMP%`）与临时 `KS_DATA_DIR`
 *   2. `dsh <tmp> --from-default-profile headless`（初始化 profile；**要在检出根跑**）
 *   3. `dsh plugin --profile <tmp> add "<repo>/plugin"`（真 pnpm add）
 *   4. `dsh <tmp> --dump-config`：断言里**同时**有 `# == ks-dsh-plugin` 与 `- id: ks-engine`
 *   5. 起假引擎（`/api/v1/health` → 扁平 JSON）+ 写 `engine.session.json`
 *   6. 起假网关（OpenAI 兼容 **SSE 流式**）：记下第一个 chat/completions 的
 *      `tools[].function.name` 全集；第一轮回 `tool_calls`(ks_ping)，第二轮回纯文本 `e2e-done`
 *   7. `dsh <tmp> --patch <overlay> --json <task>` 跑 headless
 *   8. 断言 exit 0 / 6 个 ks_ 工具全在 / ks_ping 的 tool result 里 ok:true + httpStatus:200 /
 *      stdout 里有 `e2e-done`
 *
 * ## 两条**实测钉死**的装配细节（照抄，别猜）
 *   · **headless profile 没有 `webserver` 行**（只有 `web-app` bundle 挂它，
 *     见 `packages/bundle/web-app/cordis.patch.yml` 的 `- id: webserver`）⇒ 直接装我们的插件，
 *     插件会 PENDING（实测原文：`ks-engine (ks-dsh-plugin): pending (waiting for service: webServer)`）。
 *     ⇒ overlay 必须补一行 webserver（`@deepseek-ai/dsh-host-webserver`，profile 的
 *     module-fallback 会从检出解析到它；`port: 0` = 系统分配，不占端口）。
 *   · **settings.yaml 这条路对 headless 不可靠**：实测同一份 `llm-pi-ai.providers` +
 *     `agent-default-model` 写进 `$DSH_HOME/settings.yaml` 后，请求**根本没到假网关**
 *     （`TRANSPORT: Connection error.`，`NODE_DEBUG=net` 显示一次 TCP 连接都没有）——
 *     原因未查明。而 `--patch` 覆盖同两行**能跑通** ⇒ 本脚本用 `--patch`（`--patch` 是
 *     `args.ts:155` 的正式接口，可重复）。
 *
 * ## 钱（业主明令："真花钱"不可自作主张）
 * 起宿主的子进程环境里**剥掉所有 `*_API_KEY`**（尤其 `DEEPSEEK_API_KEY`）与 `KS_PYTHON`，
 * 只留 `KS_FAKE_KEY='fake'`；并在脚本里加一条**自证断言**（子环境里 `DEEPSEEK_API_KEY` 不存在）。
 * 另：`overlay` 把 `llm-pi-ai` 的 providers **整体替换**成只有 `ks-fake` 一条 ⇒ 即使
 * settings/组合层有别的 provider，宿主的默认模型路由也只能落到假网关（端点仅 127.0.0.1）。
 *
 * ## 环境隔离
 * `$DSH_HOME` 只设给**子进程**（绝不动 `web` profile，也绝不动本进程环境）；
 * 所有产物落 `%TEMP%\ks-e2e-<pid>-*`，`finally` 里删干净；代码树零运行产物。
 *
 * 跑法：`node plugin/scripts/e2e-install-compose.mjs`（退出码 0 = 全通过）
 */

import { spawn } from 'node:child_process'
import { createServer } from 'node:http'
import { mkdtemp, rm, writeFile, mkdir } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'

const REPO = resolve(import.meta.dirname, '..', '..')
const PLUGIN_DIR = join(REPO, 'plugin')
const CHECKOUT = process.env.KS_DSH_CHECKOUT || 'D:\\AI\\DSH\\deepseek-harness'
const CLI = ['--import', 'tsx/esm', 'apps/cli/src/bin.ts']
/** 宿主起步上限（任务书 §2.5：≤120s，超时按**红**处理并打完整命令行 + stdout/stderr 尾部）。 */
const BOOT_TIMEOUT_MS = 120_000
/** `pnpm add` 是本地 link，实测 ~0.6s；给足余量但也要有上限（否则挂死）。 */
const ADD_TIMEOUT_MS = 180_000

const KS_TOOLS = ['ks_ping', 'ks_resolve_clause', 'ks_answer', 'ks_effect_report',
  'ks_materials', 'ks_collect']

const results = []
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}
function tail(text, lines = 25) {
  return (text ?? '').split(/\r?\n/).filter((l) => l.trim() !== '').slice(-lines).join('\n')
}

const cleanup = []

async function main() {
  console.log('=== 真宿主 e2e：临时 profile + 真 DSH + 假网关 + 假引擎 ===\n')

  /* ------------------------- 0. 检出（找不到 ⇒ 红） ------------------------- */
  if (!existsSync(CHECKOUT)) {
    check('DSH 检出存在（$env:KS_DSH_CHECKOUT 或默认路径）', false, CHECKOUT)
    return finish('找不到 DSH 检出 ⇒ 本 e2e 判红，不静默跳过（同 run-gates.ps1 的"命令不存在"立论）')
  }
  const cliEntry = join(CHECKOUT, 'apps', 'cli', 'src', 'bin.ts')
  if (!existsSync(cliEntry)) {
    check('DSH CLI 入口存在', false, cliEntry)
    return finish('检出里没有 apps/cli/src/bin.ts')
  }
  check('DSH 检出存在且 CLI 入口在位', true, `${CHECKOUT}（CLI=${cliEntry}）`)

  /* ---------------------------- 1. 临时家目录 ---------------------------- */
  const TEMP_ROOT = await mkdtemp(join(tmpdir(), `ks-e2e-${process.pid}-`))
  cleanup.push(() => rm(TEMP_ROOT, { recursive: true, force: true, maxRetries: 3 }))
  const DSH_HOME = join(TEMP_ROOT, 'dsh-home')
  const KS_DATA_DIR = join(TEMP_ROOT, 'ks-data')
  const OVERLAY_DIR = join(TEMP_ROOT, 'overlay')
  await mkdir(DSH_HOME, { recursive: true })
  await mkdir(KS_DATA_DIR, { recursive: true })
  await mkdir(OVERLAY_DIR, { recursive: true })
  const PROFILE = `kse2e${process.pid}`
  console.log(`      临时 DSH_HOME = ${DSH_HOME}`)
  console.log(`      临时 KS_DATA_DIR = ${KS_DATA_DIR}`)
  console.log(`      临时 profile 名 = ${PROFILE}\n`)

  /* --------------- 2. 建 profile（必须在 `plugin add` **之前** ---------------
   * ⚠ 实测：`dsh plugin --profile <name> add` 在 profile 不存在时会**自己初始化一个空的**
   * （只跟 `plugin` 命令行有关，拿不到 `--from-default-profile`）⇒ 之后再
   * `--from-default-profile headless` 会报 `profile "<name>" already exists`。
   * 所以顺序是：先用 `--dump-config` 那次调用做 init（`--dump-config` 不吃 app 参数，
   * 不会被 headless app 的"要一个 task"拦下），再 `plugin add`。
   * ------------------------------------------------------------------------- */
  const initResult = await runCli([PROFILE, '--from-default-profile', 'headless', '--dump-config'],
    { DSH_HOME, KS_DATA_DIR }, BOOT_TIMEOUT_MS)
  const initLines = (initResult.stdout ?? '').split(/\r?\n/)
  const initPluginRow = initLines.filter((l) => l.includes('name: ks-dsh-plugin'))
  check('2. `dsh <tmp> --from-default-profile headless --dump-config` 建出 profile 且 exit 0',
    initResult.code === 0 && initPluginRow.length === 0,
    initResult.code === 0
      ? `exit=0，${initResult.ms}ms，dump ${initLines.length} 行；此时还没有我们的插件行（name: ks-dsh-plugin 命中 ${initPluginRow.length} 处）`
      : `exit=${initResult.code}（${initResult.ms}ms）\n--- 命令行 ---\n${initResult.commandLine}`
        + `\n--- stdout 尾部 ---\n${tail(initResult.stdout)}\n--- stderr 尾部 ---\n${tail(initResult.stderr)}`)

  /* ------------------- 3. 装插件（真 CLI → 真 pnpm） ------------------- */
  const addResult = await runCli(['plugin', '--profile', PROFILE, 'add', PLUGIN_DIR],
    { DSH_HOME, KS_DATA_DIR }, ADD_TIMEOUT_MS)
  check('3. `dsh plugin --profile <tmp> add <repo>/plugin` 成功（exit 0）',
    addResult.code === 0,
    addResult.code === 0
      ? `exit=0，${addResult.ms}ms；pnpm 输出尾部：…${tail(addResult.stdout, 8).replace(/\n/g, ' ⏎ ')}`
      : `exit=${addResult.code}（${addResult.ms}ms）\n--- 命令行 ---\n${addResult.commandLine}`
        + `\n--- stdout 尾部 ---\n${tail(addResult.stdout)}\n--- stderr 尾部 ---\n${tail(addResult.stderr)}`)

  /* --------------------------- 4. --dump-config --------------------------- */
  const dumpResult = await runCli([PROFILE, '--dump-config'], { DSH_HOME, KS_DATA_DIR }, BOOT_TIMEOUT_MS)
  const dumpLines = (dumpResult.stdout ?? '').split(/\r?\n/)
  const bundleHeaderHits = dumpLines.filter((l) => l.includes('# == ks-dsh-plugin'))
  const engineRowHits = dumpLines.filter((l) => l.includes('- id: ks-engine'))
  const pluginNameHits = dumpLines.filter((l) => l.includes('name: ks-dsh-plugin'))
  check('4. --dump-config 成功（exit 0）', dumpResult.code === 0,
    dumpResult.code === 0 ? `exit=0，${dumpResult.ms}ms，dump ${dumpLines.length} 行`
      : `exit=${dumpResult.code}（${dumpResult.ms}ms）\n--- 命令行 ---\n${dumpResult.commandLine}`
        + `\n--- stdout 尾部 ---\n${tail(dumpResult.stdout)}\n--- stderr 尾部 ---\n${tail(dumpResult.stderr)}`)
  check('4. dump 里同时有 `# == ks-dsh-plugin`（bundle 段头）与 `- id: ks-engine`（我们的行）',
    bundleHeaderHits.length > 0 && engineRowHits.length > 0,
    `bundle 段头 ${bundleHeaderHits.length} 处：${bundleHeaderHits[0] ?? '(缺)'}`
      + ` ｜ 行 id ${engineRowHits.length} 处：${engineRowHits[0] ?? '(缺)'}`
      + ` ｜ name 行：${pluginNameHits[0] ?? '(缺)'}`)

  /* ------------------------ 5. 假引擎 + engine.session ------------------------ */
  const engineHits = []
  const engine = createServer((req, res) => {
    const path = String(req.url ?? '').split('?')[0]
    engineHits.push(path)
    if (path === '/api/v1/health') {
      res.writeHead(200, { 'content-type': 'application/json' })
      res.end(JSON.stringify({
        status: 'ok', uptime_seconds: 12.5, db_status: 'ok',
        vector_engine: 'unknown', parser_worker: 'ok',
      }))
      return
    }
    res.writeHead(404, { 'content-type': 'application/json' })
    res.end(JSON.stringify({ code: 404, error: 'not_found' }))
  })
  await new Promise((r) => engine.listen(0, '127.0.0.1', r))
  const enginePort = engine.address().port
  cleanup.push(() => new Promise((r) => engine.close(r)))
  const sessionFile = join(KS_DATA_DIR, 'engine.session.json')
  await writeFile(sessionFile, JSON.stringify({
    port: enginePort, pid: process.pid, token: 'tok_e2e_fake_engine', started_at: null,
  }))
  check('5. 假引擎在 127.0.0.1 上监听且写好了 engine.session.json（探活即"活着"）',
    Number.isInteger(enginePort) && enginePort > 0,
    `port=${enginePort} sessionFile=${sessionFile}`)

  /* ------------------------------ 6. 假网关 ------------------------------ */
  const gatewayRequests = []
  let toolResultText = null
  const gateway = createServer((req, res) => {
    let raw = ''
    req.on('data', (c) => { raw += c })
    req.on('end', () => {
      let body = null
      try { body = JSON.parse(raw) } catch { body = null }
      const messages = Array.isArray(body?.messages) ? body.messages : []
      const toolNames = (body?.tools ?? []).map((t) => t?.function?.name).filter((n) => typeof n === 'string')
      const toolMessages = messages.filter((m) => m.role === 'tool')
      gatewayRequests.push({
        n: gatewayRequests.length + 1,
        url: req.url,
        model: body?.model,
        stream: body?.stream,
        toolCount: toolNames.length,
        toolNames,
      })
      if (toolMessages.length > 0) {
        toolResultText = toolMessages.map((m) => String(m.content)).join('\n')
        console.log(`      假网关收到 tool result（第 ${gatewayRequests.length} 个请求）：`
          + `${toolResultText.replace(/\s+/g, ' ').slice(0, 220)}`)
      }
      const id = 'chatcmpl-ks-e2e'
      const created = Math.floor(Date.now() / 1000)
      const sse = (delta, finishReason) => {
        res.writeHead(200, { 'content-type': 'text/event-stream', 'cache-control': 'no-cache' })
        res.write(`data: ${JSON.stringify({ id, object: 'chat.completion.chunk', created, model: 'ks-fake-model', choices: [{ index: 0, delta, finish_reason: null }] })}\n\n`)
        res.write(`data: ${JSON.stringify({ id, object: 'chat.completion.chunk', created, model: 'ks-fake-model', choices: [{ index: 0, delta: {}, finish_reason: finishReason }] })}\n\n`)
        res.end('data: [DONE]\n\n')
      }
      if (gatewayRequests.length === 1) {
        sse({
          role: 'assistant',
          tool_calls: [{
            index: 0, id: 'call_ks_ping_1', type: 'function',
            function: { name: 'ks_ping', arguments: '{}' },
          }],
        }, 'tool_calls')
        return
      }
      sse({ role: 'assistant', content: 'e2e-done' }, 'stop')
    })
  })
  await new Promise((r) => gateway.listen(0, '127.0.0.1', r))
  const gatewayPort = gateway.address().port
  cleanup.push(() => new Promise((r) => gateway.close(r)))
  check('6. 假网关（OpenAI 兼容 / SSE 流式）在 127.0.0.1 上监听', Number.isInteger(gatewayPort),
    `port=${gatewayPort}`)

  /* ------------------- overlay：两处装配缺口（见文件头注释） ------------------- */
  const overlayPath = join(OVERLAY_DIR, 'overlay.yml')
  await writeFile(overlayPath, `# e2e overlay：补齐 headless profile 缺的两样（都是**实测**出来的，不是猜的）
- insert:
    # ① headless 的 bundle 里没有 webserver 行（只有 web-app 挂它）⇒ 我们的插件是硬 inject，
    #    缺它整个插件 PENDING、6 个工具一个都不注册。port: 0 = 系统分配，不占端口。
    - id: webserver
      name: '@deepseek-ai/dsh-host-webserver'
      config:
        host: '127.0.0.1'
        port: 0
# ② 默认模型必须落到假网关：providers **整体替换**，只留 ks-fake 一条。
- id: agent-default-model
  config:
    provider: ks-fake
    model: ks-fake-model
- id: llm-pi-ai
  config:
    providers:
      ks-fake:
        apiKeyEnv: KS_FAKE_KEY
        displayName: KS fake
        api: openai-completions
        baseURL: http://127.0.0.1:${gatewayPort}/v1
        models:
          - id: ks-fake-model
            name: KS fake
            contextWindow: 100000
            maxTokens: 8192
            input: [ text ]
`)

  /* ------------------------------ 7. 跑 headless ------------------------------ */
  const headlessEnv = childEnv(DSH_HOME, KS_DATA_DIR)
  // 自证：子环境里**没有**真 key（"万一模型选择没被假 provider 接住"是本条唯一能真花钱的口子）。
  const keyLeaks = Object.keys(headlessEnv).filter((k) => k.endsWith('_API_KEY') && k !== 'KS_FAKE_KEY')
  check('钱：起宿主的子环境里没有任何 *_API_KEY（只剩 KS_FAKE_KEY=fake）',
    keyLeaks.length === 0 && headlessEnv.KS_FAKE_KEY === 'fake'
      && headlessEnv.DEEPSEEK_API_KEY === undefined && headlessEnv.KS_PYTHON === undefined,
    `泄漏键=${keyLeaks.join(',') || '(无)'} KS_FAKE_KEY=${headlessEnv.KS_FAKE_KEY}`
      + ` DEEPSEEK_API_KEY=${String(headlessEnv.DEEPSEEK_API_KEY)} KS_PYTHON=${String(headlessEnv.KS_PYTHON)}`)

  const run = await runCli([PROFILE, '--patch', overlayPath, '--json', 'ping 一次然后说 e2e-done'],
    { DSH_HOME, KS_DATA_DIR }, BOOT_TIMEOUT_MS)
  check('8. headless 真跑一轮 exit 0（含宿主起步 ≤120s）',
    run.code === 0 && run.timedOut === false,
    run.timedOut
      ? `⛔ 超时（${run.ms}ms > ${BOOT_TIMEOUT_MS}ms）\n--- 命令行 ---\n${run.commandLine}`
        + `\n--- stdout 尾部 ---\n${tail(run.stdout)}\n--- stderr 尾部 ---\n${tail(run.stderr)}`
      : `exit=${run.code}，${run.ms}ms`)

  /* --------------------- 8. 工具清单 + ks_ping 真的执行了 --------------------- */
  const first = gatewayRequests[0]
  const offered = first?.toolNames ?? []
  const offeredKs = offered.filter((n) => n.startsWith('ks_'))
  const missingKs = KS_TOOLS.filter((n) => !offeredKs.includes(n))
  check('8. 假网关从宿主第一个请求里读到工具清单（宿主真的发出了请求）',
    first !== undefined,
    first === undefined
      ? `⛔ 一个请求都没收到；命令行=${run.commandLine}\n--- stderr 尾部 ---\n${tail(run.stderr)}`
      : `第 1 个请求 ${first.url} model=${first.model} stream=${first.stream}`
        + ` tools=${first.toolCount} 个`)
  check('8. 我们的 6 个工具**全在** offer 给模型的清单里（包含断言，不是"正好"）',
    missingKs.length === 0 && offeredKs.length >= KS_TOOLS.length,
    `命中 ${offeredKs.length}/6：${offeredKs.join(',') || '(none)'}`
      + `${missingKs.length ? ` ｜缺：${missingKs.join(',')}` : ''}`
      + ` ｜宿主 offer 的工具总数=${offered.length}`)
  console.log(`      宿主 offer 的完整工具清单（${offered.length} 个）：${offered.join(', ')}`)

  const pingOk = toolResultText !== null && /"ok"\s*:\s*true/.test(toolResultText)
    && /"httpStatus"\s*:\s*200/.test(toolResultText)
  check('8. ks_ping 的 tool result 里 ok:true 且 httpStatus:200（真执行到我们的假引擎）',
    pingOk,
    toolResultText === null
      ? '⛔ 没收到 tool result（模型可能没调 ks_ping）'
      : `tool result 片段：${toolResultText.replace(/\s+/g, ' ').slice(0, 240)}`)
  check('5. 假引擎真的被探活过（/api/v1/health 命中）',
    engineHits.some((p) => p === '/api/v1/health'),
    `假引擎收到的路径=${engineHits.join(',') || '(none)'}`)
  check('8. stdout 里出现 `e2e-done`（模型最终答复回灌到宿主输出）',
    (run.stdout ?? '').includes('e2e-done'),
    `stdout 尾部：${tail(run.stdout, 6).replace(/\n/g, ' ⏎ ')}`)

  return finish(null, {
    gatewayRequests: gatewayRequests.map((r) => ({ n: r.n, url: r.url, model: r.model,
      stream: r.stream, toolCount: r.toolCount, ksTools: r.toolNames.filter((n) => n.startsWith('ks_')) })),
    offeredToolCount: offered.length,
    offeredKsTools: offeredKs,
    toolResultSnippet: toolResultText === null ? null : toolResultText.replace(/\s+/g, ' ').slice(0, 400),
    dumpHits: { bundleHeader: bundleHeaderHits[0] ?? null, engineRow: engineRowHits[0] ?? null },
    headlessExit: run.code,
  })
}

/* ------------------------------------------------------------------ *
 * 子进程：命令行、环境、超时、证据
 * ------------------------------------------------------------------ */

/** 起宿主的子环境：剥掉所有 `*_API_KEY` + `KS_PYTHON` + 代理，只留 `KS_FAKE_KEY`。 */
function childEnv(dshHome, ksDataDir) {
  const env = { ...process.env }
  for (const key of Object.keys(env)) {
    if (key.endsWith('_API_KEY') && key !== 'KS_FAKE_KEY') delete env[key]
    if (/^(http_proxy|https_proxy|all_proxy|no_proxy|node_use_env_proxy)$/i.test(key)) delete env[key]
  }
  delete env.KS_PYTHON
  delete env.NODE_DEBUG
  env.KS_FAKE_KEY = 'fake'
  env.DSH_HOME = dshHome
  env.KS_DATA_DIR = ksDataDir
  return env
}

/**
 * 在**检出根**跑一次 `dsh`（`node --import tsx/esm apps/cli/src/bin.ts <args>`）。
 * 自带超时；超时按红处理并把**完整命令行**与 stdout/stderr 留给调用方。
 */
function runCli(args, envs, timeoutMs) {
  const env = childEnv(envs.DSH_HOME, envs.KS_DATA_DIR)
  const commandLine = `cwd=${CHECKOUT} :: "${process.execPath}" ${[...CLI, ...args].map((a) => JSON.stringify(a)).join(' ')}`
  const started = Date.now()
  return new Promise((resolveRun) => {
    const child = spawn(process.execPath, [...CLI, ...args], {
      cwd: CHECKOUT, env, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'],
    })
    let stdout = ''
    let stderr = ''
    let timedOut = false
    let settled = false
    const timer = setTimeout(() => {
      timedOut = true
      child.kill('SIGKILL')
    }, timeoutMs)
    child.stdout.on('data', (c) => { stdout += c.toString('utf8') })
    child.stderr.on('data', (c) => { stderr += c.toString('utf8') })
    const done = (code) => {
      if (settled) return
      settled = true
      clearTimeout(timer)
      resolveRun({ code, timedOut, ms: Date.now() - started, stdout, stderr, commandLine })
    }
    child.on('error', (error) => {
      stderr += `\n[spawn error] ${error?.message ?? error}`
      done(-1)
    })
    child.on('close', (code, signal) => done(signal === null ? code : `signal:${signal}`))
  })
}

/** 汇总 + 清理（真宿主 e2e 的清理必须在 finally 里做，不能只在绿路径做）。 */
let finished = false
async function finish(earlyFatal, summary) {
  if (finished) return
  finished = true
  if (earlyFatal) check('可运行前提', false, earlyFatal)
  // 清理：反序（先关两个 server，再删临时目录）
  for (const step of [...cleanup].reverse()) {
    try { await step() } catch (error) { console.log(`      （清理告警：${error?.message ?? error}）`) }
  }
  const failed = results.filter((r) => !r.ok)
  console.log(`\n== e2e-install-compose ${failed.length === 0 ? 'PASS' : 'FAIL'} `
    + `(${results.length - failed.length}/${results.length}) ==`)
  if (summary !== undefined) {
    console.log(`== 机器可读摘要 ==`)
    console.log(JSON.stringify({
      kind: 'ks-e2e-install-compose',
      ok: failed.length === 0,
      checks: results,
      checkout: CHECKOUT,
      ...summary,
    }, null, 2))
  }
  if (failed.length > 0) {
    console.log(`\n失败断言：`)
    for (const f of failed) console.log(`  FAIL  ${f.name}`)
  }
  process.exit(failed.length === 0 ? 0 : 1)
}

main().catch(async (error) => {
  console.error(`[fatal] ${error && error.stack ? error.stack : error}`)
  await finish(`未捕获异常：${error?.message ?? error}`)
})
