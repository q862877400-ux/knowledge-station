/**
 * ks-dsh-plugin — scripts/smoke-ingest.mjs
 *
 * Host-side smoke for the R27 入库预览 proxy routes（`src/ingest.js`）。
 *
 * 判据（每条都要求"可证 FAIL"，不做恒真断言）：
 *   1. 方法闸：三条路由对错误 method 一律 405；
 *   2. 请求体闸：非 JSON → 400 bad_json、超限 → 400 body_too_large；
 *   3. **白名单**：`allow_deep` / 未知字段**不得**被转发给引擎（预览零外发在代理层的护栏）、
 *      `path`/`doc_type` 必须逐字段转发；
 *   4. 引擎错误码透传：引擎 422 → 400、404 → 404、5xx/异常 → 502/503（不许把 422 说成 500）；
 *   5. 目录兜底：引擎不可用时 `GET /ks/ingest/inbox` 仍返回 host 侧列表（degraded 标记），
 *      且只列 .pdf；
 *   6. 默认「待入库」目录：`GET /ks/ingest/inbox-default` 幂等创建并回传绝对路径；
 *   7. batch 参数校验：负 sample / 负 limit_files / 空 paths → 400。
 *
 * 引擎用 `globalThis.fetch` 打桩（health 透传真引擎会让 ensureLive 起引擎，不值得为 smoke 拉起），
 * manager 也用桩：`ensureLive()` 返回固定 session。
 *
 * Run:  node scripts/smoke-ingest.mjs     (exit 0 = all cases pass)
 */

import { EventEmitter } from 'node:events'
import { mkdtemp, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

import {
  KS_INGEST_BATCH_PATH,
  KS_INGEST_INBOX_DEFAULT_PATH,
  KS_INGEST_INBOX_PATH,
  KS_INGEST_PREVIEW_PATH,
  defaultInboxDir,
  registerKsIngestRoutes,
} from '../src/ingest.js'

const results = []
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}

/** Fake IncomingMessage: real EventEmitter so readJsonBody() can stream it. */
function fakeReq({ method = 'GET', url, body = '' } = {}) {
  const req = new EventEmitter()
  req.method = method
  req.headers = {}
  req.url = url
  req.destroy = () => {}
  process.nextTick(() => {
    if (body) req.emit('data', Buffer.from(body, 'utf8'))
    req.emit('end')
  })
  return req
}

function fakeRes() {
  return {
    status: 0,
    body: null,
    writeHead(status) { this.status = status },
    end(text) {
      try { this.body = text ? JSON.parse(text) : null } catch { this.body = text }
    },
  }
}

function captureRoutes() {
  const byPath = new Map()
  const ctx = {
    webServer: {
      register(route) {
        byPath.set(route.path, route.handler)
        return () => byPath.delete(route.path)
      },
    },
  }
  const manager = {
    ensureLive: async () => ({ port: 65001, token: 'smoke-token' }),
  }
  const dispose = registerKsIngestRoutes(ctx, manager)
  return { byPath, dispose }
}

const { byPath, dispose } = captureRoutes()

/** 调一次真实 handler。 */
async function call(path, { method = 'GET', url, body } = {}) {
  const res = fakeRes()
  await byPath.get(path)(fakeReq({ method, url: url ?? path, body }), res)
  return res
}

// --------------------------------------------------------------------------- #
// 引擎打桩：记录每一次请求，按 scenario 返回预设响应
// --------------------------------------------------------------------------- #
const realFetch = globalThis.fetch
const seen = []
let scenario = () => ({ status: 200, body: { code: 200, status: 'success', data: { stub: true } } })

globalThis.fetch = async (url, init = {}) => {
  const u = String(url)
  const bodyText = typeof init.body === 'string' ? init.body : ''
  seen.push({ url: u, method: init.method ?? 'GET', body: bodyText })
  if (u.includes('/api/v1/health')) {
    return new Response(JSON.stringify({ status: 'healthy' }), {
      status: 200, headers: { 'Content-Type': 'application/json' },
    })
  }
  const s = scenario(u)
  return new Response(JSON.stringify(s.body), {
    status: s.status, headers: { 'Content-Type': 'application/json' },
  })
}

const inboxDir = await mkdtemp(join(tmpdir(), 'ks-ingest-smoke-'))
await writeFile(join(inboxDir, 'a.pdf'), '%PDF-1.4 fake')
await writeFile(join(inboxDir, 'b.PDF'), '%PDF-1.4 fake')
await writeFile(join(inboxDir, 'note.txt'), 'not a pdf')

console.log('=== ks-dsh-plugin ingest-preview host-route smoke ===\n')

// ---------------------------------------------------------------- 1) 方法闸
for (const [path, want] of [
  [KS_INGEST_PREVIEW_PATH, 'POST'], [KS_INGEST_BATCH_PATH, 'POST'],
]) {
  const r = await call(path, { method: 'GET' })
  check(`${path} rejects ${'GET'} with 405`, r.status === 405 && r.body?.error?.code === 'method_not_allowed',
    `${r.status} ${JSON.stringify(r.body)}`)
  check(`${path} advertises ${want} only`, String(r.body?.error?.message).includes(want),
    r.body?.error?.message)
}
const rInboxPost = await call(KS_INGEST_INBOX_PATH, { method: 'POST' })
check('GET-only inbox rejects POST with 405', rInboxPost.status === 405,
  `${rInboxPost.status}`)
const rDefPost = await call(KS_INGEST_INBOX_DEFAULT_PATH, { method: 'POST' })
check('GET-only inbox-default rejects POST with 405', rDefPost.status === 405,
  `${rDefPost.status}`)

// ---------------------------------------------------------------- 2) 请求体闸
const rBadJson = await call(KS_INGEST_PREVIEW_PATH, { method: 'POST', body: '{not json' })
check('preview rejects malformed JSON with 400 bad_json',
  rBadJson.status === 400 && rBadJson.body?.error?.code === 'bad_json',
  `${rBadJson.status} ${JSON.stringify(rBadJson.body)}`)

const rNoPath = await call(KS_INGEST_PREVIEW_PATH, { method: 'POST', body: '{}' })
check('preview without path is 400 missing_path',
  rNoPath.status === 400 && rNoPath.body?.error?.code === 'missing_path',
  `${rNoPath.status} ${JSON.stringify(rNoPath.body)}`)

const huge = JSON.stringify({ path: 'x'.repeat(70_000) })
const rHuge = await call(KS_INGEST_PREVIEW_PATH, { method: 'POST', body: huge })
check('preview rejects oversized body with 400 body_too_large',
  rHuge.status === 400 && rHuge.body?.error?.code === 'body_too_large',
  `${rHuge.status} ${JSON.stringify(rHuge.body)}`)

// ---------------------------------------------------------------- 3) 白名单转发
seen.length = 0
scenario = () => ({
  status: 200, body: { code: 200, status: 'success', data: { verdict: 'warn', grade: 'C' } },
})
const rOk = await call(KS_INGEST_PREVIEW_PATH, {
  method: 'POST',
  body: JSON.stringify({
    path: 'C:/x/a.pdf', doc_type: 'standard',
    allow_deep: true, deep_fallback: true, evil: 'nope', __proto__: { x: 1 },
  }),
})
const forwarded = seen.find((s) => s.url.includes('/api/v1/ingest/preview'))
const sentBody = forwarded ? JSON.parse(forwarded.body) : {}
check('preview happy path returns 200 + data', rOk.status === 200 && rOk.body?.data?.verdict === 'warn',
  `${rOk.status} ${JSON.stringify(rOk.body)}`)
check('preview forwards path + doc_type verbatim',
  sentBody.path === 'C:/x/a.pdf' && sentBody.doc_type === 'standard', JSON.stringify(sentBody))
check('preview DROPS allow_deep / deep_fallback / unknown keys (zero-egress guard)',
  !('allow_deep' in sentBody) && !('deep_fallback' in sentBody) && !('evil' in sentBody)
  && Object.keys(sentBody).sort().join(',') === 'doc_type,path', JSON.stringify(sentBody))

seen.length = 0
const rBatch = await call(KS_INGEST_BATCH_PATH, {
  method: 'POST',
  body: JSON.stringify({ dir: inboxDir, sample: 2, limit_files: 10, doc_type: 'standard',
    allow_deep: true, junk: 1 }),
})
const batchSent = JSON.parse(seen.find((s) => s.url.includes('/api/v1/ingest/preview/batch')).body)
check('batch happy path returns 200', rBatch.status === 200, `${rBatch.status}`)
check('batch forwards dir/sample/limit_files/doc_type only',
  batchSent.dir === inboxDir && batchSent.sample === 2 && batchSent.limit_files === 10
  && batchSent.doc_type === 'standard'
  && Object.keys(batchSent).sort().join(',') === 'dir,doc_type,limit_files,sample',
  JSON.stringify(batchSent))

// ---------------------------------------------------------------- 4) batch 参数校验
for (const [label, body, code] of [
  ['negative sample', { dir: inboxDir, sample: -1 }, 'bad_sample'],
  ['non-integer sample', { dir: inboxDir, sample: 1.5 }, 'bad_sample'],
  ['negative limit_files', { dir: inboxDir, limit_files: -3 }, 'bad_limit'],
  ['empty paths array', { paths: [] }, null],
]) {
  const r = await call(KS_INGEST_BATCH_PATH, { method: 'POST', body: JSON.stringify(body) })
  if (code === null) {
    check(`batch rejects ${label} (falls back to default inbox, not a 400)`,
      r.status === 200, `${r.status}`)
  } else {
    check(`batch rejects ${label} with 400 ${code}`,
      r.status === 400 && r.body?.error?.code === code, `${r.status} ${JSON.stringify(r.body)}`)
  }
}
const rBadPaths = await call(KS_INGEST_BATCH_PATH, {
  method: 'POST', body: JSON.stringify({ paths: [1, 2] }),
})
check('batch rejects non-string paths with 400 bad_paths',
  rBadPaths.status === 400 && rBadPaths.body?.error?.code === 'bad_paths',
  `${rBadPaths.status} ${JSON.stringify(rBadPaths.body)}`)

// ---------------------------------------------------------------- 5) 引擎错误码透传
scenario = () => ({ status: 422, body: { code: 422, error: 'preview_unsupported_type', message: '不是 PDF' } })
const r422 = await call(KS_INGEST_PREVIEW_PATH, { method: 'POST', body: JSON.stringify({ path: 'x' }) })
check('engine 422 maps to same-origin 400 keeping the engine code',
  r422.status === 400 && r422.body?.error?.code === 'preview_unsupported_type',
  `${r422.status} ${JSON.stringify(r422.body)}`)

scenario = () => ({ status: 404, body: { code: 404, error: 'preview_file_not_found', message: 'no' } })
const r404 = await call(KS_INGEST_PREVIEW_PATH, { method: 'POST', body: JSON.stringify({ path: 'x' }) })
check('engine 404 maps to same-origin 404', r404.status === 404 && r404.body?.error?.code === 'preview_file_not_found',
  `${r404.status} ${JSON.stringify(r404.body)}`)

scenario = () => ({ status: 500, body: { code: 500, error: 'internal_error', message: 'boom' } })
const r500 = await call(KS_INGEST_PREVIEW_PATH, { method: 'POST', body: JSON.stringify({ path: 'x' }) })
check('engine 5xx maps to 502 engine-side failure', r500.status === 502,
  `${r500.status} ${JSON.stringify(r500.body)}`)

// ---------------------------------------------------------------- 6) inbox 兜底
scenario = () => ({ status: 200, body: { code: 200, status: 'success',
  data: { dir: inboxDir, count: 2, files: [{ file_name: 'a.pdf' }] } } })
const rInboxOk = await call(KS_INGEST_INBOX_PATH, { url: `${KS_INGEST_INBOX_PATH}?dir=${encodeURIComponent(inboxDir)}` })
check('inbox proxies the engine listing when available',
  rInboxOk.status === 200 && rInboxOk.body?.data?.count === 2 && !rInboxOk.body?.degraded,
  `${rInboxOk.status} ${JSON.stringify(rInboxOk.body)}`)

scenario = () => ({ status: 503, body: { code: 503, error: 'engine_unavailable', message: 'down' } })
const rInboxDeg = await call(KS_INGEST_INBOX_PATH, { url: `${KS_INGEST_INBOX_PATH}?dir=${encodeURIComponent(inboxDir)}` })
check('inbox degrades to a host-side listing when the engine is down',
  rInboxDeg.status === 200 && rInboxDeg.body?.degraded === 'engine_unavailable'
  && rInboxDeg.body?.data?.count === 2
  && rInboxDeg.body.data.files.every((f) => f.file_name.toLowerCase().endsWith('.pdf')),
  `${rInboxDeg.status} ${JSON.stringify(rInboxDeg.body?.data?.count)}`)
check('host-side listing is sorted and excludes non-PDF',
  rInboxDeg.body?.data?.files?.map((f) => f.file_name).join(',') === 'a.pdf,b.PDF',
  rInboxDeg.body?.data?.files?.map((f) => f.file_name).join(','))

// ---------------------------------------------------------------- 7) 默认待入库目录
const rDef = await call(KS_INGEST_INBOX_DEFAULT_PATH)
check('inbox-default returns the absolute default dir',
  rDef.status === 200 && typeof rDef.body?.data?.dir === 'string'
  && rDef.body.data.dir === defaultInboxDir(),
  `${rDef.status} ${JSON.stringify(rDef.body?.data)}`)
const rDef2 = await call(KS_INGEST_INBOX_DEFAULT_PATH)
check('inbox-default is idempotent', rDef2.status === 200 && rDef2.body?.data?.dir === rDef.body?.data?.dir)

// ---------------------------------------------------------------- 8) 卸载不泄漏
const before = byPath.size
dispose()
check('dispose removes every ingest route', byPath.size === before - 4, `${before} -> ${byPath.size}`)

globalThis.fetch = realFetch

const failed = results.filter((r) => !r.ok)
console.log(`\n== ingest smoke ${failed.length === 0 ? 'PASS' : 'FAIL'} (${results.length - failed.length}/${results.length}) ==`)
if (failed.length > 0) {
  for (const f of failed) console.log(`FAILED: ${f.name}`)
  process.exitCode = 1
}
