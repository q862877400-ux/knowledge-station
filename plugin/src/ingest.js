/**
 * ks-dsh-plugin — src/ingest.js（R27 入库预览 / 批量分桶 host 半，2026-09-11）
 *
 * 把引擎侧**只读**的 R27 预览端点接到同源 `/ks/` 面上，供 📥 入库预览面板使用。
 * 引擎端点（`src/core/api/routes_ingest_preview.py`）：
 *   POST /api/v1/ingest/preview           单本 R27 完整体检报告
 *   POST /api/v1/ingest/preview/batch     目录批量 + ✅/⚠️/❌ 分桶
 *   GET  /api/v1/ingest/preview/inbox     列候选 PDF（只列名/大小）
 *
 * ## 设计纪律（与 inspection/announce 的刻意区别）
 * 纯代理、**零缓存、零状态文件**：预览是"此刻这批文件长什么样"的即时快照，
 * 不是跨进程触发真值（那才需要状态文件）。引擎懒拉起/单实例复用照旧。
 *
 * ## 待入库目录（inbox）
 * 浏览器无法浏览本机目录，所以给一个**可预期的落点**：默认
 * `%USERPROFILE%\Documents\KnowledgeStation\待入库`。host 只在被请求时按需创建
 * （`mkdir -p` 语义、幂等、只在自己的数据目录语义下），并把解析后的绝对路径回给 UI，
 * 让用户知道该把 PDF 放哪。**host 不读文件内容**——预览一律由引擎做。
 *
 * ## 只读红线
 * host 侧只做「列目录 + 转发」；不移动/复制/改写用户文件；不写库。
 *
 * Only Node builtins + ./engine.js helpers — no cordis import.
 */

import { mkdir, readdir, stat } from 'node:fs/promises'
import { homedir } from 'node:os'
import { basename, extname, join, resolve } from 'node:path'

import { apiGet, apiPost, originUrl } from './engine.js'

export const KS_INGEST_INBOX_PATH = '/ks/ingest/inbox'
export const KS_INGEST_INBOX_DEFAULT_PATH = '/ks/ingest/inbox-default'
export const KS_INGEST_PREVIEW_PATH = '/ks/ingest/preview'
export const KS_INGEST_BATCH_PATH = '/ks/ingest/preview/batch'

const ENGINE_INBOX_PATH = '/api/v1/ingest/preview/inbox'
const ENGINE_PREVIEW_PATH = '/api/v1/ingest/preview'
const ENGINE_BATCH_PATH = '/api/v1/ingest/preview/batch'

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
      // 只透传白名单字段；`allow_deep` 不暴露（预览零外发是产品性质，不给开关）
      const payload = {}
      if (typeof body.path === 'string' && body.path.trim()) payload.path = body.path.trim()
      if (typeof body.doc_type === 'string' && body.doc_type.trim()) {
        payload.doc_type = body.doc_type.trim()
      }
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

/** Register all ingest-preview routes; returns the combined disposer. */
export function registerKsIngestRoutes(ctx, manager) {
  const disposers = [
    registerInboxDefaultRoute(ctx),
    registerInboxRoute(ctx, manager),
    registerPreviewRoute(ctx, manager),
    registerBatchRoute(ctx, manager),
  ]
  return () => {
    for (const dispose of disposers) dispose()
  }
}

/** 供 smoke 断言（不参与运行时逻辑）。 */
export const __internals = { listPdfs, basename }
