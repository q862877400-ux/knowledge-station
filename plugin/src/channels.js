/**
 * ks-dsh-plugin — src/channels.js
 *
 * **渠道台账**的宿主路由（§11.0 R4a）。两个口：
 *
 *   GET  /ks/channels         → 引擎 GET  /api/v1/channels   （列表 + summary）
 *   POST /ks/channels/probe   → 引擎 POST /api/v1/channels/probe（人工"立刻探一遍"）
 *
 * ## 为什么这两条要过宿主（而不是让浏览器直连引擎）
 * 与大字体那条（`fetchExportBlob` 直连引擎取产物）**故意不同**：
 * 探针会**对外发请求**（访问二十多个政府站），必须留在宿主侧——浏览器侧发起的话，
 * 谁探了哪个站、探几次都不受控，而且 `Referer`/`Origin` 会带上 GUI 的地址，
 * 对政府站的反爬是个不必要的信号。列表也一样走宿主：口径统一、只多一跳。
 *
 * ## 两条纪律
 * 1. **白名单转发**：query/body 只放行下面列出的键，界面不发明字段、宿主动不转发别的；
 * 2. **探针给足超时**（`PROBE_TIMEOUT_MS`）：一次探 28 条、每条一次请求、个别站点会超时，
 *    默认 20s 的 GET 超时会让"最后一次探测"变成"永远超时"——那是把人劝退的假失败。
 */
import { apiGet, apiPost, originUrl } from './engine.js'
import { errorBody, jsonResponse, pickQuery, readJsonBody, mapProbe } from './route_util.js'

/** 「渠道台账」路由（与 `plugin/client/api.ts` 里的常量**逐字一致**）。 */
export const KS_CHANNELS_PATH = '/ks/channels'
export const KS_CHANNELS_PROBE_PATH = '/ks/channels/probe'

const ENGINE_CHANNELS_PATH = '/api/v1/channels'
const ENGINE_PROBE_PATH = '/api/v1/channels/probe'

/** 列出的筛选键白名单（顺序无关；`enabled_only` 是布尔，其余是枚举/数字）。 */
const LIST_KEYS = ['category', 'wiring', 'state', 'verification', 'enabled_only', 'limit']

/** 探针总超时：28 条 × 单条最长 20s 的极端情形也留了余量。 */
const PROBE_TIMEOUT_MS = 150_000

function registerChannelsListRoute(ctx, manager) {
  return ctx.webServer.register({
    kind: 'exact',
    path: KS_CHANNELS_PATH,
    handler: async (req, res) => {
      if (req.method !== 'GET') {
        jsonResponse(res, 405, errorBody('method_not_allowed', 'GET only'))
        return
      }
      const q = pickQuery(req.url, LIST_KEYS)
      const qs = new URLSearchParams(q).toString()
      let session
      try {
        session = await manager.ensureLive()
      } catch (err) {
        jsonResponse(res, 503, errorBody('engine_unavailable',
          err instanceof Error ? err.message : String(err)))
        return
      }
      // ⚠ 会话只取**一次**（`ensureLive()` 两次调用在多引擎/轮换场景下可能拿到两个会话，
      //   那样 port 与 token 会配错——宁可写成"取一次、用两处"）。
      const probe = await apiGet(originUrl(session.port),
        qs ? `${ENGINE_CHANNELS_PATH}?${qs}` : ENGINE_CHANNELS_PATH,
        { token: session.token, timeoutMs: 20_000 })
      mapProbe(res, probe)
    },
  })
}

function registerChannelsProbeRoute(ctx, manager) {
  return ctx.webServer.register({
    kind: 'exact',
    path: KS_CHANNELS_PROBE_PATH,
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
      if (raw.ids !== undefined) {
        if (!Array.isArray(raw.ids) || raw.ids.some((i) => typeof i !== 'string')) {
          jsonResponse(res, 422, errorBody('illegal_ids', 'ids 必须是字符串数组'))
          return
        }
        body.ids = raw.ids
      }
      if (raw.persist !== undefined) body.persist = raw.persist === true
      let session
      try {
        session = await manager.ensureLive()
      } catch (err) {
        jsonResponse(res, 503, errorBody('engine_unavailable',
          err instanceof Error ? err.message : String(err)))
        return
      }
      const probe = await apiPost(originUrl(session.port), ENGINE_PROBE_PATH,
        { token: session.token, timeoutMs: PROBE_TIMEOUT_MS, body })
      if (probe.status === 404) {
        const code = probe.body && typeof probe.body === 'object' ? probe.body.error : null
        jsonResponse(res, 404, errorBody(typeof code === 'string' ? code : 'channel_not_found',
          probe.body?.message ?? '渠道不存在'))
        return
      }
      mapProbe(res, probe)
    },
  })
}

/**
 * 注册两条渠道路由。返回 disposer 数组（随 fiber 撤销，与其它 register 模块同契约）。
 */
export function registerKsChannelsRoutes(ctx, manager) {
  return [
    registerChannelsListRoute(ctx, manager),
    registerChannelsProbeRoute(ctx, manager),
  ]
}
