/**
 * ks-dsh-plugin — scripts/smoke-docimage.mjs
 *
 * 端点接线冒烟（2026-09-13）：/ks/doc-image 代理（src/docimage.js）。
 *
 * 覆盖面（全部纯逻辑 / fake webServer + fake manager，不 spawn 真引擎）：
 *
 *  1. parseDocImagePath 三形态解析（figure / formula?clause / table-image）
 *     —— 非法形态（缺 clause、非数字 page、未知 kind、越界段数）→ null
 *  2. 路由注册 + 信任栅栏：guardWebServer 门面下 handler 可达（与 apply() 同款接线）
 *  3. 引擎 404 透传：占位隐藏契约（前端隐藏，不是 5xx）
 *  4. 引擎 200 PNG：字节 + Content-Type + X-Frac-* 逐字透传
 *  5. 引擎 401×2 → 502（会话轮换重试一次后仍失败）
 *  6. 非 GET → 405；非法路径 → 400
 *  7. dpi 钳制（72~300；非法默认 144）
 *
 * Run: node scripts/smoke-docimage.mjs   (exit 0 = pass)
 */

import { EventEmitter } from 'node:events'

const { parseDocImagePath, registerKsDocImageRoutes, KS_DOC_IMAGE_PATH } =
  await import(new URL('../src/docimage.js', import.meta.url).href)
const { guardWebServer } = await import(new URL('../src/trust.js', import.meta.url).href)
const { apiGetBytes } = await import(new URL('../src/engine.js', import.meta.url).href)

const results = []
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}

/* ============================================== 1. parseDocImagePath */
{
  const q = (s) => new URLSearchParams(s)
  check('figure 形态解析',
    parseDocImagePath('doc1/figure/A.1', q(''))?.enginePath
      === '/api/v1/documents/doc1/figure/A.1')
  check('formula 形态解析（clause 必带）',
    parseDocImagePath('doc1/formula/3', q('clause=5.2.1'))?.enginePath
      === '/api/v1/documents/doc1/formula/3?clause=5.2.1')
  check('formula 缺 clause → null',
    parseDocImagePath('doc1/formula/3', q('')) === null)
  check('table-image 形态解析（数字段校验）',
    parseDocImagePath('doc1/table-image/6/0', q(''))?.enginePath
      === '/api/v1/documents/doc1/table-image/6/0')
  check('table-image 非数字页 → null',
    parseDocImagePath('doc1/table-image/abc/0', q('')) === null)
  check('table-image 非数字 idx → null',
    parseDocImagePath('doc1/table-image/6/x', q('')) === null)
  check('未知 kind → null', parseDocImagePath('doc1/asset/9', q('')) === null)
  check('越界段数（figure 多段）→ null', parseDocImagePath('doc1/figure/1/2', q('')) === null)
  check('空路径 → null', parseDocImagePath('', q('')) === null)
  // doc_id 与编号段 encodeURIComponent（防注入穿越）。
  check('特殊字符编码（doc id）',
    parseDocImagePath('a b/figure/图1', q(''))?.enginePath
      === '/api/v1/documents/a%20b/figure/%E5%9B%BE1')
}

/* ============================================== 2-6. 路由 handler（栅栏 + 代理行为） */

/** fake IncomingMessage（真实 EventEmitter，流式 body 可空）。 */
function fakeReq({ method = 'GET', url = KS_DOC_IMAGE_PATH + '/doc1/figure/1', headers = {} } = {}) {
  const req = new EventEmitter()
  req.method = method
  req.headers = headers
  req.url = url
  req.destroy = () => {}
  process.nextTick(() => req.emit('end'))
  return req
}

/** fake ServerResponse：收集 status/headers/body（Buffer 或 JSON）。 */
function fakeRes() {
  return {
    status: 0,
    headers: {},
    body: null,
    writeHead(status, headers = {}) { this.status = status; this.headers = headers },
    end(data) {
      this.body = data === undefined ? null
        : Buffer.isBuffer(data) ? data : Buffer.from(data)
    },
  }
}

/**
 * fake manager：ensureLive 指向受控 stub；拦截全局 fetch 让 apiGetBytes 命中我们的
 * 假引擎响应（PNG bytes / 404 / 401），从而测到真实代理转发链。
 */
function makeHarness(engineReply, { auth401Twice = false } = {}) {
  const seen = []
  let sessionCounter = 0
  const manager = {
    async ensureLive() {
      sessionCounter += 1
      return { port: 9000 + sessionCounter, pid: 1, token: `tok-${sessionCounter}`, spawnedByUs: true }
    },
  }
  const calls = []
  const origFetch = globalThis.fetch
  globalThis.fetch = async (url, init) => {
    calls.push({ url: String(url), headers: init?.headers ?? {} })
    const reply = engineReply(seen.length)
    seen.push(reply)
    return {
      status: reply.status,
      ok: reply.status === 200,
      headers: {
        get(name) {
          const k = name.toLowerCase()
          if (k === 'content-type') return reply.contentType ?? null
          if (reply.frac !== undefined && k === 'x-frac-x0') return String(reply.frac[0])
          if (reply.frac !== undefined && k === 'x-frac-w') return String(reply.frac[1])
          if (reply.frac !== undefined && k === 'x-frac-h') return String(reply.frac[2])
          return null
        },
      },
      arrayBuffer: async () => reply.bytes ?? new ArrayBuffer(0),
    }
  }
  const restore = () => { globalThis.fetch = origFetch }
  return { manager, calls, restore }
}

// 栅栏门面（与 apply() 同款）——handler 经 guardWebServer 才是生产路径。
function makeCtx(manager, trustOpts = {}) {
  const routes = []
  const webServer = {
    register(route) {
      routes.push(route)
      return () => { routes.splice(routes.indexOf(route), 1) }
    },
  }
  const ctx = { webServer: guardWebServer(webServer, trustOpts) }
  const dispose = registerKsDocImageRoutes(ctx, manager)
  return { routes, dispose }
}

const LOOPBACK_HEADERS = { host: '127.0.0.1:3080', origin: 'http://127.0.0.1:3080' }

/* ---- 3+4. 引擎 200 PNG / 404 透传 ---- */
{
  const png = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 1, 2, 3])
  const h = makeHarness((i) => (i === 0
    ? { status: 200, contentType: 'image/png', bytes: png.buffer.slice(png.byteOffset, png.byteOffset + png.length), frac: [0.1, 0.5, 0.2] }
    : { status: 404 }))
  const { routes, dispose } = makeCtx(h.manager)
  const handler = routes[0].handler
  const res1 = fakeRes()
  await handler(fakeReq({ headers: LOOPBACK_HEADERS, url: KS_DOC_IMAGE_PATH + '/doc1/figure/2?dpi=999' }), res1)
  check('200 PNG：字节逐字透传', res1.status === 200 && Buffer.compare(res1.body, png) === 0)
  check('200 PNG：Content-Type 透传', res1.headers['Content-Type'] === 'image/png')
  check('200 PNG：X-Frac-* 透传',
    res1.headers['X-Frac-X0'] === '0.1' && res1.headers['X-Frac-W'] === '0.5'
    && res1.headers['X-Frac-H'] === '0.2')
  check('200 PNG：Content-Length 一致', Number(res1.headers['Content-Length']) === png.length)
  check('dpi 钳制 999→300', h.calls[0].url.includes('dpi=300'))
  check('Bearer 交给引擎（token 不出 host 面）',
    h.calls[0].headers.Authorization === 'Bearer tok-1')

  const res404 = fakeRes()
  await handler(fakeReq({ headers: LOOPBACK_HEADERS, url: KS_DOC_IMAGE_PATH + '/doc1/figure/9' }), res404)
  check('引擎 404 → 404 状态码透传 + 本地信封（占位隐藏契约）', res404.status === 404
    && JSON.parse(res404.body.toString('utf8')).error.code === 'ks_image_not_found')

  dispose()
  h.restore()
}

/* ---- 5. 401×2 → 502（会话轮换重试一次） ---- */
{
  const h = makeHarness(() => ({ status: 401, contentType: 'application/json' }))
  const { routes, dispose } = makeCtx(h.manager)
  const res = fakeRes()
  await routes[0].handler(fakeReq({ headers: LOOPBACK_HEADERS, url: KS_DOC_IMAGE_PATH + '/doc1/formula/3?clause=5.2' }), res)
  check('401×2 → 502 ks_engine_auth', res.status === 502
    && JSON.parse(res.body.toString('utf8')).error.code === 'ks_engine_auth')
  check('401 重试恰好两次（ensureLive 两次 + fetch 两次）', h.calls.length === 2)
  dispose()
  h.restore()
}

/* ---- 6. 方法/路径守卫 ---- */
{
  const h = makeHarness(() => ({ status: 200, contentType: 'image/png' }))
  const { routes, dispose } = makeCtx(h.manager)
  const res405 = fakeRes()
  await routes[0].handler(fakeReq({ method: 'POST', headers: LOOPBACK_HEADERS, url: KS_DOC_IMAGE_PATH + '/doc1/figure/1' }), res405)
  check('POST → 405', res405.status === 405)
  const res400 = fakeRes()
  await routes[0].handler(fakeReq({ headers: LOOPBACK_HEADERS, url: KS_DOC_IMAGE_PATH + '/doc1/unknown/1' }), res400)
  check('非法 kind → 400', res400.status === 400)
  // HEAD → 200 只发头（Content-Length 有、无 body）。
  const resHead = fakeRes()
  await routes[0].handler(fakeReq({ method: 'HEAD', headers: LOOPBACK_HEADERS, url: KS_DOC_IMAGE_PATH + '/doc1/figure/1' }), resHead)
  check('HEAD → 200 无 body（预热可用）', resHead.status === 200 && resHead.body === null)
  dispose()
  h.restore()
}

/* ---- 7. 信任栅栏：非回环 Origin → 拒绝（复用 trust.js 语义） ---- */
{
  const h = makeHarness(() => ({ status: 200, contentType: 'image/png' }))
  const { routes, dispose } = makeCtx(h.manager)
  const res = fakeRes()
  await routes[0].handler(fakeReq({
    headers: { host: 'evil.example.com:3080' },
    url: KS_DOC_IMAGE_PATH + '/doc1/figure/1',
  }), res)
  check('非可信 Host → 栅栏拒绝（不触引擎）', res.status !== 200 && h.calls.length === 0,
    `status=${res.status} engineCalls=${h.calls.length}`)
  dispose()
  h.restore()
}

/* ---- apiGetBytes 契约自检（非 JSON 头 + 字节保真） ---- */
{
  const png = Buffer.from([1, 2, 3, 4])
  const origFetch = globalThis.fetch
  globalThis.fetch = async () => ({
    status: 200, ok: true,
    headers: { get: (n) => (n.toLowerCase() === 'content-type' ? 'image/png' : null) },
    arrayBuffer: async () => png.buffer.slice(png.byteOffset, png.byteOffset + png.length),
  })
  const got = await apiGetBytes('http://127.0.0.1:1', '/x', { token: 't' })
  globalThis.fetch = origFetch
  check('apiGetBytes 字节保真（不走 text() 腐蚀）',
    got.status === 200 && Buffer.from(got.bytes).equals(png)
    && got.headers['content-type'] === 'image/png')
}

const failed = results.filter((r) => !r.ok)
if (failed.length > 0) {
  console.error(`\nsmoke-docimage: ${failed.length}/${results.length} FAILED`)
  process.exit(1)
}
console.log(`\nsmoke-docimage: ${results.length}/${results.length} PASS`)
