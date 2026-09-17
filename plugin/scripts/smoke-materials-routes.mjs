/**
 * ks-dsh-plugin — scripts/smoke-materials-routes.mjs
 *
 * `/ks/materials/*` 同源路由回归（Phase B 第五步：**界面用的材料读写通道**）。
 *
 * ## 这一层为什么必须有自己的冒烟
 * 它是**评审硬门**在界面侧的唯一入口：批准/拒绝只能从这里进来。
 * 所以这里要钉的不是"每个端点 200"，而是：
 *   ① **方法守卫**（GET-only 的端点收 POST 必须 405）；
 *   ② **必填参数缺失时 400 且不打扰引擎**（不能拿空 project_id 去查）；
 *   ③ **评审决定只收 approved/rejected**（`pending`/`auto` 一律 400——
 *      否则"自动通过"会从界面这条缝里漏进来，硬门形同虚设）；
 *   ④ **轴 A 改动留痕**（tier 的 `source` 默认 `user`，用户改的与系统判的不能混）；
 *   ⑤ **query 白名单**（未知键不得透传）；
 *   ⑥ 引擎侧 422/5xx/不可达 → 400/502/503 如实映射。
 *
 * ## 做法
 * `registerKsMaterialsRoutes` 收一个假 `ctx.webServer.register`，把注册进来的
 * `{kind,path,handler}` 收下，然后**直接调 handler**（配假 req/res），
 * 引擎侧用**本地桩 HTTP 服务**——这样 URL/query/body 的构造走的是**真 apiGet/apiPost**，
 * 不是复刻。
 *
 * 跑法：node scripts/smoke-materials-routes.mjs   （退出码 0 = 全通过）
 */

import { EventEmitter } from 'node:events'
import { createServer } from 'node:http'

import {
  KS_MATERIALS_PATHS,
  REVIEW_DECISIONS,
  registerKsMaterialsRoutes,
} from '../src/materials_routes.js'

const results = []
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}

/* ------------------------------- 桩引擎 ------------------------------- */

const seen = []
let responder = () => ({ body: { code: 200, status: 'success', data: {} } })

const server = createServer((req, res) => {
  const chunks = []
  req.on('data', (c) => chunks.push(c))
  req.on('end', () => {
    const raw = Buffer.concat(chunks).toString('utf8')
    let sent = null
    try { sent = raw.length > 0 ? JSON.parse(raw) : null } catch { sent = { __unparsed: raw } }
    seen.push({ method: req.method, path: req.url, sent })
    const r = responder(req.url)
    res.writeHead(r.http ?? 200, { 'content-type': 'application/json' })
    res.end(JSON.stringify(r.body ?? r))
  })
})
await new Promise((r) => server.listen(0, '127.0.0.1', r))
const PORT = server.address().port

/* --------------------------- 捕获注册的路由 --------------------------- */

const routes = new Map()
const ctx = {
  webServer: {
    register(def) {
      routes.set(def.path, def)
      return () => {}
    },
  },
}
const manager = { ensureLive: async () => ({ port: PORT, token: 'tok_stub' }) }
const dispose = registerKsMaterialsRoutes(ctx, manager)

/* ----------------------------- 假 req / res ----------------------------- */

function makeRes() {
  const out = { status: null, body: null }
  return {
    out,
    writeHead(status) { out.status = status },
    end(text) { try { out.body = JSON.parse(text) } catch { out.body = text } },
  }
}

/** 造一个假请求并**等** handler 跑完（POST body 通过事件推给它）。 */
async function invoke(path, { method = 'GET', body = undefined, rawBody = undefined, search = '' } = {}) {
  const def = routes.get(path)
  if (def === undefined) throw new Error(`路由未注册: ${path}`)
  const req = new EventEmitter()
  req.method = method
  req.url = `${path}${search}`
  req.destroy = () => {}
  const res = makeRes()
  const p = def.handler(req, res)
  // 下一拍再推 body：让 handler 先把监听挂上
  setImmediate(() => {
    // `rawBody` 用来送**畸形 JSON**（身体不过 JSON.stringify）。
    // ⚠ 这个能力是独立复核要求补上的：本冒烟原先只会 `JSON.stringify`，
    // 于是"畸形 body"这条路径**零覆盖**，而 `readJsonBody` 正好在那条路上挂死过（P0）。
    const payload = rawBody !== undefined ? rawBody
      : (body !== undefined ? JSON.stringify(body) : undefined)
    if (payload !== undefined) req.emit('data', Buffer.from(payload, 'utf8'))
    req.emit('end')
  })
  await p
  return { status: res.out.status, body: res.out.body }
}

const lastEngine = () => seen[seen.length - 1]

/* --------------------------- 1. 注册面 --------------------------- */

{
  check(`注册了全部 ${KS_MATERIALS_PATHS.length} 条材料路由`,
    routes.size === KS_MATERIALS_PATHS.length
    && KS_MATERIALS_PATHS.every((p) => routes.has(p)),
    `${routes.size} routes`)
  check('全部是 kind=exact（字面路径，不会被通配吃掉）',
    [...routes.values()].every((d) => d.kind === 'exact'))
  check('评审决定白名单只有 approved/rejected',
    REVIEW_DECISIONS.join(',') === 'approved,rejected', REVIEW_DECISIONS.join(','))
  check('dispose 可调用（cordis effect 契约）', typeof dispose === 'function')
}

/* --------------------------- 2. 项目 --------------------------- */

{
  seen.length = 0
  responder = () => ({ body: { code: 200, data: [{ project_id: 'prj_a', name: '财报' }] } })
  const r = await invoke('/ks/materials/projects')
  check('GET /projects 透传引擎结果', r.status === 200 && r.body.ok === true
    && r.body.data[0].project_id === 'prj_a', JSON.stringify(r.body))
  check('GET /projects 打到引擎正确路径',
    lastEngine().method === 'GET' && lastEngine().path === '/api/v1/materials/projects',
    `${lastEngine().method} ${lastEngine().path}`)

  seen.length = 0
  responder = () => ({ body: { code: 200, data: { project_id: 'prj_new' } } })
  const created = await invoke('/ks/materials/projects', {
    method: 'POST', body: { name: ' 财报分析 ', note: 'n', authority_policy: { a: 1 } },
  })
  check('POST /projects 建项目并**去空白**',
    created.status === 200 && lastEngine().method === 'POST'
    && lastEngine().sent.name === '财报分析'
    && lastEngine().sent.note === 'n'
    && JSON.stringify(lastEngine().sent.authority_policy) === '{"a":1}',
    JSON.stringify(lastEngine().sent))

  seen.length = 0
  const noName = await invoke('/ks/materials/projects', { method: 'POST', body: {} })
  check('缺 name → 400 且**不打扰引擎**',
    noName.status === 400 && noName.body.error.code === 'bad_request' && seen.length === 0,
    `${noName.status} engineCalls=${seen.length}`)
}

/* --------------------------- 3. 材料列表 / 收件 --------------------------- */

{
  seen.length = 0
  responder = () => ({ body: { code: 200, data: [{ material_id: 'mat_1' }] } })
  const r = await invoke('/ks/materials/list', {
    search: '?project_id=prj_a&status=pending&evil=1',
  })
  check('GET /list 透传 project_id 与 status，**未知 query 键被丢弃**',
    r.status === 200
    && lastEngine().path === '/api/v1/materials/projects/prj_a/materials?project_id=prj_a&status=pending',
    lastEngine().path)
  check('未知 query 键没有透传（防透传面扩大）', !lastEngine().path.includes('evil'),
    lastEngine().path)

  seen.length = 0
  const noPid = await invoke('/ks/materials/list')
  check('GET /list 缺 project_id → 400 且不打扰引擎',
    noPid.status === 400 && seen.length === 0, `${noPid.status} engineCalls=${seen.length}`)

  seen.length = 0
  responder = () => ({ body: { code: 200, data: { dir: 'D:\\x', files: [] } } })
  await invoke('/ks/materials/inbox', { search: '?project_id=prj_a' })
  check('GET /inbox 打到引擎 inbox 路径',
    lastEngine().path === '/api/v1/materials/projects/prj_a/inbox', lastEngine().path)

  seen.length = 0
  responder = () => ({ body: { code: 200, data: { scanned: 1, registered: 1, rows: [] } } })
  await invoke('/ks/materials/scan', { method: 'POST', search: '?project_id=prj_a' })
  check('POST /scan 默认 origin=user（扫描**不会**自动批准，只是登记）',
    lastEngine().method === 'POST' && lastEngine().sent.origin === 'user',
    JSON.stringify(lastEngine().sent))
}

/* --------------------------- 3b. 自采（C-5 接线） --------------------------- */

{
  // 抓取失败是**结果**不是错误码：引擎回 200 + collected:false，本层必须原样透传
  // （界面要把"SSRF 拒绝/404/不是文本"显示给人看）。
  seen.length = 0
  responder = () => ({
    body: { code: 200, data: { collected: false, status: 403, reason: 'URL 被 SSRF 纪律拒绝' } },
  })
  const failed = await invoke('/ks/materials/collect', {
    method: 'POST', search: '?project_id=prj_a', body: { url: 'http://127.0.0.1:9/x' },
  })
  check('POST /collect 打到引擎正确路径',
    lastEngine().method === 'POST'
    && lastEngine().path === '/api/v1/materials/projects/prj_a/collect',
    `${lastEngine().method} ${lastEngine().path}`)
  check('POST /collect **原样透传** collected:false + 原因（不当成 HTTP 错误吞掉）',
    failed.status === 200 && failed.body.ok === true
    && failed.body.data.collected === false && /SSRF/.test(failed.body.data.reason),
    JSON.stringify(failed.body))

  seen.length = 0
  responder = () => ({ body: { code: 200, data: { collected: true, material: {} } } })
  await invoke('/ks/materials/collect', {
    method: 'POST', search: '?project_id=prj_a',
    body: { url: '  https://a.example/x  ', title: 'T', note: '', published_at: '' },
  })
  check('POST /collect 去空白、空串归 null（不发含混的空值）',
    lastEngine().sent.url === 'https://a.example/x'
    && lastEngine().sent.title === 'T'
    && lastEngine().sent.note === null
    && lastEngine().sent.published_at === null,
    JSON.stringify(lastEngine().sent))

  // ⚠ 本战役在 `sanitizeParams` 上栽过同款：字段被静默吞掉、功能全死、无人报错。
  // 所以"不接受 source_tier"必须是**响亮**的 400。
  seen.length = 0
  const tier = await invoke('/ks/materials/collect', {
    method: 'POST', search: '?project_id=prj_a',
    body: { url: 'https://a.example/x', source_tier: 'T0' },
  })
  check('POST /collect 带 source_tier → 400 且**不打扰引擎**（采集不得自 claim 可信度）',
    tier.status === 400 && tier.body.error.code === 'bad_request' && seen.length === 0,
    `${tier.status} engineCalls=${seen.length}`)

  // ⚠ 只挡 `source_tier` 一个拼写不够（复核 A 的 MEDIUM）：同义/同名键会被**静默忽略**，
  // 而"响亮拒绝、绝不静默丢弃"正是本路由的立论。这里逐个钉。
  for (const key of ['sourceTier', 'tier', 'review_status', 'origin', 'lifecycle']) {
    seen.length = 0
    const r = await invoke('/ks/materials/collect', {
      method: 'POST', search: '?project_id=prj_a',
      body: { url: 'https://a.example/x', [key]: 'x' },
    })
    check(`POST /collect 未知字段 ${key} → 400 且不打扰引擎`,
      r.status === 400 && seen.length === 0, `${r.status} engineCalls=${seen.length}`)
  }

  seen.length = 0
  const urls = await invoke('/ks/materials/collect', {
    method: 'POST', search: '?project_id=prj_a', body: { urls: ['https://a.example/1'] },
  })
  check('POST /collect 批量形式 → 400（预算未定之前没有批量入口，§11.4）',
    urls.status === 400 && seen.length === 0, `${urls.status} engineCalls=${seen.length}`)

  seen.length = 0
  const noUrl = await invoke('/ks/materials/collect', {
    method: 'POST', search: '?project_id=prj_a', body: { url: '   ' },
  })
  check('POST /collect 空 url → 400 且不打扰引擎',
    noUrl.status === 400 && seen.length === 0, `${noUrl.status} engineCalls=${seen.length}`)

  seen.length = 0
  const noPid = await invoke('/ks/materials/collect', {
    method: 'POST', body: { url: 'https://a.example/x' },
  })
  check('POST /collect 缺 project_id → 400 且不打扰引擎',
    noPid.status === 400 && seen.length === 0, `${noPid.status} engineCalls=${seen.length}`)
}

/* --------------------------- 4. 评审（核心） --------------------------- */

{
  seen.length = 0
  responder = () => ({ body: { code: 200, data: { review_status: 'approved' } } })
  const ok = await invoke('/ks/materials/review', {
    method: 'POST', search: '?material_id=mat_1', body: { decision: 'approved', note: '看过' },
  })
  check('POST /review 批准：**翻译成引擎的 status 字段**并带上 note',
    ok.status === 200 && lastEngine().path === '/api/v1/materials/mat_1/review'
    && lastEngine().sent.status === 'approved' && lastEngine().sent.note === '看过',
    JSON.stringify(lastEngine().sent))
  check('POST /review **不发** decision 字段（引擎只认 status，发错就每次 422）',
    lastEngine().sent.decision === undefined, JSON.stringify(lastEngine().sent))

  responder = () => ({ body: { code: 200, data: { review_status: 'rejected' } } })
  const rej = await invoke('/ks/materials/review', {
    method: 'POST', search: '?material_id=mat_1', body: { decision: 'rejected' },
  })
  check('POST /review 拒绝同样翻译成 status=rejected', rej.status === 200
    && lastEngine().sent.status === 'rejected', JSON.stringify(lastEngine().sent))

  // **核心纪律**：pending 不是"可以评成的状态"；任何别的值都不许过
  for (const bad of ['pending', 'auto', 'APPROVED', '', 'approve']) {
    seen.length = 0
    const r = await invoke('/ks/materials/review', {
      method: 'POST', search: '?material_id=mat_1', body: { decision: bad },
    })
    check(`评审决定 ${JSON.stringify(bad)} 被拒（400）且不打扰引擎`,
      r.status === 400 && seen.length === 0, `${r.status} engineCalls=${seen.length}`)
  }

  // ⚠ **引擎的字段名不许能当后门**（独立复核 2026-09-17 报的覆盖缺口）：
  // 本冒烟原来**从不发** `status`（引擎侧那个字段名），于是一个 `.status` 兜底
  // （`decision ?? status`）能把白名单整个绕过去而冒烟仍然全绿。
  // 现在把"直接说引擎的话"这条路也钉死：发了 `status` 必须**仍然 400**。
  seen.length = 0
  const viaEngineField = await invoke('/ks/materials/review', {
    method: 'POST', search: '?material_id=mat_1', body: { status: 'approved' },
  })
  check('用引擎字段名 `status` 直接调也必须 400（白名单不可绕）',
    viaEngineField.status === 400 && seen.length === 0,
    `${viaEngineField.status} engineCalls=${seen.length}`)
  seen.length = 0
  const bothFields = await invoke('/ks/materials/review', {
    method: 'POST', search: '?material_id=mat_1', body: { status: 'pending', decision: 'approved' },
  })
  check('同时给 status=pending 与 decision=approved ⇒ 以 decision 为准（不给 status 留缝）',
    bothFields.status === 200 && lastEngine().sent.status === 'approved'
    && lastEngine().sent.decision === undefined, JSON.stringify(lastEngine().sent))

  seen.length = 0
  const noMid = await invoke('/ks/materials/review', { method: 'POST', body: { decision: 'approved' } })
  check('POST /review 缺 material_id → 400 且不打扰引擎',
    noMid.status === 400 && seen.length === 0, `${noMid.status} engineCalls=${seen.length}`)

  // ⚠ **`data` 里的每个字段都要能到界面**（"算了但看不见"是本战役反复打的坑）：
  // 批准后引擎会在 `data.track_l` 里报告 Track L（自动入库）的结果，本层必须原样转发。
  // 用一个**多字段**的 data 钉住：将来谁给 mapProbe 加个 `pick` 白名单，这条会红。
  seen.length = 0
  responder = () => ({
    body: {
      code: 200,
      data: {
        material_id: 'mat_1', review_status: 'approved', doc_id: 'doc_x',
        track_l: { action: 'import', imported: true, why: '已走既有 ingest 管线入库并回指' },
      },
    },
  })
  const withTl = await invoke('/ks/materials/review', {
    method: 'POST', search: '?material_id=mat_1', body: { decision: 'approved' },
  })
  check('批准响应里的 `track_l`（自动入库结果）被转发给界面',
    withTl.status === 200 && withTl.body.data?.track_l?.action === 'import'
    && withTl.body.data?.doc_id === 'doc_x',
    JSON.stringify(withTl.body.data ?? null))

  seen.length = 0
  const badJson = await invoke('/ks/materials/review', {
    method: 'POST', search: '?material_id=mat_1', body: undefined,
  })
  check('POST /review 空 body → 400（解析不出 decision，不当默认批准）',
    badJson.status === 400 && seen.length === 0, `${badJson.status} engineCalls=${seen.length}`)
}

/* ---------------- 4b. 畸形 JSON：**必须**有响应，绝不能挂死 ----------------
 *
 * 独立复核 2026-09-17 报的 **P0**：`route_util.readJsonBody` 第一版在 `end` 里先
 * `done = true` 再走一个"见 done 就 return"的 `fail()`，于是**畸形 JSON 的请求永不 settle**
 * —— 9 条材料路由与既有 `/ks/report/export` 一起挂死（客户端只能超时，且 handler 与
 * 连接被永久占住）。
 *
 * ⚠ 这个 bug **逃过了本冒烟的第一版**：`invoke()` 只会 `JSON.stringify`，
 * 畸形 body 那条路**零覆盖**。所以这里既补覆盖，也用**超时竞赛**保证
 * "挂死"表现为**一条会红的断言**，而不是把冒烟本身挂住。
 */
{
  for (const [path, opts] of [
    ['/ks/materials/review', { method: 'POST', search: '?material_id=mat_1' }],
    ['/ks/materials/tier', { method: 'POST', search: '?material_id=mat_1' }],
    ['/ks/materials/role', { method: 'POST', search: '?material_id=mat_1' }],
    ['/ks/materials/scan', { method: 'POST', search: '?project_id=prj_a' }],
    ['/ks/materials/collect', { method: 'POST', search: '?project_id=prj_a' }],
    ['/ks/materials/projects', { method: 'POST' }],
  ]) {
    seen.length = 0
    const result = await Promise.race([
      invoke(path, { ...opts, rawBody: '{"decision":' }),      // 截断的 JSON
      new Promise((resolve) => setTimeout(() => resolve({ status: 'HANG' }), 1500)),
    ])
    check(`畸形 JSON → ${path} 有响应（400），不挂死`,
      result.status === 400 && seen.length === 0,
      `status=${result.status} engineCalls=${seen.length}`)
  }

  // 非 JSON 的纯文本同样要走 400 而不是崩/挂
  const notJson = await Promise.race([
    invoke('/ks/materials/review', {
      method: 'POST', search: '?material_id=mat_1', rawBody: 'not json at all',
    }),
    new Promise((resolve) => setTimeout(() => resolve({ status: 'HANG' }), 1500)),
  ])
  check('非 JSON 文本 → 400，不挂死', notJson.status === 400, String(notJson.status))
}

/* --------------------------- 5. 两个轴 --------------------------- */

{
  seen.length = 0
  responder = () => ({ body: { code: 200, data: { source_tier: 'T2' } } })
  await invoke('/ks/materials/tier', {
    method: 'POST', search: '?material_id=mat_1', body: { tier: 'T2' },
  })
  check('轴 A（tier）改动**默认留痕为 user**（用户改的与系统判的不能混）',
    lastEngine().path === '/api/v1/materials/mat_1/tier'
    && lastEngine().sent.tier === 'T2' && lastEngine().sent.source === 'user',
    JSON.stringify(lastEngine().sent))

  seen.length = 0
  responder = () => ({ body: { code: 200, data: { task_role: 'criterion' } } })
  await invoke('/ks/materials/role', {
    method: 'POST', search: '?material_id=mat_1', body: { role: 'criterion' },
  })
  check('轴 B（role）独立于轴 A 单独设置',
    lastEngine().path === '/api/v1/materials/mat_1/role'
    && lastEngine().sent.role === 'criterion', JSON.stringify(lastEngine().sent))

  // ⚠ **`role: null` 必须放行**（独立复核 2026-09-17 报的 MEDIUM）：面板上「未声明效力」
  // 这个选项发的就是 `null`（撤销声明），而引擎/仓库本来就支持 None。
  // 原实现要求"非空字符串" ⇒ 那个选项**每次都被 400 打回**，装了却用不了。
  seen.length = 0
  responder = () => ({ body: { code: 200, data: { task_role: null } } })
  const cleared = await invoke('/ks/materials/role', {
    method: 'POST', search: '?material_id=mat_1', body: { role: null },
  })
  check('role: null（撤销声明）放行到引擎，不再 400',
    cleared.status === 200 && lastEngine().sent.role === null,
    `${cleared.status} sent=${JSON.stringify(lastEngine()?.sent)}`)
  seen.length = 0
  const noRoleKey = await invoke('/ks/materials/role', {
    method: 'POST', search: '?material_id=mat_1', body: {},
  })
  check('缺 role 键 → 400（"没说要设什么"与"要撤销"是两回事）',
    noRoleKey.status === 400 && seen.length === 0, String(noRoleKey.status))
  seen.length = 0
  const emptyRole = await invoke('/ks/materials/role', {
    method: 'POST', search: '?material_id=mat_1', body: { role: '' },
  })
  check('role 为空串 → 400（含混的值不猜）',
    emptyRole.status === 400 && seen.length === 0, String(emptyRole.status))

  // tier 的 `reason` 必须转发：引擎把 tier_reason **写成**它，不传就擦掉原判据
  seen.length = 0
  responder = () => ({ body: { code: 200, data: { source_tier: 'T2' } } })
  await invoke('/ks/materials/tier', {
    method: 'POST', search: '?material_id=mat_1',
    body: { tier: 'T2', reason: '用户改级：T1 → T2' },
  })
  check('tier 的 reason 被转发（否则原判级说明被擦成空）',
    lastEngine().sent.reason === '用户改级：T1 → T2', JSON.stringify(lastEngine().sent))
  seen.length = 0
  await invoke('/ks/materials/tier', {
    method: 'POST', search: '?material_id=mat_1', body: { tier: 'T2' },
  })
  check('不给 reason 时发 null（显式，而不是漏字段）',
    'reason' in lastEngine().sent && lastEngine().sent.reason === null,
    JSON.stringify(lastEngine().sent))

  seen.length = 0
  const noTier = await invoke('/ks/materials/tier', {
    method: 'POST', search: '?material_id=mat_1', body: {},
  })
  check('缺 tier → 400 且不打扰引擎', noTier.status === 400 && seen.length === 0)
  seen.length = 0
  const noRole = await invoke('/ks/materials/role', {
    method: 'POST', search: '?material_id=mat_1', body: {},
  })
  check('缺 role → 400 且不打扰引擎', noRole.status === 400 && seen.length === 0)

  seen.length = 0
  responder = () => ({ body: { code: 200, data: { chunks: [] } } })
  await invoke('/ks/materials/chunks', { search: '?material_id=mat_1&offset=0&limit=5' })
  check('GET /chunks 透传分页（评审必须能读到正文，否则是盲签）',
    lastEngine().path === '/api/v1/materials/mat_1/chunks?material_id=mat_1&offset=0&limit=5',
    lastEngine().path)

  seen.length = 0
  responder = () => ({ body: { code: 200, data: { T0: '法定/官方原文' } } })
  await invoke('/ks/materials/tiers')
  check('GET /tiers 从引擎取层定义（判据只有一个所有者，前端不抄一份）',
    lastEngine().path === '/api/v1/materials/tiers', lastEngine().path)

  // ---- 引用锚点稳定性（§10.49）：两个 id 走**同一个字面路径**，必给其一 ----
  seen.length = 0
  responder = () => ({ body: { code: 200, data: { material_id: 'mat_1', status: 'ok' } } })
  await invoke('/ks/materials/locators', { search: '?material_id=mat_1' })
  check('GET /locators?material_id= 打到单份材料的锚点健康度',
    lastEngine().path === '/api/v1/materials/mat_1/locators', lastEngine().path)

  seen.length = 0
  responder = () => ({ body: { code: 200, data: { project_id: 'prj_a', counts: {} } } })
  await invoke('/ks/materials/locators', { search: '?project_id=prj_a' })
  check('GET /locators?project_id= 打到项目级总览（一次拿全，界面不逐行发请求）',
    lastEngine().path === '/api/v1/materials/projects/prj_a/locators', lastEngine().path)

  seen.length = 0
  const noId = await invoke('/ks/materials/locators')
  check('两者都不给 → 400 且不打扰引擎（不猜）',
    noId.status === 400 && seen.length === 0, String(noId.status))

  seen.length = 0
  responder = () => ({ body: { code: 200, data: { status: 'unavailable', why: '验不了' } } })
  await invoke('/ks/materials/reverify', { method: 'POST', search: '?material_id=mat_1' })
  check('POST /reverify 打到重解析比对（**贵**动作，只由用户点）',
    lastEngine().path === '/api/v1/materials/mat_1/reverify', lastEngine().path)
}

/* --------------------------- 6. 方法与错误映射 --------------------------- */

{
  for (const [path, method] of [
    ['/ks/materials/list', 'POST'],
    ['/ks/materials/inbox', 'POST'],
    ['/ks/materials/projects', 'DELETE'],
    ['/ks/materials/chunks', 'POST'],
    ['/ks/materials/tiers', 'POST'],
    ['/ks/materials/collect', 'GET'],
    ['/ks/materials/locators', 'POST'],
    ['/ks/materials/reverify', 'GET'],
  ]) {
    const r = await invoke(path, { method, search: '?project_id=prj_a&material_id=mat_1' })
    check(`${method} ${path} → 405（方法守卫）`, r.status === 405, String(r.status))
  }

  seen.length = 0
  responder = () => ({ http: 422, body: { code: 422, error: 'tier_invalid', message: '非法层级' } })
  const bad = await invoke('/ks/materials/tier', {
    method: 'POST', search: '?material_id=mat_1', body: { tier: 'T9' },
  })
  check('引擎 422 → 400 并**原样带出引擎的错误信息**',
    bad.status === 400 && bad.body.error.code === 'tier_invalid'
    && bad.body.error.message === '非法层级', JSON.stringify(bad.body))

  responder = () => ({ http: 500, body: { code: 500, error: 'internal_error' } })
  const boom = await invoke('/ks/materials/projects')
  check('引擎 5xx → 502 engine_error', boom.status === 502
    && boom.body.error.code === 'engine_error', JSON.stringify(boom.body))

  const savedPort = manager.ensureLive
  manager.ensureLive = async () => { throw new Error('引擎没起来（模拟）') }
  const down = await invoke('/ks/materials/projects')
  manager.ensureLive = savedPort
  check('引擎不可达 → 503 engine_unavailable（不抛到框架）',
    down.status === 503 && down.body.error.code === 'engine_unavailable',
    JSON.stringify(down.body))
}

server.close()

/* ------------------------------------------------------------------ */

const failed = results.filter((r) => !r.ok)
if (failed.length > 0) {
  console.error(`\nsmoke-materials-routes: ${failed.length}/${results.length} FAILED`)
  for (const f of failed) console.error(`  - ${f.name}`)
  process.exit(1)
}
console.log(`\nsmoke-materials-routes: ${results.length}/${results.length} PASS`)
