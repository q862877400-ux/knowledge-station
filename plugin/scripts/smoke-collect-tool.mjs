/**
 * ks-dsh-plugin — scripts/smoke-collect-tool.mjs
 *
 * 模型侧**采集**工具 `ks_collect`（Phase C-6）的宿主侧回归。
 *
 * ## 这一层要钉的不是"能不能抓"
 * 抓的能力在引擎（`harvest.collect_url`，已有自己的 Python 测试）。这一层钉的是**权限与
 * 措辞**——它们错了不会报错，只会让模型以为"我采到了证据"或"我能自己批准"：
 *   ① 目标项目**不猜**：会话绑定优先、冲突报错、两者都没有则报错（且**不打扰引擎**）；
 *   ② **绝不发 `source_tier`**（采集者不得自 claim 可信度；schema 里也不许有这个键）；
 *   ③ 抓取失败是**结果**（collected:false + 原因），不是"已经采到了"；
 *   ④ 回执必须如实说"**待评审、T3=仅线索、不能代批**"；
 *   ⑤ 信封异常（200 无 data / 404）必须**抛**，不得伪装成"采到了"或"没采到"。
 *
 * 跑法：node scripts/smoke-collect-tool.mjs   （退出码 0 = 全通过）
 */

import { createServer } from 'node:http'

import { makeCollectTool, MAX_COLLECT_PER_SESSION } from '../src/collect.js'

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
    seen.push({ method: req.method, path: req.url, auth: req.headers.authorization ?? null, sent })
    const r = responder(req.url)
    res.writeHead(r.http ?? 200, { 'content-type': 'application/json' })
    res.end(JSON.stringify(r.body ?? r))
  })
})
await new Promise((r) => server.listen(0, '127.0.0.1', r))
const PORT = server.address().port

const fakeManager = { ensureLive: async () => ({ port: PORT, token: 'tok_stub' }) }
const baseMode = {
  forensic: true, bookmarksOnly: false, folderId: null, folderName: null,
  materialProjectId: null, materialProjectName: null, source: 'session',
}
/** 造工具（`chatModeOf` 用固定值替换，模拟 host 的会话级真值）。 */
const toolWith = (mode) => makeCollectTool(fakeManager, () => mode)
let _sessSeq = 0
/**
 * 调一次工具。⚠ **每次给一个新的 session id**：采集工具带**会话级暂定上限**，
 * 用同一个 id 会让各条用例互相累加计数（本文件第一版就是这样，跑到后面因"超限"变红）。
 * 上限本身另有专门用例。
 */
const call = (args, mode = baseMode, sessionId = `sess-${_sessSeq += 1}`) =>
  toolWith(mode).execute(args, {
    signal: new AbortController().signal,
    agent: { session: { id: sessionId } },
  })

/* --------------------------- 1. 工具契约 --------------------------- */

{
  const tool = toolWith(baseMode)
  check('工具名是 ks_collect', tool.name === 'ks_collect', tool.name)
  check('url 是必填参数',
    Array.isArray(tool.parameters.required) && tool.parameters.required.join(',') === 'url')
  check('**schema 里没有 source_tier**（采集者不得自 claim 可信度）',
    !Object.prototype.hasOwnProperty.call(tool.parameters.properties, 'source_tier')
    && !JSON.stringify(tool.parameters).includes('source_tier'),
    Object.keys(tool.parameters.properties).join(','))
  check('描述写明"不能批准"',
    tool.description.includes('不能批准') && tool.description.includes('用户'))
  check('描述写明采到的是"仅线索、不得单独支撑结论"',
    tool.description.includes('仅线索') && tool.description.includes('不得单独支撑结论'))
  check('描述要求优先原始出处',
    tool.description.includes('原始出处'))
}

/* --------------------------- 2. 目标项目不猜 --------------------------- */

{
  seen.length = 0
  let threw = null
  try { await call({ url: 'https://a.example/x' }) } catch (e) { threw = e }
  check('未绑定且未给 project_id → 报错且**不打扰引擎**',
    threw !== null && String(threw.message).includes('没有目标项目') && seen.length === 0,
    `${String(threw?.message).slice(0, 40)} engineCalls=${seen.length}`)

  seen.length = 0
  let conflict = null
  try {
    await call({ url: 'https://a.example/x', project_id: 'prj_other' },
      { ...baseMode, materialProjectId: 'prj_bound' })
  } catch (e) { conflict = e }
  check('显式 project_id 与绑定冲突 → 报错且**不打扰引擎**（不偷偷换项目）',
    conflict !== null && String(conflict.message).includes('不一致') && seen.length === 0,
    `engineCalls=${seen.length}`)

  seen.length = 0
  let blank = null
  try { await call({ url: '   ' }) } catch (e) { blank = e }
  check('空 url → 报错且不打扰引擎',
    blank !== null && String(blank.message).includes('url') && seen.length === 0,
    `engineCalls=${seen.length}`)

  // 绑定存在时用绑定的那个（模型不给 project_id）
  seen.length = 0
  responder = () => ({
    body: { code: 200, data: { collected: true, material: { material_id: 'mat_1' } } },
  })
  await call({ url: 'https://a.example/x' },
    { ...baseMode, materialProjectId: 'prj_bound' })
  check('绑定存在时打到**绑定**的项目',
    seen[0].path === '/api/v1/materials/projects/prj_bound/collect', seen[0]?.path)

  // 显式给了同一个：允许（不算冲突）
  seen.length = 0
  await call({ url: 'https://a.example/x', project_id: 'prj_bound' },
    { ...baseMode, materialProjectId: 'prj_bound' })
  check('显式 project_id 与绑定**相同**时放行', seen[0].path.endsWith('/prj_bound/collect'),
    seen[0]?.path)

  // 未绑定但显式给了：允许（模型用 ks_materials 查到的 id）
  seen.length = 0
  await call({ url: 'https://a.example/x', project_id: 'prj_a/b?x=1' })
  check('未绑定时用显式 project_id，且被 URL 编码',
    seen[0].path === '/api/v1/materials/projects/prj_a%2Fb%3Fx%3D1/collect', seen[0]?.path)
}

/* --------------------------- 3. 请求体形状 --------------------------- */

{
  seen.length = 0
  responder = () => ({
    body: { code: 200, data: { collected: true, material: { material_id: 'mat_1' } } },
  })
  await call({ url: '  https://a.example/x  ', title: '标题', note: '' },
    { ...baseMode, materialProjectId: 'prj_a' })
  const sent = seen[0].sent
  check('POST + Bearer token',
    seen[0].method === 'POST' && seen[0].auth === 'Bearer tok_stub',
    `${seen[0].method} ${seen[0].auth}`)
  check('url 去空白后原样发出', sent.url === 'https://a.example/x', JSON.stringify(sent))
  check('空串 note 归 null（不发含混的空值）', sent.note === null, JSON.stringify(sent))
  check('**请求体里没有 source_tier**（引擎端点会 422，这里连试都不试）',
    !Object.prototype.hasOwnProperty.call(sent, 'source_tier'), JSON.stringify(sent))

  seen.length = 0
  await call({ url: 'https://a.example/x' }, { ...baseMode, materialProjectId: 'prj_a' })
  check('省略 title/note 时显式发 null（而不是漏字段）',
    'title' in seen[0].sent && 'note' in seen[0].sent
    && seen[0].sent.title === null && seen[0].sent.note === null, JSON.stringify(seen[0].sent))
}

/* --------------------------- 4. 成功回执的措辞 --------------------------- */

{
  responder = () => ({
    body: {
      code: 200, status: 'success',
      data: {
        collected: true, status: 200, truncated: false, duplicate: false,
        material: {
          material_id: 'mat_9', title: '某通知', review_status: 'pending',
          source_tier: 'T3', origin: 'collected', lifecycle: 'ephemeral',
          url: 'https://a.example/x', domain: 'a.example',
          tier_reason: '自采：HTTP 200 来自 a.example',
          content_hash: 'SHOULD_NOT_APPEAR', raw_path: 'D:\\secret\\x.html',
        },
      },
    },
  })
  const out = await call({ url: 'https://a.example/x' },
    { ...baseMode, materialProjectId: 'prj_a' })
  check('collected=true 且原样带出 review_status/轴 A',
    out.collected === true && out.material.review_status === 'pending'
    && out.material.source_tier === 'T3', JSON.stringify(out.material))
  check('hint 说明**待评审、不会进结论、不能代批**',
    typeof out.hint === 'string' && out.hint.includes('待评审')
    && out.hint.includes('仅线索') && out.hint.includes('不能代批'), out.hint)
  const dumped = JSON.stringify(out)
  check('不透出 content_hash / raw_path 等内部字段',
    !dumped.includes('SHOULD_NOT_APPEAR') && !dumped.includes('secret'), dumped.slice(0, 120))

  responder = () => ({
    body: {
      code: 200, data: {
        collected: true, duplicate: true, material: { material_id: 'mat_1' },
      },
    },
  })
  const dup = await call({ url: 'https://a.example/x' },
    { ...baseMode, materialProjectId: 'prj_a' })
  check('dup 回执说明"内容与已有的一份相同、没有重复登记"',
    dup.duplicate === true && dup.hint.includes('相同'), dup.hint)
}

/* --------------------------- 5. 抓取失败：结果而非异常 --------------------------- */

{
  seen.length = 0
  responder = () => ({
    body: {
      code: 200, status: 'success',
      data: { collected: false, status: 403, reason: 'URL 被 SSRF 纪律拒绝（仅 http/https 且禁内网/保留地址）' },
    },
  })
  const out = await call({ url: 'http://127.0.0.1:9/x' },
    { ...baseMode, materialProjectId: 'prj_a' })
  check('抓取失败回 collected:false + 原因（**不抛**，让模型能换来源）',
    out.ok === true && out.collected === false && String(out.reason).includes('SSRF'),
    JSON.stringify(out))
  check('失败 hint 明确"没有登记成材料、不要算作已获取的证据"',
    out.hint.includes('没有') && out.hint.includes('不要把它算作已获取的证据'), out.hint)
  check('失败回执不带 material（不给模型任何"已经有这条"的错觉）',
    out.material === undefined, JSON.stringify(out.material))
}

/* --------------------------- 6. 信封异常不伪装 --------------------------- */

{
  responder = () => ({ body: { code: 200, status: 'success' } })   // 无 data
  let threw = null
  try {
    await call({ url: 'https://a.example/x' }, { ...baseMode, materialProjectId: 'prj_a' })
  } catch (e) { threw = e }
  check('200 但信封缺 data → 抛错（不伪装成"已经采到了"）',
    threw !== null && String(threw.message).includes('响应异常'), String(threw?.message))

  responder = () => ({ http: 404, body: { code: 404, status: 'error', error: 'not_found' } })
  let threw2 = null
  try {
    await call({ url: 'https://a.example/x' }, { ...baseMode, materialProjectId: 'prj_a' })
  } catch (e) { threw2 = e }
  check('404（旧引擎未加载路由）→ 抛错并建议 ks_ping',
    threw2 !== null && String(threw2.message).includes('ks_ping'), String(threw2?.message))

  // ⚠ **`data` 里没有 `collected` 字段 ≠ "没采到"**（2026-09-17 复核的 MEDIUM）：
  // 那是**信封/版本**问题，而引擎可能**已经登记了**一条 pending 材料 ⇒ 必须**抛**，
  // 不能回 `collected:false` 让模型对用户说"没采到"（可能是一句假话）。
  // 本文件原先钉的正是**相反**的行为（复核按文档加抛后冒烟变红，M7 RED）——已改正。
  responder = () => ({ body: { code: 200, data: { reason: 'x' } } })
  let missing = null
  try {
    await call({ url: 'https://a.example/x' }, { ...baseMode, materialProjectId: 'prj_a' },
      'sess-missing-collected')
  } catch (e) { missing = e }
  check('data 缺 `collected` 字段 ⇒ **抛**（不谎报成"没采到"）',
    missing !== null && String(missing.message).includes('形状不认识'),
    String(missing?.message).slice(0, 60))

  // 合法的"抓取失败"：**有** `collected:false` ⇒ 如实回报（不抛）
  responder = () => ({
    body: { code: 200, data: { collected: false, status: 404, reason: 'HTTP 404' } },
  })
  const legitFail = await call({ url: 'https://a.example/x' },
    { ...baseMode, materialProjectId: 'prj_a' }, 'sess-legit-fail')
  check('合法的抓取失败（`collected:false` + reason）⇒ 如实回报，不抛',
    legitFail.ok === true && legitFail.collected === false
    && legitFail.reason === 'HTTP 404', JSON.stringify(legitFail))

  // 硬塞 `source_tier` 必须响亮拒绝（schema 里没有该键，但绕过 schema 是现实路径）
  let injected = null
  try {
    await call({ url: 'https://a.example/x', source_tier: 'T0' },
      { ...baseMode, materialProjectId: 'prj_a' }, 'sess-inject-tier')
  } catch (e) { injected = e }
  check('硬塞 source_tier ⇒ 响亮拒绝（不静默忽略）',
    injected !== null && String(injected.message).includes('source_tier'),
    String(injected?.message).slice(0, 50))

  check('暂定上限的**数值**有钉子（改成 1e6 会让这条红，逼着决定被显式做出来）',
    MAX_COLLECT_PER_SESSION === 20, String(MAX_COLLECT_PER_SESSION))
}

/* --------------------------- 7. 会话级刹车（暂定上限） --------------------------- */

{
  const mode = { ...baseMode, materialProjectId: 'prj_a' }
  responder = () => ({
    body: { code: 200, data: { collected: true, material: { material_id: 'mat_x' } } },
  })
  const sess = 'sess-cap'
  let last = null
  for (let i = 0; i < MAX_COLLECT_PER_SESSION; i += 1) {
    last = await call({ url: `https://a.example/${i}` }, mode, sess)
  }
  check('回执里带上"本会话已采/上限"（让节奏看得见）',
    last.session_collected === MAX_COLLECT_PER_SESSION
    && last.session_limit === MAX_COLLECT_PER_SESSION,
    `used=${last.session_collected} limit=${last.session_limit}`)

  seen.length = 0
  let over = null
  try { await call({ url: 'https://a.example/over' }, mode, sess) } catch (e) { over = e }
  check('超出暂定上限 → 响亮报错且**不打扰引擎**',
    over !== null && String(over.message).includes('上限') && seen.length === 0,
    `${String(over?.message).slice(0, 36)} engineCalls=${seen.length}`)
  check('超限的报错点明"暂定上限 + 由用户决定"，并**显式禁止**两种错误读法',
    over !== null && String(over.message).includes('暂定')
    && String(over.message).includes('告诉用户')
    && String(over.message).includes('不要**把它当成'),
    String(over?.message).slice(0, 70))

  // 另一个会话不受这个会话的计数影响（上限是**会话级**，不是全局停机）
  const other = await call({ url: 'https://a.example/other' }, mode, 'sess-other')
  check('上限是会话级：另一个会话照样能采', other.collected === true
    && other.session_collected === 1, JSON.stringify(other.session_collected))

  // 计数按"发起的采集请求"算：抓取失败也计入（刹车宁可多算不可少算）
  responder = () => ({ body: { code: 200, data: { collected: false, reason: 'x' } } })
  const failedOnce = await call({ url: 'https://a.example/y' }, mode, 'sess-count')
  check('抓取失败也计入会话计数（刹车宁可多算）',
    failedOnce.session_collected === 1, String(failedOnce.session_collected))
}

/* ------------------------------------------------------------------ */

server.close()

const failed = results.filter((r) => !r.ok)
if (failed.length > 0) {
  console.error(`\nsmoke-collect-tool: ${failed.length}/${results.length} FAILED`)
  for (const f of failed) console.error(`  - ${f.name}`)
  process.exit(1)
}
console.log(`\nsmoke-collect-tool: ${results.length}/${results.length} PASS`)
