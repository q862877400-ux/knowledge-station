// prove-fix.mjs — self-contained proof that the plugin's wasm route 404 is a
// CODE DEFECT (async readdir in a sync `new Set(...)`), and that the lazy
// asynchronous readdir fix makes the same route serve 200 + application/wasm.
//
// This mirrors plugin/src/index.js registerPdfWasmRoute exactly, but in ISOLATION
// (no repo/plugin file is touched). Run: node prove-fix.mjs
import { createRequire } from 'node:module'
import { readFile, readdir } from 'node:fs/promises'
import { dirname, join } from 'node:path'
import { createServer } from 'node:http'

const KS_PDF_WASM_PATH = '/ks/assets/pdf-wasm'

// Resolve pdfjs-dist exactly as the plugin does: createRequire is rooted at the
// PLUGIN's module path (plugin/src/index.js), so require.resolve finds the
// plugin's own node_modules copy.
const PLUGIN_MODULE = 'D:/AI/work space/zcode/plugin/src/index.js'
function dirnameOfPkg() {
  const require = createRequire(PLUGIN_MODULE)
  const pkg = require.resolve('pdfjs-dist/package.json')
  return join(dirname(pkg), 'wasm')
}

// --- BUGGY replica ------------------------------------------------------
// readdirSyncSafe returns `readdir(dir)` — the PROMISE from fs/promises.
function readdirSyncSafe(dir) { return readdir(dir) }
function makeBuggyRoute() {
  let baseDir = null
  let allow = null
  try {
    baseDir = dirnameOfPkg()
    allow = new Set(readdirSyncSafe(baseDir)) // <-- TypeError: not iterable
  } catch {
    baseDir = null
    allow = null
  }
  return async (req, res) => {
    if (baseDir === null || allow === null || allow.size === 0) {
      res.writeHead(404, { 'Content-Type': 'application/json; charset=utf-8' })
      res.end(JSON.stringify({ ok: false, error: { code: 'wasm_unavailable' } }))
      return
    }
    res.writeHead(500); res.end('unreachable-buggy')
  }
}

// --- FIXED replica (recommended: lazy memoized async readdir) -----------
function makeFixedRoute() {
  let baseDir = null
  let allow = null
  let allowLoading = null
  try {
    baseDir = dirnameOfPkg()
  } catch {
    baseDir = null
  }
  return async (req, res) => {
    if (baseDir === null) {
      res.writeHead(404, { 'Content-Type': 'application/json; charset=utf-8' })
      res.end(JSON.stringify({ ok: false, error: { code: 'wasm_unavailable' } }))
      return
    }
    if (allow === null) {
      if (allowLoading === null) allowLoading = readdir(baseDir).catch(() => [])
      allow = new Set(await allowLoading)           // await unwraps -> string[] -> Set
    }
    let name = ''
    try {
      name = decodeURIComponent(new URL(req.url ?? '/', 'http://localhost').pathname).slice(KS_PDF_WASM_PATH.length + 1)
    } catch { name = '' }
    if (name.length === 0 || name.includes('/') || name.includes('..') || !allow.has(name)) {
      res.writeHead(404, { 'Content-Type': 'application/json; charset=utf-8' })
      res.end(JSON.stringify({ ok: false, error: { code: 'wasm_not_found' } }))
      return
    }
    try {
      const bytes = await readFile(join(baseDir, name))
      const type = name.endsWith('.wasm') ? 'application/wasm' : 'text/javascript; charset=utf-8'
      res.writeHead(200, { 'Content-Type': type, 'Cache-Control': 'no-store' })
      res.end(bytes)
    } catch (error) {
      res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' })
      res.end(JSON.stringify({ ok: false, error: { code: 'wasm_read_failed' } }))
    }
  }
}

// Prefix matcher equivalent to WebServer.match() (longest prefix wins).
function makeMatcher(handler) {
  return async (req, res) => {
    const pathname = new URL(req.url ?? '/', 'http://x').pathname
    const prefix = KS_PDF_WASM_PATH
    if (pathname !== prefix && !pathname.startsWith(prefix + '/')) { res.writeHead(404); res.end(); return }
    await handler(req, res)
  }
}

function listen(handler) {
  const server = createServer((req, res) => { makeMatcher(handler)(req, res) })
  return new Promise((resolve) => server.listen(0, '127.0.0.1', () => resolve(server)))
}

const url = (port, name) => `http://127.0.0.1:${port}${KS_PDF_WASM_PATH}/${name}`
async function probe(server, name) {
  const u = url(server.address().port, name)
  const r = await fetch(u)
  const buf = await r.arrayBuffer()
  return { name, status: r.status, ct: r.headers.get('content-type'), bytes: buf.byteLength }
}

async function main() {
  const buggy = await listen(makeBuggyRoute())
  const fixed = await listen(makeFixedRoute())
  const buggyRes = await probe(buggy, 'openjpeg.wasm')
  const fixedRes = await probe(fixed, 'openjpeg.wasm')
  const fixedRes2 = await probe(fixed, 'openjpeg.wasm') // second hit: memoized allow
  const fixedNoSuch = await probe(fixed, 'does-not-exist.wasm')
  console.log('BUGGY  ->', JSON.stringify(buggyRes))
  console.log('FIXED  ->', JSON.stringify(fixedRes))
  console.log('FIXED*2->', JSON.stringify(fixedRes2))
  console.log('FIXED-miss->', JSON.stringify(fixedNoSuch))
  console.log('---')
  console.log('buggy 404?', buggyRes.status === 404)
  console.log('fixed 200?', fixedRes.status === 200, '| ct =', fixedRes.ct, '| bytes =', fixedRes.bytes)
  buggy.close(); fixed.close()
}
main()
