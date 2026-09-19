/**
 * ks-dsh-plugin — src/ingest.js（R27 入库预览 / 批量分桶 host 半，2026-09-11）
 *
 * 把引擎侧**只读**的 R27 预览端点接到同源 `/ks/` 面上，供 📥 入库预览面板使用。
 * 引擎端点（`src/core/api/routes_ingest_preview.py`）：
 *   POST /api/v1/ingest/preview           单本 R27 完整体检报告
 *   POST /api/v1/ingest/preview/batch     目录批量 + ✅/⚠️/❌ 分桶
 *   GET  /api/v1/ingest/preview/inbox     列候选 PDF（只列名/大小）
 *   POST /api/v1/ingest/preview/jobs      异步全量预览（万级；2026-09-12 L239）
 *   GET  /api/v1/ingest/preview/jobs/{id}  任务进度 + 瘦身行分页
 *   POST /api/v1/ingest/preview/jobs/{id}/abort  协作式中断
 *
 * ## 设计纪律（与 inspection/announce 的刻意区别）
 * 同步预览（preview/batch）：纯代理、**零缓存、零状态文件**——预览是"此刻这批
 * 文件长什么样"的即时快照，不是跨进程触发真值（那才需要状态文件）。
 * **异步任务（preview/jobs）则镜像 inspection.js 的 adoptBatch+runPollLoop**：
 * 触发真值 + last 快照落 `ks-ingest.json`（引擎 session 文件旁边），浏览器关掉
 * 后仍由 host 权威推进；引擎死亡 → 连续错误计数 → 标 failed（不假装仍在跑）。
 *
 * ## 待入库目录（inbox）
 * 浏览器无法浏览本机目录，所以给一个**可预期的落点**：默认
 * `%USERPROFILE%\Documents\KnowledgeStation\待入库`。host 只在被请求时按需创建
 * （`mkdir -p` 语义、幂等、只在自己的数据目录语义下），并把解析后的绝对路径回给 UI，
 * 让用户知道该把 PDF 放哪。**host 不读文件内容**——预览一律由引擎做。
 *
 * ## 只读红线
 * host 侧只做「列目录 + 转发 + 任务进度镜像」；不移动/复制/改写用户文件；不写库。
 *
 * Only Node builtins + ./engine.js helpers — no cordis import.
 */

import { mkdir, readdir, readFile, stat, writeFile } from 'node:fs/promises'
import { homedir } from 'node:os'
import { basename, dirname, extname, join, resolve } from 'node:path'

import { apiGet, apiPost, originUrl } from './engine.js'
import { sessionFilePath } from './engine.js'

export const KS_INGEST_INBOX_PATH = '/ks/ingest/inbox'
export const KS_INGEST_INBOX_DEFAULT_PATH = '/ks/ingest/inbox-default'
export const KS_INGEST_PREVIEW_PATH = '/ks/ingest/preview'
export const KS_INGEST_BATCH_PATH = '/ks/ingest/preview/batch'
export const KS_INGEST_JOB_START_PATH = '/ks/ingest/preview/jobs'
export const KS_INGEST_JOB_STATUS_PREFIX = '/ks/ingest/preview/jobs/'   // + job_id
export const KS_INGEST_JOB_ABORT_PREFIX = '/ks/ingest/preview/jobs/'   // + job_id + '/abort'

const ENGINE_INBOX_PATH = '/api/v1/ingest/preview/inbox'
const ENGINE_PREVIEW_PATH = '/api/v1/ingest/preview'
const ENGINE_BATCH_PATH = '/api/v1/ingest/preview/batch'
const ENGINE_JOB_PATH = (id) => `/api/v1/ingest/preview/jobs/${encodeURIComponent(id)}`

/** 单本预览：解析 + 倾斜测量都可能秒级到分钟级（真机扫描件实测 0.5–4s） */
const PREVIEW_TIMEOUT_MS = 240_000
/** 批量：抽样式批量（默认 5 本）——同步接口，别让它拖成"永远转圈" */
const BATCH_TIMEOUT_MS = 900_000
const BODY_CAP = 65_536

/* ------------------------------------------------------------------ *
 * Helpers（与 report.js 同款独立实现：模块保持 smoke 可加载纯度）
 * ------------------------------------------------------------------ */

function jsonResponse(res, status, body) {
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' })
  res.end(JSON.stringify(body))
}

function errorBody(code, message) {
  return { ok: false, error: { code, message } }
}

function readJsonBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = []
    let size = 0
    let done = false
    const fail = (err) => { if (!done) { done = true; reject(err) } }
    req.on('data', (chunk) => {
      if (done) return
      size += chunk.length
      if (size > BODY_CAP) { fail(new Error('body_too_large')); return }
      chunks.push(chunk)
    })
    req.on('end', () => {
      if (done) return
      done = true
      const raw = Buffer.concat(chunks).toString('utf8').trim()
      if (!raw) { resolve({}); return }
      try { resolve(JSON.parse(raw)) } catch { reject(new Error('bad_json')) }
    })
    req.on('error', fail)
  })
}

/** GET with one 401 self-heal retry（token 轮换 → ensureLive 重读 session）。 */
async function engineGetWithRetry(manager, path, timeoutMs = 20_000) {
  let session = await manager.ensureLive()
  let probe = await apiGet(originUrl(session.port), path, { token: session.token, timeoutMs })
  if (probe.status === 401) {
    session = await manager.ensureLive()
    probe = await apiGet(originUrl(session.port), path, { token: session.token, timeoutMs })
  }
  return probe
}

/** POST with one 401 self-heal retry（同 engineGetWithRetry 的纪律）。 */
async function enginePostWithRetry(manager, path, body, timeoutMs) {
  let session = await manager.ensureLive()
  let probe = await apiPost(originUrl(session.port), path,
    { token: session.token, timeoutMs, body })
  if (probe.status === 401) {
    session = await manager.ensureLive()
    probe = await apiPost(originUrl(session.port), path,
      { token: session.token, timeoutMs, body })
  }
  return probe
}

/** 引擎错误 → 同源响应（保留引擎自己的错误码，别把 422 说成 500）。 */
function mapEngine(res, probe) {
  if (probe.status === 200 && probe.body && typeof probe.body === 'object') {
    jsonResponse(res, 200, { ok: true, data: probe.body.data ?? {} })
    return
  }
  const engineCode = probe.body && typeof probe.body === 'object'
    ? String(probe.body.error ?? probe.body.detail ?? '') : ''
  const engineMsg = probe.body && typeof probe.body === 'object'
    ? String(probe.body.message ?? probe.body.detail ?? '') : ''
  const status = probe.status === 404 ? 404 : (probe.status === 422 ? 400 : 502)
  jsonResponse(res, status, errorBody(engineCode || 'engine_error',
    engineMsg || `引擎返回 HTTP ${probe.status}: ${probe.error || probe.text || 'no response'}`))
}

function pickQuery(reqUrl, allowed) {
  const out = {}
  const qs = String(reqUrl || '').split('?')[1]
  if (!qs) return out
  for (const [k, v] of new URLSearchParams(qs).entries()) {
    if (allowed.includes(k) && v !== '') out[k] = v
  }
  return out
}

/** 默认待入库目录：用户可见、可预期（浏览器无法浏览本机目录，必须给一个落点）。 */
export function defaultInboxDir() {
  return join(homedir(), 'Documents', 'KnowledgeStation', '待入库')
}

/** 确保目录存在并回传绝对路径（幂等；失败抛错由调用方转 500）。 */
export async function ensureInboxDir(dir) {
  const target = resolve(dir && String(dir).trim() ? String(dir).trim() : defaultInboxDir())
  await mkdir(target, { recursive: true })
  return target
}

/** 列目录下的 PDF（host 侧兜底列表：引擎不可用时 UI 仍能看到"有哪些文件"）。 */
async function listPdfs(dir) {
  const names = await readdir(dir, { withFileTypes: true })
  const files = []
  for (const e of names) {
    if (!e.isFile()) continue
    if (extname(e.name).toLowerCase() !== '.pdf') continue
    try {
      const st = await stat(join(dir, e.name))
      files.push({ file_name: e.name, size: st.size, path: join(dir, e.name) })
    } catch { /* 读不到就跳过（并发删除） */ }
  }
  files.sort((a, b) => (a.file_name < b.file_name ? -1 : 1))
  return files
}

/* ------------------------------------------------------------------ *
 * Routes
 * ------------------------------------------------------------------ */

function registerInboxDefaultRoute(ctx) {
  return ctx.webServer.register({
    kind: 'exact',
    path: KS_INGEST_INBOX_DEFAULT_PATH,
    handler: async (req, res) => {
      if (req.method !== 'GET') {
        jsonResponse(res, 405, errorBody('method_not_allowed', 'GET only'))
        return
      }
      try {
        const dir = await ensureInboxDir(defaultInboxDir())
        jsonResponse(res, 200, { ok: true, data: { dir } })
      } catch (err) {
        jsonResponse(res, 500, errorBody('inbox_dir_failed',
          err instanceof Error ? err.message : String(err)))
      }
    },
  })
}

function registerInboxRoute(ctx, manager) {
  return ctx.webServer.register({
    kind: 'exact',
    path: KS_INGEST_INBOX_PATH,
    handler: async (req, res) => {
      if (req.method !== 'GET') {
        jsonResponse(res, 405, errorBody('method_not_allowed', 'GET only'))
        return
      }
      const q = pickQuery(req.url, ['dir', 'recursive', 'limit'])
      let dir
      try {
        dir = await ensureInboxDir(q.dir || defaultInboxDir())
      } catch (err) {
        jsonResponse(res, 500, errorBody('inbox_dir_failed',
          err instanceof Error ? err.message : String(err)))
        return
      }
      const qs = new URLSearchParams({ ...q, dir }).toString()
      try {
        const probe = await engineGetWithRetry(manager, `${ENGINE_INBOX_PATH}?${qs}`)
        if (probe.status === 200) { mapEngine(res, probe); return }
        // 引擎不可用/目录判定失败 → host 侧兜底列表（UI 至少要能显示有哪些文件）
        const files = await listPdfs(dir)
        jsonResponse(res, 200, { ok: true, degraded: 'engine_unavailable',
          data: { dir, count: files.length, files } })
      } catch (err) {
        try {
          const files = await listPdfs(dir)
          jsonResponse(res, 200, { ok: true, degraded: 'engine_unavailable',
            data: { dir, count: files.length, files } })
        } catch (err2) {
          jsonResponse(res, 503, errorBody('engine_unavailable',
            err instanceof Error ? err.message : String(err2)))
        }
      }
    },
  })
}

function registerPreviewRoute(ctx, manager) {
  return ctx.webServer.register({
    kind: 'exact',
    path: KS_INGEST_PREVIEW_PATH,
    handler: async (req, res) => {
      if (req.method !== 'POST') {
        jsonResponse(res, 405, errorBody('method_not_allowed', 'POST only'))
        return
      }
      let body
      try { body = await readJsonBody(req) } catch (err) {
        const code = err instanceof Error && err.message === 'body_too_large'
          ? 'body_too_large' : 'bad_json'
        jsonResponse(res, 400, errorBody(code, '请求体必须是 JSON'))
        return
      }
      // 白名单透传。`allow_deep` **要转发**（2026-09-17 独立复核 F1）：
      // 原先这里写"不暴露（预览零外发是产品性质，不给开关）"，把引擎已解开的能力又
      // 在桥这一层掐掉了——锁只是从引擎搬到了桥。现行口径（D5）：**默认不外发，
      // 显式 allow_deep=true 才走云深度通道并如实回 egress**；桥只做**严格布尔**转发，
      // 不下判断（判断在引擎侧，且引擎会拒非布尔值）。
      const payload = {}
      if (typeof body.path === 'string' && body.path.trim()) payload.path = body.path.trim()
      if (typeof body.doc_type === 'string' && body.doc_type.trim()) {
        payload.doc_type = body.doc_type.trim()
      }
      if (body.allow_deep === true) payload.allow_deep = true
      if (!payload.path) {
        jsonResponse(res, 400, errorBody('missing_path', '需要 path（要预览的 PDF 绝对路径）'))
        return
      }
      try {
        const probe = await enginePostWithRetry(manager, ENGINE_PREVIEW_PATH, payload,
          PREVIEW_TIMEOUT_MS)
        mapEngine(res, probe)
      } catch (err) {
        jsonResponse(res, 503, errorBody('engine_unavailable',
          err instanceof Error ? err.message : String(err)))
      }
    },
  })
}

function registerBatchRoute(ctx, manager) {
  return ctx.webServer.register({
    kind: 'exact',
    path: KS_INGEST_BATCH_PATH,
    handler: async (req, res) => {
      if (req.method !== 'POST') {
        jsonResponse(res, 405, errorBody('method_not_allowed', 'POST only'))
        return
      }
      let body
      try { body = await readJsonBody(req) } catch (err) {
        const code = err instanceof Error && err.message === 'body_too_large'
          ? 'body_too_large' : 'bad_json'
        jsonResponse(res, 400, errorBody(code, '请求体必须是 JSON'))
        return
      }
      const payload = {}
      const hasPaths = Array.isArray(body.paths) && body.paths.length > 0
      if (hasPaths) {
        payload.paths = body.paths.filter((p) => typeof p === 'string' && p.trim())
        if (payload.paths.length === 0) {
          jsonResponse(res, 400, errorBody('bad_paths', 'paths 必须是字符串数组'))
          return
        }
      } else {
        let dir
        try {
          dir = await ensureInboxDir(body.dir || defaultInboxDir())
        } catch (err) {
          jsonResponse(res, 500, errorBody('inbox_dir_failed',
            err instanceof Error ? err.message : String(err)))
          return
        }
        payload.dir = dir
      }
      if (body.sample !== undefined) {
        const sample = Number(body.sample)
        if (!Number.isInteger(sample) || sample < 0) {
          jsonResponse(res, 400, errorBody('bad_sample', 'sample 必须是 ≥0 的整数（0 = 不抽样）'))
          return
        }
        payload.sample = sample
      }
      if (body.limit_files !== undefined) {
        const limit = Number(body.limit_files)
        if (!Number.isInteger(limit) || limit < 0) {
          jsonResponse(res, 400, errorBody('bad_limit', 'limit_files 必须是 ≥0 的整数'))
          return
        }
        payload.limit_files = limit
      }
      if (typeof body.doc_type === 'string' && body.doc_type.trim()) {
        payload.doc_type = body.doc_type.trim()
      }
      if (body.recursive === true) payload.recursive = true
      // allow_deep 同单文件路由：严格布尔转发，默认不外发（F1）
      if (body.allow_deep === true) payload.allow_deep = true
      try {
        const probe = await enginePostWithRetry(manager, ENGINE_BATCH_PATH, payload,
          BATCH_TIMEOUT_MS)
        mapEngine(res, probe)
      } catch (err) {
        jsonResponse(res, 503, errorBody('engine_unavailable',
          err instanceof Error ? err.message : String(err)))
      }
    },
  })
}

/* ------------------------------------------------------------------ *
 * 异步全量预览任务（万级；2026-09-12 L239）— 镜像 inspection.js 范式：
 * 状态文件 ks-ingest.json（引擎 session 旁边）+ adoptBatch + runPollLoop。
 * 浏览器关掉后仍由 host 权威推进；引擎死亡 → MAX_STALL_TICKS → 标 failed。
 * ------------------------------------------------------------------ */

const JOB_POLL_INTERVAL_MS = 1_500
const JOB_MAX_STALL_TICKS = 40          // 连续引擎错误 ~60s → failed（别永久空转）
const JOB_RUNNING_CAP_MS = 6 * 60 * 60 * 1000  // 万级上限 6h——超时停轮询标 stale
const JOB_TERMINAL = new Set(['done', 'aborted', 'failed'])
const JOB_ROWS_PAGE = 200               // host 侧一次拉的瘦身行页大小

/** Trigger truth + last snapshot，落在引擎 session 文件旁边（同 inspection）。 */
export function ingestJobFilePath() {
  return join(dirname(sessionFilePath()), 'ks-ingest.json')
}

let _jobState = null
let _jobPersistChain = Promise.resolve()
let _jobPoll = null // { jobId, stopped }
/** 卸载代数：`registerKsIngestRoutes` 的 disposer 递增它，让"仍在飞的启动收尾"作废
 *  （否则 await 窗口里被卸载后，收尾还会 `adoptJob` 装一个活轮询）。 */
let _jobEpoch = 0

function defaultJobState() {
  return { last: null, stale_run: false }
}

function sanitizeJobLast(raw) {
  const last = { ...raw }
  last.job_id = typeof last.job_id === 'string' ? last.job_id : ''
  last.status = typeof last.status === 'string' ? last.status : 'unknown'
  last.total = Number(last.total) || 0
  last.done = Number(last.done) || 0
  const b = last.buckets && typeof last.buckets === 'object' ? last.buckets : {}
  last.buckets = {
    ok: Number(b.ok) || 0, warn: Number(b.warn) || 0, block: Number(b.block) || 0,
  }
  last.dir = typeof last.dir === 'string' ? last.dir : ''
  last.error = typeof last.error === 'string' ? last.error : null
  delete last.rows
  return last
}

async function loadJobStateFile() {
  try {
    const raw = await readFile(ingestJobFilePath(), 'utf8')
    const parsed = JSON.parse(raw)
    if (parsed !== null && typeof parsed === 'object') {
      const s = defaultJobState()
      if (parsed.last && typeof parsed.last === 'object') s.last = sanitizeJobLast(parsed.last)
      if (parsed.stale_run === true) s.stale_run = true
      return s
    }
  } catch { /* absent or corrupt -> defaults */ }
  return defaultJobState()
}

async function initJobState() {
  if (_jobState === null) _jobState = await loadJobStateFile()
  return _jobState
}

function jobState() {
  if (_jobState === null) _jobState = defaultJobState()
  return _jobState
}

function persistJobState() {
  _jobPersistChain = _jobPersistChain
    .then(() => writeFile(ingestJobFilePath(), JSON.stringify(jobState(), null, 2), 'utf8'))
    .catch(() => { /* best-effort — memory truth */ })
  return _jobPersistChain
}

function updateJobState(fn) {
  const s = jobState()
  const out = fn(s)
  void persistJobState()
  return out
}

function stopJobPoll() {
  if (_jobPoll) _jobPoll.stopped = true
  _jobPoll = null
}

function adoptJob(manager, jobId, initialStatus) {
  if (_jobPoll && _jobPoll.jobId === jobId && !_jobPoll.stopped) return
  stopJobPoll()
  _jobPoll = { jobId, stopped: false }
  // ⚠ `manager` **必须**原样往下传：2026-09-19 修的是一个静默失效——这里曾写成
  // `runJobPollLoop(jobId, initialStatus)`，而签名是 `(manager, jobId, initialStatus)`
  // ⇒ `manager` 收到的是 job_id 字符串、`jobId` 收到的是状态串，循环第一句
  // `jobTick('running')` 因 id 不匹配立刻退出。表现是宿主镜像永不推进、遗留 running
  // 批永不重接管，**且不抛任何错**。守卫见 scripts/smoke-lifecycle.mjs A1/A2。
  // `.catch` 不是顺手加的：`void` 的 rejection 在 Node 20+ 会**终止宿主进程**，而后台轮询
  // 失败本来就该表现为"镜像不推进"，不该升级成把宿主带走。
  void runJobPollLoop(manager, jobId, initialStatus).catch(() => {
    /* best-effort：真相在引擎侧，宿主镜像只是缓存 */
  })
}

function jobTick(jobId) {
  return !_jobPoll || _jobPoll.stopped || _jobPoll.jobId !== jobId
}

async function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function runJobPollLoop(manager, jobId, initialStatus) {
  let stall = 0
  const startedAt = Date.now()
  // adopt 时已 terminal（启动收尾/上一进程留下的终态）→ 不轮询，直接收
  if (JOB_TERMINAL.has(initialStatus)) {
    await refreshJobFinal(manager, jobId)
    stopJobPoll()
    return
  }
  while (!jobTick(jobId)) {
    // 空闲保活：每 tick 记引擎活动，idle 计时器不在批中触发
    manager.touchActivity()
    if (Date.now() - startedAt > JOB_RUNNING_CAP_MS) {
      updateJobState((s) => {
        if (s.last && s.last.job_id === jobId) {
          s.last.error = '运行超时（6 小时），已停止轮询；任务可能已中断'
        }
        s.stale_run = true
        return s
      })
      stopJobPoll()
      return
    }
    let sess = null
    try { sess = await manager.ensureLive() } catch { /* down — stall */ }
    if (!sess) {
      stall += 1
      if (stall >= JOB_MAX_STALL_TICKS) {
        await markJobFailed(jobId, '任务轮询期间引擎不可达（已停止轮询）')
        stopJobPoll()
        return
      }
      await sleep(JOB_POLL_INTERVAL_MS)
      continue
    }
    const probe = await apiGet(
      originUrl(sess.port),
      ENGINE_JOB_PATH(jobId),
      { token: sess.token, timeoutMs: 15_000 },
    )
    if (probe.status === 404) {
      // 引擎活着但任务不在（引擎重启丢进程内任务表——设计上就不落库，如实报告）
      await markJobFailed(jobId, '任务不存在（引擎重启会丢进程内任务，请重新发起）')
      stopJobPoll()
      return
    }
    if (probe.status !== 200) {
      stall += 1
      if (stall >= JOB_MAX_STALL_TICKS) {
        await markJobFailed(jobId, `引擎任务查询持续失败（HTTP ${probe.status}）`)
        stopJobPoll()
        return
      }
      await sleep(JOB_POLL_INTERVAL_MS)
      continue
    }
    stall = 0
    const data = probe.body && typeof probe.body === 'object'
      ? (probe.body.data ?? {}) : {}
    const status = String(data.status ?? '')
    updateJobState((s) => {
      if (!s.last || s.last.job_id !== jobId) return s
      s.last.status = status
      s.last.done = Number(data.done) || 0
      s.last.total = Number(data.total) || 0
      const b = data.buckets && typeof data.buckets === 'object' ? data.buckets : {}
      s.last.buckets = {
        ok: Number(b.ok) || 0, warn: Number(b.warn) || 0, block: Number(b.block) || 0,
      }
      s.last.error = typeof data.error === 'string' ? data.error : null
      s.stale_run = false
      return s
    })
    if (JOB_TERMINAL.has(status)) {
      await refreshJobFinal(manager, jobId)
      stopJobPoll()
      return
    }
    await sleep(JOB_POLL_INTERVAL_MS)
  }
}

async function refreshJobFinal(manager, jobId) {
  // terminal 后再拉一次全量行（分页拉全，供 UI 总账与明细导出用）
  let sess = null
  try { sess = await manager.ensureLive() } catch { return }
  const rows = []
  let offset = 0
  for (;;) {
    const probe = await apiGet(
      originUrl(sess.port),
      `${ENGINE_JOB_PATH(jobId)}?rows_offset=${offset}&rows_limit=${JOB_ROWS_PAGE}`,
      { token: sess.token, timeoutMs: 60_000 },
    )
    if (probe.status !== 200 || !probe.body || !Array.isArray(probe.body.data?.rows)) break
    rows.push(...probe.body.data.rows)
    if (rows.length >= (Number(probe.body.data.rows_count) || 0)) break
    offset += probe.body.data.rows.length
    if (probe.body.data.rows.length === 0) break
  }
  updateJobState((s) => {
    if (!s.last || s.last.job_id !== jobId) return s
    if (rows.length > 0) s.last.rows = rows
    return s
  })
}

async function markJobFailed(jobId, message) {
  updateJobState((s) => {
    if (!s.last || s.last.job_id !== jobId) return s
    s.last.status = 'failed'
    s.last.error = message
    return s
  })
}

/** Boot-time handover：上一个 host 进程留下的非 terminal 任务 → 接管轮询。
 *  ⚠ 加载状态文件是 `await`；若卸载正好落在这个窗口里，收尾**必须作废**——
 *  否则它会在 dispose 之后调用 `adoptJob`，装一个持有已死 ctx 的活轮询。 */
export async function ingestJobStartupCheck(ctx, manager) {
  const epoch = _jobEpoch
  await initJobState()
  if (epoch !== _jobEpoch) return
  const s = jobState()
  if (s.last && !JOB_TERMINAL.has(s.last.status)) {
    adoptJob(manager, s.last.job_id, s.last.status)
  }
}

async function handleJobStart(req, res, manager) {
  let body
  try { body = await readJsonBody(req) } catch (err) {
    const code = err instanceof Error && err.message === 'body_too_large'
      ? 'body_too_large' : 'bad_json'
    jsonResponse(res, 400, errorBody(code, '请求体必须是 JSON'))
    return
  }
  const hasPaths = Array.isArray(body.paths) && body.paths.length > 0
  let dir
  if (!hasPaths) {
    try {
      dir = await ensureInboxDir(body.dir || defaultInboxDir())
    } catch (err) {
      jsonResponse(res, 500, errorBody('inbox_dir_failed',
        err instanceof Error ? err.message : String(err)))
      return
    }
  }
  const payload = {}
  if (hasPaths) {
    payload.paths = body.paths.filter((p) => typeof p === 'string' && p.trim())
    if (payload.paths.length === 0) {
      jsonResponse(res, 400, errorBody('bad_paths', 'paths 必须是字符串数组'))
      return
    }
  } else {
    payload.dir = dir
  }
  if (body.recursive === true) payload.recursive = true
  if (body.batch_size !== undefined) {
    const n = Number(body.batch_size)
    if (!Number.isInteger(n) || n < 0) {
      jsonResponse(res, 400, errorBody('bad_batch_size', 'batch_size 必须是 ≥0 的整数'))
      return
    }
    if (n > 0) payload.batch_size = n
  }
  if (typeof body.doc_type === 'string' && body.doc_type.trim()) {
    payload.doc_type = body.doc_type.trim()
  }
  // allow_deep 同前两条路由：严格布尔转发，默认不外发（F1）
  if (body.allow_deep === true) payload.allow_deep = true
  try {
    const probe = await enginePostWithRetry(manager, '/api/v1/ingest/preview/jobs', payload, 30_000)
    if (probe.status !== 200 || !probe.body?.data?.job_id) {
      mapEngine(res, probe)
      return
    }
    const view = probe.body.data
    await initJobState()
    updateJobState((s) => {
      s.last = sanitizeJobLast({
        job_id: view.job_id, status: view.status, total: view.total, done: 0,
        buckets: { ok: 0, warn: 0, block: 0 }, dir: dir || '',
        error: null, rows: [],
      })
      s.stale_run = false
      return s
    })
    adoptJob(manager, view.job_id, view.status)
    jsonResponse(res, 200, { ok: true, data: view })
  } catch (err) {
    jsonResponse(res, 503, errorBody('engine_unavailable',
      err instanceof Error ? err.message : String(err)))
  }
}

async function handleJobStatus(req, res, manager, jobId) {
  // host 镜像快照（浏览器关掉期间的推进记录）；引擎仍可查则用实时值
  await initJobState()
  const s = jobState()
  const mirror = s.last && s.last.job_id === jobId ? s.last : null
  const q = pickQuery(req.url, ['rows_offset', 'rows_limit'])
  let live = null
  try {
    const sess = await manager.ensureLive()
    const probe = await apiGet(
      originUrl(sess.port),
      `${ENGINE_JOB_PATH(jobId)}?rows_offset=${encodeURIComponent(q.rows_offset ?? 0)}&rows_limit=${encodeURIComponent(q.rows_limit ?? JOB_ROWS_PAGE)}`,
      { token: sess.token, timeoutMs: 20_000 },
    )
    if (probe.status === 200 && probe.body?.data) live = probe.body.data
  } catch { /* 引擎不可达 → 只回镜像快照（stale 如实标注） */ }
  const stale = live === null
  const merged = live ?? mirror ?? null
  if (!merged) {
    jsonResponse(res, 404, errorBody('job_not_found', '任务不存在'))
    return
  }
  const rows = Array.isArray(live?.rows) ? live.rows
    : (Array.isArray(mirror?.rows) ? mirror.rows : [])
  jsonResponse(res, 200, {
    ok: true,
    data: {
      job_id: merged.job_id, status: merged.status,
      total: Number(merged.total) || 0, done: Number(merged.done) || 0,
      buckets: merged.buckets ?? { ok: 0, warn: 0, block: 0 },
      rows, rows_count: live?.rows_count ?? rows.length,
      error: merged.error ?? null, stale,
    },
  })
}

function registerJobStatusRoute(ctx, manager) { /* folded into dispatcher */ }
function registerJobAbortRoute(ctx, manager) { /* folded into dispatcher */ }

/** 统一分发：POST /jobs（启动）· GET /jobs/{id}（进度）· POST /jobs/{id}/abort。
 *  单个 prefix 路由（避免两个同前缀路由互踩）。 */
function registerJobDispatcher(ctx, manager) {
  return ctx.webServer.register({
    kind: 'prefix',
    path: KS_INGEST_JOB_START_PATH,
    handler: async (req, res) => {
      const url = String(req.url || '')
      const tail = url.split('?')[0].slice(KS_INGEST_JOB_START_PATH.length)
        .replace(/^\/+/, '').replace(/\/+$/, '')

      // ---- POST /ks/ingest/preview/jobs → 启动 ----
      if (req.method === 'POST' && tail === '') {
        await handleJobStart(req, res, manager)
        return
      }
      // ---- GET /ks/ingest/preview/jobs/{job_id} → 进度 ----
      if (req.method === 'GET' && tail && !tail.includes('/')) {
        await handleJobStatus(req, res, manager, decodeURIComponent(tail))
        return
      }
      // ---- POST /ks/ingest/preview/jobs/{job_id}/abort → 中断 ----
      if (req.method === 'POST' && tail.endsWith('/abort')) {
        const jobId = decodeURIComponent(tail.slice(0, -'/abort'.length))
        if (jobId && !jobId.includes('/')) {
          try {
            const probe = await enginePostWithRetry(
              manager, `${ENGINE_JOB_PATH(jobId)}/abort`, {}, 30_000)
            mapEngine(res, probe)
          } catch (err) {
            jsonResponse(res, 503, errorBody('engine_unavailable',
              err instanceof Error ? err.message : String(err)))
          }
          return
        }
        jsonResponse(res, 404, errorBody('bad_job_id', 'job_id 不能包含斜杠'))
        return
      }
      jsonResponse(res, 404, errorBody('no_such_route',
        '可用：POST /jobs · GET /jobs/{id} · POST /jobs/{id}/abort'))
    },
  })
}

/** Register all ingest-preview routes; returns the combined disposer. */
export function registerKsIngestRoutes(ctx, manager) {
  const disposers = [
    registerInboxDefaultRoute(ctx),
    registerInboxRoute(ctx, manager),
    registerPreviewRoute(ctx, manager),
    registerBatchRoute(ctx, manager),
    registerJobDispatcher(ctx, manager),
  ]
  return () => {
    // 递增代数是必须的（作废仍在飞的启动收尾）；"放在 stopJobPoll 之前"不是必须的
    // ——disposer 体全同步，两条语句之间不可能插入续体（复核实测：对调不改变结果）。
    // ⚠ 这里曾经**连 stopJobPoll 都没有**：而本模块的轮询是 `while(!jobTick(jobId))`，
    //   它**只在 `_jobPoll` 被清空时才自终止** ⇒ 卸载后仍会继续轮询（潜伏的泄漏，
    //   **不被 dispose 终止**；最长被 `JOB_RUNNING_CAP_MS`（6h）截断，期间反复 `ensureLive()`。
    //   ⚠ 复核 2026-09-19 提醒：我原先写的"无界"**说重了** —— 它是有 6h 上限的）。
    //   复核用变异体实测：卸载后 3.5s 内又 `ensureLive` 2 次。此前没人发现，
    //   是因为 adoptJob 的参数错位（§10.135 一）让轮询根本没跑起来。
    _jobEpoch += 1
    stopJobPoll()
    for (const dispose of disposers) dispose()
  }
}

