#!/usr/bin/env node
/**
 * plugin/scripts/ui-render-shot.mjs — 离屏渲染 + 无头截图（**已入库**，2026-09-20 第 5 步 5c）
 *
 * ## 它解决什么
 * 宿主 GUI（http://127.0.0.1:3080）对浏览器自动化是 **401**（见 docs/UI-BASELINE.md 第五节：
 * `browser4-cli` 拿到的是一张 133 字节的 401 残页，补 Origin/Referer/Sec-Fetch-* 仍 401）
 * ⇒ 代理**看不到自己的页面长什么样**。本脚本绕开宿主：把 `plugin/client/` 里**一个指定页面组件**
 * 用 esbuild 打包 → 在 jsdom 里**真的挂进 DOM**（真 React、真事件、真类名）→ 序列化成
 * **自包含 HTML**（内联：渲染结果 + 宿主主题 token + 宿主 ui-primitives 的真实 CSS + 我们的
 * KS_STYLES）→ 无头浏览器截图。**它替代的是"打开宿主页面截图"这一步，不是验证本身。**
 *
 * ## 保真度（重要，别把图当"宿主里的样子"）
 * - **宿主原语是真的**：alias `@deepseek-ai/dsh-client-ui-primitives` 到 DSH 检出的
 *   `lib/index.js`（真 Button/Tag/Pill/Checkbox/Input/Menu/Switch），并把它们的
 *   `*.module.css` 用 esbuild `local-css` 一起打包 ⇒ 类名/几何/配色都是宿主发货的那份。
 *   这与 `plugin/scripts/smoke-kb-page-render.mjs` 的**桩**不同（那边只是为了断言行为）。
 * - **主题 token 是真的**：内联 DSH 检出 `packages/client/ui-theme/src/styles/*.css`
 *   （`base.css` + `design-platform.css`），默认走 `body{}` = **浅色一套**。
 *   ⚠ design-platform.css 里 `--dsw-alias-*` 引用 `--dsw-static-*`，两层都在同一份文件里 ⇒ 全链可解。
 * - **宿主外壳是假的**：没有侧栏/标题栏/面板圆角，只有一个定宽 `<div id="ks-shell">`。
 * - **字体是系统字体**（走 base.css 的 --dsw-font-family），非宿主自带字体的复现。
 * - **KaTeX 字体被抹掉**（`.woff` / `.woff2` / `.ttf` 一律 loader `empty`）⇒ **公式渲染不可信**。
 * - 页面数据：kb 页是组件内占位常量（页面自己声明"只有 UI"）；ingest 面板需要 HTTP，
 *   这里用 `fetch` 桩喂**人造数据**（形状按 api.ts 的 TS 类型写），见 STUB 段
 *   ⇒ **那一页只能判"排版/配色"，不能判数据口径**。
 * - **全页截图（窗口高=内容高）看不出 `position:sticky`**：批量条会落在列表末尾。
 *   要判"批量条钉在底部"必须 `--viewport <h>` 用**视口高固定**的截图。
 *
 * ## 用法
 *   node plugin/scripts/ui-render-shot.mjs --page kb --out var/tmp/ui-shots/kb-520.png --width 520
 *   --page kb|ingest|capabilities|materials
 *   --out  <png 路径>（同目录会写一份同名 .html）
 *   --width <px>     默认按页面给（kb 520 / ingest 520 / capabilities 900 / materials 900）
 *   --height <px>    窗口高**固定**（默认：量内容高，全页截图）
 *   --viewport <px>  同上，语义更直白（"这是视口高，不是全页"）
 *                    ⚠ **它不能用来判 `position:sticky`**：`--screenshot` 在这种无头模式下
 *                      是"整页截图"，滚动位置不进产物（5c 实测：加 scrollTo 后图里只剩空白）。
 *                      批量条位置只能在**真宿主页面**里看，见 docs/UI-BASELINE.md 第五节。
 *   --interact <a,b> 可选：kb-detail / kb-select / kb-filter / kb-empty / kb-empty-folder /
 *                    kb-tags-view / ingest-batch / cap-dialog
 *                    ⚠ kb-empty-folder 是 P1-7 补的：点一个"树里有、文件数为 0"的叶子 ⇒ 拿到
 *                      **真的**空态（原来的 kb-empty 点树根，页面仍有文件，p05-kb-520-empty.png
 *                      就是那么来的、名不副实）。kb-filter 是 P1-4 的：点「已废止」⇒ 看筛选
 *                      真的作用在行数上。kb-detail 改走「⋮ → 详情」（行内常驻按钮已收进菜单）。
 *   --theme light|dark  默认 light
 *   --browser <exe>  默认自动找 Edge/Chrome（可用 $KS_BROWSER 覆盖）
 *   --harness <dir>  DSH 检出（默认 $KS_HARNESS_DIR，再退到下方 DEFAULT_HARNESS）
 *   --keep           保留临时构建目录
 *
 * 退出码：0 = 图已生成；1 = 缺件/截图失败（**不是通过**）；2 = 参数错。
 */
import { existsSync } from 'node:fs'
import { mkdir, mkdtemp, readFile, readdir, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { spawnSync } from 'node:child_process'

const here = dirname(fileURLToPath(import.meta.url))
const repoRoot = resolve(here, '..', '..')
const pluginRoot = join(repoRoot, 'plugin')

/* ────────────────────────────── 参数 ────────────────────────────── */
function arg(name, fallback) {
  const i = process.argv.indexOf(`--${name}`)
  if (i !== -1 && process.argv[i + 1] !== undefined && !process.argv[i + 1].startsWith('--')) return process.argv[i + 1]
  return fallback
}
const flag = (name) => process.argv.includes(`--${name}`)

/**
 * DSH 检出：**唯一**一处"本机具体路径"，三条出口按优先级 ——
 *   ① `--harness <dir>`（显式）；② `$KS_HARNESS_DIR`（CI/复核机）；③ 本机开发默认目录。
 * 三条都落空时**报错退出**（不静默降级），并打印找过哪些路径。
 * ⚠ 它是**消费**一个外部 checkout（读它的 ui-primitives/主题 CSS/jsdom），不是我们的产物。
 */
const DEFAULT_HARNESS = 'D:\\AI\\DSH\\deepseek-harness'
const harness = resolve(arg('harness', process.env.KS_HARNESS_DIR ?? DEFAULT_HARNESS))

const themeName = arg('theme', 'light')
const keep = flag('keep')

const PAGES = {
  kb: { width: 520, file: 'KsKnowledgePage.tsx', symbol: 'KsKnowledgePage', interact: [] },
  ingest: { width: 520, file: 'KsIngestPanel.tsx', symbol: 'KsIngestPanel', interact: ['ingest-batch'] },
  capabilities: { width: 900, file: 'KsCapabilityPage.tsx', symbol: 'KsCapabilityPage', interact: [] },
  materials: { width: 900, file: 'KsMaterialsPanel.tsx', symbol: 'KsMaterialsPanel', interact: [] },
}
const page = arg('page', 'kb')
if (!PAGES[page]) { console.error(`❌ 未知 --page ${page}（可选：${Object.keys(PAGES).join(' / ')}）`); process.exit(2) }
const outPng = resolve(arg('out', join(repoRoot, 'var', 'tmp', 'ui-shots', `${page}.png`)))
const width = Number(arg('width', String(PAGES[page].width)))
const fixedHeightRaw = arg('viewport', arg('height', ''))
const fixedHeight = fixedHeightRaw === '' ? null : Number(fixedHeightRaw)
if (fixedHeight !== null && (!Number.isFinite(fixedHeight) || fixedHeight <= 0)) {
  console.error(`❌ --viewport/--height 要是正数（拿到 ${String(fixedHeightRaw)}）`); process.exit(2)
}
const interacts = arg('interact', PAGES[page].interact.join(',')) .split(',').map((s) => s.trim()).filter(Boolean)

/* ────────────────────── 缺件即报错（不静默降级） ────────────────────── */
const jsdomDir = join(harness, 'node_modules', 'jsdom')
const webNodeModules = join(harness, 'packages', 'client', 'web', 'node_modules')
const primitivesDir = join(harness, 'packages', 'client', 'ui-primitives')
const themeDir = join(harness, 'packages', 'client', 'ui-theme', 'src', 'styles')
const esbuildMain = join(pluginRoot, 'node_modules', 'esbuild', 'lib', 'main.js')

const missing = []
for (const [what, p] of [
  ['jsdom', join(jsdomDir, 'package.json')],
  ['react', join(webNodeModules, 'react', 'package.json')],
  ['react-dom', join(webNodeModules, 'react-dom', 'package.json')],
  ['宿主 ui-primitives', join(primitivesDir, 'lib', 'index.js')],
  ['宿主主题 CSS 目录', themeDir],
  ['esbuild（plugin/node_modules）', esbuildMain],
]) if (!existsSync(p)) missing.push(`${what}: ${p}`)
if (missing.length > 0) {
  console.error(`❌ 渲染脚本**没跑**（缺件），这不是通过：`)
  console.error(`   harness = ${harness}`)
  for (const m of missing) console.error(`   - ${m}`)
  console.error('   → 用 --harness <DSH 检出> 或设 KS_HARNESS_DIR。')
  process.exit(1)
}

/* ────────────────────── 无头浏览器 ────────────────────── */
const BROWSERS = [
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
]
const browser = arg('browser', process.env.KS_BROWSER ?? BROWSERS.find((p) => existsSync(p)) ?? '')
if (browser === '' || !existsSync(browser)) {
  console.error('❌ 找不到无头浏览器（--browser 或 $KS_BROWSER 指一个 chrome.exe/msedge.exe）。找过：')
  for (const p of BROWSERS) console.error(`   - ${p}`)
  process.exit(1)
}

const { build } = await import(pathToFileURL(esbuildMain).href)

/* ══════════════════════════ 1. 打包 ══════════════════════════ */
// 中间产物放**系统临时目录**（不是仓里）：这里会 fork esbuild + 建浏览器 profile，
// 万一 --keep 忘了删，也不该在仓里留东西（本仓"代码树零运行产物"）。
const workRoot = join(tmpdir(), 'ks-ui-render-work')
await mkdir(workRoot, { recursive: true })
const work = await mkdtemp(join(workRoot, `${page}-`))

// 入口：从**源码** import 目标组件（真源码，不是 client.js 产物），props 由外面传。
const componentPath = join(pluginRoot, 'client', PAGES[page].file)
const entry = join(work, 'entry.tsx')
await writeFile(entry, `
import { createElement } from 'react'
import { createRoot } from 'react-dom/client'
import { ${PAGES[page].symbol} } from ${JSON.stringify(componentPath)}

export function mount(container, props) {
  const root = createRoot(container)
  root.render(createElement(${PAGES[page].symbol}, props))
  return root
}
`, 'utf8')

const bundleDir = join(work, 'bundle')
await build({
  entryPoints: [entry],
  bundle: true,
  platform: 'browser',
  format: 'esm',
  outdir: bundleDir,
  entryNames: 'bundle',
  assetNames: 'assets/[name]',
  jsx: 'automatic',
  // 宿主原语用**真的**（DSH 检出 lib/index.js），它的 *.module.css 一起打包成一份 CSS。
  // ⚠ 字体/图片一律 `empty`：**不许引外部资源**（katex 的 KaTeX_*.woff2 是从 MarkdownText
  //   那条链带进来的）。代价：数学公式字体缺失（本脚本要截的几页都不渲染公式）。
  loader: {
    '.css': 'local-css',
    '.woff': 'empty', '.woff2': 'empty', '.ttf': 'empty', '.otf': 'empty', '.eot': 'empty',
    '.svg': 'empty', '.png': 'empty', '.jpg': 'empty', '.jpeg': 'empty', '.gif': 'empty',
  },
  alias: {
    '@deepseek-ai/dsh-client-ui-primitives': join(primitivesDir, 'lib', 'index.js'),
    react: join(webNodeModules, 'react', 'index.js'),
    'react/jsx-runtime': join(webNodeModules, 'react', 'jsx-runtime.js'),
    'react-dom': join(webNodeModules, 'react-dom', 'index.js'),
    'react-dom/client': join(webNodeModules, 'react-dom', 'client.js'),
  },
  define: { 'process.env.NODE_ENV': '"production"' },
  logLevel: 'warning',
})
const bundleJs = join(bundleDir, 'bundle.js')
const primitivesCss = existsSync(join(bundleDir, 'bundle.css')) ? await readFile(join(bundleDir, 'bundle.css'), 'utf8') : ''

/* ══════════════════════════ 2. jsdom 里真渲染 ══════════════════════════ */
const { JSDOM } = await import(pathToFileURL(join(jsdomDir, 'lib', 'api.js')).href)
const dom = new JSDOM('<!doctype html><html><head></head><body><div id="root"></div></body></html>', { url: 'http://localhost/' })
globalThis.window = dom.window
globalThis.document = dom.window.document
Object.defineProperty(globalThis, 'navigator', { value: dom.window.navigator, configurable: true, writable: true })
globalThis.HTMLElement = dom.window.HTMLElement
globalThis.Node = dom.window.Node
globalThis.Event = dom.window.Event
globalThis.requestAnimationFrame = (cb) => setTimeout(() => { cb(Date.now()) }, 0)
globalThis.cancelAnimationFrame = (id) => { clearTimeout(id) }

/* ── STUB：ingest 面板要 HTTP。形状按 plugin/client/api.ts 的 TS 类型写（不是瞎编）。 ── */
const STUB_DIR = 'D:\\KnowledgeStation\\inbox'
const stubFiles = [
  { file_name: 'GB 30871-2022 危险化学品企业特殊作业安全规范.pdf', size: 3_412_889, path: `${STUB_DIR}\\GB 30871-2022.pdf` },
  { file_name: 'GB 50016-2014 建筑设计防火规范.pdf', size: 8_120_004, path: `${STUB_DIR}\\GB 50016-2014.pdf` },
  { file_name: 'GB 55037-2022 建筑防火通用规范.pdf', size: 2_004_551, path: `${STUB_DIR}\\GB 55037-2022.pdf` },
  { file_name: '扫描件_2025 年安全评价报告（无文本层）.pdf', size: 41_889_334, path: `${STUB_DIR}\\scan-2025.pdf` },
  { file_name: 'GB 50084-2017 自动喷水灭火系统设计规范.pdf', size: 6_772_110, path: `${STUB_DIR}\\GB 50084-2017.pdf` },
]
const stubBatch = {
  total_candidates: 5, truncated: false, limit_files: 200, sampled: 5, unprocessed: 0,
  evaluated: 5, sample_requested: 5, conservation_ok: true, elapsed_ms: 12_430, doc_type: 'standard', egress: 'none',
  buckets: { ok: 3, warn: 1, block: 1 },
  by_bucket: {},
  files: [
    { path: stubFiles[0].path, file_name: stubFiles[0].file_name, verdict: 'ok', grade: 'A', pages: 42, total_clauses: 318, doc_confidence: 0.94, one_line: 'A 级 · 文本层完好，条款切分正常', reasons: ['文本层完好'], error: null },
    { path: stubFiles[1].path, file_name: stubFiles[1].file_name, verdict: 'ok', grade: 'A', pages: 189, total_clauses: 1204, doc_confidence: 0.92, one_line: 'A 级 · 表格已重建 12 处', reasons: ['表格重建'], error: null },
    { path: stubFiles[2].path, file_name: stubFiles[2].file_name, verdict: 'ok', grade: 'B', pages: 33, total_clauses: 210, doc_confidence: 0.81, one_line: 'B 级 · 条款编号风格不统一', reasons: ['编号风格'], error: null },
    { path: stubFiles[3].path, file_name: stubFiles[3].file_name, verdict: 'warn', grade: 'C', pages: 96, total_clauses: 0, doc_confidence: 0.42, one_line: 'C 级 · 无文本层，需 OCR 或云深度解析', reasons: ['无文本层', '疑似扫描件'], error: null },
    { path: stubFiles[4].path, file_name: stubFiles[4].file_name, verdict: 'block', grade: 'D', pages: 0, total_clauses: 0, doc_confidence: 0.0, one_line: 'D 级 · 文件损坏，无法解析', reasons: ['解析失败'], error: 'PDF 结构损坏（EOF 缺失）' },
  ],
}
globalThis.fetch = async (input) => {
  const url = typeof input === 'string' ? input : String(input?.url ?? input)
  const reply = (payload) => ({ ok: true, status: 200, json: async () => payload, text: async () => JSON.stringify(payload) })
  if (url.includes('/ks/ingest/inbox-default')) return reply({ ok: true, data: { dir: STUB_DIR } })
  if (url.includes('/ks/ingest/inbox')) return reply({ ok: true, data: { dir: STUB_DIR, count: stubFiles.length, files: stubFiles } })
  if (url.includes('/ks/ingest/preview/batch')) return reply({ ok: true, data: stubBatch })
  if (url.includes('/ks/ingest/preview')) return reply({ ok: true, data: null })
  return reply({ ok: false, error: { code: 'STUB_MISS', message: `未预料的请求：${url}` } })
}

const { mount } = await import(pathToFileURL(bundleJs).href)
/** 让 React 的更新真的落地：等宏任务 + 定时器（jsdom 里 React 18 的调度走 setTimeout/immediate）。 */
const flush = async () => {
  for (let i = 0; i < 6; i += 1) await new Promise((r) => { setTimeout(r, 0) })
  await new Promise((r) => { setTimeout(r, 20) })
}
const container = document.getElementById('root')

const PROPS = {
  kb: {
    useTabInfo: () => ({ tab: { id: 'ks-kb-tab', visible: true, navigation: { address: 'ks:kb', revision: 1, params: { page: 'manage' } } } }),
    dataSource: 'mock',
  },
  ingest: { visible: true },
  capabilities: {},
  materials: { projectId: 'prj_demo', visible: true },
}

const root = mount(container, PROPS[page])
await flush()
await flush()

/* ── 交互（可选）：只是点真按钮，走真事件 ── */
const q = (sel) => [...container.querySelectorAll(sel)]
const byText = (sel, text) => q(sel).find((el) => (el.textContent ?? '').includes(text))
const click = async (el) => {
  if (!el) return false
  el.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true }))
  await flush()
  return true
}
const notes = []
for (const how of interacts) {
  if (how === 'kb-detail') {
    // ⚠ P1-1（2026-09-20）改道：行内的常驻「详情」按钮没了（收进行尾「⋮」溢出菜单）
    //   ⇒ 先点第一行的「⋮」，再点菜单里的「详情」。旧写法（button[aria-label^="打开"]）
    //   在改版后永远找不到按钮、只回一句"没找到按钮"——那种"静默没做成"正是本脚本要避免的。
    const row = q('.ks-item')[0]
    const more = row?.querySelector('.ks-item-more button')
    const opened = await click(more)
    const item = opened
      ? [...document.querySelectorAll('[role=menuitem]')].find((el) => (el.textContent ?? '') === '详情')
      : null
    const done = item ? await click(item) : false
    notes.push(`kb-detail: ${opened ? '点了第一行的「⋮」' : '没找到「⋮」'} → ${done ? '点了菜单里的「详情」' : '没找到菜单项'}`)
  } else if (how === 'kb-filter') {
    // P1-4 验收：筛选**真的作用在页面状态上**。点「已废止」胶囊，报出筛选前后的行数。
    const before = q('.ks-item').length
    const chip = byText('.ks-chip', '已废止')
    const ok = await click(chip)
    notes.push(`kb-filter: ${ok ? '点了「已废止」胶囊' : '没找到胶囊'}`
      + ` → 行数 ${before} → ${q('.ks-item').length}`
      + `，空态卡 ${q('.ks-empty-card').length} 张`)
  } else if (how === 'kb-filter-empty') {
    // 筛选到 **0 行** ⇒ 看"被筛没了"的那一支空态（P1-4 的两种空之一）。
    // 怎么造出 0 行：先切到只有现行件的「供应商资料」（1 篇，status=current），
    // 再点「已废止」⇒ 0 行。这是**页面状态**真的生效的证据，不是画出来的。
    const folder = q('.ks-kb-cards .ks-kb-card').find((el) => (el.textContent ?? '').includes('供应商资料'))
    const moved = await click(folder)
    const before = q('.ks-item').length
    const chip = byText('.ks-chip', '已废止')
    const ok = await click(chip)
    notes.push(`kb-filter-empty: ${moved ? '切到「供应商资料」' : '没找到自建夹卡'}`
      + ` → 行数 ${before} → ${q('.ks-item').length}`
      + `，空态卡 ${q('.ks-empty-card').length} 张`
      + `，空态标题「${q('.ks-empty-t').map((el) => el.textContent).join('|')}」`)
  } else if (how === 'kb-select') {
    const box = q('input[type=checkbox]')[0]
    notes.push(`kb-select: ${await click(box) ? '点了全选' : '没找到勾选框'}`)
  } else if (how === 'ingest-batch') {
    const ok = await click(byText('button', '开始预览'))
    notes.push(`ingest-batch: ${ok ? '点了「开始预览」' : '没找到按钮'}`
      + ` → 批量行 ${q('button').filter((b) => /\.pdf$/.test((b.textContent ?? '').trim())).length} 条`
      + `，总账 ${container.textContent.includes('共评估') ? '有' : '无'}`
      + `，失败 ${container.textContent.includes('预览失败') ? container.textContent.split('预览失败')[1]?.slice(0, 60) : '无'}`)
  } else if (how === 'kb-empty') {
    // 点一个**没有文档**的树节点（自带树的根节点 "P 土木、建筑"）⇒ 看空态卡
    const node = q('.ks-kb-tline').find((el) => (el.textContent ?? '').includes('P 土木、建筑'))
    notes.push(`kb-empty: ${await click(node) ? `点了「${(node.textContent ?? '').trim()}」` : '没找到节点'}`
      + ` → 空态卡 ${q('.ks-empty-card').length} 张`)
  } else if (how === 'kb-empty-folder') {
    // P1-7 验收要的**真空态**：点一个"树里有、文件数为 0"的节点 ⇒ 列表 0 行 + 空态卡 1 张。
    // 注意原有的 kb-empty 点的是树**根**节点（根下没有直接文件，点它会展开/收起，
    // 屏幕上仍有上一次选中的夹子 ⇒ 拿不到空态）。这里选 "P15/19 工程抗震、工程防火、人防工程"
    // ——它在种子里**没有文档**（文件都在它的子层 P16），而父节点 P 土木、建筑 默认展开。
    // 库里 p05-kb-520-empty.png 名不副实（那一跑是有数据 + 已选中的场景）—— 这条就是补它。
    const node = q('.ks-kb-tline').find((el) => (el.textContent ?? '').includes('P15/19'))
    const ok = await click(node)
    notes.push(`kb-empty-folder: ${ok ? `点了「${(node.textContent ?? '').trim()}」` : '没找到节点'}`
      + ` → 文件行 ${q('.ks-item').length} 行，空态卡 ${q('.ks-empty-card').length} 张`
      + `，空态标题「${q('.ks-empty-t').map((el) => el.textContent).join('|')}」`)
  } else if (how === 'kb-tags-view') {
    const pill = byText('button', '标签')
    notes.push(`kb-tags-view: ${await click(pill) ? '切到标签视图' : '没找到「标签」'}`)
  } else if (how === 'cap-dialog') {
    const card = q('.ks-cap-card').find((c) => q('.ks-cap-card').length > 0 && [...c.querySelectorAll('button')].some((b) => (b.textContent ?? '').includes('设置')))
    notes.push(`cap-dialog: ${await click(card?.querySelector('button')) ? '开了第一张带「设置…」的窗' : '没找到'}`)
  }
}

const rendered = container.innerHTML

/* ══════════════════════════ 3. 自包含 HTML ══════════════════════════ */
const ksStylesSrc = await readFile(join(pluginRoot, 'client', 'ksGuideStyles.ts'), 'utf8')
// ⚠ **行尾必须容错**（复核 ui5 2026-09-20）：`core.autocrlf=true` 下 `git worktree`/`git archive`
//   提取出来的树是 **CRLF**，而这条正则原来要求闭引号后紧跟 `\n` ⇒ CRLF 树里 `\r\n` 匹配不上，
//   脚本会报"抠不出 KS_STYLES"、让人误以为**交付件坏了**（它只是行尾不同）。⇒ 用 `\r?\n`。
const m = /export const KS_STYLES = `([\s\S]*?)`\r?\n/.exec(ksStylesSrc)
if (m === null) {
  console.error('❌ 从 ksGuideStyles.ts 里抠不出 KS_STYLES（行尾已容错 CRLF/LF，所以这**不是**行尾问题：'
    + '多半是模板字符串被截断 —— 注释里出现反引号是已知踩坑）')
  process.exit(1)
}
const ksStyles = m[1]

let themeCss = ''
for (const f of (await readdir(themeDir)).filter((f) => f.endsWith('.css')).sort()) {
  themeCss += `\n/* ===== ${f} ===== */\n` + await readFile(join(themeDir, f), 'utf8')
}
const darkAttr = themeName === 'dark' ? ' data-ds-dark-theme' : ''
/**
 * 页壳的 min-height：全页截图（窗口高=内容高）时用 100vh 让背景铺满；
 * **固定视口**时必须是 auto —— 否则 `--window-size=W,H` 下文档不足 H 时会被 100vh 撑高。
 */
const shellMinHeight = fixedHeight === null ? '100vh' : 'auto'

const html = `<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>h=0</title>
<!-- 1) DSH 宿主主题 token（**逐字取自检出** packages/client/ui-theme/src/styles/*.css，没编色值） -->
<style id="ks-theme">${themeCss}</style>
<!-- 2) 宿主 ui-primitives 的真实 CSS Modules（esbuild local-css 产出的哈希类名，与 JS 一致） -->
<style id="ks-primitives">${primitivesCss}</style>
<!-- 3) 我们插件的运行时样式表（KS_STYLES 全文） -->
<style id="ks-plugin-styles">${ksStyles}</style>
<!-- 4) 页壳：**这是假的宿主外壳**，只给一个定宽容器 -->
<style id="ks-shell-css">
  html,body{margin:0;padding:0;}
  body{font-family:var(--dsw-font-family);font-size:13px;color:var(--dsw-alias-label-primary);
       background:var(--dsw-alias-bg-layer-2);}
  #ks-shell{width:${width}px;box-sizing:border-box;padding:12px;background:var(--dsw-alias-bg-layer-1);
            min-height:${shellMinHeight};}
</style>
</head>
<body${darkAttr}>
<div id="ks-shell">${rendered}</div>
<script>
/* 量高 + 量几何：**浏览器里算出来的真值**，随 dump-dom 回传（截的是同一份 HTML）。   ⚠ .ks-item 那几项是 5c 为「文件名与标签簇之间有没有死白」专门加的：
     · .ks-check   = 文件名（含勾选框）的盒子
     · .ks-item-tags = 标签簇
     · deadGap = 标签簇左缘 - 文件名盒子右缘（**死白就是它**）
     · .ks-item-btn = 「＋标签」「详情」（右端按钮，flex:none，用来判"没被挤扁"）
   ⚠ 本段在**模板字符串**里：注释不许用反引号（会截断模板），也不许写美元加大括号（会被当插值）。 */
(function () {
  try {
    var sels = ['#ks-shell','.ks-item','.ks-detail','.ks-rail','.ks-main','.ks-kb-card','.ks-cap-card',
                '.ks-batch','.ks-lhead','.ks-page-title','.ks-kb-tn','.ks-item-tags','.ks-item-add',
                '.ks-cap-engine','.ks-knob-label','.ks-kb-banner','.ks-field','.ks-tagrow',
                '.ks-list','.ks-filters','.ks-chip','.ks-status','.ks-item-more','.ks-item-title','.ks-item-sub',
                '.ks-check','.ks-item-meta','.ks-batch-btn','.ks-empty-card','.ks-empty-t','.ks-empty-d'];
    var out = {};
    sels.forEach(function (s) {
      var els = document.querySelectorAll(s);
      if (els.length === 0) return;
      var r = els[0].getBoundingClientRect();
      var cs = getComputedStyle(els[0]);
      out[s] = { n: els.length, x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height),
                 fs: cs.fontSize, lh: cs.lineHeight, pad: cs.padding, gap: cs.gap, radius: cs.borderRadius };
    });
    // 列表行的**节距**（相邻 .ks-item 的 y 差）——"4px 网格/行高"要看的就是它
    var items = document.querySelectorAll('.ks-item');
    if (items.length > 1) {
      var ys = [].map.call(items, function (el) { return Math.round(el.getBoundingClientRect().y); });
      out['.ks-item#pitch'] = { n: ys.length, y: ys[0], w: 0, h: ys[1] - ys[0], fs: '', lh: ys.join(','), pad: '', gap: '', radius: '' };
    }
    // 每一行：文件名盒子有多宽、标签簇在哪、中间空多少（死白量）
    // ⚠ P1-1（2026-09-20）起 btnH 的来源换人了：行内两个常驻 Button（＋标签/详情）收进了
    //   行尾「⋮」溢出菜单 ⇒ 这里量到的最后一个 .ks-item-btn 是**菜单触发器**（宿主 size=sm）。
    //   ctrls = 这一行**可见控件数**（勾选框 + 状态徽章 + ⋮）—— 就是 P1-1 的验收口径。
    if (items.length > 0) {
      out['.ks-item#rows'] = { n: items.length, y: 0, w: 0, h: 0, fs: '', lh: '', pad: '', gap: '', radius: '',
        rows: [].map.call(items, function (el) {
          var chk = el.querySelector('.ks-check');
          var fname = chk ? chk.querySelector('span') : null;
          var tags = el.querySelector('.ks-item-tags');
          var more = el.querySelector('.ks-item-more button');
          var r0 = el.getBoundingClientRect();
          var rc = chk ? chk.getBoundingClientRect() : null;
          var rf = fname ? fname.getBoundingClientRect() : null;
          var rt = tags ? tags.getBoundingClientRect() : null;
          var rm = more ? more.getBoundingClientRect() : null;
          var ctrls = el.querySelectorAll('.ks-check,.ks-status,.ks-item-more').length;
          return { rowW: Math.round(r0.width), nameW: rc ? Math.round(rc.width) : null,
                   fileNameW: rf ? Math.round(rf.width) : null,
                   nameRight: rc ? Math.round(rc.right - r0.left) : null,
                   tagsLeft: rt ? Math.round(rt.left - r0.left) : null,
                   deadGap: (rc && rt) ? Math.round(rt.left - rc.right) : null,
                   btnH: rm ? Math.round(rm.height) : null,
                   ctrls: ctrls };
        }) };
    }
    // 每张卡（.ks-kb-card / .ks-cap-card）的**逐个高度**：判"同列卡等高"要看的就是它
    // （P0-2/P0-3 之前只能看首张，于是"212 / 115 / 85 三档"只能靠肉眼估）。
    // ⚠⚠ **P1-9 修正（2026-09-20）**：这里原选择器还含 「.ks-kb-card」 —— 而 「.ks-kb-card」
    //   除了"卡"还被**两处非卡元素**复用：① 「.ks-detail」 里的占位小方块、② 标签视图里那个
    //   包检索语法输入的描边盒。它们是 .ks-main 的**直接子元素**，高度不受 .ks-kb-cards>*
    //   的 min-height 约束 ⇒ 于是 「#cards.h」 里冒出 72 / 66 这种"小于 136"的值，
    //   读起来像"卡没吃到 min-height"（假的）。**只留 .ks-cap-card 之后坑就填上了**：
    //   两个页面上确实是"卡"的只有 「.ks-kb-cards>*」 与 「.ks-cap-card」。
    var cardEls = document.querySelectorAll('.ks-kb-cards>*,.ks-cap-card');
    if (cardEls.length > 0) {
      var hs = [].map.call(cardEls, function (el) { return Math.round(el.getBoundingClientRect().height); });
      var ws = [].map.call(cardEls, function (el) { return Math.round(el.getBoundingClientRect().width); });
      out['#cards'] = { n: hs.length, y: 0, w: 0, h: 0, fs: '', lh: hs.join(','), pad: ws.join(','), gap: '', radius: '' };
    }
    // 批量条的**一行装得下吗**：w = 最后一个子元素的右缘 - 条子的右缘（正数 = 溢出/被截，
    // 负数 = 还剩多少余量）。h = 条子高（折成两行会明显变高）。P0-5 判"两行/溢出"就靠它。
    // ⚠⚠ **P1-9 修正（2026-09-20）**：原来 「lastKid.right - br.right」 量的是"**条子**的右缘"，
    //   而它是 sticky + width:fit-content 的**浮层**、贴右缘时会算出负数 —— 那是"条子右缘
    //   在子元素右缘右边多少"（= 内边距 + 余量），**不是溢出**。真正的溢出判据是
    //   "最后一个子元素的右缘有没有超过条子的**内容盒**右缘"：br.right - paddingRight。
    //   量不动时（paddings 解析不出数字）退回旧口径，并在 title 里给出 **条子自身的绝对坐标**
    //   （bx/bw）—— P1-6 要看的"居中且宽 < 容器"就是它，不必再去二进制里翻 BMP。
    var bar = document.querySelector('.ks-batch');
    if (bar) {
      var br = bar.getBoundingClientRect();
      var cbs = getComputedStyle(bar);
      var pr = parseFloat(cbs.paddingRight);
      var barInnerRight = br.right - (isFinite(pr) ? pr : 0);
      var kids = bar.children;
      var lastKid = kids.length > 0 ? kids[kids.length - 1].getBoundingClientRect() : null;
      out['.ks-batch#fit'] = { n: kids.length, x: Math.round(br.x), y: Math.round(br.width), w: lastKid ? Math.round(lastKid.right - barInnerRight) : 0,
                               h: Math.round(br.height), fs: '', lh: '', pad: (isFinite(pr) ? String(Math.round(pr)) : ''),
                               gap: '', radius: '' };
    }
    document.title = 'h=' + document.documentElement.scrollHeight + '|m=' + JSON.stringify(out);
  } catch (e) {
    document.title = 'h=' + document.documentElement.scrollHeight + '|m={"error":' + JSON.stringify(String(e)) + '}';
  }
})();
</script>
</body>
</html>`

await mkdir(dirname(outPng), { recursive: true })
const outHtml = outPng.replace(/\.png$/i, '.html')
await writeFile(outHtml, html, 'utf8')

/* ══════════════════════════ 4. 截图（两趟：先量高，再按高截全景） ══════════════════════════ */
const fileUrl = pathToFileURL(outHtml).href
const runBrowser = (args) => spawnSync(browser, [
  '--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-first-run', '--no-default-browser-check',
  '--disable-extensions', '--virtual-time-budget=4000',
  `--user-data-dir=${join(work, 'profile')}`,
  ...args,
], { encoding: 'utf8', timeout: 120_000 })

const probe = runBrowser(['--dump-dom', '--window-size=800,600', fileUrl])
const hMatch = /<title>h=(\d+)\|m=/.exec(probe.stdout ?? '')
if (hMatch === null) {
  console.error('❌ 量高失败（--dump-dom 里没有 <title>h=…|m=…</title>）。stderr 尾部：')
  console.error((probe.stderr ?? '').split('\n').slice(-6).join('\n'))
  process.exit(1)
}
const cssHeight = Number(hMatch[1])
let measured = {}
const mJson = /\|m=(\{.*?\})<\/title>/s.exec(probe.stdout ?? '')
if (mJson !== null) { try { measured = JSON.parse(mJson[1].replace(/&quot;/g, '"')) } catch { measured = { parse_error: true } } }
// --viewport 给定时**按视口高截**（这才看得出 position:sticky；全页截图看不出来）
const shotHeight = fixedHeight ?? Math.max(320, Math.min(cssHeight, 6000))

const shot = runBrowser([`--screenshot=${outPng}`, `--window-size=${width},${shotHeight}`, fileUrl])
if (!existsSync(outPng)) {
  console.error('❌ 截图失败。stderr 尾部：')
  console.error((shot.stderr ?? '').split('\n').slice(-6).join('\n'))
  process.exit(1)
}

/* PNG 真实像素尺寸（从 IHDR 读，不引依赖） */
const buf = await readFile(outPng)
const pxW = buf.readUInt32BE(16)
const pxH = buf.readUInt32BE(20)

if (!keep) await rm(work, { recursive: true, force: true })

console.log(JSON.stringify({
  page,
  width,
  theme: themeName,
  viewportHeight: fixedHeight,
  interact: notes,
  htmlPath: outHtml,
  pngPath: outPng,
  pixelSize: `${pxW}x${pxH}`,
  cssHeight,
  measured,
  renderedChars: rendered.length,
  bundle: { js: bundleJs.replace(work, '<work>'), primitivesCssChars: primitivesCss.length },
  browser,
}, null, 2))
