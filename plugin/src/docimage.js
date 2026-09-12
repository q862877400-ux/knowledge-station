/**
 * ks-dsh-plugin — src/docimage.js
 *
 * 文档图片同源代理（2026-09-13 端点接线 · ZERO→LIVE 三连）：
 *
 *   GET /ks/doc-image/<doc_id>/figure/<fig_no>?dpi=…        → 引擎 PNG 截图/矢量重绘
 *   GET /ks/doc-image/<doc_id>/formula/<fno>?clause=…&dpi=…  → 引擎公式原图 PNG
 *   GET /ks/doc-image/<doc_id>/table-image/<page>/<tbl>?dpi=… → 引擎带图表格整表截图
 *
 * 背景：引擎三端点（/api/v1/documents/{id}/figure|formula|table-image，见
 * server.py L225/L379/L441）自 2026-09-02 起实现完备，但旧独立前端（App.tsx）
 * 退役后无任何 GUI 消费者——2026-09-13 端点消费图谱把它们归为 ZERO「未接线」。
 * 本路由 + client 正文视图（KsEvidenceTab 正文模式 + api.ts fetchers）补上
 * host 代理这一半：token 只在 host→引擎段，页面只拿同源 PNG。
 *
 * 设计约束（与 /ks/bbox 同款信任模型）：
 *   - 只读代理，零缓存零状态；
 *   - 引擎 404 → 状态码 404 透传 + 本地信封 ks_image_not_found（前端隐藏占位图，不是错误）；
 *   - X-Frac-* 头逐字转发（截图按原版比例还原的展示契约）；
 *   - dpi 由 host 钳制（72~300），query 原样拼接。
 */

import { apiGetBytes, originUrl } from './engine.js'

export const KS_DOC_IMAGE_PATH = '/ks/doc-image'

/** 引擎转发头白名单：X-Frac-* 是截图比例契约（三端点共用）。
 *  对 = [fetch 小写名（Headers.get 大小写不敏感）, 线上写出的规范名]。 */
const FORWARD_HEADERS = [
  ['x-frac-x0', 'X-Frac-X0'],
  ['x-frac-w', 'X-Frac-W'],
  ['x-frac-h', 'X-Frac-H'],
]

/** dpi 值域（与引擎端 max(72, min(300, …)) 一致——host 侧先钳一遍防脏查询串）。 */
function clampDpi(raw) {
  const n = Number.parseInt(raw ?? '', 10)
  if (!Number.isFinite(n)) return 144
  return Math.min(300, Math.max(72, n))
}

/**
 * 解析 /ks/doc-image/ 前缀后的子路径。
 * @returns {{docId:string, enginePath:string}|null} 非法形态 → null（400）。
 *
 * 三种合法形态（与引擎路由一一对应）：
 *   <doc>/figure/<fig_no>            → /api/v1/documents/<doc>/figure/<fig_no>
 *   <doc>/formula/<fno>?clause=…     → /api/v1/documents/<doc>/formula/<fno>?clause=…
 *   <doc>/table-image/<page>/<tbl>   → /api/v1/documents/<doc>/table-image/<page>/<tbl>
 */
export function parseDocImagePath(subPath, query) {
  // subPath 形如 "<doc>/<kind>/<…>"；doc_id 与编号段各自 encodeURIComponent 防注入。
  const segs = subPath.split('/').filter((s) => s.length > 0)
  if (segs.length < 2) return null
  const [docId, kind, ...rest] = segs
  const enc = encodeURIComponent
  if (kind === 'figure' && rest.length === 1 && rest[0].length > 0) {
    return { docId, enginePath: `/api/v1/documents/${enc(docId)}/figure/${enc(rest[0])}` }
  }
  if (kind === 'formula' && rest.length === 1 && rest[0].length > 0) {
    const clause = typeof query.get('clause') === 'string' ? query.get('clause') : ''
    if (clause.length === 0) return null   // 引擎契约：formula 必带 clause（条款号）
    return {
      docId,
      enginePath: `/api/v1/documents/${enc(docId)}/formula/${enc(rest[0])}`
        + `?clause=${enc(clause)}`,
    }
  }
  if (kind === 'table-image' && rest.length === 2
      && /^\d+$/.test(rest[0]) && /^\d+$/.test(rest[1])) {
    return {
      docId,
      enginePath: `/api/v1/documents/${enc(docId)}/table-image/${rest[0]}/${rest[1]}`,
    }
  }
  return null
}

/**
 * 注册 /ks/doc-image 前缀路由（经 guardWebServer 栅栏——apply() 统一包裹）。
 * @returns {() => void} disposer。
 */
export function registerKsDocImageRoutes(ctx, manager) {
  return ctx.webServer.register({
    kind: 'prefix',
    path: KS_DOC_IMAGE_PATH,
    handler: async (req, res) => {
      const send = (status, headers, body) => {
        res.writeHead(status, headers)
        res.end(body)
      }
      const json = (status, payload) =>
        send(status, { 'Content-Type': 'application/json; charset=utf-8' },
             JSON.stringify(payload))
      if (req.method !== undefined && req.method !== 'GET' && req.method !== 'HEAD') {
        json(405, { ok: false, error: { code: 'method_not_allowed', message: 'GET only' } })
        return
      }
      const u = new URL(req.url ?? '/', 'http://localhost')
      let parsed = null
      try {
        parsed = parseDocImagePath(
          decodeURIComponent(u.pathname).slice(KS_DOC_IMAGE_PATH.length + 1), u.searchParams)
      } catch {
        parsed = null
      }
      if (parsed === null) {
        json(400, { ok: false, error: { code: 'bad_request', message: '非法图路径（期望 figure/<no> / formula/<no>?clause= / table-image/<page>/<idx>）' } })
        return
      }
      const dpi = clampDpi(u.searchParams.get('dpi'))
      const enginePath = `${parsed.enginePath}${parsed.enginePath.includes('?') ? '&' : '?'}dpi=${dpi}`
      try {
        const session = await manager.ensureLive()
        const call = (sess, signal) => apiGetBytes(originUrl(sess.port), enginePath, {
          token: sess.token, signal, timeoutMs: 45_000,
          captureHeaders: FORWARD_HEADERS.map(([fetchName]) => fetchName),
        })
        let probe = await call(session)
        // 401 → 会话文件可能轮换（引擎每次启动换 port/token），重读一次再试（同 /ks/bbox）。
        if (probe.status === 401) {
          const fresh = await manager.ensureLive()
          if (fresh && (fresh.port !== session.port || fresh.token !== session.token)) {
            probe = await call(fresh)
          }
        }
        if (probe.status === 401) {
          json(502, { ok: false, error: { code: 'ks_engine_auth', message: '引擎拒绝了 Bearer token(401)，重读会话后仍失败' } })
          return
        }
        // 引擎 404 = 定位不到图/公式/表（占位应隐藏）→ 404 + 本地信封
        // （verifier P2-8：非"透传"——引擎 404 body 是它自己的 JSON，这里
        //  换成插件语义信封 ks_image_not_found，客户端按契约隐藏占位）。
        if (probe.status === 404) {
          json(404, { ok: false, error: { code: 'ks_image_not_found', message: '引擎未定位到该图/公式/表（占位隐藏）' } })
          return
        }
        if (!probe.ok || probe.bytes === null) {
          throw new Error(`引擎返回 HTTP ${probe.status}${probe.error ? `: ${probe.error}` : ''}`)
        }
        // 引擎未给 Content-Type 时兜底 application/octet-stream（verifier P2-10：
        // image/png 兜底会让消费端 image/* 校验对未知字节放行——octet-stream
        // 保守可辨，fetchDocImage 校验会显式拒绝）。
        const headers = {
          'Content-Type': probe.headers['content-type'] ?? 'application/octet-stream',
          'Cache-Control': 'max-age=86400',
          'Content-Length': String(probe.bytes.length),
        }
        for (const [fetchName, wireName] of FORWARD_HEADERS) {
          if (typeof probe.headers[fetchName] === 'string') {
            headers[wireName] = probe.headers[fetchName]
          }
        }
        // HEAD 只发头（img 预热/探测可用）。
        if (req.method === 'HEAD') {
          send(200, headers, undefined)
          return
        }
        send(200, headers, probe.bytes)
      } catch (error) {
        json(503, {
          ok: false,
          error: {
            code: 'ks_doc_image_unavailable',
            message: error instanceof Error ? error.message : String(error),
          },
        })
      }
    },
  })
}
