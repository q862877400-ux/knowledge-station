/**
 * ks-dsh-plugin — scripts/smoke-settings-guard.mjs
 *
 * Host-side smoke for the SAME-ORIGIN TRUST FENCE (verifier F9 + P0-1/P1-3/P2-6).
 *
 * Why: `/ks/*` routes are served by the DSH web server on 127.0.0.1, but the
 * browser does not distinguish hostnames — a DNS-rebinding page (attacker domain
 * resolving to 127.0.0.1) can read `/ks/session`'s engine Bearer token or write
 * local state. verifier measured exactly that when only the 3 credential routes
 * were guarded, so the fence now wraps EVERY `/ks` route via `guardWebServer`
 * (see index.js apply()). This smoke runs the REAL wrapper + the REAL handlers
 * with a fake manager whose ensureLive() always throws: reaching the engine
 * stage (503 engine_unavailable) proves the request was allowed through, while
 * 403/415/400 prove it was rejected before any engine call.
 *
 * Run:  node scripts/smoke-settings-guard.mjs     (exit 0 = all cases pass)
 */

import { EventEmitter } from 'node:events'

import { registerKsSettingsRoutes } from '../src/settings.js'
import { guardWebServer } from '../src/trust.js'

const CONFIG_PATH = '/ks/settings/api-config'
const TEST_PATH = '/ks/settings/api-config/test'
const LOOPBACK = { host: '127.0.0.1:3080', origin: 'http://127.0.0.1:3080' }

/** Fake IncomingMessage: real EventEmitter so readJsonBody() can stream it. */
function fakeReq({ method = 'GET', headers = {}, body = '', url = CONFIG_PATH } = {}) {
  const req = new EventEmitter()
  req.method = method
  req.headers = headers
  req.url = url
  req.destroy = () => {}
  process.nextTick(() => {
    if (body) req.emit('data', Buffer.from(body, 'utf8'))
    req.emit('end')
  })
  return req
}

function fakeRes() {
  return {
    status: 0,
    body: null,
    writeHead(status) { this.status = status },
    end(text) {
      try { this.body = text ? JSON.parse(text) : null } catch { this.body = text }
    },
  }
}

/** Capture the registered handlers instead of a real web server. */
function captureHandlers(trustOpts = {}) {
  const byPath = new Map()
  const webServer = {
    register(route) {
      byPath.set(route.path, route.handler)
      return () => byPath.delete(route.path)
    },
  }
  // 真实门面：所有路由都自动带栅栏（与 apply() 同款接线）
  const ctx = { webServer: guardWebServer(webServer, trustOpts) }
  const manager = {
    ensureLive: async () => { throw new Error('stub-no-engine') },
  }
  const dispose = registerKsSettingsRoutes(ctx, manager)
  // 一条非凭据路由：证明栅栏覆盖的是全部 /ks 路由，不只凭据三条（P0-1）
  let nonCredentialHit = false
  ctx.webServer.register({
    kind: 'exact',
    path: '/ks/inspection/summary',
    handler: async (req, res) => {
      nonCredentialHit = true
      res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' })
      res.end(JSON.stringify({ ok: true }))
    },
  })
  return { byPath, dispose, isNonCredentialHit: () => nonCredentialHit }
}

const results = []
function check(name, ok, detail) {
  results.push({ name, ok, detail })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail ? ` — ${detail}` : ''}`)
}

async function call(handler, reqOpts) {
  const res = fakeRes()
  await handler(fakeReq(reqOpts), res)
  return res
}

async function main() {
  console.log('=== ks-dsh-plugin same-origin trust fence smoke ===')
  const { byPath, dispose, isNonCredentialHit } = captureHandlers()
  const config = byPath.get(CONFIG_PATH)
  const test = byPath.get(TEST_PATH)
  check('routes registered', typeof config === 'function' && typeof test === 'function')

  // ---- 1. DNS rebinding: Host is an attacker domain → 403, no engine call
  const rebind = await call(config, {
    method: 'GET', headers: { host: 'evil.example.com:3080' },
  })
  check('rebind Host blocked (GET)', rebind.status === 403
    && rebind.body?.error?.code === 'forbidden_origin', `status=${rebind.status}`)

  const rebindPut = await call(config, {
    method: 'PUT',
    headers: { host: 'evil.example.com:3080', 'content-type': 'application/json' },
    body: JSON.stringify({ mineru_cloud: { api_key: 'x' } }),
  })
  check('rebind Host blocked (PUT, before engine)', rebindPut.status === 403,
    `status=${rebindPut.status}`)

  // ---- 2. missing Host (HTTP/1.0-ish) → 403 fail-closed
  const noHost = await call(config, { method: 'GET', headers: {} })
  check('missing Host blocked', noHost.status === 403, `status=${noHost.status}`)

  // ---- 3. NON-credential route is fenced too (P0-1 regression)
  const nonCred = await call(byPath.get('/ks/inspection/summary'), {
    method: 'GET', headers: { host: 'evil.example.com:3080' },
  })
  check('non-credential /ks route fenced (P0-1)', nonCred.status === 403
    && isNonCredentialHit() === false, `status=${nonCred.status}`)

  // ---- 4. legitimate loopback request passes the fence
  const okLoop = await call(config, {
    method: 'PUT',
    headers: { ...LOOPBACK, 'content-type': 'application/json' },
    body: JSON.stringify({ mineru_cloud: { api_key: 'x' } }),
  })
  check('loopback request passes fence', okLoop.status === 503
    && okLoop.body?.error?.code === 'engine_unavailable', `status=${okLoop.status}`)

  const ipv6 = await call(config, {
    method: 'GET', headers: { host: '[::1]:3080' },
  })
  check('IPv6 loopback accepted', ipv6.status === 503, `status=${ipv6.status}`)

  // ---- 5. cross-site Origin / authority mismatch (P2-6) → 403
  const crossSite = await call(config, {
    method: 'PUT',
    headers: {
      host: '127.0.0.1:3080', origin: 'https://evil.example.com',
      'content-type': 'application/json',
    },
    body: JSON.stringify({ mineru_cloud: { api_key: 'x' } }),
  })
  check('cross-site Origin blocked', crossSite.status === 403
    && crossSite.body?.error?.code === 'forbidden_origin', `status=${crossSite.status}`)

  const otherPort = await call(config, {
    method: 'PUT',
    headers: {
      host: '127.0.0.1:3080', origin: 'http://localhost:9999',
      'content-type': 'application/json',
    },
    body: JSON.stringify({ mineru_cloud: { api_key: 'x' } }),
  })
  check('loopback-but-different-authority blocked', otherPort.status === 403,
    `status=${otherPort.status}`)

  const crossFetch = await call(config, {
    method: 'GET', headers: { ...LOOPBACK, 'sec-fetch-site': 'cross-site' },
  })
  check('Sec-Fetch-Site: cross-site blocked', crossFetch.status === 403,
    `status=${crossFetch.status}`)

  const sameFetch = await call(config, {
    method: 'GET', headers: { ...LOOPBACK, 'sec-fetch-site': 'same-origin' },
  })
  check('Sec-Fetch-Site: same-origin accepted', sameFetch.status === 503,
    `status=${sameFetch.status}`)

  // ---- 6. LAN deployment: 403 by default, allowed once declared (P1-3)
  const lan = await call(config, { method: 'GET', headers: { host: '192.168.1.5:3080' } })
  check('undeclared LAN Host blocked', lan.status === 403, `status=${lan.status}`)

  const lanOpts = captureHandlers({ trustedHosts: ['192.168.1.5'] })
  const lanOk = await call(lanOpts.byPath.get(CONFIG_PATH), {
    method: 'GET',
    headers: { host: '192.168.1.5:3080', origin: 'http://192.168.1.5:3080' },
  })
  check('declared trustedHosts accepted (P1-3)', lanOk.status === 503, `status=${lanOk.status}`)
  lanOpts.dispose()

  // ---- 7. non-JSON content-type (HTML form / simple request) → 415
  const form = await call(config, {
    method: 'PUT',
    headers: { ...LOOPBACK, 'content-type': 'application/x-www-form-urlencoded' },
    body: 'mineru_cloud.api_key=x',
  })
  check('non-JSON content-type blocked', form.status === 415
    && form.body?.error?.code === 'unsupported_media_type', `status=${form.status}`)

  const noCt = await call(config, {
    method: 'PUT', headers: { ...LOOPBACK }, body: '{}',
  })
  check('missing content-type blocked', noCt.status === 415, `status=${noCt.status}`)

  // ---- 8. malformed JSON / empty whitelist / unknown channel
  const badJson = await call(config, {
    method: 'PUT',
    headers: { ...LOOPBACK, 'content-type': 'application/json' },
    body: '{not json',
  })
  check('malformed JSON → 400', badJson.status === 400
    && badJson.body?.error?.code === 'bad_request', `status=${badJson.status}`)

  const empty = await call(config, {
    method: 'PUT',
    headers: { ...LOOPBACK, 'content-type': 'application/json' },
    body: JSON.stringify({ mineru_cloud: { provider: 'x' } }),
  })
  check('no whitelisted field → 400', empty.status === 400
    && empty.body?.error?.code === 'empty_payload', `status=${empty.status}`)

  // 2026-09-15：model_version（MinerU 云模式，非密值）必须能穿过白名单到达引擎。
  // 引擎未起时表现为 503（= 已放行、只是引擎不在）——与 valid probe 同款判据。
  const modeOnly = await call(config, {
    method: 'PUT',
    headers: { ...LOOPBACK, 'content-type': 'application/json' },
    body: JSON.stringify({ mineru_cloud: { model_version: 'vlm' } }),
  })
  check('model_version-only PUT passes whitelist', modeOnly.status === 503,
    `status=${modeOnly.status} code=${modeOnly.body?.error?.code ?? ''}`)

  const modeOnLlm = await call(config, {
    method: 'PUT',
    headers: { ...LOOPBACK, 'content-type': 'application/json' },
    body: JSON.stringify({ llm: { api_key: 'k', model_version: 'vlm' } }),
  })
  check('llm 通道不转发 model_version（仍能保存 api_key）',
    modeOnLlm.status === 503, `status=${modeOnLlm.status}`)

  const badChannel = await call(test, {
    method: 'POST',
    headers: { ...LOOPBACK, 'content-type': 'application/json' },
    body: JSON.stringify({ channel: 'openai' }),
  })
  check('unknown channel → 400', badChannel.status === 400
    && badChannel.body?.error?.code === 'unknown_channel', `status=${badChannel.status}`)

  const probe = await call(test, {
    method: 'POST',
    headers: { ...LOOPBACK, 'content-type': 'application/json' },
    body: JSON.stringify({ channel: 'mineru_cloud' }),
  })
  check('valid probe reaches engine', probe.status === 503, `status=${probe.status}`)

  const wrongMethod = await call(test, { method: 'GET', headers: { ...LOOPBACK } })
  check('probe GET → 405', wrongMethod.status === 405, `status=${wrongMethod.status}`)

  dispose()
  const failed = results.filter((r) => !r.ok)
  console.log(`\n== fence smoke ${failed.length === 0 ? 'PASS' : 'FAIL'} `
    + `(${results.length - failed.length}/${results.length}) ==`)
  process.exit(failed.length === 0 ? 0 : 1)
}

main().catch((err) => {
  console.error(`[fatal] ${err && err.stack ? err.stack : err}`)
  process.exit(1)
})
