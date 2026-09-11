/**
 * ks-dsh-plugin — src/settings.js (API 配置, 2026-09-08)
 *
 * 引擎「设置→API配置」的 host 代理：云 OCR（MinerU 官方云）与 LLM 通道的
 * Key/Base URL 管理 + 活体连通探测。
 *
 * 信任模型：**纯代理零缓存**——凭据只由引擎写入 Windows 用户注册表
 * （HKCU\Environment，与 setx 同落点），host 不落盘、不回显、不记日志；
 * 引擎响应本身已脱敏（只给 configured 布尔 + base_url）。
 *
 * 通道语义（2026-09-08 用户修订）：导入文件时——配置了云 OCR Key → 云优先、
 * 本地兜底；未配置 → 直接本地通道（纯本地不外发）。见引擎
 * src/core/ingestion/mineru_adapter.py::_cloud_enabled。
 *
 * Routes:
 *   GET  /ks/settings/api-config        脱敏状态（configured/base_url）
 *   PUT  /ks/settings/api-config        写入凭据（引擎侧立即 reset 缓存）
 *   POST /ks/settings/api-config/test   活体探测 {channel}
 *
 * 安全：Host/Origin 信任栅栏由 trust.js 在 apply() 统一套到**全部** /ks 路由
 * （verifier P0-1）；本文件只额外要求写请求体为 application/json。
 *
 * Only Node builtins + ./engine.js / ./trust.js helpers — no cordis import.
 */

import { originUrl } from './engine.js'
import { requireJsonBody } from './trust.js'

export const KS_API_CONFIG_PATH = '/ks/settings/api-config'
export const KS_API_CONFIG_TEST_PATH = '/ks/settings/api-config/test'

const ENGINE_API_CONFIG_PATH = '/api/v1/settings/api-config'
const BODY_CAP = 16_384

function jsonResponse(res, status, body) {
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' })
  res.end(JSON.stringify(body))
}

function errorBody(code, message) {
  return { ok: false, error: { code, message } }
}

/**
 * 凭据写路由的**额外**要求：请求体必须是 application/json（挡 HTML 表单类简单请求）。
 * Host/Origin 的信任判定已由 trust.js 的全局栅栏完成（见 index.js apply()），
 * 这里不重复做，避免两处 trustedHosts 口径不一致（verifier P1-3）。
 */

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

/** 通用引擎请求（GET/PUT/POST；apiGet/apiPost 覆盖不到 PUT）。 */
async function engineRequest(method, base, path, { token, timeoutMs = 30_000, body } = {}) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  const headers = { accept: 'application/json' }
  if (token) headers.Authorization = `Bearer ${token}`
  if (body !== undefined) headers['content-type'] = 'application/json'
  try {
    const res = await fetch(`${base}${path}`, {
      method,
      headers,
      signal: controller.signal,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
    let parsed = null
    try { parsed = await res.json() } catch { /* non-JSON */ }
    return { status: res.status, body: parsed }
  } catch (error) {
    return {
      status: 0,
      body: null,
      error: error instanceof Error ? error.message : String(error),
    }
  } finally {
    clearTimeout(timer)
  }
}

/** 引擎响应 → 同源响应：成功透传 data，失败按状态码映射。 */
function mapProbe(res, probe) {
  if (probe.status === 200 && probe.body && typeof probe.body === 'object') {
    // 引擎的 api-config 响应是扁平 {ok, mineru_cloud, llm}（无 data 信封）
    const { ok, ...rest } = probe.body
    jsonResponse(res, 200, { ok: true, ...rest })
    return
  }
  if (probe.status === 422 || probe.status === 400) {
    const code = probe.body && typeof probe.body === 'object' ? probe.body.error : null
    const message = probe.body && typeof probe.body === 'object' && probe.body.message
      ? String(probe.body.message) : '非法参数'
    jsonResponse(res, 400, errorBody(typeof code === 'string' ? code : 'invalid_params', message))
    return
  }
  if (probe.status === 500) {
    const message = probe.body && typeof probe.body === 'object' && probe.body.message
      ? String(probe.body.message) : '引擎写入失败'
    jsonResponse(res, 502, errorBody('engine_write_failed', message))
    return
  }
  jsonResponse(res, 502, errorBody('engine_error',
    `引擎返回 HTTP ${probe.status}: ${probe.error || 'no response'}`))
}

/** Register API-config routes; returns the combined disposer. */
export function registerKsSettingsRoutes(ctx, manager) {
  const withSession = async (res, fn) => {
    let session
    try {
      session = await manager.ensureLive()
    } catch (err) {
      jsonResponse(res, 503, errorBody('engine_unavailable',
        err instanceof Error ? err.message : String(err)))
      return
    }
    await fn(session)
  }

  const disposers = [
    ctx.webServer.register({
      kind: 'exact',
      path: KS_API_CONFIG_PATH,
      handler: async (req, res) => {
        if (req.method === 'GET') {
          await withSession(res, async (session) => {
            const probe = await engineRequest('GET', originUrl(session.port),
              ENGINE_API_CONFIG_PATH, { token: session.token })
            mapProbe(res, probe)
          })
          return
        }
        if (req.method === 'PUT') {
          if (!requireJsonBody(req, res)) return
          let raw
          try {
            raw = await readJsonBody(req)
          } catch {
            jsonResponse(res, 400, errorBody('bad_request', 'body 必须是合法 JSON'))
            return
          }
          // 白名单：只接受两个通道对象，字段由引擎再校验
          const body = {}
          for (const ch of ['mineru_cloud', 'llm']) {
            const sec = raw && typeof raw === 'object' ? raw[ch] : null
            if (sec && typeof sec === 'object') {
              const clean = {}
              if (typeof sec.api_key === 'string') clean.api_key = sec.api_key
              if (typeof sec.base_url === 'string') clean.base_url = sec.base_url
              if (Object.keys(clean).length > 0) body[ch] = clean
            }
          }
          if (Object.keys(body).length === 0) {
            jsonResponse(res, 400, errorBody('empty_payload', '未提供任何凭据字段'))
            return
          }
          await withSession(res, async (session) => {
            const probe = await engineRequest('PUT', originUrl(session.port),
              ENGINE_API_CONFIG_PATH, { token: session.token, body })
            mapProbe(res, probe)
          })
          return
        }
        jsonResponse(res, 405, errorBody('method_not_allowed', 'GET or PUT'))
      },
    }),
    ctx.webServer.register({
      kind: 'exact',
      path: KS_API_CONFIG_TEST_PATH,
      handler: async (req, res) => {
        if (req.method !== 'POST') {
          jsonResponse(res, 405, errorBody('method_not_allowed', 'POST only'))
          return
        }
        if (!requireJsonBody(req, res)) return
        let raw
        try {
          raw = await readJsonBody(req)
        } catch {
          jsonResponse(res, 400, errorBody('bad_request', 'body 必须是合法 JSON'))
          return
        }
        const channel = typeof raw.channel === 'string' ? raw.channel : ''
        if (channel !== 'mineru_cloud' && channel !== 'llm') {
          jsonResponse(res, 400, errorBody('unknown_channel', `未知通道: ${channel || '(空)'}`))
          return
        }
        await withSession(res, async (session) => {
          const probe = await engineRequest('POST', originUrl(session.port),
            `${ENGINE_API_CONFIG_PATH}/test`,
            { token: session.token, timeoutMs: 60_000, body: { channel } })
          mapProbe(res, probe)
        })
      },
    }),
  ]
  return () => {
    for (const dispose of disposers) dispose()
  }
}
