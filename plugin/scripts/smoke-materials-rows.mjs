/**
 * ks-dsh-plugin — scripts/smoke-materials-rows.mjs
 *
 * 备料**行级行为**冒烟（S3-b2，2026-09-22）：挂载 KsMaterialsPanel（jsdom + react-dom/client，
 * 照 smoke-turn-tab 的 M6 段惯用法；jsdom 从 DSH 检出引——本仓不装 jsdom）。钉五件事：
 *   ① 两行真渲染（.ks-mat-row 类名钩子）；
 *   ② **免评审行无批准钮**（人工上传 origin=user：没步骤就没按钮）+「人工上传：免评审」说明在；
 *     自采行（collected）批准/拒绝都在（硬门只管自采）；
 *   ③ 地位胶囊词随 task_role（未声明首点 → 必须遵守）；
 *   ④ **点胶囊真发** POST /ks/materials/role（台账核 body.role）；
 *   ⑤ 勾两行 ⇒ 批量条**文案逐字** +「批量设为仅供参考」真逐项发 role（恰 2 条）+ 取消选择清条。
 *
 * 用法：node scripts/smoke-materials-rows.mjs   （退出码 0 = 全通过）
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

let React, renderToStaticMarkupUnused
try {
  React = await import('react')
} catch (err) {
  console.error(`根 node_modules 缺少 react：${err && err.message ? err.message : String(err)}`)
  process.exit(1)
}

const tmp = await mkdtemp(join(tmpdir(), 'ks-mat-rows-'))
const outfile = join(pluginRoot, '.materials-rows.smoke.mjs')
await build({
  entryPoints: [join(pluginRoot, 'client', 'KsMaterialsPanel.tsx')],
  bundle: true, platform: 'node', format: 'esm', outfile,
  absWorkingDir: pluginRoot, loader: { '.tsx': 'tsx', '.ts': 'ts' },
  external: ['react', 'react-dom', 'react/jsx-runtime', 'pdfjs-dist'],
  logLevel: 'warning',
})
const mod = await import(pathToFileURL(outfile).href)
await rm(outfile, { force: true })

const { KsMaterialsPanel } = mod
check('导出齐：KsMaterialsPanel', typeof KsMaterialsPanel === 'function')

/* ── jsdom 真挂载 + fetch 桩（路径照 api.ts 真路由；请求进台账） ── */
const harness = process.env.KS_HARNESS_DIR ?? 'D:\\AI\\DSH\\deepseek-harness'
const jsdomDir = join(harness, 'node_modules', 'jsdom')
const { JSDOM } = await import(pathToFileURL(join(jsdomDir, 'lib', 'api.js')).href)
const dom = new JSDOM('<!doctype html><html><body><div id="root"></div></body></html>')
const saved = { document: globalThis.document, window: globalThis.window, fetch: globalThis.fetch }
globalThis.document = dom.window.document
globalThis.window = dom.window

const calls = []
const MAT_UP = {
  material_id: 'mat_up', project_id: 'prj_1', title: '人工上传的制度.pdf', origin: 'user',
  kind: 'legal', review_status: 'approved', source_tier: 'T1', tier_label: 'T1 用户自有原件',
  tier_source: 'system', task_role: null, chunk_count: 3,
}
const MAT_COL = {
  material_id: 'mat_col', project_id: 'prj_1', title: '抓来的网页正文', origin: 'collected',
  kind: 'legal', review_status: 'pending', source_tier: 'T3', tier_label: 'T3 未核来源',
  tier_source: 'system', task_role: 'criterion', chunk_count: 1,
}
globalThis.fetch = async (input, init = {}) => {
  const url = String(input)
  const method = String((init && init.method) || 'GET').toUpperCase()
  const body = init && init.body ? String(init.body) : ''
  calls.push({ url, method, body })
  const json = (payload, status = 200) => ({
    ok: status >= 200 && status < 300,
    status,
    json: async () => payload,
    text: async () => JSON.stringify(payload),
  })
  const p = new URL(url, 'http://localhost').pathname
  if (p === '/ks/materials/projects') return json({ ok: true, data: [{ project_id: 'prj_1', name: '演示项目' }] })
  if (p === '/ks/materials/list') return json({ ok: true, data: [MAT_UP, MAT_COL] })
  if (p === '/ks/materials/tiers') return json({ ok: true, data: [{ tier: 'T1', label: '用户自有原件' }, { tier: 'T3', label: '未核来源' }] })
  if (p === '/ks/materials/role' && method === 'POST') {
    return json({ ok: true, data: { material_id: 'mat_x', task_role: body.includes('reference') ? 'reference' : 'criterion' } })
  }
  return json({ ok: true, data: method === 'GET' ? [] : {} })
}

try {
  const { createRoot } = await import('react-dom/client')
  const root = createRoot(dom.window.document.getElementById('root'))
  root.render(React.createElement(KsMaterialsPanel, { visible: true }))
  await new Promise((r) => setTimeout(r, 30))
  /* 选中项目（受控 select：原生 setter + change，同 setInput 惯例）。 */
  const sel = dom.window.document.querySelector('select[aria-label="参考资料项目"]')
  if (sel !== null) {
    const setter = Object.getOwnPropertyDescriptor(dom.window.HTMLSelectElement.prototype, 'value').set
    setter.call(sel, 'prj_1')
    sel.dispatchEvent(new dom.window.Event('change', { bubbles: true }))
    await new Promise((r) => setTimeout(r, 30))
  }
  const q = (s) => [...dom.window.document.querySelectorAll(s)]
  const click = async (el) => {
    el.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true, cancelable: true }))
    await new Promise((r) => setTimeout(r, 20))
  }

  const rows = q('.ks-mat-row')
  check('① 两行真渲染（.ks-mat-row 钩子 + 标题在）',
    rows.length === 2 && (dom.window.document.body.textContent ?? '').includes('人工上传的制度.pdf'),
    `行 ${String(rows.length)}`)

  const rowUp = rows.find((r) => (r.textContent ?? '').includes('人工上传的制度.pdf')) ?? { textContent: '' }
  const rowCol = rows.find((r) => (r.textContent ?? '').includes('抓来的网页正文')) ?? { textContent: '' }
  const btnTexts = (r) => [...r.querySelectorAll('button')].map((b) => (b.textContent ?? '').trim())
  check('② 免评审行**无批准钮** +「人工上传：免评审」说明在（没步骤就不装样子）',
    !btnTexts(rowUp).some((t) => t.includes('批准')) && (rowUp.textContent ?? '').includes('人工上传：免评审'),
    btnTexts(rowUp).join(' | '))
  check('② 自采行批准/拒绝都在（硬门只管自采）',
    btnTexts(rowCol).some((t) => t.includes('批准（可进入作答）')) && btnTexts(rowCol).some((t) => t === '拒绝'),
    btnTexts(rowCol).join(' | '))

  check('③ 地位胶囊词随 task_role（未声明 / 必须遵守）',
    btnTexts(rowUp).includes('未声明') && btnTexts(rowCol).includes('必须遵守'),
    `up=${btnTexts(rowUp).find((t) => ['未声明', '必须遵守', '仅供参考'].includes(t))} col=${btnTexts(rowCol).find((t) => ['未声明', '必须遵守', '仅供参考'].includes(t))}`)

  const roleCalls = () => calls.filter((c) => c.url.includes('/ks/materials/role'))
  await click([...rowUp.querySelectorAll('button')].find((b) => (b.textContent ?? '').trim() === '未声明'))
  check('④ 点胶囊**真发** POST /ks/materials/role（未声明首点 → role:criterion）',
    roleCalls().length === 1 && roleCalls()[0].method === 'POST' && roleCalls()[0].body.includes('"role":"criterion"')
    && roleCalls()[0].url.includes('material_id=mat_up'),
    roleCalls().map((c) => c.body).join(' | '))

  const boxes = q('.ks-mat-row input[type=checkbox]')
  await click(boxes[0])
  await click(boxes[1])
  const batch = dom.window.document.querySelector('.ks-batch')
  const batchText = batch === null ? '' : (batch.textContent ?? '')
  check('⑤ 勾两行 ⇒ 批量条文案逐字（已选 2 项 · 批量设为必须遵守 · 批量设为仅供参考 · 取消选择）',
    batch !== null && ['已选 2 项', '批量设为必须遵守', '批量设为仅供参考', '取消选择'].every((t) => batchText.includes(t)),
    batchText.replace(/\s+/g, ' ').slice(0, 60))
  const beforeBatch = roleCalls().length
  await click([...batch.querySelectorAll('button')].find((b) => (b.textContent ?? '').includes('批量设为仅供参考')))
  check('⑤ 批量设为仅供参考**真逐项发 role**（恰 2 条 role:reference）',
    roleCalls().length - beforeBatch === 2
    && roleCalls().slice(-2).every((c) => c.body.includes('"role":"reference"')),
    roleCalls().slice(-2).map((c) => c.body).join(' | '))
  await click(q('.ks-mat-row input[type=checkbox]')[0])
  await click(q('.ks-mat-row input[type=checkbox]')[1])
  const batch2 = dom.window.document.querySelector('.ks-batch')
  await click([...batch2.querySelectorAll('button')].find((b) => (b.textContent ?? '').trim() === '取消选择'))
  check('⑤ 取消选择 ⇒ 批量条消失（不留悬空条）', dom.window.document.querySelector('.ks-batch') === null)

  root.unmount()
} finally {
  globalThis.document = saved.document
  globalThis.window = saved.window
  globalThis.fetch = saved.fetch
  await rm(tmp, { recursive: true, force: true })
}

const failed = results.filter((r) => !r.ok)
console.log(`\n== materials-rows smoke ${failed.length === 0 ? 'PASS' : 'FAIL'} (${results.filter((r) => r.ok).length}/${results.length}) ==`)
process.exit(failed.length === 0 ? 0 : 1)
