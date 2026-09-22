/**
 * ks-dsh-plugin — scripts/smoke-turn-tab.mjs
 *
 * 「本轮」依据行的**渲染级**冒烟（S1-b）。照 smoke-anchor-mark / smoke-evidence-warn 的
 * 零依赖做法：`react-dom/server` 静态渲染纯组件。钉四件事：
 *   ① 依据行：标准号+条款号、效力徽章词（现行有效 / YYYY-MM-DD 起实施）、摘要、
 *      **「看原文」按钮文案逐字**（原型定稿句）；
 *   ② 空态两句**逐字**（原型定稿句，不许改成散文）；
 *   ③ URL 构造（turnEvidenceHref）真走 `evidenceUrlOf` 契约：doc/page/rev 齐进 query；
 *   ④ 渲染结果**无字面 `**`**（语言规范 §二.6）与**无字面色兜底**（F0 教训）。
 *
 * 用法：node scripts/smoke-turn-tab.mjs   （退出码 0 = 全通过）
 */
import { mkdtemp, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

import { build } from 'esbuild'

import { ksClientPrimitivesAlias } from './lib/ks-primitives-stub.mjs'

const here = dirname(fileURLToPath(import.meta.url))
const pluginRoot = resolve(here, '..')

const results = []
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}

let React, renderToStaticMarkup
try {
  React = await import('react')
  ;({ renderToStaticMarkup } = await import('react-dom/server'))
} catch (err) {
  console.error('根 node_modules 缺少 react / react-dom：'
    + `${err && err.message ? err.message : String(err)}\n  修法：在仓库根执行 npm install。`)
  process.exit(1)
}

const tmp = await mkdtemp(join(tmpdir(), 'ks-turn-tab-'))
const primStubDir = await mkdtemp(join(tmpdir(), 'ks-turn-tab-prim-'))
const primitivesAlias = ksClientPrimitivesAlias(pluginRoot, primStubDir)
const outfile = join(pluginRoot, '.turn-tab.smoke.mjs')
await build({
  entryPoints: [join(pluginRoot, 'client', 'KsTurnTab.tsx')],
  bundle: true, platform: 'node', format: 'esm', outfile,
  absWorkingDir: pluginRoot, loader: { '.tsx': 'tsx', '.ts': 'ts' },
  external: ['react', 'react-dom', 'react/jsx-runtime', 'pdfjs-dist'],
  alias: { ...primitivesAlias },
  logLevel: 'warning',
})
const mod = await import(pathToFileURL(outfile).href)
await rm(outfile, { force: true })

const { KsTurnEvidenceRow, KsTurnEmptyState, KsTurnModeChip, KsTurnTab, turnEvidenceHref } = mod
check('导出齐：KsTurnEvidenceRow / KsTurnEmptyState / KsTurnModeChip / turnEvidenceHref',
  typeof KsTurnEvidenceRow === 'function' && typeof KsTurnEmptyState === 'function'
  && typeof KsTurnModeChip === 'function' && typeof turnEvidenceHref === 'function')

if (typeof KsTurnModeChip === 'function') {
  const chip = renderToStaticMarkup(React.createElement(KsTurnModeChip, {
    mode: { forensic: true, bookmarksOnly: true, folderName: '夹名一', materialProjectName: null },
    scope: { folder_count: 3, doc_count: 12 },
  }))
  check('口径胶囊：夹内提问/查法规/范围 三味都出词（只读快照的口径行）',
    chip.includes('仅在『夹名一』内提问') && chip.includes('查法规模式')
    && chip.includes('范围：3 个目录 · 12 篇'), chip.slice(0, 80))
  const none = renderToStaticMarkup(React.createElement(KsTurnModeChip, { mode: {}, scope: null }))
  check('口径胶囊：无口径 ⇒ 不渲染（不占一行空白）', none === '', none)
}

if (typeof KsTurnEvidenceRow === 'function' && typeof KsTurnEmptyState === 'function') {
  const EV = {
    doc_id: 'doc_X', clause_revision_id: 'rev_1', standard_no: 'GB 51283-2020', clause_number: '第4.2.9条',
    legal_status: 'effective', legal_hierarchy: 'GB', page_start: 7,
    snippet: '……动火作业分为特殊动火作业、一级动火作业和二级动火作业……',
  }
  const row = renderToStaticMarkup(React.createElement(KsTurnEvidenceRow, { ev: EV, onLook: () => {} }))
  check('依据行：标准号+条款号+效力徽章+摘要都在',
    row.includes('GB 51283-2020') && row.includes('第4.2.9条')
    && row.includes('现行有效') && row.includes('动火作业分为'), row.slice(0, 80))
  check('「看原文」按钮文案逐字（原型定稿句）',
    row.includes('看原文（跳到那一页，红箭头指着）'))
  const up = renderToStaticMarkup(React.createElement(KsTurnEvidenceRow, {
    ev: { ...EV, legal_status: 'upcoming', effective_from: '2026-12-01' }, onLook: () => {},
  }))
  check('即将实施：徽章带生效日期（2026-12-01 起实施）', up.includes('2026-12-01 起实施'))

  const empty = renderToStaticMarkup(React.createElement(KsTurnEmptyState))
  check('空态两句逐字（原型定稿，不许改散文）',
    empty.includes('这一轮还没用到依据。')
    && empty.includes('在对话里提问后，这里会列出这次答案用到的条款与核对结果。'))

  const href = typeof turnEvidenceHref === 'function'
    ? turnEvidenceHref({ doc_id: 'doc_X', page_start: 7, clause_revision_id: 'rev_1' })
    : null
  check('URL 构造走 evidenceUrlOf 契约（doc/page/rev 齐进 query）',
    typeof href === 'string' && href.includes('doc=doc_X') && href.includes('page=7') && href.includes('rev=rev_1'),
    String(href))

  check('渲染结果无字面 **（语言规范 §二.6）', !row.includes('**') && !empty.includes('**'))
  check('渲染结果无字面色兜底（F0 教训：var(...,#hex) 也是写死）',
    !row.includes('#') && !empty.includes('#'))
}

/* ---- 复核 S1（M6 打回补）：**点击行为判据** —— 挂载 KsTurnTab 全链（fetch 桩→依据行→点击→
        openEvidence）；原来 onLook 里删掉 openEvidence(href) 调用**全绿**（无行为判据且未登记，
        打回直接理由）。⚠ 更正留痕：我原写"jsdom 在根 node_modules"——**想当然**，本仓从没装过
        jsdom（仓内多处注释明写）；照 smoke-kb-page-render 的惯用法从 **DSH 检出**引。 ---- */
{
  const harness = process.env.KS_HARNESS_DIR ?? 'D:\\AI\\DSH\\deepseek-harness'
  const jsdomDir = join(harness, 'node_modules', 'jsdom')
  const { JSDOM } = await import(pathToFileURL(join(jsdomDir, 'lib', 'api.js')).href)
  const dom = new JSDOM('<!doctype html><html><body><div id="root"></div></body></html>')
  const saved = {
    document: globalThis.document, window: globalThis.window, fetch: globalThis.fetch,
  }
  globalThis.document = dom.window.document
  globalThis.window = dom.window
  globalThis.fetch = async () => ({
    ok: true,
    json: async () => ({
      ok: true,
      data: {
        seq: 1, session: 's', turn: {
          query: 'Q', verification: null, notes: [], scope: null, mode: null,
          evidence: [{
            doc_id: 'doc_Y', clause_revision_id: 'rev_2', standard_no: 'GB 2',
            clause_number: '第1条', legal_status: 'effective',
          }],
        },
      },
    }),
  })
  try {
    const { createRoot } = await import('react-dom/client')
    const opened = []
    const root = createRoot(dom.window.document.getElementById('root'))
    root.render(React.createElement(KsTurnTab, {
      useTabInfo: () => ({
        tab: { id: 't1', kind: 'ks-turn', title: '本轮', navigation: { revision: 0 }, visible: true },
      }),
      sessionId: 's', dataSource: 'host-stash',
      openEvidence: (u) => { opened.push(u) },
    }))
    await new Promise((r) => setTimeout(r, 20))
    const btn = [...dom.window.document.querySelectorAll('button')]
      .find((b) => (b.textContent ?? '').includes('看原文'))
    check('M6 前置：fetch→依据行真渲染（行在才有得点）', btn !== undefined)
    if (btn !== undefined) {
      btn.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true }))
      check('M6：点「看原文」⇒ openEvidence 收到 evidenceUrlOf 的地址（点击→跳页最后一跳）',
        opened.length === 1 && String(opened[0]).includes('doc=doc_Y'),
        JSON.stringify(opened))
    } else {
      check('M6：点「看原文」⇒ openEvidence 收到 evidenceUrlOf 的地址（点击→跳页最后一跳）',
        false, '按钮没渲染出来')
    }
    root.unmount()
  } finally {
    globalThis.document = saved.document
    globalThis.window = saved.window
    globalThis.fetch = saved.fetch
  }
}

await rm(tmp, { recursive: true, force: true })
await rm(primStubDir, { recursive: true, force: true }).catch(() => {})
const failed = results.filter((r) => !r.ok)
console.log(`\n== turn-tab smoke ${failed.length === 0 ? 'PASS' : 'FAIL'} (${results.filter((r) => r.ok).length}/${results.length}) ==`)
process.exit(failed.length === 0 ? 0 : 1)
