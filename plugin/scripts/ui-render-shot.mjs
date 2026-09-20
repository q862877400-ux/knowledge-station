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
 * - ⚠ **5h-补（2026-09-20）截图的滚动条是"真的"**：本脚本**不再**传 `--hide-scrollbars`
 *   （那个开关会让滚动条根本不画 ⇒ 业主点名的"滑动条"在图上永远看不见）。代价：凡**真溢出**的
 *   容器都会多出一条原生滚动条，页宽/版式可能因此变一点点 —— 这是**有意**的，不是缺陷。
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
 *   --band-scroll <px|end>  5h-补：在**真 Chrome** 里把卡片带的横向滚动容器滚到该位置（默认 0 = 不滚）。
 *                      ⚠ 为什么要有它：jsdom 预渲染那趟**没有布局**（scrollWidth 恒 0）⇒ 卡片带的
 *                        scrollLeft 只能是 0，"滚到中段/末端"那张图需要的位移出不来。它写的是**真元素**的
 *                        scrollLeft（等同用户拖了那条滚动条），位移与滚动条拇指位置都由真布局算。
 *   --interact <a,b> 可选：kb-files / kb-detail / kb-select / kb-filter / kb-filter-empty /
 *                    kb-search / kb-search-dirs / kb-search-dirs-empty / kb-empty-files /
 *                    kb-tags-view / kb-band-start / kb-band-end /
 *                    kb-enter-law / kb-enter-l2 / kb-back / ingest-batch / cap-dialog
 *                    ⚠⚠ **5i（2026-09-20 收尾批）：未知场景名 ⇒ 报错 + exit 2**（列出可用名字）。
 *                      复核实测旧行为：`--interact kb-empty`（已删掉的场景名）⇒ `notes=[]`、**exit 0**。
 *                      另外**每个分支都必须"落地"**：做不到就报 note + **exit 1**（`mustLand`），
 *                      不再有"什么都没做还成功"的路径（见 `SCENARIOS` 与 `landing` 的注释）。
 *                    ⚠ **5h（2026-09-20）新 IA 改了基准态**：默认态 =「卡片带 + **一级目录**」
 *                      （业主："先占上一级目录文件夹…到最末一级才是文件"）⇒ 凡是要"文件表格 /
 *                      状态徽章 / 搜索框"的场景都必须**先下钻**。脚本里那四个 helper
 *                      （`gotoCard` / `gotoFilesView` / `gotoStdLeaf` / `gotoBandEnd`）就是这一步，共用一份。
 *                      ⚠ 每个 helper 都**自带兜底**：`--interact` 允许一次给多个场景，前一个场景可能把
 *                        卡片带滚到别处、或把页切到「标签」视图 ⇒ 后一个场景会"找不到东西"（实测踩到过）。
 *                        `gotoCard` 先把带滚回最左（5h-补：卡片现在**全在 DOM 里**，滚回即可），
 *                        `gotoFilesView` 先切回文件视图。
 *                      为此 kb-detail / kb-select / kb-filter / kb-filter-empty / kb-search /
 *                      kb-tags-view **各自加了前置导航**（断言的实质没变：还是量行数/徽章/像素）。
 *                    ⚠ 原来那条 `kb-empty` / `kb-empty-folder` **已删**（它们点的是**树节点**
 *                      `.ks-kb-tline`，而树被业主点名删掉 ⇒ 写法永远找不到节点）。替代品
 *                      `kb-empty-files`：下钻 → 全选 → 批量删除 ⇒ 目录**真的**空了，拿到
 *                      "这个文件夹还没有文件"那一支空态（比旧写法更真，不是点一个假节点）。
 *                    ⚠ `kb-files` 是给 `smoke-kb-cols.mjs`（列对齐三档）与 `ui-badge-pixels.mjs`
 *                      （徽章像素）用的**前置步骤**：它们验的是表格/徽章，而默认态停在目录层。
 *                    ⚠ kb-band-end / kb-band-start / kb-enter-law / kb-enter-l2 / kb-back 都是 5h 新增，
 *                      对应业主原话里的"左右翻页滑动条"与"进入二级目录就自动出现返回上一级的按钮"。
 *                    ⚠ kb-search 是 P2 头条（2026-09-20）补的：往列表上方的搜索框里打字，
 *                      报出"行数 初始 → 按标准号 → 按名称 → 不存在的串 → 清空"五步，
 *                      用来证明那个框**真的过滤**（不是画个壳）。
 *                    ⚠ kb-filter 是 P1-4 的：点「已废止」⇒ 看筛选真的作用在行数上。kb-detail
 *                      走「⋮ → 详情」（行内常驻按钮已收进菜单）。
 *   --theme light|dark  默认 light
 *   --browser <exe>  默认自动找 Edge/Chrome（可用 $KS_BROWSER 覆盖）
 *                    ⚠ 文档里说的"真 Chrome"是**约定叫法**（同一 Chromium 内核）：本机
 *                      （5i-补 2026-09-20 实测）命中的是 `msedge.exe`，不是 Google Chrome。
 *   --harness <dir>  DSH 检出（默认 $KS_HARNESS_DIR，再退到下方 DEFAULT_HARNESS）
 *   --keep           保留临时构建目录
 *
 * ## ⚠ 本脚本**自己会判红**（2026-09-20 P2 复核打回 B，`verify-freeze-p2`）
 * 复核的变异 M4（把表头与行的 `grid-template-columns` 改成**不一致**：header `416px 100px …`
 * vs row `444px 72px …`）当时全绿 —— 因为 `#cols` 只是**报告值、没有断言**，而"列对齐"正是
 * P2 头条的验收之一。现在 `#cols` 是**真断言**：表头与第一行的 computed
 * `grid-template-columns`（与 `column-gap`）必须**逐字相同**，不一致 ⇒ 打出两边的值 + 宽度 +
 * 主题，**exit 1**。三档（520/1300/900）由 `scripts/smoke-kb-cols.mjs` 逐档跑本脚本、任一档红即红。
 * ⚠ 没有 `.ks-lhead` 的页面（capabilities/material/ingest）与**没有数据行**的场景（空态截图）
 *   不适用这条断言 ⇒ 本脚本**明说"这条没判"**（打印 note），不是静默通过。
 *
 * ⚠⚠ **5i（2026-09-20 收尾批）又加了一条真断言**：`#kbcards`（卡片带里逐张卡的宽/高）必须
 *   **全等**，不等 ⇒ 逐张打印实际值 + **exit 1**（`cardsCheck`）。为什么：复核把列模板改成
 *   `60px 120px 200px`（三张卡三种宽）之后**渲染冒烟 51/51 全绿** —— 旧的 `#cards` 只是报告值，
 *   全仓没有断言引用它，而"知识库卡片尺寸统一"是业主点名的形态。同样三档由 `smoke-kb-cols` 跑。
 *
 * 退出码：0 = 图已生成且（适用时）列对齐/卡片尺寸自检通过；1 = 缺件/截图失败/自检失败/**--interact
 *   场景没落地**（**不是通过**）；2 = 参数错（含**未知的 --interact 场景名**，5i 起）。
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
/**
 * **`--interact` 的合法场景名**（唯一所有者）。
 *
 * ⚠⚠ **5i（2026-09-20 收尾批）：未知场景名不再静默通过。**
 *   复核实测：`--interact kb-empty`（一个**已删掉**的场景名 —— 它点的是被业主点名删掉的目录树
 *   `.ks-kb-tline`）⇒ 循环里没有分支接住它 ⇒ `notes=[]`、**exit 0**。而这个文件自己的注释还写着
 *   "那种静默没做成正是本脚本要避免的" —— 同一个病：**什么都不做还能成功**。
 *   ⇒ 现在两条路都堵死：
 *     · 名字**不在**这张表里 ⇒ 打错误 + 列出可用名字 + **exit 2**（参数错，与 `--page` 同一档）；
 *     · 名字在表里、但这一跑**没落地**（见下面的 `mustLand`）⇒ 报 note + **exit 1**（断言红）。
 *     · 名字在表里、但 if/else 链**没有分支**接住它 ⇒ 走链尾的 `else` 兜底 ⇒ 报 note + **exit 1**。
 *   ⚠ **更正（5i-补 2026-09-20）**：这里原写"表与 if/else 链不一致时前者会当场红（见 `handled` 集合）"
 *     —— **那句话是错的，`handled` 从来没堵住过任何东西**：它在循环**首**无条件 `add`，
 *     循环尾 `!handled.has(how)` 是**死代码**。复核 verify-freeze-5i（`581d20d`）实测探针
 *     `'kb-fake-probe'`（加进本表、链里不写分支）⇒ **`interact: []`、exit 0**。
 *     本轮改成上面的 `else` 兜底；同一探针现在 **exit 1 并打出名字**（见循环内那段注释）。
 *   ⚠ 这张表是**活的所有者**：加一个场景就加一行，删一个场景就删一行。
 */
const SCENARIOS = [
  'kb-files', 'kb-band-start', 'kb-band-end', 'kb-enter-law', 'kb-enter-l2', 'kb-back',
  'kb-detail', 'kb-filter', 'kb-filter-empty', 'kb-search', 'kb-search-dirs',
  'kb-search-dirs-empty', 'kb-select', 'kb-empty-files', 'kb-tags-view',
  'ingest-batch', 'cap-dialog',
]
const unknownScenarios = interacts.filter((name) => !SCENARIOS.includes(name))
if (unknownScenarios.length > 0) {
  console.error(`❌ 未知的 --interact 场景名：${unknownScenarios.join(', ')}`)
  console.error(`   可用场景名（共 ${String(SCENARIOS.length)} 个）：${SCENARIOS.join(' / ')}`)
  console.error('   ⚠ 这不是"忽略一下继续跑"的情况：旧行为是**什么都不做还 exit 0**（复核 verify-freeze-5h'
    + ' 实测 --interact kb-empty ⇒ notes=[]、exit 0），那种静默本批已堵死。')
  process.exit(2)
}
/**
 * `--band-scroll <px|end>`（5h-补，2026-09-20）：**在真浏览器里**把卡片带的横向滚动容器滚到指定位置。
 *
 * ⚠ 为什么需要它：jsdom 预渲染那趟**没有布局**（`scrollWidth` 恒 0）⇒ 卡片带的 `scrollLeft`
 *   在那儿只能是 0，于是"滚到中段/末端"这张图需要的**位移**在图里出不来。
 *   注意这不是"造假滚动"：它写的是**真 Chrome 里真元素**的 `scrollLeft`（就像用户拖了那条滚动条），
 *   卡片位移与滚动条拇指位置都由浏览器的真布局算出来。默认 `0` = 不注入这段脚本。
 */
const bandScrollRaw = arg('band-scroll', '0').trim().toLowerCase()

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
/**
 * 往**受控 input** 里打字（`kb-search` 与两个目录层搜索场景共用）。
 * ⚠ 必须走**原生 setter**：直接 `el.value = x` 会被 React 的 value tracker 判成"没变化"而不触发
 *   `onChange` —— 渲染级冒烟第一版就是这么失败的（本脚本当初也踩过同一个坑）。
 */
const setSearchInput = async (el, value) => {
  const nativeSetter = Object.getOwnPropertyDescriptor(dom.window.HTMLInputElement.prototype, 'value').set
  nativeSetter.call(el, value)
  el.dispatchEvent(new dom.window.Event('input', { bubbles: true }))
  await flush()
}
const notes = []
/**
 * **场景"落地"的判定**（5i 2026-09-20 收尾批；与上面的 `SCENARIOS` 表配套）。
 *
 * 为什么要有它：`--interact` 的每个分支都必须**真的做到那一件事**，做不到就得**报红**，
 * 不能只在 note 里写一句"没找到卡"然后 exit 0 —— 那就是"什么都没做还成功"。
 * ⚠ 边界（诚实）：**卡片带那两个**场景在 jsdom 里"滚动"本来就动不了（没有布局引擎，
 *   `scrollWidth` 恒 0，组件里那条兜底明说"量不出几何就不滚并返回 false"）⇒ 它们的落地判据
 *   只能钉到"这条带 + 5 张卡真的在 DOM 里、箭头真的被点到"，**位移**由真 Chrome 的
 *   `--band-scroll` 那一趟（或 `measured["#kbband"]`）取证。这不是放宽：件数少了在这里必红。
 */
const landing = []
const mustLand = (ok, msg) => { if (!ok) landing.push(msg) }
/* ⚠ **更正（5i-补 2026-09-20）**：这里原来还有一个 `const handled = new Set()`，配合循环首的
 * `handled.add(how)` 与循环尾的 `!handled.has(how)` 想表达"表里有、链里没有 ⇒ 红"。
 * 那**从来没生效过**：`add` 在循环首**无条件**执行 ⇒ 循环尾那条检查恒假 = **死代码**
 * （复核 verify-freeze-5i / `581d20d` 用 `'kb-fake-probe'` 探针实测：`interact: []`、exit 0）。
 * 现在改由 if/else 链的 **`else` 兜底分支**接手（见循环内那条注释），概念只有一个所有者。 */
/* ── 5h（2026-09-20）导航小工具：新 IA 下**默认态不再是文件表格** ──
 * 默认态 =「卡片带 + **一级目录**」（业主："先占上一级目录文件夹…到最末一级才是文件"）。
 * ⇒ 凡是要"文件表格 / 状态徽章 / 搜索框"的场景（kb-detail / kb-select / kb-search / kb-filter…），
 *   都必须**先下钻**到最末一级。这三个 helper 就是那几步，写在这里共用一份。 */
const cardNamed = (name) => q('.ks-kb-cards .ks-kb-card')
  .find((el) => (el.querySelector('.ks-kb-ct')?.textContent ?? '').trim() === name)
const dirNamed = (text) => q('.ks-dir').find((el) => (el.textContent ?? '').includes(text))
/** 卡片带的左右箭头（**5h-补 2026-09-20 起 aria-label 是"上一张/下一张"**：箭头改成 `scrollBy`
 *  一次滚一张卡，不再是"上一组/下一组"的窗口翻页）。 */
const navNamed = (which) => q('.ks-kbband-nav').find((b) => (b.getAttribute('aria-label') ?? '').includes(which))
/** 卡片带那个横向滚动容器（`.ks-kbband-clip`）—— 滚动的真源是它的 `scrollLeft`。 */
const bandClip = () => q('.ks-kbband-clip')[0]
/** 标准 → P 土木、建筑 → P15/19… → P16 工程防火：**4 篇文件**的那一层（与渲染冒烟同一层）。 */
const gotoStdLeaf = async () => {
  await gotoCard('标准')
  await click(cardNamed('标准'))
  await click(dirNamed('P 土木、建筑'))
  await click(dirNamed('P15/19'))
  await click(dirNamed('P16 工程防火'))
  return q('.ks-item').length
}
/**
 * 确保处在「**文件**」页内视图。
 * ⚠ 为什么需要：`--interact` 可以一次给多个场景，前一个场景可能把页切到「标签」
 *   —— 标签视图里**没有目录层也没有表格**（`view === 'tags'` 那一支），后面的场景就会"找不到东西"。
 *   实测：串跑 `kb-tags-view,kb-enter-l2` 时后者报出空面包屑。点一下「文件」胶囊即可复原
 *   （重复点同一个胶囊是无害的幂等操作）。
 */
const gotoFilesView = async () => {
  const pill = q('.ks-subtabs button').find((b) => (b.textContent ?? '').trim() === '文件')
  if (pill !== undefined) await click(pill)
  return q('.ks-subtabs').length
}
/**
 * 把卡片带滚到**指定卡片可见**的位置。
 * ⚠ 5h-补（2026-09-20）**改写**：卡片带不再是"窗口切片 + 上一组/下一组"（那时"直接找卡"会
 *   因为**离屏的卡不在 DOM 里**而找不到），现在**全部卡片一次渲染**进一个横向滚动容器 ⇒
 *   卡永远在 DOM 里，只需要把容器滚到它跟前。
 * ⚠ 为什么仍保留这个 helper：`--interact` 可以一次给多个场景，前一个场景可能已经把带滚到末尾
 *   —— 每个场景要**自成一体**，不看前一个场景的脸色（这条纪律没变）。
 * ⚠ `scrollIntoView` 在 jsdom 里**是 no-op**（没有布局）；这里**不靠它**，只调一次，
 *   真正的确保交给"卡在 DOM 里"这一事实 —— 本脚本要的是**真 Chrome 里**的滚动位置。
 */
const gotoCard = async (name) => {
  await gotoFilesView()
  const clip = bandClip()
  if (clip !== undefined) clip.scrollLeft = 0
  const card = cardNamed(name)
  if (card !== undefined && typeof card.scrollIntoView === 'function') card.scrollIntoView()
  await flush()
  return { found: card !== undefined, left: clip === undefined ? null : Math.round(clip.scrollLeft) }
}
/**
 * 点右箭头一路滚到底（到"尾"⇒ 右箭头 disabled）。
 * ⚠ 5h-补：真 Chrome 里这一步**真的会改 `scrollLeft`**（jsdom 预渲染那趟不会，见下面的注释），
 *   所以它的 note 顺便报出 `scrollLeft/scrollWidth/clientWidth` —— 那就是"能滚 + 有滚动条"的证据。
 */
const gotoBandEnd = async () => {
  let guard = 0
  while (guard < 20 && navNamed('下一张') !== undefined && navNamed('下一张').disabled === false) {
    await click(navNamed('下一张'))
    guard += 1
  }
  return guard
}
for (const how of interacts) {
  if (how === 'kb-files') {
    // **5h 新增**：把页面开到"标准 / P 土木、建筑 / P15/19… / P16 工程防火"（4 行文件 + 表头）。
    // 这是 `smoke-kb-cols.mjs`（列对齐三档）与 `ui-badge-pixels.mjs`（徽章像素）**必须**先走的一步
    // —— 它们验的是**表格/徽章**，而默认态现在停在目录层（业主本轮定的 IA）。
    const rows = await gotoStdLeaf()
    mustLand(rows === 4 && q('.ks-lhead').length === 1, `kb-files 只下钻到 ${rows} 行（期望 4 行 + 1 个表头）`)
    notes.push(`kb-files: 下钻到「标准 / P 土木、建筑 / P15/19… / P16 工程防火」`
      + ` → 文件行 ${rows} 行、表头 ${q('.ks-lhead').length} 个、返回上一级 ${q('.ks-back').length} 个`
      + `，面包屑「${q('.ks-crumb-path').map((el) => el.textContent).join('')}」`)
  } else if (how === 'kb-band-end') {
    // **5h 新增 / 5h-补 改口径**（业主："一个小框下面自带一个左右翻页滑动条"）：
    // 现在"到尾"= 横向滚动容器滚到最右 ⇒ 图上应该看到**卡片真的位移了**、右箭头置灰、左箭头可用。
    const before = bandClip() === undefined ? null : Math.round(bandClip().scrollLeft)
    const clicks = await gotoBandEnd()
    const clip = bandClip()
    // ⚠ 落地判据见 `mustLand` 的注释：jsdom 里滚不动是**环境事实**，这里只钉"带和 5 张卡真的在"。
    mustLand(clip !== undefined && q('.ks-kb-cards .ks-kb-card').length === 5,
      `kb-band-end 找不到卡片带或卡片不是 5 张（卡 ${q('.ks-kb-cards .ks-kb-card').length} 张、点击 ${clicks} 次）`)
    notes.push(`kb-band-end: 点了 ${clicks} 次「下一张」 → scrollLeft ${String(before)} → `
      + `${String(clip === undefined ? null : Math.round(clip.scrollLeft))}`
      + `（scrollWidth=${String(clip?.scrollWidth)} clientWidth=${String(clip?.clientWidth)}`
      + ` ⇒ 可滚 ${String(clip === undefined ? null : clip.scrollWidth - clip.clientWidth)}）`
      + `、右箭头 disabled=${String(navNamed('下一张')?.disabled)}、左箭头 disabled=${String(navNamed('上一张')?.disabled)}`
      + `，带里 5 张卡 ${q('.ks-kb-cards .ks-kb-card').map((el) => (el.querySelector('.ks-kb-ct')?.textContent ?? '').trim()).join('/')}`)
  } else if (how === 'kb-band-start') {
    // 滚回最左（左箭头应置灰）——与 kb-band-end 配对，用来对照"置灰"确实是状态而不是恒灰。
    await gotoBandEnd()
    let guard = 0
    while (guard < 20 && navNamed('上一张') !== undefined && navNamed('上一张').disabled === false) {
      await click(navNamed('上一张'))
      guard += 1
    }
    const clip = bandClip()
    mustLand(clip !== undefined && q('.ks-kb-cards .ks-kb-card').length === 5,
      `kb-band-start 找不到卡片带或卡片不是 5 张（卡 ${q('.ks-kb-cards .ks-kb-card').length} 张）`)
    notes.push(`kb-band-start: 滚回最左（点了 ${guard} 次「上一张」）→ 左箭头 disabled=${String(navNamed('上一张')?.disabled)}`
      + `，scrollLeft=${String(clip === undefined ? null : Math.round(clip.scrollLeft))}`
      + `，带里 5 张卡 ${q('.ks-kb-cards .ks-kb-card').map((el) => (el.querySelector('.ks-kb-ct')?.textContent ?? '').trim()).join('/')}`)
  } else if (how === 'kb-enter-law') {
    // **5h 新增**：点「法律法规」卡 = 进入该库，看它的**一级目录**（法律 / 行政法规）。
    const g = await gotoCard('法律法规')
    const ok = await click(cardNamed('法律法规'))
    mustLand(ok && q('.ks-dir').length === 2, `kb-enter-law ${ok ? '点了卡' : '没找到卡（gotoCard found=' + String(g.found) + '）'}`
      + ` 但一级目录只有 ${q('.ks-dir').length} 张（期望 2）`)
    notes.push(`kb-enter-law: ${ok ? '点了「法律法规」卡' : '没找到卡'}`
      + ` → 一级目录 ${q('.ks-dir').map((el) => (el.querySelector('.ks-dir-name')?.textContent ?? '').trim()).join('/')}`
      + `，文件行 ${q('.ks-item').length}，返回上一级 ${q('.ks-back').length} 个`
      + `，面包屑「${q('.ks-crumb-path').map((el) => el.textContent).join('')}」`)
  } else if (how === 'kb-enter-l2') {
    // **5h 新增**：进**二级目录**（法律法规 → 法律 ⇒ 宪法与行政法）——业主点名要的状态：
    // 「进入二级目录就自动出现返回上一级的按钮」。图上应该有「← 返回上一级」+ 面包屑「法律法规 / 法律」。
    await gotoCard('法律法规')
    await click(cardNamed('法律法规'))
    await click(dirNamed('法律'))
    const l2Crumb = q('.ks-crumb-path').map((el) => el.textContent).join('')
    // ⚠ 这条正是复核第 3 组串跑（`kb-tags-view,kb-enter-l2`）打回的地方：面包屑曾是 **空串**。
    //   落地判据因此**逐字钉面包屑**（不是"有目录层就算数"）。
    mustLand(l2Crumb === '法律法规 / 法律' && q('.ks-dir').length === 1,
      `kb-enter-l2 没到二级目录：面包屑「${l2Crumb}」（期望「法律法规 / 法律」）、目录卡 ${q('.ks-dir').length} 张（期望 1）`)
    notes.push(`kb-enter-l2: 点了「法律法规」卡 → 一级目录「法律」`
      + ` → 二级目录 ${q('.ks-dir').map((el) => (el.querySelector('.ks-dir-name')?.textContent ?? '').trim()).join('/')}`
      + `，返回上一级 ${q('.ks-back').length} 个`
      + `，面包屑「${l2Crumb}」`)
  } else if (how === 'kb-back') {
    // **5h 新增**：二级目录 → 点「返回上一级」⇒ 回到一级目录层、按钮**消失**。
    await gotoCard('法律法规')
    await click(cardNamed('法律法规'))
    await click(dirNamed('法律'))
    const before = q('.ks-back').length
    await click(q('.ks-back')[0])
    const backDirs = q('.ks-dir').map((el) => (el.querySelector('.ks-dir-name')?.textContent ?? '').trim()).join('/')
    // 从「法律法规 → 法律」返回 ⇒ 回到**库根**（法律 / 行政法规 **2 张**）、返回按钮消失。
    mustLand(before === 1 && q('.ks-dir').length === 2 && q('.ks-back').length === 0,
      `kb-back 没回到库根：返回按钮 ${before} → ${q('.ks-back').length} 个、目录卡 ${q('.ks-dir').length} 张（期望 2 张、0 个按钮）`)
    notes.push(`kb-back: 二级目录（返回按钮 ${before} 个）→ 点「返回上一级」`
      + ` → 目录 ${backDirs}`
      + `，返回上一级 ${q('.ks-back').length} 个`
      + `，面包屑「${q('.ks-crumb-path').map((el) => el.textContent).join('')}」`)
  } else if (how === 'kb-detail') {
    // ⚠ P1-1（2026-09-20）改道：行内的常驻「详情」按钮没了（收进行尾「⋮」溢出菜单）
    //   ⇒ 先点第一行的「⋮」，再点菜单里的「详情」。旧写法（button[aria-label^="打开"]）
    //   在改版后永远找不到按钮、只回一句"没找到按钮"——那种"静默没做成"正是本脚本要避免的。
    // ⚠ 5h（2026-09-20）：**先下钻到文件层**（默认态现在是目录层，没有行可点）。
    const rows = await gotoStdLeaf()
    const row = q('.ks-item')[0]
    const more = row?.querySelector('.ks-item-more button')
    const opened = await click(more)
    const item = opened
      ? [...document.querySelectorAll('[role=menuitem]')].find((el) => (el.textContent ?? '') === '详情')
      : null
    const done = item ? await click(item) : false
    mustLand(done && q('.ks-detail .ks-kb-card').length === 1,
      `kb-detail 没打开详情卡（下钻 ${rows} 行／⋮ ${String(opened)}／菜单项 ${String(item !== null)}／详情卡 ${q('.ks-detail .ks-kb-card').length} 张）`)
    notes.push(`kb-detail: 先下钻（文件行 ${rows} 行）→ ${opened ? '点了第一行的「⋮」' : '没找到「⋮」'}`
      + ` → ${done ? '点了菜单里的「详情」' : '没找到菜单项'}`
      + `，详情卡 ${q('.ks-detail .ks-kb-card').length} 张`)
  } else if (how === 'kb-filter') {
    // P1-4 验收：筛选**真的作用在页面状态上**。点「已废止」胶囊，报出筛选前后的行数。
    // ⚠ 5h：先下钻到文件层（4 行里 1 行是已废止 ⇒ 筛选后应剩 1 行）。
    await gotoStdLeaf()
    const before = q('.ks-item').length
    const chip = byText('.ks-chip', '已废止')
    const ok = await click(chip)
    mustLand(ok && before === 4 && q('.ks-item').length === 1,
      `kb-filter 没筛出 1 行（胶囊 ${String(ok)}／行数 ${before} → ${q('.ks-item').length}）`)
    notes.push(`kb-filter: ${ok ? '点了「已废止」胶囊' : '没找到胶囊'}`
      + ` → 行数 ${before} → ${q('.ks-item').length}`
      + `，空态卡 ${q('.ks-empty-card').length} 张`)
  } else if (how === 'kb-filter-empty') {
    // 筛选到 **0 行** ⇒ 看"被筛没了"的那一支空态（P1-4 的两种空之一）。
    // 怎么造出 0 行：先切到只有现行件的「供应商资料」（1 篇，status=current），
    // 再点「已废止」⇒ 0 行。这是**页面状态**真的生效的证据，不是画出来的。
    // ⚠ 5h-补：卡片**全部在 DOM 里**（不再有"最后一屏"这回事）⇒ gotoCard 只把带滚回最左，
    //   "供应商资料"这张卡本来就在 DOM 里，直接点即可（滚动位置不影响点击）。
    const g = await gotoCard('供应商资料')
    const folder = cardNamed('供应商资料')
    const moved = await click(folder)
    const before = q('.ks-item').length
    const chip = byText('.ks-chip', '已废止')
    const ok = await click(chip)
    mustLand(moved && ok && before === 1 && q('.ks-item').length === 0 && q('.ks-empty-card').length === 1,
      `kb-filter-empty 没造出空态（卡 ${String(moved)}／胶囊 ${String(ok)}／行数 ${before} → ${q('.ks-item').length}`
      + `／空态卡 ${q('.ks-empty-card').length} 张）`)
    notes.push(`kb-filter-empty: 先滚回带首（scrollLeft=${String(g.left)}、found ${String(g.found)}） → ${moved ? '点「供应商资料」卡' : '没找到卡'}`
      + ` → 行数 ${before} → ${q('.ks-item').length}`
      + `，空态卡 ${q('.ks-empty-card').length} 张`
      + `，空态标题「${q('.ks-empty-t').map((el) => el.textContent).join('|')}」`)
  } else if (how === 'kb-search') {
    // P2 头条验收：**搜索框真的过滤**（不是画个壳）。
    // ⚠ 5h：先下钻到文件层。⚠ 5i：文件层这一支的**位置与行为都没变**；目录层新加了同一个框
    //   （见下面 `kb-search-dirs`）。
    await gotoStdLeaf()

    // 分三步取证：① 输入只命中 1 行的串 ⇒ 行数真的变 1；② 只命中名称的串 ⇒ 也是 1；
    // ③ 清空 ⇒ 恢复原行数。受控 input 必须走**原生 setter**（直接 el.value = x 会被
    // React 的 value tracker 判成"没变化"而不触发 onChange —— 渲染级冒烟第一版就是这么失败的）。
    const box = q('.ks-search input')[0]
    if (!box) {
      mustLand(false, 'kb-search 没找到 .ks-search 里的输入框（这一条不判 = 失败，不是通过）')
      notes.push('kb-search: 没找到 .ks-search 里的输入框')
    } else {
      const before = q('.ks-item').length
      await setSearchInput(box, 'GB 50016-2014')
      const byNo = q('.ks-item').length
      await setSearchInput(box, '喷水')
      const byName = q('.ks-item').length
      await setSearchInput(box, '搜索一个不存在的串')
      const none = q('.ks-item').length
      const emptyCard = q('.ks-empty-t').map((el) => el.textContent).join('|')
      await setSearchInput(box, '')
      const after = q('.ks-item').length
      mustLand(before === 4 && byNo === 1 && byName === 1 && none === 0 && after === 4,
        `kb-search 过滤不成立：行数 初始 ${before}（期望 4）→ 标准号 ${byNo}（1）→ 名称 ${byName}（1）`
        + ` → 不存在 ${none}（0）→ 清空 ${after}（4）`)
      notes.push(`kb-search: 行数 初始 ${before} → 标准号「GB 50016-2014」${byNo}`
        + ` → 名称「喷水」${byName} → 不存在「搜索一个不存在的串」${none}（空态「${emptyCard}」）`
        + ` → 清空 ${after}`)
      // 收尾**停在"筛出 1 行"的状态**（不是清空态）：这样这张图本身就是"搜索真的生效"的像素证据
      // （图上搜索框里有字、表里只剩 1 行）。清空那一步的证据在上面那条 note 里（行数回到 before）。
      await setSearchInput(box, '喷水')
      notes.push(`kb-search（收尾）: 搜索框留在「喷水」⇒ 图上是 1 行`
        + `（体量 ${q('.ks-item').length} / 表头 ${q('.ks-lhead').length}）`)
    }
  } else if (how === 'kb-search-dirs') {
    /* **5i 新增**（业主 2026-09-20 只说"搜索框：保留"、未限定层级 ⇒ 按最强解释"每层常驻"）：
     * 库根（一级目录层）也用**同一个搜索框**过滤，过滤对象是**目录名**。
     * 这一跑停在"框里有词 + 目录被筛到 1 张"的状态 ⇒ 这一张图就是"目录层有搜索框且真的过滤"的证据。
     * ⚠ 判据：3 张一级目录 → 「环境」1 张（Z 环境保护）→ 清空回 3 张；每一步都打印实际张数。 */
    await gotoCard('标准')
    await click(cardNamed('标准'))
    const box = q('.ks-search input')[0]
    const all = q('.ks-dir').length
    if (!box) {
      mustLand(false, 'kb-search-dirs 目录层没有 .ks-search 输入框（每一层常驻是本轮的验收）')
      notes.push('kb-search-dirs: 目录层没找到 .ks-search 里的输入框')
    } else {
      await setSearchInput(box, '环境')
      const hit = q('.ks-dir').length
      const hitName = q('.ks-dir-name').map((el) => (el.textContent ?? '').trim()).join('/')
      await setSearchInput(box, '')
      const restored = q('.ks-dir').length
      mustLand(all === 3 && hit === 1 && hitName.includes('Z 环境保护') && restored === 3,
        `kb-search-dirs 目录名过滤不成立：目录 ${all}（期望 3）→「环境」${hit}（1）→ 清空 ${restored}（3）`)
      notes.push(`kb-search-dirs: 库根目录 ${all} 张 →「环境」${hit} 张（${hitName}）→ 清空 ${restored} 张；`
        + `面包屑「${q('.ks-crumb-path').map((el) => el.textContent).join('')}」、子目录计数「${q('.ks-crumb-n').map((el) => el.textContent).join('')}」`)
      // 收尾停在"被筛到 1 张"那一态：图上要看得到**目录层的搜索框**（不是空表）。
      await setSearchInput(box, '环境')
      notes.push(`kb-search-dirs（收尾）: 框里留在「环境」⇒ 图上是 1 张目录卡`
        + `（目录 ${q('.ks-dir').length} 张 / 文件行 ${q('.ks-item').length}）`)
    }
  } else if (how === 'kb-search-dirs-empty') {
    /* **5i 新增**：目录层搜索**没命中** ⇒ 专门的空态「没有符合搜索的目录」+「清除搜索」
     * （不复用文件层那句"没有符合筛选或搜索的文件"）。图上要看到那个空态卡与框里的词。 */
    await gotoCard('标准')
    await click(cardNamed('标准'))
    const box = q('.ks-search input')[0]
    if (!box) {
      mustLand(false, 'kb-search-dirs-empty 目录层没有 .ks-search 输入框')
      notes.push('kb-search-dirs-empty: 目录层没找到 .ks-search 里的输入框')
    } else {
      await setSearchInput(box, '不存在的目录')
      const dirs = q('.ks-dir').length
      const title = q('.ks-empty-t').map((el) => el.textContent).join('|')
      mustLand(dirs === 0 && title === '没有符合搜索的目录',
        `kb-search-dirs-empty 空态不对：目录 ${dirs} 张（期望 0）、空态标题「${title}」（期望「没有符合搜索的目录」）`)
      notes.push(`kb-search-dirs-empty: 框里「不存在的目录」⇒ 目录 ${dirs} 张、空态标题「${title}」、`
        + `清除按钮 ${byText('.ks-empty-card button', '清除搜索') !== undefined ? '在' : '不在'}`)
    }
  } else if (how === 'kb-select') {
    // ⚠ 5h：先下钻到文件层（要选的是**文件行**的勾选框）。
    const rows = await gotoStdLeaf()
    const box = q('input[type=checkbox]')[0]
    mustLand(rows === 4 && box !== undefined, `kb-select 没走到文件层或没有勾选框（行 ${rows}／框 ${String(box !== undefined)}）`)
    notes.push(`kb-select: 先下钻（文件行 ${rows} 行）→ ${await click(box) ? '点了全选' : '没找到勾选框'}`
      + ` → 批量条 ${q('.ks-batch').length} 条`)
  } else if (how === 'ingest-batch') {
    const ok = await click(byText('button', '开始预览'))
    const batchRows = q('button').filter((b) => /\.pdf$/.test((b.textContent ?? '').trim())).length
    mustLand(ok && batchRows > 0, `ingest-batch ${ok ? '点了按钮' : '没找到「开始预览」'} 但批量行 ${batchRows} 条`)
    notes.push(`ingest-batch: ${ok ? '点了「开始预览」' : '没找到按钮'}`
      + ` → 批量行 ${batchRows} 条`
      + `，总账 ${container.textContent.includes('共评估') ? '有' : '无'}`
      + `，失败 ${container.textContent.includes('预览失败') ? container.textContent.split('预览失败')[1]?.slice(0, 60) : '无'}`)
  } else if (how === 'kb-empty-files') {
    // **5h 新增，替代原来的 kb-empty / kb-empty-folder**（那两个场景点的是**树节点**，
    // 而树在本轮被业主点名删掉了 ⇒ 它们的写法再也找不到节点）。
    // 新的取法**比旧的更真**：下钻到文件层 → 全选 → 批量删除 ⇒ 目录真的空了，
    // 于是拿到"这个文件夹还没有文件"这一支空态（**不是**被筛没的那一支）。
    await gotoStdLeaf()
    await click(q('input[type=checkbox]')[0])
    const selected = q('.ks-batch').length
    await click(byText('.ks-batch button', '批量删除'))
    const emptyTitle = q('.ks-empty-t').map((el) => el.textContent).join('|')
    mustLand(q('.ks-item').length === 0 && emptyTitle.includes('这个文件夹还没有文件'),
      `kb-empty-files 没拿到"本来就没文件"那一支空态：行 ${q('.ks-item').length}／空态「${emptyTitle}」`)
    notes.push(`kb-empty-files: 先下钻（4 行）→ 全选（批量条 ${selected} 条）→ 点「批量删除」`
      + ` → 文件行 ${q('.ks-item').length} 行，空态卡 ${q('.ks-empty-card').length} 张`
      + `，空态标题「${emptyTitle}」`)
  } else if (how === 'kb-tags-view') {
    // ⚠ 5h：标签视图的数据按**整库**统计（标签跨目录定义）；先落到一个有文件的库
    //   （自建夹「公司制度」只有一级 ⇒ 点它就直接是文件层），免得截出空视图。
    await gotoCard('公司制度')
    await click(cardNamed('公司制度'))
    const pill = byText('button', '标签')
    const ok = await click(pill)
    mustLand(ok && q('.ks-tagrow').length > 0, `kb-tags-view ${ok ? '切了标签视图' : '没找到「标签」'} 但标签行 ${q('.ks-tagrow').length} 行`)
    notes.push(`kb-tags-view: 先进「公司制度」（文件行 ${q('.ks-item').length} 行）→ ${ok ? '切到标签视图' : '没找到「标签」'}`
      + `（标签行 ${q('.ks-tagrow').length} 行）`)
  } else if (how === 'cap-dialog') {
    const card = q('.ks-cap-card').find((c) => q('.ks-cap-card').length > 0 && [...c.querySelectorAll('button')].some((b) => (b.textContent ?? '').includes('设置')))
    const ok = await click(card?.querySelector('button'))
    mustLand(ok && document.querySelectorAll('[role=dialog]').length > 0,
      `cap-dialog ${ok ? '点了「设置…」' : '没找到带「设置…」的卡'} 但对话框 ${document.querySelectorAll('[role=dialog]').length} 个`)
    notes.push(`cap-dialog: ${ok ? '开了第一张带「设置…」的窗' : '没找到'}`
      + `（宿主 Modal 是 portal 到 body 的，所以这里查的是 document）`)
  } else {
    /* ⚠ **兜底分支**（5i-补 2026-09-20）：名字在 `SCENARIOS` 表里、但这条 if/else 链**没有**任何
     * 分支接住它 ⇒ 当场报红（走下面 `landing` 那条路 = **exit 1**，并打出这个名字）。
     * ⚠ 为什么原来没有它：旧写法在循环**首**无条件 `handled.add(how)`，于是循环尾那条
     *   `if (!handled.has(how))` 是**死代码** —— 复核 verify-freeze-5i（`581d20d`）实测：
     *   往 `SCENARIOS` 加一个 `'kb-fake-probe'`（链里没有对应分支）再 `--interact kb-fake-probe`
     *   ⇒ **`interact: []`、exit 0**，正是本批要消灭的"什么都没做还成功"。现在该探针 **exit 1**。 */
    landing.push(`${how}: 在 SCENARIOS 表里但 if/else 链没有分支处理它（表与链不同步）`)
  }
}
/* ── 未处理的场景名 / 没落地的场景 ⇒ **exit 1**（不是 exit 0） ──
 * ⚠ 这一条与上面那个 exit 2 的分工：**名字根本不存在** = 参数错（2）；名字存在但这一跑**没做成**
 *   = 断言红（1）。两者都堵死"什么都没做还成功"那条路。 */
if (landing.length > 0) {
  console.error('❌ --interact 有场景**没落地**（这一跑不算通过）：')
  for (const p of landing) console.error(`   - ${p}`)
  console.error(`   跑过的场景：${interacts.join(' / ')}`)
  console.error('   ⇒ 每个分支都必须真的做到那一件事；做不到就**报红**，不许在 note 里写一句'
    + '"没找到"然后 exit 0（复核 verify-freeze-5h 实测过这种静默）。')
  process.exit(1)
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
/**
 * `--band-scroll` 的注入片段（见上面该参数的注释）。
 * ⚠ 这段直接拼进**测量脚本开头**（不是单独一个 <script>）：单独放一个 script 会先测后滚
 *   ⇒ 量到的 `scrollLeft` 还是 0，与图上的位移对不上。放开头 = 同一趟里"先滚再量"，两者自洽。
 * ⚠ 拼进的是 html 那个模板字符串 ⇒ 这段里**不许出现反引号**（用单引号拼字符串）。
 *   值只接受 `end` 或非负数；非法值直接 exit 2（**不静默忽略**）。
 */
let bandScrollTarget = 0
if (bandScrollRaw !== '' && bandScrollRaw !== '0') {
  // `end` 用 -1 当哨兵（"滚到最右"），不是"负数位置" ⇒ 先认它，再校验数字。
  bandScrollTarget = bandScrollRaw === 'end' ? -1 : Number(bandScrollRaw)
  if (bandScrollTarget !== -1 && (!Number.isFinite(bandScrollTarget) || bandScrollTarget < 0)) {
    console.error('❌ --band-scroll 只接受非负数或 end（拿到 ' + bandScrollRaw + '）'); process.exit(2)
  }
}
const bandScrollStmt = bandScrollTarget === 0 ? '' : [
  '    // 5h-补 --band-scroll：在**真 Chrome** 里把卡片带滚到指定位置（jsdom 那趟没有布局，滚不动）。',
  "    var kbc0 = document.querySelector('.ks-kbband-clip');",
  '    if (kbc0) {',
  '      var max0 = kbc0.scrollWidth - kbc0.clientWidth;',
  '      kbc0.scrollLeft = ' + (bandScrollTarget === -1 ? 'max0' : 'Math.min(' + String(bandScrollTarget) + ', max0)') + ';',
  '    }',
].join('\n')

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
${bandScrollStmt}
    var sels = ['#ks-shell','.ks-item','.ks-detail','.ks-rail','.ks-main','.ks-kb-card','.ks-cap-card',
                '.ks-batch','.ks-lhead','.ks-page-title','.ks-kb-tn','.ks-item-tags','.ks-item-add',
                '.ks-cap-engine','.ks-knob-label','.ks-kb-banner','.ks-field','.ks-tagrow',
                '.ks-list','.ks-filters','.ks-chip','.ks-status','.ks-item-more','.ks-item-title','.ks-item-sub',
                '.ks-check','.ks-item-meta','.ks-batch-btn','.ks-empty-card','.ks-empty-t','.ks-empty-d',
                '.ks-search','.ks-fileico','.ks-list-cap','.ks-cell','.ks-col-tags','.ks-col-date','.ks-col-status',
                '.ks-lhead-col','.ks-tag',
                /* 5h（2026-09-20）新 IA 的量点：卡片带（框/箭头）、面包屑、返回按钮、目录层。
                   ⚠ 注意这段在**模板字符串**里：注释里不许出现反引号（会截断模板，本轮已踩）。
                   ⚠ .ks-rail 与 .ks-kb-tn 留在名单里但**已经量不到**（树/目录轨被业主点名删了）
                     —— 不删这两个名字是为了让"量不到"在产物里**可见**（5h 之前的图里有值）。 */
                '.ks-kbband','.ks-kbband-nav','.ks-kbband-clip','.ks-crumb','.ks-crumb-path','.ks-back',
                '.ks-dirs','.ks-dir','.ks-dir-name',
                /* 5j（2026-09-20）页面留边：量这几个盒子的**绝对坐标**（.ks-page 是那个只管
                   container-type 的容器，.ks-kb/.ks-ing/.ks-mat 是三个页面根，.ks-split 是
                   "详情栏有没有被挤到第二行"的锚点）。**判据不在这里**（这里只报告），
                   Node 侧的 ksPadCheck 按 #kspad 逐条判 —— 见本段下面的 #kspad 段。 */
                '.ks-page','.ks-kb','.ks-ing','.ks-mat','.ks-split'];
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
    //   ctrls = 这一行**可见控件数** —— 就是 P1-1 的验收口径。
    // ⚠⚠ **2026-09-20 打回更正**：原来 ctrls 数的是**写死的类名清单**
    //   （.ks-check,.ks-status,.ks-item-more）⇒ 复核的变异 M2（把「＋标签」按钮加回行内、
    //   class=ks-item-add）**量不到**，26/26 照旧 PASS。改成与
    //   plugin/scripts/smoke-kb-page-render.mjs 的 CTRL_SEL **同一口径**（两处必须一起改）：
    //   按钮/输入类元素与控件角色，外加纯展示的 .ks-status（验收口径点名要算它）。
    //   行内再塞任何能点的东西 —— 不管挂什么类名 —— 这个数必 +1。
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
          var ctrls = el.querySelectorAll('button,input,select,textarea,[role=button],[role=checkbox],[role=switch],[contenteditable=true],.ks-status').length;
          return { rowW: Math.round(r0.width), nameW: rc ? Math.round(rc.width) : null,
                   fileNameW: rf ? Math.round(rf.width) : null,
                   nameRight: rc ? Math.round(rc.right - r0.left) : null,
                   tagsLeft: rt ? Math.round(rt.left - r0.left) : null,
                   deadGap: (rc && rt) ? Math.round(rt.left - rc.right) : null,
                   btnH: rm ? Math.round(rm.height) : null,
                   ctrls: ctrls };
        }) };
    }
    // 卡片带那条**横向滚动条**的机械证据（5h-补，2026-09-20）。
    // 业主原话是「一个小框下面自带一个左右翻页**滑动条**」⇒ 光有 overflow-x:auto 不算数，
    // 要在真 Chrome 里量到三件事：① 内容真的溢出（scrollWidth > clientWidth）；
    // ② 滚动位置真的能变（scrollLeft）；③ **那条条真的占位**（clientHeight < offsetHeight
    //    ⇒ 两值之差就是滚动条的厚度）。
    // ⚠ 这就是**为什么本脚本不再传 --hide-scrollbars**：那个开关会把滚动条**画都不画**，
    //   于是"到底有没有滑动条"在图上永远看不见（P1 那批图当初就是不想让滚动条入镜才加的）。
    //   ⚠⚠ 本段是**模板字符串里的一段 JS**：注释里同样**不许出现反引号**（会当场截断上面那个
    //      html 模板，症状是 node --check 报在 L571 的 const html 上，看着完全不相干）。
    //   去掉它之后：只有真溢出的容器才多出一条，其余截图不受影响（**不做**假滚动条）。
    // 借字段名（同 #cards / #cols 的先例，注释里写清就不算说谎）：
    //   x=clientWidth y=scrollWidth w=scrollLeft h=clientHeight fs=offsetHeight lh=可滚上限
    //   pad=cardsTotalW gap=scrollbarThickness radius=overflowX
    var kbc = document.querySelector('.ks-kbband-clip');
    if (kbc) {
      var kcs = getComputedStyle(kbc);
      var inner = kbc.querySelector('.ks-kb-cards');
      out['#kbband'] = {
        n: kbc.querySelectorAll('.ks-kb-card').length,
        x: Math.round(kbc.clientWidth), y: Math.round(kbc.scrollWidth), w: Math.round(kbc.scrollLeft),
        h: Math.round(kbc.clientHeight), fs: Math.round(kbc.offsetHeight),
        lh: String(Math.round(kbc.scrollWidth - kbc.clientWidth)),
        pad: inner ? Math.round(inner.getBoundingClientRect().width) : 0,
        gap: Math.round(kbc.offsetHeight - kbc.clientHeight),
        radius: kcs.overflowX,
      };
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
    // **卡片带里每一张卡的逐个宽/高**（5i 2026-09-20 收尾批）。
    // 为什么另开一个键：上面那个 #cards 是 .ks-kb-cards>*,.ks-cap-card **混在一起**的报告值，
    // 而且**全仓没有一条断言引用它** —— 复核 verify-freeze-5h 把列模板改成 60px 120px 200px
    // （三张卡三种宽）之后，渲染冒烟 51/51 仍然全绿。而"知识库卡片尺寸统一"是业主亲口点名的形态。
    // 这里只量**卡片带**里的卡，逐张报 {name,w,h}，Node 侧按"全等"下断言（见文件末尾 cardsCheck）。
    // 借字段名（同 #cards / #cols 的先例）：x=最小宽 y=最大宽 w=最小高 h=最大高，
    //   lh=逐张宽 pad=逐张高，items=逐张明细。
    // ⚠ 本段是模板字符串里的一段 JS：注释里**不许出现反引号**（第 11 次踩，见 UI-BASELINE 5h-补）。
    var bandCardEls = document.querySelectorAll('.ks-kbband .ks-kb-cards>.ks-kb-card');
    if (bandCardEls.length > 0) {
      var bw = [].map.call(bandCardEls, function (el) { return Math.round(el.getBoundingClientRect().width); });
      var bh = [].map.call(bandCardEls, function (el) { return Math.round(el.getBoundingClientRect().height); });
      out['#kbcards'] = {
        n: bandCardEls.length,
        x: Math.min.apply(null, bw), y: Math.max.apply(null, bw),
        w: Math.min.apply(null, bh), h: Math.max.apply(null, bh),
        fs: '', lh: bw.join(','), pad: bh.join(','), gap: '', radius: '',
        items: [].map.call(bandCardEls, function (el, i) {
          var t = el.querySelector('.ks-kb-ct');
          return { name: t ? (t.textContent || '').trim() : '', w: bw[i], h: bh[i] };
        }),
      };
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
    // 表格列对齐（P2 头条，2026-09-20）：**表头行与数据行的 computed 列模板必须逐字相同**。
    // 这是"列对齐"的唯一机械证据（jsdom 里量不到网格），所以放在真 Chrome 的这段脚本里量。
    // ⚠⚠ **P2 复核打回 B（2026-09-20，变异 M4）**：原来它只是**报告值**（没有断言）⇒ 把表头的
    //   grid-template-columns 改成与行不一致，本脚本照旧 exit 0、smoke 也 33/33 全绿。
    //   ⇒ 现在 Node 侧对它下断言（见文件末尾「#cols 的**真断言**」），三档由 smoke-kb-cols 逐档跑。
    // 借字段名：lh = 表头行的 grid-template-columns，pad = 第一数据行的；gap = 表头的 column-gap，
    // radius = **行**的 column-gap（同名借用，见 #cards 的先例 —— 注释里写清就不算说谎）。
    // n = 这一行里 cell 的个数（两个档都应是 5：窄档是隐藏两列，不是删 DOM）；x = 第一行的 cell 数。
    var lhead = document.querySelector('.ks-lhead');
    var firstRow = document.querySelector('.ks-item');
    if (lhead) {
      var lcs = getComputedStyle(lhead);
      var rcs = firstRow ? getComputedStyle(firstRow) : null;
      var ln = lhead.children.length;
      var rn = firstRow ? firstRow.children.length : 0;
      out['#cols'] = { n: ln, x: rn, y: 0, w: 0, h: 0, fs: '',
                       lh: lcs.gridTemplateColumns, pad: rcs ? rcs.gridTemplateColumns : '(没有数据行)',
                       gap: lcs.columnGap || lcs.gap, radius: rcs ? (rcs.columnGap || rcs.gap) : '(没有数据行)' };
    }
    // 状态徽章的**逐个颜色 + 几何**（P2 复核打回 A，2026-09-20）：用来在 PNG 上按 rect 裁剪、
    // 数"等于文字色的像素数"，从而机械判"深色下「已废止」的文字读不读得出来"。
    // ⚠ 这段只**报告**（不在浏览器里判红）：像素计数在 Node 侧做（plugin/scripts/ui-badge-pixels.mjs）。
    var stEls = document.querySelectorAll('.ks-status');
    if (stEls.length > 0) {
      out['#status'] = { n: stEls.length, x: 0, y: 0, w: 0, h: 0, fs: '', lh: '', pad: '', gap: '', radius: '',
        items: [].map.call(stEls, function (el) {
          var r = el.getBoundingClientRect();
          var s = getComputedStyle(el);
          return { text: (el.textContent || '').trim(), x: Math.round(r.x), y: Math.round(r.y),
                   w: Math.round(r.width), h: Math.round(r.height),
                   color: s.color, bg: s.backgroundColor, border: s.borderTopColor };
        }) };
    }
    // **页面留边**（5j，2026-09-20）：量"元素外缘到 shell **内容边**的最小距离"。
    // 业主原话是「窗口四周要留点边啊，你这按钮都快跑到侧边栏外面去了」⇒ 判据变成可量的：
    // 页面根 / 卡片带外框 / 表格容器 / 批量条 / 页内按钮行 / 空态卡 的**外缘**
    // 到 shell 内容边 ≥ --ks-page-pad-x（规范值见 docs/UI-BASELINE.md 第二节，Node 侧钉数）。
    // ⚠ **为什么减掉 shell 的 padding**：#ks-shell 那 12px 是**本脚本自己的假外壳**（见 ks-shell-css），
    //   不是我们样式的贡献。不减掉它，我们的留边会被假外壳"垫高"，而变异（把留边改成 0）
    //   还剩 12px 兜着 —— 那正是"靠宿主外壳留边"的假绿。d/dR 是**我们自己**的距离；
    //   dRaw/dRRaw 是到 shell 外框（= 窗口代理）的距离，一并报出（业主说的"窗口四周"）。
    // ⚠ 页面根看**内容盒**（padding 在它自己身上，它的边框盒外缘本来就贴着 shell 内容边 ——
    //   那是"根铺满"的正常形态，不是"内容贴边"）；其余元素看**边框盒**（外框就是用户看到的边）。
    // 借字段名（同 #cards / #cols 的先例）：x=shell 内容盒左缘 y=shell 内容盒右缘
    //   w=shell 宽 h=shell 高 fs='' lh='' pad=shell 自己的左右 padding gap='' radius=''。
    var shellEl = document.getElementById('ks-shell');
    if (shellEl) {
      var shR = shellEl.getBoundingClientRect();
      var shCs = getComputedStyle(shellEl);
      var shPl = parseFloat(shCs.paddingLeft); if (!isFinite(shPl)) shPl = 0;
      var shPr = parseFloat(shCs.paddingRight); if (!isFinite(shPr)) shPr = 0;
      var cLeft = shR.left + shPl;
      var cRight = shR.right - shPr;
      // ⚠ 这一串**必须与 docs/UI-BASELINE.md 第二节的适用面一致**（Node 侧 ksPadCheck 逐条判，
      //   并有"文档适用面 ↔ 本表"的棘轮，见 PAD_SUBJECTS_ALL）。
      //   isRoot=1 表示"看它的内容盒"，0 = "看它的边框盒"。
      var padSel = [['.ks-kb', 1], ['.ks-ing', 1], ['.ks-mat', 1],
                    ['.ks-kbband', 0], ['.ks-list', 0], ['.ks-batch', 0], ['.ks-dirs', 0],
                    ['.ks-page-head', 0], ['.ks-kb-row', 0], ['.ks-empty-card', 0]];
      var padItems = [];
      for (var pi = 0; pi < padSel.length; pi++) {
        var pel = document.querySelector(padSel[pi][0]);
        // ⚠⚠ 5j-补（2026-09-20，复核 verify-freeze-5j 打回 E①）：**缺失不再静默跳过**。
        //   原写法是 find-or-continue ⇒ 复核的变异 M6（把 .ks-dirs 的类名改掉，元素**整个从 DOM 消失**）
        //   两侧全绿：items 里少一项，而 Node 侧只判"量到的那些" ⇒ "元素没了"与"留边合规"长得一样。
        //   现在缺失也 push 一条 missing:true（d/dR 全 null），由 Node 侧按**声明的期望集合**
        //   （PAD_REQUIRED）逐条判：声明里该有的、这里没有 ⇒ 当场红。
        if (!pel) { padItems.push({ sel: padSel[pi][0], root: padSel[pi][1] === 1, missing: true,
                                   d: null, dR: null, dRaw: null, dRRaw: null,
                                   padL: null, padR: null, padT: null, padB: null, h: null, n: 0 });
                     continue; }
        var isRoot = padSel[pi][1] === 1;
        var pR = pel.getBoundingClientRect();
        var pCs = getComputedStyle(pel);
        var ppl = parseFloat(pCs.paddingLeft); if (!isFinite(ppl)) ppl = 0;
        var ppr = parseFloat(pCs.paddingRight); if (!isFinite(ppr)) ppr = 0;
        var ppt = parseFloat(pCs.paddingTop); if (!isFinite(ppt)) ppt = 0;
        var ppb = parseFloat(pCs.paddingBottom); if (!isFinite(ppb)) ppb = 0;
        var vL = isRoot ? pR.left + ppl : pR.left;
        var vR = isRoot ? pR.right - ppr : pR.right;
        // 页面根自己的**生效留边**（宽/窄两档由 .ks-page 的容器查询切）：
        // 报出来给 Node 侧核对"量到的档位"与"该档的规范值"是不是同一个。
        // h/padT/padB 是给**批量条**用的：留边会挤窄可用宽，条子会从一行变两行
        // （5j 实测：520 下 40px→72px）⇒ 这个高度得有断言兜着，不能只靠看图。
        padItems.push({ sel: padSel[pi][0], root: isRoot,
                        d: Math.round(vL - cLeft), dR: Math.round(cRight - vR),
                        dRaw: Math.round(vL - shR.left), dRRaw: Math.round(shR.right - vR),
                        padL: Math.round(ppl), padR: Math.round(ppr),
                        padT: Math.round(ppt), padB: Math.round(ppb), h: Math.round(pR.height), n: 1 });
      }
      var pageBox = document.querySelector('.ks-page');
      out['#kspad'] = { n: padItems.length, x: Math.round(cLeft), y: Math.round(cRight),
                        w: Math.round(shR.width), h: Math.round(shR.height), fs: '', lh: '',
                        pad: String(Math.round(shPl)) + '/' + String(Math.round(shPr)), gap: '',
                        radius: '', pageW: pageBox ? Math.round(pageBox.getBoundingClientRect().width) : 0,
                        pageN: document.querySelectorAll('.ks-page').length, items: padItems };
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
  // ⚠ **5h-补（2026-09-20）：去掉了 `--hide-scrollbars`。** 业主点名的"滑动条"必须**在图上看得见**
  //   （那是验收标准本身），而这个开关会让滚动条**根本不画** ⇒ 之前那条卡片带的滚动条在截图里
  //   永远不存在。去掉后只有**真溢出**的容器会多出一条（没有假滚动条）；宽度/高度都可能因此变一点，
  //   所以 5h-补 的图与断言用的是同一趟实测值。
  '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
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

/* ══════════════ #cols 的**真断言**（P2 复核打回 B，2026-09-20；变异 M4 现在会红） ══════════════
 * 复核的变异 M4：把表头与行的 grid-template-columns 改成**不一致**（header 416px 100px …
 * vs row 444px 72px …）⇒ 当时本脚本 exit 0、smoke 33/33 绿 —— 因为 #cols 只是报告值。
 * "列对齐"（文档 §7.7/§8.1 的验收）不能只有一个报告值兜着 ⇒ 这里把它变成**带诊断的失败**：
 *   ① 表头与第一行的 computed grid-template-columns 必须**逐字相同**；
 *   ② 两者的 computed column-gap 也必须逐字相同（列对齐含间距，不只是列宽）；
 *   ③ 取到空值/取不到值 ⇒ 也算红（"没验到"不能渲染成"通过"）。
 * 适用面：只有"有 .ks-lhead 且这一跑真的有数据行"的页面/场景才判；其余**明说没判**（colsCheck.skipReason），
 * 不静默通过。三档（520/1300/900）由 scripts/smoke-kb-cols.mjs 逐档跑本脚本，任一档红即红。 */
const cols = measured['#cols']
const colsProblems = []
let colsSkipReason = null
if (cols === undefined) {
  colsSkipReason = `本页没有 .ks-lhead（page=${page}），列对齐不适用`
} else if (cols.pad === '(没有数据行)' || cols.radius === '(没有数据行)') {
  colsSkipReason = '这一跑没有数据行（空态截图），没有可比的行'
} else {
  if (!cols.lh || !cols.pad) {
    colsProblems.push(`取到空值（取不到值本身就不算验过）：表头 ${JSON.stringify(cols.lh)} / 行 ${JSON.stringify(cols.pad)}`)
  } else if (cols.lh !== cols.pad) {
    colsProblems.push(`表头与行的 grid-template-columns 不一致：表头 ${JSON.stringify(cols.lh)} / 行 ${JSON.stringify(cols.pad)}`)
  }
  if (!cols.gap || !cols.radius) {
    colsProblems.push(`column-gap 取到空值：表头 ${JSON.stringify(cols.gap)} / 行 ${JSON.stringify(cols.radius)}`)
  } else if (cols.gap !== cols.radius) {
    colsProblems.push(`表头与行的 column-gap 不一致：表头 ${JSON.stringify(cols.gap)} / 行 ${JSON.stringify(cols.radius)}`)
  }
}
const colsCheck = {
  checked: colsProblems.length === 0 && colsSkipReason === null,
  skipReason: colsSkipReason,
  problems: colsProblems,
  header: cols?.lh ?? null,
  row: cols?.pad ?? null,
  gapHeader: cols?.gap ?? null,
  gapRow: cols?.radius ?? null,
}

/* ══════════ `#kbcards` 的**真断言**（5i 2026-09-20 收尾批；卡片尺寸统一） ══════════
 * 复核 `verify-freeze-5h` 的变异：把卡片带里 `.ks-kb-cards` 的列模板改成 `60px 120px 200px`
 * （三张卡三种宽）⇒ **渲染冒烟 51/51 依旧绿** —— 因为 `#cards` 只是**报告值**，全仓没有断言引用它。
 * "知识库卡片尺寸统一"是业主点名的形态，不能只有一个报告值兜着 ⇒ 这里把它变成**带诊断的失败**：
 *   ① 卡片带里**每一张卡的宽度必须全等**（真 Chrome 的 `getBoundingClientRect`，逐张打印实际值）；
 *   ② **每一张卡的高度也必须全等**；
 *   ③ 量到 0 / 取不到值也算红（"没验到"不能渲染成"通过"）。
 * ⚠ 容差 1px：值已经 `Math.round`，等宽卡在亚像素上也可能差 1（本轮实测是 172×5 / 136×5，
 *   一模一样；容差只是防四舍五入的假红）。**不等宽 >1px 必红**。
 * 适用面：只有"这一跑真的有卡片带"的页面才判（kb 页一定判）；其余页面**明说没判**（skipReason）。
 * 变异实测（本批）：给第 2 张卡加 `.ks-kbband .ks-kb-card:nth-child(2){flex:0 0 60px}`
 *   ⇒ 本脚本 exit 1（宽度 172,60,172,172,172）；还原即绿。三档由 smoke-kb-cols 逐档跑。
 * ⚠ **更正（5i-补 2026-09-20，复核 verify-freeze-5i）——两侧判的不是同一件事，别互相顶替**：
 *   · jsdom 侧（`smoke-kb-page-render.mjs` 的 `bandFlex`）钉的是 **computed `flex` 的声明串**
 *     逐字相同 —— 它**没有布局引擎**，量不到像素。**逐卡覆盖 token** 那种变异
 *     （`.ks-kbband .ks-kb-card:nth-child(2){--ks-band-card-w:60px}`）声明串**仍然相同** ⇒
 *     jsdom `PASS (67/67)` 全绿（实测），对这类**全盲**。
 *   · **像素级等宽/等高只有这一处**（本脚本 `cardsCheck`，量 `getBoundingClientRect`）：
 *     同一变异在这里 `卡片**宽度不全等**："172,81,172,172,172"` ⇒ **exit 1**（实测）。
 *   · 所以"卡片尺寸统一"被钉住 = 两侧**同时**成立；`smoke-kb-cols.mjs` 三档对每一档
 *     **同时**要求 `colsCheck.checked` 与 `cardsCheck.checked`（任一"没判到"即算失败）。
 * ⚠ 「真 Chrome」是**约定叫法**：本脚本按 `BROWSERS` 顺序找浏览器，**本机实际命中的是
 *   `msedge.exe`**（Edge/Chromium 内核）。措辞不精确，结论不变（同一内核、同一像素口径）。 */
const kbc = measured['#kbcards']
const cardsProblems = []
let cardsSkipReason = null
if (kbc === undefined) {
  cardsSkipReason = `本页没有卡片带（page=${page}），卡片尺寸统一不适用`
} else if (kbc.n < 2) {
  cardsSkipReason = `卡片带里只有 ${String(kbc.n)} 张卡，没有"全等"可比`
} else {
  const ws = String(kbc.lh).split(',').map((v) => Number(v.trim()))
  const hs = String(kbc.pad).split(',').map((v) => Number(v.trim()))
  const bad = (arr) => arr.length !== kbc.n || arr.some((v) => !Number.isFinite(v) || v <= 0)
  const spread = (arr) => Math.max(...arr) - Math.min(...arr)
  if (bad(ws)) {
    cardsProblems.push(`有卡的宽度量不到（<=0 或个数不对）：${JSON.stringify(String(kbc.lh))}（期望 ${String(kbc.n)} 个正数）`)
  } else if (spread(ws) > 1) {
    cardsProblems.push(`卡片**宽度不全等**：${JSON.stringify(kbc.lh)}`
      + `（逐张 ${JSON.stringify((kbc.items ?? []).map((it) => `${it.name}=${String(it.w)}px`))}）`)
  }
  if (bad(hs)) {
    cardsProblems.push(`有卡的高度量不到（<=0 或个数不对）：${JSON.stringify(String(kbc.pad))}（期望 ${String(kbc.n)} 个正数）`)
  } else if (spread(hs) > 1) {
    cardsProblems.push(`卡片**高度不全等**：${JSON.stringify(kbc.pad)}`
      + `（逐张 ${JSON.stringify((kbc.items ?? []).map((it) => `${it.name}=${String(it.h)}px`))}）`)
  }
}
const cardsCheck = {
  checked: cardsProblems.length === 0 && cardsSkipReason === null,
  skipReason: cardsSkipReason,
  problems: cardsProblems,
  count: kbc?.n ?? null,
  widths: kbc?.lh ?? null,
  heights: kbc?.pad ?? null,
  items: kbc?.items ?? null,
}

/* ══════════ `#kspad` 的**真断言**（5j，2026-09-20；业主：「窗口四周要留点边啊」） ══════════
 * 来源：业主 2026-09-20 原话「窗口四周要留点边啊，你这按钮都快跑到侧边栏外面去了，你改一下 UI
 *   设计规范，然后应用上」。改前**只有报告值没有断言**的风险与本仓已踩三次的坑一模一样
 *   （`#cols` 变异 M4、`#cards` 变异逐卡覆盖 token 都是"报告值全绿"）⇒ 这里一次立成真断言。
 *
 * 判据（与 docs/UI-BASELINE.md 第二节「页面留边」逐字一致）：
 *   页面根（.ks-kb/.ks-ing/.ks-mat，看**内容盒**）/ 卡片带外框 `.ks-kbband` / 表格容器 `.ks-list`
 *   / 批量条 `.ks-batch` / 目录层 `.ks-dirs` / 页头 `.ks-page-head` / 页内按钮行 `.ks-kb-row`
 *   / 空态卡 `.ks-empty-card` 的**外缘**到 shell **内容边**的最小距离 ≥ 该档的 --ks-page-pad-x。
 *
 * ⚠ **期望值必须是"冻结的规范值"，不能从被测元素自己的 computed padding 反推** ——
 *   否则"把留边改成 0"会让期望值一起变成 0，断言恒真（那是本仓最恨的假绿）。所以：
 *   ① 下面三个 PAGE_PAD_* 是**规范锚点**（冻结常数，出处 UI-BASELINE 第二节 + 5j）；
 *   ② 同时从 `ksGuideStyles.ts` **抠出** :root 里的 token 定义与 @container 阈值，三者必须一致
 *      —— 谁改了 token 而没改这里（或反过来），这一条就红（"规范 ↔ 实现"的棘轮）。
 * ⚠ `d`/`dR` 是**我们自己样式**给出的距离（已减掉本脚本假外壳 #ks-shell 的 12px padding）；
 *   `dRaw`/`dRRaw` 是到 shell 外框（窗口代理）的距离。两者都判 —— 业主说的是"窗口四周"。
 * ⚠ 适用面：`.ks-page` 不在这一跑里（页面根没被包住）⇒ **明说没判**（ksPadCheck.skipReason），
 *   不静默通过；量到的档位由 `.ks-page` 的实测宽与阈值比出来（与浏览器里容器查询同一口径）。 */
const PAGE_PAD_X_NARROW = 16
const PAGE_PAD_X_WIDE = 24
const PAGE_PAD_BREAKPOINT = 660
/**
 * > ⚠⚠ **5j-补（2026-09-20）：复核 `verify-freeze-5j` 打回 E① —— "元素整个消失也不红"。**
 * > 复核的变异 **M6**：把 `.ks-dirs`（规范第二节明文点名的适用面之一）的类名改掉让它从 DOM 消失
 * > ⇒ `ui-render-shot` **exit 0 自检通过**（items 里直接少一项）、`smoke-kb-page-render` **72/72 PASS**。
 * > 根因就是下面这张表**原本不存在**：页面侧 `padSel` 找不到元素就 `continue`，Node 侧只判"量到的那些"
 * > ⇒ "元素被改名/删掉"与"留边合规"不可分辨。**量不到就必须判红，不许当通过。**
 *
 * 两件事一起做（缺一不可）：
 *   ① 页面侧缺失也上报（`missing:true`，见注入脚本里那段）；
 *   ② Node 侧按**本表声明的期望集合**判存在性 —— 声明里该有、items 里没有 ⇒ 红。
 *      ⚠ 不同页/不同场景本来就有不同的元素集（能力页没有卡片带、入库页只有一个根），
 *      所以期望**必须按 (page|interact) 显式声明**，不能"要求全都有"（那会假红）也不能"找到就判"
 *      （那正是被打回的假绿）。**组合没在本表里 ⇒ `coverageDeclared=false`，明说"这一跑没判覆盖面"**
 *      （不静默通过；门禁里跑的每一组都在本表里）。
 *   ③ 本表**并集**必须覆盖 `PAD_SUBJECTS_ALL`（= 规范第二节适用面的机器副本）——少一个就红：
 *      这就是"规范加了适用面、脚本没跟上"的棘轮（同 token/阈值的做法）。
 */
const PAD_SUBJECTS_ALL = ['.ks-kb', '.ks-ing', '.ks-mat', '.ks-kbband', '.ks-list', '.ks-batch',
  '.ks-dirs', '.ks-page-head', '.ks-kb-row', '.ks-empty-card']
/** 键 = `${page}|${interacts.join('+')}`（与 `--page`/`--interact` 同一口径）。值 = 这一跑**必须量到**的选择器。 */
const PAD_REQUIRED = {
  'kb|': ['.ks-kb', '.ks-kbband', '.ks-dirs', '.ks-page-head', '.ks-kb-row'],
  'kb|kb-select': ['.ks-kb', '.ks-kbband', '.ks-list', '.ks-batch', '.ks-page-head', '.ks-kb-row'],
  'kb|kb-files': ['.ks-kb', '.ks-kbband', '.ks-list', '.ks-page-head', '.ks-kb-row'],
  'kb|kb-empty-files': ['.ks-kb', '.ks-kbband', '.ks-list', '.ks-page-head', '.ks-kb-row', '.ks-empty-card'],
  'capabilities|': ['.ks-kb', '.ks-page-head', '.ks-kb-row'],
  'ingest|ingest-batch': ['.ks-ing'],
  'materials|': ['.ks-mat'],
}
const padComboKey = `${page}|${interacts.join('+')}`
const padRequired = PAD_REQUIRED[padComboKey] ?? null
const stylesSrcPath = join(pluginRoot, 'client', 'ksGuideStyles.ts')
const baselineDocPath = join(repoRoot, 'docs', 'UI-BASELINE.md')
let ksPadTokenProblems = []
try {
  const stylesSrc = await readFile(stylesSrcPath, 'utf8')
  const tokenOf = (name) => {
    const m = new RegExp(`--${name}\\s*:\\s*(\\d+)px`).exec(stylesSrc)
    return m === null ? null : Number(m[1])
  }
  const tkNarrow = tokenOf('ks-page-pad-x-narrow')
  const tkWide = tokenOf('ks-page-pad-x-wide')
  if (tkNarrow !== PAGE_PAD_X_NARROW) {
    ksPadTokenProblems.push(`ksGuideStyles.ts 的 --ks-page-pad-x-narrow = ${JSON.stringify(tkNarrow)}，`
      + `而本脚本冻结的规范值是 ${String(PAGE_PAD_X_NARROW)}（改了 token 就要同步 UI-BASELINE 第二节与本脚本）`)
  }
  if (tkWide !== PAGE_PAD_X_WIDE) {
    ksPadTokenProblems.push(`ksGuideStyles.ts 的 --ks-page-pad-x-wide = ${JSON.stringify(tkWide)}，`
      + `而本脚本冻结的规范值是 ${String(PAGE_PAD_X_WIDE)}（同上）`)
  }
  const mBp = /@container\s*\(min-width:\s*(\d+)px\)\s*\{([^}]*)\}/g
  let bp = null
  // ⚠ 只认**页面留边那一条** @container（body 里出现 .ks-page）—— 本表里还有一条给
  //   `.ks-list` 切列档的 `@container (min-width:660px)`，取"第一个 @container"会认错对象。
  for (const m of stylesSrc.matchAll(mBp)) {
    if (m[2].includes('.ks-page')) { bp = Number(m[1]); break }
  }
  if (bp !== PAGE_PAD_BREAKPOINT) {
    ksPadTokenProblems.push(`ksGuideStyles.ts 里页面留边的 @container 阈值 = ${JSON.stringify(bp)}，`
      + `而本脚本冻结的是 ${String(PAGE_PAD_BREAKPOINT)}（宽/窄两档的切换点只许有一个数）`)
  }
  /* 「规范 ↔ 脚本」的**主体表棘轮**（5j-补）：从 UI-BASELINE 第二节的**适用面**那一段里抠出所有
     `.ks-*` 选择器，要求与本脚本的 PAD_SUBJECTS_ALL **一模一样**（多一个/少一个都红）。
     为什么必须抠文档而不是"抄一份在脚本里"：规范里加了适用面（例如再加一个 `.ks-x`）而脚本没跟上，
     那种漂移正是本轮被打回的那一类 —— 抄一份等于允许两份各自漂移。 */
  const docSrc = await readFile(baselineDocPath, 'utf8')
  const segStart = docSrc.indexOf('**适用面**')
  const segEnd = segStart === -1 ? -1 : docSrc.indexOf('**判据', segStart)
  if (segStart === -1 || segEnd === -1) {
    ksPadTokenProblems.push(`在 ${baselineDocPath} 里找不到「**适用面** …**判据」这一段`
      + '（抠不到规范的主体表 ⇒ 这条棘轮无从判定，不算验过）')
  } else {
    const docSubjects = [...new Set((docSrc.slice(segStart, segEnd).match(/\.ks-[a-z0-9-]+/g) ?? []))]
    const onlyDoc = docSubjects.filter((s) => !PAD_SUBJECTS_ALL.includes(s))
    const onlyScript = PAD_SUBJECTS_ALL.filter((s) => !docSubjects.includes(s))
    if (onlyDoc.length > 0 || onlyScript.length > 0) {
      ksPadTokenProblems.push('规范第二节的适用面与本脚本的 PAD_SUBJECTS_ALL 不一致：'
        + `只在规范里=[${onlyDoc.join(' ')}]、只在脚本里=[${onlyScript.join(' ')}]`
        + '（两边必须一模一样）。'
        /* ⚠ 5j-补-补-补（2026-09-20）：复核 `verify-freeze-5jb` 指出原来那句"改了规范就要同步脚本"
           **低估了**改动面；`verify-freeze-5jbb` 又指出"四处"的清单与实际副本**不重合**。这里按完整
           副本清单写清：① 规范第二节「适用面」② 本文件的 PAD_SUBJECTS_ALL ③ 本文件的 PAD_REQUIRED
           ④ smoke-kb-pad-pixels 的 SPEC_SUBJECTS ⑤ jsdom 的 PAD_SUBJECTS ⑥ 注入脚本的 padSel
           ⑦ 第六节 5j① 的表格（散文）。已绑棘轮的：①②④ 逐字一致、②③ 并集 + "声明的键必须真被跑过"；
           ⑥ 是**间接**被保护的（不在 padSel 里 ⇒ 每一跑都"没量到" ⇒ 红）；⑤⑦ 只有散文性同步。 */
        + '⚠ 副本清单：规范第二节 / 本文件 PAD_SUBJECTS_ALL / 本文件 PAD_REQUIRED / '
        + 'smoke-kb-pad-pixels 的 SPEC_SUBJECTS（前四者已互相绑成棘轮）+ jsdom 的 PAD_SUBJECTS '
        + '+ 注入的 padSel + 第六节 5j① 表格。要收窄规范得**同时改前四处**；改一两处**必红**'
        + '（红在哪一条取决于改的是哪两处）。')
    }
  }
} catch (e) {
  ksPadTokenProblems.push(`读不到 ${stylesSrcPath} 或 ${baselineDocPath}：${String(e)}（读不到就不算验过）`)
}
/* 本表并集必须覆盖规范的全部适用面（5j-补）：**声明里没出现过的科目 = 没有任何一跑在判它**。
   这正是复核 M6 的另一半 —— 元素"有人在判"才算被保护。 */
{
  const covered = new Set(Object.values(PAD_REQUIRED).flat())
  const uncovered = PAD_SUBJECTS_ALL.filter((s) => !covered.has(s))
  if (uncovered.length > 0) {
    ksPadTokenProblems.push(`规范点名的这些适用面在 PAD_REQUIRED 里**没有任何一跑声明**（等于没人判）：`
      + `[${uncovered.join(' ')}] —— 给它们各补一组声明；真要从规范里去掉，得**四处一起**改`
      + '（规范第二节 / PAD_SUBJECTS_ALL / PAD_REQUIRED / smoke-kb-pad-pixels 的 SPEC_SUBJECTS）')
  }
  const unknown = [...covered].filter((s) => !PAD_SUBJECTS_ALL.includes(s))
  if (unknown.length > 0) {
    ksPadTokenProblems.push(`PAD_REQUIRED 里出现了不在规范适用面里的选择器：[${unknown.join(' ')}]`
      + '（要么它该进规范，要么表里写错了）')
  }
}

const ksp = measured['#kspad']
const ksPadProblems = ksPadTokenProblems.slice()
let ksPadSkipReason = null
if (ksp === undefined) {
  ksPadSkipReason = `这一跑没量到 #kspad（page=${page}）—— 量不到不算验过`
} else if (ksp.pageN !== 1) {
  ksPadSkipReason = `.ks-page 容器实测 ${String(ksp.pageN)} 个（期望恰好 1 个）—— 页面根没被包住，这一跑不判`
} else if ((ksp.items ?? []).length === 0) {
  ksPadSkipReason = '这一跑一个"不得贴边"的元素都没量到 —— 量不到不算验过'
} else {
  /* ── 5j-补：**存在性先判**（复核 E① 的正解）──
     声明里该有的元素，items 里必须有一条**非 missing** 的记录。缺了就是红；
     ② 「组合没声明」⇒ 不判存在性，但**明说没判**（coverageDeclared=false），不许当通过。 */
  const items = ksp.items ?? []
  const bySel = new Map(items.map((it) => [it.sel, it]))
  if (padRequired === null) {
    ksPadProblems.push(`这一跑的组合 ${padComboKey} **没有在 PAD_REQUIRED 里声明期望元素**`
      + ' ⇒ 存在性（"元素被改名/删掉"这一类）这一跑**没判**；要把这一跑纳入保护就给它加一行声明')
  } else {
    for (const sel of padRequired) {
      const it = bySel.get(sel)
      if (it === undefined || it.missing === true) {
        ksPadProblems.push(`**规范点名的适用面 ${sel} 这一跑根本没量到**（元素消失/改名都会这样）`
          + ' —— 量不到就不算验过；改回类名，或按设计把它从适用面里去掉（同时改规范与 PAD_REQUIRED）')
      }
    }
  }
  /* 档位**不许只由被测容器自己的实宽决定**（复核 E⑥ 的软点 M7：给 `.ks-page` 强制 width:600px
     后，1300 的壳里被读成"窄档"、期望 16 ⇒ exit 0 通过）。这里再拿 shell 的**内容宽**独立钉一次：
     ① `.ks-page` 是页面根的唯一容器，它就该**铺满** shell 内容盒（差 >1px 说明有东西在偷偷缩它）；
     ② 档位必须与 shell 内容宽一致（壳够宽 ⇒ 必须宽档）。 */
  const [shPl, shPr] = String(ksp.pad ?? '0/0').split('/').map(Number)
  const shellContentW = Number(ksp.w) - (Number.isFinite(shPl) ? shPl : 0) - (Number.isFinite(shPr) ? shPr : 0)
  if (Math.abs(Number(ksp.pageW) - shellContentW) > 1) {
    ksPadProblems.push(`.ks-page 实测宽 ${String(ksp.pageW)}px 与 shell 内容宽 ${String(shellContentW)}px 不符`
      + '（页面根应当铺满内容盒）—— 那会让"档位"读成错的那一档，留边期望跟着错')
  }
  const wide = Number(ksp.pageW) >= PAGE_PAD_BREAKPOINT
  const wideByShell = shellContentW >= PAGE_PAD_BREAKPOINT
  if (wide !== wideByShell) {
    ksPadProblems.push(`档位与 shell 内容宽不一致：按 .ks-page 实宽(${String(ksp.pageW)}px)读成`
      + `${wide ? '宽' : '窄'}档，按 shell 内容宽(${String(shellContentW)}px)应是${wideByShell ? '宽' : '窄'}档`
      + ' —— 档位必须由壳宽独立钉住，不能只信被测容器自己')
  }
  const expect = wide ? PAGE_PAD_X_WIDE : PAGE_PAD_X_NARROW
  for (const it of items) {
    const tag = `${it.sel}${it.root === true ? '（页面根，看内容盒）' : ''}`
    if (it.missing === true) continue
    if (!Number.isFinite(it.d) || !Number.isFinite(it.dR)) {
      ksPadProblems.push(`${tag} 的左右留边量不到（d=${JSON.stringify(it.d)} dR=${JSON.stringify(it.dR)}）`)
      continue
    }
    if (it.d < expect) {
      ksPadProblems.push(`${tag} **左缘贴边**：到 shell 内容边只有 ${String(it.d)}px < 该档留边 ${String(expect)}px`
        + `（到 shell 外框 ${String(it.dRaw)}px）`)
    }
    if (it.dR < expect) {
      ksPadProblems.push(`${tag} **右缘贴边**：距 shell 内容边右缘只有 ${String(it.dR)}px < 该档留边 ${String(expect)}px`
        + `（距 shell 外框 ${String(it.dRRaw)}px）`)
    }
    if (it.dRaw < expect) {
      ksPadProblems.push(`${tag} **距窗口代理左缘**只有 ${String(it.dRaw)}px < ${String(expect)}px`
        + '（连本脚本假外壳那 12px 一起算上都不够 ⇒ 真机上只会更窄）')
    }
    if (it.dRRaw < expect) {
      ksPadProblems.push(`${tag} **距窗口代理右缘**只有 ${String(it.dRRaw)}px < ${String(expect)}px（同上）`)
    }
    if (it.root === true && it.padL !== expect) {
      ksPadProblems.push(`${tag} 自己声明的 padding-left = ${String(it.padL)}px，`
        + `与这一档（${wide ? '宽' : '窄'}档，页面根宽 ${String(ksp.pageW)}px）的规范值 ${String(expect)}px 不符`
        + ' —— 档位没切对，或 token 没被消费')
    }
  }
  /* 批量条**不许因为留边被挤成两行**（5j 的连带修复，见 ksGuideStyles 的窄档紧凑规则）：
     单行 = padding-top + --ks-btn-h-sm(24) + padding-bottom（实测 520 下 8+24+8 = 40）；
     两行 = 72（5j 变异实测）。判据留 8px 余量：h > 单行预算 + 8 就是折行了。 */
  const batchItem = (ksp.items ?? []).find((it) => it.sel === '.ks-batch')
  const batchOneRow = batchItem === undefined ? null : batchItem.padT + 24 + batchItem.padB
  if (batchItem !== undefined && Number.isFinite(batchItem.h) && batchItem.h > batchOneRow + 8) {
    ksPadProblems.push(`.ks-batch **被挤成两行**（高 ${String(batchItem.h)}px > 单行预算 ${String(batchOneRow)}px + 8）`
      + ' —— 留边吃掉可用宽之后条子折行了；按现有 @container 口径在窄档把它收紧凑'
      + '（ksGuideStyles.ts 的 `@container (max-width:520px){.ks-batch{...}}`）')
  }
}
const ksPadCheck = {
  checked: ksPadProblems.length === 0 && ksPadSkipReason === null,
  skipReason: ksPadSkipReason,
  problems: ksPadProblems,
  tier: ksp === undefined ? null : (Number(ksp.pageW) >= PAGE_PAD_BREAKPOINT ? 'wide' : 'narrow'),
  pageW: ksp?.pageW ?? null,
  shellPad: ksp?.pad ?? null,
  expect: ksp === undefined ? null : (Number(ksp.pageW) >= PAGE_PAD_BREAKPOINT ? PAGE_PAD_X_WIDE : PAGE_PAD_X_NARROW),
  /* 5j-补（复核 E① 的正解）：**这一跑到底判了哪些元素的"存在性"**，以及有没有没判的科目。
     门禁里的 `smoke-kb-pad-pixels.mjs` 要求 coverageDeclared=true —— 没声明就等于没保护。 */
  comboKey: padComboKey,
  coverageDeclared: padRequired !== null,
  required: padRequired,
  missingSubjects: (ksp?.items ?? []).filter((it) => it.missing === true).map((it) => it.sel),
  items: ksp?.items ?? null,
}

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
  colsCheck,
  cardsCheck,
  ksPadCheck,
  renderedChars: rendered.length,
  bundle: { js: bundleJs.replace(work, '<work>'), primitivesCssChars: primitivesCss.length },
  browser,
}, null, 2))

/* ⚠ 自检结论走 **stderr**（不是 stdout）：stdout 是**一份 JSON**，调用方（smoke-kb-cols /
 * ui-badge-pixels）要 `JSON.parse` 它 —— 往 stdout 后面追加一行"✅…"会把机器可读的产物弄坏
 * （本仓已经因为"人读的尾巴混进机器读的产物"返工过一次）。 */
if (colsSkipReason !== null) {
  console.error(`· #cols 自检：**这一跑不判**（${colsSkipReason}）`)
} else if (colsProblems.length === 0) {
  console.error(`· #cols 自检通过：表头 = 行 = ${JSON.stringify(colsCheck.header)}，`
    + `column-gap = ${JSON.stringify(colsCheck.gapHeader)}（page=${page} width=${width} theme=${themeName}）`)
} else {
  console.error('')
  console.error(`❌ 列对齐自检失败（P2 头条的验收之一；page=${page} width=${width} theme=${themeName}）：`)
  for (const p of colsProblems) console.error(`   - ${p}`)
  console.error('   ⇒ 表头（.ks-lhead）与数据行（.ks-item）必须共用同一条列模板：')
  console.error('      ksGuideStyles.ts 的 `.ks-lhead,.ks-item{grid-template-columns:var(--ks-cols)}`')
  console.error('      与 `.ks-list` 上唯一的 --ks-cols（宽/窄两档也只覆盖这一个属性）。')
  process.exit(1)
}

/* `#kbcards` 的自检结论同样走 **stderr**（理由同上：stdout 必须是完整可 JSON.parse 的一份产物）。 */
if (cardsSkipReason !== null) {
  console.error(`· #kbcards 自检：**这一跑不判**（${cardsSkipReason}）`)
} else if (cardsProblems.length === 0) {
  console.error(`· #kbcards 自检通过：${String(cardsCheck.count)} 张卡宽全等 ${JSON.stringify(cardsCheck.widths)}、`
    + `高全等 ${JSON.stringify(cardsCheck.heights)}（page=${page} width=${width} theme=${themeName}）`)
} else {
  console.error('')
  console.error(`❌ 卡片尺寸统一自检失败（业主点名的形态"知识库卡片尺寸统一"；page=${page} width=${width} theme=${themeName}）：`)
  for (const p of cardsProblems) console.error(`   - ${p}`)
  console.error('   ⇒ 卡宽的唯一声明是 ksGuideStyles.ts 的 `.ks-kbband .ks-kb-card{flex:0 0 var(--ks-band-card-w)}`，')
  console.error('      同排等高靠容器 `.ks-kbband .ks-kb-cards{align-items:stretch}` + `>*{min-height:var(--ks-card-h)}`。')
  console.error('      给**单张卡**另钉宽度/高度（例如 :nth-child(2){flex:0 0 60px}）就是这条断言要抓的回归。')
  process.exit(1)
}

/* `#kspad` 的自检结论同样走 **stderr**（理由同上：stdout 必须是完整可 JSON.parse 的一份产物）。 */
if (ksPadSkipReason !== null) {
  console.error(`· #kspad 自检：**这一跑不判**（${ksPadSkipReason}）`)
} else if (ksPadProblems.length === 0) {
  const detail = (ksPadCheck.items ?? []).map((it) => `${it.sel} ${String(it.d)}/${String(it.dR)}`).join('、')
  console.error(`· #kspad 自检通过：${ksPadCheck.tier === 'wide' ? '宽' : '窄'}档（页面根宽 `
    + `${String(ksPadCheck.pageW)}px）留边 ${String(ksPadCheck.expect)}px；逐项 左/右 = ${detail}`
    + `（page=${page} width=${width} theme=${themeName}）`)
} else {
  console.error('')
  console.error(`❌ 页面留边自检失败（业主：「窗口四周要留点边啊」；page=${page} width=${width} theme=${themeName}）：`)
  for (const p of ksPadProblems) console.error(`   - ${p}`)
  console.error('   ⇒ 页面根 / 卡片带外框 / 表格容器 / 批量条 / 页内按钮行 都不许贴边：')
  console.error('      ksGuideStyles.ts 的 `.ks-kb,.ks-ing,.ks-mat{padding-*:var(--ks-page-pad-x|y)}`，')
  console.error('      值在 :root 的 --ks-page-pad-x-narrow/wide（窄 16 / 宽 24，@container 660 切档）。')
  console.error('      把留边改成 0（或负 margin）、或把 token 改歪，就是这条断言要抓的回归。')
  process.exit(1)
}

