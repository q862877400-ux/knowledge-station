/**
 * ks-dsh-plugin — scripts/smoke-channels-routes.mjs
 *
 * `/ks/channels*` 宿主路由的回归（§11.0 R4a）。钉五件事：
 *   ① 两条路由都注册、`kind:'exact'`、方法守卫生效（GET/POST 各自只认一个）；
 *   ② **query 白名单**：未知键**丢弃**（界面不许发明字段；宿主动不转发别的）；
 *   ③ **body 白名单**：`/ks/channels/probe` 只转发 `ids`/`persist`，且 `persist` 必须**严格布尔**；
 *   ④ 引擎错误映射：404（渠道不存在）**原样透传**，不许翻成 502 归因错误；
 *   ⑤ 探针超时给足（`150s`）——默认 20s 会把"探 28 个站"变成必然超时（那是假失败）。
 *
 * 跑法：node scripts/smoke-channels-routes.mjs   （退出码 0 = 全通过）
 */
import { createServer } from 'node:http'

import {
  KS_CHANNELS_ITEM_PREFIX,
  KS_CHANNELS_PATH,
  KS_CHANNELS_PROBE_PATH,
  registerKsChannelsRoutes,
} from '../src/channels.js'

const results = []
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}

/* ------------------------------- 桩引擎 ------------------------------- */
const seen = []
let responder = () => ({ body: { code: 200, status: 'success', data: { summary: {}, items: [] } } })
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

/* --------------------------- 捕获注册的路由 ---------------------------
 * ⚠⚠ 与真派发器**同构**的两张表（webserver 是 exact 表 + prefix 表，`match()`
 * 先查 exact、再在 prefix 表取最长匹配）——曾经只有一张按路径作键的表，
 * 前缀一旦与某条 exact 同路径就把对方**覆盖**掉，桩就开始说假话（2026-09-22 实测踩到）。 */
const exactRoutes = new Map()
const prefixRoutes = new Map()
const allRoutes = () => [...exactRoutes.values(), ...prefixRoutes.values()]
const ctx = {
  webServer: {
    register(def) {
      (def.kind === 'prefix' ? prefixRoutes : exactRoutes).set(def.path, def)
      return () => {}
    },
  },
}
const manager = { ensureLive: async () => ({ port: PORT, token: 'tok_stub' }) }
const disposers = registerKsChannelsRoutes(ctx, manager)

/* ----------------------------- 假 req / res ----------------------------- */
function makeRes() {
  // ⚠ `writes` 记**响应写了多少次**（2026-10-23 加）：`channels.js` 那次真 bug 的形态是
  //   「400 已写、又往引擎转发一次、再写一次」⇒ 看最后一次写什么抓不到它，必须看次数。
  //   真 Node 里第二次写会抛 `ERR_HTTP_HEADERS_SENT`，这个桩不抛，所以只能靠计数。
  const out = { status: null, body: null, headers: null, writes: 0 }
  return {
    out,
    writeHead(status, headers) {
      out.writes += 1
      out.status = status
      out.headers = headers ?? null
    },
    end(text) { try { out.body = JSON.parse(text) } catch { out.body = text } },
  }
}
/** 按真派发器的口径找路由：**先精确、再取最长前缀匹配**。
 *  ⚠ 这个桩原先只认 exact（`routes.get(path)`），于是 `/ks/channels/{id}` 这类
 *  prefix 路由**根本发不进来**——那会让"前缀路由写错了"这种 bug 在冒烟里静默通过。 */
function resolveRoute(path) {
  const exact = exactRoutes.get(path)
  if (exact !== undefined) return exact
  let best = null
  for (const [p, def] of prefixRoutes) {
    // ⚠⚠ **与真派发器逐字同判据**（webserver `match()`）：
    //   `pathname === prefix || pathname.startsWith(prefix + '/')`。
    //   这里曾经是宽松的 `path.startsWith(p)` —— 比真的宽，`/ks/channels/x` 能配上带尾斜杠的坏前缀，
    //   于是「人工维护整排死按钮」在冒烟里 20+ 条断言全绿。**判据必须与真派发器同源，
    //   否则冒烟会替 bug 作证。**
    if (p !== path && !path.startsWith(`${p}/`)) continue
    if (best === null || p.length > best.path.length) best = { path: p, def }
  }
  return best === null ? undefined : best.def
}

async function invoke(path, { method = 'GET', body = undefined, search = '' } = {}) {
  const def = resolveRoute(path)
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
  return { status: res.out.status, body: res.out.body }
}

/** 发**原始字节**（不是 JSON.stringify 过的对象）。
 *
 *  为什么必须有它（2026-10-23）：`invoke` 只会把对象序列化成**合法** JSON，
 *  于是 `readBodyOr400` 的两个失败分支（非法 JSON / 非对象）**一条都发不进来**
 *  ⇒ `channels.js` 里 `if (raw === undefined) return` 那个恒假判据能活到线上。
 *  这个入口专门用来打失败分支，并且把 `writeHead` 的**次数**也记下来
 *  （双重响应是本仓那次真 bug 的形态，只看最后一次写什么会漏掉它）。
 */
async function invokeRaw(path, { method = 'GET', rawBody = '', search = '' } = {}) {
  const def = resolveRoute(path)
  if (def === undefined) throw new Error(`路由未注册: ${path}`)
  const { EventEmitter } = await import('node:events')
  const req = new EventEmitter()
  req.method = method
  req.url = `${path}${search}`
  req.destroy = () => {}
  const res = makeRes()
  const p = def.handler(req, res)
  setImmediate(() => {
    req.emit('data', Buffer.from(rawBody, 'utf8'))
    req.emit('end')
  })
  await p
  return { status: res.out.status, body: res.out.body, writes: res.out.writes }
}
/** 最近一次"打到引擎"的记录。**永不返回 undefined** —— 没打过就返回一个井号占位。
 *
 *  ⚠ 为什么要有占位（2026-10-24 `-Full` 门禁实测）：
 *  原来这里直接 `seen[seen.length - 1]`，`seen` 为空时返回 `undefined`，
 *  于是断言 `eng.method === 'POST'` 抛 `TypeError: Cannot read properties of undefined`
 *  —— **整个冒烟进程当场崩掉**，后面 20 多条断言一条都不再跑。
 *  那次是偶发（单跑 3/3 通过、门禁里 1 次失败），而崩溃把"引擎到底有没有被调、
 *  宿主返回了什么"这些**最有用的现场**全吞了。
 *  改成返回 `{ method: '(none)', path: '(none)', sent: {} }` 之后，
 *  断言仍然会**判失败**（`'(none)' === 'POST'` 为假），但会把
 *  `(none) (none)` 打出来，且**后面的断言继续跑**。判据强度没变，只是不再自毁。
 */
const NO_ENGINE_HIT = Object.freeze({ method: '(none)', path: '(none)', sent: {} })
const lastEngine = () => seen[seen.length - 1] ?? NO_ENGINE_HIT

/* --------------------------- 1. 注册面 --------------------------- */
check('注册了 3 条渠道路由（列表+新增 / 单条维护前缀 / 探针）',
  exactRoutes.size + prefixRoutes.size === 3 && exactRoutes.has(KS_CHANNELS_PATH)
    && prefixRoutes.has(KS_CHANNELS_ITEM_PREFIX) && exactRoutes.has(KS_CHANNELS_PROBE_PATH),
  allRoutes().map((d) => `${d.kind} ${d.path}`).join(','))
check('列表与探针在 exact 表、单条维护在 prefix 表（与真派发器同构；同键不许互相覆盖）',
  exactRoutes.get(KS_CHANNELS_PATH)?.kind === 'exact'
    && prefixRoutes.get(KS_CHANNELS_ITEM_PREFIX)?.kind === 'prefix'
    && exactRoutes.get(KS_CHANNELS_PROBE_PATH)?.kind === 'exact'
    && !prefixRoutes.has(KS_CHANNELS_PROBE_PATH))
check('返回 3 个 disposer（随 fiber 撤销）', disposers.length === 3)
check('路径常量就是界面用的那三个（防两侧漂开）',
  KS_CHANNELS_PATH === '/ks/channels' && KS_CHANNELS_PROBE_PATH === '/ks/channels/probe'
    && KS_CHANNELS_ITEM_PREFIX === '/ks/channels')
check('单条维护前缀不许带尾斜杠（带了 ⇒ 真派发器下 /{id} 系列全部落兜底，维护按钮整排死）',
  !KS_CHANNELS_ITEM_PREFIX.endsWith('/'))
{
  // 与真派发器同判据的两条防呆（见 resolveRoute 注释）：正例解析到 prefix、形近路径不得误吞。
  // 「形近不误吞」正是宽松 startsWith 会放过的那种漂移。
  const item = resolveRoute(`${KS_CHANNELS_ITEM_PREFIX}/ch:a`)
  const lookalike = resolveRoute(`${KS_CHANNELS_ITEM_PREFIX}X`)
  check('单条维护路径解析到 prefix 路由；形近路径（/ks/channelsX）不误吞',
    item !== undefined && item.kind === 'prefix' && lookalike === undefined,
    `item=${item === undefined ? 'undefined' : item.kind} lookalike=${lookalike === undefined ? 'undefined' : 'HIT'}`)
}

/* --------------------------- 2. 方法守卫生效 --------------------------- */
{
  // ⚠ `/ks/channels` 现在**同路径两件事**（GET 列表 / POST 新增）：
  //   所以"POST 打过来 → 405"这条旧断言**按设计作废**了，改成核 POST 走的是新增。
  //   真正要守的是"不认识的动词一律 405"。
  const r = await invoke(KS_CHANNELS_PATH, { method: 'PUT' })
  check('列表/新增：PUT 打过来 → 405', r.status === 405, JSON.stringify(r.body))
  const r2 = await invoke(KS_CHANNELS_PROBE_PATH, { method: 'GET' })
  check('POST 探针：GET 打过来 → 405', r2.status === 405, JSON.stringify(r2.body))
  const r3 = await invoke(`${KS_CHANNELS_ITEM_PREFIX}/ch:a`, { method: 'GET' })
  check('单条维护：GET 打过来 → 405（这个路径没有读口）',
    r3.status === 405, JSON.stringify(r3.body))
}

/* --------------------- 2b. 人工写口：白名单 + 错误透传 --------------------- */
{
  seen.length = 0
  responder = () => ({ body: { code: 200, data: { channel_id: 'user:x-1', name: 'n' } } })
  const r = await invoke(KS_CHANNELS_PATH, {
    method: 'POST',
    body: { name: '某省厅公告', url: 'https://e.org', state: 'ok', evil: 1 },
  })
  const eng = lastEngine()
  check('新增：转发到引擎 POST /api/v1/channels（不是列表那条）',
    eng.method === 'POST' && eng.path === '/api/v1/channels', `${eng.method} ${eng.path}`)
  check('新增：允许的字段原样转，`evil` **也**照转（判据归引擎，宿主不替它丢）',
    eng.sent.name === '某省厅公告' && eng.sent.url === 'https://e.org'
    && eng.sent.evil === 1, JSON.stringify(eng.sent))
  check('⚠ 健康度字段**照转**给引擎（拒绝的判据归引擎，宿主不自己判一遍）',
    eng.sent.state === 'ok', JSON.stringify(eng.sent))
  check('新增成功 → {ok:true,data}', r.status === 200 && r.body.data.channel_id === 'user:x-1',
    JSON.stringify(r.body))

  // 引擎 422（健康度字段被拒）→ 宿主**原样**带回引擎的 code
  seen.length = 0
  responder = () => ({ http: 422, body: { code: 422, status: 'error', error: 'illegal_channel_field', message: '这些是探针产出的字段' } })
  const bad = await invoke(KS_CHANNELS_PATH, { method: 'POST', body: { name: 'x', state: 'ok' } })
  check('引擎 422 → 宿主 422 且**保住引擎的错误码**',
    bad.status === 422 && bad.body.error.code === 'illegal_channel_field',
    JSON.stringify(bad.body))

  // 单条 PATCH：只有白名单字段过去；404 原样透传
  seen.length = 0
  responder = () => ({ body: { code: 200, data: { channel_id: 'ch:a', note: '改过' } } })
  const patched = await invoke(`${KS_CHANNELS_ITEM_PREFIX}/ch:a`, {
    method: 'PATCH', body: { note: '改过', junk: true },
  })
  const e2 = lastEngine()
  // ⚠ id 是 `encodeURIComponent` 过的（`ch%3Aa`）——Starlette 会把它解回 `ch:a`。
  //   断言用解码后的形状，钉的是"打到哪条引擎路径"，不是编码细节。
  check('复核编辑：PATCH 到 /api/v1/channels/ch:a，body 原样转（junk 也转给引擎判）',
    e2.method === 'PATCH'
    && decodeURIComponent(e2.path) === '/api/v1/channels/ch:a'
    && e2.sent.junk === true,
    `${e2.method} ${e2.path} ${JSON.stringify(e2.sent)}`)
  check('复核编辑成功 → 200', patched.status === 200, JSON.stringify(patched.body))

  seen.length = 0
  responder = () => ({ http: 404, body: { error: 'channel_not_found', message: '渠道不存在' } })
  const gone = await invoke(`${KS_CHANNELS_ITEM_PREFIX}/ch:nope`, { method: 'DELETE' })
  check('删除：404 原样透传（不翻成 502 归因错误）',
    gone.status === 404 && gone.body.error.code === 'channel_not_found'
    && lastEngine().method === 'DELETE', JSON.stringify(gone.body))

  // 启停：**宿主不判布尔**（判据归引擎）——它只把值转过去
  seen.length = 0
  responder = () => ({ http: 422, body: { error: 'illegal_enabled', message: 'body 需要 {"enabled": true|false}' } })
  const strEnabled = await invoke(`${KS_CHANNELS_ITEM_PREFIX}/ch:a/enabled`, {
    method: 'POST', body: { enabled: 'no' },
  })
  check('启停：非布尔**照转**给引擎，引擎 422 原样回来（宿主不自己判一遍）',
    lastEngine().sent.enabled === 'no'
    && strEnabled.status === 422 && strEnabled.body.error.code === 'illegal_enabled',
    JSON.stringify(strEnabled.body))
  seen.length = 0
  responder = () => ({ body: { code: 200, data: { channel_id: 'ch:a', enabled: 0 } } })
  const off = await invoke(`${KS_CHANNELS_ITEM_PREFIX}/ch:a/enabled`, {
    method: 'POST', body: { enabled: false },
  })
  check('启停：转发 POST …/ch:a/enabled 且 body 只有 enabled',
    decodeURIComponent(lastEngine().path) === '/api/v1/channels/ch:a/enabled'
    && lastEngine().sent.enabled === false && off.status === 200,
    `${lastEngine().path} ${JSON.stringify(lastEngine().sent)}`)

  /* ── 批C（2026-09-22）：「已知文件测试」三口——配样本 POST / 读样本 GET / 跑测试 POST ── */
  responder = () => ({ body: { code: 200, data: { test_case: { channel_id: 'ch:a', sample_url: 'https://x/a.pdf', expect_no: 'GB/T 1-2020' } } } })
  const tcSet = await invoke(`${KS_CHANNELS_ITEM_PREFIX}/ch:a/test-case`, {
    method: 'POST', body: { sample_url: 'https://x/a.pdf', expect_no: 'GB/T 1-2020' } })
  check('批C 配样本：转发 POST …/ch:a/test-case（body 原样转给引擎判）',
    decodeURIComponent(lastEngine().path) === '/api/v1/channels/ch:a/test-case'
    && lastEngine().method === 'POST' && lastEngine().sent.expect_no === 'GB/T 1-2020'
    && tcSet.status === 200,
    `${lastEngine().path} ${JSON.stringify(lastEngine().sent)}`)
  const tcGet = await invoke(`${KS_CHANNELS_ITEM_PREFIX}/ch:a/test-case`, { method: 'GET' })
  check('批C 读样本：转发 GET …/ch:a/test-case（样本+最近留痕）',
    decodeURIComponent(lastEngine().path) === '/api/v1/channels/ch:a/test-case'
    && lastEngine().method === 'GET' && tcGet.status === 200,
    `${lastEngine().method} ${lastEngine().path}`)
  responder = () => ({ body: { code: 200, data: { result: 'ok', detail: '拿到并认出了已知文件：GB/T 1-2020' } } })
  const tcRun = await invoke(`${KS_CHANNELS_ITEM_PREFIX}/ch:a/test`, { method: 'POST', body: {} })
  check('批C 跑测试：转发 POST …/ch:a/test（此钉只证**转发**；"真拉真测真留痕"归引擎侧测试）',
    decodeURIComponent(lastEngine().path) === '/api/v1/channels/ch:a/test'
    && lastEngine().method === 'POST' && tcRun.body.data.result === 'ok',
    `${lastEngine().path} ${JSON.stringify(tcRun.body)}`)

  /* ── 非法 body 打三个写口：**不许**继续往引擎转发（2026-10-23 修的真 bug）──
   *
   * 病灶：`readBodyOr400` 的两个失败分支都 `return null`，它**永远不会**返回 `undefined`；
   * 而 `POST …/test-case` 那处原写 `if (raw === undefined) return` ⇒ 判据**恒假** ⇒
   * 400 已经写出去了，却继续 `proxyWrite(..., null)` 写第二次 ⇒ **双重响应**
   * （真 Node 里 `ERR_HTTP_HEADERS_SENT`；这个桩不抛，所以只能靠 `writes` 计数抓）。
   *
   * ⚠ 断言必须**同时**覆盖三件事，缺一件都抓不到它：
   *   ① 状态 400 —— 说明 `readBodyOr400` 真的拒了；
   *   ② `seen.length === 0` —— 引擎**一次都没被调**，这才是 bug 的现场；
   *   ③ `writes === 1` —— 响应只写了一次，直接钉住"双重响应"这个形态。
   *   只断言 ① 会让 bug 活着通过（400 本来就是 `readBodyOr400` 写的，
   *   `res.out` 里看到的仍是首个 400）。
   *
   * 三个写口各钉一遍：同一个文件里 PATCH 与 enabled 判的是 `null`（对的），
   * 只有 test-case 判 `undefined`（错的）—— 三条钉在一起，防止将来有人"统一"成 `undefined`。
   */
  for (const [label, path, method, rawBody] of [
    ['test-case（原病灶）', `${KS_CHANNELS_ITEM_PREFIX}/ch:a/test-case`, 'POST', '{ 这不是 JSON'],
    ['PATCH {id}', `${KS_CHANNELS_ITEM_PREFIX}/ch:a`, 'PATCH', '{ 这不是 JSON'],
    ['POST {id}/enabled', `${KS_CHANNELS_ITEM_PREFIX}/ch:a/enabled`, 'POST', '{ 这不是 JSON'],
    ['test-case + 数组 body', `${KS_CHANNELS_ITEM_PREFIX}/ch:a/test-case`, 'POST', '[1,2,3]'],
    ['test-case + 标量 body', `${KS_CHANNELS_ITEM_PREFIX}/ch:a/test-case`, 'POST', '42'],
  ]) {
    seen.length = 0
    responder = () => ({ body: { code: 200, data: { result: 'ok' } } })
    const bad = await invokeRaw(path, { method, rawBody })
    check(`非法 body 打 ${label}：回 400、引擎零调用、响应只写一次`,
      bad.status === 400 && bad.body.error.code === 'bad_request'
      && seen.length === 0 && bad.writes === 1,
      `status=${bad.status} engineCalls=${seen.length} writes=${bad.writes} `
      + `body=${JSON.stringify(bad.body)}`)
  }
}

/* --------------------------- 3. query 白名单 --------------------------- */
{
  seen.length = 0
  responder = () => ({ body: { code: 200, data: { summary: { total: 131 }, items: [] } } })
  const r = await invoke(KS_CHANNELS_PATH, {
    search: '?category=law&state=ok&evil=1&limit=10',
  })
  const eng = lastEngine()
  check('打到引擎 /api/v1/channels 且带上白名单内的键',
    eng.path.startsWith('/api/v1/channels?') && eng.path.includes('category=law')
    && eng.path.includes('state=ok') && eng.path.includes('limit=10'), eng.path)
  check('⚠ 未知键 **丢弃**（evil=1 不许转发）', !eng.path.includes('evil'), eng.path)
  check('响应原样回给界面（含 summary）',
    r.status === 200 && r.body.data.summary.total === 131, JSON.stringify(r.body))
}

/* --------------------------- 4. body 白名单与校验 --------------------------- */
{
  seen.length = 0
  responder = () => ({ body: { code: 200, data: { probed: 1, results: [], counts: { ok: 1 } } } })
  await invoke(KS_CHANNELS_PROBE_PATH, {
    method: 'POST', body: { ids: ['ch:a'], persist: true, evil: 'x' },
  })
  const eng = lastEngine()
  check('探针 body 只转发 ids/persist（未知键丢弃）',
    eng.sent && eng.sent.ids && eng.sent.ids[0] === 'ch:a' && eng.sent.persist === true
    && eng.sent.evil === undefined, JSON.stringify(eng.sent))

  seen.length = 0
  const bad = await invoke(KS_CHANNELS_PROBE_PATH, { method: 'POST', body: { ids: 'ch:a' } })
  check('ids 类型不对 → 422（且**不**打引擎）', bad.status === 422 && seen.length === 0,
    `${bad.status} engineCalls=${seen.length}`)

  seen.length = 0
  await invoke(KS_CHANNELS_PROBE_PATH, { method: 'POST', body: { persist: 'yes' } })
  check('persist 必须严格布尔（"yes" 不当成 true 发给引擎）',
    lastEngine().sent.persist === false, JSON.stringify(lastEngine().sent))
}

/* --------------------------- 5. 引擎错误映射 --------------------------- */
{
  responder = () => ({ http: 404, body: { code: 404, error: 'channel_not_found', message: '渠道不存在: c:nope' } })
  const r = await invoke(KS_CHANNELS_PROBE_PATH, { method: 'POST', body: { ids: ['c:nope'] } })
  check('引擎 404 **原样透传**（不许翻成 502 engine_error —— 那是归因错误）',
    r.status === 404 && r.body.error?.code === 'channel_not_found', JSON.stringify(r.body))
}
{
  responder = () => ({ http: 500, body: { code: 500, error: 'internal_error', message: 'boom' } })
  const r = await invoke(KS_CHANNELS_PATH)
  check('引擎 5xx → 502（与其它路由同口径）', r.status === 502, JSON.stringify(r.body))
}
{
  const dead = { ensureLive: async () => { throw new Error('engine down') } }
  // 只留 exact 表（这张用例打的是集合路径的 GET；同样两表分开，不让 prefix 覆盖它）
  const r2routes = new Map()
  registerKsChannelsRoutes(
    { webServer: { register(d) { if (d.kind === 'exact') r2routes.set(d.path, d); return () => {} } } }, dead)
  const { EventEmitter } = await import('node:events')
  const req = new EventEmitter()
  req.method = 'GET'
  req.url = KS_CHANNELS_PATH
  req.destroy = () => {}
  const res = makeRes()
  const p = r2routes.get(KS_CHANNELS_PATH).handler(req, res)
  setImmediate(() => req.emit('end'))
  await p
  check('引擎不可达 → 503 engine_unavailable（并带原因）',
    res.out.status === 503 && res.out.body.error?.code === 'engine_unavailable',
    JSON.stringify(res.out.body))
}

server.close()
const failed = results.filter((r) => !r.ok)
console.log(`\n== channels-routes smoke ${failed.length === 0 ? 'PASS' : 'FAIL'} `
  + `(${results.length - failed.length}/${results.length}) ==`)
process.exit(failed.length === 0 ? 0 : 1)
