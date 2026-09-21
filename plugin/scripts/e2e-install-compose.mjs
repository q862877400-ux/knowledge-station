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
 *   8. 断言 exit 0 / 6 个 ks_ 工具全在 / ks_ping 的 tool result 里 ok:true + httpStatus:200
 *      **且 `engine.port` 恰是我们这台假引擎、`engine.reused === true`** /
 *      stdout 里有 `e2e-done`
 *
 * ## ⚠ 复核打回的三处（2026-09-21，`verify-e2e-real-report.md`；错话保留 + 就地更正）
 *   · **假绿（本文件最要紧的一处）**：旧第 8 条断言原文是
 *     "ks_ping 的 tool result 里 ok:true 且 httpStatus:200（**真执行到我们的假引擎**）"。
 *     **"真执行到我们的假引擎"这句当时没有证据**：复核实测把假引擎 `/api/v1/health` 改成 500，
 *     e2e 仍 **14/14 PASS / exit 0** —— 插件按陈旧会话 `spawn` 了**真 python 引擎**顶包
 *     （`plugin/src/engine.js:558`；实测 `port=14226 pid=36776 reused=false`，假引擎是 **14215**）。
 *     ⇒ 现在把 tool result 的 `engine.port`/`engine.reused` 与**假引擎端口**绑死（见第 8 条）。
 *   · **A2 打印了 API key 的值**：旧 `:290` 是 `` DEEPSEEK_API_KEY=${String(...)} `` ⇒ 父进程
 *     设真 key 时**真值进了输出**，而失败步输出会被 `run-gates.ps1` 落盘。⇒ 只打**存在性**，
 *     外加全输出 `redact()` 兜底（见顶部）。
 *   · **C 变异 5 红得不可诊断**：overlay 去掉 webserver 行时，报的是 `unknown tool "ks_ping"`，
 *     全程没有 `pending`/`webServer` 字样 ⇒ 现在把宿主给的**插件待命原因**捞进失败信息。
 *
 * ## 两条装配细节（**第一条实测钉死；第二条见下面的更正，别照抄旧的结论**）
 *   · **headless profile 没有 `webserver` 行**（只有 `web-app` bundle 挂它，
 *     见 `packages/bundle/web-app/cordis.patch.yml` 的 `- id: webserver`）⇒ 直接装我们的插件，
 *     插件会 PENDING（实测原文：`ks-engine (ks-dsh-plugin): pending (waiting for service: webServer)`）。
 *     ⇒ overlay 必须补一行 webserver（`@deepseek-ai/dsh-host-webserver`，profile 的
 *     module-fallback 会从检出解析到它；`port: 0` = 系统分配，不占端口）。
 *   · **`--patch` 覆盖 `agent-default-model` + `llm-pi-ai` 这条**是本脚本实际走的、
 *     **实测能跑通**的路（`--patch` 是 `args.ts:155` 的正式接口，可重复）。
 *
 * ### ⚠ 更正（2026-09-21，复核要求限时探一次之后）：settings 路的旧结论**撤回**
 * 本文件第一版写的是"settings.yaml 这条路对 headless 不可靠 …… `TRANSPORT: Connection error.`，
 * `NODE_DEBUG=net` 显示一次 TCP 连接都没有 ⇒ 改用 `--patch`"。**那句话保留，但它现在站不住**：
 * 复核让我限时探根因，我探到的是——**我当时那些最小探针自己是坏的**：
 *   ① 探针网关只发 `data: [DONE]`、**没有 content chunk** ⇒ pi-ai 的流永远不结束（TCP 连上了、
 *      HTTP 请求也到了，但宿主一直等）——`NODE_DEBUG=net` 里能看到 `afterConnect` + `_read`；
 *   ② 探针**没有设 `KS_DATA_DIR`** ⇒ 插件会去找**真** `%APPDATA%\KnowledgeStation` 的引擎会话。
 *   ⇒ 所以"settings 路不行"这个结论**不能维持**，我**没有**证明它。
 * **已经**能钉住的只有两条（都有原文）：
 *   · **`settings.yaml` 在 headless 档确实被读了**：往里写坏 YAML，宿主当场报
 *     `settings (@deepseek-ai/dsh-settings-file): Error: settings-file: invalid document at
 *     <home>\settings.yaml: BAD_INDENT at line 3, column 1` ⇒ 文件**有**消费者。
 *   · **`--dump-config` 天生看不到 settings 内容**：headless 的 dump 里
 *     `- id: llm-pi-ai` 这一行**在**（`name: '@deepseek-ai/dsh-llm-pi-ai'`，行后**没有 `config:`**，
 *     与 `packages/bundle/base/cordis.patch.yml` 里该行的形状一致）；整份 363 行 dump 里
 *     `providers` 命中 **0** 行、`ks-fake` 命中 **0** 行。⇒ "dump 里没有 providers" **不是**根因，
 *     那只是 dump 只打组合层（settings 是运行时 provider）。
 * **未查明** = "settings 里的 `llm-pi-ai.providers.ks-fake` / `agent-default-model` 在 headless
 * 档到底有没有变成可用路由"。要查清得用**好探针**（带 content chunk 的网关 + 设 `KS_DATA_DIR`）
 * 重跑一次；本脚本继续用 `--patch`（已知能通、且不依赖这个问题）。
 *
 * ## 钱（业主明令："真花钱"不可自作主张）
 * 起宿主的子进程环境里**剥掉所有 `*_API_KEY`**（尤其 `DEEPSEEK_API_KEY`）与 `KS_PYTHON`，
 * 只留 `KS_FAKE_KEY='fake'`；并在脚本里加一条**自证断言**（子环境里 `DEEPSEEK_API_KEY` 不存在）。
 * 另：`overlay` 把 `llm-pi-ai` 的 providers **整体替换**成只有 `ks-fake` 一条 ⇒ 即使
 * settings/组合层有别的 provider，宿主的默认模型路由也只能落到假网关（端点仅 127.0.0.1）。
 *
 * ## 环境隔离（实测数字，2026-09-21 复核要求补）
 * `$DSH_HOME` 只设给**子进程**（绝不动 `web` profile，也绝不动本进程环境）；
 * 所有产物落 `%TEMP%\ks-e2e-<pid>-*`，`finally` 里**同步/await 删干净**；代码树零运行产物。
 * **实测**：`%TEMP%\ks-e2e-*` 在连跑 3 次 + 再跑 2 次前后都是 **0 个**（本脚本自己清干净）。
 * （同批的 `verify-tools-real.mjs` 当时每跑泄漏 2 个目录 —— 已在那边修掉并在注释里留痕。）
 * ⚠ **补（2026-09-21 复核打回）**：上面"清干净"说的是**删成功**那条路。**删失败**时旧版只打
 * `（清理告警：…）` 仍 `exit 0`（与 `verify-tools-real.mjs` 的 exit 1 口径不一致）⇒ 现在
 * 清理失败**登记为一条失败断言、计入退出码**（告警文案保留）。
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

/**
 * ★ 值一律不进输出（**A2，2026-09-21 复核打回**）。
 *
 * 旧版 `:290` 打的是 `` DEEPSEEK_API_KEY=${String(headlessEnv.DEEPSEEK_API_KEY)} ``：父进程
 * 一旦设了真 key，失败步的完整输出会被 `run-gates.ps1` 落盘 ⇒ **真 key 写进门禁日志**。
 * 复核实测：父环境设 `SHOULD-NOT-LEAK` 时它**照打不误**。
 * ⇒ 现在只打**存在性**（`存在=是/否`），并加一道**全输出兜底**：本脚本从父环境收下的
 * 每一个 key 值都登记进 `LEAK_VALUES`，`console.log` 出口统一做替换。兜底覆盖
 * "子进程 stdout/stderr 又把它带回来"（例如宿主把配置回显在报错里）这种非本地拼接。
 *
 * **口径**：`redact()` 只对**我们知道的那些值**做替换（不是通用脱敏器）——
 * 它守的是"本脚本不会把自己收到/生出的凭据打出去"，不宣称能脱敏任意第三方文本。
 */
const LEAK_VALUES = new Set()
function registerLeakValue(value) {
  if (typeof value === 'string' && value.length >= 4) LEAK_VALUES.add(value)
}
;(function seedParentLeakValues() {
  for (const [key, value] of Object.entries(process.env)) {
    if (key.endsWith('_API_KEY') && key !== 'KS_FAKE_KEY') registerLeakValue(value)
  }
})()
const API_KEY_PATTERN = /(("?)([A-Za-z0-9_]*_API_KEY)\2\s*[:=]\s*)("([^"]*)"|'([^']*)'|[^\s,;]+)/g
function redact(text) {
  let out = String(text)
  let masked = 0
  for (const value of LEAK_VALUES) {
    if (out.includes(value)) { out = out.split(value).join('<redacted>'); masked += 1 }
  }
  out = out.replace(API_KEY_PATTERN, (_all, prefix, _q, name) => {
    masked += 1
    return `${prefix}<redacted:${name}>`
  })
  return { text: out, masked }
}
const rawLog = console.log.bind(console)
console.log = (...args) => rawLog(...args.map((arg) =>
  (typeof arg === 'string' ? redact(arg).text : arg)))

const results = []
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}

/**
 * ★ C（2026-09-21 复核打回）：**"工具没被 offer"的红必须能看出原因。**
 *
 * 复核实测**变异 5**（overlay 去掉 webserver 行）⇒ e2e 红（0/6、`unknown tool "ks_ping"`），
 * 但**全程没有 `pending`/`webServer` 字样**、dump 两条仍绿 ⇒ 读报告的人看不出"是缺 webserver"。
 * 宿主其实**打了**这条（`app-boot` 的 `activationDiagnostic` → `stderr`：
 * `dsh: warning: 1 entry did not activate` + `ks-engine (ks-dsh-plugin): pending
 * (waiting for service: webServer)`，原文见 DSH 检出
 * `packages/boot/app-boot/src/index.ts:820-828`），只是**没有任何断言把它捞出来**。
 * ⇒ 这里在 stdout/stderr 里搜插件待命原因，**原样带出**到失败信息里。
 */
const PLUGIN_PENDING_PATTERNS = [
  /did not activate/i,
  /pending \(waiting for service/i,
  /Plugins waiting for services/i,
  /ks-dsh-plugin|ks-engine/,
]
function pluginStandbyReason(...texts) {
  const lines = texts.join('\n').split(/\r?\n/)
  const hits = lines
    .map((line, index) => ({ line: line.trim(), index }))
    .filter(({ line }) => line !== '' && PLUGIN_PENDING_PATTERNS.some((re) => re.test(line)))
  if (hits.length === 0) return '(宿主输出里没有插件待命线索：搜 did not activate / pending (waiting for service / ks-dsh-plugin 命中 0 行)'
  // 待命原因常与它的标题行相邻（`...: pending (…)` 紧跟在 `dsh: warning: …` 后面），
  // 所以命中行 + 它**前面一行**一起带出（如 `dsh: warning: 1 entry did not activate`）。
  const shown = []
  for (const { index } of hits.slice(0, 3)) {
    const context = lines.slice(Math.max(0, index - 1), index + 1).map((l) => l.trim()).filter(Boolean)
    shown.push(context.join(' ⏎ '))
  }
  return `${hits.length} 行线索 ｜ ${shown.join(' ； ')}`
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

  /* ------------------- 钱的自证（**必须在起宿主之前**） -------------------
   * `childEnv()` 是**同一份**环境：所有 `dsh` 子进程都收这一份，所以断言看的就是
   * 宿主真正拿到的那份环境。⚠ 旧版把它放在第 7 步，用的是**又新建的**一份
   * `childEnv(…)`——内容碰巧相同，但"断言的那份 ≠ 交出去的那份"是个坏形状，
   * 一并收紧。诊断**只打存在性，值一律不打**（见文件顶部 `redact()` 的说明）。
   * ------------------------------------------------------------------------- */
  const headlessEnv = childEnv(DSH_HOME, KS_DATA_DIR)
  // 自证：子环境里**没有**真 key（"万一模型选择没被假 provider 接住"是本条唯一能真花钱的口子）。
  const keyLeaks = Object.keys(headlessEnv).filter((k) => k.endsWith('_API_KEY') && k !== 'KS_FAKE_KEY')
  const keyPresent = (key) => headlessEnv[key] === undefined ? '否' : '是'
  check('钱：起宿主的子环境里没有任何 *_API_KEY（只剩 KS_FAKE_KEY）',
    keyLeaks.length === 0 && headlessEnv.KS_FAKE_KEY === 'fake'
      && headlessEnv.DEEPSEEK_API_KEY === undefined && headlessEnv.KS_PYTHON === undefined,
    `泄漏键=${keyLeaks.join(',') || '(无)'}`
      + ` KS_FAKE_KEY 存在=${keyPresent('KS_FAKE_KEY')}`
      + ` DEEPSEEK_API_KEY 存在=${keyPresent('DEEPSEEK_API_KEY')}`
      + ` KS_PYTHON 存在=${keyPresent('KS_PYTHON')}`)

  /* --------------- 2. 建 profile（必须在 `plugin add` **之前** ---------------
   * ⚠ 实测：`dsh plugin --profile <name> add` 在 profile 不存在时会**自己初始化一个空的**
   * （只跟 `plugin` 命令行有关，拿不到 `--from-default-profile`）⇒ 之后再
   * `--from-default-profile headless` 会报 `profile "<name>" already exists`。
   * 所以顺序是：先用 `--dump-config` 那次调用做 init（`--dump-config` 不吃 app 参数，
   * 不会被 headless app 的"要一个 task"拦下），再 `plugin add`。
   * ------------------------------------------------------------------------- */
  const initResult = await runCli([PROFILE, '--from-default-profile', 'headless', '--dump-config'],
    headlessEnv, BOOT_TIMEOUT_MS)
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
    headlessEnv, ADD_TIMEOUT_MS)
  check('3. `dsh plugin --profile <tmp> add <repo>/plugin` 成功（exit 0）',
    addResult.code === 0,
    addResult.code === 0
      ? `exit=0，${addResult.ms}ms；pnpm 输出尾部：…${tail(addResult.stdout, 8).replace(/\n/g, ' ⏎ ')}`
      : `exit=${addResult.code}（${addResult.ms}ms）\n--- 命令行 ---\n${addResult.commandLine}`
        + `\n--- stdout 尾部 ---\n${tail(addResult.stdout)}\n--- stderr 尾部 ---\n${tail(addResult.stderr)}`)

  /* --------------------------- 4. --dump-config --------------------------- */
  const dumpResult = await runCli([PROFILE, '--dump-config'], headlessEnv, BOOT_TIMEOUT_MS)
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
  const run = await runCli([PROFILE, '--patch', overlayPath, '--json', 'ping 一次然后说 e2e-done'],
    headlessEnv, BOOT_TIMEOUT_MS)
  check('8. headless 真跑一轮 exit 0（含宿主起步 ≤120s）',
    run.code === 0 && run.timedOut === false,
    run.timedOut
      ? `⛔ 超时（${run.ms}ms > ${BOOT_TIMEOUT_MS}ms）\n--- 命令行 ---\n${run.commandLine}`
        + `\n--- stdout 尾部 ---\n${tail(run.stdout)}\n--- stderr 尾部 ---\n${tail(run.stderr)}`
      : `exit=${run.code}，${run.ms}ms`)

  /* --------------------- 8. 工具清单 + ks_ping 真的执行了 ---------------------
   * ⚠ **位置无关**（2026-09-21 复核要求 + 自查）：请求序列是 DSH 内部行为（实测一轮
   * 3 个请求：第 1 个 tools=30、第 2 个 tools=0、第 3 个 tools=30 且带回结果），换个版本
   * 就可能变 ⇒ 断言只依赖**语义**：
   *   · "所有收到过的请求里，至少有一个带着我们的全部 6 个工具"（不是"第 1 个必须带"）；
   *   · "至少有一个请求带着 ks_ping 的 tool result，且里面 ok:true + httpStatus:200"
   *     （不是"第 3 个必须是它"）。
   * **本文件里没有任何"正好 N 个请求"的硬编码**（唯一的按序号分支是假网关自己的应答
   * 剧本：第 1 个请求回 tool_calls，其余回纯文本 —— 那是**我们造的行为**，不是断言）。
   * ------------------------------------------------------------------------- */
  const allOffered = gatewayRequests.flatMap((r) => r.toolNames)
  const offeredKs = [...new Set(allOffered.filter((n) => n.startsWith('ks_')))]
  const missingKs = KS_TOOLS.filter((n) => !offeredKs.includes(n))
  const carrier = gatewayRequests.find((r) => KS_TOOLS.every((n) => r.toolNames.includes(n)))
  check('8. 假网关从宿主请求里读到过工具清单（宿主真的发出了请求）',
    gatewayRequests.length > 0,
    gatewayRequests.length === 0
      ? `⛔ 一个请求都没收到；命令行=${run.commandLine}\n--- stderr 尾部 ---\n${tail(run.stderr)}`
      : `共 ${gatewayRequests.length} 个请求；带全部 6 个工具的请求序号=`
        + `${carrier === undefined ? '(无)' : carrier.n}`)
  check('8. 我们的 6 个工具**全在** offer 给模型的清单里（包含断言，不是"正好"）',
    missingKs.length === 0,
    `命中 ${offeredKs.length}/6：${offeredKs.join(',') || '(none)'}`
      + `${missingKs.length ? ` ｜缺：${missingKs.join(',')}` : ''}`
      + ` ｜承载它们的那个请求 offer 总数=${carrier?.toolCount ?? '(n/a)'}`
      + `${missingKs.length ? `\n            ∵ 插件没把工具注册上来，宿主给的待命原因：`
        + `${pluginStandbyReason(run.stdout ?? '', run.stderr ?? '')}` : ''}`)
  console.log(`      宿主 offer 的完整工具清单（取并集，去重后 ${[...new Set(allOffered)].length} 个）：`
    + `${[...new Set(allOffered)].join(', ')}`)

  /* ------------------- ★ A：tool result 必须绑在**我们的假引擎**上 -------------------
   * **这就是复核打回的那条假绿**（2026-09-21）：旧断言只看 `ok:true` + `httpStatus:200`，
   * 而插件在假引擎返非 200 时会**按陈旧会话 spawn 真 python 引擎**顶包
   * （`plugin/src/engine.js:558 spawnEngine`；复核实测 `port=14226 pid=36776 reused=false`
   * 而假引擎是 14215）⇒ 假引擎坏掉，e2e **照样 14/14 PASS / exit 0**。
   *
   * 现在把 tool result 里的 `engine` 与**我们起的那台假引擎**绑死：
   *   · `engine.port === enginePort`（我们这一跑实际 listen 的端口）；
   *   · `engine.reused === true`（会话文件里那个实例是**外部的**、不是插件自己起的
   *     —— `plugin/src/index.js:792` 的 `reused: !session.spawnedByUs`）。
   * 任一不成立 ⇒ **红**，并且诊断打出**期望端口 vs 实测端口**与 `reused`。
   * 真 python 顶包时 `engine.port` ≠ 假引擎端口（且 reused=false），所以这条有牙。
   * ------------------------------------------------------------------------- */
  const parsedToolResult = (() => {
    if (toolResultText === null) return null
    try { return JSON.parse(toolResultText) } catch { return null }
  })()
  const resultEngine = parsedToolResult?.engine ?? null
  const engineResultPort = resultEngine?.port ?? null
  const engineResultReused = resultEngine?.reused ?? null
  const realEnginePorts = [...new Set(
    [...`${run.stdout ?? ''}\n${run.stderr ?? ''}`.matchAll(/KNOWLEDGE_STATION_PORT=(\d+)/g)].map((m) => Number(m[1])))]
  const pingBoundToFakeEngine = engineResultPort === enginePort && engineResultReused === true
  const pingDiag = toolResultText === null
    ? '⛔ 没收到 tool result（模型可能没调 ks_ping）'
    : `期望假引擎端口=${enginePort} ｜ 实测 tool result engine.port=${String(engineResultPort)}`
      + `（${engineResultPort === enginePort ? '相符' : '❌ 不符'}）`
      + ` ｜ reused=${String(engineResultReused)}（期望 true）`
      + ` ｜ ok=${String(parsedToolResult?.ok)} httpStatus=${String(parsedToolResult?.httpStatus)}`
      + ` ｜ 宿主输出里的真引擎端口=${realEnginePorts.join(',') || '(无)'}`
      + `${engineResultPort !== enginePort ? ' ⇒ 工具执行打到了**别的**引擎上（真 python 顶包？）' : ''}`
      + `\n            tool result 片段：${toolResultText.replace(/\s+/g, ' ').slice(0, 240)}`
  check('8. ks_ping 的 tool result **绑在假引擎上**：ok:true + httpStatus:200 + '
    + 'engine.port === 假引擎端口 + engine.reused === true',
  toolResultText !== null && parsedToolResult !== null && parsedToolResult.ok === true
    && parsedToolResult.httpStatus === 200 && pingBoundToFakeEngine,
  pingDiag)
  check('5. 假引擎真的被探活过（/api/v1/health 命中）',
    engineHits.some((p) => p === '/api/v1/health'),
    `假引擎收到的路径=${engineHits.join(',') || '(none)'}`)
  check('8. stdout 里出现 `e2e-done`（模型最终答复回灌到宿主输出）',
    (run.stdout ?? '').includes('e2e-done'),
    `stdout 尾部：${tail(run.stdout, 6).replace(/\n/g, ' ⏎ ')}`)

  return finish(null, {
    gatewayRequests: gatewayRequests.map((r) => ({ n: r.n, url: r.url, model: r.model,
      stream: r.stream, toolCount: r.toolCount, ksTools: r.toolNames.filter((n) => n.startsWith('ks_')) })),
    offeredToolCountUnion: [...new Set(allOffered)].length,
    carrierRequestNumber: carrier?.n ?? null,
    carrierToolCount: carrier?.toolCount ?? null,
    offeredKsTools: offeredKs,
    fakeEnginePort: enginePort,
    toolResultEngine: resultEngine,
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
    if (key.endsWith('_API_KEY') && key !== 'KS_FAKE_KEY') {
      // 剥之前先把**父环境里那个值**登记进兜底脱敏名单：即使它经别的通道（宿主回显
      // 配置、报错文本）又出现在输出里，出口处也会被替换成 `<redacted>`。
      registerLeakValue(env[key])
      delete env[key]
    }
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
 *
 * `env` 由调用方传入（`childEnv()` 的产物）——**不要在这里再调一次 `childEnv(envs…)`**：
 * 那样每次都会重建一份对象，而"自证钱没泄漏"的断言必须看**真正交给宿主的那一份**。
 */
function runCli(args, env, timeoutMs) {
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
  // ⚠ **B（2026-09-21 复核打回）：清理失败必须计入退出码**（与 `verify-tools-real.mjs:56-65`
  // 同口径 —— 那边是 `results.push({ok:false})` + exit 1）。旧版这里只打
  // `（清理告警：…）` 然后照样 exit 0 ⇒ **临时目录泄漏被判绿**（复核实测：探针让删除失败，
  // verify-tools-real exit 1，而 e2e exit 0）。现在：告警文案保留，另外**登记成一条失败断言**。
  const cleanupFailures = []
  for (const step of [...cleanup].reverse()) {
    try { await step() } catch (error) {
      const reason = error?.message ?? error
      console.log(`      （清理告警：${reason}）`)
      cleanupFailures.push(String(reason))
    }
  }
  if (cleanupFailures.length > 0) {
    check(`清理临时目录/服务（${cleanupFailures.length} 处失败 ⇒ 计入退出码）`, false,
      `${cleanupFailures.join(' ｜ ')}（删不掉，请手工清）`)
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
