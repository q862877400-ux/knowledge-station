/**
 * ks-dsh-plugin — scripts/smoke-cancel.mjs
 *
 * 第 6 步 §4「取消与内层超时必须可分辨 + 加过的监听必须摘干净」的**离线**冒烟。
 * 施工单 [docs/research/STEP6-WORKORDER.md](../../docs/research/STEP6-WORKORDER.md) §4。
 *
 * 这个脚本**同时是复现器**：改前跑它，D1/D2/D3/D5/D6 是红的（红本身就是要留的证据）；
 * 改到全绿才算修完。施工单 §4 风险 1 的纪律：**先写红断言，再改实现**。
 *
 * 覆盖（断言名与施工单 §4「怎么验」表对齐）：
 *   D1  combineSignals 摘掉自己加的监听（假 signal 台账 + 真实 signal 的 getEventListeners 双证）
 *   D2  调用方取消 ⇒ 文案含 cancel、不含 timed out（apiGet / apiGetBytes / apiPost 三条路径）
 *   D3  内层 timeoutMs 到点、调用方未取消 ⇒ 文案含 timed out、不含 cancel（同三条路径）
 *   D4  真 abort 到得了 fetch：传进 fetch 的 signal 在调用方 abort 后 aborted === true
 *   D5  一次调用结束后不留监听（三次完整 apiGet 周期净增 = 0）
 *   D6  调用方 signal 早已 abort ⇒ **一次都不碰 fetch**，立刻回 status 0
 *
 * 完全离线：`globalThis.fetch` 被打桩（只观察 signal、按真实 fetch 的语义以
 * `signal.reason` reject），不发任何网络请求、不起引擎、不碰用户数据目录。
 *
 * ## ⚠ 工单实测更正（A 批，就地留痕；错话保留、不悄悄删）
 * 施工单 §4「我们现状」那条括号里写：`apiGet` 的 `finally`（`signal.removeEventListener`）
 * 摘的是"**别人加到我们身上的**"，**不是**"我们加到 caller 身上的"——
 * **这句实测不成立，是错的**。`apiGet`/`apiGetBytes`/`apiPost` 加在 caller signal 上的就是
 * `onAbort`，`finally` 摘的正是它，所以**这三条传输路径本来就是不泄漏的**：
 * 改前本文件 D5 就已经是 `added=3 removed=3`（这条对照断言因此**空转**，如实标出）。
 * ⇒ 监听泄漏**真实存在但只在一个地方：`combineSignals`**（改前 D1：`a=1/0 b=1/0`，
 * 真实 signal 上残留 1 个监听）。4B-1 因此仍必须做（它是签名变更 + `dispose`），
 * 但它的**收益位置**与工单那句话指的不是同一处。4B-2（可分辨）不受影响。
 *
 * Run: node scripts/smoke-cancel.mjs   (exit 0 = all checks pass)
 */
import { getEventListeners } from 'node:events'
import { mkdtemp } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

// 引擎会话文件落点隔离（engine.js 在 import 期只算路径，不读文件；这行是保险）。
process.env.KS_DATA_DIR = await mkdtemp(join(tmpdir(), 'ks-cancel-smoke-'))

// 命名空间导入（不是解构）：改前 `describeTransportFailure` 还不存在，这个脚本仍要能
// **跑到底并给出红的证据**，而不是 import 期就炸掉（那就没有"改前"的证据了）。
const engine = await import(new URL('../src/engine.js', import.meta.url).href)
const { combineSignals, apiGet, apiGetBytes, apiPost } = engine

// 看门狗：任何一条路径若忘了武装超时，这里 30s 后收摊，不让冒烟挂死。
const watchdog = setTimeout(() => {
  console.log('\n== cancel smoke FAIL (watchdog: a transport call never settled) ==')
  process.exit(3)
}, 30_000)

const results = []
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}

/* ------------------------------------------------------------------ *
 * 打桩 fetch：只观察 signal，并以真实 fetch 的语义(以 signal.reason reject)结束。
 * Node 的 fetch 在 signal abort 后 reject 的就是 signal.reason——这里逐字复刻，
 * 所以"两条路 error.message 完全相同"这件事是真复现，不是桩造成的假象。
 * ------------------------------------------------------------------ */
const realFetch = globalThis.fetch
let fetchCalls = []
globalThis.fetch = (url, opts = {}) => {
  const signal = opts.signal
  fetchCalls.push({ url: String(url), signal })
  return new Promise((_resolve, reject) => {
    const fail = () => reject(
      signal && signal.reason !== undefined
        ? signal.reason
        : new DOMException('This operation was aborted', 'AbortError'),
    )
    if (!signal) return                    // 无 signal：按"永不 settle"处理（本模块从不这样调）
    if (signal.aborted) { fail(); return }
    signal.addEventListener('abort', fail, { once: true })
  })
}

/** 一个**会计账**的 signal：包住真 AbortController，记录被加/摘了几次监听。 */
function countingSignal() {
  const inner = new AbortController()
  const ledger = { added: 0, removed: 0 }
  const wrapper = {
    get aborted() { return inner.signal.aborted },
    get reason() { return inner.signal.reason },
    get ledger() { return ledger },
    addEventListener(type, fn, opts) {
      if (type === 'abort') ledger.added += 1
      return inner.signal.addEventListener(type, fn, opts)
    },
    removeEventListener(type, fn) {
      if (type === 'abort') ledger.removed += 1
      return inner.signal.removeEventListener(type, fn)
    },
    abort(reason) { inner.abort(reason) },
  }
  return wrapper
}

/** `combineSignals` 新旧两种返回形状都吃得下（改前=裸 signal，改后={signal,dispose}）。 */
function unwrap(combined) {
  const isObj = combined !== null && typeof combined === 'object' && 'signal' in combined
  return {
    signal: isObj ? combined.signal : combined,
    dispose: isObj && typeof combined.dispose === 'function' ? combined.dispose : null,
  }
}

const tick = () => new Promise((r) => setTimeout(r, 0))
const BASE = 'http://127.0.0.1:9'      // 端口 9（discard）——fetch 被打桩，永不真连

/* ==================================================== D1 监听必须摘干净 */
{
  const a = countingSignal()
  const b = countingSignal()
  const real = new AbortController()
  const combined = combineSignals(a, b, real.signal)
  const { signal, dispose } = unwrap(combined)

  check('D1.0 fuse still aborts (sanity)', signal !== undefined)

  if (dispose) { dispose(); dispose() }   // 第二次必须是幂等空操作

  check('D1.1 fake signal ledger symmetric (added === removed)',
    a.ledger.added === a.ledger.removed && b.ledger.added === b.ledger.removed,
    `a=${a.ledger.added}/${a.ledger.removed} b=${b.ledger.added}/${b.ledger.removed}`)
  const left = getEventListeners(real.signal, 'abort').length
  check('D1.2 real signal holds no abort listener after dispose', left === 0, `listeners=${left}`)
  check('D1.3 dispose is idempotent (double dispose does not double-remove)',
    a.ledger.removed <= 1, `a.removed=${a.ledger.removed}`)
}
{
  // 反向：融合本身必须还真能用（防"dispose 太早把融合摘死"）
  const a = countingSignal()
  const b = countingSignal()
  const { signal, dispose } = unwrap(combineSignals(a, b))
  let aborted = false
  signal.addEventListener('abort', () => { aborted = true }, { once: true })
  a.abort()
  await tick()
  check('D1.4 any input still aborts the fusion', aborted === true && signal.aborted === true)
  if (dispose) dispose()
}

/* ==================================================== D2/D3 两条路必须可分辨 */
/** 三条传输路径共用的形状探针（每条都跑一遍"调用方取消"与"内层超时"）。 */
const TRANSPORTS = [
  { name: 'apiGet', fn: (base, opts) => apiGet(base, '/x', opts) },
  { name: 'apiGetBytes', fn: (base, opts) => apiGetBytes(base, '/x', opts) },
  { name: 'apiPost', fn: (base, opts) => apiPost(base, '/x', opts) },
]

for (const t of TRANSPORTS) {
  // D2：调用方取消（内层 30s 远未到点）
  const ctrl = new AbortController()
  const pending = t.fn(BASE, { signal: ctrl.signal, timeoutMs: 30_000 })
  await tick()
  ctrl.abort()
  const cancelled = await pending
  const cText = String(cancelled.error ?? '')
  check(`D2 ${t.name}: caller cancel reads as cancelled`,
    cText.includes('cancel') && !cText.includes('timed out'),
    `error=${JSON.stringify(cText)} code=${cancelled.error_code}`)

  // D3：内层超时（没有调用方 signal）
  const timed = await t.fn(BASE, { timeoutMs: 30 })
  const tText = String(timed.error ?? '')
  check(`D3 ${t.name}: inner timeout reads as timed out`,
    tText.includes('timed out') && !tText.includes('cancel'),
    `error=${JSON.stringify(tText)} code=${timed.error_code}`)

  check(`D2/D3 ${t.name}: the two are distinguishable`,
    cancelled.error_code !== undefined && timed.error_code !== undefined
      && cancelled.error_code !== timed.error_code,
    `${cancelled.error_code} vs ${timed.error_code}`)
  check(`D2/D3 ${t.name}: both still fail closed (status 0)`,
    cancelled.status === 0 && timed.status === 0)
}

/* ==================================================== D4 真 abort 到得了 fetch */
{
  fetchCalls = []
  const ctrl = new AbortController()
  const pending = apiGet(BASE, '/x', { signal: ctrl.signal, timeoutMs: 30_000 })
  await tick()
  const seen = fetchCalls.at(-1)?.signal
  ctrl.abort()
  await pending
  check('D4 apiGet hands fetch a signal wired to the caller',
    seen !== undefined && seen.aborted === true, `aborted=${seen?.aborted}`)
}
{
  // 走过的正是 index.js:372 那条真实组合路径（签名变更后"漏改调用点"的守门断言）
  fetchCalls = []
  const caller = new AbortController()
  const fused = unwrap(combineSignals(caller.signal, AbortSignal.timeout(30_000)))
  const pending = apiGet(BASE, '/x', { signal: fused.signal, timeoutMs: 30_000 })
  await tick()
  const seen = fetchCalls.at(-1)?.signal
  caller.abort()
  const r = await pending
  if (fused.dispose) fused.dispose()
  check('D4b fused signal (combineSignals(...).signal) reaches fetch',
    seen !== undefined && seen.aborted === true, `aborted=${seen?.aborted}`)
  check('D4b caller cancel through the fuse is distinguishable',
    String(r.error ?? '').includes('cancel'), `error=${JSON.stringify(String(r.error ?? ''))}`)
}

/* ==================================================== D5 结算后净增监听 = 0 */
{
  const c = countingSignal()
  for (let i = 0; i < 3; i += 1) {
    await apiGet(BASE, '/x', { signal: c, timeoutMs: 20 })
  }
  check('D5 no listener survives a settled call (3 cycles)',
    c.ledger.added === c.ledger.removed,
    `added=${c.ledger.added} removed=${c.ledger.removed}`)
}

/* ==================================================== D6 早已 abort 的调用方 */
{
  fetchCalls = []
  const ctrl = new AbortController()
  ctrl.abort()
  const r = await apiGet(BASE, '/x', { signal: ctrl.signal, timeoutMs: 5000 })
  check('D6 pre-aborted caller never reaches fetch',
    fetchCalls.length === 0 && r.status === 0,
    `fetchCalls=${fetchCalls.length} status=${r.status} error=${JSON.stringify(String(r.error ?? ''))}`)
}

/* ==================================================== D7/D8 共享 ensureLive 不被一个调用方拖垮
 * 这一段是第 6 步 §3（isConcurrencySafe）的**前置条件**的证据：并行之后，同轮两条工具调用
 * 会共享同一段探活/spawn；若那段的命运绑在"第一个调用方"的 signal 上，一个被取消就**连坐**。
 * 复现/验证方式：让 spawnEngine 停在一个可控的 promise 上，取消第一个调用方，再看
 * ①它是否被如实告知"cancelled"②共享的那段工作是否**还活着**③另一个调用方是否照样拿到引擎。
 * ------------------------------------------------------------------ */
{
  const m = new engine.EngineManager({})
  let release
  let spawnCalls = 0
  m.spawnEngine = async () => {
    spawnCalls += 1
    await new Promise((r) => { release = r })
    return { port: 48010, token: 'tok', pid: 1, spawnedByUs: true }
  }
  const ctrl = new AbortController()
  const first = m.ensureLive(ctrl.signal)     // 调用方 A：带着自己的 signal（例如 timeout-policy 装的那条）
  const sibling = m.ensureLive()              // 调用方 B：同轮另一条工具调用（无 signal）
  await tick(); await tick()                  // 让 readSessionFile → spawnEngine 真的起来
  check('D7.0 one shared spawn for both callers', spawnCalls === 1, `spawnCalls=${spawnCalls}`)
  ctrl.abort()                                 // A 被取消
  const aErr = await first.then(() => null, (e) => e)
  check('D7.1 the cancelled caller is told "cancelled"',
    String(aErr?.message ?? '').includes('cancel'), `message=${JSON.stringify(String(aErr?.message ?? ''))}`)
  check('D7.2 the shared spawn is NOT cancelled by that caller',
    m._spawnAbort !== null && m._spawnAbort.signal.aborted === false,
    `internalAborted=${m._spawnAbort?.signal.aborted}`)
  release()
  const s = await sibling
  check('D7.3 the sibling caller still gets the engine', s.port === 48010)
}
{
  // D8：调用方**早已**取消 ⇒ 立刻拒（但仍不阻止引擎起来——那是 §4B-3 的有意取舍）
  const m = new engine.EngineManager({})
  let release
  m.spawnEngine = async () => {
    await new Promise((r) => { release = r })
    return { port: 48011, token: 'tok', pid: 2, spawnedByUs: true }
  }
  const ctrl = new AbortController()
  ctrl.abort()
  const err = await m.ensureLive(ctrl.signal).then(() => null, (e) => e)
  check('D8 pre-aborted caller rejects as cancelled',
    String(err?.message ?? '').includes('cancel'), `message=${JSON.stringify(String(err?.message ?? ''))}`)
  await tick(); await tick()   // 拒的是"等的人"；底下那段 spawn 仍要真起来（有意取舍）
  check('D8 the cold start still runs for nobody (documented tradeoff)',
    typeof release === 'function')
  if (typeof release === 'function') release()
  await tick(); await tick()
  check('D8 the internal spawn settles cleanly', m._spawning === null,
    `spawning=${m._spawning === null ? 'settled' : 'still pending'}`)
}

/* ==================================================== 纯函数分流（防"文案靠猜"） */
{
  const d = engine.describeTransportFailure
  const has = typeof d === 'function'
  check('describeTransportFailure exists (exported, testable)', has)
  check('describeTransportFailure: caller cancel wins',
    has && d(new Error('This operation was aborted'), { callerAborted: true }) === 'the call was cancelled')
  check('describeTransportFailure: inner timeout',
    has && d(new Error('This operation was aborted'), { timedOut: true }) === 'the request timed out')
  check('describeTransportFailure: real transport error is preserved',
    has && d(new Error('fetch failed: ECONNREFUSED'), {}) === 'fetch failed: ECONNREFUSED')
}

globalThis.fetch = realFetch
clearTimeout(watchdog)

/* ==================================================== 汇总 */
const failed = results.filter((r) => !r.ok)
console.log(`\n== cancel smoke ${failed.length === 0 ? 'PASS' : 'FAIL'} ` +
  `(${results.length - failed.length}/${results.length}) ==`)
if (failed.length > 0) console.log(`FAILED: ${failed.map((f) => f.name).join(' | ')}`)
process.exit(failed.length === 0 ? 0 : 1)
