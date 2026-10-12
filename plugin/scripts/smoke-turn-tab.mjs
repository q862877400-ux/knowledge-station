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

const {
  KsTurnEvidenceRow, KsTurnEmptyState, KsTurnModeChip, KsTurnTab, turnEvidenceHref,
  groupTurnEvidence, compareClauseOrder, clauseOrderKey,
} = mod
check('导出齐：KsTurnEvidenceRow / KsTurnEmptyState / KsTurnModeChip / turnEvidenceHref'
  + ' / groupTurnEvidence / compareClauseOrder',
  typeof KsTurnEvidenceRow === 'function' && typeof KsTurnEmptyState === 'function'
  && typeof KsTurnModeChip === 'function' && typeof turnEvidenceHref === 'function'
  && typeof groupTurnEvidence === 'function' && typeof compareClauseOrder === 'function')

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
  /* ⚠ 2026-10-10（spec 009，业主要求 1）**就地翻面**（原文保留在上面）：
     原来这条断言是"依据行含标准号 GB 51283-2020" —— 而业主明确要求
     「一个文件里的多个条款就不要重复文件标题了」⇒ 条款行**不再带文件标题**，
     标题改由外层分组卡出一次。⇒ 断言改成：
       · 条款行**必须**有条款号与效力徽章；
       · 条款行**不许**再出现标准号（那是分组卡的活）。
     判据见下面新增的"分组"一组。 */
  check('依据行（条款行）：条款号 + 效力徽章 + 摘要都在', 
    row.includes('第4.2.9条') && row.includes('现行有效') && row.includes('动火作业分为'), row.slice(0, 80))
  check('依据行（条款行）**不再重复文件标题**（spec 009 业主要求 1）',
    !row.includes('GB 51283-2020'),
    `行里还有标准号 ⇒ ${row.slice(0, 80)}`)
  /* ⚠ 2026-10-10（spec 009，业主要求 2）：**负向钉** —— 层级字样不许回来。
     业主原话：「现行有效后面的 GB 字样删除。」
     判法（可靠版）：把 EV 的 `legal_hierarchy` 设成一个**绝不会出现在别处**的哨兵值，
     再看渲染里有没有它 —— 有它 ⇒ 说明这一处又在渲染层级了。
     ⚠ 不用"渲染里不许出现 GB"这种写法：标准号本身可能含 GB（如 `GB 51283-2020`），
       那种全称判据会假红。 */
  const rowSentinel = renderToStaticMarkup(React.createElement(KsTurnEvidenceRow, {
    ev: { ...EV, legal_hierarchy: '哨兵层级XYZ' }, onLook: () => {},
  }))
  check('依据行**不再显示 legal_hierarchy**（spec 009 业主要求 2：删掉「GB」字样）',
    !rowSentinel.includes('哨兵层级XYZ'),
    rowSentinel.slice(0, 120))
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

  /* ⚠⚠ 2026-10-10（spec 009，**红箭头不出现的决定性一环**）：
     原来 `evidenceUrlOf` **只编 doc/page/rev，从不编 bbox** ⇒ 任何调用方传了 bbox
     都会在编码这步丢掉 ⇒ 证据 tab 里 `evidence.current?.bbox` 恒 undefined ⇒ **箭头永不画**。
     下面四条把这条契约钉死（有 bbox ⇒ 必须进 URL；没有/形状不对 ⇒ 不许编）。 */
  const hrefBbox = typeof turnEvidenceHref === 'function'
    ? turnEvidenceHref({
        doc_id: 'doc_X', page_start: 7, clause_revision_id: 'rev_1',
        bbox: [76, 643.43, 117, 655.43], bbox_page: 7,
      })
    : null
  check('★ bbox 必须进证据 URL（红箭头第③环：原来这里把它丢了）',
    /* ⚠ 断言用**解码后**的串比：`URLSearchParams` 会把逗号编码成 `%2C`，
       拿编码串去 `includes('bbox=76,643.43,...')` 会**假红**（我自己第一版就这么错了）。 */
    typeof hrefBbox === 'string'
    && decodeURIComponent(hrefBbox).includes('bbox=76,643.43,117,655.43'),
    String(hrefBbox))
  check('★ bbox_page 也要进 URL（箭头只在该页画）',
    typeof hrefBbox === 'string' && hrefBbox.includes('bboxPage=7'), String(hrefBbox))
  check('★ 没有 bbox ⇒ **不许编空参**（编空串会让 parseBbox 得 NaN、画出错位置的箭头）',
    typeof href === 'string' && !href.includes('bbox='), String(href))
  const hrefBadBbox = typeof turnEvidenceHref === 'function'
    ? turnEvidenceHref({ doc_id: 'doc_X', bbox: [1, 2, 3], bbox_page: 0 })
    : null
  check('★ bbox 形状不对（3 个数）/ bbox_page=0 ⇒ 不编进 URL',
    typeof hrefBadBbox === 'string' && !hrefBadBbox.includes('bbox'), String(hrefBadBbox))

  /* ⚠⚠ 2026-10-10（spec 009）：**上一版这一条判据没有牙**（我自己做变异时发现）——
     只测 `turnEvidenceHref` 的话，它在**它自己那层**已经做了形状初筛
     （`Array.isArray && length===4 && every isFinite`），
     于是 `evidenceUrlOf` 里那道 `isBbox` 校验**永远走不到**、改坏它也没人红。
     ⇒ 补一组**直接打 `evidenceUrlOf`** 的判据。它是 URL 契约的**唯一所有者**，
       「不许编空参/错参」这条规矩必须在**它**身上有牙。
     ⚠ 实现方式：**单独 bundle `ksEvidence.ts`**（它不依赖 React，是纯函数模块），
       不从 `KsTurnTab` 转出口 —— 后者本来就没 re-export 它（也不该为测试加）。
     ⚠ 这也是一条真实边界：`evidenceUrlOf` 是 public 导出、别处也能调，
       不能靠"调用方都先筛过了"来担保。 */
  {
    const evOut = join(pluginRoot, '.ks-evidence.smoke.mjs')
    await build({
      entryPoints: [join(pluginRoot, 'client', 'ksEvidence.ts')],
      bundle: true, platform: 'node', format: 'esm', outfile: evOut,
      absWorkingDir: pluginRoot, loader: { '.tsx': 'tsx', '.ts': 'ts' },
      logLevel: 'warning',
    })
    const evMod = await import(pathToFileURL(evOut).href)
    await rm(evOut, { force: true })
    const bad3 = evMod.evidenceUrlOf({ doc: 'd', bbox: [1, 2, 3] })
    check('★ evidenceUrlOf：bbox 只有 3 个数 ⇒ 不编（不许编错参）',
      typeof bad3 === 'string' && !bad3.includes('bbox'), String(bad3))
    const badNaN = evMod.evidenceUrlOf({ doc: 'd', bbox: [1, 2, 3, Number.NaN] })
    check('★ evidenceUrlOf：bbox 含 NaN ⇒ 不编',
      typeof badNaN === 'string' && !badNaN.includes('bbox'), String(badNaN))
    const good = evMod.evidenceUrlOf({ doc: 'd', bbox: [1, 2, 3, 4], bboxPage: 2 })
    check('★ evidenceUrlOf：合法 bbox + bboxPage ⇒ 都编进去',
      typeof good === 'string' && decodeURIComponent(good).includes('bbox=1,2,3,4')
      && good.includes('bboxPage=2'), String(good))
    const noBox = evMod.evidenceUrlOf({ doc: 'd' })
    check('★ evidenceUrlOf：没有 bbox ⇒ 一个 bbox 参数都不编（不许出现空参）',
      typeof noBox === 'string' && !noBox.includes('bbox'), String(noBox))
    /* 往返：编出来的 URL 必须能被 parseEvidence **原样解回来** —— 这是"只进不出"那个病的正面判据。 */
    const round = evMod.parseEvidence(good)
    check('★ 往返一致：evidenceUrlOf → parseEvidence 能解回 bbox / bboxPage',
      round !== null && Array.isArray(round.bbox)
      && JSON.stringify(round.bbox) === JSON.stringify([1, 2, 3, 4])
      && round.bboxPage === 2, JSON.stringify(round))
  }

  /* ⚠⚠ 2026-10-10（spec 009，业主要求 1）：**同文件的多个条款不重复文件标题**。
     业主原话：「一个文件里的多个条款就不要重复文件标题了，一个文件标题下面多个条款按先后顺序排列。」 */
  if (typeof groupTurnEvidence === 'function') {
    const multi = [
      { doc_id: 'd1', standard_no: 'GB 1', title: '文件一', clause_number: '5.10.1', clause_revision_id: 'r1' },
      { doc_id: 'd1', standard_no: 'GB 1', title: '文件一', clause_number: '5.2.3', clause_revision_id: 'r2' },
      { doc_id: 'd1', standard_no: 'GB 1', title: '文件一', clause_number: '5.2.10', clause_revision_id: 'r3' },
      { doc_id: 'd2', standard_no: 'GB 2', title: '文件二', clause_number: '1.1', clause_revision_id: 'r4' },
    ]
    const groups = groupTurnEvidence(multi)
    check('★ 分组：4 条依据（2 个文件）⇒ **2 组**（不是 4 张卡）', groups.length === 2,
      `groups=${String(groups.length)}`)
    const g1 = groups[0]
    check('★ 分组：同一文件下 3 个条款归到一组',
      g1 !== undefined && g1.items.length === 3,
      `g1.items=${String(g1 === undefined ? 'undefined' : g1.items.length)}`)
    const order = g1 === undefined ? [] : g1.items.map((x) => String(x.clause_number))
    check('★ 组内按条款号**数值感知升序**（5.2.3 < 5.2.10 < 5.10.1，不是字典序）',
      JSON.stringify(order) === JSON.stringify(['5.2.3', '5.2.10', '5.10.1']), JSON.stringify(order))
    check('★ 组标题含标准号与文件名（**只出一遍**）',
      g1 !== undefined && g1.title.includes('GB 1') && g1.title.includes('文件一'),
      String(g1 === undefined ? '' : g1.title))
    const noDoc = groupTurnEvidence([
      { clause_number: '1', clause_revision_id: 'a' },
      { clause_number: '2', clause_revision_id: 'b' },
    ])
    check('★ 无 doc_id 的条目**各自成组**（不许混成一个组）', noDoc.length === 2,
      `groups=${String(noDoc.length)}`)
    let threw = false
    try {
      groupTurnEvidence([
        { doc_id: 'd', clause_number: '第一条' },
        { doc_id: 'd', clause_number: '' },
        { doc_id: 'd', clause_number: '8.1.1' },
      ])
    } catch (e) { threw = true }
    check('★ 排序键稳健：中文条款号 / 空值**不抛错**', !threw)
    check('★ compareClauseOrder 纯数字在前、中文在后（数值段优先）',
      compareClauseOrder({ clause_number: '1.1' }, { clause_number: '第一条' }) < 0)
  }

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
