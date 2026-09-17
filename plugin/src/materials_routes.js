/**
 * ks-dsh-plugin — src/materials_routes.js
 *
 * host 侧 `/ks/materials/*` 路由：**供界面使用的材料平面读写通道**（Phase B 第五步）。
 *
 * ## 为什么需要这一层（而不是让 client 直连引擎）
 * client 半边**拿不到引擎 Bearer token**（token 只在 host 与引擎之间），
 * 所以界面要用材料能力，必须由 host 做同源代理——与 `/ks/report/*`、`/ks/ingest/*` 同款。
 *
 * ## 与 `ks_materials`（模型工具）的**分工**（别混）
 * - `ks_materials`（`materials.js`，模型用）：**只读**。模型可以看项目与评审状态，
 *   但**不能**批准/拒绝——那等于让模型自己给自己发许可（方案 §6 硬门）。
 * - 本模块（界面用）：**可写**，因为它的调用者是**用户界面**，而评审正是**用户的判断**
 *   （业主裁定 J4："经用户评审确认参考资料可用后再做分析"）。
 *   ⇒ `review` 端点**只接受** `approved` / `rejected` 两个决定值；没有"自动批准"。
 *
 * ## 依赖面
 * 只用 node 内建 + `./engine.js` + `./route_util.js`（无 cordis import，可离线冒烟）。
 */

import { apiGet, apiPost, originUrl } from './engine.js'
import {
  ROUTE_BODY_CAP,
  errorBody,
  jsonResponse,
  mapProbe,
  pickQuery,
  readJsonBody,
} from './route_util.js'

/* ------------------------------------------------------------------ 路径 */

/** 界面用的同源前缀（client 硬编码同值，见 client/api.ts）。 */
export const KS_MATERIALS_PATH = '/ks/materials'

/** 引擎侧前缀。 */
const ENGINE_MATERIALS = '/api/v1/materials'

/** 允许的评审决定：**只有这两个**（没有"自动通过"，也没有 pending 以外的状态）。 */
export const REVIEW_DECISIONS = ['approved', 'rejected']

/* ------------------------------------------------------------------ 引擎访问 */

/**
 * 读引擎会话并按需重读一次（401 = port/token 轮换）。
 * 与 report.js 的 `engineGetWithRetry` 同款；此处额外支持 POST。
 */
async function engineCall(manager, method, path, body) {
  const doCall = (sess) => (method === 'GET'
    ? apiGet(originUrl(sess.port), path, { token: sess.token, timeoutMs: 30_000 })
    : apiPost(originUrl(sess.port), path, { token: sess.token, timeoutMs: 60_000, body }))
  let session = await manager.ensureLive()
  let probe = await doCall(session)
  if (probe.status === 401) {
    const fresh = await manager.ensureLive()
    if (fresh && (fresh.port !== session.port || fresh.token !== session.token)) {
      session = fresh
      probe = await doCall(session)
    }
  }
  return probe
}

/** 统一的"引擎不可用"兜底（任何异常都变成 503，不让路由抛到框架）。 */
function guard(handler) {
  return async (req, res) => {
    try {
      await handler(req, res)
    } catch (err) {
      jsonResponse(res, 503, errorBody('engine_unavailable',
        err instanceof Error ? err.message : String(err)))
    }
  }
}

/** 只允许某些方法，否则 405（每个路由都要，抽出来免得漏）。 */
function methodOnly(req, res, allowed) {
  if (!allowed.includes(req.method)) {
    jsonResponse(res, 405, errorBody('method_not_allowed', `${allowed.join(' or ')} only`))
    return false
  }
  return true
}

/** 读 JSON body，非法即 400（返回 `undefined` 表示已响应，调用方直接 return）。 */
async function readBodyOr400(req, res) {
  try {
    return await readJsonBody(req, ROUTE_BODY_CAP)
  } catch {
    jsonResponse(res, 400, errorBody('bad_request', 'body 必须是合法 JSON'))
    return undefined
  }
}

/* ------------------------------------------------------------------ 路由 */

/** `GET /ks/materials/projects`：列项目（含 authority_policy，供界面显示"本项目以谁为准"）。 */
function registerListProjects(ctx, manager) {
  return ctx.webServer.register({
    kind: 'exact',
    path: `${KS_MATERIALS_PATH}/projects`,
    handler: guard(async (req, res) => {
      if (!methodOnly(req, res, ['GET', 'POST'])) return
      if (req.method === 'POST') {
        const body = await readBodyOr400(req, res)
        if (body === undefined) return
        if (typeof body?.name !== 'string' || body.name.trim() === '') {
          jsonResponse(res, 400, errorBody('bad_request', '缺少 name（项目名）'))
          return
        }
        const probe = await engineCall(manager, 'POST', `${ENGINE_MATERIALS}/projects`, {
          name: body.name.trim(),
          note: typeof body.note === 'string' ? body.note : null,
          authority_policy: body.authority_policy ?? null,
        })
        mapProbe(res, probe)
        return
      }
      mapProbe(res, await engineCall(manager, 'GET', `${ENGINE_MATERIALS}/projects`))
    }),
  })
}

/** `GET /ks/materials/list?project_id=&status=`：某项目的材料（**含未批准**——否则没法批）。 */
function registerListMaterials(ctx, manager) {
  return ctx.webServer.register({
    kind: 'exact',
    path: `${KS_MATERIALS_PATH}/list`,
    handler: guard(async (req, res) => {
      if (!methodOnly(req, res, ['GET'])) return
      const q = pickQuery(req.url, ['project_id', 'status'])
      if (!q.project_id) {
        jsonResponse(res, 400, errorBody('bad_request', '缺少 project_id'))
        return
      }
      const qs = new URLSearchParams(q).toString()
      mapProbe(res, await engineCall(manager, 'GET',
        `${ENGINE_MATERIALS}/projects/${encodeURIComponent(q.project_id)}/materials?${qs}`))
    }),
  })
}

/** `GET /ks/materials/inbox?project_id=`：参考资料文件夹里**尚未登记**的文件。 */
function registerInbox(ctx, manager) {
  return ctx.webServer.register({
    kind: 'exact',
    path: `${KS_MATERIALS_PATH}/inbox`,
    handler: guard(async (req, res) => {
      if (!methodOnly(req, res, ['GET'])) return
      const q = pickQuery(req.url, ['project_id'])
      if (!q.project_id) {
        jsonResponse(res, 400, errorBody('bad_request', '缺少 project_id'))
        return
      }
      mapProbe(res, await engineCall(manager, 'GET',
        `${ENGINE_MATERIALS}/projects/${encodeURIComponent(q.project_id)}/inbox`))
    }),
  })
}

/** `POST /ks/materials/scan?project_id=`：扫描收件（登记为**待评审**，不会自动批准）。 */
function registerScan(ctx, manager) {
  return ctx.webServer.register({
    kind: 'exact',
    path: `${KS_MATERIALS_PATH}/scan`,
    handler: guard(async (req, res) => {
      if (!methodOnly(req, res, ['POST'])) return
      const q = pickQuery(req.url, ['project_id'])
      if (!q.project_id) {
        jsonResponse(res, 400, errorBody('bad_request', '缺少 project_id'))
        return
      }
      const body = await readBodyOr400(req, res)
      if (body === undefined) return
      mapProbe(res, await engineCall(manager, 'POST',
        `${ENGINE_MATERIALS}/projects/${encodeURIComponent(q.project_id)}/scan`,
        { origin: typeof body?.origin === 'string' ? body.origin : 'user' }))
    }),
  })
}

/**
 * `POST /ks/materials/review?material_id=`：**用户的评审决定**（本模块的核心）。
 *
 * 只收 `approved` / `rejected`：`pending` 是"还没评"，不是可以"评成"的状态；
 * 别的值一律 400 —— 评审是本功能的**硬门**，不能因为界面传错值而静默放过。
 */
function registerReview(ctx, manager) {
  return ctx.webServer.register({
    kind: 'exact',
    path: `${KS_MATERIALS_PATH}/review`,
    handler: guard(async (req, res) => {
      if (!methodOnly(req, res, ['POST'])) return
      const q = pickQuery(req.url, ['material_id'])
      if (!q.material_id) {
        jsonResponse(res, 400, errorBody('bad_request', '缺少 material_id'))
        return
      }
      const body = await readBodyOr400(req, res)
      if (body === undefined) return
      const decision = typeof body?.decision === 'string' ? body.decision : ''
      if (!REVIEW_DECISIONS.includes(decision)) {
        jsonResponse(res, 400, errorBody('bad_request',
          `decision 只能是 ${REVIEW_DECISIONS.join(' / ')}（收到 ${JSON.stringify(decision)}）`))
        return
      }
      mapProbe(res, await engineCall(manager, 'POST',
        `${ENGINE_MATERIALS}/${encodeURIComponent(q.material_id)}/review`,
        // ⚠ **字段名要翻译**：对界面的契约是 `decision`（approved/rejected，语义明确、
        // 且不会与响应信封里的 `status:"success"` 混淆），而**引擎侧收的是 `status`**
        // （`routes_materials.py` 的 materials_review 读 `body["status"]`，且它允许三态）。
        // 2026-09-17 一步之遥踩中：本路由最初发 `{decision}` ⇒ 引擎对**每一次**审批都回
        // 422，界面会看到"批准失败"。**别把这里改回直接透传 body**。
        { status: decision, note: typeof body?.note === 'string' ? body.note : null }))
    }),
  })
}

/** `POST /ks/materials/tier?material_id=`：轴 A（来源可信度 T0~T4），**用户可改**。 */
function registerTier(ctx, manager) {
  return ctx.webServer.register({
    kind: 'exact',
    path: `${KS_MATERIALS_PATH}/tier`,
    handler: guard(async (req, res) => {
      if (!methodOnly(req, res, ['POST'])) return
      const q = pickQuery(req.url, ['material_id'])
      if (!q.material_id) {
        jsonResponse(res, 400, errorBody('bad_request', '缺少 material_id'))
        return
      }
      const body = await readBodyOr400(req, res)
      if (body === undefined) return
      if (typeof body?.tier !== 'string' || body.tier === '') {
        jsonResponse(res, 400, errorBody('bad_request', '缺少 tier（T0~T4）'))
        return
      }
      // `source` 由**调用方**声明（'user' = 用户改的）。前端固定传 user，
      // 免得"用户改的层级"和"系统判的层级"在留痕里混掉（轴 A 的判据必须可追）。
      mapProbe(res, await engineCall(manager, 'POST',
        `${ENGINE_MATERIALS}/${encodeURIComponent(q.material_id)}/tier`,
        { tier: body.tier, source: typeof body?.source === 'string' ? body.source : 'user' }))
    }),
  })
}

/** `POST /ks/materials/role?material_id=`：轴 B（任务内效力 criterion/reference）。 */
function registerRole(ctx, manager) {
  return ctx.webServer.register({
    kind: 'exact',
    path: `${KS_MATERIALS_PATH}/role`,
    handler: guard(async (req, res) => {
      if (!methodOnly(req, res, ['POST'])) return
      const q = pickQuery(req.url, ['material_id'])
      if (!q.material_id) {
        jsonResponse(res, 400, errorBody('bad_request', '缺少 material_id'))
        return
      }
      const body = await readBodyOr400(req, res)
      if (body === undefined) return
      if (typeof body?.role !== 'string' || body.role === '') {
        jsonResponse(res, 400, errorBody('bad_request', '缺少 role（criterion / reference）'))
        return
      }
      mapProbe(res, await engineCall(manager, 'POST',
        `${ENGINE_MATERIALS}/${encodeURIComponent(q.material_id)}/role`, { role: body.role }))
    }),
  })
}

/** `GET /ks/materials/chunks?material_id=&offset=&limit=`：读切片（评审必须能读到正文）。 */
function registerChunks(ctx, manager) {
  return ctx.webServer.register({
    kind: 'exact',
    path: `${KS_MATERIALS_PATH}/chunks`,
    handler: guard(async (req, res) => {
      if (!methodOnly(req, res, ['GET'])) return
      const q = pickQuery(req.url, ['material_id', 'offset', 'limit'])
      if (!q.material_id) {
        jsonResponse(res, 400, errorBody('bad_request', '缺少 material_id'))
        return
      }
      const qs = new URLSearchParams(q).toString()
      mapProbe(res, await engineCall(manager, 'GET',
        `${ENGINE_MATERIALS}/${encodeURIComponent(q.material_id)}/chunks?${qs}`))
    }),
  })
}

/** `GET /ks/materials/tiers`：轴 A 的层定义（界面下拉用；判据在引擎，别在前端抄一份）。 */
function registerTiers(ctx, manager) {
  return ctx.webServer.register({
    kind: 'exact',
    path: `${KS_MATERIALS_PATH}/tiers`,
    handler: guard(async (req, res) => {
      if (!methodOnly(req, res, ['GET'])) return
      mapProbe(res, await engineCall(manager, 'GET', `${ENGINE_MATERIALS}/tiers`))
    }),
  })
}

/**
 * 注册全部材料路由，返回合并 disposer（cordis effect 会调用）。
 *
 * 注意注册顺序**无关**：这里全是 `kind:'exact'` 的字面路径（没有 `{id}` 通配），
 * 所以不会出现"字面量被通配吃掉"那种坑（引擎侧踩过一次，见 §10.11）。
 */
export function registerKsMaterialsRoutes(ctx, manager) {
  const disposers = [
    registerListProjects(ctx, manager),
    registerListMaterials(ctx, manager),
    registerInbox(ctx, manager),
    registerScan(ctx, manager),
    registerReview(ctx, manager),
    registerTier(ctx, manager),
    registerRole(ctx, manager),
    registerChunks(ctx, manager),
    registerTiers(ctx, manager),
  ]
  return () => {
    for (const dispose of disposers) dispose()
  }
}

/** 供冒烟/诊断用：本模块对外暴露的路径清单。 */
export const KS_MATERIALS_PATHS = [
  `${KS_MATERIALS_PATH}/projects`,
  `${KS_MATERIALS_PATH}/list`,
  `${KS_MATERIALS_PATH}/inbox`,
  `${KS_MATERIALS_PATH}/scan`,
  `${KS_MATERIALS_PATH}/review`,
  `${KS_MATERIALS_PATH}/tier`,
  `${KS_MATERIALS_PATH}/role`,
  `${KS_MATERIALS_PATH}/chunks`,
  `${KS_MATERIALS_PATH}/tiers`,
]
