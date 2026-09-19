/**
 * ks-dsh-plugin — engine.js
 *
 * Node-side manager for the KnowledgeStation Python engine. It owns the
 * single-instance decision (read engine.session.json + probe /health), the
 * lazy spawn of `python -m src.core.main`, the bounded start-up poll, and the
 * cleanup that only ever kills an engine THIS manager spawned (never a
 * pre-existing healthy instance).
 *
 * This module only imports Node builtins — it never imports cordis or
 * dsh-* packages — so it is also loadable by the standalone smoke script
 * (scripts/smoke.mjs) without a DSH host.
 */

import { spawn, spawnSync } from 'node:child_process'
import { readFile, stat } from 'node:fs/promises'
import { join } from 'node:path'
import { homedir } from 'node:os'

/* ------------------------------------------------------------------ *
 * Constants (match the engine's own contract — do not edit the engine)
 * ------------------------------------------------------------------ */

/** Binds a random free port, writes session.json, prints PORT/TOKEN. */
export const MODULE_ARG = 'src.core.main'
export const ENGINE_ROOT = 'D:\\AI\\work space\\zcode'
export const DEFAULT_PYTHON = join(ENGINE_ROOT, '.venv', 'Scripts', 'python.exe')
export const HEALTH_PATH = '/api/v1/health'
/** P1b: synchronous forensic-answer endpoint (Bearer). */
export const KS_ANSWER_PATH = '/api/v1/ks/answer'

/** %APPDATA%\KnowledgeStation\engine.session.json */
export function sessionFilePath() {
  const root =
    process.env.KS_DATA_DIR ||
    join(process.env.APPDATA || join(homedir(), 'AppData', 'Roaming'), 'KnowledgeStation')
  return join(root, 'engine.session.json')
}

/** Resolve the python interpreter: $KS_PYTHON first, else the repo venv. */
export function resolvePythonPath() {
  return process.env.KS_PYTHON || DEFAULT_PYTHON
}

/* ------------------------------------------------------------------ *
 * Small helpers
 * ------------------------------------------------------------------ */

export function parseSession(raw) {
  let value = raw
  if (typeof raw === 'string') {
    try {
      value = JSON.parse(raw)
    } catch {
      return null
    }
  }
  if (!value || typeof value !== 'object') return null
  const port = Number(value.port)
  const pid = Number(value.pid)
  if (!Number.isInteger(port) || port <= 0 || !Number.isInteger(pid) || pid <= 0) return null
  if (typeof value.token !== 'string' || value.token.length === 0) return null
  return {
    port,
    token: value.token,
    pid,
    started_at: value.started_at ?? null,
  }
}

export async function readSessionFile() {
  const file = sessionFilePath()
  try {
    const raw = await readFile(file, 'utf8')
    return parseSession(raw)
  } catch {
    return null
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export function isProcessAlive(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return false
  // win32: query the single process by id (no taskkill /IM python.exe).
  const r = spawnSync('powershell.exe', [
    '-NoProfile',
    '-NonInteractive',
    '-Command',
    `Get-Process -Id ${pid} -ErrorAction SilentlyContinue`,
  ], { windowsHide: true, encoding: 'utf8' })
  // A live process prints one line to stdout; exit code is 0 in both cases
  // (we rely on the captured output, not the exit code).
  return (r.stdout ?? '').trim().length > 0
}

/**
 * Kill ONE process by its pid using `Stop-Process -Id` (the engine contract's
 * required teardown). Never uses taskkill /IM python.exe (would kill every
 * python). Returns true once the pid is gone / stop was requested.
 */
export function killPid(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return false
  const r = spawnSync('powershell.exe', [
    '-NoProfile',
    '-NonInteractive',
    '-Command',
    `Stop-Process -Id ${pid} -Force -ErrorAction SilentlyContinue`,
  ], { windowsHide: true, encoding: 'utf8' })
  return r.status === 0
}

/**
 * 合并多个 AbortSignal：任一 abort 即 abort。
 *
 * **为什么不用 `AbortSignal.any`**（2026-10，第 6 步 §4）：
 * ① 官方自己在**同位点**明确避开它——「Fuse caller and wrapper cancellation **without
 *    nesting `AbortSignal.any`**. Keeping the relay dispatch-scoped also removes listeners
 *    when work settles.」((DSH) `packages/core/tools/src/index.ts:1905-1908`)。
 *    理由正是本函数要解决的问题：`AbortSignal.any` 不给你一个"工作结束时把监听摘掉"的把手，
 *    而我们要（见下面的 `dispose`）。官方在别处确实用它（`agent-loop/src/index.ts:882`），
 *    两种都能用——判据是"要不要显式 dispose"，不是"必须换"。
 * ② 旧注释写的"不依赖它（Node 20.3+ 才有）"**已过期**：宿主下限是 Node 22.19
 *    ((DSH) 根 `package.json` engines)，本机实测 v26.7.0，`AbortSignal.any` 存在。
 *    那句话删掉了——留着一句不成立的理由比没有理由坏。
 *
 * **返回值是 `{ signal, dispose }`，不是裸 signal**（签名变更，3 个调用点同步改）：
 * 本函数往**输入的**每个 signal 上加了一个 abort 监听，只有调用方在结束时 `dispose()`
 * 才能把它们摘掉。旧实现返回裸 signal，于是"加进去的监听永不摘"——实测 added=1/removed=0
 * （见 `plugin/scripts/smoke-cancel.mjs` 的 D1）。`dispose` 幂等。
 *
 * 放在 engine.js 的理由（2026-09-17）：它服务于"给引擎调用配超时/取消"这件事，
 * 而各工具的 HTTP 调用都过本模块。原先它在 index.js 里，于是**任何**新工具模块
 * （如 materials.js）要么 import index.js 成环，要么靠"依赖注入"绕——两者都比
 * 把它放到唯一的自然归属地差。
 */
export function combineSignals(...signals) {
  const list = signals.filter((s) => s && typeof s.addEventListener === 'function')
  // 没有可合并的 / 只有一个：不需要中转控制器，`dispose` 是空操作。
  // （仍返回同一形状，避免调用点要分两种返回值处理——那正是"静默失效"的温床。）
  if (list.length === 0) return { signal: undefined, dispose() {} }
  if (list.length === 1) return { signal: list[0], dispose() {} }
  const controller = new AbortController()
  const onAbort = () => controller.abort()
  let attached = []
  for (const s of list) {
    if (s.aborted) {
      controller.abort()
      break
    }
    s.addEventListener('abort', onAbort, { once: true })
    attached.push(s)
  }
  let disposed = false
  const dispose = () => {
    if (disposed) return          // 幂等：重复 dispose 不许重复摘（计数会失真）
    disposed = true
    for (const s of attached) s.removeEventListener('abort', onAbort)
    attached = []
  }
  // 某个输入**进来就是 aborted** —— 我们没往任何 signal 上加监听（循环里 break 了），
  // 已经没有什么可摘；这里只是把状态收敛成"这次合并已经结束"。
  if (controller.signal.aborted) dispose()
  return { signal: controller.signal, dispose }
}

/**
 * 把一次传输层失败翻成人话，**并且让"调用方取消"与"我们内层超时"分得开**。
 *
 * 缺陷本体（第 6 步 §4 实测）：改前两条路都只回 `error.message`，而
 * `AbortController.abort()` 无 reason 时那个 message 就是
 * `This operation was aborted` —— 排障时**分不清"用户点了停止"和"引擎太慢"**。
 * 所以判据必须来自调用点的**局部事实**（`timedOut` 布尔 / caller signal 是否 aborted），
 * **不许**去 match `error.message`。文案照 WeKnora 的 `describeTransportFailure`
 * ((WK) `src/client.ts:331-337`) 的两种人话。
 *
 * 第三种（真传输错误，如 ECONNREFUSED）原样透出——不要把它也糊成"被取消"。
 */
export function describeTransportFailure(error, { callerAborted = false, timedOut = false } = {}) {
  if (callerAborted) return 'the call was cancelled'
  if (timedOut) return 'the request timed out'
  return error instanceof Error ? error.message : String(error)
}

/**
 * 一次传输调用的取消/超时管路：把**调用方的 signal** 与**我们自己的 `timeoutMs`**
 * 融到一个本函数独占的 controller 上，并给出 `dispose()`。
 *
 * 与 `combineSignals` 同样的"谁加谁摘"纪律：这里往调用方 signal 上加的监听，
 * `dispose()` 一定摘掉（`apiGet`/`apiGetBytes`/`apiPost` 的 `finally` 都调它）。
 */
function armTransportCall(signal, timeoutMs) {
  const attached = signal && typeof signal.addEventListener === 'function' ? signal : null
  const controller = new AbortController()
  let timedOut = false
  let callerAborted = !!(attached && attached.aborted)
  const onAbort = () => {
    callerAborted = true
    controller.abort(attached.reason)
  }
  if (attached && !callerAborted) attached.addEventListener('abort', onAbort, { once: true })
  const timer = setTimeout(() => {
    timedOut = true
    // 带上 reason：`error.name === 'TimeoutError'` 也能分流（文案之外的第二个判据）。
    controller.abort(new DOMException('the request timed out', 'TimeoutError'))
  }, timeoutMs)
  return {
    signal: controller.signal,
    /** 调用方**在开始之前**就已经取消了 —— 一根线都不用碰。 */
    preAborted: callerAborted,
    /** 把 catch 到的东西翻成 { status, ok, error, error_code? }（各 apiX 再并自己的字段）。 */
    failure(error) {
      const byCaller = callerAborted || !!(attached && attached.aborted)
      return {
        status: 0,
        ok: false,
        error: describeTransportFailure(error, { callerAborted: byCaller, timedOut }),
        // 机器可读的第二判据：改前这一格不存在，两条路在结构上无从区分。
        ...(byCaller ? { error_code: 'CANCELLED' }
          : timedOut ? { error_code: 'TIMEOUT' } : {}),
      }
    },
    dispose() {
      clearTimeout(timer)
      if (attached) attached.removeEventListener('abort', onAbort)
    },
  }
}

/**
 * 等 `promise`，但 `signal` 一 abort 就**停止等待**（不取消底下的工作）。
 * 每一条结算路径都摘掉自己加的监听（与 `combineSignals` 同款）。
 *
 * 为什么要"只影响等不等结果"：`ensureLive` 的 in-flight promise 是**多个调用方共享**的。
 * 旧写法把"第一个调用方"的 signal 交给整段探活/spawn（见 `ensureLive`），于是那一个
 * 调用方被取消会把**同轮并行的其它工具**一起拖垮——而 `timeout-policy` 正是**按每一条
 * 工具调用**替换 `exec.signal` 的（(DSH) `packages/guard/timeout-policy/src/index.ts:61-66`），
 * 所以这不是罕见路径（第 6 步 §3 风险 1）。
 */
function awaitOwn(promise, signal) {
  const attached = signal && typeof signal.addEventListener === 'function' ? signal : null
  if (!attached || promise === undefined) return promise
  if (attached.aborted) return Promise.reject(callerCancelError())
  return new Promise((resolve, reject) => {
    const onAbort = () => {
      attached.removeEventListener('abort', onAbort)
      reject(callerCancelError())
    }
    attached.addEventListener('abort', onAbort, { once: true })
    const settle = (fn) => (value) => {
      attached.removeEventListener('abort', onAbort)
      fn(value)
    }
    promise.then(settle(resolve), settle(reject))
  })
}

/** 调用方取消时抛给工具的错误（文案与 `describeTransportFailure` 同源）。 */
function callerCancelError() {
  const error = new Error('the call was cancelled')
  error.name = 'AbortError'
  error.code = 'CANCELLED'
  return error
}

/** GET one JSON endpoint through the local FastAPI, returning status + body. */
export async function apiGet(base, path, { token, signal, timeoutMs = 10000 } = {}) {
  const call = armTransportCall(signal, timeoutMs)
  if (call.preAborted) {
    call.dispose()
    return { body: null, text: '', ...call.failure(null) }
  }
  const headers = {}
  if (token) headers.Authorization = `Bearer ${token}`
  try {
    const res = await fetch(`${base}${path}`, { headers, signal: call.signal })
    const text = await res.text()
    let body = null
    if (text.length > 0) {
      try {
        body = JSON.parse(text)
      } catch {
        body = { raw: text }
      }
    }
    return { status: res.status, ok: res.ok, body, text }
  } catch (error) {
    return { body: null, text: '', ...call.failure(error) }
  } finally {
    call.dispose()
  }
}

/**
 * GET one BINARY endpoint through the local FastAPI, returning status + raw
 * bytes (Uint8Array) + selected response headers. Used by the /ks/doc-image
 * proxy (PNG screenshots from the engine's figure/formula/table-image
 * endpoints) — apiGet/apiPost assume a textual/JSON body and would corrupt
 * binary payloads through res.text().
 *
 * `captureHeaders` lists the engine headers worth forwarding verbatim
 * (X-Frac-* sizing contract); Content-Type is always forwarded when present.
 * Returns the same { status, ok, error } failure shape as apiGet.
 */
export async function apiGetBytes(
  base, path,
  { token, signal, timeoutMs = 30000, captureHeaders = [] } = {},
) {
  const call = armTransportCall(signal, timeoutMs)
  if (call.preAborted) {
    call.dispose()
    return { bytes: null, headers: {}, ...call.failure(null) }
  }
  const headers = {}
  if (token) headers.Authorization = `Bearer ${token}`
  headers.accept = 'image/png,image/*'
  try {
    const res = await fetch(`${base}${path}`, { headers, signal: call.signal })
    const buffer = new Uint8Array(await res.arrayBuffer())
    const out = { status: res.status, ok: res.ok, bytes: buffer, headers: {} }
    const ct = res.headers.get('content-type')
    if (ct !== null) out.headers['content-type'] = ct
    for (const name of captureHeaders) {
      const v = res.headers.get(name)
      if (v !== null) out.headers[name] = v
    }
    return out
  } catch (error) {
    return { bytes: null, headers: {}, ...call.failure(error) }
  } finally {
    call.dispose()
  }
}

/**
 * POST a JSON body to one endpoint through the local FastAPI, returning the
 * same { status, ok, body, text, error } shape as apiGet. Use for the
 * request-bearing endpoints (e.g. POST /api/v1/ks/answer). A non-JSON body
 * (body === undefined) is sent without a Content-Type, so the engine's own
 * request parsing stays in charge for GET-like POSTs.
 */
export async function apiPost(base, path, { token, signal, timeoutMs = 10000, body } = {}) {
  const call = armTransportCall(signal, timeoutMs)
  if (call.preAborted) {
    call.dispose()
    return { body: null, text: '', ...call.failure(null) }
  }
  const headers = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (token) headers.Authorization = `Bearer ${token}`
  try {
    const res = await fetch(`${base}${path}`, {
      method: 'POST',
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: call.signal,
    })
    const text = await res.text()
    let parsed = null
    if (text.length > 0) {
      try {
        parsed = JSON.parse(text)
      } catch {
        parsed = { raw: text }
      }
    }
    return { status: res.status, ok: res.ok, body: parsed, text }
  } catch (error) {
    return { body: null, text: '', ...call.failure(error) }
  } finally {
    call.dispose()
  }
}

/** Engine origin (scheme + host + port), with no path. */
export function originUrl(port) {
  return `http://127.0.0.1:${port}`
}

/* ------------------------------------------------------------------ *
 * EngineManager
 * ------------------------------------------------------------------ */

export class EngineManager {
  constructor(opts = {}) {
    this.engineRoot = opts.engineRoot || ENGINE_ROOT
    this.python = opts.python || resolvePythonPath()
    this.startupTimeoutMs = opts.startupTimeoutMs ?? 60_000
    this.pollIntervalMs = opts.pollIntervalMs ?? 700
    this.probeTimeoutMs = opts.probeTimeoutMs ?? 4_000
    /** Health-probe budget while the engine is still warming up (the first
     *  /health call loads the local embedding model, which can take a while). */
    this.startupProbeTimeoutMs = opts.startupProbeTimeoutMs ?? 20_000
    // 2026-09-12 批3（问题清单#3）：空闲回收默认 15min → 30min。慢查询
    // （ks_answer 自带 LLM 推理，120s 工具超时）与阅读长 PDF 的间歇都装得下；
    // 经 DSH 插件配置 idleTimeoutMs 仍可覆盖（默认值的唯一所有者是 index.js 的 `Config` schema）。
    this.idleTimeoutMs = opts.idleTimeoutMs ?? 30 * 60 * 1000

    /**
     * 批3 keepalive 钩子（问题清单#12）：空闲回收动手前询问一次——
     * 返回 true 则本轮不杀、续满整个窗口（查法规模式开着 → 引擎不断供）。
     * 由 index.js 接线（engine.js 保持零 cordis 依赖、可被 smoke 独立加载）。
     * 抛错按 false 处理（keepalive 只是优待，绝不能把回收搞挂）。
     */
    this.keepAliveCheck = null

    /** ChildProcess we spawned (set only when WE launch the engine).
     *  NOTE: the repo venv `python.exe` is a launcher that re-execs the real
     *  base interpreter, so `child.pid` is the LAUNCHER, while the actual
     *  engine runs as a separate pid recorded in engine.session.json. */
    this.child = null
    /** The real engine pid (from engine.session.json) we must stop. */
    this.enginePid = null
    /** Last known live session { port, token, pid, started_at, spawnedByUs }. */
    this.current = null
    /** Whether the currently-live engine is one we spawned. */
    this.ownsCurrent = false
    /** Whether we ever observed a healthy pre-existing (not-ours) instance. */
    this.sawExternal = false
    /** Diagnostics tail captured from the child's stdio. */
    this.diag = ''
    /** Last spawn failure (for clearer tool errors). */
    this.lastSpawnError = null

    this._idleTimer = null
    this._lastActivity = 0
    this._disposed = false
    /** 批3：进行中的 spawn（并发 ensureLive 合并用；null=无进行中）。 */
    this._spawning = null
    /** 第 6 步 §4B-3：这次探活/spawn 的**内部** controller（不绑第一个调用方）。 */
    this._spawnAbort = null
    /** 批3：死会话是否已留档过（一次 manager 生命周期只留一份，避免刷屏）。 */
    this._staleSessionLogged = false
  }

  get sessionFile() {
    return sessionFilePath()
  }

  touchActivity() {
    this._lastActivity = Date.now()
    this.armIdle()
  }

  /** (Re)arm the idle auto-kill timer; only ever kills an engine we own. */
  armIdle() {
    if (this._disposed || this.idleTimeoutMs <= 0) return
    if (this._idleTimer) clearTimeout(this._idleTimer)
    this._idleTimer = setTimeout(() => {
      this._idleTimer = null
      // Only touch an engine we actually spawned; never a pre-existing one.
      if (this.ownsCurrent && this.child) {
        // 批3 keepalive（问题清单#12）：查法规模式等"会用引擎"的状态开着时，
        // 引擎被回收会让下一次 ks_* 调用承担整段冷启动（载入 embedding 模型，
        // 实测 >20s）。钩子说"续"就续满整个窗口再考虑下一次回收。
        let keep = false
        try {
          keep = typeof this.keepAliveCheck === 'function' && this.keepAliveCheck()
        } catch {
          keep = false
        }
        if (keep) {
          this.armIdle()
          return
        }
        this.killOwned()
      }
    }, this.idleTimeoutMs)
    if (this._idleTimer.unref) this._idleTimer.unref()
  }

  clearIdle() {
    if (this._idleTimer) clearTimeout(this._idleTimer)
    this._idleTimer = null
  }

  /**
   * 批3 并发合并（问题清单#3）：同一 manager 上并发的 ensureLive（多工具同轮
   * 齐发、路由+工具撞车）**共享整段操作**（探活 + spawn）——否则每个调用各自
   * 起一个引擎进程，后写的 engine.session.json 把先写的顶掉，先起来的那个变成
   * "幽灵引擎"（无人引用、永不回收）。占位必须**同步**发生在任何 await 之前：
   * 探活/spawn 之间存在多个异步间隙，晚赋值会让并发调用穿过去（冒烟抓到）。
   */
  ensureLive(signal) {
    if (this._disposed) {
      return Promise.reject(new Error('ks-engine manager is disposed'))
    }
    this.touchActivity()
    if (!this._spawning) {
      // 第 6 步 §4B-3（§3 并行的前置）：探活/spawn 用**内部** signal，**不绑第一个调用方**。
      // 旧写法 `this._ensureLive(signal)` 让"第一个调用方"的取消决定整段共享操作的命运：
      // 它一 abort，`/health` 探活就以 status 0 结束，而下面把它**一律解释成"没有健康实例"**
      // ⇒ 继续 spawn，且带着已 abort 的 signal ⇒ 同轮并行、共享这份 promise 的**其它工具**
      // 一起失败。`timeout-policy` 是按**每一条工具调用**替换 `exec.signal` 的
      // ((DSH) `packages/guard/timeout-policy/src/index.ts:61-66`)，所以分开之后这条路会变常态。
      //
      // ⚠ **有意的取舍**：调用方取消**不再**终止冷启动——"用户点停止"之后，这次
      // startupTimeoutMs（默认 60s）以内的冷启动会**继续跑完**。换来的是"一个工具被取消
      // 不拖垮同轮其它工具"。别把它当"取消失效"的 bug（§4B-3 风险 5）。
      // 需要真停的时候只有一条路：`dispose()`（下面会 abort 这个内部 controller）。
      const controller = new AbortController()
      this._spawnAbort = controller
      const run = this._ensureLive(controller.signal)
      this._spawning = run
      // 单次注册（不是 `run.catch().finally()` 的两段链）：清理必须排在任何调用方的
      // `then` **之前**跑完，否则调用方一恢复就还会看见一个**已结算**的 `_spawning`
      // （于是"刚结束就又调一次"会复用旧结果，而不是重新探活）。两段链会多一个微任务。
      const clearSpawning = () => {
        // run 可能已 reject——清理后 _spawning 归 null，下一个调用正常重入
        // （并发窗口内的后来者拿到同一份结果，包括同一份错误）。
        if (this._spawning === run) {
          this._spawning = null
          this._spawnAbort = null
        }
      }
      run.then(clearSpawning, clearSpawning)
    }
    // 调用方的取消只影响"等不等结果"：立刻 reject 这一个调用方，底下的引擎照起。
    return awaitOwn(this._spawning, signal)
  }

  async _ensureLive(signal) {
    // 1. Re-read the session file on EVERY call — port/token rotate per start.
    const existing = await readSessionFile()
    if (existing) {
      const probe = await apiGet(originUrl(existing.port), HEALTH_PATH, {
        signal,
        timeoutMs: this.probeTimeoutMs,
      })
      if (probe.status === 200) {
        // A healthy instance. Is it ours (an engine WE spawned)?
        const ours = this.enginePid === existing.pid
        this.current = { ...existing, spawnedByUs: !!ours }
        this.ownsCurrent = !!ours
        if (!ours) this.sawExternal = true
        this.armIdle()
        return this.current
      }
      // 批3 stale 会话处置（问题清单#3）：会话文件指向的端口已不通——最常见
      // 形态是"pid 是死的（上次宿主退出把引擎带走了）"。旧实现在此无条件
      // spawn，新引擎起来后把新会话写进同一文件（行为正确）；这里补一层**留档**：
      // 把死会话改名保留，避免"engine.session.json 被覆盖"式的排障盲区，
      // 也让外部诊断工具能看出"上次那个引擎去哪了"。
      if (!this._staleSessionLogged) {
        this._staleSessionLogged = true
        try {
          const { rename } = await import('node:fs/promises')
          const stale = `${this.sessionFile}.stale-${existing.pid}-${Date.now()}`
          await rename(this.sessionFile, stale)
        } catch {
          /* 改名失败（不存在/被占用）→ 无害，spawn 会覆盖它 */
        }
      }
    }

    // 2. No healthy instance -> spawn.
    return this.spawnEngine(signal)
  }

  async spawnEngine(signal) {
    this.diag = ''
    this.lastSpawnError = null
    this.enginePid = null
    this.touchActivity()

    const child = spawn(this.python, ['-m', MODULE_ARG], {
      cwd: this.engineRoot,
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
      env: { ...process.env },
    })
    this.child = child

    // The engine prints KNOWLEDGE_STATION_PORT=<port> on stdout (from the real
    // engine process). We attribute the session to OUR spawn by that port,
    // because the venv launcher re-execs the base python (different pid).
    let enginePort = null
    const capture = (chunk) => {
      this.diag = (this.diag + chunk.toString('utf8')).slice(-20000)
      const m = /KNOWLEDGE_STATION_PORT=(\d+)/.exec(this.diag)
      if (m) enginePort = Number(m[1])
    }
    if (child.stdout) child.stdout.on('data', capture)
    if (child.stderr) child.stderr.on('data', capture)
    let spawnError = null
    child.on('error', (err) => {
      spawnError = err
      this.lastSpawnError = err
    })

    const deadline = Date.now() + this.startupTimeoutMs
    while (Date.now() < deadline) {
      if (signal && signal.aborted) {
        this.killOwned()
        throw new Error('ks-engine spawn aborted by caller')
      }
      if (spawnError) {
        this.killOwned()
        throw new Error(
          `ks-engine could not start interpreter "${this.python}": ${spawnError.message}`,
        )
      }
      // Launcher died before the engine ever published a port -> nothing to wait for.
      if (enginePort === null && child.exitCode !== null) {
        this.killOwned()
        const tail = this.diag.trim().split('\n').slice(-12).join('\n')
        throw new Error(
          `ks-engine exited early (code ${child.exitCode}). Is the repo venv built? Tail:\n${tail}`,
        )
      }

      if (enginePort !== null) {
        // Probe OUR engine's port directly (it is announced on stdout), so a
        // stale/foreign session file can never make us wait on the wrong port.
        const probe = await apiGet(originUrl(enginePort), HEALTH_PATH, {
          signal,
          timeoutMs: this.startupProbeTimeoutMs,
        })
        if (probe.status === 200) {
          // The engine is up. Read the session for the token + real engine pid.
          const session = await readSessionFile()
          if (session && session.port === enginePort) {
            this.enginePid = session.pid
            this.current = { ...session, spawnedByUs: true }
            this.ownsCurrent = true
            this.armIdle()
            return this.current
          }
          // session not (re)written yet — keep polling so we pick up its token.
        }
      }
      await sleep(this.pollIntervalMs)
    }

    // Startup budget exhausted -> stop OUR engine and surface a clear error.
    this.killOwned()
    const tail = this.diag.trim().split('\n').slice(-20).join('\n')
    throw new Error(
      `ks-engine did not become healthy within ${this.startupTimeoutMs}ms ` +
        `(session file: ${this.sessionFile}). ${enginePort ? `port=${enginePort}` : 'no port on stdout'}. Stdout/stderr tail:\n${tail}`,
    )
  }

  /** Stop the engine we spawned (its session pid) and the venv launcher.
   *  Uses Stop-Process -Id — never taskkill /IM python.exe. Never kills a
   *  pre-existing (external) engine, because `child`/`enginePid` are only set
   *  when WE spawn. */
  killOwned() {
    const pids = new Set()
    if (this.child && this.child.pid) pids.add(this.child.pid)
    if (this.enginePid) pids.add(this.enginePid)
    this.child = null
    this.enginePid = null
    this.ownsCurrent = false
    for (const pid of pids) {
      try {
        if (isProcessAlive(pid)) killPid(pid)
      } catch {
        /* ignore teardown errors */
      }
    }
  }

  /** Clear idle timer + tear down any engine we spawned. Safe to call once. */
  async dispose() {
    if (this._disposed) return
    this._disposed = true
    this.clearIdle()
    // 内部 spawn controller 的**唯一** abort 点：让一次进行中的冷启动当场收摊
    // （`spawnEngine` 的 `signal.aborted` 分支因此不是死代码）。调用方 signal 做不到这件事
    // ——那是上面 ensureLive 的有意取舍。
    if (this._spawnAbort) {
      try { this._spawnAbort.abort() } catch { /* controller 已被丢弃 */ }
      this._spawnAbort = null
    }
    this.killOwned()
  }
}
