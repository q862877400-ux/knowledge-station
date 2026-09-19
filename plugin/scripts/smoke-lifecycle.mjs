/**
 * ks-dsh-plugin — scripts/smoke-lifecycle.mjs
 *
 * 生命周期 / 所有权守卫（2026-09-19）：两处"会坏但不报错"的缺陷，各配一条**可证 FAIL** 的断言。
 *
 *   A. **入库任务接管真的会推进吗**——`ingestJobStartupCheck` 尾巴上的 `adoptJob` 曾经把
 *      `runJobPollLoop` 的 `manager` 参数漏了（`runJobPollLoop(jobId, initialStatus)`，
 *      而函数签名是 `(manager, jobId, initialStatus)`）⇒ `manager` 实参是**字符串 job_id**、
 *      `jobId` 实参是状态串，循环第一句 `jobTick('running')` 就因为 id 不匹配**直接退出**。
 *      后果：宿主侧镜像永不推进（浏览器关掉后的权威记录是空的）、上次遗留的 running 批
 *      永不重接管。**不会抛错**，所以没人发现。
 *
 *   B. **启动收尾的竞态**——`inspectionStartupCheck` 是 fire-and-forget，但 effect 的 disposer
 *      只 `stopAutoInspectionTimer()`；若卸载落在 `await initInspectionState()` 窗口内，
 *      先停（timer 还是 null）、后建 ⇒ **泄漏一个 30s `setInterval`**，且它持有已 dispose 的 ctx。
 *      断言分两半：竞态下**不许**安装定时器（B1）、干净路径下**必须**安装并被清理（B2）
 *      —— 只断言 B1 会被"永远取消"的假实现骗过。
 *
 * 隔离：`KS_DATA_DIR` → 临时目录。⚠ 该变量同时是**引擎**的数据目录；本文件把 fetch 与
 * manager 都打桩、绝不拉起真引擎，所以安全（同 smoke-engine-guard 的口径）。
 * 不设它的话，状态文件会写进**真实** `%APPDATA%\KnowledgeStation` —— 那会让真产品下次启动
 * 去接管一个烟测造出来的假任务。
 *
 * Run:  node scripts/smoke-lifecycle.mjs     (exit 0 = all cases pass)
 */

import { mkdtemp, readFile, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

import { ingestJobStartupCheck } from '../src/ingest.js'
import { inspectionStartupCheck, registerKsInspectionRoutes } from '../src/inspection.js'

const dataDir = await mkdtemp(join(tmpdir(), 'ks-lifecycle-smoke-'))
process.env.KS_DATA_DIR = dataDir

const results = []
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}

/** 有界等待：返回 fn() 何时为真，超时返回 false（不 busy-poll 无上限）。 */
async function waitFor(fn, timeoutMs = 3000, stepMs = 20) {
  const t0 = Date.now()
  for (;;) {
    if (await fn()) return true
    if (Date.now() - t0 > timeoutMs) return false
    await new Promise((resolve) => { setTimeout(resolve, stepMs) })
  }
}

async function readJson(path) {
  try { return JSON.parse(await readFile(path, 'utf8')) } catch { return null }
}

const realFetch = globalThis.fetch
console.log('=== ks-dsh-plugin lifecycle smoke ===\n')

/* ------------------------------------------------------------------ *
 * A. 入库任务接管：宿主镜像必须真的推进到终态
 * ------------------------------------------------------------------ */

const JOB_ID = 'job-smoke-A'

// 引擎打桩：状态查询（无 query）→ 直接终态 done；行页（rows_offset）→ 空页就收。
let statusProbes = 0
globalThis.fetch = async (url) => {
  const u = String(url)
  if (u.includes('/api/v1/health')) {
    return new Response(JSON.stringify({ status: 'healthy' }), {
      status: 200, headers: { 'Content-Type': 'application/json' },
    })
  }
  if (u.includes('rows_offset')) {
    return new Response(JSON.stringify({
      code: 200, status: 'success', data: { rows: [], rows_count: 0 },
    }), { status: 200, headers: { 'Content-Type': 'application/json' } })
  }
  statusProbes += 1
  return new Response(JSON.stringify({
    code: 200,
    status: 'success',
    data: { status: 'done', done: 2, total: 2, buckets: { ok: 2, warn: 0, block: 0 }, error: null },
  }), { status: 200, headers: { 'Content-Type': 'application/json' } })
}

// 上一进程留下的"正在跑"的任务（就是启动接管要处理的情形）。
await writeFile(join(dataDir, 'ks-ingest.json'), JSON.stringify({
  last: {
    job_id: JOB_ID, status: 'running', total: 2, done: 0,
    buckets: { ok: 0, warn: 0, block: 0 }, dir: '', error: null,
  },
  stale_run: false,
}, null, 2), 'utf8')

let liveCalls = 0
const managerA = {
  ensureLive: async () => { liveCalls += 1; return { port: 65001, token: 'smoke-token' } },
  touchActivity() {},
}
const ctxA = { logger: { info() {}, warn() {}, error() {} } }

await ingestJobStartupCheck(ctxA, managerA)

// adopt 是 fire-and-forget —— 轮询在后台推进镜像，这里等它落到 done。
const advanced = await waitFor(async () => {
  const s = await readJson(join(dataDir, 'ks-ingest.json'))
  return s?.last?.status === 'done'
})

check('A1 接管必须真的去问引擎（ensureLive 被调用）', liveCalls >= 1,
  `ensureLive=${liveCalls}（0 = 轮询循环被参数错位整条跳过）`)
check('A2 宿主镜像推进到 done', advanced === true,
  `status=${(await readJson(join(dataDir, 'ks-ingest.json')))?.last?.status ?? 'n/a'}`
  + ` · statusProbes=${statusProbes}`)

globalThis.fetch = realFetch

/* ------------------------------------------------------------------ *
 * B. 巡检启动收尾的竞态：disposer 落在 await 窗口内不许安装定时器
 * ------------------------------------------------------------------ */

// 上一进程留下的终态批次（total=0 ⇒ 跳过细分自愈，不碰引擎）。
await writeFile(join(dataDir, 'ks-inspection.json'), JSON.stringify({
  last: { batch_id: 'batch-smoke-B', status: 'done', total: 0 },
  stale_run: false,
}, null, 2), 'utf8')

const realSetInterval = globalThis.setInterval
const realClearInterval = globalThis.clearInterval
let intervals = 0
let cleared = 0
globalThis.setInterval = () => { intervals += 1; return { unref() {} } }
globalThis.clearInterval = () => { cleared += 1 }

const webCtx = {
  webServer: { register: () => () => {} },
  logger: { info() {}, warn() {}, error() {} },
}
const managerB = {
  ensureLive: async () => ({ port: 65001, token: 'smoke-token' }),
  touchActivity() {},
}

// ---- B1 竞态窗口：注册 → 启动检查（fire-and-forget）→ **同一 tick 内**卸载
const dispose1 = registerKsInspectionRoutes(webCtx, managerB)
const pending = inspectionStartupCheck(webCtx, managerB)
dispose1()
await pending

check('B1 竞态下不许泄漏定时器（disposer 落在 await 窗口内）', intervals === 0,
  `setInterval=${intervals}（1 = 卸载后仍安装了一个 30s 定时器，且持有已 dispose 的 ctx）`)

// ---- B2 非真空性：干净路径必须**真的**安装定时器，并能被卸载清掉
intervals = 0
cleared = 0
const dispose2 = registerKsInspectionRoutes(webCtx, managerB)
await inspectionStartupCheck(webCtx, managerB)
const installed = intervals
dispose2()

check('B2 干净路径必须安装定时器（证明 B1 不是"永远取消"）', installed === 1,
  `setInterval=${installed}`)
check('B3 卸载必须清掉定时器本身', installed === 1 && cleared === 1,
  `clearInterval=${cleared}`)

globalThis.setInterval = realSetInterval
globalThis.clearInterval = realClearInterval

/* ------------------------------------------------------------------ */

const failed = results.filter((r) => !r.ok)
console.log(`\n${results.length - failed.length}/${results.length} assertions passed`)
if (failed.length > 0) process.exit(1)
