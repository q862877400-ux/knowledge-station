/**
 * ks-dsh-plugin — scripts/smoke-effect-tool.mjs
 *
 * Host-side END-TO-END smoke for the MODEL TOOLS — `ks_effect_report`
 * (verifier F3/F4/F5/F6/F14/F16/F18 + P1-2/P2-5) and `ks_resolve_clause`'s
 * not-found path (P1-4) — run against the REAL engine, without a dsh restart.
 *
 * How: `apply()` is called with a minimal fake cordis ctx (tools.register /
 * webServer.register / effect), so the tools the plugin would publish are
 * captured here and invoked directly. The engine is reached through the same
 * EngineManager the plugin uses (session-file reuse / spawn).
 *
 * Two passes:
 *   1. LIVE   — real engine, real endpoints (proves the wiring works).
 *   2. STUBBED — a synthetic envelope + synthetic red/yellow rows, so the
 *      mapping assertions (F4 request shape, F18 evidence_url, tree cap) are
 *      NON-VACUOUS even when the library happens to hold no red/yellow docs
 *      (verifier P2-5: rows=0 made the old assertions always true).
 *
 * Run:  node scripts/smoke-effect-tool.mjs     (exit 0 = all checks pass)
 */

import { mkdtemp } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

// 隔离落盘：本脚本会 setMode()（查法规模式的用具例）。verifier 四轮 P2-H4：不隔离就会把
// 用例会话写进用户的 %APPDATA%\KnowledgeStation\ks-chatmode.json。
// 注意用 **KS_CHATMODE_DIR**（只挪开关状态文件）而**不是** KS_DATA_DIR —— 后者同时决定
// 引擎自己的数据目录/库，会把下面的 live 通道打到刚 spawn 的空库上（实测会 500）。
process.env.KS_CHATMODE_DIR = await mkdtemp(join(tmpdir(), 'ks-effect-tool-smoke-'))

const { apply, evidenceAnchor } = await import('../src/index.js')
const { __resetChatModeForTests, setMode } = await import('../src/chatmode.js')

// 查法规模式的子会话继承走 `agents.get(sessionId).session.header.parentSession`；
// 这里给一个可控的假注册表（默认空 = 不继承）。
//
// ⚠ 2026-09-19：`agents` / `commands` **已从 `inject` 里移出**（它们是"可缺省"的服务），
// 所以插件改走官方指定的读法 **`ctx.get(name)`**（官方 `docs/postmortem/0001-…md`：
// "For a service a plugin reads opportunistically but does NOT declare in `static inject`,
// use `ctx.get(name)`, never `ctx.<name>`"）。⇒ 这个假 ctx **必须实现 `get()`**，
// 否则桩与真契约不一致，会造出一条**假红**（`ctx.get` 返回 undefined ⇒ 子会话不继承）。
const fakeSessions = new Map()
const registeredCommands = []
const tools = new Map()
/** 假服务表：既供 `ctx.<name>`（硬依赖，如 webServer）也供 `ctx.get('<name>')`（可缺省）。 */
const _services = {
  tools: { register(tool) { tools.set(tool.name, tool) } },
  webServer: { register() { return () => {} } },
  // apply() 现在无条件注册提示段（verifier 二轮：本脚本原先缺这一项直接 fatal）
  systemPrompt: { section() { return () => {} } },
  agents: { get(sessionId) { return fakeSessions.get(sessionId) } },
  // 斜杠命令（2026-10：dock 改成 /forensic、/bookmarks）也要能注册；这里捕获名字，
  // 顺带断言两条命令真的挂上去了。
  commands: { register(def) { registeredCommands.push(def); return () => {} } },
}
const ctx = {
  ..._services,
  /** cordis 的服务查找：**只返回已提供的服务**（这里用同一张表模拟）。 */
  get(name) { return _services[name] },
  effect(fn) { return fn() },
}

const results = []
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}

/** Deep scan for `undefined` (DSH tool output is validated losslessly). */
function findUndefined(value, path = '$') {
  if (value === undefined) return path
  if (Array.isArray(value)) {
    for (let i = 0; i < value.length; i += 1) {
      const hit = findUndefined(value[i], `${path}[${i}]`)
      if (hit) return hit
    }
    return null
  }
  if (value && typeof value === 'object') {
    for (const [k, v] of Object.entries(value)) {
      const hit = findUndefined(v, `${path}.${k}`)
      if (hit) return hit
    }
  }
  return null
}

/** 合成一份 E1 信封 + 红/黄清单响应（用于不可空转的映射断言）。 */
const SYNTH_SUMMARY = {
  code: 200,
  status: 'success',
  data: {
    generated_at: '2026-09-08 12:00:00',
    window: 'all',
    colors: { red: 2, yellow: 1, green: 7, gray: 3 },
    total: 13,
    std: { total: 10, colors: { red: 2, yellow: 1, green: 6, gray: 1 } },
    law: { total: 3, colors: { red: 0, yellow: 0, green: 1, gray: 2 } },
    tree: [
      {
        top: 'std',
        name: '国家标准·行业标准·团体标准',
        colors: { red: 2, yellow: 1, green: 6, gray: 1 },
        items: [
          { name: 'C 医药、卫生、劳动保护', colors: { red: 1, yellow: 1, green: 2, gray: 0 } },
          { name: 'F 能源、核技术', colors: { red: 1, yellow: 0, green: 1, gray: 0 } },
          { name: 'J 机械', colors: { red: 0, yellow: 0, green: 1, gray: 0 } },
          { name: 'K 电工', colors: { red: 0, yellow: 0, green: 1, gray: 0 } },
          { name: 'Q 建材', colors: { red: 0, yellow: 0, green: 1, gray: 1 } },
        ],
      },
      { top: 'law', name: '法律法规', colors: { red: 0, yellow: 0, green: 1, gray: 2 }, items: [] },
    ],
  },
}
const SYNTH_DOCS = [
  { status: 'superseded', color: 'red', doc_id: 'doc_r1', standard_no: 'GB 1111-2011',
    standard_name: '红一号', effective_from: '2011-01-01', published_at: null,
    superseded_by: 'GB 1111-2021', withdrawn_date: null },
  { status: 'withdrawn', color: 'red', doc_id: 'doc_r2', standard_no: 'GB 2222-2012',
    standard_name: '红二号', effective_from: '2012-01-01', published_at: null,
    superseded_by: null, withdrawn_date: '2026-01-04' },
  { status: 'upcoming', color: 'yellow', doc_id: 'doc_y1', standard_no: 'GB 3333-2026',
    standard_name: '黄一号', effective_from: '2099-01-01', published_at: null,
    superseded_by: null, withdrawn_date: null },
]

async function main() {
  console.log('=== ks_effect_report model-tool smoke ===')
  apply(ctx, {})
  const tool = tools.get('ks_effect_report')
  check('tool registered', typeof tool?.execute === 'function')
  check('slash commands registered on the host command table',
    // 期望集合**跟着声明走**（别写死两份名字）：加命令时这里不该变红
    registeredCommands.map((d) => d.name).join(',')
      === ['forensic', 'bookmarks', 'materials'].join(','),
    registeredCommands.map((d) => '/' + d.name).join(',') || '(none)')
  check('outer timeout covers spawn + inner calls', tool.timeoutMs === 90_000,
    `timeoutMs=${tool.timeoutMs}`)
  // 工具**注册面**：这条防的是"模块写好了但忘了在 apply() 里注册"——
  // `smoke-collect-tool.mjs` 是直接 import 模块的，**抓不到**那种漏（改了自己跑不起来）。
  // 所以这里按**名字**点名断言（加工具时要显式改这一行，是刻意的摩擦）。
  check('model tools registered: ping/resolve/answer/effect_report/materials/collect',
    ['ks_ping', 'ks_resolve_clause', 'ks_answer', 'ks_effect_report',
      'ks_materials', 'ks_collect'].every((n) => tools.has(n)),
    [...tools.keys()].join(','))
  check('写权限只给了 ks_collect 一个（读/写工具分开，名字即权限）',
    typeof tools.get('ks_collect')?.execute === 'function'
    && tools.get('ks_materials')?.description.includes('只读'),
    [...tools.keys()].join(','))

  // ---------------------------------------------- 命令注册的爆炸半径护栏（2026-09-11）
  // host 侧 ctx.commands.register 会走 normalizeDefinition 校验并**抛 TypError**。
  // 裸调用的话异常会冒出 apply()，把整个宿主半边（全部 /ks/* 路由、提示段、模型工具）
  // 一起带走；这里实测两种情况都只降级、不连坐。
  {
    const captured = []
    const realError = console.error
    const errors = []
    console.error = (...args) => { errors.push(args.map(String).join(' ')) }
    try {
      // (a) 单条命令校验失败：另一条仍要注册，模型工具仍要挂上
      const seenTools = []
      const partial = []
      const hostileA = {
        tools: { register(t) { seenTools.push(t.name) } },
        webServer: { register() { return () => {} } },
        systemPrompt: { section() { return () => {} } },
        agents: { get() { return undefined } },
        // ⚠ 可缺省服务要走 ctx.get()（见文件顶部说明）：桩必须实现它，否则是假红。
        get(name) { return name === 'agents' ? this.agents : undefined },
        commands: { register(def) {
          if (def.name === 'forensic') throw new TypeError('command name "forensic" must match /^[a-z][a-z0-9_-]*$/u')
          partial.push(def.name)
          return () => {}
        } },
        effect(fn) { return fn() },
      }
      let threwA = null
      try { apply(hostileA, {}) } catch (error) { threwA = error }
      check('a failing command definition cannot abort apply()', threwA === null, String(threwA))
      check('the other commands still register (per-command fallback)',
        partial.join(',') === 'bookmarks,materials', partial.join(',') || '(none)')
      check('model tools still register despite the command failure',
        seenTools.includes('ks_effect_report') && seenTools.length >= 3, seenTools.join(','))
      check('the skipped command is reported loudly', errors.length >= 1, `${errors.length} console.error`)

      // (b) 命令服务本身不可用/不兼容：同样只降级
      const seenToolsB = []
      const realErrorB = errors.length
      const hostileB = {
        tools: { register(t) { seenToolsB.push(t.name) } },
        webServer: { register() { return () => {} } },
        systemPrompt: { section() { return () => {} } },
        agents: { get() { return undefined } },
        // ⚠ 可缺省服务要走 ctx.get()（见文件顶部说明）：桩必须实现它，否则是假红。
        get(name) { return name === 'agents' ? this.agents : undefined },
        commands: undefined,
        effect(fn) { return fn() },
      }
      let threwB = null
      try { apply(hostileB, {}) } catch (error) { threwB = error }
      check('an unavailable commands service cannot abort apply()', threwB === null, String(threwB))
      check('tools still register when commands is unavailable',
        seenToolsB.includes('ks_effect_report') && seenToolsB.length >= 3, seenToolsB.join(','))
      // 早返回必须是**可观测的**：报告一次「服务不可用」，而不是退化成两条「单条注册失败」。
      // （去掉早返回时这里会变成 2 条且措辞不同 —— 变异测试据此能抓住。）
      const deltaB = errors.slice(realErrorB)
      check('the unavailable service is reported loudly', deltaB.length > 0, `${deltaB.length} new console.error`)
      check('the unavailable service short-circuits to ONE clear report',
        deltaB.length === 1 && deltaB[0].includes('命令服务不可用'),
        `${deltaB.length} 条 / 末条=${JSON.stringify(deltaB.at(-1)?.slice(0, 60))}`)
    } finally {
      console.error = realError
      captured.length = 0
    }
  }

  // ---------------------------------------------------------------- LIVE pass
  const value = await tool.execute({ limit: 3 }, {})
  console.log(`\n-- live value --\n${JSON.stringify(value, null, 2)}\n`)

  check('LIVE ok=true', value.ok === true)
  check('LIVE four-colour block', ['red', 'yellow', 'green', 'gray']
    .every((c) => typeof value.colors?.[c] === 'number'))
  check('F16 constant window omitted', !('window' in value))
  check('no undefined anywhere', findUndefined(value) === null, findUndefined(value) ?? '')
  const hasLists = Array.isArray(value.red_list?.docs) && Array.isArray(value.yellow_list?.docs)
  const hasError = typeof value.attention_error === 'string' && value.attention_error.length > 0
  check('F6 attention: lists XOR explicit error', hasLists !== hasError,
    hasError ? `attention_error=${value.attention_error}` : 'lists present')
  check('LIVE trees capped at 3 categories',
    Array.isArray(value.trees) && value.trees.every((t) => (t.categories ?? []).length <= 3))

  // ------------------------------------------------------------ STUBBED pass
  // Only the report endpoints are faked; health passes through so ensureLive()
  // keeps reusing the real engine (no spawn).
  const realFetch = globalThis.fetch
  const capturedUrls = []
  const fakeReport = (summaryBody, docsBody) => async (url, init) => {
    const u = String(url)
    if (u.includes('/api/v1/report/effect/color')) {
      capturedUrls.push(u)
      return { status: 200, ok: true, text: async () => JSON.stringify(docsBody) }
    }
    if (u.includes('/api/v1/report/effect')) {
      capturedUrls.push(u)
      return { status: 200, ok: true, text: async () => JSON.stringify(summaryBody) }
    }
    return realFetch(url, init)
  }

  globalThis.fetch = fakeReport(SYNTH_SUMMARY, {
    code: 200, status: 'success',
    data: { colors: { red: 2, yellow: 1, green: 0, gray: 0 }, count: 3, per_color: true, docs: SYNTH_DOCS },
  })
  const synth = await tool.execute({ limit: 2 }, {})
  globalThis.fetch = realFetch

  console.log(`\n-- stubbed value --\n${JSON.stringify(synth, null, 2)}\n`)
  const colorUrl = capturedUrls.find((u) => u.includes('/effect/color')) ?? ''
  check('F4 one aggregated call, per-colour, limit passed',
    capturedUrls.filter((u) => u.includes('/effect/color')).length === 1
    && /color=red%2Cyellow|color=red,yellow/.test(colorUrl)
    && colorUrl.includes('per_color=1') && colorUrl.includes('limit=2'), colorUrl)
  check('F4 red/yellow buckets split by colour',
    synth.red_list?.docs?.length === 2 && synth.yellow_list?.docs?.length === 1
    && synth.red_list.docs.every((d) => d.status !== 'upcoming')
    && synth.yellow_list.docs[0]?.status === 'upcoming',
    `red=${synth.red_list?.docs?.length} yellow=${synth.yellow_list?.docs?.length}`)
  check('F4 counts come from the library-wide histogram',
    synth.red_list?.count === 2 && synth.yellow_list?.count === 1,
    `red=${synth.red_list?.count} yellow=${synth.yellow_list?.count}`)
  check('F18 row carries doc_id + exact evidence_url',
    synth.red_list?.docs?.[0]?.doc_id === 'doc_r1'
    && synth.red_list?.docs?.[0]?.evidence_url
      === 'http://127.0.0.1:1/__ks_evidence__?doc=doc_r1',
    String(synth.red_list?.docs?.[0]?.evidence_url))
  check('F16 tree cap is real (5 → 3)',
    synth.trees?.[0]?.categories?.length === 3
    && synth.trees[0].categories.map((c) => c.name)
      .join('|') === 'C 医药、卫生、劳动保护|F 能源、核技术|J 机械')
  check('STUBBED no undefined anywhere', findUndefined(synth) === null)

  // ---- negative paths
  globalThis.fetch = fakeReport({ hello: 'world' }, { code: 200, data: { docs: [] } })
  let f5Error = null
  try { await tool.execute({ include_attention: false }, {}) } catch (e) { f5Error = e }
  globalThis.fetch = realFetch
  check('F5 non-envelope 200 → throws', f5Error !== null
    && /响应异常/.test(String(f5Error?.message)), String(f5Error?.message ?? '').slice(0, 60))

  // F6: 清单调用失败（500）→ 统计仍返回 + 显式 attention_error
  globalThis.fetch = async (url, init) => {
    const u = String(url)
    if (u.includes('/api/v1/report/effect/color')) {
      return { status: 500, ok: false, text: async () => JSON.stringify({ code: 500, message: 'boom' }) }
    }
    if (u.includes('/api/v1/report/effect')) {
      return { status: 200, ok: true, text: async () => JSON.stringify(SYNTH_SUMMARY) }
    }
    return realFetch(url, init)
  }
  const degraded = await tool.execute({ limit: 2 }, {})
  globalThis.fetch = realFetch
  check('F6 list failure degrades loudly', degraded.ok === true
    && typeof degraded.attention_error === 'string'
    && degraded.attention_error.includes('500')
    && !('red_list' in degraded), String(degraded.attention_error))

  // F14: 401 → loud, actionable error
  globalThis.fetch = async (url, init) => {
    const u = String(url)
    if (u.includes('/api/v1/report/')) {
      return { status: 401, ok: false, text: async () => JSON.stringify({ detail: 'unauthorized' }) }
    }
    return realFetch(url, init)
  }
  let f14Error = null
  try { await tool.execute({ include_attention: false }, {}) } catch (e) { f14Error = e }
  globalThis.fetch = realFetch
  check('F14 401 → loud error', f14Error !== null
    && /401/.test(String(f14Error?.message)), String(f14Error?.message ?? '').slice(0, 60))

  // include_attention=false → statistics only
  const statsOnly = await tool.execute({ include_attention: false }, {})
  check('include_attention=false drops lists',
    !('red_list' in statsOnly) && !('yellow_list' in statsOnly)
    && !('attention_error' in statsOnly))
  check('stats-only still has totals', typeof statsOnly.total === 'number')

  // F18 锚点契约（与 client/ksEvidence.ts 一致），不依赖库内有无红/黄文档
  check('F18 evidenceAnchor doc+page', evidenceAnchor({ doc_id: 'doc_x', page_start: 3 })
    === 'http://127.0.0.1:1/__ks_evidence__?doc=doc_x&page=3')
  check('F18 evidenceAnchor doc only', evidenceAnchor({ doc_id: 'doc_x' })
    === 'http://127.0.0.1:1/__ks_evidence__?doc=doc_x')
  check('F18 evidenceAnchor no doc → null', evidenceAnchor({}) === null)

  // ---- ks_resolve_clause 的「查无此条」路径（verifier P1-4）：引擎 404 体
  //      没有 data 键，若原样返回 undefined 会让整条工具输出被 DSH 判
  //      INVALID_TOOL_OUTPUT。这里打真实引擎查一个不存在的条款。
  const resolve = tools.get('ks_resolve_clause')
  const miss = await resolve.execute(
    { standard_no: 'GB 00000-9999', clause_number: '99.99.99' }, {})
  check('P1-4 resolve not-found has no undefined',
    findUndefined(miss) === null, findUndefined(miss) ?? '')
  check('P1-4 resolve not-found returns data:null', miss.data === null && miss.found === false,
    `found=${miss.found} data=${JSON.stringify(miss.data)}`)

  // ---- 查法规模式：工具层强制（verifier 二轮 P1 —— 提示词层与工具层必须同一真值，
  //      子会话继承也必须在**工具层**生效，否则会出现"提示词说已限收藏集、实际全库查"）
  const answer = tools.get('ks_answer')
  check('ks_answer registered', typeof answer?.execute === 'function')
  const SYNTH_ANSWER = {
    code: 200, status: 'success',
    data: {
      tier: 'direct',
      evidence: [{
        doc_id: 'doc_a1', page_start: 3, clause_revision_id: 'rev_a1',
        standard_no: 'GB 1111-2020', clause_number: '5.1.2',
        legal_status: 'effective', legal_hierarchy: '国家标准',
        content_text: '高处作业分级……',
      }],
      derivation: '按条款推导',
      conclusion: '结论',
      verification: { is_valid: true, confidence: 0.9 },
      notes: [],
    },
  }
  const captureAnswerCall = (sessions, exec) => {
    const realFetch2 = globalThis.fetch
    let sentBody = null
    globalThis.fetch = async (url, init) => {
      const u = String(url)
      if (u.includes('/api/v1/ks/answer')) {
        sentBody = init?.body ? JSON.parse(String(init.body)) : null
        return { status: 200, ok: true, text: async () => JSON.stringify(sessions) }
      }
      return realFetch2(url, init)
    }
    return answer.execute({ query: '高处作业怎么分级' }, exec).then((value) => {
      globalThis.fetch = realFetch2
      return { value, sentBody }
    }, (error) => {
      globalThis.fetch = realFetch2
      throw error
    })
  }
  const parentExec = { agent: { session: { id: 'smoke-parent', header: {} } } }
  const childExec = { agent: { session: { id: 'smoke-child', header: { parentSession: 'smoke-parent' } } } }
  fakeSessions.set('smoke-child', { session: { header: { parentSession: 'smoke-parent' } } })
  fakeSessions.set('smoke-parent', { session: { header: {} } })

  __resetChatModeForTests()
  setMode('smoke-parent', { forensic: true, bookmarksOnly: true })

  const offCall = await captureAnswerCall(SYNTH_ANSWER, { agent: { session: { id: 'smoke-off', header: {} } } })
  check('bookmarks off → params carries no bookmarks_only',
    offCall.sentBody?.params?.bookmarks_only === undefined
    && offCall.value.answer_scope?.bookmarks_only === false,
    JSON.stringify(offCall.value.answer_scope))
  check('answer payload has no undefined', findUndefined(offCall.value) === null,
    findUndefined(offCall.value) ?? '')

  const onCall = await captureAnswerCall(SYNTH_ANSWER, parentExec)
  check('bookmarks on → host FORCES params.bookmarks_only=true',
    onCall.sentBody?.params?.bookmarks_only === true, JSON.stringify(onCall.sentBody?.params))
  check('answer_scope echoes the enforced scope + source',
    onCall.value.answer_scope?.bookmarks_only === true
    && onCall.value.answer_scope?.forensic === true
    && onCall.value.answer_scope?.source === 'session', JSON.stringify(onCall.value.answer_scope))

  const childCall = await captureAnswerCall(SYNTH_ANSWER, childExec)
  check('a CHILD session inherits and is enforced too (prompt/tool parity)',
    childCall.sentBody?.params?.bookmarks_only === true
    && childCall.value.answer_scope?.source === 'parent',
    JSON.stringify(childCall.value.answer_scope))

  // 模型显式传 bookmarks_only:false 也改不了（host 强制覆盖在校验后的参数之上）
  {
    const realFetch3 = globalThis.fetch
    let body = null
    globalThis.fetch = async (url, init) => {
      const u = String(url)
      if (u.includes('/api/v1/ks/answer')) {
        body = init?.body ? JSON.parse(String(init.body)) : null
        return { status: 200, ok: true, text: async () => JSON.stringify(SYNTH_ANSWER) }
      }
      return realFetch3(url, init)
    }
    await answer.execute({ query: 'x', params: { bookmarks_only: false } }, parentExec)
    globalThis.fetch = realFetch3
    check('a model-supplied bookmarks_only:false cannot opt out of the enforced scope',
      body?.params?.bookmarks_only === true, JSON.stringify(body?.params))
  }

  // 200 但没有 data（反代/旧引擎）→ 抛错，绝不伪装成"库内无此条款"
  {
    const realFetch4 = globalThis.fetch
    globalThis.fetch = async (url, init) => {
      const u = String(url)
      if (u.includes('/api/v1/ks/answer')) {
        return { status: 200, ok: true, text: async () => JSON.stringify({ hello: 'world' }) }
      }
      return realFetch4(url, init)
    }
    let envelopeError = null
    try {
      await answer.execute({ query: 'x' }, { agent: { session: { id: 'smoke-off', header: {} } } })
    } catch (error) {
      envelopeError = error
    }
    globalThis.fetch = realFetch4
    check('ks_answer 200-without-data throws (never "库内无此条款")',
      envelopeError !== null && /信封异常/.test(String(envelopeError?.message)),
      String(envelopeError?.message ?? '').slice(0, 70))
  }

  // 「仅收藏」也要覆盖 ks_resolve_clause（verifier 二轮 P1：定位路径不能成为后门）
  {
    const realFetch5 = globalThis.fetch
    const HIT = {
      code: 200, status: 'success',
      data: {
        doc_id: 'doc_r9', page_start: 7, clause_revision_id: 'rev_r9',
        clause_key: 'k_r9', standard_no: 'GB 2222-2020', clause_number: '3.1',
        legal_status: 'effective', bookmarked: false,
      },
    }
    globalThis.fetch = async (url, init) => {
      const u = String(url)
      if (u.includes('/api/v1/clauses/resolve')) {
        return { status: 200, ok: true, text: async () => JSON.stringify(HIT) }
      }
      return realFetch5(url, init)
    }
    const outside = await resolve.execute(
      { standard_no: 'GB 2222-2020', clause_number: '3.1' }, parentExec)
    const inside = await resolve.execute(
      { standard_no: 'GB 2222-2020', clause_number: '3.1' },
      { agent: { session: { id: 'smoke-off', header: {} } } })
    // 同一会话、命中在收藏集内 → bookmarks_scope=inside 且**没有** scope_notice
    const realFetch5b = globalThis.fetch
    globalThis.fetch = async (url, init) => {
      const u = String(url)
      if (u.includes('/api/v1/clauses/resolve')) {
        return { status: 200, ok: true, text: async () => JSON.stringify({
          ...HIT, data: { ...HIT.data, bookmarked: true },
        }) }
      }
      return realFetch5b(url, init)
    }
    const resolveInsideHit = await resolve.execute(
      { standard_no: 'GB 2222-2020', clause_number: '3.1' }, parentExec)
    globalThis.fetch = realFetch5b
    globalThis.fetch = realFetch5
    check('resolve hit carries a clickable evidence_url (doc+page+rev)',
      outside.evidence_url
        === 'http://127.0.0.1:1/__ks_evidence__?doc=doc_r9&page=7&rev=rev_r9',
      String(outside.evidence_url))
    check('resolve outside the bookmark collection is flagged + banned from 依据',
      outside.bookmarks_scope === 'outside' && typeof outside.scope_notice === 'string'
      && outside.bookmarks_scope !== inside.bookmarks_scope,
      `${outside.bookmarks_scope} / ${String(inside.bookmarks_scope)}`)
    check('resolve with bookmarks off carries no scope claim', inside.bookmarks_scope === null,
      String(inside.bookmarks_scope))
    check('an in-collection hit gets bookmarks_scope=inside and NO scope_notice',
      resolveInsideHit !== null && resolveInsideHit.bookmarks_scope === 'inside'
      && resolveInsideHit.scope_notice === undefined
      && resolveInsideHit.bookmarked === true,
      `${String(resolveInsideHit?.bookmarks_scope)} notice=${String(resolveInsideHit?.scope_notice)}`)
    check('resolve payload has no undefined', findUndefined(outside) === null,
      findUndefined(outside) ?? '')
  }

  // 查无此条 + 仅收藏：bookmarks_scope 必须是 null（verifier 三轮 P2：旧实现回 "inside"，
  // 等于对一条不存在的条款断言"它在你的收藏集内"）
  {
    const realFetch6 = globalThis.fetch
    globalThis.fetch = async (url, init) => {
      const u = String(url)
      if (u.includes('/api/v1/clauses/resolve')) {
        return { status: 404, ok: false, text: async () => JSON.stringify({ code: 404, error: 'clause_not_found' }) }
      }
      return realFetch6(url, init)
    }
    const missScoped = await resolve.execute(
      { standard_no: 'GB 00000-9999', clause_number: '99.99.99' }, parentExec)
    globalThis.fetch = realFetch6
    check('a not-found resolve under 仅收藏 claims NO scope (null, not "inside")',
      missScoped.found === false && missScoped.bookmarks_scope === null
      && missScoped.bookmarked === null && missScoped.evidence_url === null,
      JSON.stringify({ found: missScoped.found, scope: missScoped.bookmarks_scope }))
  }

  // ks_answer 的证据里透出 `bookmarked`（规则 6 要模型据此判断"范围过滤是否生效"）
  {
    const markedAnswer = {
      code: 200, status: 'success',
      data: {
        tier: 'direct',
        evidence: [
          { doc_id: 'doc_a1', page_start: 3, standard_no: 'GB 1111-2020', clause_number: '5.1.2',
            legal_status: 'effective', content_text: 'x', bookmarked: true },
          { doc_id: 'doc_a2', page_start: 9, standard_no: 'GB 2222-2020', clause_number: '3.1',
            legal_status: 'effective', content_text: 'y', bookmarked: false },
        ],
        derivation: 'd', conclusion: 'c', verification: { is_valid: true }, notes: [],
      },
    }
    const marked = await captureAnswerCall(markedAnswer, parentExec)
    const ev = marked.value.evidence ?? []
    check('evidence carries the engine-provided bookmarked flag verbatim',
      ev.length === 2 && ev[0].bookmarked === true && ev[1].bookmarked === false
      && marked.value.answer_scope?.bookmarks_only === true,
      JSON.stringify(ev.map((e) => e.bookmarked)))
    // verifier 四轮 P1-A：引擎**不提供**该字段时（旧引擎/异常路径）host 绝不能强转成
    // false —— 那会配合规则 6 让模型每次误报"范围过滤未生效"。
    const unmarked = {
      code: 200, status: 'success',
      data: {
        tier: 'direct',
        evidence: [{ doc_id: 'doc_a1', page_start: 3, standard_no: 'GB 1111-2020',
          clause_number: '5.1.2', legal_status: 'effective', content_text: 'x' }],
        derivation: 'd', conclusion: 'c', verification: { is_valid: true }, notes: [],
      },
    }
    const unmarkedCall = await captureAnswerCall(unmarked, parentExec)
    check('a missing bookmarked field becomes null (host never fabricates a boolean)',
      unmarkedCall.value.evidence?.[0]?.bookmarked === null,
      JSON.stringify(unmarkedCall.value.evidence?.[0]?.bookmarked))
  }

  // ---- 收藏夹内提问（2026-10 收藏目录）：host 强制 folder_id + resolve 夹标记 ----
  {
    // 会话基线：一个开夹范围的会话 + 一个无范围的会话
    setMode('smoke-folder', { folderId: 'bmf_SMOKE01', folderName: '冒烟夹' })

    const folderCall = await captureAnswerCall(SYNTH_ANSWER,
      { agent: { session: { id: 'smoke-folder', header: {} } } })
    check('folder scope on → host FORCES params.folder_id',
      folderCall.sentBody?.params?.folder_id === 'bmf_SMOKE01',
      JSON.stringify(folderCall.sentBody?.params))
    check('answer_scope echoes folder truth + name',
      folderCall.value.answer_scope?.folder === true
        && folderCall.value.answer_scope?.folder_id === 'bmf_SMOKE01'
        && folderCall.value.answer_scope?.folder_name === '冒烟夹'
        && folderCall.value.answer_scope?.forensic === true,
      JSON.stringify(folderCall.value.answer_scope))

    const plainCall = await captureAnswerCall(SYNTH_ANSWER,
      { agent: { session: { id: 'smoke-plain', header: {} } } })
    check('folder scope off → no folder_id in params, answer_scope.folder=false',
      plainCall.sentBody?.params?.folder_id === undefined
        && plainCall.value.answer_scope?.folder === false
        && plainCall.value.answer_scope?.folder_id === null,
      JSON.stringify(plainCall.value.answer_scope))
    check('plain answer payload has no undefined', findUndefined(plainCall.value) === null,
      findUndefined(plainCall.value) ?? '')

    // 模型显式传别的 folder_id 也改不了（host 强制覆盖）
    {
      const realFetchF = globalThis.fetch
      let bodyF = null
      globalThis.fetch = async (url, init) => {
        const u = String(url)
        if (u.includes('/api/v1/ks/answer')) {
          bodyF = init?.body ? JSON.parse(String(init.body)) : null
          return { status: 200, ok: true, text: async () => JSON.stringify(SYNTH_ANSWER) }
        }
        return realFetchF(url, init)
      }
      await answer.execute(
        { query: 'x', params: { folder_id: 'bmf_MODEL_GUESS' } },
        { agent: { session: { id: 'smoke-folder', header: {} } } })
      globalThis.fetch = realFetchF
      check('a model-supplied folder_id cannot hijack the session folder',
        bodyF?.params?.folder_id === 'bmf_SMOKE01', JSON.stringify(bodyF?.params))
    }

    // 模型传了合法 folder_id 且会话没开夹范围 → 白名单放行（模型可主动用夹范围，
    // 但 answer_scope 如实回显 folder:false 因为这是模型自己的选择不是 host 强制）
    {
      const realFetchG = globalThis.fetch
      let bodyG = null
      globalThis.fetch = async (url, init) => {
        const u = String(url)
        if (u.includes('/api/v1/ks/answer')) {
          bodyG = init?.body ? JSON.parse(String(init.body)) : null
          return { status: 200, ok: true, text: async () => JSON.stringify(SYNTH_ANSWER) }
        }
        return realFetchG(url, init)
      }
      await answer.execute(
        { query: 'x', params: { folder_id: 'bmf_MODEL_PICK' } },
        { agent: { session: { id: 'smoke-plain2', header: {} } } })
      globalThis.fetch = realFetchG
      check('a well-formed model-supplied folder_id passes the whitelist when no session scope',
        bodyG?.params?.folder_id === 'bmf_MODEL_PICK', JSON.stringify(bodyG?.params))
    }

    // 子会话继承夹范围（工具层与提示层同一真值）
    fakeSessions.set('smoke-folder-child',
      { session: { header: { parentSession: 'smoke-folder' } } })
    const folderChildCall = await captureAnswerCall(SYNTH_ANSWER,
      { agent: { session: { id: 'smoke-folder-child', header: { parentSession: 'smoke-folder' } } } })
    check('a CHILD session inherits the folder scope too (enforced at tool layer)',
      folderChildCall.sentBody?.params?.folder_id === 'bmf_SMOKE01'
        && folderChildCall.value.answer_scope?.source === 'parent',
      JSON.stringify(folderChildCall.value.answer_scope))

    // 夹范围 + 仅收藏叠加：两个强制参数都在
    setMode('smoke-folder', { bookmarksOnly: true })
    const stackedCall = await captureAnswerCall(SYNTH_ANSWER,
      { agent: { session: { id: 'smoke-folder', header: {} } } })
    check('folder + bookmarks stack: both enforced params present',
      stackedCall.sentBody?.params?.folder_id === 'bmf_SMOKE01'
        && stackedCall.sentBody?.params?.bookmarks_only === true,
      JSON.stringify(stackedCall.sentBody?.params))

    // 关夹范围后参数消失（bookmarksOnly 保留——只清 folder 维度）
    setMode('smoke-folder', { folderId: null })
    const closedCall = await captureAnswerCall(SYNTH_ANSWER,
      { agent: { session: { id: 'smoke-folder', header: {} } } })
    check('folderId:null closes only the folder dimension (bookmarks kept)',
      closedCall.sentBody?.params?.folder_id === undefined
        && closedCall.sentBody?.params?.bookmarks_only === true,
      JSON.stringify(closedCall.sentBody?.params))
    setMode('smoke-folder', { bookmarksOnly: false, forensic: false })

    // resolve 的夹标记：引擎回 inside / outside / 无标记（旧引擎）
    const resolveFolderExec = { agent: { session: { id: 'smoke-resolve-folder', header: {} } } }
    setMode('smoke-resolve-folder', { folderId: 'bmf_RSV', folderName: '定位夹' })
    const withResolve = (engineFolderScope) => {
      const realFetchH = globalThis.fetch
      globalThis.fetch = async (url, init) => {
        const u = String(url)
        if (u.includes('/api/v1/clauses/resolve')) {
          return { status: 200, ok: true, text: async () => JSON.stringify({
            code: 200, status: 'success',
            data: {
              doc_id: 'doc_r9', page_start: 7, clause_revision_id: 'rev_r9',
              clause_key: 'k_r9', standard_no: 'GB 2222-2020', clause_number: '3.1',
              legal_status: 'effective', bookmarked: true,
              ...(engineFolderScope === null ? {} : { folder_scope: engineFolderScope }),
            },
          }) }
        }
        return realFetchH(url, init)
      }
      return resolve.execute(
        { standard_no: 'GB 2222-2020', clause_number: '3.1' }, resolveFolderExec)
        .then((v) => { globalThis.fetch = realFetchH; return v },
          (e) => { globalThis.fetch = realFetchH; throw e })
    }
    const rsIn = await withResolve('inside')
    check('resolve: engine folder_scope=inside passes cleanly (no folder_notice)',
      rsIn.folder_scope === 'inside' && rsIn.folder_notice === undefined
        && rsIn.folder_name === '定位夹',
      JSON.stringify({ scope: rsIn.folder_scope, name: rsIn.folder_name }))
    const rsOut = await withResolve('outside')
    check('resolve: engine folder_scope=outside gets the locating-only ban',
      rsOut.folder_scope === 'outside' && typeof rsOut.folder_notice === 'string'
        && rsOut.folder_notice.includes('不得写入依据区'),
      JSON.stringify({ scope: rsOut.folder_scope }))
    const rsUnknown = await withResolve(null)
    check('resolve: engine gives no folder verdict → unknown, no ban, no fabrication',
      rsUnknown.folder_scope === 'unknown' && rsUnknown.folder_notice === undefined
        && rsUnknown.folder_name === undefined,
      JSON.stringify({ scope: rsUnknown.folder_scope, name: rsUnknown.folder_name }))
    check('resolve folder outputs have no undefined',
      findUndefined(rsIn) === null && findUndefined(rsOut) === null
        && findUndefined(rsUnknown) === null,
      `${findUndefined(rsIn) ?? ''}${findUndefined(rsOut) ?? ''}${findUndefined(rsUnknown) ?? ''}`)
    // 夹范围未激活 → folder_scope 全 null（不声称任何范围；即使引擎带回了字段）
    setMode('smoke-resolve-folder', { folderId: null, forensic: false })
    const realFetchI = globalThis.fetch
    globalThis.fetch = async (url, init) => {
      const u = String(url)
      if (u.includes('/api/v1/clauses/resolve')) {
        return { status: 200, ok: true, text: async () => JSON.stringify({
          code: 200, status: 'success',
          data: { doc_id: 'doc_r9', page_start: 7, clause_revision_id: 'rev_r9',
            clause_key: 'k_r9', standard_no: 'GB 2222-2020', clause_number: '3.1',
            legal_status: 'effective', bookmarked: false, folder_scope: 'inside' },
        }) }
      }
      return realFetchI(url, init)
    }
    const rsOff = await resolve.execute(
      { standard_no: 'GB 2222-2020', clause_number: '3.1' },
      { agent: { session: { id: 'smoke-plain3', header: {} } } })
    globalThis.fetch = realFetchI
    check('folder scope inactive → resolve claims NO folder scope regardless of engine field',
      rsOff.folder_scope === null && rsOff.folder_notice === undefined
        && rsOff.folder_name === undefined,
      JSON.stringify({ scope: rsOff.folder_scope }))
  }

  // ── 插件 Config：官方要求「Config 必须是标准 schema」；这三条钉住它别被删掉 ──
  // 官方文档规范与插件契约一致要求导出的配置是 Standard Schema（Schemastery），
  // 「导普通对象**不会校验**」——那正是静默失效。而本地 schemastery 挡不住"键名拼错"，
  // 所以 apply 里另有一道未知键检查（见 src/index.js 的注释）。
  {
    const mod = await import('../src/index.js')
    check('插件导出 Config（官方要求：配置必须是标准 schema，否则不校验）',
      mod.Config !== undefined && typeof mod.Config === 'function',
      `typeof Config = ${typeof mod.Config}`)
    let typeRejected = false
    try { mod.Config({ startupTimeoutMs: 'abc' }) } catch { typeRejected = true }
    check('Config 拒绝类型错的配置（字符串当毫秒数）', typeRejected)
    let unknownRejected = false
    try { mod.apply({}, { typoKey: 1 }) } catch (e) { unknownRejected = /未知键/.test(String(e.message)) }
    check('apply 拒绝**未知配置键**（本地 schemastery 挡不住这件事，所以自己挡）',
      unknownRejected)
    const okCfg = mod.Config({})
    check('Config 填默认值且不给"留空有意义"的键造默认值',
      okCfg.startupTimeoutMs === 60_000 && okCfg.idleTimeoutMs === 30 * 60 * 1000
      && okCfg.engineRoot === undefined && okCfg.python === undefined,
      JSON.stringify(okCfg))
  }

  const failed = results.filter((r) => !r.ok)
  console.log(`\n== tool smoke ${failed.length === 0 ? 'PASS' : 'FAIL'} `
    + `(${results.length - failed.length}/${results.length}) ==`)
  process.exit(failed.length === 0 ? 0 : 1)
}

main().catch((err) => {
  console.error(`[fatal] ${err && err.stack ? err.stack : err}`)
  process.exit(1)
})
