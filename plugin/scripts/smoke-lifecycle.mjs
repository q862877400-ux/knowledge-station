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
import { registerKsAnnounceRoutes } from '../src/announce.js'
import {
  __resetInspectionForTests,
  inspectionStartupCheck,
  registerKsInspectionRoutes,
} from '../src/inspection.js'

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
// ⚠ 先复位模块内存态：状态是**模块级缓存**的，A 段/上一次运行留下的 `_state` 会让这里的
//   fixture **完全不生效**（B4 第一版就踩了这个：fixture 写了，`reached=false`）。
__resetInspectionForTests()
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

/* ------------------------------------------------------------------ *
 * B4 跨模块回装：收尾的**最后一个** await 之后也要作废
 * ------------------------------------------------------------------ *
 * 独立复核（2026-09-19）拿可复现脚本指出的洞：`inspectionStartupCheck` 在
 * `await finalizeBatch(...)` **之后没有**代数比对，而 `finalizeBatch` 的尾巴会
 * `void triggerAfterInspection(...)` → `announce.adoptScanPoll(...)`。
 * ⇒ 卸载若落在 `finalizeBatch` 自己的 await（拉 changes）窗口里，
 * **卸载后仍会装起一个公告扫描轮询**（复核实测：3 次扫描轮询 + 4 次 ensureLive）。
 *
 * 断言：卸载之后**不许**再向公告扫描端点发请求。用"卡住 changes 那次 fetch"把窗口
 * 做成确定性的——不靠 sleep 抢时序。
 */

const announceCtx = {
  webServer: { register: () => () => {} },
  logger: { info() {}, warn() {}, error() {} },
}

// B4 也要自己的干净起点（`__resetInspectionForTests` 同时把代数 +1，让 B1/B2 的残留失效）。
__resetInspectionForTests()
await writeFile(join(dataDir, 'ks-inspection.json'), JSON.stringify({
  // running + 引擎回"终态" ⇒ 启动检查会走到 `await finalizeBatch(...)`
  last: { batch_id: 'batch-smoke-B4', status: 'running', total: 1 },
  stale_run: false,
}, null, 2), 'utf8')

const SCAN_LAST_MARK = '/api/v1/update/announce-scan/last'
let summariesStarted = false
let releaseSummaries = null
let summariesGate = new Promise((resolve) => { releaseSummaries = resolve })
let scanProbes = 0
let scanProbesAfterDispose = 0
let disposedFlag = false

const realFetch2 = globalThis.fetch
globalThis.fetch = async (url) => {
  const u = String(url)
  const json = (body) => new Response(JSON.stringify(body), {
    status: 200, headers: { 'Content-Type': 'application/json' },
  })
  if (u.includes('/api/v1/update/batch/')) {
    // 上次那批已经终态 ⇒ 走 `TERMINAL.has(status)` 分支 → finalizeBatch
    return json({ code: 200, status: 'success', data: { status: 'done' } })
  }
  if (u.includes('/api/v1/update/changes')) {
    summariesStarted = true
    await summariesGate           // ← 故意卡在这里，让"卸载"落进这个窗口
    return json({ code: 200, status: 'success',
      data: { by_type: { new_version: 0, superseded: 0, withdrawn: 0, not_found: 0, no_change: 0 },
              by_class: { total: 0, unreadable: 0, classes: {} } } })
  }
  if (u.includes(SCAN_LAST_MARK)) {   // ⚠ 必须先判 `/last`：它是下面那条路径的前缀
    scanProbes += 1
    if (disposedFlag) scanProbesAfterDispose += 1
    // 终态 ⇒ 即使被装上轮询，它也会立刻收尾（不会让本冒烟挂着不退）
    return json({ code: 200, status: 'success', data: { status: 'done', scan_id: 'scan-smoke-B4' } })
  }
  if (u.endsWith('/announce-scan')) {
    // 巡检尾触发的 POST：回一个 scan_id ⇒ `adoptScanPoll`（真机上正常也会这样）
    return json({ code: 200, status: 'success',
      data: { status: 'started', scan_id: 'scan-smoke-B4' } })
  }
  return json({ code: 200, status: 'success', data: {} })
}

const disposeInspection4 = registerKsInspectionRoutes(webCtx, managerB)
const disposeAnnounce4 = registerKsAnnounceRoutes(announceCtx, managerB)
const pending4 = inspectionStartupCheck(webCtx, managerB)

// 等启动检查真的卡在 changes 那次 await 上（有界等待，不赌时序）
const reached = await waitFor(() => summariesStarted, 5000, 10)
disposedFlag = true
disposeInspection4()
disposeAnnounce4()
releaseSummaries()
await pending4
// 给被（错误地）装上的轮询一点时间去做它的第一次探测
await new Promise((resolve) => { setTimeout(resolve, 200) })

check('B4 卸载后不许再装跨模块轮询（finalize 尾巴的 triggerAfterInspection）',
  reached === true && scanProbesAfterDispose === 0,
  `reached=${reached} scanProbes=${scanProbes} afterDispose=${scanProbesAfterDispose}`)

/* B5 —— **正向对照**：同一场景**不卸载**时，必须真的探测公告扫描端点。
   没有这一条，B4 会被"把 stub 的 scan_id 去掉"骗过（复核 2026-09-19 实测：那样 B4 仍绿）：
   只断言"卸载后不许探测"的实现，在"根本不会探测"的假桩下也是绿的。 */
__resetInspectionForTests()
await writeFile(join(dataDir, 'ks-inspection.json'), JSON.stringify({
  last: { batch_id: 'batch-smoke-B5', status: 'running', total: 1 },
  stale_run: false,
}, null, 2), 'utf8')

summariesStarted = false
summariesGate = new Promise((resolve) => { releaseSummaries = resolve })
releaseSummaries()                      // B5 不需要卡住：让它一路走完
scanProbes = 0
disposedFlag = false

const disposeInspection5 = registerKsInspectionRoutes(webCtx, managerB)
const disposeAnnounce5 = registerKsAnnounceRoutes(announceCtx, managerB)
await inspectionStartupCheck(webCtx, managerB)
await waitFor(() => scanProbes > 0, 2000, 10)
const cleanProbes = scanProbes
disposeInspection5()                    // 清掉 B5 装上的 30s 定时器（否则进程不退出）
disposeAnnounce5()

check('B5 正向对照：不卸载时**必须**探测（证明 B4 不是"永远不探测"的假绿）',
  cleanProbes > 0, `scanProbes=${cleanProbes}`)

globalThis.fetch = realFetch2


/* ------------------------------------------------------------------ *
 * C/D 共用的最小 req/res 桩（`readJsonBody` 只用到 req 的 on('data'|'end'|'error')）。
 * ⚠ 放在**模块作用域**：C 段与 D 段都要用，而块作用域里的 `const` 另一块取不到
 *   （第一版我把它们写在 C 里，D 一跑就 `ReferenceError: fakeRes is not defined`）。
 * ------------------------------------------------------------------ */
const _emitter = await import('node:events')
const fakeReq = (method, body) => {
  const req = new _emitter.EventEmitter()
  req.method = method
  req.url = '/ks/announce/ingest'
  if (body !== undefined) {
    const text = typeof body === 'string' ? body : JSON.stringify(body)
    queueMicrotask(() => {
      if (text) req.emit('data', Buffer.from(text, 'utf8'))
      req.emit('end')
    })
  } else {
    queueMicrotask(() => req.emit('end'))
  }
  return req
}
const fakeRes = () => {
  const res = new _emitter.EventEmitter()
  res.statusCode = 0
  res.headers = {}
  res.body = null
  res.writeHead = (code) => { res.statusCode = code; return res }
  res.end = (chunk) => { res.body = chunk === undefined ? '' : String(chunk); return res }
  return res
}

/* ------------------------------------------------------------------ *
 * C. 公告**正文入库**那两条路由（2026-09-24 切片②下半，开发史 §10.193）
 *
 * 为什么单独加这一组：这两条是**面向上线的新契约**（界面按它们取数与写入），而
 * "注册在哪个路径、POST 体怎么转、引擎路径常量写没写错"在别处**一条判据都没有**
 * （引擎侧有端点用例，但那是引擎的路由，不是 host 的代理）。这里用**真模块 + 桩 fetch**
 * 把代理这一段钉住：能抓住"常量写错/方法写错/体没转"这类改动。
 * ------------------------------------------------------------------ */

{
  const registered = []
  const recCtx = {
    webServer: {
      register: (route) => {
        registered.push(route)
        return () => {}
      },
    },
    logger: { info() {}, warn() {}, error() {} },
  }
  const disposeC = registerKsAnnounceRoutes(recCtx, managerB)
  const byPath = new Map(registered.map((r) => [r.path, r]))
  check('C1 入库两条路由都注册成了 exact 路径',
    byPath.get('/ks/announce/ingest')?.kind === 'exact'
    && byPath.get('/ks/announce/ingest/pending')?.kind === 'exact',
    registered.map((r) => `${r.kind} ${r.path}`).join(' | '))

  const engineCalls = []
  const realFetch3 = globalThis.fetch
  globalThis.fetch = async (url, init) => {
    engineCalls.push({ url: String(url), method: init?.method ?? 'GET', body: init?.body })
    if (String(url).includes('/announce-ingest/pending')) {
      return new Response(JSON.stringify({ code: 200, status: 'success',
        data: { total: 7, ingested: 5, pending: 2,
                pending_by_status: { effective: 1, reference: 1, withdrawn: 0 },
                skipped_non_normative: 0 } }),
      { status: 200, headers: { 'Content-Type': 'application/json' } })
    }
    return new Response(JSON.stringify({ code: 200, status: 'success',
      data: { tried: 1, ingested: 1, skipped: 0, failed: 0, pending_left: 0,
              stopped_early: false, stop_reason: null, items: [] } }),
    { status: 200, headers: { 'Content-Type': 'application/json' } })
  }

  const resGet = fakeRes()
  await byPath.get('/ks/announce/ingest/pending').handler(fakeReq('GET'), resGet)
  const gotGet = JSON.parse(resGet.body)
  /* ⚠ 判**路径全等**，不用 `url.includes(...)`（独立复核：把引擎路径常量
     `…/announce-ingest/pending` 改成 `…/pendingX` 时，子串判据仍然 PASS —— 后缀型手滑漏掉）。 */
  const enginePathOf = (u) => { try { return new URL(u).pathname } catch { return String(u) } }
  check('C2 GET pending 打到引擎的 pending 端点、值原样回给界面',
    engineCalls.length === 1
    && enginePathOf(engineCalls[0].url) === '/api/v1/update/announce-ingest/pending'
    && resGet.statusCode === 200 && gotGet.ok === true && gotGet.data.pending === 2,
    `${engineCalls[0]?.url} → ${resGet.statusCode} ${resGet.body}`)

  engineCalls.length = 0
  const resPost = fakeRes()
  await byPath.get('/ks/announce/ingest').handler(
    fakeReq('POST', { limit: 3, source_id: 'src_x', force: true }), resPost)
  const sent = engineCalls[0]?.body ? JSON.parse(engineCalls[0].body) : null
  check('C3 POST ingest 打到引擎的 ingest 端点、**请求体原样转**（limit/source_id/force）',
    engineCalls.length === 1
    && engineCalls[0].method === 'POST'
    && enginePathOf(engineCalls[0].url) === '/api/v1/update/announce-ingest'
    && sent?.limit === 3 && sent?.source_id === 'src_x' && sent?.force === true,
    `${engineCalls[0]?.url} body=${engineCalls[0]?.body}`)

  // 反向：非法 JSON 必须 400（**不许**把它当空体转下去 —— 那会把 limit 悄悄变成默认值）
  engineCalls.length = 0
  const resBad = fakeRes()
  await byPath.get('/ks/announce/ingest').handler(fakeReq('POST', '{不是 JSON'), resBad)
  check('C4 非法 JSON ⇒ 400 且一个字节都不往引擎转',
    resBad.statusCode === 400 && engineCalls.length === 0,
    `${resBad.statusCode} engineCalls=${engineCalls.length}`)

  // 方法纪律：GET 打 ingest（写路径）必须 405
  const resMethod = fakeRes()
  await byPath.get('/ks/announce/ingest').handler(fakeReq('GET'), resMethod)
  check('C5 GET /ks/announce/ingest ⇒ 405（写路径不许被 GET 触发）',
    resMethod.statusCode === 405 && engineCalls.length === 0, String(resMethod.statusCode))

  /* C6–C8（2026-09-24）：两条**只读**出口 —— 此前有引擎端点、界面完全没接（= 白做）。
     钉三件事：① 路由注册成 exact；② 打到**路径全等**的引擎端点且值原样回；
     ③ POST 打只读口 ⇒ 405（不许"只读口能写"）。 */
  check('C6 两条只读出口都注册成了 exact 路径',
    byPath.get('/ks/announce/ingest/triage')?.kind === 'exact'
    && byPath.get('/ks/announce/change-signals')?.kind === 'exact',
    registered.map((r) => `${r.kind} ${r.path}`).join(' | '))

  engineCalls.length = 0
  globalThis.fetch = async (url, init) => {
    engineCalls.push({ url: String(url), method: init?.method ?? 'GET', body: init?.body })
    const p = enginePathOf(String(url))
    if (p === '/api/v1/update/announce-ingest/triage') {
      return new Response(JSON.stringify({ code: 200, status: 'success',
        data: { total: 3, counts: { clear: 1, review: 1, keep: 1 },
                items: [{ title: 'A', verdict: 'clear', confidence: 0.97 },
                        { title: 'B', verdict: 'review', confidence: 0.82 },
                        { title: 'C', verdict: 'keep', confidence: 0.4 }] } }),
      { status: 200, headers: { 'Content-Type': 'application/json' } })
    }
    if (p === '/api/v1/laws/change-signals') {
      return new Response(JSON.stringify({ code: 200, status: 'success',
        data: { count: 55, by_signal: { draft: 16, issued: 28, repealed: 4, revised: 7 },
                items: [{ doc_id: 'd1', standard_no: 'X', change_signal: 'repealed' }] } }),
      { status: 200, headers: { 'Content-Type': 'application/json' } })
    }
    return new Response(JSON.stringify({ code: 500, status: 'error', error: 'unexpected',
      message: p }), { status: 500, headers: { 'Content-Type': 'application/json' } })
  }
  const resTri = fakeRes()
  await byPath.get('/ks/announce/ingest/triage').handler(fakeReq('GET'), resTri)
  const gotTri = JSON.parse(resTri.body)
  const resSig = fakeRes()
  await byPath.get('/ks/announce/change-signals').handler(fakeReq('GET'), resSig)
  const gotSig = JSON.parse(resSig.body)
  check('C7 两条只读出口打到**路径全等**的引擎端点、值原样回给界面',
    engineCalls.length === 2
    && enginePathOf(engineCalls[0].url) === '/api/v1/update/announce-ingest/triage'
    && enginePathOf(engineCalls[1].url) === '/api/v1/laws/change-signals'
    && resTri.statusCode === 200 && gotTri.ok === true && gotTri.data.counts?.review === 1
    && resSig.statusCode === 200 && gotSig.ok === true && gotSig.data.count === 55,
    `${engineCalls.map((c) => enginePathOf(c.url)).join(' , ')}`
    + ` ⇒ ${resTri.statusCode} ${resTri.body} / ${resSig.statusCode} ${resSig.body}`)

  engineCalls.length = 0
  const resReadOnly = fakeRes()
  await byPath.get('/ks/announce/ingest/triage').handler(fakeReq('POST', {}), resReadOnly)
  check('C8 POST 打只读口 ⇒ 405 且一个字节都不往引擎转',
    resReadOnly.statusCode === 405 && engineCalls.length === 0,
    `${resReadOnly.statusCode} engineCalls=${engineCalls.length}`)

  // C9（2026-09-24 真机量测后加）：triage 的**超时与条数上限是一对**，必须成对成立。
  //   实测 0.46s/条（真库 125 条 = 57.6s）⇒ 我第一版给 30s 超时**必然白等 30s 才失败**。
  //   这条钉住"引擎上限 × 单条耗时 ≤ host 超时"，改一边不改另一边就会红。
  //   ⚠ 仓库根从**本文件位置**推（`../..`），不写死绝对路径——提取树里也必须能读。
  {
    const { fileURLToPath: toPath } = await import('node:url')
    const { dirname } = await import('node:path')
    const here = dirname(toPath(import.meta.url))              // …/plugin/scripts
    const repoOfPlugin = join(here, '..', '..')                 // 仓库根（scripts → plugin → 根）
    const src = await readFile(join(repoOfPlugin, 'src', 'core', 'update', 'web_ingest.py'), 'utf8')
    const m = src.match(/min\(int\(limit or \d+\), (\d+)\)/)
    const cap = m ? Number(m[1]) : 0
    const PER_ITEM_S = 0.46          // 实测值（var/tmp/measure-triage-latency.py）
    const hostSrc = await readFile(join(here, '..', 'src', 'announce.js'), 'utf8')
    const t = hostSrc.match(/probeRead[\s\S]{0,900}?timeoutMs: ([\d_]+)/)
    const timeoutS = t ? Number(t[1].replace(/_/g, '')) / 1000 : 0
    // ⚠⚠ **两边必须同单位**（秒 vs 毫秒）——第一版拿"秒"去比"毫秒"，
    //   300×0.46×1.2=165.6 ≤ 30000 恒成立 ⇒ 这条判据**恒真**，改超时它也不红
    //   （2026-09-24 实测：把 180_000 改回 30_000，C9 照样 PASS，当场识破）。
    const needS = cap * PER_ITEM_S * 1.2
    check('C9 triage 超时与条数上限**成对**（上限 × 实测单条耗时 × 1.2 ≤ 超时，**秒对秒**）',
      cap > 0 && timeoutS > 0 && needS <= timeoutS,
      `上限 ${cap} 条 × ${PER_ITEM_S}s × 1.2 = ${needS.toFixed(0)}s vs host 超时 ${timeoutS}s`)
  }

  globalThis.fetch = realFetch3
  disposeC()
}


/* ------------------------------------------------------------------ *
 * D. 扫描收尾的**自动入库**（2026-09-24 §10.194）
 *
 * 这是**无人值守**也会跑的一步（每天巡检尾 → 扫描 → 入库），所以必须有判据：
 *   ① 扫描成功收尾 ⇒ **确实**发了一次入库请求，且请求体是 `{limit: 20}`；
 *   ② 入库结果**落进状态文件**（`last.ingest`，界面读它显示"上次自动入了几条"）；
 *   ③ 开关关掉 ⇒ **一次都不发**（反向对照：只断言①会被"永远入库"的实现骗过，
 *      只断言③会被"永远不入库"骗过 —— 两条都要）；
 *   ④ 引擎报错 ⇒ 如实写 `{error}`，**不许静默**（这条最容易假绿：静默失败看起来"没坏"）。
 * ------------------------------------------------------------------ */

{
  const { announceFilePath } = await import('../src/announce.js')

  /* D 段自己注册一套路由到**记录式 ctx**（C 段的 `registered` 在 C 的块作用域里，取不到 ——
     我第一版就写错在这儿）。这样 D 也能顺带再核一遍"入库相关路由确实注册了"。 */
  const dRoutes = []
  const dCtx = {
    webServer: {
      register: (route) => {
        dRoutes.push(route)
        return () => {}
      },
    },
    logger: { info() {}, warn() {}, error() {} },
  }
  const disposeD = registerKsAnnounceRoutes(dCtx, managerB)
  const registered = dRoutes
  const realFetch4 = globalThis.fetch
  let ingestCalls = []
  /** 桩：扫描启动 → 状态查询 → 最近公告 → 入库。 */
  const stubFor = (ingestBody, ingestHttp = 200) => async (url, init) => {
    const u = String(url)
    const json = (body, http = 200) => new Response(JSON.stringify(body),
      { status: http, headers: { 'Content-Type': 'application/json' } })
    if (u.endsWith('/api/v1/update/announce-scan')) {
      return json({ code: 200, status: 'success', data: { status: 'started', scan_id: 'scan-D' } })
    }
    if (u.includes('/announce-scan/last')) {
      return json({ code: 200, status: 'success',
        data: { scan_id: 'scan-D', status: 'done', new_count: 2, items_seen: 3,
                sources_total: 1, sources_done: 1, per_source: [], recent: [] } })
    }
    if (u.includes('/announce-items')) {
      return json({ code: 200, status: 'success', data: { items: [], total: 0 } })
    }
    if (u.endsWith('/api/v1/update/announce-ingest')) {
      ingestCalls.push({ url: u, body: init?.body ?? null, method: init?.method ?? 'GET' })
      return ingestHttp === 200
        ? json({ code: 200, status: 'success', data: ingestBody })
        : json({ code: 500, status: 'error', message: 'boom' }, 500)
    }
    return json({ code: 200, status: 'success', data: {} })
  }

  /* 驱动方式说明：**不用** `announceStartupCheck`（它的语义是"引擎说同一个扫描还在跑才接管"，
     我的桩说 done ⇒ 它按设计标 stale_run、不接管 ⇒ 根本走不到入库那一步；我第一版就这么写错的）。
     改用真路由 `POST /ks/announce/scan` → `adoptScanPoll` → 终态 → 自动入库尾巴。 */
  const scanRoute = registered.find((r) => r.path === '/ks/announce/scan')
  const autoRoute = registered.find((r) => r.path === '/ks/announce/auto-ingest')
  const drive = async () => {
    const res = fakeRes()
    await scanRoute.handler(fakeReq('POST', {}), res)
    // 轮询是 fire-and-forget：等它把入库那一步做完
    await waitFor(() => ingestCalls.length > 0, 6000, 20)
    return res
  }

  // ①② 开着（默认就是开）⇒ 发一次、请求体对、结果落盘
  ingestCalls = []
  globalThis.fetch = stubFor({ tried: 3, ingested: 2, skipped: 1, failed: 0,
    by_status: { effective: 1, reference: 1, withdrawn: 0 }, pending_left: 4,
    stopped_early: true })
  await drive()
  const sentD = ingestCalls[0]?.body ? JSON.parse(ingestCalls[0].body) : null
  check('D1 扫描成功后**确实**自动入库一次，请求体是 {limit: 20}',
    ingestCalls.length === 1 && ingestCalls[0].method === 'POST' && sentD?.limit === 20,
    `calls=${ingestCalls.length} body=${ingestCalls[0]?.body}`)
  const stD = JSON.parse(await readFile(announceFilePath(), 'utf8'))
  check('D2 自动入库的结果落进状态文件（界面靠它显示"上次自动入了几条"）',
    stD.last?.ingest?.ingested === 2 && stD.last?.ingest?.pending_left === 4
    && stD.last?.ingest?.by_status?.reference === 1,
    JSON.stringify(stD.last?.ingest))

  // ③ 关掉 ⇒ 一次都不发（反向对照）
  const resOff = fakeRes()
  await autoRoute.handler(fakeReq('POST', { enabled: false }), resOff)
  check('D3a 开关路由能写状态（关）',
    resOff.statusCode === 200 && JSON.parse(resOff.body).data.auto_ingest === false,
    `${resOff.statusCode} ${resOff.body}`)
  ingestCalls = []
  globalThis.fetch = stubFor({ tried: 0, ingested: 0, skipped: 0, failed: 0,
    by_status: { effective: 0, reference: 0, withdrawn: 0 }, pending_left: 0,
    stopped_early: false })
  await drive()
  await new Promise((resolve) => { setTimeout(resolve, 400) })
  check('D3b 开关关掉 ⇒ **一次都不发**（反向对照，防"永远入库"的实现）',
    ingestCalls.length === 0, `calls=${ingestCalls.length}`)

  // ④ 再开回来 + 引擎报错 ⇒ 如实留痕，不静默
  const resOn = fakeRes()
  await autoRoute.handler(fakeReq('POST', { enabled: true }), resOn)
  ingestCalls = []
  globalThis.fetch = stubFor(null, 500)
  await drive()
  await new Promise((resolve) => { setTimeout(resolve, 300) })
  const stD4 = JSON.parse(await readFile(announceFilePath(), 'utf8'))
  check('D4 自动入库失败 ⇒ 状态文件里留 error（**不许静默**）',
    typeof stD4.last?.ingest?.error === 'string' && stD4.last.ingest.error.includes('500'),
    JSON.stringify(stD4.last?.ingest))

  globalThis.fetch = realFetch4
  disposeD()

  /* D5/D6 —— **新进程**里判"开关是从磁盘读的"（这一条 D3b 判不到）：
     D3b 走的是"内存里已被路由改成 false"；真正的风险是**重启之后第一次扫描** ——
     那时内存是空的，若实现读的是"内存默认值（开）"，业主明明关了也会照旧入库。
     ⇒ 起两个子进程（各自全新模块状态、同一个临时数据目录），只换 `ks-announce.json` 里的
       `auto_ingest`，数入库请求：false 必须 0 次、true 必须 1 次（正向对照）。
     ⚠ 子进程用**导出的** `triggerAfterInspection` 驱动（那条链的正式入口），不复制 host 内部实现。 */
  const { spawnSync } = await import('node:child_process')
  const { pathToFileURL } = await import('node:url')
  const announceUrl = pathToFileURL(join(import.meta.dirname, '..', 'src', 'announce.js')).href
  const childCode = `
    const calls = []
    globalThis.fetch = async (url) => {
      const u = String(url)
      const json = (b) => new Response(JSON.stringify(b),
        { status: 200, headers: { 'Content-Type': 'application/json' } })
      if (u.endsWith('/api/v1/update/announce-scan')) {
        return json({ code: 200, status: 'success', data: { status: 'started', scan_id: 'scan-child' } })
      }
      if (u.includes('/announce-scan/last')) {
        return json({ code: 200, status: 'success',
          data: { scan_id: 'scan-child', status: 'done', new_count: 1, items_seen: 1,
                  sources_total: 1, sources_done: 1, per_source: [], recent: [] } })
      }
      if (u.includes('/announce-items')) {
        return json({ code: 200, status: 'success', data: { items: [], total: 0 } })
      }
      if (u.endsWith('/api/v1/update/announce-ingest')) {
        calls.push(u)
        return json({ code: 200, status: 'success', data: { tried: 1, ingested: 1, skipped: 0,
          failed: 0, by_status: { effective: 1, reference: 0, withdrawn: 0 }, pending_left: 0,
          stopped_early: false } })
      }
      return json({ code: 200, status: 'success', data: {} })
    }
    const m = await import(${JSON.stringify(announceUrl)})
    const ctx = { webServer: { register: () => () => {} },
                  logger: { info() {}, warn() {}, error() {} } }
    const manager = { ensureLive: async () => ({ port: 65002, token: 'child' }),
                      touchActivity() {} }
    await m.triggerAfterInspection(ctx, manager)
    await new Promise((r) => setTimeout(r, 900))
    console.log('INGEST_CALLS=' + calls.length)
  `
  const runChild = async (auto) => {
    await writeFile(announceFilePath(), JSON.stringify({
      last: null, stale_run: false, auto_ingest: auto,
    }, null, 2), 'utf8')
    const r = spawnSync(process.execPath, ['--input-type=module', '-e', childCode],
      { env: { ...process.env }, encoding: 'utf8' })
    const m = /INGEST_CALLS=(\d+)/.exec(r.stdout ?? '')
    return { n: m ? Number(m[1]) : -1, err: (r.stderr ?? '').slice(-300) }
  }
  const off = await runChild(false)
  const on = await runChild(true)
  check('D5 新进程 + 磁盘上开关=关 ⇒ 一次都不入库（重启后第一次扫描也守规矩）',
    off.n === 0, `calls=${off.n} ${off.err}`)
  check('D6 正向对照：新进程 + 磁盘上开关=开 ⇒ 确实入库一次（证明 D5 不是"永远不入库"）',
    on.n === 1, `calls=${on.n} ${on.err}`)
}


/* ------------------------------------------------------------------ */

const failed = results.filter((r) => !r.ok)
console.log(`\n${results.length - failed.length}/${results.length} assertions passed`)
if (failed.length > 0) process.exit(1)
