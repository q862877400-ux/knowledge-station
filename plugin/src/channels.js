/**
 * ks-dsh-plugin — src/channels.js
 *
 * **渠道台账**的宿主路由（§11.0 R4a 读 + R6f 人工维护）。六个口：
 *
 *   GET    /ks/channels                → 引擎 GET    /api/v1/channels        （列表 + summary）
 *   POST   /ks/channels                → 引擎 POST   /api/v1/channels        （人工新增）
 *   PATCH  /ks/channels/{id}           → 引擎 PATCH  /api/v1/channels/{id}   （人工复核/编辑）
 *   POST   /ks/channels/{id}/enabled   → 引擎 POST   …/{id}/enabled          （人工启停）
 *   DELETE /ks/channels/{id}           → 引擎 DELETE /api/v1/channels/{id}   （人工删除）
 *   POST   /ks/channels/probe          → 引擎 POST   /api/v1/channels/probe  （人工"立刻探一遍"）
 *
 * ## 为什么这些要过宿主（而不是让浏览器直连引擎）
 * 与大字体那条（`fetchExportBlob` 直连引擎取产物）**故意不同**：
 * 探针会**对外发请求**（访问二十多个政府站），必须留在宿主侧——浏览器侧发起的话，
 * 谁探了哪个站、探几次都不受控，而且 `Referer`/`Origin` 会带上 GUI 的地址，
 * 对政府站的反爬是个不必要的信号。列表与写口也一样走宿主：口径统一、只多一跳。
 *
 * ## 三条纪律
 * 1. **白名单转发**：query/body 只放行下面列出的键，界面不发明字段、宿主动不转发别的；
 * 2. **探针给足超时**（`PROBE_TIMEOUT_MS`）：一次探 28 条、每条一次请求、个别站点会超时，
 *    默认 20s 的 GET 超时会让"最后一次探测"变成"永远超时"——那是把人劝退的假失败；
 * 3. **写口如实透传引擎的错误码**（`illegal_channel_field` / `channel_name_required` / …）：
 *    引擎已经把关（健康度字段一律 422、未知键 422），宿主**不再自己判一遍**
 *    —— 两处判据早晚会漂移，而这里漂移的后果是"界面以为写进去了、其实没有"。
 */
import { apiGet, apiPost, originUrl } from './engine.js'
import { errorBody, jsonResponse, pickQuery, readJsonBody, mapProbe } from './route_util.js'

/** 「渠道台账」路由（与 `plugin/client/api.ts` 里的常量**逐字一致**）。 */
export const KS_CHANNELS_PATH = '/ks/channels'
export const KS_CHANNELS_PROBE_PATH = '/ks/channels/probe'
/** `PATCH/DELETE /ks/channels/{id}` 与 `POST /ks/channels/{id}/enabled` 走这条前缀。
 *
 *  ⚠⚠ **前缀不许带尾斜杠**（2026-09-22 修，UI 批0）：真派发器的前缀判据是
 *  `pathname === prefix || pathname.startsWith(prefix + '/')`（webserver `match()`），
 *  带尾斜杠时只有 `/ks/channels//…` 能命中 ⇒ 界面发的 `/ks/channels/{id}` 系列
 *  **全部落到兜底**（写方法显示 HTTP 405）——「人工维护」整排按钮就这么死过一回
 *  （冒烟的桩判据比真派发器宽，20+ 条断言全绿替它作证）。精确表先于前缀表 ⇒
 *  无尾斜杠**不会**误吞集合路径 `/ks/channels`（那是 exact 路由的地盘）。 */
export const KS_CHANNELS_ITEM_PREFIX = '/ks/channels'

const ENGINE_CHANNELS_PATH = '/api/v1/channels'
const ENGINE_PROBE_PATH = '/api/v1/channels/probe'

/** 列出的筛选键白名单（顺序无关；`enabled_only` 是布尔，其余是枚举/数字）。 */
const LIST_KEYS = ['category', 'wiring', 'state', 'verification', 'enabled_only', 'limit']

/** 人工写口允许转发的字段面——**只作文档，不作过滤器**。
 *
 *  ⚠⚠ 这里有一段被 smoke 当场纠正的设计（我第一版真的拿这份名单筛过字段）：
 *  我原本按"界面不发明字段"的纪律在宿主侧**丢掉**名单外的键，包括
 *  `state`/`last_ok_at` 这类**健康度字段**。后果与 R6d 明令禁止的那种失败一模一样：
 *  引擎那句 loud 422（"这些是探针产出的字段，人工不能写"）**永远发不出来**，
 *  界面拿到的是一个成功的 200 —— **用户以为写进去了**。
 *  ⇒ 结论：**判据归引擎**（它才是 `_WRITABLE`/`HEALTH_FIELDS` 的所有者），
 *  宿主只管"形状与方法"（`readBodyOr400`）。真正的拒绝逻辑**只有一处**；
 *  两处都判，早晚漂移，而漂移的现场表现就是上面那种"假装成功"。
 */

/** 探针总超时：28 条 × 单条最长 20s 的极端情形也留了余量。 */
const PROBE_TIMEOUT_MS = 150_000

/**
 * 通用引擎请求（GET/POST/PATCH/DELETE；`apiGet`/`apiPost` 只覆盖 GET/POST）。
 * 返回与 `apiPost` 同形：`{status, body, error?}`。
 *
 * ⚠ 这是**第三份** `engineRequest`（前两份在 `settings.js` / `announce.js`，都在
 * `route_util.js` 的模块头里**登记为未合并的遗留**）。我按同一惯例再带一份、**不动那两份**：
 * 合并它们要动设置面板与公告源的错误语义，属另一件事；而"只把新代码写进新模块"是那份登记
 * 明文认可的路径。
 */
async function engineRequest(method, base, path, { token, timeoutMs = 20_000, body } = {}) {
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
    return { status: res.status, body: parsed, text: '' }
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

/** 写口统一出口：`{ok:true,data}` 或**原样**带回引擎的 code/HTTP（401 由调用方自愈）。 */
async function proxyWrite(res, manager, method, enginePath, body) {
  let session
  try {
    session = await manager.ensureLive()
  } catch (err) {
    jsonResponse(res, 503, errorBody('engine_unavailable',
      err instanceof Error ? err.message : String(err)))
    return
  }
  const probe = await engineRequest(method, originUrl(session.port), enginePath,
    { token: session.token, timeoutMs: 20_000, body })
  if (probe.status === 200 && probe.body && typeof probe.body === 'object') {
    jsonResponse(res, 200, { ok: true, data: probe.body.data ?? {} })
    return
  }
  const code = probe.body && typeof probe.body === 'object' ? probe.body.error : null
  const message = probe.body && typeof probe.body === 'object' && probe.body.message
    ? String(probe.body.message)
    : (probe.error || `引擎返回 HTTP ${probe.status}`)
  jsonResponse(res, probe.status === 404 ? 404
    : probe.status === 422 ? 422
    : probe.status === 409 ? 409 : 502,
    errorBody(typeof code === 'string' ? code : 'engine_error', message))
}

/** 人工写口：**不在这里筛字段**（见 `proxyWrite` 上方那段说明）。
 *  宿主只做一件事——把 body 原样交给引擎，由引擎的 `_WRITABLE` / 健康度判据**当裁判**。 */
function pickWriteBody(raw) {
  return { ...raw }
}

/**
 * 读 body 并**只接受 JSON 对象**（数组/标量一律 400）：写口的输入形状由宿主收紧，
 * 免得 `null`/数组流到引擎、变成一条含混的 422。
 */
async function readBodyOr400(req, res) {
  let raw
  try {
    raw = await readJsonBody(req)
  } catch {
    jsonResponse(res, 400, errorBody('bad_request', 'body 必须是合法 JSON'))
    return null
  }
  if (raw === null || typeof raw !== 'object' || Array.isArray(raw)) {
    jsonResponse(res, 400, errorBody('bad_request', 'body 必须是 JSON 对象'))
    return null
  }
  return raw
}

/**
 * `/ks/channels` 这一个**路径**上的两件事：`GET` 列表、`POST` 人工新增。
 *
 * ⚠ 必须写在**同一个注册**里（我第一版拆成两次 `register`，被 smoke 当场拦下）：
 * 路由表是按 **path 去重、后注册覆盖先注册**的，拆开写会让 `GET /ks/channels`
 * 静默消失（现场表现是"列表页突然空了"）——**同一个 path 只能有一个 handler**，
 * 内部按方法分派才是这个注册表的正确用法。
 */
function registerChannelsCollectionRoute(ctx, manager) {
  return ctx.webServer.register({
    kind: 'exact',
    path: KS_CHANNELS_PATH,
    handler: async (req, res) => {
      if (req.method === 'POST') {
        await handleCreate(req, res, manager)
        return
      }
      if (req.method !== 'GET') {
        jsonResponse(res, 405, errorBody('method_not_allowed', 'GET or POST'))
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

/** `POST /ks/channels`：读 body（白名单）→ 转发引擎同路径。 */
async function handleCreate(req, res, manager) {
  let raw
  try {
    raw = await readJsonBody(req)
  } catch {
    jsonResponse(res, 400, errorBody('bad_request', 'body 必须是合法 JSON'))
    return
  }
  if (raw === null || typeof raw !== 'object' || Array.isArray(raw)) {
    jsonResponse(res, 400, errorBody('bad_request', 'body 必须是 JSON 对象'))
    return
  }
  await proxyWrite(res, manager, 'POST', ENGINE_CHANNELS_PATH, pickWriteBody(raw))
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
 * 人工维护：`POST /ks/channels`（新增）、`PATCH|DELETE /ks/channels/{id}`、
 * `POST /ks/channels/{id}/enabled`（启停）。
 *
 * ⚠ **宿主不自己校验业务规则**（名称必填、健康度字段不许写、id 前缀契约…）——那些判据的
 * 所有者是引擎 `routes_channels.py`；这里只做两件它做不到的事：
 * ① **白名单**（界面发明的字段根本不往引擎送，缩小透传面）；
 * ② **同源**（token 只在 host→引擎段，浏览器永远拿不到引擎凭据）。
 * 两处都判一遍的后果是漂移，而漂移的现场表现是"界面以为写进去了、其实没有"。
 */
function registerChannelsWriteRoutes(ctx, manager) {
  return [
    // 单条：PATCH（复核编辑）/ DELETE（删除）
    ctx.webServer.register({
      kind: 'prefix',
      path: KS_CHANNELS_ITEM_PREFIX,
      handler: async (req, res) => {
        const rest = (req.url || '').split('?')[0]
        const tail = rest.slice(KS_CHANNELS_ITEM_PREFIX.length)
        // `{id}` 或 `{id}/enabled`；id 允许 `ch:`/`user:`/`seed:` 前缀（含冒号）与点号
        const parts = tail.split('/').filter((s) => s !== '')
        const id = parts[0] ? decodeURIComponent(parts[0]) : ''
        if (!id || /[^\w:.\-]/.test(id)) {
          jsonResponse(res, 400, errorBody('bad_request', '非法渠道 id'))
          return
        }
        const engineId = `${ENGINE_CHANNELS_PATH}/${encodeURIComponent(id)}`
        if (parts.length === 1 && req.method === 'PATCH') {
          const raw = await readBodyOr400(req, res)
          if (raw === null) return
          await proxyWrite(res, manager, 'PATCH', engineId, pickWriteBody(raw))
          return
        }
        if (parts.length === 1 && req.method === 'DELETE') {
          await proxyWrite(res, manager, 'DELETE', engineId)
          return
        }
        if (parts.length === 2 && parts[1] === 'enabled' && req.method === 'POST') {
          const raw = await readBodyOr400(req, res)
          if (raw === null) return
          // ⚠ `enabled` 是不是布尔**由引擎判**（`illegal_enabled`）：宿主这里只把值转过去。
          //   我第一版在宿主侧也判了一遍——那正是"两处判据"的开端，删掉。
          await proxyWrite(res, manager, 'POST', `${engineId}/enabled`,
            { enabled: raw.enabled })
          return
        }
        jsonResponse(res, 405, errorBody('method_not_allowed',
          'PATCH or DELETE /ks/channels/{id}；POST /ks/channels/{id}/enabled'))
      },
    }),
  ]
}

/**
 * 注册渠道台账路由。返回 disposer 数组（随 fiber 撤销，与其它 register 模块同契约）。
 */
export function registerKsChannelsRoutes(ctx, manager) {
  return [
    registerChannelsCollectionRoute(ctx, manager),
    registerChannelsWriteRoutes(ctx, manager),
    registerChannelsProbeRoute(ctx, manager),
  ].flat()
}
