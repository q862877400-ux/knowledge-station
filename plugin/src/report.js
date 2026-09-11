/**
 * ks-dsh-plugin — src/report.js (效力报告, 决策 21 · 用户修订版, 2026-09)
 *
 * Host-half wiring for the engine's effect-report aggregation (库内现行快照，
 * 按文件目录分类体系组织——永不混排，用户修订拍板；设计 verify_rollout
 * 三路择优 0.516)。
 *
 * 与 inspection/announce 的刻意区别：**纯代理零缓存零状态文件**——报告是
 * 即时聚合快照（每个请求现拉引擎），不是跨进程触发真值；ensureLive 的
 * 单实例/复用纪律照旧。401 → 重读会话重试一次（token 轮换自愈）。
 *
 * Routes:
 *   GET  /ks/report/effect        骨架+四色统计（query 白名单透传）
 *   GET  /ks/report/effect/docs   节点明细（瘦身行；query 白名单透传）
 *   POST /ks/report/export        两步代理（引擎 xlsx → /export/download →
 *                                 同源 attachment 回传；镜像 inspection.js）
 *
 * Only Node builtins + ./engine.js helpers — no cordis import.
 */

import { apiGet, apiPost, originUrl } from './engine.js'

export const KS_REPORT_EFFECT_PATH = '/ks/report/effect'
export const KS_REPORT_DOCS_PATH = '/ks/report/effect/docs'
export const KS_REPORT_EXPORT_PATH = '/ks/report/export'

const ENGINE_EFFECT_PATH = '/api/v1/report/effect'
const ENGINE_DOCS_PATH = '/api/v1/report/effect/docs'
const ENGINE_EXPORT_PATH = '/api/v1/report/effect/export'
const ENGINE_DOWNLOAD_PATH = '/api/v1/export/download'

const BODY_CAP = 65_536
const XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

/* ------------------------------------------------------------------ *
 * Helpers（与 announce.js 同款独立 helper：模块保持 smoke 可加载纯度）
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
    const fail = (err) => {
      if (done) return
      done = true
      reject(err)
    }
    req.on('data', (chunk) => {
      if (done) return
      size += chunk.length
      if (size > BODY_CAP) {
        fail(new Error('request body too large'))
        req.destroy()
        return
      }
      chunks.push(chunk)
    })
    req.on('end', () => {
      if (done) return
      done = true
      try {
        const text = Buffer.concat(chunks).toString('utf8')
        resolve(text.length === 0 ? {} : JSON.parse(text))
      } catch (err) {
        reject(err)
      }
    })
    req.on('error', fail)
  })
}

/** GET with one 401 self-heal retry（token 轮换 → ensureLive 重读 session）。 */
async function engineGetWithRetry(manager, path) {
  let session = await manager.ensureLive()
  let probe = await apiGet(originUrl(session.port), path,
    { token: session.token, timeoutMs: 20_000 })
  if (probe.status === 401) {
    session = await manager.ensureLive()
    probe = await apiGet(originUrl(session.port), path,
      { token: session.token, timeoutMs: 20_000 })
  }
  return probe
}

/** GET one binary resource through the engine（导出文件下载）。 */
async function fetchBinary(base, path, { token, timeoutMs = 30_000 } = {}) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  const headers = {}
  if (token) headers.Authorization = `Bearer ${token}`
  try {
    const res = await fetch(`${base}${path}`, { headers, signal: controller.signal })
    const buffer = await res.arrayBuffer()
    return { status: res.status, ok: res.ok, buffer }
  } catch (error) {
    return {
      status: 0,
      ok: false,
      buffer: null,
      error: error instanceof Error ? error.message : String(error),
    }
  } finally {
    clearTimeout(timer)
  }
}

/** query 白名单清洗：只保留允许键且值非空（未知键丢弃，防透传面扩大）。 */
/** query 白名单清洗：只保留允许键且值非空（未知键丢弃，防透传面扩大）。
 *  用 URLSearchParams 解析——标准语义会把 + 还原为空格。真机回归教训：
 *  旧实现 decodeURIComponent 不还原 +，而 client 的 URLSearchParams 把空格
 *  编码为 +，含空格的类目名（"C 医药…"）到引擎变成 "C+医药…"，精确匹配
 *  落空 → UI 全显示"（无文档）"。 */
function pickQuery(reqUrl, allowed) {
  const out = {}
  const qs = (reqUrl || '').split('?')[1]
  if (!qs) return out
  for (const [k, v] of new URLSearchParams(qs).entries()) {
    if (allowed.includes(k) && v !== '') out[k] = v
  }
  return out
}

/** 引擎 GET 聚合结果 → 同源响应统一映射（401 已在 engineGetWithRetry 自愈）。 */
function mapProbe(res, probe, engineErrorStatus = 502) {
  if (probe.status === 200 && probe.body && typeof probe.body === 'object') {
    jsonResponse(res, 200, { ok: true, data: probe.body.data ?? {} })
    return
  }
  if (probe.status === 422) {
    const code = probe.body && typeof probe.body === 'object' ? probe.body.error : null
    const message = probe.body && typeof probe.body === 'object' && probe.body.message
      ? String(probe.body.message) : '非法参数'
    jsonResponse(res, 400, errorBody(typeof code === 'string' ? code : 'invalid_params', message))
    return
  }
  jsonResponse(res, engineErrorStatus, errorBody('engine_error',
    `引擎返回 HTTP ${probe.status}: ${probe.error || probe.text || 'no response'}`))
}

/* ------------------------------------------------------------------ *
 * Routes
 * ------------------------------------------------------------------ */

function registerEffectRoute(ctx, manager) {
  return ctx.webServer.register({
    kind: 'exact',
    path: KS_REPORT_EFFECT_PATH,
    handler: async (req, res) => {
      if (req.method !== 'GET') {
        jsonResponse(res, 405, errorBody('method_not_allowed', 'GET only'))
        return
      }
      const q = pickQuery(req.url, ['window', 'color'])
      const qs = new URLSearchParams(q).toString()
      try {
        const probe = await engineGetWithRetry(
          manager, qs ? `${ENGINE_EFFECT_PATH}?${qs}` : ENGINE_EFFECT_PATH)
        mapProbe(res, probe)
      } catch (err) {
        jsonResponse(res, 503, errorBody('engine_unavailable',
          err instanceof Error ? err.message : String(err)))
      }
    },
  })
}

function registerDocsRoute(ctx, manager) {
  return ctx.webServer.register({
    kind: 'exact',
    path: KS_REPORT_DOCS_PATH,
    handler: async (req, res) => {
      if (req.method !== 'GET') {
        jsonResponse(res, 405, errorBody('method_not_allowed', 'GET only'))
        return
      }
      const q = pickQuery(req.url, ['top', 'l2', 'l3', 'l4', 'window', 'color',
        'limit', 'offset'])
      const qs = new URLSearchParams(q).toString()
      try {
        const probe = await engineGetWithRetry(
          manager, qs ? `${ENGINE_DOCS_PATH}?${qs}` : ENGINE_DOCS_PATH)
        mapProbe(res, probe)
      } catch (err) {
        jsonResponse(res, 503, errorBody('engine_unavailable',
          err instanceof Error ? err.message : String(err)))
      }
    },
  })
}

function registerExportRoute(ctx, manager) {
  return ctx.webServer.register({
    kind: 'exact',
    path: KS_REPORT_EXPORT_PATH,
    handler: async (req, res) => {
      if (req.method !== 'POST') {
        jsonResponse(res, 405, errorBody('method_not_allowed', 'POST only'))
        return
      }
      let raw
      try {
        raw = await readJsonBody(req)
      } catch {
        jsonResponse(res, 400, errorBody('bad_request', 'body 必须是合法 JSON'))
        return
      }
      const body = {}
      if (typeof raw.window === 'string' && raw.window) body.window = raw.window
      if (raw.color !== undefined) body.color = raw.color
      let session
      try {
        session = await manager.ensureLive()
      } catch (err) {
        jsonResponse(res, 503, errorBody('engine_unavailable',
          err instanceof Error ? err.message : String(err)))
        return
      }
      // 1) 引擎生成 xlsx（全量聚合可能耗时：给足超时）
      const build = await apiPost(originUrl(session.port), ENGINE_EXPORT_PATH,
        { token: session.token, timeoutMs: 90_000, body })
      if (build.status !== 200) {
        if (build.status === 422) {
          const code = build.body && typeof build.body === 'object' ? build.body.error : null
          jsonResponse(res, 400, errorBody(typeof code === 'string' ? code : 'invalid_params',
            build.body?.message ?? '非法参数'))
          return
        }
        jsonResponse(res, 502, errorBody('engine_error',
          `引擎导出失败 HTTP ${build.status}: ${build.error || build.text || 'no response'}`))
        return
      }
      const name = build.body?.data?.name
      if (typeof name !== 'string' || !name) {
        jsonResponse(res, 502, errorBody('engine_bad_response', '引擎未返回导出文件名'))
        return
      }
      // 2) 取字节同源回传（token 只在 host→引擎段）
      const dl = await fetchBinary(originUrl(session.port),
        `${ENGINE_DOWNLOAD_PATH}?name=${encodeURIComponent(name)}`,
        { token: session.token, timeoutMs: 90_000 })
      if (dl.status !== 200 || !dl.buffer) {
        jsonResponse(res, 502, errorBody('download_failed',
          `下载导出文件失败（HTTP ${dl.status}）`))
        return
      }
      const asciiFallback = name.replace(/[^\x20-\x7e]/g, '_')
      res.writeHead(200, {
        'Content-Type': XLSX_MIME,
        'Content-Length': dl.buffer.byteLength,
        'Content-Disposition': `attachment; filename="${asciiFallback}"; filename*=UTF-8''${encodeURIComponent(name)}`,
      })
      res.end(Buffer.from(dl.buffer))
    },
  })
}

/** Register all three report routes; returns the combined disposer. */
export function registerKsReportRoutes(ctx, manager) {
  const disposers = [
    registerEffectRoute(ctx, manager),
    registerDocsRoute(ctx, manager),
    registerExportRoute(ctx, manager),
  ]
  return () => {
    for (const dispose of disposers) dispose()
  }
}
