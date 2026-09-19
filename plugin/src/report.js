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
// 共用路由小工具（2026-09-17 抽到 route_util.js）。本模块原先自带一份逐字相同的
// 拷贝：`BODY_CAP=65536`、jsonResponse/errorBody/readJsonBody/pickQuery/mapProbe
// 全部同形，故这次是**纯粹的搬家**，行为不变（smoke-tools/verify:commands 兜底）。
import {
  ROUTE_BODY_CAP,
  errorBody,
  jsonResponse,
  mapProbe,
  pickQuery,
  readJsonBody as readJsonBodyUtil,
} from './route_util.js'

export const KS_REPORT_EFFECT_PATH = '/ks/report/effect'
export const KS_REPORT_DOCS_PATH = '/ks/report/effect/docs'
export const KS_REPORT_EXPORT_PATH = '/ks/report/export'
/** 研究报告（Phase D）：材料平面的产出物（Markdown + HTML 两种形态）。 */
export const KS_REPORT_RESEARCH_PATH = '/ks/report/research'
/** 结论**草稿**（Phase D-5a，§10.96）：**不落盘**，`status` 恒为 `unapproved_draft`。 */
export const KS_REPORT_DRAFT_PATH = '/ks/report/research/draft'
const ENGINE_EFFECT_PATH = '/api/v1/report/effect'
const ENGINE_DOCS_PATH = '/api/v1/report/effect/docs'
const ENGINE_EXPORT_PATH = '/api/v1/report/effect/export'
const ENGINE_RESEARCH_PATH = '/api/v1/report/research'
const ENGINE_DRAFT_PATH = '/api/v1/report/research/draft'
const ENGINE_DOWNLOAD_PATH = '/api/v1/export/download'

const XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

/* ------------------------------------------------------------------ *
 * Helpers
 *
 * 三个原语（jsonResponse / errorBody / readJsonBody）与 pickQuery / mapProbe
 * 都从 `route_util.js` 取——**本模块不再自带拷贝**。下面只保留本模块特有的
 * `readJsonBody(req)` 形状（固定 cap），让调用点不必到处传常量。
 * ------------------------------------------------------------------ */

/** 固定 cap 的请求体读取（与迁移前的 `BODY_CAP` 同值）。 */
function readJsonBody(req) {
  return readJsonBodyUtil(req, ROUTE_BODY_CAP)
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

/**
 * `POST /ks/report/research/draft`：**结论草稿**（Phase D-5a，§10.96）。
 *
 * 系统基于**已批准材料**起草一段结论，回给用户**编辑/批准**；`status` 恒为
 * `unapproved_draft`（**那是契约的一部分**，界面必须显示）。
 *
 * 与 `/ks/report/research` 的两点关键区别：
 *   1. **`query` 必填**（起草必须先知道要回答什么）——缺了由引擎回 422；
 *   2. **不落盘**（响应里没有 `files`）——是否采用由用户**逐次显式**决定。
 *
 * 转发规则**同款白名单**（未知键不透传）：只认 `project_id`/`query`/`limit`。
 */
function registerDraftRoute(ctx, manager) {
  return ctx.webServer.register({
    kind: 'exact',
    path: KS_REPORT_DRAFT_PATH,
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
      if (typeof raw.project_id === 'string' && raw.project_id.trim() !== '') {
        body.project_id = raw.project_id.trim()
      }
      if (typeof raw.query === 'string' && raw.query.trim() !== '') {
        body.query = raw.query.trim()
      }
      if (raw.limit !== undefined) body.limit = raw.limit
      if (body.project_id === undefined) {
        jsonResponse(res, 400, errorBody('bad_request', '缺少 project_id'))
        return
      }
      if (body.query === undefined) {
        jsonResponse(res, 400, errorBody('bad_request', '缺少 query（起草结论必须先有研究问题）'))
        return
      }
      let session
      try {
        session = await manager.ensureLive()
      } catch (err) {
        jsonResponse(res, 503, errorBody('engine_unavailable',
          err instanceof Error ? err.message : String(err)))
        return
      }
      // 一次同步 LLM 调用：与研究报告同量级超时（甚至更久，故给 120s）
      const probe = await apiPost(originUrl(session.port), ENGINE_DRAFT_PATH,
        { token: session.token, timeoutMs: 120_000, body })
      mapProbe(res, probe)
    },
  })
}

/** Register all report routes; returns the combined disposer. */
export function registerKsReportRoutes(ctx, manager) {
  const disposers = [
    registerEffectRoute(ctx, manager),
    registerDocsRoute(ctx, manager),
    registerExportRoute(ctx, manager),
    registerResearchRoute(ctx, manager),
    registerDraftRoute(ctx, manager),
  ]
  return () => {
    for (const dispose of disposers) dispose()
  }
}
