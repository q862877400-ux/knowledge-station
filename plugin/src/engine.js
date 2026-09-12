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

/** GET one JSON endpoint through the local FastAPI, returning status + body. */
export async function apiGet(base, path, { token, signal, timeoutMs = 10000 } = {}) {
  const controller = new AbortController()
  const onAbort = () => controller.abort()
  if (signal) {
    if (signal.aborted) controller.abort()
    else signal.addEventListener('abort', onAbort, { once: true })
  }
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  const headers = {}
  if (token) headers.Authorization = `Bearer ${token}`
  try {
    const res = await fetch(`${base}${path}`, { headers, signal: controller.signal })
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
    return {
      status: 0,
      ok: false,
      body: null,
      text: '',
      error: error instanceof Error ? error.message : String(error),
    }
  } finally {
    clearTimeout(timer)
    if (signal) signal.removeEventListener('abort', onAbort)
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
  const controller = new AbortController()
  const onAbort = () => controller.abort()
  if (signal) {
    if (signal.aborted) controller.abort()
    else signal.addEventListener('abort', onAbort, { once: true })
  }
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  const headers = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (token) headers.Authorization = `Bearer ${token}`
  try {
    const res = await fetch(`${base}${path}`, {
      method: 'POST',
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
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
    return {
      status: 0,
      ok: false,
      body: null,
      text: '',
      error: error instanceof Error ? error.message : String(error),
    }
  } finally {
    clearTimeout(timer)
    if (signal) signal.removeEventListener('abort', onAbort)
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
    // 经 DSH 插件配置 idleTimeoutMs 仍可覆盖（index.js DEFAULTS 同步改）。
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
    if (this._spawning) return this._spawning
    const run = this._ensureLive(signal)
    this._spawning = run
    return run.finally(() => {
      // run 可能已 reject——finally 之后 _spawning 归 null，下一个调用正常重入
      // （并发窗口内的后来者拿到同一份结果，包括同一份错误）。
      if (this._spawning === run) this._spawning = null
    })
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
    this.killOwned()
  }
}
