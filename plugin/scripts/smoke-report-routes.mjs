/**
 * ks-dsh-plugin — scripts/smoke-report-routes.mjs
 *
 * `/ks/report/*` 同源路由的宿主侧回归（**本文件之前这类路由一条都没被冒烟覆盖**——
 * 2026-09-17 加研究报告路由时发现的**覆盖缺口**，顺手补上）。
 *
 * 钉四件事：
 *   ① **五条**路由都注册、都是 `kind:'exact'`、方法守卫生效；
 *   ② **query 白名单**（未知键丢弃）与**body 白名单**（`/ks/report/research` 只转发认识的键）；
 *   ③ 引擎错误映射：**404 原样透传**（不许翻成 502 engine_error——那是归因错误）、
 *      422 → 400、5xx → 502、引擎不可达 → 503；
 *   ④ `/ks/report/export` 的二进制回传链（POST 生成 → GET 下载 → 以 xlsx MIME 回给调用方）。
 *
 * ⚠ 2026-09-19（EXECUTION-PLAN 第 4 步）：原来的第 5 条路由
 * `/ks/report/research/slides`（PPT）与它的整节断言**已随业主否决 Word/PPT 交付物拆除**
 * ——路由数 6 → **5**。
 *
 * 跑法：node scripts/smoke-report-routes.mjs   （退出码 0 = 全通过）
 */

import { createServer } from 'node:http'

import {
  KS_REPORT_DOCS_PATH,
  KS_REPORT_DRAFT_PATH,
  KS_REPORT_EFFECT_PATH,
  KS_REPORT_EXPORT_PATH,
  KS_REPORT_RESEARCH_PATH,
  registerKsReportRoutes,
} from '../src/report.js'

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
    if (r.bytes !== undefined) {          // 二进制回传（导出文件下载）
      res.writeHead(r.http ?? 200, { 'content-type': 'application/octet-stream' })
      res.end(Buffer.from(r.bytes))
      return
    }
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
const dispose = registerKsReportRoutes(ctx, manager)

/* ----------------------------- 假 req / res ----------------------------- */

function makeRes() {
  const out = { status: null, body: null, headers: null, raw: null }
  return {
    out,
    writeHead(status, headers) { out.status = status; out.headers = headers ?? null },
    end(text) {
      out.raw = text
      try { out.body = JSON.parse(text) } catch { out.body = text }
    },
  }
}

async function invoke(path, { method = 'GET', body = undefined, search = '' } = {}) {
  const def = routes.get(path)
  if (def === undefined) throw new Error(`路由未注册: ${path}`)
  const { EventEmitter } = await import('node:events')
  const req = new EventEmitter()
  req.method = method
  req.url = `${path}${search}`
  req.destroy = () => {}
  const res = makeRes()
  const p = def.handler(req, res)
  setImmediate(() => {
    if (body !== undefined) req.emit('data', Buffer.from(JSON.stringify(body), 'utf8'))
    req.emit('end')
  })
  await p
  return { status: res.out.status, body: res.out.body, headers: res.out.headers, raw: res.out.raw }
}

const lastEngine = () => seen[seen.length - 1]

/* --------------------------- 1. 注册面 --------------------------- */

{
  check('注册了全部 5 条报告路由',
    routes.size === 5 && [KS_REPORT_EFFECT_PATH, KS_REPORT_DOCS_PATH,
      KS_REPORT_EXPORT_PATH, KS_REPORT_RESEARCH_PATH,
      KS_REPORT_DRAFT_PATH]
      .every((p) => routes.has(p)),
    `${routes.size} routes`)
  check('全部是 kind=exact（字面路径，不会被通配吃掉）',
    [...routes.values()].every((d) => d.kind === 'exact'))
  check('dispose 可调用（cordis effect 契约）', typeof dispose === 'function')
}

/* --------------------------- 2. 效力报告（既有三条） --------------------------- */

{
  seen.length = 0
  responder = () => ({ body: { code: 200, status: 'success', data: { total: 0 } } })
  await invoke(KS_REPORT_EFFECT_PATH, { search: '?window=all&color=red&evil=1' })
  check('GET /ks/report/effect 透传 window/color，丢弃未知 query 键',
    lastEngine().path === '/api/v1/report/effect?window=all&color=red',
    lastEngine().path)

  seen.length = 0
  await invoke(KS_REPORT_DOCS_PATH, { search: '?top=std&l2=C%20医药&l3=x' })
  check('GET /ks/report/effect/docs 透传下钻参数（含空格还原）',
    lastEngine().path.includes('%20') || lastEngine().path.includes('+'),
    lastEngine().path)

  seen.length = 0
  const notPost = await invoke(KS_REPORT_EXPORT_PATH)
  check('GET /ks/report/export → 405（方法守卫）且不打扰引擎',
    notPost.status === 405 && seen.length === 0, `${notPost.status} engineCalls=${seen.length}`)
}

/* --------------------------- 3. 二进制回传链（export） --------------------------- */

{
  seen.length = 0
  responder = (url) => {
    if (url.startsWith('/api/v1/export/download')) return { bytes: Buffer.from('XLSXBYTES') }
    return { body: { code: 200, status: 'success', data: { name: '效力报告.xlsx' } } }
  }
  const r = await invoke(KS_REPORT_EXPORT_PATH, { method: 'POST', body: { window: 'all' } })
  check('POST /ks/report/export：生成 → 下载 → 以 xlsx MIME 回给调用方',
    r.status === 200 && String(r.raw).includes('XLSXBYTES')
    && String(r.headers?.['Content-Type'] ?? '').includes('spreadsheetml'),
    `${r.status} ctype=${r.headers?.['Content-Type']}`)
  check('下载文件名带 UTF-8 编码（中文名不炸）',
    String(r.headers?.['Content-Disposition'] ?? '').includes("filename*=UTF-8''"),
    String(r.headers?.['Content-Disposition'] ?? ''))

  responder = () => ({ body: { code: 200, status: 'success', data: {} } })
  const noName = await invoke(KS_REPORT_EXPORT_PATH, { method: 'POST', body: {} })
  check('引擎没给文件名 → 502 engine_bad_response（不假装成功）',
    noName.status === 502 && noName.body.error.code === 'engine_bad_response',
    `${noName.status} ${JSON.stringify(noName.body)}`)
}

/* --------------------------- 4. 研究报告（本步新增） --------------------------- */

{
  seen.length = 0
  responder = () => ({ body: { code: 200, status: 'success', data: { markdown: '# R' } } })
  await invoke(KS_REPORT_RESEARCH_PATH, {
    method: 'POST',
    body: { project_id: ' prj_a ', title: 'T', query: 'Q', conclusion_md: 'C',
      limit: 5, dry_run: true, 未知键: 'x' },
  })
  check('POST /ks/report/research 打到引擎正确路径',
    lastEngine().method === 'POST' && lastEngine().path === '/api/v1/report/research',
    `${lastEngine().method} ${lastEngine().path}`)
  check('转发认识的键 + 去空白 + dry_run 归一成布尔',
    lastEngine().sent.project_id === 'prj_a' && lastEngine().sent.title === 'T'
    && lastEngine().sent.query === 'Q' && lastEngine().sent.conclusion_md === 'C'
    && lastEngine().sent.limit === 5 && lastEngine().sent.dry_run === true,
    JSON.stringify(lastEngine().sent))
  check('**未知键不透传**（白名单，不是整包转发）',
    lastEngine().sent['未知键'] === undefined, JSON.stringify(lastEngine().sent))

  seen.length = 0
  const noPid = await invoke(KS_REPORT_RESEARCH_PATH, { method: 'POST', body: { title: 'T' } })
  check('缺 project_id → 400 且**不打扰引擎**',
    noPid.status === 400 && seen.length === 0, `${noPid.status} engineCalls=${seen.length}`)

  seen.length = 0
  const blankPid = await invoke(KS_REPORT_RESEARCH_PATH, {
    method: 'POST', body: { project_id: '   ' },
  })
  check('空白 project_id → 400 且不打扰引擎',
    blankPid.status === 400 && seen.length === 0, `${blankPid.status} engineCalls=${seen.length}`)

  seen.length = 0
  const getMethod = await invoke(KS_REPORT_RESEARCH_PATH, { search: '?project_id=prj_a' })
  check('GET /ks/report/research → 405（方法守卫）',
    getMethod.status === 405 && seen.length === 0, `${getMethod.status}`)

  // ⚠ **404 必须原样透传**（不许翻成 502 engine_error）：引擎说"项目不存在"，
  // 界面就该显示"项目不存在"，否则用户会去查引擎（归因错误）。
  seen.length = 0
  responder = () => ({
    http: 404,
    body: { code: 404, status: 'error', error: 'materials_not_found',
      message: 'report: 项目不存在: prj_x' },
  })
  const notFound = await invoke(KS_REPORT_RESEARCH_PATH, {
    method: 'POST', body: { project_id: 'prj_x' },
  })
  check('引擎 404 → 同源 404 且带出引擎的原因（不是 502 engine_error）',
    notFound.status === 404 && notFound.body.error.code === 'materials_not_found'
    && String(notFound.body.error.message).includes('项目不存在'),
    `${notFound.status} ${JSON.stringify(notFound.body)}`)

  responder = () => ({
    http: 422, body: { code: 422, error: 'materials_bad_request', message: 'limit 必须是整数' },
  })
  const bad = await invoke(KS_REPORT_RESEARCH_PATH, {
    method: 'POST', body: { project_id: 'prj_a', limit: 'x' },
  })
  check('引擎 422 → 同源 400 且原样带出引擎的错误信息',
    bad.status === 400 && bad.body.error.message === 'limit 必须是整数',
    `${bad.status} ${JSON.stringify(bad.body)}`)

  responder = () => ({ http: 500, body: { code: 500, error: 'internal_error' } })
  const boom = await invoke(KS_REPORT_RESEARCH_PATH, {
    method: 'POST', body: { project_id: 'prj_a' },
  })
  check('引擎 5xx → 502 engine_error', boom.status === 502, String(boom.status))

  responder = () => ({ body: { code: 200, status: 'success' } })   // 没有 data
  const noData = await invoke(KS_REPORT_RESEARCH_PATH, {
    method: 'POST', body: { project_id: 'prj_a' },
  })
  check('引擎 200 但没有 data → 依然 200 + 空对象（与本模块其它路由同款，不伪装）',
    noData.status === 200 && noData.body.ok === true, JSON.stringify(noData.body))
}

/* --------------------------- 5. 结论草稿（/research/draft，§10.96） --------------------------- */

{
  seen.length = 0
  responder = () => ({
    body: { code: 200, status: 'success',
      data: { status: 'unapproved_draft', disclaimer: '未经用户批准…',
        draft_md: '每晚不超过五百元 [[m:0]]。', derivation_md: 'd',
        citations: { material_refs: [0], unknown: [], not_load_bearing: [],
          unchecked_law_refs: [] },
        warnings: [], counts: { approved: 1 }, notes: [], usable_indices: [0],
        llm_called: true } },
  })
  const ok = await invoke(KS_REPORT_DRAFT_PATH, {
    method: 'POST',
    body: { project_id: ' prj_a ', query: ' 住宿标准 ', limit: 4, 未知键: 'x' },
  })
  check('POST /ks/report/research/draft 打到引擎正确路径',
    lastEngine().method === 'POST'
    && lastEngine().path === '/api/v1/report/research/draft',
    `${lastEngine().method} ${lastEngine().path}`)
  check('草稿路由：只转发 project_id/query/limit（**未知键与 title/conclusion_md 都不发**）',
    lastEngine().sent.project_id === 'prj_a' && lastEngine().sent.query === '住宿标准'
    && lastEngine().sent.limit === 4 && lastEngine().sent['未知键'] === undefined
    && lastEngine().sent.title === undefined
    && lastEngine().sent.conclusion_md === undefined,
    JSON.stringify(lastEngine().sent))
  check('`unapproved_draft` 与草稿正文原样带出（**契约**：界面必须能看出未批准）',
    ok.status === 200 && ok.body.data.status === 'unapproved_draft'
    && String(ok.body.data.draft_md).includes('[[m:0]]'),
    JSON.stringify(ok.body.data ?? null))

  seen.length = 0
  const noPid = await invoke(KS_REPORT_DRAFT_PATH,
    { method: 'POST', body: { query: 'Q' } })
  check('草稿路由：缺 project_id → 400 且**不打扰引擎**',
    noPid.status === 400 && seen.length === 0, `${noPid.status} engineCalls=${seen.length}`)

  seen.length = 0
  const noQuery = await invoke(KS_REPORT_DRAFT_PATH,
    { method: 'POST', body: { project_id: 'prj_a' } })
  check('草稿路由：缺 query → 400 且不打扰引擎（起草必须先有研究问题）',
    noQuery.status === 400 && seen.length === 0, `${noQuery.status} engineCalls=${seen.length}`)

  seen.length = 0
  const blankQuery = await invoke(KS_REPORT_DRAFT_PATH,
    { method: 'POST', body: { project_id: 'prj_a', query: '   ' } })
  check('草稿路由：空白 query → 400 且不打扰引擎',
    blankQuery.status === 400 && seen.length === 0,
    `${blankQuery.status} engineCalls=${seen.length}`)

  seen.length = 0
  const getDraft = await invoke(KS_REPORT_DRAFT_PATH, {})
  check('草稿路由：GET → 405（方法守卫）',
    getDraft.status === 405 && seen.length === 0, String(getDraft.status))

  // 引擎说"没有可承重材料"（200 + 空草稿 + llm_called=false）⇒ **原样透传**，不许翻成错误
  responder = () => ({
    body: { code: 200, status: 'success',
      data: { status: 'unapproved_draft', draft_md: '', derivation_md: '',
        warnings: ['没有起草'], llm_called: false, usable_indices: [] } },
  })
  const none = await invoke(KS_REPORT_DRAFT_PATH,
    { method: 'POST', body: { project_id: 'prj_a', query: 'Q' } })
  check('没有可承重材料：200 + llm_called=false 原样透传（**不是**失败）',
    none.status === 200 && none.body.data.llm_called === false
    && none.body.data.draft_md === '', JSON.stringify(none.body.data ?? null))

  // LLM 不可用：引擎 500 llm_unavailable ⇒ 本层按 502 引擎错误转达（不伪装成功）
  responder = () => ({
    http: 500, body: { code: 500, error: 'llm_unavailable', message: '未配置 Key' },
  })
  const noLlm = await invoke(KS_REPORT_DRAFT_PATH,
    { method: 'POST', body: { project_id: 'prj_a', query: 'Q' } })
  check('LLM 不可用（引擎 500）→ 502 engine_error（不假装起草成功）',
    noLlm.status === 502, String(noLlm.status))
}

/* ------------------------------------------------------------------ */

server.close()

const failed = results.filter((r) => !r.ok)
if (failed.length > 0) {
  console.error(`\nsmoke-report-routes: ${failed.length}/${results.length} FAILED`)
  for (const f of failed) console.error(`  - ${f.name}`)
  process.exit(1)
}
console.log(`\nsmoke-report-routes: ${results.length}/${results.length} PASS`)
