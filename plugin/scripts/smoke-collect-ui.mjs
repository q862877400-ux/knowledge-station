/**
 * ks-dsh-plugin — scripts/smoke-collect-ui.mjs
 *
 * **客户端侧自采接线**的契约冒烟（Phase D-3）。
 *
 * ## 为什么单独一条（而不是只加字符串断言）
 * `smoke-client-entry.mjs` 只能证明"产物里有某句文案"——它**抓不到**请求契约漂移：
 *   · `project_id` 从 query 挪到 body（主机侧读 query ⇒ 400 缺 project_id）；
 *   · 多发了 `source_tier`（主机**响亮拒绝**，界面按钮直接不可用）；
 *   · 把"没采到（collected:false）"当成异常抛（用户看到红字，而引擎的本意是
 *     **如实报告原因给人看**）；
 *   · 信封缺 `collected` 时**不抛**（把"信封坏了"渲染成"没采到"——本战役栽过同款）。
 * 本冒烟用**替身 fetch** 把真实请求截下来验，并把四种响应形状逐一喂回去。
 *
 * 用法：node scripts/smoke-collect-ui.mjs   （退出码 0 = 全通过）
 */
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

import { build } from 'esbuild'

const here = dirname(fileURLToPath(import.meta.url))
const pluginRoot = resolve(here, '..')

const results = []
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}

/* ---------------------------------------------------- 打包 client/api.ts
 * `api.ts` **没有 import**（只依赖浏览器全局 fetch），所以可以单独打进来直接调。
 */
const tmp = await mkdtemp(join(tmpdir(), 'ks-collect-ui-'))
const outPath = join(tmp, 'api.bundle.mjs')
await build({
  entryPoints: [join(pluginRoot, 'client', 'api.ts')],
  bundle: true, platform: 'node', format: 'esm', outfile: outPath,
  absWorkingDir: pluginRoot, loader: { '.tsx': 'tsx', '.ts': 'ts' },
  logLevel: 'warning',
})
const api = await import(pathToFileURL(outPath).href)

/* ---------------------------------------------------- 替身 fetch */
let calls = []
let nextResponse = null
globalThis.fetch = async (url, init) => {
  calls.push({ url: String(url), init: init ?? {} })
  if (nextResponse === null) throw new Error('（冒烟未设置响应）')
  return nextResponse
}

function jsonRes(body, { status = 200, ok = true } = {}) {
  return { ok, status, async json() { return body } }
}
/** 引擎/主机的成功信封（`ksJson` 认 `ok:true` + `data`）。 */
const envelope = (data) => jsonRes({ ok: true, data })

const PROJ = 'prj_smoke_collect'
const URL1 = 'https://openstd.example/GB10146-2015'

/* ---------------------------------------------------- 1. 请求契约 */
{
  calls = []
  nextResponse = envelope({ collected: true, status: 200, material: { title: 'T' } })
  await api.collectMaterialUrl(PROJ, { url: `  ${URL1}  ` })
  const [c] = calls
  check('打到主机的自采路由（路径逐字）',
    c.url === `/ks/materials/collect?project_id=${PROJ}`, c.url)
  check('方法 POST', c.init.method === 'POST', String(c.init.method))
  check('声明 JSON 请求/接受',
    c.init.headers['content-type'] === 'application/json'
      && c.init.headers.accept === 'application/json',
    JSON.stringify(c.init.headers))
  const body = JSON.parse(c.init.body)
  check('body 只有 url（标题/备注为空时**不发**空串）',
    JSON.stringify(Object.keys(body).sort()) === '["url"]', JSON.stringify(body))
  check('⚠ 绝不发 source_tier（采集者不得自 claim 可信度）',
    !('source_tier' in body) && !('tier' in body) && !('sourceTier' in body),
    JSON.stringify(body))
  check('url **不做 trim**（原样交给引擎/主机去判，界面只挡空串）',
    body.url === `  ${URL1}  `, JSON.stringify(body.url))
}

/* ---------------------------------------------------- 2. 给了标题/备注 */
{
  calls = []
  nextResponse = envelope({ collected: true, material: {} })
  await api.collectMaterialUrl(PROJ, { url: URL1, title: '某标准', note: '用户自采' })
  const body = JSON.parse(calls[0].init.body)
  check('标题/备注非空时**照发**（评审人要看得到"这条是怎么来的"）',
    body.title === '某标准' && body.note === '用户自采' && body.url === URL1,
    JSON.stringify(body))
  check('仍然只有白名单那四个键的**子集**（主机对未知键一律 400）',
    Object.keys(body).every((k) => ['url', 'title', 'note', 'published_at'].includes(k)),
    JSON.stringify(Object.keys(body)))
}

/* ---------------------------------------------------- 3. 成功形状 */
{
  nextResponse = envelope({
    collected: true, status: 200, truncated: true, duplicate: false,
    material: { material_id: 'mat_1', title: '某标准', review_status: 'pending',
                source_tier: 'T3', chunk_count: 7 },
  })
  const out = await api.collectMaterialUrl(PROJ, { url: URL1 })
  check('成功：collected/truncated/material 原样带出（界面据此如实说"被截断"）',
    out.collected === true && out.truncated === true
      && out.material?.review_status === 'pending' && out.material?.chunk_count === 7,
    JSON.stringify(out))
}

/* ---------------------------------------------------- 4. "没采到"不是异常 */
{
  nextResponse = envelope({ collected: false, status: 404, reason: '抓取失败：HTTP 404' })
  let threw = null
  let out = null
  try { out = await api.collectMaterialUrl(PROJ, { url: URL1 }) } catch (err) { threw = err }
  check('没采到 ⇒ **正常返回**（不抛）：引擎刻意用 200+collected:false 表达它',
    threw === null && out?.collected === false, threw === null ? 'returned' : String(threw))
  check('原因与 HTTP 状态**都带出来**（要显示给人看）',
    out?.reason === '抓取失败：HTTP 404' && out?.status === 404, JSON.stringify(out))
}

/* ---------------------------------------------------- 5. 坏信封必须抛 */
{
  nextResponse = envelope({ status: 200 })
  let msg = ''
  try { await api.collectMaterialUrl(PROJ, { url: URL1 }) } catch (err) { msg = String(err?.message ?? err) }
  check('信封缺 collected ⇒ **抛**（不谎报成"没采到"）',
    msg.includes('缺少 collected'), msg)

  nextResponse = jsonRes({ ok: true }, { status: 200 })
  msg = ''
  try { await api.collectMaterialUrl(PROJ, { url: URL1 }) } catch (err) { msg = String(err?.message ?? err) }
  check('data 缺失 ⇒ 抛（`ok:true` 但没 data 不算成功）', msg !== '', msg)

  nextResponse = jsonRes({ error: { code: 'engine_error', message: '引擎未运行' } },
    { status: 502, ok: false })
  msg = ''
  try { await api.collectMaterialUrl(PROJ, { url: URL1 }) } catch (err) { msg = String(err?.message ?? err) }
  check('HTTP 非 2xx ⇒ 抛并带出引擎的 message（不吞成"没采到"）',
    msg.includes('引擎未运行'), msg)
}

await rm(tmp, { recursive: true, force: true })

const failed = results.filter((r) => !r.ok)
console.log(`\n== collect-ui smoke ${failed.length === 0 ? 'PASS' : 'FAIL'} `
  + `(${results.length - failed.length}/${results.length}) ==`)
process.exit(failed.length === 0 ? 0 : 1)
