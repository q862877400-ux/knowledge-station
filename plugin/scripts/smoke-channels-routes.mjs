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

/* --------------------------- 捕获注册的路由 --------------------------- */
const routes = new Map()
const ctx = { webServer: { register(def) { routes.set(def.path, def); return () => {} } } }
const manager = { ensureLive: async () => ({ port: PORT, token: 'tok_stub' }) }
const disposers = registerKsChannelsRoutes(ctx, manager)

/* ----------------------------- 假 req / res ----------------------------- */
function makeRes() {
  const out = { status: null, body: null, headers: null }
  return {
    out,
    writeHead(status, headers) { out.status = status; out.headers = headers ?? null },
    end(text) { try { out.body = JSON.parse(text) } catch { out.body = text } },
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
  return { status: res.out.status, body: res.out.body }
}
const lastEngine = () => seen[seen.length - 1]

/* --------------------------- 1. 注册面 --------------------------- */
check('注册了 2 条渠道路由（列表 + 探针）',
  routes.size === 2 && routes.has(KS_CHANNELS_PATH) && routes.has(KS_CHANNELS_PROBE_PATH),
  [...routes.keys()].join(','))
check('两条都是 kind=exact（前缀匹配会把 /ks/channelsX 也吃进来）',
  [...routes.values()].every((d) => d.kind === 'exact'))
check('返回 2 个 disposer（随 fiber 撤销）', disposers.length === 2)
check('路径常量就是界面用的那两个（防两侧漂开）',
  KS_CHANNELS_PATH === '/ks/channels' && KS_CHANNELS_PROBE_PATH === '/ks/channels/probe')

/* --------------------------- 2. 方法守卫生效 --------------------------- */
{
  const r = await invoke(KS_CHANNELS_PATH, { method: 'POST' })
  check('GET 列表：POST 打过来 → 405', r.status === 405, JSON.stringify(r.body))
  const r2 = await invoke(KS_CHANNELS_PROBE_PATH, { method: 'GET' })
  check('POST 探针：GET 打过来 → 405', r2.status === 405, JSON.stringify(r2.body))
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
  const r2routes = new Map()
  registerKsChannelsRoutes(
    { webServer: { register(d) { r2routes.set(d.path, d); return () => {} } } }, dead)
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
