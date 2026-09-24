/**
 * ks-dsh-plugin — scripts/smoke-tool-contract.mjs
 *
 * 第 6 步 §1 的门禁：**6 个模型工具的返回值必须满足它们自己声明的 `output.schema`**，
 * 且那份 schema 本身必须是宿主支持的子集。
 *
 * ## 为什么必须有一条**离线**门禁（真机那两个消费点长什么样）
 * 宿主的两条检查都只在真机上生效：
 *   · 注册期 `assertSupportedJsonSchema(tool.output.schema)`（(DSH)
 *     `packages/core/tools/src/index.ts:1062`）——schema 用了子集外的关键字 ⇒ 抛错 ⇒
 *     **整个插件挂不上**（不是这一个工具不可用）；
 *   · 取值期 `snapshotToolValue` + `validateJsonSchemaValue`（同文件 `:1813-1816`）——
 *     返回值和 schema 对不上 ⇒ `ToolOutputError` ⇒ **每次调用都 isError**。
 * 两者在离线侧（本仓所有其它冒烟）**完全静默** ⇒ 必须有一条能当场红、又不依赖真宿主的脚本。
 *
 * ## 怎么做到零依赖、不 spawn 引擎、不发真实网络请求
 *   1. `apply()` 用**假 cordis ctx**（口径照 `smoke-effect-tool.mjs` 的 `_services`：
 *      可缺省服务一律走 `ctx.get(name)`），`tools.register` 只把定义**捕获**下来；
 *   2. `globalThis.fetch` **全量打桩**：路由到本文件里的桩响应，没有兜底的真实 fetch；
 *   3. `KS_DATA_DIR` 指向临时目录并预置一份"健康"的 `engine.session.json` ⇒
 *      `ensureLive()` 探活即 200 ⇒ **绝不 spawn 引擎**（数据写 %TEMP%，代码树零运行产物）。
 *
 * ## 断言分两类（**反向对照是这条门禁的全部价值**）
 *   · 正向：每个工具各 1–3 组 `(args, 桩响应)`，每组过 `checkToolContract`
 *     （schema 合法 / 值无 undefined / 值满足 schema / render 给出非空 text 块）；
 *   · 反向（A4/A5）：把同一个值拿去喂**故意错**的 schema，断言**必须出现违规**——
 *     没有这两条，上面那四条完全可能是空转的假绿（施工单 §1"怎么验"的 A4 原话：
 *     "A2 空转 ⇒ 整个第 1 条是假绿"）。
 *
 * 跑法：node scripts/smoke-tool-contract.mjs   （退出码 0 = 全通过）
 */

import { mkdtemp, readFile, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

// 隔离落盘（同 `smoke-effect-tool.mjs` 的理由）：`apply()` 会拉起整个 host 半边，
// 其中有会落盘的状态文件与引擎会话文件。两个变量都指向临时目录。
process.env.KS_CHATMODE_DIR = await mkdtemp(join(tmpdir(), 'ks-tool-contract-chatmode-'))
const DATA_DIR = await mkdtemp(join(tmpdir(), 'ks-tool-contract-data-'))
process.env.KS_DATA_DIR = DATA_DIR
// 预置"健康"的引擎会话：`ensureLive()` 读到它会去探活（fetch 已打桩 ⇒ 200）⇒ 复用，不 spawn。
// pid 用本进程：`parseSession` 只要求正整数；复用路径不查进程存活（(engine.js) `_ensureLive`）。
await writeFile(join(DATA_DIR, 'engine.session.json'), JSON.stringify({
  port: 45_777, pid: process.pid, token: 'tok_smoke_contract', started_at: null,
}))

const { apply } = await import('../src/index.js')
const { setMode, effectiveChatMode, __resetChatModeForTests } = await import('../src/chatmode.js')
const { checkToolContract, violationsOf } = await import('./lib/tool-contract.mjs')

const results = []
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}

/* ------------------------------------------------------------------ *
 * 假引擎桩（`globalThis.fetch` 全量打桩；**没有**兜底的真实 fetch）
 * ------------------------------------------------------------------ */

/** `/api/v1/health` 的扁平体（引擎 `health()` 的真实字段，`src/core/api/server.py`）。 */
const HEALTH_OK = {
  status: 'healthy', uptime_seconds: 12, db_status: 'ok',
  vector_engine: 'ok', parser_worker: 'ok',
}
/** 只有 `status` 的稀疏体：其余字段缺席 ⇒ 工具必须回 `null`（**不是** undefined）。 */
const HEALTH_SPARSE = { status: 'degraded' }

/** 兜底响应：`apply()` 里那几条 fire-and-forget 的启动巡检/公告/入库接线也会打 fetch。 */
const benign = (path) => (path.startsWith('/api/v1/health')
  ? { body: HEALTH_OK }
  : { body: { code: 200, status: 'success', data: {} } })

/** 当前场景的响应器：`(path, init) => ({ http?, body })`（未命中一律回落 `benign`）。 */
let responder = benign

const stripOrigin = (url) => String(url).replace(/^https?:\/\/[^/]+/, '')

globalThis.fetch = async (url, init) => {
  const path = stripOrigin(url)
  const r = responder(path, init)
  const status = r.http ?? 200
  return {
    status,
    ok: status >= 200 && status < 300,
    text: async () => JSON.stringify(r.body ?? r),
  }
}

/* ------------------------------------------------------------------ *
 * 假 cordis ctx（口径照 `smoke-effect-tool.mjs` 的 `_services`）
 * ------------------------------------------------------------------ */

const fakeSessions = new Map()
const tools = new Map()
const registeredCommands = []
const _services = {
  tools: { register(tool) { tools.set(tool.name, tool) } },
  webServer: { register() { return () => {} } },
  systemPrompt: { section() { return () => {} } },
  agents: { get(sessionId) { return fakeSessions.get(sessionId) } },
  commands: { register(def) { registeredCommands.push(def); return () => {} } },
  logger: { info() {}, warn() {}, error() {} },
}
const ctx = {
  ..._services,
  /** cordis 的服务查找：**只返回已提供的服务**（这里用同一张表模拟）。 */
  get(name) { return _services[name] },
  effect(fn) { return fn() },
}

/* ------------------------------------------------------------------ *
 * 桩响应数据
 * ------------------------------------------------------------------ */

const EFFECT_SUMMARY = {
  code: 200,
  status: 'success',
  data: {
    generated_at: '2026-10-01 09:00:00',
    window: 'all',
    colors: { red: 2, yellow: 1, green: 5, gray: 2, reference: 0 },
    total: 10,
    std: { total: 8, colors: { red: 2, yellow: 1, green: 4, gray: 1, reference: 0 } },
    law: { total: 2, colors: { red: 0, yellow: 0, green: 1, gray: 1, reference: 0 } },
    tree: [
      {
        top: 'std',
        name: '国家标准·行业标准·团体标准',
        colors: { red: 2, yellow: 1, green: 4, gray: 1, reference: 0 },
        items: [
          { name: 'C 医药、卫生、劳动保护', colors: { red: 1, yellow: 1, green: 1, gray: 1, reference: 0 } },
          { name: 'F 能源、核技术', colors: { red: 1, yellow: 0, green: 1, gray: 0, reference: 0 } },
          { name: 'J 机械', colors: { red: 0, yellow: 0, green: 1, gray: 0, reference: 0 } },
          { name: 'K 电工', colors: { red: 0, yellow: 0, green: 1, gray: 0, reference: 0 } },
        ],
      },
      { top: 'law', name: '法律法规', colors: { red: 0, yellow: 0, green: 1, gray: 1, reference: 0 }, items: [] },
    ],
  },
}
/** 一红一黄：**第二条故意没有 `doc_id`** ⇒ `evidence_url` 必须是 `null`（覆盖可空字段）。 */
const EFFECT_DOCS = [
  { status: 'superseded', color: 'red', doc_id: 'doc_r1', standard_no: 'GB 1111-2011',
    standard_name: '红一号', effective_from: '2011-01-01', superseded_by: 'GB 1111-2021',
    withdrawn_date: null },
  { status: 'upcoming', color: 'yellow', standard_no: 'GB 3333-2026', standard_name: '黄一号',
    effective_from: '2099-01-01', superseded_by: null, withdrawn_date: null },
]

const RESOLVE_HIT = {
  code: 200,
  status: 'success',
  data: {
    doc_id: 'doc_r9', page_start: 7, clause_revision_id: 'rev_r9', clause_key: 'k_r9',
    standard_no: 'GB 2222-2020', clause_number: '3.1', legal_status: 'effective',
    bookmarked: false,
  },
}

const ANSWER_FULL = {
  code: 200,
  status: 'success',
  data: {
    tier: 'direct',
    evidence: [
      { doc_id: 'doc_a1', page_start: 3, clause_revision_id: 'rev_a1', standard_no: 'GB 1111-2020',
        clause_number: '5.1.2', title: '高处作业分级', legal_status: 'effective',
        legal_hierarchy: '国家标准', snippet: '高处作业分级……', bookmarked: true },
      // 第二条**不给 bookmarked / snippet / page_start** ⇒ 必须是 null（旧引擎/异常路径不造字段）
      { doc_id: 'doc_a2', standard_no: 'GB 2222-2020', clause_number: '3.1' },
    ],
    derivation: '按条款推导',
    conclusion: '结论',
    verification: {
      is_valid: true,
      answer_confidence: 'high',
      confidence_reasons: ['核验通过且证据高可信'],
      unsupported_clauses: ['9.9.9'],
      unsupported_context: [{
        clause_number: '9.9.9', standard_no: 'GB 9999-2020',
        verdict: 'outside_evidence_standard', reason: '本轮证据里没有这部标准',
      }],
      unverified_numbers: [],
      modality_violations: [{ clause_number: '5.1.2', kind: 'must' }],
      legal_element_violations: [],
      citation_index_warnings: ['[[3]] 未命中'],
    },
    notes: ['只引证据内条款'],
    /* ⚠ 2026-09-20：这一桩**原本只写 `{project_id, counts}`**（简化形体），而引擎两条分支
       （`src/core/llm/ks_answer.py:685-701`）**都**会给 `notes` / `usable_indices` ⇒
       schema 的 `required` 照引擎写全之后，这个"简化桩"就暴露成不忠实。
       **不是把 schema 放宽，而是把桩改成引擎真形状** —— 否则桩会替引擎掩盖形状漂移
       （那正是本项目反复打的"夹具比真相宽松⇒永远量不到"）。 */
    material_usage: {
      project_id: 'prj_x', project_found: true,
      counts: { total: 2, approved: 1, pending: 1, rejected: 0 },
      notes: ['本项目材料已装配'],
      usable_indices: [0],
    },
    _meta: {
      evidence_total: 2,
      retrieval: { result_count: 2, expanded_count: 1, vector_engine: 'ok', rerank: { on: true } },
      llm_raw_length: 1234,
    },
  },
}
/** 200 但 `data` 只有 tier/notes：`evidence` 缺席、`verification` 缺席 ⇒ 全给 null/空。 */
const ANSWER_BARE = {
  code: 200, status: 'success', data: { tier: 'reference', notes: [] },
}
/**
 * 第 6 步（2026-09-21）：**引擎回显的检索范围**（`data.scope`）那一支。
 *
 * ⚠ 这条桩的形状逐字照引擎 `ks_answer.answer()`（`src/core/llm/ks_answer.py`）：
 *   `{kind, folder_ids, folder_count, doc_count, empty}`。而 `ANSWER_FULL` / `ANSWER_BARE`
 *   都**没有** `scope` ⇒ 那里工具应当给 `scope: null`（"没限定范围"），两个方向都在这份冒烟里。
 * ⚠ 为什么值得单开：`scope` 是**引擎算的真值**，与宿主侧的 `answer_scope`（"host 是否强制传参"）
 *   是两个东西；少转发它，聊天里的模型就说不出"这次是在什么范围里检索的"（本批就是被
 *   `smoke-trim` 的"引擎字段一个都不许静默丢"抓到的）。
 */
const ANSWER_KB_SCOPE = {
  code: 200,
  status: 'success',
  data: {
    tier: 'direct',
    evidence: [{ doc_id: 'doc_in1', clause_revision_id: 'rev_in1', standard_no: 'GB 55037-2022',
      clause_number: '5.2.3', title: '建筑防火通用规范', legal_status: 'effective',
      legal_hierarchy: '国家标准', page_start: 12, snippet: '范围内的一条……' }],
    derivation: '按范围内条款推导',
    conclusion: '范围内答得出',
    verification: null,
    notes: ['【知识库目录范围】检索已在范围内限定。'],
    scope: { kind: 'kb', folder_ids: ['kbf_a', 'kbf_a_child'], folder_count: 2, doc_count: 7, empty: false },
    _meta: { evidence_total: 1, retrieval: { result_count: 1 } },
  },
}
/**
 * ⚠⚠ 2026-09-20（复核 `verify-freeze-step6-1` 打回 A 的**回归位**）：引擎**材料装配失败**那一支
 * （`src/core/llm/ks_answer.py:698-701`）给的是 `{project_id, counts: null, notes: [], usable_indices: [],
 * error}` —— `counts` **是 null**。我第一版 schema 把它写成必填的 `object`（自己的注释里都写着 null），
 * 复核用**真 `ToolRuntime.execute`** 跑出 `INVALID_TOOL_OUTPUT`（真机 isError）。
 * 这一组就是那次的漏网处：**17 组里 `ks_answer` 只有正常分支/422/空信封**。
 */
const ANSWER_MATERIAL_ERROR = {
  code: 200,
  status: 'success',
  data: {
    tier: 'reference',
    evidence: [],
    derivation: '',
    conclusion: '',
    verification: null,
    notes: ['【参考资料】项目 prj_x 的材料载入失败'],
    material_usage: {
      project_id: 'prj_x', counts: null, notes: [], usable_indices: [],
      error: '项目材料载入失败: boom',
    },
    _meta: { evidence_total: 0, retrieval: { result_count: 0, expanded_count: 0 }, llm_raw_length: 12 },
  },
}

const MATERIAL_ROWS = [{
  material_id: 'mat_1', title: '某公司 2024 年年度报告', source_tier: 'T3',
  tier_label: '线索（网上找来的）', tier_source: 'system', task_role: 'reference',
  review_status: 'pending', chunk_count: 12, origin: 'collected', kind: 'report',
  url: 'https://example.com/a', domain: 'example.com', tier_reason: '自采：HTTP 200',
}]

const COLLECTED_MATERIAL = {
  material_id: 'mat_9', title: '某局行政处罚决定书', review_status: 'pending', source_tier: 'T3',
  origin: 'collected', lifecycle: null, url: 'https://example.com/b', domain: 'example.com',
  tier_reason: '自采：HTTP 200',
}

/* ------------------------------------------------------------------ *
 * 场景运行器
 * ------------------------------------------------------------------ */

const execFor = (sessionId) => ({ agent: { session: { id: sessionId, header: {} } } })

let groupCount = 0
/**
 * 跑一组 `(tool, args, 桩响应)` 并过契约门禁。
 *
 * ⚠ `execute()` **抛错**也要如实判 FAIL（不许静默跳过）——那正是真机上
 * `INVALID_TOOL_OUTPUT`/`projectionError` 的离线对应物。
 */
async function group(toolName, label, args, responderFn, sessionId = 'smoke-contract') {
  groupCount += 1
  const tool = tools.get(toolName)
  if (typeof tool?.execute !== 'function') {
    check(`${toolName} [${label}] — the tool is registered`, false, 'tools.get() 不是工具定义')
    return null
  }
  responder = responderFn
  let value = null
  try {
    value = await tool.execute(args, execFor(sessionId))
  } catch (error) {
    check(`${toolName} [${label}] — execute() resolved`, false, String(error?.message ?? error))
    return null
  }
  const report = checkToolContract(tool, args, value)
  for (const c of report.checks) check(`${toolName} [${label}] — ${c.name}`, c.ok, c.detail)
  return value
}

/** 只认某一个路径片段的响应器（其余回落 `benign`，免得启动接线把场景搅浑）。 */
const onlyPath = (fragment, body, http) => (path) => (path.includes(fragment)
  ? { body, http }
  : benign(path))

/** 精确路径匹配的响应器（用于 `/materials/projects` 这种**是别人前缀**的路径）。 */
const exactPath = (target, body) => (path) => (path.split('?')[0] === target
  ? { body }
  : benign(path))

async function main() {
  console.log('=== model-tool output.schema contract smoke ===')
  apply(ctx, {})

  check('6 个模型工具都被 apply() 注册（否则本冒烟是空转）',
    ['ks_ping', 'ks_resolve_clause', 'ks_answer', 'ks_effect_report',
      'ks_materials', 'ks_collect'].every((n) => tools.has(n)),
    [...tools.keys()].join(','))

  __resetChatModeForTests()

  /* ------------------------------ ks_effect_report ------------------------------ */
  const effectFull = await group('ks_effect_report', 'summary+lists', { limit: 2 }, (path) => (
    path.includes('/api/v1/report/effect/color')
      ? { body: { code: 200, status: 'success', data: { colors: { red: 2, yellow: 1 }, count: 3, per_color: true, docs: EFFECT_DOCS } } }
      : onlyPath('/api/v1/report/effect', EFFECT_SUMMARY)(path)
  ))
  check('ks_effect_report [summary+lists] — 红/黄清单都在（这组不是只走了统计分支）',
    Array.isArray(effectFull?.red_list?.docs) && Array.isArray(effectFull?.yellow_list?.docs),
    `red=${effectFull?.red_list?.docs?.length} yellow=${effectFull?.yellow_list?.docs?.length}`)
  check('ks_effect_report [summary+lists] — 无 doc_id 的行的 evidence_url 是 null',
    effectFull?.yellow_list?.docs?.[0]?.evidence_url === null,
    String(effectFull?.yellow_list?.docs?.[0]?.evidence_url))

  await group('ks_effect_report', 'stats-only', { include_attention: false },
    onlyPath('/api/v1/report/effect', EFFECT_SUMMARY))
  await group('ks_effect_report', 'list-failure', { limit: 2 },
    (path) => (path.includes('/api/v1/report/effect/color')
      ? { http: 500, body: { code: 500, message: 'boom' } }
      : onlyPath('/api/v1/report/effect', EFFECT_SUMMARY)(path)))

  /* ---------------------------------- ks_ping ---------------------------------- */
  const pingFull = await group('ks_ping', 'healthy', {},
    onlyPath('/api/v1/health', HEALTH_OK))
  const pingSparse = await group('ks_ping', 'sparse-health', {},
    onlyPath('/api/v1/health', HEALTH_SPARSE))
  check('ks_ping [healthy] — health 的五项都透出（这组真的读到了引擎体）',
    pingFull?.status === 'healthy' && pingFull?.vectorEngine === 'ok'
      && pingFull?.engine?.reused === true,
    JSON.stringify({ status: pingFull?.status, vector: pingFull?.vectorEngine }))
  check('ks_ping [sparse-health] — 引擎没给的字段是 null（**不是** undefined）',
    pingSparse?.uptimeSeconds === null && pingSparse?.dbStatus === null
      && pingSparse?.vectorEngine === null && pingSparse?.parserWorker === null
      && pingSparse?.status === 'degraded',
    JSON.stringify(pingSparse))

  /* ----------------------------- ks_resolve_clause ----------------------------- */
  await group('ks_resolve_clause', 'hit', { standard_no: 'GB 2222-2020', clause_number: '3.1' },
    onlyPath('/api/v1/clauses/resolve', RESOLVE_HIT))
  // ⚠ 「仅收藏」**依附于** forensic（(chatmode.js) `normalizeMode`：`forensic || scoped` 才留
  // bookmarksOnly）⇒ 只 setMode({bookmarksOnly:true}) 是**空转**。这里两个都开，并当场断言
  // 开关真的生效——否则下面那组会变成"永远绿"的假绿。
  setMode('smoke-contract-bookmarks', { forensic: true, bookmarksOnly: true })
  check('前置：用例会话的「仅收藏」真的开了（不然下面那组是空转）',
    effectiveChatMode('smoke-contract-bookmarks').bookmarksOnly === true)
  const resolveOutside = await group('ks_resolve_clause', 'hit-outside-bookmarks',
    { standard_no: 'GB 2222-2020', clause_number: '3.1' },
    onlyPath('/api/v1/clauses/resolve', RESOLVE_HIT), 'smoke-contract-bookmarks')
  check('ks_resolve_clause [hit-outside-bookmarks] — 真的走到了 scope_notice 分支',
    typeof resolveOutside?.scope_notice === 'string'
      && resolveOutside?.bookmarks_scope === 'outside',
    `${String(resolveOutside?.bookmarks_scope)} / notice=${typeof resolveOutside?.scope_notice}`)
  setMode('smoke-contract-bookmarks', { bookmarksOnly: false, forensic: false })
  await group('ks_resolve_clause', 'not-found',
    { standard_no: 'GB 00000-9999', clause_number: '99.99.99' },
    onlyPath('/api/v1/clauses/resolve', { code: 404, error: 'clause_not_found' }, 404))

  /* --------------------------------- ks_answer --------------------------------- */
  const answerFull = await group('ks_answer', 'full-answer', { query: '高处作业怎么分级' },
    onlyPath('/api/v1/ks/answer', ANSWER_FULL))
  check('ks_answer [full-answer] — 核验块与证据都在（不是空壳）',
    answerFull?.verification?.unsupported_context?.length === 1
      && answerFull?.evidence?.length === 2
      && typeof answerFull?.answer_scope?.source === 'string',
    `ev=${answerFull?.evidence?.length} ctx=${answerFull?.verification?.unsupported_context?.length}`)
  /* ⚠⚠ 2026-09-20（顺带抓到的第二条真缺陷的**回归位**）：`params.material_project_id.description`
     明写 "The result carries material_usage" —— 而 `trimAnswer` 算出的 `material_usage`
     **在 `execute` 的 return 里漏抄**，模型永远看不到"本次用了哪个项目的哪几条材料"。
     ⚠ 光有"值满足 schema"**抓不到**它：schema 里 `material_usage` 是**条件键（不 required）**
     （422 路径没有它）⇒ 掉了照样通过。所以这里必须有一条**显式的键在位**断言。 */
  check('ks_answer [full-answer] — 真的转发了 material_usage（description 承诺了它，掉了不会因为 schema 红）',
    answerFull?.material_usage?.project_id === 'prj_x'
      && Array.isArray(answerFull?.material_usage?.usable_indices),
    JSON.stringify(answerFull?.material_usage))
  /* ⚠⚠ 复核 S1（M4 打回补）：**生产端链路判据** —— makeAnswerTool → recordKsTurn 这一环
     原先无判据（删掉 mode 快照全绿）。这里在**真工具调用之后**查只读口，钉住"暂存真的发生
     且 mode 五键在位"。只钉形状不钉取值：取值随 setMode 组变，而**继承边界**已由生产端
     改用执行同作用域 chatMode 统一（复核第 5 条），本判据不把任何一种取值钉成正确。 */
  {
    const { KS_TURN_LAST_PATH, registerKsTurnRoutes } = await import('../src/turn.js')
    const exactRoutes = new Map()
    registerKsTurnRoutes({ webServer: { register(d) { exactRoutes.set(d.path, d); return () => {} } } })
    const out = { status: null, body: null }
    const res = {
      out,
      writeHead(status) { out.status = status },
      end(text) { try { out.body = JSON.parse(text) } catch { out.body = text } },
    }
    await exactRoutes.get(KS_TURN_LAST_PATH).handler({ method: 'GET', url: KS_TURN_LAST_PATH }, res)
    const turn = out.body?.data?.turn
    check('ks_answer [full-answer] — 生产端真暂存（/ks/turn/last 取回这一轮，query 同源）',
      turn?.query === '高处作业怎么分级', JSON.stringify(turn?.query))
    check('ks_answer [full-answer] — mode 快照**五键在位**（生产端断链 = 复核 M4 打回点）',
      turn?.mode !== null && typeof turn?.mode === 'object'
      && ['forensic', 'bookmarksOnly', 'folderId', 'folderName', 'materialProjectName']
        .every((k) => k in turn.mode),
      JSON.stringify(turn?.mode))
  }
  await group('ks_answer', '422-validation-error', { query: 'x' },
    onlyPath('/api/v1/ks/answer', { code: 422, error: 'bad_request', message: 'query 太短' }, 422))
  await group('ks_answer', 'bare-envelope', { query: 'x' },
    onlyPath('/api/v1/ks/answer', ANSWER_BARE))
  /* 引擎材料装配**失败**那一支：`material_usage.counts === null`。
     ⚠ 这一组的价值不在"值满足 schema"那一句（它当然要满足），而在于**它把那条路径钉进覆盖**：
     上一版正是缺这一组，才让"`counts` 写成必填 object"这个真机 isError 全绿地溜过去。 */
  const answerMatErr = await group('ks_answer', 'material-usage-engine-error',
    { query: 'x', params: { material_project_id: 'prj_x' } },
    onlyPath('/api/v1/ks/answer', ANSWER_MATERIAL_ERROR))
  check('ks_answer [material-usage-engine-error] — 引擎失败分支（counts:null + error）能原样通过自己的 schema',
    answerMatErr?.material_usage?.counts === null
      && typeof answerMatErr?.material_usage?.error === 'string',
    JSON.stringify(answerMatErr?.material_usage))
  /* ⚠ 2026-09-20（复核 `verify-freeze-step6-1b` 的 D②）：`material_usage` 是引擎自有的结构、我们只是直通
     ⇒ 外层声明成**开放的 object**（不写 `additionalProperties:false`）。这一组把那个决定钉住：
     引擎将来**加一个我们不知道的键**时，这次调用**不许**变 isError（否则又是一次"本批新引入的真机故障"）。
     反向变异：把外层改回 `additionalProperties:false` ⇒ 这一组必须红。 */
  const answerMatExtra = await group('ks_answer', 'material-usage-engine-extra-key',
    { query: 'x', params: { material_project_id: 'prj_x' } },
    onlyPath('/api/v1/ks/answer', {
      ...ANSWER_MATERIAL_ERROR,
      data: {
        ...ANSWER_MATERIAL_ERROR.data,
        material_usage: {
          ...ANSWER_MATERIAL_ERROR.data.material_usage,
          counts: { total: 1, approved: 1, pending: 0, rejected: 0 },
          // 引擎**将来**可能加的第 6 个键（这里故意用一个我们今天不知道的名字）
          future_engine_field: '引擎演化时新增的字段',
        },
      },
    }))
  check('ks_answer [material-usage-engine-extra-key] — 引擎在 material_usage 里加未知键时**不许** isError（外层是开放 object）',
    answerMatExtra?.material_usage?.future_engine_field === '引擎演化时新增的字段'
      && answerMatExtra?.material_usage?.counts?.total === 1,
    JSON.stringify(answerMatExtra?.material_usage))

  /* ══════════ 第 6 步（2026-09-21）：**知识库目录范围**（`kb_folder_ids` / `kb_doc_ids`）══════════
   * 父代理裁定：这是业主那句「每一级都能在此范围内提问」在**聊天**那条路上的落点 ——
   * 引擎入口与 HTTP 端点支持了、知识库页直连引擎能用，但**模型给不出范围**，功能对业主等于没上。
   *
   * 判据分四层（少一层就有一条静默失效的通道）：
   *   ① 参数进得了白名单（`sanitizeParams`）⇒ **请求体里真的看得见**；
   *   ② **空数组也照样发**（引擎把"显式空范围"与"没给范围"严格区分：前者一次检索都不做、
   *      后者是全库 —— 宿主若把空数组"优化"掉，就是"范围内提问悄悄变成全库"，正是红线）；
   *   ③ 引擎回显的 `scope` 必须出现在**工具返回值**里（否则模型说不出"这次在什么范围里检索的"）；
   *   ④ 没给范围时必须是 `null`（"没限定"与"限定了但范围内没有"要能区分）。
   * ⚠ 反向变异（本批实测过）：把请求体里的 kb_folder_ids 删掉 ⇒ ①红；把返回值里的 scope 删掉 ⇒ ③红。 */
  const answerBodies = []
  const captureAnswer = (body) => (path, init) => {
    if (path.includes('/api/v1/ks/answer')) {
      try { answerBodies.push(JSON.parse(init?.body ?? '{}')) } catch { answerBodies.push(null) }
      return { body }
    }
    return benign(path)
  }
  const scoped = await group('ks_answer', 'kb-scope-forwarded',
    { query: '动火作业怎么分级',
      params: { kb_folder_ids: ['kbf_a', 'kbf_a_child'], kb_doc_ids: ['doc_in1'] } },
    captureAnswer(ANSWER_KB_SCOPE))
  const sent = answerBodies[answerBodies.length - 1] ?? {}
  check('ks_answer [kb-scope-forwarded] — 目录范围**真的到引擎**（请求体 params.kb_folder_ids 逐字）',
    JSON.stringify(sent?.params?.kb_folder_ids) === JSON.stringify(['kbf_a', 'kbf_a_child']),
    JSON.stringify(sent?.params ?? null))
  check('ks_answer [kb-scope-forwarded] — 显式文件范围也到了（请求体 params.kb_doc_ids）',
    JSON.stringify(sent?.params?.kb_doc_ids) === JSON.stringify(['doc_in1']),
    JSON.stringify(sent?.params ?? null))
  check('ks_answer [kb-scope-forwarded] — 引擎回显的 scope 出现在**工具返回值**里（模型能说出范围）',
    scoped?.scope?.doc_count === 7 && scoped?.scope?.folder_count === 2
    && scoped?.scope?.empty === false && Array.isArray(scoped?.scope?.folder_ids),
    JSON.stringify(scoped?.scope ?? null))
  await group('ks_answer', 'kb-scope-empty-array-forwarded',
    { query: 'x', params: { kb_folder_ids: [] } }, captureAnswer(ANSWER_BARE))
  const sentEmpty = answerBodies[answerBodies.length - 1] ?? {}
  check('ks_answer [kb-scope-empty-array-forwarded] — **空数组也发给引擎**'
    + '（被宿主吃掉就成"没给范围"= 全库检索，正是红线）',
    Array.isArray(sentEmpty?.params?.kb_folder_ids) && sentEmpty.params.kb_folder_ids.length === 0,
    JSON.stringify(sentEmpty?.params ?? null))
  await group('ks_answer', 'kb-scope-hygiene',
    { query: 'x', params: { kb_folder_ids: ['kbf_ok', '   ', 'x'.repeat(80), 42, 'kbf_ok'] } },
    captureAnswer(ANSWER_BARE))
  const sentDirty = answerBodies[answerBodies.length - 1] ?? {}
  check('ks_answer [kb-scope-hygiene] — 空白/超长/非字符串被丢掉、重复去掉、合法项留下',
    JSON.stringify(sentDirty?.params?.kb_folder_ids) === JSON.stringify(['kbf_ok']),
    JSON.stringify(sentDirty?.params ?? null))
  check('ks_answer [full-answer] — 引擎没给 scope 时工具给 **null**（不是编一个"全库"）',
    answerFull?.scope === null, JSON.stringify(answerFull?.scope ?? null))
  /* ⚠⚠ **2026-09-21（复核 LOW-1/LOW-2/LOW-4/LOW-5 打回后补的几条）**：输入侧的"静默放宽/静默截断"
     与输出侧的"形状比 schema 多一个键"，都是**同一个失败模式**（看着没事、其实换了个问题）。
       ① 字符串形态 ⇒ 按**引擎口径**规范化成单项数组（引擎 `_as_list` 就接受字符串；宿主不许更严、
          更不许整键丢掉 —— 那会让"以为限定了范围"变成全库检索）；
       ② 非数组（数字/对象）⇒ **显式报错**（不许静默丢键）；
       ③ 超上限 ⇒ **显式报错**（复核实测 600 个 id 被悄悄砍到 500；"截断后的范围"答的是另一个问题）；
       ④ 运行时 `scope` 多一个 `roots`（给目录范围时）⇒ 它必须在 **schema 的 properties** 里。 */
  await group('ks_answer', 'kb-scope-string-normalized',
    { query: 'x', params: { kb_folder_ids: 'kbf_single' } }, captureAnswer(ANSWER_BARE))
  const sentStr = answerBodies[answerBodies.length - 1] ?? {}
  check('ks_answer [kb-scope-string-normalized] — 字符串形态按引擎口径**规范化成单项数组**'
    + '（不许整键丢掉 = 悄悄变成全库）',
    JSON.stringify(sentStr?.params?.kb_folder_ids) === JSON.stringify(['kbf_single']),
    JSON.stringify(sentStr?.params ?? null))
  /** "必须抛错"的小助手（静默路径的反面：宁可让调用方看见错，也不要换个问题答）。 */
  const expectThrow = async (label, args, want) => {
    const tool = tools.get('ks_answer')
    try {
      await tool.execute(args, execFor('smoke-contract'))
      check(`ks_answer [${label}] — 必须**显式报错**（不许静默丢弃/截断）`, false,
        'execute() 居然成功返回了')
    } catch (error) {
      const msg = String(error?.message ?? error)
      check(`ks_answer [${label}] — 必须**显式报错**（不许静默丢弃/截断）`, msg.includes(want),
        msg.slice(0, 200))
    }
  }
  await expectThrow('kb-scope-non-array-rejected',
    { query: 'x', params: { kb_folder_ids: 42 } }, 'must be an array of strings')
  await expectThrow('kb-scope-over-limit-rejected',
    { query: 'x', params: { kb_folder_ids: Array.from({ length: 201 }, (_, i) => `kbf_${String(i)}`) } },
    'over the limit')
  /* ⚠⚠ **2026-09-22（复核：`kb_doc_ids` 的 2000 没有依据）** —— 上限改成 **20000**，并把依据
     写进注释（引擎对文档 id 本身**没有**上限；20000 ≈ 今天真库 6417 篇的 3 倍，只是**载荷兜底**）。
     ⚠ 下面这两个数**从源码里读出来**（`KB_SCOPE_LIMITS`），**不写死**：
       ① 闸门那一条用 `docLimit + 1` ⇒ 证明"闸就在这个数上"（多了就显式报错、不静默截断）；
       ② 描述那一条要求**参数描述里的 `Limit: N ids` 与源码同一个 N** ⇒
          "代码改了、描述没改"（或反过来）当场红 —— 模型正是照着描述判断会不会被拒。
     ⚠ 为什么必须从源码读：第一版我把 20000 写死在断言里，**变异（描述改成 3000）照样全绿**，
     因为描述里另一句 "20000 is ~3x today's library" 也含这个子串 ⇒ 那种判据看着有牙、其实恒真。 */
  const pluginSrc = await readFile(
    join(dirname(fileURLToPath(import.meta.url)), '..', 'src', 'index.js'), 'utf8')
  const limitsMatch = /KB_SCOPE_LIMITS = \{ kb_folder_ids: (\d+), kb_doc_ids: (\d+) \}/.exec(pluginSrc)
  const folderLimit = limitsMatch ? Number(limitsMatch[1]) : NaN
  const docLimit = limitsMatch ? Number(limitsMatch[2]) : NaN
  check('ks_answer [上限] — 从源码里读到了两个上限（读不到就不算验过）',
    Number.isInteger(folderLimit) && Number.isInteger(docLimit),
    `KB_SCOPE_LIMITS = folder ${String(folderLimit)} / doc ${String(docLimit)}`)
  const docIdsOverLimit = Array.from({ length: docLimit + 1 }, (_, i) => `doc_${String(i)}`)
  await expectThrow('kb-scope-doc-over-limit-rejected',
    { query: 'x', params: { kb_doc_ids: docIdsOverLimit } }, `limit of ${String(docLimit)}`)
  const ksAnswerTool = tools.get('ks_answer')
  /* ⚠ 注册进来的就是**定义对象本体**（`parameters` 在顶层，不是 `input.schema`）—— 写错路径的
     后果是 `{}` ⇒ 两条断言直接红（这一次就是这么发现的，见上面的 raw 输出）。 */
  const scopeParamProps = ksAnswerTool?.parameters?.properties?.params?.properties ?? {}
  const folderDesc = String(scopeParamProps?.kb_folder_ids?.description ?? '')
  const docDesc = String(scopeParamProps?.kb_doc_ids?.description ?? '')
  check('ks_answer [params 描述] — 参数描述里的 `Limit: N ids` 与源码的 `KB_SCOPE_LIMITS` '
    + '**同一个数**（`kb_folder_ids` = 引擎自己的根数上限；`kb_doc_ids` = 载荷兜底，依据在源码注释里）',
    folderDesc.includes(`Limit: ${String(folderLimit)} ids`)
    && docDesc.includes(`Limit: ${String(docLimit)} ids`),
    `源码 folder=${String(folderLimit)} / doc=${String(docLimit)}；`
      + `描述里有 "Limit: ${String(folderLimit)} ids"=${String(folderDesc.includes(`Limit: ${String(folderLimit)} ids`))}、`
      + `"Limit: ${String(docLimit)} ids"=${String(docDesc.includes(`Limit: ${String(docLimit)} ids`))}`)
  check('ks_answer [params 描述] — `null`（没给范围 ⇒ 全库）与 `[]`（⇒ 422、一次检索都不做）'
    + '的**语义差异**写在模型看得见的地方（参数描述 + 工具描述），别让它靠猜',
    folderDesc.includes('422') && folderDesc.includes('OMITTED')
    && docDesc.includes('422') && docDesc.includes('OMITTED')
    && String(ksAnswerTool?.description ?? '').includes('EMPTY array'),
    `folder: 422=${String(folderDesc.includes('422'))} OMITTED=${String(folderDesc.includes('OMITTED'))} / `
      + `doc: 422=${String(docDesc.includes('422'))} OMITTED=${String(docDesc.includes('OMITTED'))} / `
      + `tool desc 有 EMPTY array=${String(String(ksAnswerTool?.description ?? '').includes('EMPTY array'))}`)
  const scopeSchemaProps = tools.get('ks_answer').output.schema.properties.scope.oneOf[0].properties
  check('ks_answer [schema] — 运行时 `scope` 的每个键都在 schema 里（含只给目录范围时多出来的 roots）',
    ['kind', 'folder_ids', 'folder_count', 'doc_count', 'empty', 'roots']
      .every((k) => k in scopeSchemaProps),
    Object.keys(scopeSchemaProps).join(','))

  /* -------------------------------- ks_materials -------------------------------- */
  const projects = await group('ks_materials', 'projects', {},
    exactPath('/api/v1/materials/projects', {
      code: 200,
      status: 'success',
      data: [
        { project_id: 'prj_a', name: '财报分析', authority_policy: { criterion: ['公司制度'] } },
        { project_id: 'prj_b', name: '宿舍改造', authority_policy: null },
      ],
    }))
  check('ks_materials [projects] — 项目行真的透出来了（不是空壳）',
    projects?.count === 2 && projects?.projects?.[0]?.project_id === 'prj_a',
    JSON.stringify(projects?.count))
  const materialsPending = await group('ks_materials', 'materials-pending',
    { action: 'materials', project_id: 'prj_a' },
    // ⚠ 片段必须是**完整**的 `/projects/prj_a/materials`：写成 `/materials/prj_a/materials`
    // 就永远匹配不上，于是回落 `benign`（data:{}）——那是本文件第一版的**假绿**（数组断言
    // 会红，object 断言会静默过）。这条注释就是那次实测的留痕。
    onlyPath('/projects/prj_a/materials', {
      code: 200, status: 'success', data: MATERIAL_ROWS,
    }))
  check('ks_materials [materials-pending] — 走到 pending>0 分支（note 是字符串）',
    materialsPending?.count === 1 && materialsPending?.review_counts?.pending === 1
      && typeof materialsPending?.note === 'string',
    `count=${materialsPending?.count} pending=${materialsPending?.review_counts?.pending} note=${typeof materialsPending?.note}`)
  /* ⚠⚠ 2026-09-20（顺带抓到的那条真缺陷的**回归位**）：`pending === 0` 时原来返回
     `note: undefined` —— 宿主做 lossless 快照时会把 undefined 判成"不是无损失的 JSON"⇒
     `INVALID_TOOL_OUTPUT` ⇒ **真机上这一次调用整体 isError**。既有夹具恰好 `pending=1`，
     所以这条路径一直没被量到（"夹具比真相宽松 ⇒ 永远量不到"）。这里补一组 pending=0：
     ① `checkToolContract` 的 `findUndefined` 必须**没有**命中（给了 undefined 就红）；
     ② 反过来钉住"省略键"这个修法：`note` 不在返回值里（`'note' in value === false`，
        不是 `undefined`）—— 只判 `typeof note === 'undefined'` 会把"显式 undefined"也放过。 */
  const materialsApprovedOnly = await group('ks_materials', 'materials-approved-only',
    { action: 'materials', project_id: 'prj_a' },
    onlyPath('/projects/prj_a/materials', {
      code: 200,
      status: 'success',
      data: [{
        material_id: 'mat_ok', title: '已批准的制度', review_status: 'approved',
        chunk_count: 3, origin: 'uploaded', kind: 'policy', source_tier: 'T1',
      }],
    }))
  check('ks_materials [materials-approved-only] — pending=0 时**没有** note 键（不给 undefined ⇒ 不触发 INVALID_TOOL_OUTPUT）',
    materialsApprovedOnly?.review_counts?.pending === 0
      && !Object.prototype.hasOwnProperty.call(materialsApprovedOnly ?? {}, 'note')
      && !Object.values(materialsApprovedOnly ?? {}).some((v) => v === undefined),
    `pending=${materialsApprovedOnly?.review_counts?.pending} `
      + `hasOwn(note)=${Object.prototype.hasOwnProperty.call(materialsApprovedOnly ?? {}, 'note')} `
      + `undefined 值个数=${Object.values(materialsApprovedOnly ?? {}).filter((v) => v === undefined).length}`)
  const inbox = await group('ks_materials', 'inbox', { action: 'inbox', project_id: 'prj_a' },
    onlyPath('/projects/prj_a/inbox', {
      code: 200,
      status: 'success',
      data: { dir: 'C:/tmp/prj_a', files: [{ path: 'C:/tmp/prj_a/a.pdf', file_name: 'a.pdf', size: 1024 }] },
    }))
  check('ks_materials [inbox] — 文件行真的透出来了（不是空壳）',
    inbox?.count === 1 && inbox?.files?.[0]?.file_name === 'a.pdf' && inbox?.dir === 'C:/tmp/prj_a',
    JSON.stringify({ count: inbox?.count, dir: inbox?.dir }))

  /* --------------------------------- ks_collect --------------------------------- */
  const collected = await group('ks_collect', 'collected',
    { url: 'https://example.com/b', project_id: 'prj_a' },
    onlyPath('/collect', {
      code: 200,
      status: 'success',
      data: { collected: true, status: 200, truncated: false, duplicate: false, material: COLLECTED_MATERIAL },
    }))
  check('ks_collect [collected] — 材料条目真的透出来了（不是空壳）',
    collected?.collected === true && collected?.material?.material_id === 'mat_9',
    JSON.stringify(collected?.material?.material_id))
  await group('ks_collect', 'refused', { url: 'http://127.0.0.1/x', project_id: 'prj_a' },
    onlyPath('/collect', {
      code: 200,
      status: 'success',
      data: { collected: false, reason: 'URL 被 SSRF 纪律拒绝（仅 http/https 且禁内网/保留地址）' },
    }))

  /* ------------------------- A4/A5 反向对照（最重要的一段） -------------------------
   * 把**同一批真实返回值**拿去喂两份**故意错**的 schema：必须出现违规。
   * 没有这一段，上面所有"值满足 schema"都可能是空转的假绿。
   * --------------------------------------------------------------------------- */
  const primary = new Map([
    ['ks_effect_report', effectFull],
    ['ks_ping', pingFull],
    ['ks_resolve_clause', resolveOutside],
    ['ks_answer', answerFull],
    ['ks_materials', materialsPending],
    ['ks_collect', collected],
  ])
  const EMPTY_OBJECT_SCHEMA = { type: 'object', additionalProperties: false, properties: {}, required: [] }
  for (const [name, value] of primary) {
    if (value === null) {
      check(`A4 ${name} — 非空转（空 properties 必须判违规）`, false, '该工具没有可用的值（上一组已红）')
      continue
    }
    const violations = violationsOf(EMPTY_OBJECT_SCHEMA, value)
    check(`A4 ${name} returned a value its own schema rejects（非空转）`,
      violations.length > 0,
      violations.slice(0, 1).join('; ') || '(零违规 ⇒ 校验器空转)')
  }
  for (const [name, value] of primary) {
    if (value === null) continue
    check(`A5 ${name} — 根类型写错必须红`,
      violationsOf({ type: 'array' }, value).length > 0, '')
  }

  responder = benign

  const failed = results.filter((r) => !r.ok)
  console.log(`\n== tool contract smoke ${failed.length === 0 ? 'PASS' : 'FAIL'} `
    + `(${results.length - failed.length}/${results.length}; ${groupCount} 组场景) ==`)
  process.exit(failed.length === 0 ? 0 : 1)
}

main().catch((err) => {
  console.error(`[fatal] ${err && err.stack ? err.stack : err}`)
  process.exit(1)
})
