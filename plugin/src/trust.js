/**
 * ks-dsh-plugin — src/trust.js (2026-09-08, verifier P0-1 / P1-3 / P2-6)
 *
 * 统一的「同源信任栅栏」。本插件的 `/ks/*` 路由由 DSH web server 在
 * 127.0.0.1 上提供，但**浏览器不区分域名**：恶意页面可用 DNS rebinding（攻击者
 * 域名解析到 127.0.0.1）让请求在浏览器看来「同源」，从而读走 `/ks/session` 里的
 * 引擎 Bearer token、或直写本地状态（巡检/公告配置）。verifier 实测：只给凭据
 * 三条路由加守卫时，`GET /ks/session` 带伪造 Host 仍返回 200 + token。
 * 所以栅栏必须包住**全部** `/ks` 路由（由 `guardWebServer` 在 apply() 里统一
 * 套上，含未来新增路由），而不是逐个 handler 手写。
 *
 * 判据（fail-closed，任何一项不满足即拒）：
 * 1. `Host` 必须是可信 authority——默认只认回环（127.0.0.1 / localhost / ::1），
 *    部署方可用 `trustedHosts` 显式追加（DSH 支持 `--host 0.0.0.0` +
 *    `--trusted-host` 的局域网访问，此时必须声明，否则整栏 403）；
 * 2. 带 `Origin` 的请求，其 authority 必须与 `Host` **精确相等**（同源才算——
 *    只查回环会让 `http://localhost:9999` 这类别的本机页面也通过）；
 * 3. `Sec-Fetch-Site: cross-site` 一律拒绝（浏览器自报跨站）；
 * 4. 凭据写路由额外要求 `application/json`（挡 HTML 表单类简单请求；
 *    注意不能对**所有**写路由都要求 JSON——`POST /ks/inspection/run` 无 body
 *    无 content-type，是合法调用）。
 *
 * 只读请求（页面 fetch 的 GET）浏览器不带 Origin → 通过第 2 条，由第 1 条兜底。
 */

/** 默认可信 authority 名（去端口、小写）。 */
export const LOOPBACK_HOSTS = new Set(['127.0.0.1', 'localhost', '::1', '[::1]'])

/** Host/Origin 头 → {name, port}；畸形值返回 null（宁拒不放）。 */
export function parseAuthority(value) {
  if (typeof value !== 'string') return null
  const v = value.trim().toLowerCase().replace(/\.$/, '')
  if (v.length === 0) return null
  const m = /^(\[[0-9a-f:.]+\]|[^:\s/]+)(?::(\d{1,5}))?$/.exec(v)
  if (!m) return null
  return { name: m[1], port: m[2] ?? '' }
}

/** 可信 authority 名集合 = 回环 + 部署声明的 trustedHosts。 */
export function trustedNames(trustedHosts) {
  const names = new Set(LOOPBACK_HOSTS)
  if (Array.isArray(trustedHosts)) {
    for (const h of trustedHosts) {
      const auth = parseAuthority(typeof h === 'string' ? h : '')
      if (auth) names.add(auth.name)
    }
  }
  return names
}

function jsonResponse(res, status, code, message) {
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' })
  res.end(JSON.stringify({ ok: false, error: { code, message } }))
}

/**
 * 凭据写路由用：强制 `application/json` 请求体。返回 false 表示已写出 415。
 * 信任判定由外层 guardRoute 负责（不在这里重复，避免两处 trustedHosts 不一致）。
 */
export function requireJsonBody(req, res) {
  const ct = String(req.headers?.['content-type'] ?? '').toLowerCase()
  if (!ct.startsWith('application/json')) {
    jsonResponse(res, 415, 'unsupported_media_type',
      'Content-Type 必须为 application/json')
    return false
  }
  return true
}

/**
 * 栅栏本体。返回 false 表示已写出 4xx，调用方必须直接 return。
 * @param {import('node:http').IncomingMessage} req
 * @param {import('node:http').ServerResponse} res
 * @param {{trustedHosts?: string[]}} [opts]
 */
export function guardRequest(req, res, opts = {}) {
  const names = trustedNames(opts.trustedHosts)
  const host = parseAuthority(req.headers?.host)
  if (!host || !names.has(host.name)) {
    jsonResponse(res, 403, 'forbidden_origin',
      `仅允许可信本机地址访问（当前 Host: ${req.headers?.host ?? '(缺失)'}）；`
      + '如通过局域网访问，请在插件配置 trustedHosts 中声明该地址')
    return false
  }
  const rawOrigin = req.headers?.origin
  if (typeof rawOrigin === 'string' && rawOrigin.length > 0) {
    if (rawOrigin === 'null') {
      jsonResponse(res, 403, 'forbidden_origin', '拒绝不带 authority 的 Origin')
      return false
    }
    let origin
    try {
      origin = new URL(rawOrigin)
    } catch {
      jsonResponse(res, 403, 'forbidden_origin', `无法解析 Origin: ${rawOrigin}`)
      return false
    }
    const oa = parseAuthority(origin.host)
    if (!oa || !names.has(oa.name) || oa.name !== host.name || oa.port !== host.port) {
      jsonResponse(res, 403, 'forbidden_origin',
        `拒绝跨站请求（Origin: ${rawOrigin} ≠ Host: ${req.headers?.host ?? ''}）`)
      return false
    }
  }
  const site = String(req.headers?.['sec-fetch-site'] ?? '').toLowerCase()
  if (site === 'cross-site') {
    jsonResponse(res, 403, 'forbidden_origin', '拒绝跨站请求（Sec-Fetch-Site: cross-site）')
    return false
  }
  return true
}

/** 给一条 webServer 路由套上栅栏（handler 原样保留）。 */
export function guardRoute(route, opts = {}) {
  if (!route || typeof route.handler !== 'function') return route
  const inner = route.handler
  return {
    ...route,
    handler: async (req, res) => {
      if (!guardRequest(req, res, opts)) return
      return inner(req, res)
    },
  }
}

/**
 * webServer 门面：`register()` 出来的每条路由自动带栅栏。
 * apply() 用它替代 `ctx.webServer`，即可覆盖全部 `/ks` 路由（含未来新增）。
 */
export function guardWebServer(webServer, opts = {}) {
  return {
    register: (route) => webServer.register(guardRoute(route, opts)),
  }
}
