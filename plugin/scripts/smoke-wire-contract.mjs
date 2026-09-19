/**
 * ks-dsh-plugin — scripts/smoke-wire-contract.mjs
 *
 * **wire fixture 回放**（第 6 步施工单 §5）：假引擎**从 fixture 读**响应，而不是把响应
 * 硬编码在这个文件里；6 个模型工具的每一次出网调用都被记下来，与
 * `test/fixtures/ks-engine-wire.json` 声明的契约逐条比对。
 *
 * ## 为什么要有这一层
 * 现有 5 个 `createServer` 冒烟各自拿桩引擎测"某条链的行为"，但**响应是写死在冒烟里的**——
 * 于是"我们真正发出去的请求形状"与"引擎真正回的报文字段名"这两件事**没有任何一份
 * 可核对的清单**。改了端点、少发一个字段、响应字段名漂了，只有真机才炸。本文件把那份
 * 清单固定下来（fixture），并双向夹逼。
 *
 * ## 五条断言（红了各说明什么）
 *   E1 `the plugin makes exactly the documented engine calls`
 *      observed（排序后的 canonical key）与 fixture.calls **逐条相等**，且**按场景**也要相等。
 *      红 ⇒ 有人加了/改了/删了一条出网调用而没更新 fixture（或某个工具多发了一次）。
 *   E2 `the fixture is not stale`
 *      fixture 里每条 calls[i] 至少在 observed 里出现一次。
 *      红 ⇒ fixture 里留了永不发生的条目（"文档化了的假契约"，看着很完整）。
 *   E3 `the fixture is actually loaded`（防复发，最重要）
 *      fixture 非空 **且** 假服务器真的收到请求 **且** 每个声明的场景都被驱动过、
 *      没有声明之外的场景。红 ⇒ 命中本仓已知复发模式（`smoke-lifecycle.mjs:131`：
 *      "fixture 写了但完全不生效"，E1/E2 会在 0 请求时空转通过）。
 *   E4 `a minimal envelope still yields a complete result`
 *      只回 fixture 声明的字段（minimal 探针）：
 *        a) minimal 必须是 response.body 的子形状（不许凭空造值/改值）；
 *        b) responseFieldsRead 与 minimal 的叶路径**逐条相等**（防声明与探针分叉）；
 *        c) 两次回放的**结果差异**必须全部落在 `_passthrough` 声明的支下；
 *        d) 结果里任何深度都不许出现 `undefined`（DSH lossless 校验会整条判 INVALID）。
 *      红 ⇒ 我们偷偷依赖了未声明的响应字段，或回出了 undefined。
 *   E5 `the write tool's body carries no source_tier`
 *      ks_collect 的请求体不含 `source_tier`（回归 `plugin/src/collect.js:184-185` 的纪律：
 *      采集者不得自 claim 可信度）。
 *
 * ## 纪律
 * fixture **手写**，本文件只做**比对**，绝不回写 fixture（施工单 §5 风险 1：
 * "跑一遍把观察到的记下来"会把错误一起固化）。跑法：node scripts/smoke-wire-contract.mjs
 */

import { readFileSync } from 'node:fs'
import { createServer } from 'node:http'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

import {
  makeAnswerTool,
  makeEffectReportTool,
  makePingTool,
  makeResolveTool,
} from '../src/index.js'
import { makeMaterialsTool } from '../src/materials.js'
import { makeCollectTool } from '../src/collect.js'

const here = dirname(fileURLToPath(import.meta.url))
// `KS_WIRE_FIXTURE` 只为一件事存在：**验证这些断言真的会红**（变异测试）。
// 用法：把 fixture 拷到临时文件、改坏它、`$env:KS_WIRE_FIXTURE=<临时文件>` 再跑一遍本脚本，
// 逐条确认对应断言变红。默认路径才是契约本体；跑门禁时**不设**这个变量。
const FIXTURE_PATH = process.env.KS_WIRE_FIXTURE
  || join(dirname(here), 'test', 'fixtures', 'ks-engine-wire.json')

const results = []
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}

/* --------------------------- fixture 载入（先把"载不到"变成红） --------------------------- */

let fixture = null
try {
  fixture = JSON.parse(readFileSync(FIXTURE_PATH, 'utf8'))
} catch (error) {
  check('fixture 能载入', false, `${FIXTURE_PATH}: ${error.message}`)
  console.error('\nsmoke-wire-contract: 1/1 FAILED（fixture 载不进来，其余断言无意义）')
  process.exit(1)
}
check('fixture 能载入', true, FIXTURE_PATH)

const CALLS = Array.isArray(fixture.calls) ? fixture.calls : []
const SCENARIOS = Array.isArray(fixture.scenarios) ? fixture.scenarios : []
const CALL_BY_ID = new Map(CALLS.map((c) => [c.id, c]))

/* ==========================================================================
 * 结构自检：fixture 自己先得是自洽的（不然 E1/E4 的失败会指向错的地方）
 * ========================================================================== */

{
  const problems = []
  if (CALLS.length === 0) problems.push('calls 为空')
  if (SCENARIOS.length === 0) problems.push('scenarios 为空')
  const ids = new Set()
  for (const c of CALLS) {
    if (!c.id) problems.push('有条目缺 id')
    if (ids.has(c.id)) problems.push(`id 重复: ${c.id}`)
    ids.add(c.id)
    for (const k of ['request', 'response', 'minimal', 'responseFieldsRead']) {
      if (c[k] === undefined) problems.push(`${c.id} 缺 ${k}`)
    }
    if (typeof c._source !== 'string' || c._source.length < 10) {
      problems.push(`${c.id} 缺 _source（出处）——说不出出处的 fixture 不许写`)
    }
    if (!Array.isArray(c._passthrough)) problems.push(`${c.id} 缺 _passthrough 数组`)
  }
  const seen = new Set()
  for (const s of SCENARIOS) {
    if (!Array.isArray(s.expectCalls) || s.expectCalls.length === 0) {
      problems.push(`场景 ${s.id} 没声明 expectCalls`)
      continue
    }
    for (const cid of s.expectCalls) {
      if (!CALL_BY_ID.has(cid)) problems.push(`场景 ${s.id} 引用了不存在的 call: ${cid}`)
      if (seen.has(cid)) problems.push(`call ${cid} 被多个场景声明（无法按场景归属）`)
      seen.add(cid)
    }
  }
  for (const c of CALLS) {
    if (!seen.has(c.id)) problems.push(`call ${c.id} 没有被任何场景声明 ⇒ 永远观察不到`)
  }
  check('fixture 自洽（id 唯一 / 每条都有出处 / 每条都被某个场景声明）',
    problems.length === 0, problems.length === 0 ? `${CALLS.length} calls / ${SCENARIOS.length} 场景` : problems.join('; '))
}

/* ==========================================================================
 * 假引擎：响应**从 fixture 读**
 * ========================================================================== */

let mode = 'full'                 // 'full' | 'minimal'
const observed = []               // 本次 pass 观察到的请求
let unmatched = []                // 没能在 fixture 里对上的请求
let passResponses = new Map()     // `${method} ${path}` → 该 pass 要回的 body

/** 查询串 → 普通对象（无参数时 null）。键序无关：比对时统一 sortDeep。 */
function queryObject(url) {
  const out = {}
  for (const [k, v] of url.searchParams) {
    if (k in out) out[k] = Array.isArray(out[k]) ? [...out[k], v] : [out[k], v]
    else out[k] = v
  }
  return Object.keys(out).length > 0 ? out : null
}

const server = createServer((req, res) => {
  const chunks = []
  req.on('data', (c) => chunks.push(c))
  req.on('end', () => {
    const raw = Buffer.concat(chunks).toString('utf8')
    let sent = null
    try { sent = raw.length > 0 ? JSON.parse(raw) : null } catch { sent = { __unparsed: raw } }
    const url = new URL(req.url, 'http://127.0.0.1')
    const auth = req.headers.authorization ?? null
    observed.push({
      method: req.method, path: url.pathname, rawQuery: url.search.replace(/^\?/, ''),
      query: queryObject(url), body: sent, auth: auth === null ? 'none' : 'bearer',
    })
    const key = `${req.method} ${url.pathname}`
    if (!passResponses.has(key)) {
      unmatched.push({ key, rawQuery: url.search, body: sent })
      res.writeHead(500, { 'content-type': 'application/json' })
      res.end(JSON.stringify({ code: 500, status: 'error', error: 'no_fixture_call', message: key }))
      return
    }
    const call = passResponses.get(key)
    const body = mode === 'minimal' ? call.minimal : call.response.body
    res.writeHead(call.response.http ?? 200,
      { 'content-type': call.response.contentType ?? 'application/json' })
    res.end(JSON.stringify(body))
  })
})
await new Promise((r) => server.listen(0, '127.0.0.1', r))
const PORT = server.address().port

const TOKEN = 'tok_wire_stub'
// 会话形状照 `plugin/src/engine.js:416`（`{port, token, pid, started_at, spawnedByUs}`）：
// 少给 `pid` 会让 ks_ping 回 `engine.pid: undefined`（E4d 会当场红——它就是这么发现的）。
const fakeManager = {
  ensureLive: async () => ({ port: PORT, token: TOKEN, pid: 4242, spawnedByUs: false }),
}

/** 工具工厂派发表。fixture 声明了一个这里没有的工具 ⇒ E3 会红（不许被静默跳过）。 */
const FACTORIES = {
  ks_ping: () => makePingTool(fakeManager),
  ks_resolve_clause: (chatMode) => makeResolveTool(fakeManager, () => chatMode),
  ks_answer: (chatMode) => makeAnswerTool(fakeManager, () => chatMode),
  ks_effect_report: () => makeEffectReportTool(fakeManager),
  ks_materials: () => makeMaterialsTool(fakeManager),
  ks_collect: (chatMode) => makeCollectTool(fakeManager, () => chatMode),
}

const chatModeOf = (name) => {
  const m = fixture.chatModes?.[name]
  if (!m) throw new Error(`fixture.chatModes 里没有 ${name}`)
  return m
}

/** 跑一遍全部场景，返回 `{ outputs, skipped, perScenario, errors }`。 */
async function runAllScenarios(pass) {
  mode = pass
  const outputs = {}
  const skipped = []
  const errors = []
  const perScenario = new Map()
  for (const s of SCENARIOS) {
    const make = FACTORIES[s.tool]
    if (typeof make !== 'function') {
      // 不静默跳过：这一条会让 E3 红。
      skipped.push(`${s.id}(${s.tool})`)
      continue
    }
    const tool = make(chatModeOf(s.chatMode))
    // 每次调用给一个新 session id：ks_collect 有**会话级**暂定上限（collect.js:42），
    // 复用 id 会让两次 pass 互相累加——那是"冒烟自己造成的假红"的经典形态。
    const sessionId = `wire-${pass}-${s.id}`
    observed.length = 0
    unmatched = []
    passResponses = new Map(
      s.expectCalls.map((cid) => {
        const k = `${CALL_BY_ID.get(cid).request.method} ${CALL_BY_ID.get(cid).request.path}`
        return [k, CALL_BY_ID.get(cid)]
      }))
    try {
      outputs[s.id] = await tool.execute(s.args ?? {}, {
        signal: new AbortController().signal,
        agent: { session: { id: sessionId } },
      })
    } catch (error) {
      // ⚠ **不要让异常杀掉整个脚本**：请求对不上 fixture 时假引擎回 500、工具抛错，
      // 那时候 E1 才是要说真话的那条断言。第一版没接住 ⇒ 变异测试（改坏声明路径）
      // 只得到一段栈，而不是"应发未发/发了未声明"——诊断质量掉一个档。
      errors.push(`${s.id}[${pass}]: ${error?.message ?? error}`)
      outputs[s.id] = { __threw: String(error?.message ?? error) }
    }
    perScenario.set(s.id, { observed: observed.map((o) => ({ ...o })), unmatched: [...unmatched] })
  }
  return { outputs, skipped, perScenario, errors }
}

const full = await runAllScenarios('full')
const minimal = await runAllScenarios('minimal')

/* ==========================================================================
 * E3（先跑：它红了，E1/E2 的结论不可信）
 * ========================================================================== */

{
  // E0：每个场景都得**跑成功**——请求对不上 fixture 时假引擎回 500，工具会抛，
  // 这条把栈翻成一句"哪个场景、为什么"，让 E1 的结论可读（第一版没接住 ⇒ 只有栈）。
  const errors = [...full.errors, ...minimal.errors]
  check('E0 每个场景的 execute 都成功（异常会先在这里说清）',
    errors.length === 0, errors.length === 0 ? `${SCENARIOS.length} × 2 遍` : errors.join(' | '))

  const observedFull = SCENARIOS.flatMap((s) => full.perScenario.get(s.id)?.observed ?? [])
  const observedMin = SCENARIOS.flatMap((s) => minimal.perScenario.get(s.id)?.observed ?? [])
  const observedTotal = observedFull.length + observedMin.length
  const skipped = [...full.skipped, ...minimal.skipped]
  const expectedTotal = CALLS.length * 2
  check('E3 the fixture is actually loaded (防复发)',
    CALLS.length > 0 && observedTotal > 0
    && skipped.length === 0 && full.perScenario.size === SCENARIOS.length
    && minimal.perScenario.size === SCENARIOS.length
    && observedTotal === expectedTotal,
    `fixture.calls=${CALLS.length} 场景=${SCENARIOS.length}`
    + ` 两遍共收到请求=${observedTotal}（期望 ${expectedTotal}）`
    + (skipped.length ? ` 跳过=${skipped.join(',')}` : ''))
  const unmatchedAll = [
    ...SCENARIOS.flatMap((s) => full.perScenario.get(s.id)?.unmatched ?? []),
    ...SCENARIOS.flatMap((s) => minimal.perScenario.get(s.id)?.unmatched ?? []),
  ]
  check('E3b 没有"fixture 里没有的请求"打到假引擎',
    unmatchedAll.length === 0,
    unmatchedAll.length === 0 ? 'ok' : JSON.stringify(unmatchedAll.slice(0, 3)))
}

/* ==========================================================================
 * E1 / E2：恰好这些调用（全局 + 按场景）
 * ========================================================================== */

/** 递归排键，让 JSON.stringify 与对象键序无关（并发请求顺序不定，键序也不该当契约）。 */
function sortDeep(v) {
  if (Array.isArray(v)) return v.map(sortDeep)
  if (v !== null && typeof v === 'object') {
    const out = {}
    for (const k of Object.keys(v).sort()) out[k] = sortDeep(v[k])
    return out
  }
  return v
}

function callKey(c) {
  return JSON.stringify(sortDeep({
    method: c.method, path: c.path, rawQuery: c.rawQuery ?? '',
    query: c.query ?? null, body: c.body ?? null, auth: c.auth,
  }))
}

const declaredKeys = CALLS.map((c) => callKey(c.request))

{
  const observedAll = [
    ...SCENARIOS.flatMap((s) => full.perScenario.get(s.id)?.observed ?? []),
    ...SCENARIOS.flatMap((s) => minimal.perScenario.get(s.id)?.observed ?? []),
  ]
  const observedKeys = observedAll.map(callKey)
  // 每个场景跑两遍（full / minimal）⇒ 期望集合是声明集合的两倍
  const declaredSorted = [...declaredKeys, ...declaredKeys].sort()
  const observedSorted = [...observedKeys].sort()
  const missing = declaredSorted.filter((k) => !observedSorted.includes(k))
  const extra = observedSorted.filter((k) => !declaredSorted.includes(k))
  check('E1 the plugin makes exactly the documented engine calls',
    missing.length === 0 && extra.length === 0
    && observedSorted.length === declaredSorted.length,
    missing.length === 0 && extra.length === 0
      ? `${observedSorted.length} 次调用（两遍）逐条相符`
      : `应发未发=${missing.length} 发了未声明=${extra.length}`
        + `${missing.length ? `\n      缺: ${missing.join('\n           ')}` : ''}`
        + `${extra.length ? `\n      多: ${extra.join('\n           ')}` : ''}`)

  // 按场景归属：光有全局集合相等还不够——两个工具互换端点也会让全局相等。
  const perScenario = []
  for (const s of SCENARIOS) {
    for (const [pass, run] of [['full', full], ['minimal', minimal]]) {
      const got = (run.perScenario.get(s.id)?.observed ?? []).map(callKey).sort()
      const want = s.expectCalls.map((cid) => callKey(CALL_BY_ID.get(cid).request)).sort()
      if (JSON.stringify(got) !== JSON.stringify(want)) {
        perScenario.push(`${s.id}[${pass}]: got ${JSON.stringify(got)} want ${JSON.stringify(want)}`)
      }
    }
  }
  check('E1b 每个场景的调用集合与它声明的 expectCalls 逐条相等',
    perScenario.length === 0,
    perScenario.length === 0 ? `${SCENARIOS.length} 个场景 × 2 遍各自相符` : perScenario.join(' | '))

  // E2：fixture 里不许有永远观察不到的条目（反向）
  const neverSeen = CALLS.filter((c) => !observedKeys.includes(callKey(c.request)))
  check('E2 the fixture is not stale',
    neverSeen.length === 0,
    neverSeen.length === 0 ? '每条 calls[i] 都被观察到' : neverSeen.map((c) => c.id).join(','))
}

/* ==========================================================================
 * E4：minimal 探针
 * ========================================================================== */

function isPlainObject(v) { return v !== null && typeof v === 'object' && !Array.isArray(v) }

/** minimal 必须是 full 的**子形状**：值相等、键可以不齐，但不许凭空多值/改值。 */
function subShapeProblems(min, full, base = '', out = []) {
  if (Array.isArray(min)) {
    if (!Array.isArray(full)) { out.push(`${base}: 期望数组，full 不是`); return out }
    if (min.length > full.length) { out.push(`${base}: minimal 比 full 长`); return out }
    min.forEach((v, i) => subShapeProblems(v, full[i], `${base}[${i}]`, out))
    return out
  }
  if (isPlainObject(min)) {
    if (!isPlainObject(full)) { out.push(`${base}: 期望对象，full 不是`); return out }
    for (const k of Object.keys(min)) {
      if (!(k in full)) { out.push(`${base}.${k}: full 里没有这个键`); continue }
      subShapeProblems(min[k], full[k], base ? `${base}.${k}` : k, out)
    }
    return out
  }
  if (JSON.stringify(min) !== JSON.stringify(full)) {
    out.push(`${base}: minimal=${JSON.stringify(min)} full=${JSON.stringify(full)}`)
  }
  return out
}

/** 叶路径（数组元素用 `*` 段；空数组/空对象记它自己）。 */
function leafSegs(v, base = [], out = []) {
  if (Array.isArray(v)) {
    if (v.length === 0) { out.push(base); return out }
    v.forEach((x) => leafSegs(x, [...base, '*'], out))
    return out
  }
  if (isPlainObject(v)) {
    const keys = Object.keys(v)
    if (keys.length === 0) { out.push(base); return out }
    for (const k of keys) leafSegs(v[k], [...base, k], out)
    return out
  }
  out.push(base)
  return out
}

/** 把 `a[].b` / `a.b` 解析成段数组（`[]` 段归一成 `*`）。 */
function segsOf(path) {
  return String(path).split('.').flatMap((part) => {
    const segs = []
    const m = part.match(/^([^[\]]*)((?:\[\])*)$/)
    if (!m || m[1] === '') return []
    segs.push(m[1])
    for (let i = 0; i < m[2].length / 2; i += 1) segs.push('*')
    return segs
  })
}

const MISSING = Symbol('missing')

/** 在真相里解析一条声明路径（`*` 展开数组元素）。返回命中值列表。 */
function resolveSegs(value, segs) {
  if (segs.length === 0) return [value]
  const [head, ...rest] = segs
  if (head === '*') {
    if (!Array.isArray(value)) return []
    return value.flatMap((x) => resolveSegs(x, rest))
  }
  if (value === null || typeof value !== 'object' || !(head in value)) return []
  return resolveSegs(value[head], rest)
}

const isPrefix = (a, b) => a.length <= b.length && a.every((s, i) => s === b[i])
const segsKey = (s) => s.join('.')

/** 两棵结果树的差异路径（值不同 / 键只在一边）。 */
function diffPaths(a, b, base = '', out = []) {
  const aObj = isPlainObject(a); const bObj = isPlainObject(b)
  if (aObj && bObj) {
    for (const k of new Set([...Object.keys(a), ...Object.keys(b)])) {
      diffPaths(a[k], b[k], base ? `${base}.${k}` : k, out)
    }
    return out
  }
  if (Array.isArray(a) && Array.isArray(b)) {
    if (a.length !== b.length) { out.push(base || '(root)'); return out }
    a.forEach((v, i) => diffPaths(v, b[i], `${base}[${i}]`, out))
    return out
  }
  if (JSON.stringify(a) !== JSON.stringify(b)) out.push(base || '(root)')
  return out
}

/** 收集所有 `undefined` 的路径（DSH 的 lossless 校验会拒绝它）。 */
function undefinedPaths(v, base = '', out = []) {
  if (Array.isArray(v)) { v.forEach((x, i) => undefinedPaths(x, `${base}[${i}]`, out)); return out }
  if (v !== null && typeof v === 'object') {
    for (const k of Object.keys(v)) {
      if (v[k] === undefined) out.push(base ? `${base}.${k}` : k)
      else undefinedPaths(v[k], base ? `${base}.${k}` : k, out)
    }
  }
  return out
}

{
  const shapeProblems = []
  const readProblems = []
  for (const c of CALLS) {
    shapeProblems.push(...subShapeProblems(c.minimal, c.response.body, c.id).map((p) => `${c.id}.${p}`))
    const leaves = leafSegs(c.minimal)
    for (const path of c.responseFieldsRead) {
      // ① 声明了却探针里取不到 ⇒ 声明比探针宽（写了没测，或路径写错）
      if (resolveSegs(c.minimal, segsOf(path)).length === 0) {
        readProblems.push(`${c.id}: 声明 ${path} 在 minimal 里取不到`)
      }
    }
    for (const leaf of leaves) {
      // ② 探针里有、却没有任何声明覆盖 ⇒ 探针比声明宽（偷偷多读了字段）
      const covered = c.responseFieldsRead.some((p) => isPrefix(segsOf(p), leaf))
      if (!covered) readProblems.push(`${c.id}: 探针叶 ${segsKey(leaf) || '(root)'} 没被任何声明覆盖`)
    }
    // ③ 别让 `data` 这种宽前缀把②变成空转（一个宽声明就能覆盖全部叶）：
    //    只对"严格前缀了 ≥2 个探针叶"的声明报警——那正是"把整支当一个笼统声明"的形态；
    //    `data[].authority_policy`（整块透传的不透明值）只前缀 1 个叶 ⇒ 合理，不报。
    const prefixCounts = new Map()
    for (const leaf of leaves) {
      for (const p of c.responseFieldsRead) {
        const d = segsOf(p)
        if (isPrefix(d, leaf) && d.length < leaf.length) {
          prefixCounts.set(p, (prefixCounts.get(p) ?? 0) + 1)
        }
      }
    }
    const tooWide = [...prefixCounts.entries()].filter(([, n]) => n >= 2)
      .map(([p, n]) => `${p}(覆盖${n}个叶)`)
    if (tooWide.length > 0) readProblems.push(`${c.id}: 声明过宽（等于没声明）: ${tooWide.join(',')}`)
  }
  check('E4a minimal 是 response.body 的子形状（探针不许凭空造值）',
    shapeProblems.length === 0,
    shapeProblems.length === 0 ? `${CALLS.length} 条` : shapeProblems.join(' | '))
  check('E4b responseFieldsRead 与 minimal 互相覆盖（防声明与探针分叉）',
    readProblems.length === 0,
    readProblems.length === 0 ? `${CALLS.length} 条双向覆盖` : readProblems.join(' | '))

  // E4c：两次回放的结果差异必须全部落在声明的透传支下
  const unexplained = []
  const undef = []
  for (const s of SCENARIOS) {
    const a = full.outputs[s.id]; const b = minimal.outputs[s.id]
    // 抛了的场景由 E0 负责说清楚，这里比"错误对象 vs 错误对象"没有意义
    if (a?.__threw !== undefined || b?.__threw !== undefined) continue
    undef.push(...undefinedPaths(a, `${s.id}(full)`))
    undef.push(...undefinedPaths(b, `${s.id}(minimal)`))
    const allowed = CALLS.filter((c) => s.expectCalls.includes(c.id))
      .flatMap((c) => c._passthrough ?? [])
    for (const p of diffPaths(a, b, s.id)) {
      const tail = p.slice(s.id.length + 1)
      const ok = allowed.some((pre) => tail === pre || tail.startsWith(`${pre}.`) || tail.startsWith(`${pre}[`))
      if (!ok) unexplained.push(p)
    }
  }
  check('E4c 只回声明字段时结果差异全部落在 _passthrough 下（未声明依赖会被抓）',
    unexplained.length === 0,
    unexplained.length === 0 ? 'ok' : `未声明的差异: ${unexplained.slice(0, 8).join(', ')}`)
  check('E4d 结果里没有 undefined（DSH lossless 会整条判 INVALID）',
    undef.length === 0, undef.length === 0 ? 'ok' : undef.slice(0, 8).join(', '))

  // 非空交叉证：minimal 真的比 full 小（否则这条断言可能因为"探针=全量"而空转通过）
  const shrunk = CALLS.filter((c) => leafSegs(c.minimal).length < leafSegs(c.response.body).length)
  check('E4e minimal 确实比全量小（防"探针=全量"让 E4c 空转通过）',
    shrunk.length >= CALLS.length - 1,
    `${shrunk.length}/${CALLS.length} 条收窄（其余是本来就全读的）`)
}

/* ==========================================================================
 * E5：写工具的请求体纪律
 * ========================================================================== */

{
  const collectCalls = SCENARIOS.flatMap((s) => full.perScenario.get(s.id)?.observed ?? [])
    .filter((o) => o.path.endsWith('/collect'))
  const bad = collectCalls.filter((o) => o.body !== null
    && Object.prototype.hasOwnProperty.call(o.body, 'source_tier'))
  check('E5 the write tool\'s body carries no source_tier',
    collectCalls.length === 1 && bad.length === 0,
    `collect 调用=${collectCalls.length} 带 source_tier=${bad.length}`
    + `，body 键=${JSON.stringify(Object.keys(collectCalls[0]?.body ?? {}))}`)
}

/* ------------------------------------------------------------------ */

server.close()

const failed = results.filter((r) => !r.ok)
if (failed.length > 0) {
  console.error(`\nsmoke-wire-contract: ${failed.length}/${results.length} FAILED`)
  for (const f of failed) console.error(`  - ${f.name}`)
  process.exit(1)
}
console.log(`\nsmoke-wire-contract: ${results.length}/${results.length} PASS`)
