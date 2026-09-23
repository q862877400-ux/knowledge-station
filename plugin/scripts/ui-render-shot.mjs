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
 *   --nav-page manage|channels|capabilities|materials
 *                     **加法式**开关（2026-09-23 接手批）：只对 `--page kb` 有意义 —— 它改的是
 *                     `PROPS.kb` 里 `navigation.params.page` 那个**页面分发值**（KsKnowledgePage
 *                     靠它挑"四个面"）。不给这个开关时 `params.page` **与改前逐字相同**
 *                     （仍是 'manage'）⇒ 原有场景一条都不变。
 *                     为什么需要它：四个面里的**办事台/渠道库**只能从这里进 ——
 *                     `--page capabilities` 挂的是 `KsCapabilityPage` **组件自己**（没有顶部四标签条），
 *                     而业主判"四个面是不是一致"必须看到**标签条 + 面**同屏。
 *                     `channels` 面**没有**独立 `--page`（它只活在 KsKnowledgePage 的分支里）。
 *                     ⚠ 值必须落在下面的 NAV_PAGE_VALUES 里（写错 = exit 2，不静默回落）。
 *   --out  <png 路径>（同目录会写一份同名 .html）
 *   --width <px>     默认按页面给（kb 520 / ingest 520 / capabilities 900 / materials 900）
 *   --height <px>    窗口高**固定**（默认：量内容高，全页截图）
 *   --viewport <px>  同上，语义更直白（"这是视口高，不是全页"）
 *                    ⚠ **它不能用来判 `position:sticky`**：`--screenshot` 在这种无头模式下
 *                      是"整页截图"，滚动位置不进产物（5c 实测：加 scrollTo 后图里只剩空白）。
 *                      批量条位置只能在**真宿主页面**里看，见 docs/UI-BASELINE.md 第五节。
 *   --interact <a,b> 可选：kb-files / kb-level / kb-crumb / kb-back / kb-detail /
 *                    kb-search / kb-search-dirs / kb-search-dirs-empty / kb-empty /
 *                    kb-page / kb-upload / kb-inbox / kb-inbox-picked / kb-dir-manage /
 *                    kb-ask / kb-filemenu / kb-dirmenu / ingest-batch / office-page
 *                    ⚠ `kb-filemenu` / `kb-dirmenu`（2026-09-22）：把**文件行 / 目录行**的 ⋮ 菜单
 *                      打开，逐条判渲染出来的文案（业主定的「移动到 / 复制到 / 在此文件中提问 /
 *                      移出」那一套）+ 「移出」不是删除的 title。取证截图也用这两个场景。
 *                    ⚠⚠ **未知场景名 ⇒ 报错 + exit 2**（列出可用名字）；**每个分支都必须"落地"**：
 *                      做不到就报 note + **exit 1**（`mustLand`），没有"什么都没做还成功"的路径。
 *                    ⚠⚠ **2026-09-21（KB-FOLDER-PLAN 第 3 步）这一组场景**随页面一起重写：
 *                      旧的 `kb-band-start` / `kb-band-end` / `kb-select` / `kb-tags-view` /
 *                      `kb-filter` / `kb-filter-empty` / `kb-enter-law` / `kb-enter-l2` 判的界面
 *                      **整块不存在了**（卡片带、批量条、标签视图、状态筛选胶囊都随本批删除），
 *                      继续留着它们只会变成"分支里找不到东西 ⇒ 报红"的噪声。替代：
 *                        · `kb-band-*` 的"翻页真的换位置" → **`kb-page`**（后端分页：翻页条 + offset）
 *                        · `kb-filter*` 的"筛选真的作用在行数上" → **`kb-search`**（同一件事的搜索版）
 *                        · `kb-enter-law` / `kb-enter-l2` → **`kb-level`**（进某一级看它的下级目录）
 *                        · `kb-empty-files`（下钻 → 全选 → 批量删除） → **`kb-empty`**
 *                          （进一个**真的空目录**看「这一层还没有东西」；批量删除已不在本批）
 *                        · `kb-select` → **`kb-upload`**（打开上传面板：本批新增的入口）
 *                      新增：`kb-crumb`（面包屑逐级可点，判据不变，只是换到真树的那条路径）、
 *                      `kb-back`（返回上一层）。
 *                    ⚠ `kb-files` 是给 `smoke-kb-cols.mjs`（列对齐三档）与 `ui-badge-pixels.mjs`
 *                      （徽章像素）用的**前置步骤**：默认态停在**最外层**（只有目录行）。
 *                    ⚠ `kb-level`（法律法规：**1 行目录 + 1 行文件**）是 `levelCheck` 的取证场景
 *                      —— 那是本版新增的几何断言（左列与右栏并排 + 两类行高逐字相同）。
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
 * ⚠⚠ **2026-09-21（第 3 步）就地改写**：上一版这里的真断言是 `#kbcards`（卡片带里逐张卡
 *   的宽/高必须**全等**），因为"知识库卡片尺寸统一"是业主点名的形态。**卡片带已被业主删掉**
 *   （"原来的大卡片去掉"）⇒ 那条断言**没有主体**了。取代它的是 `levelCheck`（见下面同名一段）：
 *   判**新的真实几何** —— ① 左列目录树与右栏**并排**（不是换行堆叠）；② 同一级里**目录行与
 *   文件行**的行高**逐字相同**（"目录层与文件列表同构"这句承诺的可量形态）。判据强度不减：
 *   量不到就红（不许静默 skip），由 `smoke-kb-cols.mjs` 三档逐档跑。
 *
 * 退出码：0 = 图已生成且（适用时）列对齐/几何自检通过；1 = 缺件/截图失败/自检失败/**--interact
 *   场景没落地**（**不是通过**）；2 = 参数错（含**未知的 --interact 场景名**，5i 起）。
 */
import { existsSync } from 'node:fs'
import { mkdir, mkdtemp, readFile, readdir, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { spawnSync } from 'node:child_process'

import { checkCapCards } from './lib/cap-cards-check.mjs'

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
/**
 * `--nav-page`（**加法式**，2026-09-23 接手批）：KsKnowledgePage 的 `params.page` 分发值。
 *
 * ⚠⚠ **不给这个开关时行为必须与改前逐字相同**：`navPage` 的默认值就是原来写死的那一个字面量
 *    `'manage'`，`PROPS.kb` 里那处引用改成变量之后，**不加开关的那条路走的就是同一个字符串**。
 *   （判据 = 原有场景一条都不许变红，见本轮报告里的实测数字。）
 * ⚠ 只对 `--page kb` 有意义：其余三个 `--page` 挂的是**组件自己**，根本不读 `params.page`。
 *   给了却不生效 = 静默没做成 ⇒ **当场 exit 2**（本脚本对"什么都没做还成功"的一贯口径）。
 */
const NAV_PAGE_VALUES = ['manage', 'channels', 'capabilities', 'materials']
const navPageRaw = arg('nav-page', '')
if (navPageRaw !== '' && !NAV_PAGE_VALUES.includes(navPageRaw)) {
  console.error(`❌ 未知 --nav-page ${navPageRaw}（可选：${NAV_PAGE_VALUES.join(' / ')}）`); process.exit(2)
}
if (navPageRaw !== '' && page !== 'kb') {
  console.error(`❌ --nav-page 只对 --page kb 有意义（这一跑 --page ${page} 挂的是组件自己，`
    + '不读 navigation.params.page）—— 给了它不会有任何效果，故按参数错退出（exit 2）')
  process.exit(2)
}
/** ⚠ 默认值 = 改前那一个字面量，**逐字**。 */
const navPage = navPageRaw === '' ? 'manage' : navPageRaw
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
  'kb-files', 'kb-level', 'kb-crumb', 'kb-back', 'kb-detail', 'kb-search',
  'kb-search-dirs', 'kb-search-dirs-empty', 'kb-empty', 'kb-page', 'kb-upload',
  'kb-inbox', 'kb-inbox-picked', 'kb-dir-manage', 'kb-ask', 'kb-filemenu', 'kb-dirmenu',
  'ingest-batch', 'office-page',
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
 * ⚠⚠ **2026-09-21（第 3 步）：`--band-scroll` 已撤除，并且**显式拒绝**。**
 * 它滚的是卡片带（`.ks-kbband-clip`）—— 那块界面已被业主删掉（"原来的大卡片去掉"）。
 * 一个"还在收参数但什么都不做"的开关正是本仓最恨的静默失败 ⇒ 传了就**exit 2** 并说清原因。
 * 旧口径（留痕，别删）：在**真 Chrome** 里把卡片带滚到该位置；jsdom 预渲染那趟没有布局，
 * `scrollLeft` 只能是 0，所以"滚到中段/末端"那张图需要它（它写的是真元素的 scrollLeft）。
 */
if (process.argv.includes('--band-scroll')) {
  console.error('❌ `--band-scroll` 已撤除：它滚的是**卡片带**（.ks-kbband-clip），')
  console.error('   而卡片带在 2026-09-21（KB-FOLDER-PLAN 第 3 步，业主"原来的大卡片去掉"）已删除。')
  console.error('   现在没有横向滚动容器可滚；这条开关不再有任何作用，故**拒绝**而不是静默忽略。')
  process.exit(2)
}

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
/* ── STUB（2026-09-21 第 3 步扩充）：知识库页**现在真的调引擎** `/api/v1/kb/*`，
      所以这里必须按 `src/core/api/routes_kb_folders.py` 的**真实返回形状**回话，
      否则截图里只会是一块"读不到知识库"的错误条（那就白截了）。
      形状与 `plugin/scripts/smoke-kb-page-render.mjs` 的桩**同源**：同一棵四层小树；
      这里的数据要够拍出"左列目录 + 右栏当前这一级 + 分页 + 上传面板"。 ── */
const KB_API = 'http://127.0.0.1:1234'
const kbFolder = (id, name, parentId, direct, deep, foldersDeep) => ({
  folder_id: id, parent_id: parentId, name, sort: 0, created_at: '2026-09-21 10:00:00',
  file_count_direct: direct, file_count_deep: deep, folder_count_deep: foldersDeep,
})
const KB_F = {
  std: kbFolder('fld_std', '标准', null, 0, 14, 3),
  law: kbFolder('fld_law', '法律法规', null, 1, 3, 1),
  empty: kbFolder('fld_empty', '空目录', null, 0, 0, 0),
  big: kbFolder('fld_big', '大批量', null, 120, 120, 0),
  p16: kbFolder('fld_p16', 'P16 工程防火', 'fld_std', 4, 4, 0),
  cca: kbFolder('fld_cca', '宪法与行政法', 'fld_law', 2, 2, 0),
}
/** ⚠ **`fld_law` 故意同时有 1 个下级目录 + 1 篇文件** —— 那是 `levelCheck` 的取证场景
    （同一级里两类行的行高必须逐字相同；只有两层同时在场才量得动）。 */
const KB_SUBS = {
  root: [KB_F.std, KB_F.law, KB_F.empty, KB_F.big],
  fld_std: [KB_F.p16], fld_law: [KB_F.cca],
  fld_p16: [], fld_cca: [], fld_empty: [], fld_big: [],
}
const KB_CRUMB = {
  root: [], fld_std: [KB_F.std], fld_law: [KB_F.law], fld_empty: [KB_F.empty],
  fld_big: [KB_F.big], fld_p16: [KB_F.std, KB_F.p16], fld_cca: [KB_F.law, KB_F.cca],
}
const kbDoc = (id, no, name, extra = {}) => ({
  doc_id: id, standard_no: no, standard_name: name, legal_status: 'effective',
  legal_hierarchy: 'GB', doc_type: 'standard', ccs_code: 'P16', ccs_name: '工程防火',
  published_at: '2017-05-27', effective_from: '2018-01-01', withdrawn_date: null,
  superseded_by: null, stage: 'filed', confidence: 0.93, failure_kind: null,
  suggested_folder_id: null, ...extra,
})
const KB_DOCS_P16 = [
  kbDoc('doc_fire_50016', 'GB 50016-2014', '建筑设计防火规范'),
  kbDoc('doc_fire_55037', 'GB 55037-2022', '建筑防火通用规范'),
  kbDoc('doc_fire_50084', 'GB 50084-2017', '自动喷水灭火系统设计规范'),
  kbDoc('doc_fire_old', 'GB 50016-2006', '建筑设计防火规范（2006 版）',
    { legal_status: 'withdrawn', withdrawn_date: '2015-05-01', stage: 'failed', failure_kind: '表格' }),
]
const KB_DOCS_CCA = [
  kbDoc('doc_law_safety', '', '中华人民共和国安全生产法', { legal_hierarchy: '法律', stage: 'confirming' }),
  kbDoc('doc_law_fire', '', '中华人民共和国消防法', { legal_hierarchy: '法律', stage: 'queued' }),
]
const KB_DOCS_LAW = [kbDoc('doc_law_reg', '', '危险化学品安全管理条例', { legal_hierarchy: '行政法规' })]
const KB_DOCS_BIG = Array.from({ length: 120 }, (_, i) =>
  kbDoc(`doc_big_${String(i)}`, `GB/T 90${String(i).padStart(2, '0')}-2020`, `批量测试标准 ${String(i)}`))
const KB_ITEMS = {
  root: [], fld_std: [], fld_law: KB_DOCS_LAW, fld_empty: [],
  fld_p16: KB_DOCS_P16, fld_cca: KB_DOCS_CCA, fld_big: KB_DOCS_BIG,
}
/* ── 「待分类」层的桩（第 4 步）：形状逐字照 `routes_kb_folders.py` 的 kb_inbox ──
   四篇覆盖四种档位 + 兜底桶；状态列/建议去向列都要有真东西可量。 ── */
const kbInboxItem = (id, no, name, extra = {}) => ({
  doc_id: id, standard_no: no, standard_name: name, stage: 'queued', stage_label: '排队中',
  confidence: null, failure_kind: null, suggested_folder_id: null, suggested_path: null,
  suggest_new_parent_id: null, suggest_new_name: null, catalog_hidden: 0, ...extra,
})
const KB_INBOX = [
  kbInboxItem('doc_in_q', 'GB/T 90001-2020', '排队中的一篇',
    { suggested_folder_id: KB_F.p16.folder_id,
      suggested_path: '标准 › P 土木、建筑 › P15/19 工程抗震、工程防火、人防工程 › P16 工程防火' }),
  kbInboxItem('doc_in_rec', 'GB/T 90002-2020', '识别中的一篇',
    { stage: 'recognizing', stage_label: '识别中' }),
  kbInboxItem('doc_in_ok', 'GB/T 90003-2020', '待确认的一篇',
    { stage: 'confirming', stage_label: '待确认', confidence: 0.93,
      suggested_folder_id: KB_F.p16.folder_id,
      suggested_path: '标准 › P 土木、建筑 › P15/19 工程抗震、工程防火、人防工程 › P16 工程防火',
      suggest_new_parent_id: KB_F.p16.folder_id, suggest_new_name: 'P16 工程防火（新）' }),
  kbInboxItem('doc_in_bad', 'GB/T 90004-2020', '识别失败的一篇',
    { stage: 'failed', stage_label: '识别失败', confidence: 0.4,
      failure_kind: '解析失败（正文条款为零）', catalog_hidden: 1 }),
]
/** 目录选择器用的扁平清单（整棵小树）。 */
const KB_FLAT = [
  { folder_id: KB_F.std.folder_id, parent_id: null, name: '标准', path: '标准', depth: 1 },
  { folder_id: KB_F.law.folder_id, parent_id: null, name: '法律法规', path: '法律法规', depth: 1 },
  { folder_id: KB_F.p16.folder_id, parent_id: KB_F.std.folder_id, name: 'P16 工程防火',
    path: '标准 › P 土木、建筑 › P15/19 工程抗震、工程防火、人防工程 › P16 工程防火', depth: 4 },
]
const KB_STAGE_LABELS = { queued: '排队中', recognizing: '识别中', confirming: '待确认',
                          filed: '已归位', failed: '识别失败' }
let kbReingestRunning = false
const kbReingestSeen = []
/** 第 6 步：按目录范围提问时，`/kb/scope/resolve` 收到的 `folder_ids`（逐次记，供场景断言）。 */
const kbScopeSeen = []
/** 第 6 步：`/ks/answer` 收到的整个 `params`（判"范围真的随请求发出去了"）。 */
const kbAnswerSeen = []
/** 一个范围的权威规模（目录子树 ∪ 显式文件）—— 与 `/ks/answer` 的桩共用，两处必然一致。 */
const kbScopeOf = (rootIds) => {
  const folderIds = new Set()
  const docIds = new Set()
  const walk = (fid) => {
    if (folderIds.has(fid)) return
    folderIds.add(fid)
    for (const d of (KB_ITEMS[fid] ?? [])) docIds.add(d.doc_id)
    for (const kid of (KB_SUBS[fid] ?? [])) walk(kid.folder_id)
  }
  for (const r of rootIds) walk(r)
  return { folder_ids: [...folderIds].sort(), doc_ids: [...docIds].sort() }
}
let kbDocsInLib = [kbDoc('doc_existing', 'GB 1-2000', '库里原有的一篇')]
let kbBulkSeq = 0
const kbLevel = (rawParent) => {
  const id = rawParent === null || rawParent === '' ? 'root' : rawParent
  return { code: 200, status: 'success', data: {
    folder: id === 'root' ? null : (Object.values(KB_F).find((f) => f.folder_id === id) ?? null),
    breadcrumb: KB_CRUMB[id] ?? [], subfolders: KB_SUBS[id] ?? [],
    total: (KB_SUBS[id] ?? []).length, offset: 0, limit: 200, has_more: false,
  } }
}
const kbItems = (folderId, offset, limit) => {
  const key = folderId === 'root' || folderId === 'null' ? 'root' : folderId
  const all = KB_ITEMS[key] ?? []
  const page = all.slice(offset, offset + limit)
  return { code: 200, status: 'success', data: {
    folder: key === 'root' ? null : (Object.values(KB_F).find((f) => f.folder_id === key) ?? null),
    breadcrumb: KB_CRUMB[key] ?? [], items: page, total: all.length, offset, limit,
    has_more: offset + page.length < all.length,
  } }
}

globalThis.fetch = async (input, init = {}) => {
  const url = typeof input === 'string' ? input : String(input?.url ?? input)
  const method = String(init?.method ?? 'GET').toUpperCase()
  const reply = (payload, status = 200) => ({
    ok: status >= 200 && status < 300, status,
    json: async () => payload, text: async () => JSON.stringify(payload),
  })
  if (url === '/ks/session') {
    return reply({ ok: true, engine: { port: 1234, pid: 42, reused: false }, token: 'stub-token' })
  }
  if (url.includes('/ks/ingest/inbox-default')) return reply({ ok: true, data: { dir: STUB_DIR } })
  if (url.includes('/ks/ingest/inbox')) return reply({ ok: true, data: { dir: STUB_DIR, count: stubFiles.length, files: stubFiles } })
  if (url.includes('/ks/ingest/preview/batch')) return reply({ ok: true, data: stubBatch })
  if (url.includes('/ks/ingest/preview')) return reply({ ok: true, data: null })
  if (url.startsWith(KB_API)) {
    const u = new URL(url)
    const p = u.pathname
    if (p === '/api/v1/kb/folders' && method === 'GET') return reply(kbLevel(u.searchParams.get('parent_id')))
    const mItems = /^\/api\/v1\/kb\/folders\/([^/]+)\/items$/.exec(p)
    if (mItems !== null) {
      return reply(kbItems(decodeURIComponent(mItems[1]),
        Number(u.searchParams.get('offset') ?? '0'), Number(u.searchParams.get('limit') ?? '50')))
    }
    if (p === '/api/v1/kb/inbox/confirm' || p === '/api/v1/kb/members') {
      return reply({ code: 200, status: 'success', data: { confirmed: 0, added: 0, skipped: 0, removed_from_pending: 0 } })
    }
    /* ── 第 5 步：目录/文件 CRUD 的四条（形状照 routes_kb_folders.py；本场景只用到
       `delete-preview` 一条，其余是"点下去别撞 STUB_MISS"的兜底）── */
    const mDelPreview = /^\/api\/v1\/kb\/folders\/([^/]+)\/delete-preview$/.exec(p)
    if (mDelPreview !== null) {
      const fid = decodeURIComponent(mDelPreview[1])
      const row = Object.values(KB_F).find((f) => f.folder_id === fid) ?? null
      /* 「法律法规」在桩里是**一级目录**（没有上一层）⇒ 场景图上「移到上一层」是**禁用**的
         —— 这正是要拍给业主看的两件事之一（另一个是非空目录的两个选择都在）。 */
      const isTop = row === null || row.parent_id === null
      return reply({ code: 200, status: 'success', data: {
        folder: row ?? { folder_id: fid, parent_id: null, name: '标准', sort: 0, created_at: null },
        is_empty: false, direct_subfolder_count: 1, direct_file_count: 2,
        subtree_folder_count: 3, subtree_file_count: 9,
        reparent_available: !isTop, files_kept_elsewhere: 2, files_would_be_deleted: 7 } })
    }
    if (/^\/api\/v1\/kb\/folders\/[^/]+\/(move|copy)$/.test(p)
        || /^\/api\/v1\/kb\/members\/(remove|move|copy)$/.test(p)) {
      return reply({ code: 200, status: 'success', data: {
        folder_id: '', to_folder_id: '', from_folder_id: '',
        added: 0, skipped: 0, removed: 0, moved: 0, total: 0 } })
    }
    if (p === '/api/v1/kb/folders' && method === 'POST') {
      return reply({ code: 200, status: 'success', data: {
        folder_id: 'fld_new', name: '新目录', parent_id: null, sort: 0, created_at: null } })
    }
    if (/^\/api\/v1\/kb\/folders\/[^/]+$/.test(p) && method === 'PUT') {
      return reply({ code: 200, status: 'success', data: {
        folder_id: p.split('/')[4], name: '新名字', parent_id: null } })
    }
    /* ── 第 4 步：「待分类」层的四条（形状逐字照 routes_kb_folders.py / reingest.py）── */
    if (p === '/api/v1/kb/inbox') {
      const offset = Number(u.searchParams.get('offset') ?? '0')
      const limit = Number(u.searchParams.get('limit') ?? '50')
      const page = KB_INBOX.slice(offset, offset + limit)
      return reply({ code: 200, status: 'success', data: {
        items: page, total: KB_INBOX.length, offset, limit,
        has_more: offset + page.length < KB_INBOX.length } })
    }
    if (p === '/api/v1/kb/stage-labels') {
      return reply({ code: 200, status: 'success', data: {
        labels: KB_STAGE_LABELS, stages: ['queued', 'recognizing', 'confirming', 'filed', 'failed'],
        unfiled: ['queued', 'recognizing', 'confirming', 'failed'] } })
    }
    if (p === '/api/v1/kb/folders/flat') {
      const qq = String(u.searchParams.get('q') ?? '').toLowerCase()
      const rows = qq === '' ? KB_FLAT : KB_FLAT.filter((f) => f.path.toLowerCase().includes(qq))
      return reply({ code: 200, status: 'success', data: {
        items: rows, total: rows.length, offset: 0, limit: 0, sep: ' › ' } })
    }
    if (p === '/api/v1/kb/inbox/reingest' && method === 'POST') {
      const ids = JSON.parse(init?.body ?? '{}').doc_ids ?? []
      kbReingestSeen.push(...ids)
      kbReingestRunning = true
      return reply({ code: 200, status: 'success', data: {
        queued: ids.length, started: ids.map((id) => ({ doc_id: id, path: 'D:\\x.pdf', standard_no: 'GB/T 1-2020' })),
        skipped: [] } })
    }
    if (p === '/api/v1/kb/inbox/reingest/status') {
      const was = kbReingestRunning
      kbReingestRunning = false
      return reply({ code: 200, status: 'success', data: {
        running: was, total: kbReingestSeen.length, done: was ? 0 : kbReingestSeen.length,
        results: [], started_at: null, finished_at: null } })
    }
    if (p === '/api/v1/documents/batch-delete' && method === 'POST') {
      return reply({ code: 200, status: 'success', data: { deleted: 0 } })
    }
    if (p === '/api/v1/documents') return reply({ code: 200, status: 'success', data: kbDocsInLib })
    /* ── 第 6 步：范围解析 + 取证答案（形状照 routes_kb_folders.py / server.ks_answer_endpoint）──
       ⚠ 两条路由共用 `kbScopeOf` ⇒ 界面上 chip 的篇数与答案回显的篇数**必然相等**。 */
    if (p === '/api/v1/kb/scope/resolve' && method === 'POST') {
      const roots = JSON.parse(init?.body ?? '{}').folder_ids ?? []
      kbScopeSeen.push(roots)
      const sc = kbScopeOf(roots)
      return reply({ code: 200, status: 'success', data: {
        folder_ids: sc.folder_ids, doc_ids: sc.doc_ids,
        folder_count: sc.folder_ids.length, doc_count: sc.doc_ids.length, roots } })
    }
    if (p === '/api/v1/ks/answer' && method === 'POST') {
      const pr = JSON.parse(init?.body ?? '{}').params ?? {}
      kbAnswerSeen.push(pr)
      const roots = Array.isArray(pr.kb_folder_ids) ? pr.kb_folder_ids : []
      const docs = Array.isArray(pr.kb_doc_ids) ? pr.kb_doc_ids : []
      const sc = kbScopeOf(roots)
      const docCount = new Set([...sc.doc_ids, ...docs]).size
      const echo = { kind: 'kb', folder_ids: roots, folder_count: sc.folder_ids.length,
        doc_count: docCount, empty: docCount === 0 }
      if (docCount === 0) {
        return reply({ code: 200, status: 'success', data: {
          tier: 'reference', evidence: [], derivation: '', conclusion: '',
          notes: ['【知识库目录范围】范围内没有文件，没有做任何检索。'], scope: echo } })
      }
      return reply({ code: 200, status: 'success', data: {
        tier: 'standard',
        evidence: [{ clause_revision_id: `cr_${roots[0] ?? 'x'}`, doc_id: sc.doc_ids[0] ?? docs[0],
          standard_no: 'GB 55037-2022', clause_number: '5.2.3', title: '建筑防火通用规范',
          legal_status: 'effective', legal_hierarchy: 'GB', page_start: 12,
          snippet: '桩：这一条来自范围内那批文档。', effective_from: '2023-06-01' }],
        derivation: '桩推导：范围内的依据支持这个结论。',
        conclusion: '桩结论：范围内答得出。',
        notes: ['【知识库目录范围】检索已在范围内限定。'], scope: echo } })
    }
    if (p === '/api/v1/ingest/bulk' && method === 'POST') {
      kbBulkSeq += 1
      const batchId = `bulk_${String(kbBulkSeq)}`
      kbDocsInLib = [...kbDocsInLib, kbDoc(`${batchId}_a`, 'GB 70000-2026', `新导入的一篇 A（${batchId}）`)]
      return reply({ code: 200, status: 'success', data: { batch_id: batchId, total: 1 } })
    }
    if (/^\/api\/v1\/ingest\/bulk\/[^/]+\/resume$/.test(p)) {
      return reply({ code: 200, status: 'success', data: { batch_id: p.split('/')[5] } })
    }
    if (/^\/api\/v1\/ingest\/bulk\/[^/]+$/.test(p)) {
      return reply({ code: 200, status: 'success', data: {
        batch_id: p.split('/')[5], status: 'done', total: 1, scanned: 1, parsed: 1,
        pending: 0, errors: 0, pause_reason: null,
      } })
    }
  }
  return reply({ ok: false, error: { code: 'STUB_MISS', message: `未预料的请求：${url}` } }, 404)
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
    /* ⚠ `navPage` 的默认值就是改前那个字面量 'manage'（见上面 --nav-page 那段）：
       不加开关 = 与改前逐字相同。 */
    useTabInfo: () => ({ tab: { id: 'ks-kb-tab', visible: true, navigation: { address: 'ks:kb', revision: 1, params: { page: navPage } } } }),
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
 * **截图取证专用**：把宿主 `Menu` 那份 `portal` 出去的菜单**搬进容器**。
 *
 * 为什么需要它：`Menu` 是 `createPortal(list, document.body)`（`ui-primitives/src/Menu.tsx`：
 * "portal - render the list into document.body, fixed-positioned"）⇒ 它在 `#root` **外面**，
 * 而本脚本截图只序列化 `container.innerHTML` ⇒ 不搬的话**图里永远看不到菜单**
 * （2026-09-22 实测：`kb-filemenu` 的断言全过、截图却是一张没有菜单的页面）。
 * ⚠ 断言**已经跑在真 DOM**（document 作用域）上了，这一步只影响截图；也**只**给
 *   `--interact kb-filemenu` / `kb-dirmenu` 用。
 * ⚠ jsdom 没有布局引擎 ⇒ 菜单在图里的**位置**不可信（大致落在页面左上/末尾），
 *   这张图的证据是**菜单文字**，不是它挂在哪儿（位置由 jsdom 冒烟 + 真机使用判）。
 */
const moveMenusIntoShot = () => {
  for (const el of [...dom.window.document.querySelectorAll('[role="menu"]')]) {
    container.appendChild(el)
  }
}
/**
 * **场景"落地"的判定**（5i 2026-09-20 收尾批；与上面的 `SCENARIOS` 表配套）。
 *
 * 为什么要有它：`--interact` 的每个分支都必须**真的做到那一件事**，做不到就得**报红**，
 * 不能只在 note 里写一句"没找到卡"然后 exit 0 —— 那就是"什么都没做还成功"。
 *   ⚠ 边界（诚实）：**旧版那两个卡片带场景**在 jsdom 里"滚动"本来就动不了（没有布局引擎，
 *   `scrollWidth` 恒 0）⇒ 它们的落地判据只能钉到"这条带 + 5 张卡真的在 DOM 里、箭头真的被点到"。
 *   **2026-09-21（第 3 步）起那条带整个删除了**，`kb-page` 取代了"翻页"这件事，而它判的是
 *   **后端分页**（点「下一页」⇒ 行数/页码真的变）—— 不再是"滚不滚得动"。
 */
const landing = []
const mustLand = (ok, msg) => { if (!ok) landing.push(msg) }
/* ⚠ **更正（5i-补 2026-09-20）**：这里原来还有一个 `const handled = new Set()`，配合循环首的
 * `handled.add(how)` 与循环尾的 `!handled.has(how)` 想表达"表里有、链里没有 ⇒ 红"。
 * 那**从来没生效过**：`add` 在循环首**无条件**执行 ⇒ 循环尾那条检查恒假 = **死代码**
 * （复核 verify-freeze-5i / `581d20d` 用 `'kb-fake-probe'` 探针实测：`interact: []`、exit 0）。
 * 现在改由 if/else 链的 **`else` 兜底分支**接手（见循环内那条注释），概念只有一个所有者。 */
/* ── 2026-09-21（第 3 步）导航小工具：新形态下**默认态 = 最外层**（只有目录行，
 *  文件在更深的层里）⇒ 凡是要"文件表格 / 状态徽章 / 搜索框"的场景都必须**先走进去**。
 *  这几个 helper 就是那几步，共用一份（旧版的 gotoCard/gotoFilesView/gotoBandEnd 随卡片带删除）。 ── */
const dirRows = () => q('.ks-dir-row')
const dirNameOf = (el) => (el?.querySelector('.ks-col-dname .ks-dir-name')?.textContent ?? '').trim()
const dirNamed = (text) => dirRows().find((el) => dirNameOf(el).includes(text))
const fileRows = () => q('.ks-item.ks-file-row')
const crumbText = () => q('.ks-crumb-item').map((el) => (el.textContent ?? '').trim()).join('/')
const treeLabels = () => q('.ks-tree-label').map((el) => (el.textContent ?? '').trim())
const backBtn = () => q('.ks-back')[0]
/** **回最外层**：点面包屑第 0 段（「知识库」）；已经在最外层时它是不可点的 `.ks-crumb-here` ⇒ 空操作。
 * ⚠ 每个场景都**自成一体**（`--interact` 允许一次给多个场景，前一个可能把页带到很深的层）。 */
const gotoRoot = async () => {
  const go = q('.ks-crumb-go')[0]
  if (go !== undefined) await click(go)
  return { crumb: crumbText(), dirs: dirRows().length, atRoot: q('.ks-crumb-here')[0]?.textContent?.trim() === '知识库' }
}
/** 从**最外层**往下走一串目录名（每一步都真的点右侧那一行；走不通就停）。 */
const gotoPath = async (names) => {
  await gotoRoot()
  const trail = []
  for (const n of names) {
    const row = dirNamed(n)
    if (row === undefined) break
    await click(row)
    trail.push(n)
  }
  return trail
}
/**
 * **标准 → P16 工程防火**：4 篇文件的那一层（`smoke-kb-cols.mjs` 的列对齐三档与
 * `ui-badge-pixels.mjs` 的徽章像素**必须**先走到这里 —— 它们验的是表格/徽章）。
 */
const gotoStdLeaf = async () => {
  const trail = await gotoPath(['标准', 'P16 工程防火'])
  notes.push(`gotoStdLeaf 逐步：走了 ${trail.join(' / ')}`
    + `（文件行 ${fileRows().length}、目录行 ${dirRows().length}、面包屑「${crumbText()}」）`)
  return fileRows().length
}
for (const how of interacts) {
  if (how === 'kb-files') {
    /* 把页面开到「标准 / P16 工程防火」（4 行文件 + 1 个文件表头）。
       这是 `smoke-kb-cols.mjs`（列对齐三档）与 `ui-badge-pixels.mjs`（徽章像素）**必须**先走的一步
       —— 它们验的是表格/徽章，而默认态停在**最外层**（只有目录行）。 */
    const rows = await gotoStdLeaf()
    mustLand(rows === 4 && q('.ks-list .ks-lhead').length === 1 && q('.ks-list-dirs').length === 0,
      `kb-files 只下钻到 ${String(rows)} 行（期望 4 行 + 1 个文件表头 + 0 个目录层）`)
    notes.push(`kb-files: 走到「标准 / P16 工程防火」 → 文件行 ${String(rows)}、`
      + `文件表头 ${String(q('.ks-list .ks-lhead').length)}、目录层 ${String(q('.ks-list-dirs').length)}`
      + `，面包屑「${crumbText()}」`)
  } else if (how === 'kb-ask') {
    /* 第 6 步：**按目录范围提问**（业主：每一级都能"在此范围内提问"）。
       走「标准 / P16 工程防火」（4 篇文件）⇒ 点「在此范围内提问」⇒ 范围 chip 与提问面板
       必须真的挂出来。这一跑是 `askCheck`（真 Chrome 里量 chip/按钮/面板的**高度与右缘**）
       的取证场景 —— "存在不等于看得见"那条纪律同样适用于本批的新界面。 */
    const rows = await gotoStdLeaf()
    const askBtn = byText('.ks-ask-open', '在此范围内提问')
    const clicked = await click(askBtn)
    /* ⚠ 范围规模是**异步**取回来的（`/kb/scope/resolve` → state → 渲染）⇒ 多等几拍再断言。 */
    for (let i = 0; i < 4; i += 1) await flush()
    const chipText = (q('.ks-ask-chip')[0]?.textContent ?? '').trim()
    const whereText = (q('.ks-ask-where')[0]?.textContent ?? '').trim()
    const seen = kbScopeSeen[kbScopeSeen.length - 1] ?? null
    mustLand(rows === 4, `kb-ask 没走到 4 篇文件那一级（文件行 ${String(rows)}）`)
    mustLand(clicked, 'kb-ask 没找到「在此范围内提问」按钮（入口不存在 = 这一批的核心能力没了）')
    mustLand(q('.ks-ask-chip').length === 1 && chipText.includes('4 篇'),
      `kb-ask 的范围 chip 没写出引擎给的篇数（chip=「${chipText}」）—— 篇数必须来自 /kb/scope/resolve`)
    mustLand(q('.ks-ask').length === 1 && whereText.includes('及其全部下级里提问'),
      `kb-ask 的提问面板/抬头不对：面板 ${String(q('.ks-ask').length)} 个、抬头「${whereText}」`)
    mustLand(Array.isArray(seen) && seen.includes('fld_p16'),
      `kb-ask 没按当前这一级去解析范围（最后一条 folder_ids=${JSON.stringify(seen)}）`)
    /* ⚠ **2026-09-22（业主界面要求）**：入口必须在**当前文件夹名那一行**（jsdom 侧这一半；
       真浏览器侧由 `#ask` 的 `where` 字段与 askCheck 判）。 */
    mustLand(askBtn !== undefined && askBtn.closest('.ks-list-cap') !== null
      && askBtn.closest('.ks-kb-row') === null,
      'kb-ask 的「在此范围内提问」不在 .ks-list-cap 那一行（或还留在工具栏里）—— '
      + '业主 2026-09-22 亲定它要跟着"当前文件夹名"那一行走')
    notes.push(`kb-ask: 走到「标准 / P16 工程防火」 → 文件行 ${String(rows)}、`
      + `chip=「${chipText}」、抬头「${whereText}」、解析范围=${JSON.stringify(seen)}；`
      + '真 Chrome 侧由 #ask 量 chip / 按钮 / 面板的**高度与右缘溢出**')
    /* 再**真问一次**（把答案区也带进这一跑）：① 范围必须随请求发出去（`params.kb_folder_ids`）；
       ② 答案区必须回显**引擎给的**实际范围、并列出范围内的依据 —— 业主口径第 4 条
       （"答案里如实体现范围"）要有真浏览器里看得见的形态，不能只有 jsdom 的 textContent。 */
    const qInput = q('.ks-ask-q input')[0]
    const goBtn = byText('.ks-ask-go', '问一问')
    if (qInput !== undefined) await setSearchInput(qInput, '动火作业怎么分级')
    const asked = await click(goBtn)
    for (let i = 0; i < 3; i += 1) await flush()
    const echoText = (q('.ks-ask-echo')[0]?.textContent ?? '').replace(/\s+/g, ' ').trim()
    const evRows = q('.ks-ask-evrow').length
    const sentParams = kbAnswerSeen[kbAnswerSeen.length - 1] ?? null
    mustLand(asked && Array.isArray(sentParams?.kb_folder_ids)
      && sentParams.kb_folder_ids.includes('fld_p16'),
      `kb-ask 没把范围随请求发出去（最后一条 params=${JSON.stringify(sentParams)}）`)
    mustLand(echoText.includes('这次实际范围') && echoText.includes('4 篇') && evRows >= 1,
      `kb-ask 的答案区没回显实际范围 / 没有依据：echo=「${echoText}」、依据 ${String(evRows)} 条`)
    notes.push(`kb-ask: 又真问了一次 ⇒ 请求 params=${JSON.stringify(sentParams)}、`
      + `答案区回显「${echoText}」、依据 ${String(evRows)} 条（这张截图里能看到整条答案）`)
  } else if (how === 'kb-filemenu') {
    /* ⚠ **2026-09-22（业主点菜单文案那一轮）**：**文件行**的 ⋮ 菜单 —— 文案是业主亲口定的：
       「在此文件中提问」（单篇文件）/「移动到」/「复制到」/「移出」。这一跑在**真浏览器**里把菜单
       打开、**逐条抄下渲染出来的文字**（jsdom 侧另有 `smoke-kb-page-render` 的 I5 整串相等判据），
       并判"「移出」不是删除"那句真相挂在这一行的 **⋮ 按钮 title** 上（DSH 的 `MenuItem` 没有
       `title` 字段 ⇒ 菜单项上挂不了提示，`menu-fix` 那次已核）。
       ⚠ 为什么值得在真浏览器里再判一次：菜单项是**用户直接看的东西**，
          jsdom 的 textContent 判据挡不住"某一项被 CSS 藏了 / 两个菜单叠在一起"。 */
    const rows = await gotoStdLeaf()
    mustLand(rows === 4, `kb-filemenu 没走到 4 篇文件那一级（文件行 ${String(rows)}）`)
    const moreBtn = q('.ks-item.ks-file-row .ks-item-more button')[0]
    const opened = await click(moreBtn)
    for (let i = 0; i < 3; i += 1) await flush()
    /* ⚠ 菜单项要**按 document 查**：宿主的 `Menu` 带 `portal` ⇒
       `createPortal(list, document.body)`（`ui-primitives/src/Menu.tsx`：
       "portal - render the list into document.body, fixed-positioned"）
       ⇒ 它在 `#root` **外面**，容器作用域的 `q()` 查不到（本场景第一次跑就是这么红的：
       inContainer=0 / inDocument=5）。 */
    const menuItemsNow = () => [...dom.window.document.querySelectorAll('[role=menuitem]')]
      .map((el) => (el.textContent ?? '').trim())
    const items = menuItemsNow()
    const want = ['详情', '在此文件中提问', '移动到', '复制到', '移出']
    mustLand(opened && items.join('|') === want.join('|'),
      `kb-filemenu 文件行 ⋮ 菜单不是 ${JSON.stringify(want)}，实测 ${JSON.stringify(items)} —— `
      + '业主 2026-09-22：「在**单个文件**上点开三个点，那就应该展示**在此文件中提问**」；'
      + '「复制到某个目录，直接就写复制到；挪到某个目录直接写移动到」')
    const tip = moreBtn?.getAttribute('title') ?? ''
    mustLand(tip.includes('移出') && tip.includes('文件不会删除'),
      `kb-filemenu 「⋮」按钮的 title 没写清「移出」只移出、文件不删：${tip}`)
    notes.push(`kb-filemenu: 文件行 ⋮ 菜单 = ${JSON.stringify(items)}；`
      + `⋮ 按钮 title =「${tip}」`)
    moveMenusIntoShot()
  } else if (how === 'kb-dirmenu') {
    /* ⚠ **2026-09-22**：**目录行**的 ⋮ 菜单 —— 业主定的是「移动到」「复制到」，
       而「在此范围内提问」在**目录**上保持原样（问的是那一棵目录）；
       `删掉这个目录…` 是**真删目录**（先读影响再二选一）⇒ 文案保持。 */
    await gotoRoot()
    for (let i = 0; i < 2; i += 1) await flush()
    const dirMoreBtn = q('.ks-item.ks-dir-row .ks-item-more button')[0]
    const openedDir = await click(dirMoreBtn)
    for (let i = 0; i < 3; i += 1) await flush()
    const dirItems = [...dom.window.document.querySelectorAll('[role=menuitem]')]
      .map((el) => (el.textContent ?? '').trim())
    const wantDir = ['改名…', '在这个目录下新建…', '移动到', '复制到', '在此范围内提问', '删掉这个目录…']
    mustLand(openedDir && dirItems.join('|') === wantDir.join('|'),
      `kb-dirmenu 目录行 ⋮ 菜单不是 ${JSON.stringify(wantDir)}，实测 ${JSON.stringify(dirItems)}`)
    notes.push(`kb-dirmenu: 目录行 ⋮ 菜单 = ${JSON.stringify(dirItems)}`)
    moveMenusIntoShot()
  } else if (how === 'kb-level') {
    /* 进**法律法规**那一级：它有 **1 个下级目录 + 1 篇文件**（两种行同时在 DOM 里）。
       这一跑同时是 `levelCheck`（左列与右栏并排 + 两类行高逐字相同）的取证场景。 */
    const trail = await gotoPath(['法律法规'])
    mustLand(trail.length === 1 && dirRows().length === 1 && fileRows().length === 1
      && q('.ks-list-dirs').length === 1 && q('.ks-list:not(.ks-list-dirs)').length === 1,
      `kb-level 没走到"两种行同时在"的那一级：走过 ${trail.join('/')}、目录行 ${String(dirRows().length)}、`
      + `文件行 ${String(fileRows().length)}`)
    notes.push(`kb-level: 走到「法律法规」 → 目录行 ${String(dirRows().length)}（${dirRows().map(dirNameOf).join(',')}）`
      + ` + 文件行 ${String(fileRows().length)}、面包屑「${crumbText()}」、`
      + `左列当前级「${q('.ks-tree-row[data-on="true"] .ks-tree-label').map((el) => el.textContent).join(',')}」`)
  } else if (how === 'kb-crumb') {
    /* 面包屑**逐级可点**（业主：「这种路径要每一级都能点击跳转」）。
       本批改成真树之后走的是「法律法规 → 宪法与行政法」（2 级）⇒ 面包屑 3 段：
       「知识库 / 法律法规 / 宪法与行政法」，前两段是可点的 `<button>`，末段是**不可点**的当前级。
       判据与旧版**逐字一致**（可点级别必须是 button、当前级必须不是、点第 i 级真的回到第 i 层），
       只是路径换成真树的那一条。 */
    await gotoPath(['法律法规', '宪法与行政法'])
    const btns = q('.ks-crumb-go')
    const here = q('.ks-crumb-here')
    const btnsText = btns.map((el) => (el.textContent ?? '').trim()).join('/')
    const hereText = here.map((el) => (el.textContent ?? '').trim()).join('/')
    const dirsBefore = dirRows().length
    const filesBefore = fileRows().length
    const clicked = btns.length > 1 ? await click(btns[1]) : false   // 第 1 段 = 「法律法规」
    /* ⚠⚠ **必须重新查一次 DOM**（本批实测踩到）：`here` 是**点击前**的 NodeList —— React 重渲染后
       读它的 `textContent` 可能还是旧文本（快照）⇒ 拿它判"当前级变没变"会**假红**
       （实测报「点第 1 段 true 后：当前级仍是宪法与行政法」，而同一跳的 `dirsAfter` 已经
       是「法律法规」的下级目录了 —— 页面其实已经切过去了）。 */
    const hereNow = q('.ks-crumb-here')
    const hereAfter = hereNow.map((el) => (el.textContent ?? '').trim()).join('/')
    const dirsAfter = dirRows().map(dirNameOf).join(',')
    mustLand(btns.every((el) => el.tagName === 'BUTTON')
      && here.length === 1 && here[0].tagName !== 'BUTTON'
      && btnsText === '知识库/法律法规' && hereText === '宪法与行政法'
      && clicked === true && dirsBefore === 0 && filesBefore === 2
      && dirsAfter.includes('宪法与行政法') && hereAfter === '法律法规',
      `kb-crumb 面包屑跳转不成立：可点条目 [${btnsText}]（都是 button=${String(btns.every((el) => el.tagName === 'BUTTON'))}）`
      + `、当前级「${hereText}」（不是 button=${String(here[0]?.tagName !== 'BUTTON')}）`
      + `；点第 1 段 ${String(clicked)} 后：当前级「${hereAfter}」（期望「法律法规」）、`
      + `这一级目录 ${dirsAfter}（期望含「宪法与行政法」）`)
    notes.push(`kb-crumb: 下钻到「法律法规 / 宪法与行政法」（文件行 ${String(filesBefore)} 行）`
      + `，面包屑可点 [${btnsText}] + 当前级「${hereText}」`
      + ` → 点第 1 段「法律法规」：当前级「${hereAfter}」、这一级目录 ${dirsAfter}`)
  } else if (how === 'kb-back') {
    /* 「← 返回上一层」：从二级目录点一下 ⇒ 回到上一级；且**最外层时按钮 disabled**
       （旧版是"按钮消失"，新形态是"按钮在但置灰 + 明确说你在最外层" —— 判据跟着改成新行为）。 */
    await gotoPath(['法律法规', '宪法与行政法'])
    const before = backBtn()?.disabled
    await click(backBtn())
    const midCrumb = crumbText()
    const midDirs = dirRows().length
    await click(backBtn())
    const rootCrumb = crumbText()
    const rootDirs = dirRows().length
    const rootDisabled = backBtn()?.disabled
    mustLand(before === false && midCrumb === '知识库/法律法规' && midDirs === 1
      && rootCrumb === '知识库' && rootDirs === 4 && rootDisabled === true,
      `kb-back 没逐级退回：起手 disabled=${String(before)}（期望 false）；`
      + `退一级后 面包屑「${midCrumb}」（期望「知识库/法律法规」）目录 ${String(midDirs)}（期望 1）；`
      + `再退一级后 面包屑「${rootCrumb}」（期望「知识库」）目录 ${String(rootDirs)}（期望 4）`
      + ` 返回 disabled=${String(rootDisabled)}（期望 true）`)
    notes.push(`kb-back: 二级目录（返回 disabled=${String(before)}）→ 点「返回上一层」→ 面包屑「${midCrumb}」`
      + `、目录 ${String(midDirs)} 行 → 再点一次 → 面包屑「${rootCrumb}」、目录 ${String(rootDirs)} 行、`
      + `返回 disabled=${String(rootDisabled)}（最外层）`)
  } else if (how === 'kb-detail') {
    /* 整行可点 → 详情（业主 2026-09-21 定）。
       ⚠ 本批**勾选框已撤**：分流规则只剩"按钮/菜单不处理，其余任意处打开详情"。
       这里点的是**生效日期那一格**（非交互处）——正是"整行可点"的取证点。 */
    const rows = await gotoStdLeaf()
    const row = fileRows()[2]
    await click(row?.querySelector('.ks-col-date'))
    const card = q('.ks-detail .ks-kb-card').length
    const text = q('.ks-detail')[0]?.textContent ?? ''
    mustLand(card === 1 && text.includes('自动喷水灭火系统设计规范') && text.includes('GB 50084-2017'),
      `kb-detail 没打开**那一篇**的详情（下钻 ${String(rows)} 行／详情卡 ${String(card)} 张／`
      + `内容「${text.slice(0, 50)}」）`)
    notes.push(`kb-detail: 走到文件层（${String(rows)} 行）→ 点第 3 行的**生效日期格**`
      + ` → 详情卡 ${String(card)} 张，「${text.slice(0, 40)}…」`)
  } else if (how === 'kb-search') {
    /* 搜索框**真的过滤**（不是画个壳）：五步取证 —— 初始 → 按标准号 → 按名称 → 不存在的串（空态）
       → 清空恢复。受控 input 必须走**原生 setter**（直接 el.value = x 会被 React 的 value tracker
       判成"没变化"而不触发 onChange —— 渲染冒烟第一版就是这么失败的）。 */
    await gotoStdLeaf()
    const box = q('.ks-search input')[0]
    if (!box) {
      mustLand(false, 'kb-search 没找到 .ks-search 里的输入框（这一条不判 = 失败，不是通过）')
      notes.push('kb-search: 没找到 .ks-search 里的输入框')
    } else {
      const before = fileRows().length
      await setSearchInput(box, 'GB 50016-2014')
      const byNo = fileRows().length
      await setSearchInput(box, '喷水')
      const byName = fileRows().length
      await setSearchInput(box, '搜索一个不存在的串')
      const none = fileRows().length
      const emptyTitle = q('.ks-empty-t').map((el) => el.textContent).join('|')
      await setSearchInput(box, '')
      const after = fileRows().length
      mustLand(before === 4 && byNo === 1 && byName === 1 && none === 0 && after === 4,
        `kb-search 过滤不成立：行数 初始 ${String(before)}（期望 4）→ 标准号 ${String(byNo)}（1）`
        + ` → 名称 ${String(byName)}（1）→ 不存在 ${String(none)}（0）→ 清空 ${String(after)}（4）`)
      notes.push(`kb-search: 行数 初始 ${String(before)} → 标准号「GB 50016-2014」${String(byNo)}`
        + ` → 名称「喷水」${String(byName)} → 不存在「搜索一个不存在的串」${String(none)}（空态「${emptyTitle}」）`
        + ` → 清空 ${String(after)}`)
      // 收尾**停在"筛出 1 行"的状态**：这张图本身就是"搜索真的生效"的像素证据。
      await setSearchInput(box, '喷水')
      notes.push(`kb-search（收尾）: 搜索框留在「喷水」⇒ 图上是 1 行`
        + `（文件行 ${String(fileRows().length)} / 表头 ${String(q('.ks-lhead').length)}）`)
    }
  } else if (how === 'kb-search-dirs') {
    /* **目录层**的搜索：过滤对象是**目录名**（同一个框，每层常驻）。
       这一跑停在"框里有词 + 目录被筛到 1 行"的状态 ⇒ 这张图就是"目录层有搜索框且真的过滤"的证据。 */
    await gotoPath(['标准'])
    const box = q('.ks-search input')[0]
    const all = dirRows().length
    if (!box) {
      mustLand(false, 'kb-search-dirs 目录层没有 .ks-search 输入框（每一层常驻是验收）')
      notes.push('kb-search-dirs: 目录层没找到 .ks-search 里的输入框')
    } else {
      await setSearchInput(box, 'P16')
      const hit = dirRows().length
      const hitName = dirRows().map(dirNameOf).join('/')
      await setSearchInput(box, '')
      const restored = dirRows().length
      mustLand(all === 1 && hit === 1 && hitName.includes('P16 工程防火') && restored === 1,
        `kb-search-dirs 目录名过滤不成立：目录 ${String(all)}（期望 1）→「P16」${String(hit)}（1）→ 清空 ${String(restored)}（1）`)
      notes.push(`kb-search-dirs: 「标准」这一级目录 ${String(all)} 行 →「P16」${String(hit)} 行（${hitName}）→ 清空 ${String(restored)} 行；`
        + `面包屑「${crumbText()}」、右侧计数「${q('.ks-crumb-n').map((el) => el.textContent).join('')}」`)
      await setSearchInput(box, 'P16')
      notes.push(`kb-search-dirs（收尾）: 框里留在「P16」⇒ 图上是 1 行目录`
        + `（目录 ${String(dirRows().length)} 行 / 文件行 ${String(fileRows().length)}）`)
    }
  } else if (how === 'kb-search-dirs-empty') {
    /* 目录层搜索**没命中** ⇒ 专门的空态「这一层没有符合搜索的条目」+「清除搜索」
       ⚠ 本批把两种空**分开**：这一条判的是"被搜索筛没了"，不是"这一层本来就没东西"（下面 kb-empty）。 */
    await gotoPath(['标准'])
    const box = q('.ks-search input')[0]
    if (!box) {
      mustLand(false, 'kb-search-dirs-empty 目录层没有 .ks-search 输入框')
      notes.push('kb-search-dirs-empty: 目录层没找到 .ks-search 里的输入框')
    } else {
      await setSearchInput(box, '不存在的目录')
      const dirs = dirRows().length
      const title = q('.ks-empty-t').map((el) => el.textContent).join('|')
      mustLand(dirs === 0 && title === '这一层没有符合搜索的条目',
        `kb-search-dirs-empty 空态不对：目录 ${String(dirs)} 行（期望 0）、空态标题「${title}」（期望「这一层没有符合搜索的条目」）`)
      notes.push(`kb-search-dirs-empty: 框里「不存在的目录」⇒ 目录 ${String(dirs)} 行、空态标题「${title}」、`
        + `清除按钮 ${byText('.ks-empty-card button', '清除搜索') !== undefined ? '在' : '不在'}`)
    }
  } else if (how === 'kb-empty') {
    /* **真的空目录**（stub 里「空目录」那一支：既没有下级目录也没有文件）⇒ 如实说"这一层还没有东西"。
       ⚠ 与 `kb-search-dirs-empty` 判的是**两种不同的空**，两条都要有（旧版那条"下钻 → 全选 → 批量删除"
       已随批量动作撤除，替代品比它更直接：库里的空目录本来就存在）。 */
    await gotoPath(['空目录'])
    const title = q('.ks-empty-t').map((el) => el.textContent).join('|')
    mustLand(dirRows().length === 0 && fileRows().length === 0 && q('.ks-empty-card').length === 1
      && title === '这一层还没有东西',
      `kb-empty 没拿到"本来就没东西"那一支空态：目录 ${String(dirRows().length)} 行／文件 ${String(fileRows().length)} 行／`
      + `空态卡 ${String(q('.ks-empty-card').length)} 张／标题「${title}」`)
    notes.push(`kb-empty: 进「空目录」 → 目录 ${String(dirRows().length)} 行、文件 ${String(fileRows().length)} 行、`
      + `空态卡 ${String(q('.ks-empty-card').length)} 张、标题「${title}」`)
  } else if (how === 'kb-page') {
    /* **后端分页**（本批新增的界面口）：120 篇那一级 ⇒ 第一页 50 行 + 分页条；
       点「下一页」⇒ 还是 50 行、页码文字变成第 2 页（真 Chrome 里量**布局后**的行数）。 */
    await gotoPath(['大批量'])
    const first = fileRows().length
    const pager = q('.ks-pager-n')[0]?.textContent ?? ''
    const next = q('.ks-pager-btn')[1]
    const clicked = await click(next)
    const second = fileRows().length
    const pager2 = q('.ks-pager-n')[0]?.textContent ?? ''
    mustLand(first === 50 && pager.includes('第 1 / 3 页') && clicked === true
      && second === 50 && pager2.includes('第 2 / 3 页'),
      `kb-page 分页不成立：第一页 ${String(first)} 行（期望 50）、分页条「${pager}」（期望含「第 1 / 3 页」）；`
      + `点下一页 ${String(clicked)} 后 ${String(second)} 行（期望 50）、分页条「${pager2}」（期望含「第 2 / 3 页」）`)
    notes.push(`kb-page: 「大批量」第一页 ${String(first)} 行、分页条「${pager.trim()}」`
      + ` → 点「下一页」 → ${String(second)} 行、分页条「${pager2.trim()}」`)
  } else if (how === 'kb-dir-manage') {
    /* **第 5 步的目录管理**（2026-09-21）：停在"勾了两个目录 + 删目录确认面板已打开"的样子。
       这一跑同时是两件事在**真 Chrome** 里看得见的证据：
         ① 目录层与文件层的勾选列 + 一套批量条（`.ks-batch`）；
         ② 删目录的**「先问一句」面板**（`.ks-act-del`）：几个下级目录 / 几篇文件 /
            几篇在别处也有（只丢归属）/ 几篇会真删 —— 数字全部来自 `delete-preview`（桩给的是
            真接口的形状）；勾中的两个目录里「法律法规」是一级目录 ⇒ 「移到上一层」必须**禁用**。
       ⚠ 判据用 `mustLand`（没落地就 exit 1）—— 这是"真浏览器里量得到"的那一半；
         请求体逐个核实在 jsdom 冒烟（`smoke-kb-page-render` 的 P1–P30）。 */
    await gotoRoot()
    const boxes = q('.ks-list-dirs .ks-col-dpick input[type=checkbox]')
    if (boxes.length < 2) {
      mustLand(false, `kb-dir-manage 目录层勾选框只有 ${String(boxes.length)} 个（期望 ≥ 2）`)
      notes.push(`kb-dir-manage: 目录层勾选框 ${String(boxes.length)} 个`)
    } else {
      await click(boxes[0])
      await click(boxes[1])
      const batchTexts = q('.ks-batch button').map((el) => (el.textContent ?? '').trim())
      const label = q('.ks-batch-n')[0]?.textContent ?? ''
      const delBtn = q('.ks-batch button').find((el) => (el.textContent ?? '').includes('删掉目录'))
      if (delBtn === undefined) {
        mustLand(false, `kb-dir-manage 批量条里没有「删掉目录…」（拿到 ${JSON.stringify(batchTexts)}）`)
        notes.push(`kb-dir-manage: 批量条 ${JSON.stringify(batchTexts)}`)
      } else {
        await click(delBtn)
        const panel = q('.ks-act-del')[0]
        const text = (panel?.textContent ?? '').replace(/\s+/g, ' ')
        const reparent = q('.ks-act-del button').find((el) => (el.textContent ?? '').includes('移到上一层'))
        const purge = q('.ks-act-del button').find((el) => (el.textContent ?? '').includes('连里面的文件一起删'))
        mustLand(panel !== undefined && text.includes('整棵子树') && text.includes('只丢这里的归属')
          && reparent !== undefined && reparent.disabled === true
          && purge !== undefined && purge.disabled === false,
          `kb-dir-manage 删目录面板不成立：面板 ${String(q('.ks-act-del').length)} 个、`
          + `含「整棵子树」=${String(text.includes('整棵子树'))}、含「只丢这里的归属」=${String(text.includes('只丢这里的归属'))}、`
          + `「移到上一层」disabled=${String(reparent?.disabled)}（期望 true，一级目录）、`
          + `「连里面的文件一起删」disabled=${String(purge?.disabled)}（期望 false）`)
        notes.push(`kb-dir-manage: 勾 2 个目录 ⇒ 批量条「${label}」+ ${JSON.stringify(batchTexts)}`
          + ` → 点「删掉目录…」→ 确认面板 ${String(q('.ks-act-del').length)} 个；`
          + `面板原话「${text.slice(0, 80)}…」；「移到上一层」disabled=${String(reparent?.disabled)}`
          + `、「连里面的文件一起删」disabled=${String(purge?.disabled)}`)
      }
    }
  } else if (how === 'kb-upload') {
    /* **每级上传**的入口（本批新增）：点开面板 ⇒ 来源目录默认填 host 的「待入库」目录，
       并且**如实写着这一层导入会落在哪儿**（最外层 = 留在最外层 / 目录里 = 直接放进这一级）。
       ⚠ 这里**不点「导入到这一层」**：那会真的走引擎的真导入（`/api/v1/ingest/bulk`），
         而本脚本要的是一张**面板的图**；导入链路的断言在渲染冒烟（带 fetch 桩）里逐条钉着。 */
    await gotoPath(['标准'])
    await click(q('.ks-upload-open')[0])
    const dir = q('.ks-upload-dir input')[0]?.value ?? ''
    const note = q('.ks-upload-note')[0]?.textContent ?? ''
    /* ⚠ 这里**只要求来源目录被填上了非空值**（它来自同源 `/ks/ingest/inbox-default` 的 `data.dir`）——
       不把那个绝对路径**钉死**：那是 host 按本机数据目录给的（本脚本的桩给的是
       `D:\KnowledgeStation\inbox`，真机给的是「待入库」），钉死就是拿桩的常量当规范。 */
    mustLand(q('.ks-upload').length === 1 && dir.trim().length > 0
      && note.includes('标准') && note.includes('不会进自动识别'),
      `kb-upload 面板不成立：面板 ${String(q('.ks-upload').length)} 个、来源目录「${dir}」、`
      + `说明「${note.slice(0, 60)}」`)
    notes.push(`kb-upload: 进「标准」→ 点「上传到这一层」→ 面板 ${String(q('.ks-upload').length)} 个、`
      + `来源目录「${dir}」、说明「${note.trim().slice(0, 60)}…」`)
    /* ⚠⚠ **2026-09-21 第 5 步复核 R3**：顺手点开「逐篇看」⇒ **复活的入库预览面板**（`KsIngestPanel`，
       `.ks-ing`）必须真的挂进 DOM。判据分两半：
        · 这里（jsdom 结构）：`.ks-upload-preview` 在、里面的 `.ks-ing` 在、面板自己的特征文案在；
        · 真 Chrome（#kspad）：`kb|kb-upload` 这一跑**声明了** `.ks-ing` ⇒ 量不到或高度 0 都红
          （复核的变异 V6「`{false ? (` 让它永不挂载」在这一半当场红）。 */
    await click(q('.ks-upload-preview-open')[0])
    const prevOpen = q('.ks-upload-preview').length
    const ingOpen = q('.ks-upload-preview .ks-ing').length
    const ingText = q('.ks-upload-preview .ks-ing')[0]?.textContent ?? ''
    mustLand(prevOpen === 1 && ingOpen === 1 && ingText.includes('只读预览'),
      `kb-upload 的「逐篇看」没把入库预览面板挂出来：.ks-upload-preview ${String(prevOpen)} 个、`
      + `.ks-ing ${String(ingOpen)} 个、面板文案含「只读预览」=${String(ingText.includes('只读预览'))}`)
    notes.push(`kb-upload（逐篇看）: 点开后面板 ${String(prevOpen)} 个 / .ks-ing ${String(ingOpen)} 个`
      + `（文案含「只读预览」=${String(ingText.includes('只读预览'))}）—— 真 Chrome 侧由 #kspad 量它的高度`)
  } else if (how === 'kb-inbox') {
    /* 「待分类」这一层（第 4 步）：左列那一行点进去 ⇒ 四行待分类（四种档位各一行）。
       这一跑同时是 `inboxCheck`（真 Chrome 里量：列对齐 / 状态列**看得见** / 勾选框与 ⋮ 逐行在场）
       的取证场景 —— 业主"每篇状态如实显示"必须有**真浏览器里量得到**的判据。 */
    await gotoRoot()
    await click(q('.ks-tree-name-inbox')[0])
    const rows = q('.ks-item.ks-inbox-row')
    mustLand(rows.length === 4 && q('.ks-list-inbox').length === 1
      && q('.ks-search input').length === 1,
      `kb-inbox 没走到待分类层：行 ${String(rows.length)}（期望 4）、列表 ${String(q('.ks-list-inbox').length)} 个、`
        + `搜索框 ${String(q('.ks-search input').length)} 个`)
    notes.push(`kb-inbox: 待分类层 → 行 ${String(rows.length)}、列头「`
      + `${q('.ks-list-inbox .ks-lhead .ks-cell').map((el) => (el.textContent ?? '').trim()).join('|')}」`
      + `、状态列首行「${(q('.ks-inbox-row .ks-col-istage')[0]?.textContent ?? '').replace(/\s+/g, ' ').trim()}」`)
  } else if (how === 'kb-inbox-picked') {
    /* 勾两篇 ⇒ 悬浮批量条出现（**真**批量：四条动作都对应真接口）。
       这一跑是 `inboxCheck` 里"批量条在场且不贴边"（`PAD_REQUIRED` 声明了 `.ks-batch`）的取证场景。 */
    await gotoRoot()
    await click(q('.ks-tree-name-inbox')[0])
    const boxes = q('.ks-inbox-row .ks-col-pick input[type=checkbox]')
    await click(boxes[0])
    await click(boxes[3])
    const btns = [...q('.ks-batch button')].map((b) => (b.textContent ?? '').trim())
    mustLand(q('.ks-batch').length === 1 && boxes.length === 4
      && ['接受建议', '放进同一目录', '重来一次', '删除'].every((t) => btns.some((b) => b.includes(t))),
      `kb-inbox-picked 批量条不成立：条 ${String(q('.ks-batch').length)} 个、勾选框 ${String(boxes.length)} 个、`
        + `按钮 ${JSON.stringify(btns)}`)
    notes.push(`kb-inbox-picked: 勾 2 篇 → 批量条「${(q('.ks-batch-n')[0]?.textContent ?? '').trim()}」`
      + `、按钮 ${JSON.stringify(btns)}`)
  } else if (how === 'ingest-batch') {
    const ok = await click(byText('button', '开始预览'))
    const batchRows = q('button').filter((b) => /\.pdf$/.test((b.textContent ?? '').trim())).length
    mustLand(ok && batchRows > 0, `ingest-batch ${ok ? '点了按钮' : '没找到「开始预览」'} 但批量行 ${batchRows} 条`)
    notes.push(`ingest-batch: ${ok ? '点了「开始预览」' : '没找到按钮'}`
      + ` → 批量行 ${batchRows} 条`
      + `，总账 ${container.textContent.includes('共评估') ? '有' : '无'}`
      + `，失败 ${container.textContent.includes('预览失败') ? container.textContent.split('预览失败')[1]?.slice(0, 60) : '无'}`)
  } else if (how === 'office-page') {
    /* S2-a1（2026-09-22）：原 cap-dialog（点卡片「设置…」开窗）随**卡片式作废**换新 ——
       现在点菜单第一行进专门页面，判「返回办事台」钮在（导航真的通）。 */
    const row = q('.ks-off-row')[0]
    const ok = await click(row)
    const back = [...document.querySelectorAll('button')].find((b) => (b.textContent ?? '').includes('返回办事台'))
    mustLand(ok && back !== undefined,
      `office-page ${ok ? '点了第一行' : '没找到菜单行'} 但「返回办事台」钮 ${back === undefined ? '不在' : '在'}`)
    notes.push(`office-page: ${ok ? '点了第一行进专门页面' : '没找到行'}`
      + `；返回钮 ${back === undefined ? 0 : 1} 个`)
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

/* ⚠⚠ **模板串完整性守卫**（2026-09-23 接手批新增）—— 为什么值得单写一条：
 * `ksGuideStyles.ts` 的样式全写在**一个模板字符串**里，而注释里出现**反引号**会把模板串
 * 提前截断：`tsc` 报出来的是一堆 `TS1005: ';' expected`（每一行都报），**看不出真正的原因**；
 * 而本脚本这边的正则**照样能抠出一段**（截断点那一行本身就是反引号）⇒ 会拿一份**截掉尾巴的
 * CSS** 去截图，图看着"像那么回事"却少了后面所有规则。
 * ⚠ 这不是假想的坑：本批我自己**连踩 4 次**（同一个注释里写反引号），每次都要 `tsc` 报一大片
 *   才发现。⇒ 两条机器判据，当场把原因说出来（而不是让人去数 200 行 TS1005）：
 *   ① 抠出来的样式里**不许再有反引号**（有 ⇒ 模板串在更早处就被截断了）；
 *   ② 抠出来的样式末尾必须是 `}`（模板串最后一条规则是 `.ks-page .ks-kb,…{…}`），
 *      否则说明尾巴被切掉了。
 * ⚠ 本段在**模板字符串内部**（外层是 html 模板）：这一段我自己**不许写反引号**
 *   （写一个就把外层模板截断 —— 本批已经因为这个坑在 tsc 上红了 4 次），
 *   需要提到那个字符时一律用 String.fromCharCode(96) 拼出来。 */
{
  const BT = String.fromCharCode(96)
  const bt = ksStyles.indexOf(BT)
  if (bt !== -1) {
    console.error('❌ ksGuideStyles.ts 的 KS_STYLES **被提前截断了**：抠出来的样式里还有反引号'
      + `（第 ${String(bt)} 个字符附近：${JSON.stringify(ksStyles.slice(Math.max(0, bt - 60), bt + 20))}）`
      + ' —— 十有八九是**某段注释里写了反引号**。这不是 CSS 问题，tsc 报的一片 TS1005 都是这一个根因。')
    process.exit(1)
  }
  if (!ksStyles.trimEnd().endsWith('}')) {
    console.error('❌ ksGuideStyles.ts 的 KS_STYLES **尾巴被切掉了**：抠出来的样式最后不是'
      + `「${'}'}」，而是 ${JSON.stringify(ksStyles.slice(-60))}`
      + ' —— 模板串没有正常收尾（同上：注释里的反引号）。')
    process.exit(1)
  }
}

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
 * ⚠⚠ **2026-09-21（第 3 步）：`--band-scroll` 的注入段整段删除** —— 它滚的是卡片带
 *   （`.ks-kbband-clip`），那块界面已被业主删掉；现在没有横向滚动容器可滚。
 *   参数本身在更上面被**显式拒绝**（exit 2），所以这里不再有 `bandScrollStmt`。
 */

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
/* 量高 + 量几何：**浏览器里算出来的真值**，随 dump-dom 回传（截的是同一份 HTML）。
   ⚠ 本段在**模板字符串**里：注释不许用反引号（会截断模板），也不许写美元加大括号（会被当插值）。 */
(function () {
  try {
    var sels = ['#ks-shell','.ks-item','.ks-detail','.ks-rail','.ks-main','.ks-kb-card','.ks-cap-card',
                '.ks-lhead','.ks-page-title','.ks-kb-tn','.ks-item-tags','.ks-item-add',
                '.ks-cap-engine','.ks-knob-label','.ks-kb-banner','.ks-field',
                '.ks-list','.ks-status','.ks-item-more','.ks-item-title','.ks-item-sub',
                '.ks-item-name','.ks-item-meta','.ks-empty-card','.ks-empty-t','.ks-empty-d',
                /* ⚠ .ks-fileico 现在**只由目录行**使用（2026-09-22 业主把文件行那个图标删了，
                   见 smoke-kb-page-render 的 E6/B10）；名字留在名单里是因为它仍然量得到。
                   ⚠ 本段在模板字符串里：注释里不许出现反引号（本仓已踩 21 次）。 */
                '.ks-search','.ks-fileico','.ks-list-cap','.ks-cell','.ks-col-stage','.ks-col-date','.ks-col-status',
                '.ks-lhead-col',
                /* ⚠ 名单里**刻意留着几个已经量不到的名字**（.ks-rail / .ks-kb-tn / .ks-item-tags /
                   .ks-item-add / .ks-tag / .ks-batch / .ks-chip / .ks-filters / .ks-tagrow /
                   .ks-kbband* / .ks-dir / .ks-check / .ks-col-tags）：它们对应的界面在
                   2026-09-20/21 两轮里被业主点名删掉 ⇒ 让"量不到"在产物里**可见**，
                   而不是悄悄从名单里抠掉（那才让人以为"从来没有过"）。
                   ⚠ 本段在模板字符串里：注释里不许出现反引号。 */
                '.ks-rail','.ks-kb-tn','.ks-item-tags','.ks-item-add','.ks-tag','.ks-batch','.ks-batch-btn',
                '.ks-chip','.ks-filters','.ks-tagrow','.ks-dir','.ks-check','.ks-col-tags',
                '.ks-kbband','.ks-kbband-nav','.ks-kbband-clip',
                /* 2026-09-21（第 3 步）新形态的量点：左列目录树 / 面包屑（逐级可点）/ 返回 /
                   目录层列表 / 翻页条 / 上传面板 / 错误条。 */
                '.ks-kb-tree','.ks-tree-head','.ks-tree-row','.ks-tree-name','.ks-tree-count',
                '.ks-crumb','.ks-crumb-path','.ks-crumb-item','.ks-crumb-go','.ks-crumb-here','.ks-crumb-n',
                '.ks-back','.ks-pager','.ks-pager-n','.ks-pager-btn','.ks-upload','.ks-upload-row',
                '.ks-upload-note','.ks-upload-msg','.ks-kb-err',
                '.ks-list-dirs','.ks-dir-row','.ks-dirs','.ks-dir-name',
                /* 2026-09-21（第 4 步）「待分类」层的量点：列表 / 行 / 勾选 / 状态 / 建议去向 / 批量条。 */
                '.ks-list-inbox','.ks-inbox-row','.ks-col-pick','.ks-col-iname','.ks-col-istage',
                '.ks-col-idest','.ks-col-imore','.ks-stage','.ks-stage-tag','.ks-stage-why',
                '.ks-stage-conf','.ks-stage-hidden','.ks-dest','.ks-dest-path','.ks-dest-new',
                '.ks-batch-n','.ks-act','.ks-act-item','.ks-tree-name-inbox',
                /* 5j（2026-09-20）页面留边：量这几个盒子的**绝对坐标**（.ks-page 是那个只管
                   container-type 的容器，.ks-kb/.ks-ing/.ks-mat 是三个页面根，.ks-split 是
                   "详情栏有没有被挤到第二行"的锚点）。**判据不在这里**（这里只报告），
                   Node 侧的 ksPadCheck 按 #kspad 逐条判 —— 见本段下面的 #kspad 段。 */
                '.ks-page','.ks-kb','.ks-ing','.ks-mat','.ks-split','.ks-batch'];
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
          // 这一行是哪一层（2026-09-21 补）：目录行与文件行的行内控件数**不是一回事**
          // （目录行 0 个、文件行 = ⋮ + 状态徽章）⇒ 判"等于冻结值"时必须先按层分开。
          var kind = el.classList.contains('ks-file-row') ? 'file'
            : (el.classList.contains('ks-dir-row') ? 'dir'
              : (el.classList.contains('ks-inbox-row') ? 'inbox' : '?'));
          return { kind: kind,
                   rowW: Math.round(r0.width), nameW: rc ? Math.round(rc.width) : null,
                   fileNameW: rf ? Math.round(rf.width) : null,
                   nameRight: rc ? Math.round(rc.right - r0.left) : null,
                   tagsLeft: rt ? Math.round(rt.left - r0.left) : null,
                   deadGap: (rc && rt) ? Math.round(rt.left - rc.right) : null,
                   btnH: rm ? Math.round(rm.height) : null,
                   ctrls: ctrls };
        }) };
    }
    /* ⚠⚠ **2026-09-21（第 3 步）：#kbband / #kbcards 两个量点整段删除。**
       它们量的是**卡片带**（.ks-kbband-clip 的滚动几何、逐张卡的宽/高"全等"），
       而卡片带已被业主删掉（"原来的大卡片去掉"）⇒ 量点没有主体了。
       取代它们的是下面两个新量点（Node 侧的 levelCheck 逐条判）：
         · #kbtree    —— 左列目录树与右栏的**相对位置**（必须并排，不是换行堆叠）
         · #levelrows —— 同一级里**目录行与文件行**的行高（必须逐字相同） */
    /* **目录层表头每一格的 display**（2026-09-21 复核 verify-freeze-kb-ui3 打回 §④-C 第 3 条：
       旧版第 29 条判的是"表头每一格必须是 flex，不能是 grid"—— 那一格被 grid 接管时，
       「目录」两个字会被当成两轨、只剩一个「目」。这条断言在本批重写时**掉了**，补回来。
       ⚠ 本段在**注入脚本**里（外层是模板字符串）：注释里绝对不能出现反引号 —— 第 18 次了。
       借字段名：n=表头格数 x=display 是 flex 的格数 y=display 是 grid 的格数
       w=1 表示量到了 h=0 fs='' lh=逐格 display 串 pad='' gap='' radius='' */
    var dhCells = document.querySelectorAll('.ks-list-dirs .ks-lhead .ks-cell');
    if (dhCells.length > 0) {
      var dhDisplays = [].map.call(dhCells, function (el) { return getComputedStyle(el).display; });
      out['#dirhead'] = {
        n: dhCells.length,
        x: dhDisplays.filter(function (d) { return d === 'flex'; }).length,
        y: dhDisplays.filter(function (d) { return d === 'grid'; }).length,
        w: 1, h: 0, fs: '', lh: dhDisplays.join(','), pad: '', gap: '', radius: '',
      };
    }
    /* 左列目录树（.ks-kb-tree）与右栏（.ks-main）的绝对坐标：判"并排"。
       借字段名（同 #cards / #cols 的先例，注释里写清就不算说谎）：
         x=左列右缘 y=右栏左缘 w=左列宽 h=右栏宽 fs='' lh=左列高 pad='' gap='' radius='' */
    var treeEl = document.querySelector('.ks-kb-tree');
    var mainEl = document.querySelector('.ks-main');
    if (treeEl && mainEl) {
      var tr = treeEl.getBoundingClientRect();
      var mr = mainEl.getBoundingClientRect();
      out['#kbtree'] = {
        n: document.querySelectorAll('.ks-kb-tree').length,
        x: Math.round(tr.right), y: Math.round(mr.left),
        w: Math.round(tr.width), h: Math.round(mr.width),
        fs: '', lh: String(Math.round(tr.height)), pad: '', gap: '', radius: '',
      };
    }
    /* 同一级里**两类行**的行高（目录行 + 文件行）。判据：两者必须逐字相同
       （"目录层与文件列表同构"这句承诺的可量形态：同一个 --ks-row-h-list）。
       借字段名：x=目录行数 y=文件行数 w=目录行高 h=文件行高 fs='' lh='' pad='' gap='' radius='' */
    var dirRowEls = document.querySelectorAll('.ks-dir-row');
    var fileRowEls = document.querySelectorAll('.ks-item.ks-file-row');
    if (dirRowEls.length > 0 && fileRowEls.length > 0) {
      out['#levelrows'] = {
        n: dirRowEls.length + fileRowEls.length,
        x: dirRowEls.length, y: fileRowEls.length,
        w: Math.round(dirRowEls[0].getBoundingClientRect().height),
        h: Math.round(fileRowEls[0].getBoundingClientRect().height),
        fs: '', lh: '', pad: '', gap: '', radius: '',
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
    // **办事台每一行 .ks-off-row 的逐个宽/高**（2026-09-22 v3 形态更正留痕：原为能力页
    //   .ks-cap-card 的"等宽 + 同排等高"；卡片式已作废 ⇒ 判据翻成**菜单行全部等高**，
    //   "排"概念随单列菜单消亡）。借字段名不变（#capcards 键名为历史遗留）。
    // ⚠ 本段是模板字符串里的一段 JS：注释里**不许出现反引号**（见 UI-BASELINE 5h-补）。
    var capEls = document.querySelectorAll('.ks-off-row');
    if (capEls.length > 0) {
      var cw = [].map.call(capEls, function (el) { return Math.round(el.getBoundingClientRect().width); });
      var chh = [].map.call(capEls, function (el) { return Math.round(el.getBoundingClientRect().height); });
      var ctop = [].map.call(capEls, function (el) { return Math.round(el.getBoundingClientRect().top); });
      out['#capcards'] = {
        n: capEls.length,
        x: Math.min.apply(null, cw), y: Math.max.apply(null, cw),
        w: Math.min.apply(null, chh), h: Math.max.apply(null, chh),
        fs: '', lh: cw.join(','), pad: chh.join(','), gap: '', radius: '',
        items: [].map.call(capEls, function (el, i) {
          return { name: (el.textContent || '').trim().replace(/\s+/g, ' ').slice(0, 14), w: cw[i], h: chh[i], top: ctop[i] };
        }),
      };
    }
    /* ⚠⚠ **2026-09-21（第 3 步）**：.ks-batch#fit 那个量点（批量条"一行装得下吗"）**已删除** ——
       悬浮批量条随"批量选择动作不在本批"整块撤掉，没有主体了。
       --hide-scrollbars 那条取舍（5h-补 为让卡片带的滑动条入镜而撤掉它）也随卡片带一起失去对象；
       本脚本**仍然不传**那个开关（不为了旧理由改回去，改回去只会少一个真实滚动条的可见性）。 */
    // 表格列对齐（P2 头条，2026-09-20）：**表头行与数据行的 computed 列模板必须逐字相同**。
    // 这是"列对齐"的唯一机械证据（jsdom 里量不到网格），所以放在真 Chrome 的这段脚本里量。
    // ⚠⚠ **P2 复核打回 B（2026-09-20，变异 M4）**：原来它只是**报告值**（没有断言）⇒ 把表头的
    //   grid-template-columns 改成与行不一致，本脚本照旧 exit 0、smoke 也 33/33 全绿。
    //   ⇒ 现在 Node 侧对它下断言（见文件末尾「#cols 的**真断言**」），三档由 smoke-kb-cols 逐档跑。
    // 借字段名：lh = 表头行的 grid-template-columns，pad = 第一数据行的；gap = 表头的 column-gap，
    // radius = **行**的 column-gap（同名借用，见 #cards 的先例 —— 注释里写清就不算说谎）。
    // n = 这一行里 cell 的个数（窄/宽两档都是 5：窄档是隐藏两列，不是删 DOM）；x = 第一行的 cell 数。
    // ⚠⚠ **2026-09-20 头条：两层各有一条 .ks-lhead / .ks-item，必须"按层配对"取**。
    //   这一段原来取的是**页面上第一个** .ks-lhead 与第一个 .ks-item —— 两层同构之后，
    //   它在"目录层表头 + 文件行"（或反过来）这种**跨层组合**下会拿去比，**必假红**
    //   （本批实测：kb-crumb 场景下报的是「表头 1152px 72px 36px / 行 206.328px 72px 36px」，
    //   而那两条根本不是同一层的。⇒ 判据不变（"同一层的表头与行必须逐字相同"），
    //   只是**先按层把两者配对**：目录层用 .ks-list-dirs 里的，文件层用 .ks-list（排除目录层）里的。
    //   ⚠ 层内取"第一个"数据行：目录层的第 1 行与文件层的第 1 行各与**本层**表头比。
    //   ⚠ 变量的**借用**口径与文件末尾那段 Node 侧注释一致（lh=表头模板 / pad=行模板 /
    //     gap=表头列距 / radius=行列距）。
    var dirList = document.querySelector('.ks-list-dirs');
    /* ⚠⚠ **2026-09-21（第 4 步）就地收窄**：文件层的选择器加上 :not(.ks-list-inbox)
       —— 「待分类」层也有一个 .ks-list（它有自己的 5 轨列模板：勾选/文件名/状态/建议去向/⋮）。
       不收窄的话，kb-inbox 那一跑会把**待分类层**当成文件层来量（列模板当然"相等"，
       但状态列的类名/列头完全不是一回事）⇒ #cols / #stagecol 会报**假红**或**假绿**。
       待分类层有自己的量点 #inboxcols（见下面那一段，Node 侧 inboxCheck 逐条判）。 */
    var fileList = document.querySelector('.ks-list:not(.ks-list-dirs):not(.ks-list-inbox)');
    var lhead = null;
    var firstRow = null;
    if (dirList && dirList.querySelector('.ks-item')) {
      lhead = dirList.querySelector('.ks-lhead');
      firstRow = dirList.querySelector('.ks-item');
    } else if (fileList && fileList.querySelector('.ks-item')) {
      lhead = fileList.querySelector('.ks-lhead');
      firstRow = fileList.querySelector('.ks-item');
    }
    if (lhead) {
      var lcs = getComputedStyle(lhead);
      var rcs = firstRow ? getComputedStyle(firstRow) : null;
      var ln = lhead.children.length;
      var rn = firstRow ? firstRow.children.length : 0;
      // ⚠ 诊断字段（借 y/w/h 三个没人用的槽，见 #cards 的先例）：**量到的是哪一层**。
      //   不留它的话，"跨层配对"这种假红只能靠人猜（本批实测踩过一次）。
      //   dir = 目录层 / file = 文件层；空串 = 没量到（理论上到不了这里）。
      var layerTag = (dirList && dirList.querySelector('.ks-item') && dirList.contains(lhead))
        ? 'dir' : (fileList && fileList.contains(lhead) ? 'file' : '?');
      out['#cols'] = { n: ln, x: rn, y: layerTag.length, w: 0, h: 0, fs: '',
                       lh: lcs.gridTemplateColumns, pad: rcs ? rcs.gridTemplateColumns : '(没有数据行)',
                       gap: lcs.columnGap || lcs.gap, radius: rcs ? (rcs.columnGap || rcs.gap) : '(没有数据行)' };
    }
    // **「处理状态」列到底看不看得见**（2026-09-21 第 3 步）。
    // 业主明说"所有文件都要显示处理状态"（好发现哪些文件要人工修）；而这一列在窄档是
    // **故意**藏起来的（ksGuideStyles.ts 里的 .ks-list .ks-cell.ks-col-stage{display:none}，
    // 宽档由 @container (min-width:660px) 恢复）=> "到底看没看见"必须在**真浏览器**里量：
    // jsdom 那条判的是 textContent，而 display:none 的元素照样取得到文字（**它不构成证据**）。
    // ⚠ 本段在**注入脚本**里（外层是模板字符串）：注释里绝对不能出现反引号与美元加大括号
    //    —— 2026-09-21 我自己在这里踩了第 17 次（反引号把模板截断，报错指向一行不相干的代码）。
    // 借字段名（同 #cards / #cols 的先例）：n=文件行数 x=状态列列头在不在 y=主栏内容宽
    // w=1 表示状态列可见 h=1 表示生效日期列可见 fs=状态列列头文案
    // lh=状态列 computed display pad=生效日期列 computed display。
    var fileListEl = document.querySelector('.ks-list:not(.ks-list-dirs):not(.ks-list-inbox)');
    var fRows = fileListEl ? fileListEl.querySelectorAll('.ks-item') : [];
    var stageCell0 = fileListEl ? fileListEl.querySelector('.ks-item .ks-col-stage') : null;
    var dateCell0 = fileListEl ? fileListEl.querySelector('.ks-item .ks-col-date') : null;
    var stageHeadEl = fileListEl ? fileListEl.querySelector('.ks-lhead .ks-col-stage') : null;
    var mainEl = document.querySelector('.ks-main');
    out['#stagecol'] = {
      n: fRows.length,
      x: stageHeadEl ? 1 : 0,
      y: mainEl ? Math.round(mainEl.clientWidth) : 0,
      w: stageCell0 && getComputedStyle(stageCell0).display !== 'none' ? 1 : 0,
      h: dateCell0 && getComputedStyle(dateCell0).display !== 'none' ? 1 : 0,
      fs: stageHeadEl ? (stageHeadEl.textContent || '').trim() : '',
      lh: stageCell0 ? getComputedStyle(stageCell0).display : '(没有状态列单元格)',
      pad: dateCell0 ? getComputedStyle(dateCell0).display : '(没有日期列单元格)',
      gap: '', radius: '',
    };
    // **「待分类」层的几何 + 状态列到底看不看得见**（2026-09-21 第 4 步）。
    // 为什么必须**真浏览器里量**：jsdom 那条判的是 textContent，而 display:none 的元素照样
    // 取得到文字（第 3 步复核自己踩出来的洞）⇒ 业主"每篇状态如实显示"要有可量形态。
    // 判据在 Node 侧 inboxCheck 逐条下（这里只量，不判）。
    // 借字段名（同 #cards / #cols 的先例）：n=行数 x=列头轨道数 y=列头模板 w=行模板
    // h=1 状态列看得见、0 看不见 fs=状态列列头文案 lh=状态列 computed display
    // pad=建议去向列 computed display，另加 pickN/checkedN/batch 三个诊断字段。
    // ⚠ 本段在**注入脚本**里（外层是模板字符串）：注释里不许出现反引号与美元加大括号。
    var inboxList = document.querySelector('.ks-list-inbox');
    if (inboxList) {
      var iHead = inboxList.querySelector('.ks-lhead');
      var iRow = inboxList.querySelector('.ks-item');
      var iHeadCs = iHead ? getComputedStyle(iHead) : null;
      var iRowCs = iRow ? getComputedStyle(iRow) : null;
      var iStageCell = inboxList.querySelector('.ks-item .ks-col-istage');
      var iDestCell = inboxList.querySelector('.ks-item .ks-col-idest');
      var iStageHead = inboxList.querySelector('.ks-lhead .ks-col-istage');
      var iMain = document.querySelector('.ks-main');
      var iPicks = inboxList.querySelectorAll('.ks-col-pick input[type=checkbox]');
      var iChecked = 0;
      for (var pi2 = 0; pi2 < iPicks.length; pi2++) { if (iPicks[pi2].checked) iChecked++; }
      out['#inboxcols'] = {
        n: inboxList.querySelectorAll('.ks-item').length,
        x: iHead ? iHead.children.length : 0,
        y: iHeadCs ? iHeadCs.gridTemplateColumns : '(没有表头)',
        w: iRowCs ? iRowCs.gridTemplateColumns : '(没有数据行)',
        h: iStageCell && getComputedStyle(iStageCell).display !== 'none' ? 1 : 0,
        fs: iStageHead ? (iStageHead.textContent || '').trim() : '',
        lh: iStageCell ? getComputedStyle(iStageCell).display : '(没有状态列单元格)',
        pad: iDestCell ? getComputedStyle(iDestCell).display : '(没有建议去向单元格)',
        gap: String(iMain ? Math.round(iMain.clientWidth) : 0),
        radius: JSON.stringify({ pickN: iPicks.length, checkedN: iChecked,
          batchN: document.querySelectorAll('.ks-batch').length,
          rows: inboxList.querySelectorAll('.ks-item .ks-col-imore button').length }),
      };
    }
    // **第 6 步：按目录范围提问的界面（「在此范围内提问」按钮 + 范围 chip + 提问面板）**。
    // 为什么必须**真浏览器里量**：jsdom 侧只能判"元素在不在、文字对不对"，而业主看的是
    //   "看不看得见、有没有被挤出框" —— display:none / 空盒子 / 溢出右缘在 jsdom 里都量不到。
    // 判据在 Node 侧 askCheck 逐条下（这里只量，不判）。
    // 借字段名（同 #cards / #cols 的先例）：n=按钮个数 x=chip 个数 y=面板个数
    // w=按钮高 h=chip 高 pad=面板高 fs=按钮文字 lh=chip 文字
    // gap=chip **右缘溢出量**（chip 右缘 - **它所在那一行**的内容盒右缘；<=1 = 没溢出）
    // ⚠ 2026-09-22 复核打回 §1 之前，这里的基准是 chip 的**直接父元素** —— 套一层 wrapper 就恒 0。
    // radius=那一行的右内边距（这一档的留边，供诊断）。
    // ⚠ 本段在**注入脚本**里（外层是模板字符串）：注释里不许出现反引号与美元加大括号。
    var askBtnEl = document.querySelector('.ks-ask-open');
    var askChipEl = document.querySelector('.ks-ask-chip');
    var askPanelEl = document.querySelector('.ks-ask');
    if (askBtnEl || askChipEl || askPanelEl) {
      // 按钮/chip "在哪一行"：以**最近的已知行容器**为准（文件名那一行 vs 工具栏 vs 其它）。
      // ⚠⚠ **2026-09-22（复核打回 §1）**：溢出量原来量的是 chip 的**直接父元素**
      //   （chip 的直接父元素）—— 那个写法**只要给 chip 套一层 wrapper 就退化成恒真**：
      //   wrapper 的内容盒右缘恒等于 chip 的右缘 ⇒ 溢出量恒 ≈ 0，chip 真被挤出这一行也报绿。
      //   ⇒ 现在改成量**那一行本体**：用 closest() 按**类名**找到行元素（.ks-list-cap /
      //   .ks-kb-row / .ks-ask），再拿它的内容盒右缘当基准；并额外量一个**元素身份**比较
      //   （chipRowSame：chip 所在的行元素 === 按钮所在的行元素），不靠"父元素是谁"推。
      //   ⚠ 本段在**注入脚本**里（外层是模板字符串）：注释里**绝对不能出现反引号** ——
      //     2026-09-22 我在这里又踩了两次（本次第 22、23 次），报错都指向不相干的行。
      var askRowEl = function (el) {
        if (!el) return null;
        return el.closest('.ks-list-cap') || el.closest('.ks-kb-row') || el.closest('.ks-ask');
      };
      var askRowOf = function (el) {
        if (!el) return '(没有元素)';
        var r = askRowEl(el);
        if (!r) return 'other';
        if (r.classList.contains('ks-list-cap')) return 'list-cap';
        if (r.classList.contains('ks-kb-row')) return 'kb-row';
        return 'ask-panel';
      };
      var askChipRowEl = askRowEl(askChipEl);
      var chipRowCs = askChipRowEl ? getComputedStyle(askChipRowEl) : null;
      var chipRowRect = askChipRowEl ? askChipRowEl.getBoundingClientRect() : null;
      var chipRect = askChipEl ? askChipEl.getBoundingClientRect() : null;
      var rowRight = null;
      if (chipRowRect && chipRowCs) {
        rowRight = chipRowRect.right - (parseFloat(chipRowCs.paddingRight) || 0);
      }
      out['#ask'] = {
        n: askBtnEl ? 1 : 0,
        x: askChipEl ? 1 : 0,
        y: askPanelEl ? 1 : 0,
        w: askBtnEl ? Math.round(askBtnEl.getBoundingClientRect().height) : 0,
        h: chipRect ? Math.round(chipRect.height) : 0,
        fs: askBtnEl ? (askBtnEl.textContent || '').trim() : '',
        lh: askChipEl ? (askChipEl.textContent || '').trim() : '',
        pad: askPanelEl ? Math.round(askPanelEl.getBoundingClientRect().height) : 0,
        gap: (chipRect && rowRight !== null) ? Math.round(chipRect.right - rowRight) : '',
        radius: chipRowCs ? (parseFloat(chipRowCs.paddingRight) || 0) : '',
        where: askRowOf(askBtnEl),
        chipWhere: askRowOf(askChipEl),
        chipRowSame: (askBtnEl && askChipEl)
          ? (askRowEl(askChipEl) === askRowEl(askBtnEl)) : '',
      };
    }
    // **目录层的列几何**（2026-09-21，复核 verify-freeze-dirlist 的变异 M5 打回）：
    // 复核把目录层的 --ks-cols 换成**文件层那 5 列** ⇒ 本脚本的 #cols 自检**照样通过**
    // （它只比"表头 == 行"，两边当然一起变），而真机上是**首列 344→88px + 168px 死白**。
    // ⇒ 这里单独量**目录层容器**：轨道数 + 轨道和 + gap 必须**铺满**它的内容宽（clientWidth）。
    //   借字段名（同 #cards / #cols 的先例）：x=行内 cell 数 y=容器内容宽 w=1（量到了）h=0、
    //   fs=''、lh=轨道串（解析后）、pad=gap、gap=''、radius=''。
    //   ⚠ 本段在**注入脚本**里（外层是模板字符串）：注释里**绝对不能出现反引号** ——
    //     2026-09-21 我在这里踩了第 16 次（三个反引号把模板截断，报错指向一行不相干的代码）。
    var dl2 = document.querySelector('.ks-list-dirs');
    if (dl2) {
      // ⚠ 模板要从**网格元素**上取（容器 .ks-list-dirs 自己是 display:block ⇒ 它的
      //   grid-template-columns 解析成 none，拿它比对等于没量）。
      // ⚠⚠ 宽度必须是**网格元素的内容盒**宽，不是容器的 clientWidth —— 表头/行自己带
      //   左右内边距（实测 12px×2），拿容器宽比会**差 24px 假红**（2026-09-21 我自己踩到）。
      var dGrid = dl2.querySelector('.ks-lhead') || dl2.querySelector('.ks-item');
      var dcs = dGrid ? getComputedStyle(dGrid) : null;
      var dPadL = dcs ? (parseFloat(dcs.paddingLeft) || 0) : 0;
      var dPadR = dcs ? (parseFloat(dcs.paddingRight) || 0) : 0;
      out['#dircols'] = { n: 1, x: dl2.children[0] ? dl2.children[0].children.length : 0,
                          y: dGrid ? Math.round(dGrid.clientWidth - dPadL - dPadR) : 0, w: 1, h: 0, fs: '',
                          lh: dcs ? dcs.gridTemplateColumns : '(没有网格元素)',
                          pad: String(dcs ? (parseFloat(dcs.columnGap) || 0) : 0),
                          gap: '', radius: String(Math.round(dl2.clientWidth)) };
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
                    ['.ks-kb-tree', 0], ['.ks-list', 0], ['.ks-dirs', 0],
                    ['.ks-page-head', 0], ['.ks-kb-row', 0], ['.ks-empty-card', 0],
                    /* 第 4 步：悬浮批量条（.ks-batch）**回到适用面**里 —— 第 3 步它随"假批量"
                       一起从这份表和规范里撤掉过；现在批量是真接口驱动的，条子也必须不贴边。 */
                    ['.ks-batch', 0]];
      /* ⚠⚠ 2026-09-20 头条：目录层换了形态（卡片网格 → 与文件列表同构的列表），但**不新增适用面**：
         新容器同时挂着 .ks-list 与 .ks-dirs 两个类，**两个都已在上面这张表里** ⇒ 覆盖没变窄。
         为什么**刻意不加** .ks-list-dirs 这个第三名字：这张表与"规范第二节 + PAD_SUBJECTS_ALL
         + PAD_REQUIRED + smoke-kb-pad-pixels 的 SPEC_SUBJECTS"绑成**逐字一致**的棘轮
         （本文件末尾那段自检会当场报"只在脚本里=[...]"）⇒ 加它就得同时改**规范文档**，
         而那等于为同一个元素在规范里立第二个名字（规范该收窄而不是变宽）。
         实测过这条路的代价：本批先加过 .ks-list-dirs，自检立刻红在
         「规范第二节的适用面与本脚本的 PAD_SUBJECTS_ALL 不一致 ⇒ 只在脚本里=[.ks-list-dirs]」。
         ⚠ 本注释里不许出现反引号（整段在模板字符串里）。 */
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
      /* ⚠⚠ 2026-09-21 第 5 步复核 R3：原来只报 .ks-page 的**个数**，Node 侧要求"恰好 1 个" ——
         而「逐篇看」复活的 KsIngestPanel **自带一层 .ks-page**（它只做 container-type，见其文件头）
         ⇒ 面板一打开页面里就有 2 个 .ks-page ⇒ 整条 ksPad 检查 **skip**（本批实测：CSS 变异
         display:none 时 ksPad 报"这一跑不判"、exit 0 ⇒ R3 的真浏览器那一半**根本验不到**）。
         ⇒ 改成报两件事：① 个数（信息用）；② **这一跑的页面根（.ks-kb/.ks-ing/.ks-mat）是不是被
         **第一个** .ks-page 直接包着**（pageWrapped）—— 那才是这条守卫真正要守的不变式
         （"页面根没被包住"），嵌套的面板外壳不该把它一票否决。判据强度没降：页面根没被包住、
         或第一个 .ks-page 不是它的父级 ⇒ 仍然 skip + 红。
         ⚠ 本段在**注入脚本**里（外层是模板字符串）：注释里绝对不能出现反引号 —— 第 19 次了。 */
      var rootSel = document.querySelector('.ks-kb, .ks-ing, .ks-mat');
      var rootWrapped = !!(pageBox && rootSel && rootSel.parentElement === pageBox);
      out['#kspad'] = { n: padItems.length, x: Math.round(cLeft), y: Math.round(cRight),
                        w: Math.round(shR.width), h: Math.round(shR.height), fs: '', lh: '',
                        pad: String(Math.round(shPl)) + '/' + String(Math.round(shPr)), gap: '',
                        radius: '', pageW: pageBox ? Math.round(pageBox.getBoundingClientRect().width) : 0,
                        pageN: document.querySelectorAll('.ks-page').length,
                        pageWrapped: rootWrapped ? 1 : 0, items: padItems };
    }
    /* ══════════ 四个面的"页头一致 + 不压字"（2026-09-23 接手批新增） ══════════
       ⚠⚠ 为什么必须新增（业主报障原话："把办事台唯一一个还能看的改更糟糕"）：
          · --page kb 这一路以前**只能**截到 params.page='manage' 那一个面 ⇒ 另外三个面
            **从来没有进过真浏览器**，"四个面一致"这件事此前**一次都没被量过**；
          · .ks-list-cap（"当前文件夹名"那一行）里压着 导出效力总览 / 名字 / 在此范围内提问
            / 刷新 —— 业主看的就是这一行"互相压字"。
       这两段都是**只报告、由 Node 侧断言**（本文件一贯口径：报告值必须有断言兜着）。
       ⚠ 本段在**注入脚本**里（外层是模板字符串）：注释里绝对不能出现反引号。 */
    var oneBox = function (sel) {
      var el = document.querySelector(sel);
      if (!el) return null;
      var r = el.getBoundingClientRect();
      var cs = getComputedStyle(el);
      return { x: Math.round(r.left), y: Math.round(r.top),
               w: Math.round(r.width), h: Math.round(r.height),
               fs: cs.fontSize, lh: cs.display, pad: cs.paddingTop + '/' + cs.paddingBottom,
               gap: cs.gap, radius: '', n: el.querySelectorAll('.ks-tabfolder').length };
    };
    /* 四枚标签的名称与"哪一枚被选中"（按**渲染出来的文字**判，不按类名猜）。 */
    var tabEls = [].slice.call(document.querySelectorAll('.ks-tabfolder'));
    var tabLabels = tabEls.map(function (b) { return (b.textContent || '').trim(); });
    var onLabels = tabEls.filter(function (b) { return b.className.indexOf('ks-tabfolder-on') >= 0; })
      .map(function (b) { return (b.textContent || '').trim(); });
    var strip = oneBox('.ks-tabfolder-strip');
    if (strip) {
      strip.pad = tabLabels.join('|');      // 借 pad：四枚标签的**渲染文字**
      strip.gap = onLabels.join('|');       // 借 gap：**被选中**的那一枚（恰好一枚才合格）
    }
    /* ⚠⚠ **"这一跑到底是几个 .ks-page"这件事本身不能当判据**（2026-09-23 接手批实测踩到两次）：
       ① 一、.ks-page 只承担 container-type，**面板自己**也会带一层（KsIngestPanel 自带 —— 见
          #kspad 那段既有的同名留痕；kb-upload 场景一打开就有 2 个）⇒ 上一版写的
          ".ks-page 恰好 1 个"在 kb-upload@520 上**假红**；
       ② 二、四标签外壳的形态是 .ks-page > .ks-kb > nav.ks-tabfolder-strip ⇒ 拿
          "document.querySelector('.ks-page')"（**文档里第一个**）去比，比到的是**别的**
          .ks-page，于是四个面全假红（本跑的 .ks-page 个数明明是 1）。
       ⇒ 真正要守的不变式只有一条：**标签条与页头共处于同一个 .ks-page 之下**
        （改前办事台面是"标签条在**外层** .ks-page、页头与页面内容被**第二层** .ks-page 包着"
        ⇒ 两者**不在**同一个 .ks-page 下，这一条照样抓得住；而面板自带的外壳与它俩无关）。 */
    var ancestorsIn = function (el, sel) {
      var hits = [];
      var cur = el ? el.parentElement : null;
      while (cur) { if (cur.matches && cur.matches(sel)) hits.push(cur); cur = cur.parentElement; }
      return hits;
    };
    var pageEls = [].slice.call(document.querySelectorAll('.ks-page'));
    var stripEl = document.querySelector('.ks-tabfolder-strip');
    var headEl = document.querySelector('.ks-page-head');
    var stripAnc = ancestorsIn(stripEl, '.ks-page');
    var headAnc = ancestorsIn(headEl, '.ks-page');
    var sharedPage = null;
    for (var sai = 0; sai < stripAnc.length; sai++) {
      if (headAnc.indexOf(stripAnc[sai]) >= 0) { sharedPage = stripAnc[sai]; break; }
    }
    out['#face'] = { n: document.querySelectorAll('.ks-tabfolder-strip').length,
                     x: pageEls.length,                                   // x = .ks-page 个数（信息用）
                     y: document.querySelectorAll('.ks-kb').length,       // y = .ks-kb 个数
                     w: document.querySelectorAll('.ks-page-head').length,// w = 页头个数
                     h: strip ? strip.h : 0,
                     /* fs = 标签条与页头**共处同一个 .ks-page** 吗（1/0）；lh 借来报那个 .ks-page
                        的个数上限信息（=1 表示两者只在同一层、没有第二层夹在中间）。 */
                     fs: (sharedPage && stripAnc.length === 1) ? '1' : '0',
                     lh: sharedPage ? String(headAnc.length) : '0',
                     pad: '', gap: '', radius: '',
                     strip: strip, head: oneBox('.ks-page-head'),
                     /* 页头里**真的看得见**的成员（display:none 的不算）——"只留一句介绍"的可量形态。 */
                     headKids: [].slice.call(document.querySelectorAll('.ks-page-head > *')).map(function (e) {
                       var c = getComputedStyle(e);
                       var rr = e.getBoundingClientRect();
                       var shown = c.display !== 'none' && rr.width > 0.5 && rr.height > 0.5;
                       return { cls: String(e.className || '').split(' ')[0], shown: shown ? 1 : 0 }; }) };
    /* ── .ks-list-cap：这一行里可见成员两两**真的相交**吗（业主说的"压字"） ──
       ⚠ "相交"用**边框盒真重叠**判（ox>0.5 且 oy>0.5），不是"看起来挤"；同时把相邻成员的
         **最小水平间隙**报出来 —— 业主的"压字"两种形态（真重叠 / 贴在一起看不出来是两件东西）
         都要有据可查。 */
    var capEl = document.querySelector('.ks-list-cap');
    if (capEl) {
      var cvis = function (el) {
        var c = getComputedStyle(el);
        if (c.display === 'none' || c.visibility === 'hidden' || parseFloat(c.opacity) === 0) return false;
        var r = el.getBoundingClientRect();
        return r.width > 0.5 && r.height > 0.5;
      };
      /* 成员 = 这一行里**可读的叶子控件**。三条判据都要：
         ① 可见；② 装着字（按钮 / 自己带文字节点 / 计数 span）；③ **自己不再装别的控件、
            也不再装别的有字的元素** —— 否则同一个控件会被数两遍（内层 button 与它自己各算一次
            ⇒ 报出"负间隙"这种假阳性；本批实测踩到过：ks-export-effect 被列了两次）。 */
      var hasOwnText = function (el) {
        var kn = [].slice.call(el.childNodes);
        for (var ki = 0; ki < kn.length; ki++) {
          if (kn[ki].nodeType === 3 && (kn[ki].textContent || '').trim() !== '') return true;
        }
        return false;
      };
      var isControl = function (el) { return /^(BUTTON|A|INPUT|SELECT)$/.test(el.tagName); };
      var innerControl = function (el) { return !!el.querySelector('button,a,input,select'); };
      var innerTexted = function (el) {
        var d = [].slice.call(el.querySelectorAll('*'));
        for (var di = 0; di < d.length; di++) {
          if (isControl(d[di])) return true;
          if (d[di].tagName === 'SPAN' && (d[di].textContent || '').trim() !== '') return true;
        }
        return false;
      };
      var members = [];
      var capNodes = [].slice.call(capEl.querySelectorAll('*'));
      for (var ci = 0; ci < capNodes.length; ci++) {
        var e = capNodes[ci];
        if (!cvis(e)) continue;
        var r = e.getBoundingClientRect();
        if (r.width <= 4 || r.height <= 4) continue;
        var t = (e.textContent || '').trim();
        if (!(isControl(e) || hasOwnText(e))) continue;
        if (t === '' && !isControl(e)) continue;
        if (innerControl(e) || innerTexted(e)) continue;
        members.push({ tag: e.tagName.toLowerCase(), cls: String(e.className || '').split(' ')[0],
                       txt: t.slice(0, 18), x: Math.round(r.left * 10) / 10, y: Math.round(r.top * 10) / 10,
                       r: Math.round(r.right * 10) / 10, b: Math.round(r.bottom * 10) / 10 });
      }
      var overlaps = [];
      for (var mi = 0; mi < members.length; mi++) {
        for (var mj = mi + 1; mj < members.length; mj++) {
          var A = members[mi], B = members[mj];
          var ox = Math.min(A.r, B.r) - Math.max(A.x, B.x);
          var oy = Math.min(A.b, B.b) - Math.max(A.y, B.y);
          if (ox > 0.5 && oy > 0.5) {
            overlaps.push({ a: A.tag + '.' + A.cls + '[' + A.txt + ']',
                            b: B.tag + '.' + B.cls + '[' + B.txt + ']',
                            ox: Math.round(ox * 10) / 10, oy: Math.round(oy * 10) / 10 });
          }
        }
      }
      /* 相邻成员的**水平间隙** —— ⚠ 只在**同一行**的两个成员之间量。
         这一行是 flex-wrap 的：窄档下成员会折到下一行，此时"按左缘排序后相邻"的两件东西
         根本不是同一行的邻居，量出来的负数是**折行**而不是压字
         （本批实测：520 档一跳出来几十条假阳性 —— 上一版就是这么假红的）。
         同一行的判据 = 垂直方向重叠 > 两者较小高度的 50%。 */
      var sameRow = function (p, q2) {
        var ov = Math.min(p.b, q2.b) - Math.max(p.y, q2.y);
        var minH = Math.min(p.b - p.y, q2.b - q2.y);
        return minH > 0 && ov > minH * 0.5;
      };
      var rowsMap = [];
      for (var ri = 0; ri < members.length; ri++) {
        var placed = false;
        for (var rj = 0; rj < rowsMap.length; rj++) {
          if (sameRow(rowsMap[rj][0], members[ri])) { rowsMap[rj].push(members[ri]); placed = true; break; }
        }
        if (!placed) rowsMap.push([members[ri]]);
      }
      /* ⚠⚠ **压字要查"同一个盒子里面两件东西贴在一起"**（2026-09-23 接手批，连踩两轮才立住）：
         业主报障的那一处形态是 —— .ks-lhead-name 那个 span **里面**装着"导出效力总览 按钮 +
         知识库 这段纯文字"，两者水平间隙实测 **0px**（贴成一个词）。
         ✗ 只查"成员之间"：那个 span 自己就是一件成员，成员间隙照样 8px ⇒ **一条都不报**；
         ✗ 只查"成员内部"：那个 span 因为**装得下别的控件**被判成"不是叶子"⇒ 它根本不进
           成员表 ⇒ 里面那一层**没人查**（本批两次变异实测都是 exit 0，就是这么漏的）。
         ✓ 正解 = **把这一行里所有"看得见的东西"摊平成一个列表**（叶元素 + 纯文字节点 Range 盒子），
           **再剔除"完全装在某一件东西盒子里"的那些项**（它们只是别人的内容，不是独立成员；
           不剔就会把"计数 span 在自己盒子里"误报成压字），剩下的按**同一行**两两量水平间隙。
         这样既量得到成员之间、也量得到成员**内部**，而且**不重复计数**。
         判据口径与原来一致：同一张 gaps 表、同一个下限 LISTCAP_MIN_GAP。既有的
         "成员两两边框盒重叠"那张表（overlaps）照旧只按成员算 —— 它对"真叠上"那一类仍然有效。 */
      var pieceBox = function (tag, cls, txt, rc) {
        return { tag: tag, cls: cls, txt: txt,
                 x: Math.round(rc.left * 10) / 10, y: Math.round(rc.top * 10) / 10,
                 r: Math.round(rc.right * 10) / 10, b: Math.round(rc.bottom * 10) / 10 };
      };
      /* ⚠⚠ **纯文字节点的 Range 盒子必须"按最近的可裁剪祖先夹一下"**（2026-09-23 实测）：
         Range 量的是**排版几何**，不认 overflow:hidden。ks-ask-chip-name 那种
         overflow:hidden;text-overflow:ellipsis 的格子里，文字**排**得比格子宽、只是被裁掉了，
         Range 却把整段文字的真实宽度报出来 ⇒ 它"伸进"了右边那个兄弟 span 的地盘，
         于是量出一个 **-60px 的假压字**（本批真机实测：kb-ask@520 就是这么假红的）。
         修法：从文字节点往上找**最近一个** overflow 不是 visible 的祖先，把盒子夹到它的
         内容盒里 —— 夹完报的就是"用户**看得见**的那一段"，这才是"压字"该判的东西。 */
      var clipRectOf = function (node) {
        var cur = node.parentElement;
        while (cur && cur !== capEl) {
          var cs2 = getComputedStyle(cur);
          if (cs2.overflow !== 'visible' || cs2.overflowX !== 'visible' || cs2.overflowY !== 'visible') {
            var cr = cur.getBoundingClientRect();
            var pl = parseFloat(cs2.paddingLeft); if (!isFinite(pl)) pl = 0;
            var prr = parseFloat(cs2.paddingRight); if (!isFinite(prr)) prr = 0;
            var pt = parseFloat(cs2.paddingTop); if (!isFinite(pt)) pt = 0;
            var pb = parseFloat(cs2.paddingBottom); if (!isFinite(pb)) pb = 0;
            return { l: cr.left + pl, r: cr.right - prr, t: cr.top + pt, b: cr.bottom - pb };
          }
          cur = cur.parentElement;
        }
        return null;
      };
      var pieces = [];
      /* ① 叶元素（控件 / 自己带文字的元素；装得下别的控件或带字 span 的不算叶子）。 */
      for (var pi = 0; pi < capNodes.length; pi++) {
        var pe = capNodes[pi];
        if (!cvis(pe)) continue;
        if (!(isControl(pe) || hasOwnText(pe))) continue;
        if (innerControl(pe) || innerTexted(pe)) continue;
        var pr = pe.getBoundingClientRect();
        if (pr.width <= 4 || pr.height <= 4) continue;
        pieces.push(pieceBox(pe.tagName.toLowerCase(), String(pe.className || '').split(' ')[0],
          (pe.textContent || '').trim().slice(0, 18), pr));
      }
      /* ② 纯文字节点（没有元素盒子）：用 Range 拿真盒子 —— "按钮压着四个字"里的那四个字
            就是这一种，漏了它这一条就形同虚设。 */
      var textNodes = [].slice.call(capEl.querySelectorAll('*'));
      textNodes.unshift(capEl);
      for (var ti2 = 0; ti2 < textNodes.length; ti2++) {
        var hostN = textNodes[ti2];
        var tns = [].slice.call(hostN.childNodes);
        for (var tj = 0; tj < tns.length; tj++) {
          if (tns[tj].nodeType !== 3 || (tns[tj].textContent || '').trim() === '') continue;
          var rgn = document.createRange();
          rgn.selectNodeContents(tns[tj]);
          var trn = rgn.getBoundingClientRect();
          if (trn.width <= 1 || trn.height <= 1) continue;
          /* 夹到最近的可裁剪祖先的内容盒里（见上面 clipRectOf 那段：不夹就会把"被省略号
             裁掉的那一段"也算进来，量出假压字）。 */
          var clip = clipRectOf(tns[tj]);
          var cxL = trn.left, cxR = trn.right, cyT = trn.top, cyB = trn.bottom;
          if (clip) {
            cxL = Math.max(cxL, clip.l); cxR = Math.min(cxR, clip.r);
            cyT = Math.max(cyT, clip.t); cyB = Math.min(cyB, clip.b);
          }
          if (cxR - cxL <= 1 || cyB - cyT <= 1) continue;
          pieces.push(pieceBox('#text', '', (tns[tj].textContent || '').trim().slice(0, 18),
            { left: cxL, right: cxR, top: cyT, bottom: cyB }));
        }
      }
      /* ⚠ **纯文字节点与"它自己那个元素"盒子**完全重合时要去掉一份**（2026-09-23 实测）：
         例如 .ks-kb-hint 那种 span —— 它里面只有一个文字节点，两者的盒子**逐字相同**，
         留着两份就会量出一个 0px 的"假压字"。判据：文字项的盒子与**某个元素项**的盒子
         （四边各差 <= 2px）相同 ⇒ 那一项是人家自己的内容，不是独立成员。 */
      var isDupOfElement = function (t) {
        for (var di = 0; di < pieces.length; di++) {
          var D = pieces[di];
          if (D.tag === '#text') continue;
          if (Math.abs(D.x - t.x) <= 2 && Math.abs(D.r - t.r) <= 2
            && Math.abs(D.y - t.y) <= 2 && Math.abs(D.b - t.b) <= 2) return true;
        }
        return false;
      };
      pieces = pieces.filter(function (p) { return !(p.tag === '#text' && isDupOfElement(p)); });
      /* 剔除"完全装在某一件**更大**的东西盒子里"的项（留 2px 容差）——
         判据：存在另一项 P，P 的盒子在两个方向上都不小于它、且大得不止一点点。 */
      var kept = [];
      for (var ki2 = 0; ki2 < pieces.length; ki2++) {
        var A2 = pieces[ki2];
        var contained = false;
        for (var kj = 0; kj < pieces.length; kj++) {
          if (kj === ki2) continue;
          var B2 = pieces[kj];
          var bWider = (B2.x <= A2.x + 2) && (B2.r >= A2.r - 2);
          var bTaller = (B2.y <= A2.y + 2) && (B2.b >= A2.b - 2);
          var strictlyBigger = ((B2.r - B2.x) > (A2.r - A2.x) + 2) || ((B2.b - B2.y) > (A2.b - A2.y) + 2);
          if (bWider && bTaller && strictlyBigger) { contained = true; break; }
        }
        if (!contained) kept.push(A2);
      }
      /* 同一行两两量水平间隙（只在"垂直方向真的重叠"的两件之间量 —— 折行不算压字）。 */
      var prows = [];
      for (var qi = 0; qi < kept.length; qi++) {
        var qPlaced = false;
        for (var qj = 0; qj < prows.length; qj++) {
          if (sameRow(prows[qj][0], kept[qi])) { prows[qj].push(kept[qi]); qPlaced = true; break; }
        }
        if (!qPlaced) prows.push([kept[qi]]);
      }
      var gaps = [];
      for (var qk = 0; qk < prows.length; qk++) {
        var prow = prows[qk].slice().sort(function (p, q5) { return p.x - q5.x; });
        for (var qg = 0; qg + 1 < prow.length; qg++) {
          gaps.push({ left: prow[qg].tag + '.' + prow[qg].cls + '[' + prow[qg].txt + ']',
                      right: prow[qg + 1].tag + '.' + prow[qg + 1].cls + '[' + prow[qg + 1].txt + ']',
                      gap: Math.round((prow[qg + 1].x - prow[qg].r) * 10) / 10 });
        }
      }
      out['#listcap'] = { n: members.length, x: Math.round(capEl.getBoundingClientRect().left),
                          y: Math.round(capEl.getBoundingClientRect().top),
                          w: Math.round(capEl.getBoundingClientRect().width),
                          h: Math.round(capEl.getBoundingClientRect().height),
                          fs: '', lh: '', pad: '', gap: '', radius: '',
                          overlaps: overlaps, gaps: gaps,
                          members: members.map(function (m) {
                            return m.tag + '.' + m.cls + '[' + m.txt + ']@' + String(m.x) + '-' + String(m.r); }) };
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


/* ══════════ `#kbtree` / `#levelrows` 的**真断言**（2026-09-21 第 3 步；取代 `cardsCheck`） ══════════
 * 判据与来历见下面那一大段；这里只留一句**旧口径的留痕**（不许删）：
 *   上一版本段判的是"卡片带里 5 张卡的宽/高**全等**"（`#kbcards` + `cardsCheck`），
 *   复核 `verify-freeze-5h` 曾证明"只报告不断言"会让三张卡三种宽也全绿 —— 那个教训
 *   （**报告值必须有断言兜着**）原样搬到了新判据上：`levelCheck` 同样是"量不到就红"。 */
/* **为什么换**：上一版这条断言判的是"卡片带里每一张卡的宽/高**全等**"
 *   （业主点名的"知识库卡片尺寸统一"）。**卡片带已被业主删掉**（"原来的大卡片去掉"，
 *   KB-FOLDER-PLAN 第 3 步）⇒ 那条断言**没有主体**了，继续留着只会永远 skip。
 *   ⇒ 取代它的不是"删掉就算"，而是**判新的真实几何**（同一条纪律：真 Chrome 的
 *   `getBoundingClientRect` + 量不到就红 + 诊断逐条打印）：
 *     ① **左列与右栏并排**：`.ks-kb-tree` 的右缘 ≤ `.ks-main` 的左缘 + 1px。
 *        这是 520 档（宿主侧栏默认宽）的硬约束 —— 目录列 168 + gap 8 + 主栏 min 260 = 436 < 488
 *        （页面根宽 − 2×16 留边）。**变异**：给 `.ks-kb-tree` 加 `flex-basis:100%` ⇒ 换行 ⇒ 左缘
 *        跑到右栏下面 ⇒ 这一条**红**（下面那段注释记着实测）。
 *     ② **同一级里两类行的行高逐字相同**（目录行 vs 文件行，±1px 容差）：这是"目录层与文件列表
 *        同构"这句承诺的**可量形态**（都吃 `--ks-row-h-list`）。只有在**两种行同时在 DOM 里**的
 *        那一级（stub 的「法律法规」）才量得动，所以 `kb-level` 场景是它的取证场景。
 *     ③ 量不到 / 取不到值 ⇒ **红**（"没验到"不能渲染成"通过"）。
 * 适用面：`page === 'kb'` 时**必须**判到（kb 页一定有左列+右栏）；其余页面**明说没判**（skipReason）。
 * ⚠ 「真 Chrome」是**约定叫法**：本脚本按 `BROWSERS` 顺序找浏览器，**本机实际命中的是
 *   `msedge.exe`**（Edge/Chromium 内核）。措辞不精确，结论不变（同一内核、同一像素口径）。 */
const kbt = measured['#kbtree']
const lvr = measured['#levelrows']
const levelProblems = []
let levelSkipReason = null
/** 判据②（两层行高一致）这一跑**到底判没判**（两种行不同时在场 ⇒ false）。巡查脚本据此做覆盖面判据。 */
let rowHeightJudged = false
if (page !== 'kb') {
  levelSkipReason = `本页不是知识库页（page=${page}），左列/行高几何不适用`
} else if (navPage !== 'manage') {
  /* ⚠⚠ **2026-09-23（接手批）**：这条判据的适用面从"`page === 'kb'`"收窄成
     "**知识库管理那一个面**"（`page=kb` 且 `params.page='manage'`）。
     为什么必须收窄（而不是把新面也硬判）：这四个面共用同一个 `KsKnowledgePage` 外壳
     （同一个组件、同一个标签条），但**只有 manage 面有左列目录树 + 右栏**
     （`.ks-kb-tree` / `.ks-main`）—— 渠道库/办事台/备料三个面**结构上就没有它们**。
     判据**强度没降**：管理面照样"量不到就红"（上面那条 `kbt === undefined` 分支没动），
     非管理面**明说没判**（skipReason 带上面名，不静默通过）。
     ⚠ 这条收窄**只对新增的 `--nav-page` 场景生效**：不给开关时 `navPage` 恒为 'manage'
       ⇒ 原有全部场景走的分支**与改前逐字相同**（判据只增不减）。 */
  levelSkipReason = `这一跑是知识库页的**另一个面**（params.page=${navPage}）：`
    + '左列目录树/两层行高只存在于 manage 面，本面不适用'
} else if (kbt === undefined) {
  levelProblems.push('这一跑**量不到 `#kbtree`**（左列目录树或右栏不在 DOM 里）—— 量不到就不算验过')
} else {
  const treeRight = Number(kbt.x)
  const mainLeft = Number(kbt.y)
  if (!Number.isFinite(treeRight) || !Number.isFinite(mainLeft) || Number(kbt.w) <= 0 || Number(kbt.h) <= 0) {
    levelProblems.push(`左列/右栏的几何量不到或为 0：左列宽 ${JSON.stringify(kbt.w)}、右栏宽 ${JSON.stringify(kbt.h)}、`
      + `左列右缘 ${JSON.stringify(kbt.x)}、右栏左缘 ${JSON.stringify(kbt.y)}`)
  } else if (treeRight > mainLeft + 1) {
    levelProblems.push(`**左列目录树与右栏没有并排**（换行堆叠了）：左列右缘 ${String(treeRight)}px > `
      + `右栏左缘 ${String(mainLeft)}px + 1（左列宽 ${String(kbt.w)}、右栏宽 ${String(kbt.h)}）`
      + ' —— 两列必须在同一行里；换行说明左列宽/主栏最小宽把这一行撑破了（520 档的硬约束）')
  }
  if (lvr === undefined) {
    /* ⚠ **"两种行不同时在场"不算失败**（诚实边界）：只有**同时**有下级目录与文件的那些层级才量得动
       "两层行高一致"（stub 里的「法律法规」）。一个只有目录（最外层）或只有文件（最深处）的层级
       **天然没有比较对象** ⇒ 这里不报错，而是把 `rowHeightJudged=false` 报出去，
       由**巡查脚本**（`smoke-kb-pad-pixels.mjs`）用一条**覆盖面**判据保证"至少要有一跑真的判过它"
       （与能力页 capCardsCheck 的"多卡排"那条同一种纪律：声明了不等于跑过）。 */
    rowHeightJudged = false
  } else {
    const dh = Number(lvr.w)
    const fh = Number(lvr.h)
    if (!Number.isFinite(dh) || !Number.isFinite(fh) || dh <= 0 || fh <= 0) {
      levelProblems.push(`两类行的行高量不到或为 0：目录行 ${JSON.stringify(lvr.w)} / 文件行 ${JSON.stringify(lvr.h)}`)
    } else if (Math.abs(dh - fh) > 1) {
      levelProblems.push(`**目录行与文件行的行高不同**：目录行 ${String(dh)}px vs 文件行 ${String(fh)}px`
        + '（容差 1px）—— 两层必须吃同一个行高 token（--ks-row-h-list），'
        + '否则"目录层与文件列表同构"就成了空话（真机上一眼能看出两层行距不一样）')
    } else {
      rowHeightJudged = true
    }
  }
}
const levelCheck = {
  checked: levelProblems.length === 0 && levelSkipReason === null,
  skipReason: levelSkipReason,
  problems: levelProblems,
  rowHeightJudged,
  treeRight: kbt?.x ?? null,
  mainLeft: kbt?.y ?? null,
  treeWidth: kbt?.w ?? null,
  mainWidth: kbt?.h ?? null,
  dirRowH: lvr?.w ?? null,
  fileRowH: lvr?.h ?? null,
  dirRows: lvr?.x ?? null,
  fileRows: lvr?.y ?? null,
}

/* ══════════ `#capcards` 的**真断言**（2026-09-21；能力页：**等宽** + **同排等高**） ══════════
 * 判据的**唯一所有者**是 plugin/scripts/lib/cap-cards-check.mjs（口径、为何单开模块都写在那一处）。
 * 这里只做一件事：把探针量到的 `#capcards` 交给它，并把结论带进 stdout 的 JSON 与 stderr 自检。
 * 三条来历（不许删）：
 *   ① 上一轮**先量后判**的实测：8 张 .ks-cap-card 宽全等（900 档 268 / 1300 档 236）、高按组三档
 *      （136/201/261），同排等高由 grid align-items:stretch 保证 ⇒ 页面级"尺寸统一"**不是意图**
 *      （业主那句"统一尺寸"指的是**知识库卡片带**，cardsCheck 已钉那一处）⇒ 本批**不判"统一"**；
 *   ② 父代理 2026-09-21 的裁定：只断 ① 等宽 ② 同排等高 ③ 量到 0 张即红 ④ 排数 >= 2，
 *      **不许**把"8 张"钉成冻结常量（能力卡会随功能增加，钉死会假红）；
 *   ③ 单开 lib 模块的理由：像素判据的**变异自证**必须在 %TEMP% 的 fixture 副本上跑，
 *      而那份副本要经过**同一份**判据 —— 抄一份就是本仓最恨的"两份各自漂移"。
 * 变异实测（本批，结果写进 docs/UI-BASELINE.md 那一节）：
 *   ① fixture 副本里给某张卡加宽度覆盖 ⇒ **等宽**红；把容器改成 align-items:start ⇒ **同排等高**红；
 *   ② 探针的 selector 在副本里改坏 ⇒ 红在**量到 0 张**上。 */
const capCardsCheck = checkCapCards(measured, page)
const capCardsProblems = capCardsCheck.problems
const capCardsSkipReason = capCardsCheck.skipReason

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
const PAD_SUBJECTS_ALL = ['.ks-kb', '.ks-ing', '.ks-mat', '.ks-kb-tree', '.ks-list',
  '.ks-dirs', '.ks-page-head', '.ks-kb-row', '.ks-empty-card', '.ks-batch']
/** 键 = `${page}|${interacts.join('+')}`（与 `--page`/`--interact` 同一口径）。值 = 这一跑**必须量到**的选择器。
 *  ⚠⚠ **2026-09-21（第 3 步）就地更新**：`.ks-kbband`（卡片带）与 `.ks-batch`（批量条）**已删**
 *    ⇒ 从适用面里去掉；新增 `.ks-kb-tree`（左列目录树，必须不贴边）。
 *    ⚠ 三处副本同批一起改：docs/UI-BASELINE.md 第二节的适用面 / 本文件的 `PAD_SUBJECTS_ALL` 与
 *      `PAD_REQUIRED` / `smoke-kb-pad-pixels.mjs` 的 `SPEC_SUBJECTS`
 *      （前四处互相绑着棘轮，只改一两处必红）。 */
const PAD_REQUIRED = {
  'kb|': ['.ks-kb', '.ks-kb-tree', '.ks-dirs', '.ks-page-head', '.ks-kb-row'],
  /* 这些 kb 组合都在**目录层**（.ks-list-dirs 那个容器同时挂着 .ks-dirs ⇒ 两个类都在这一集里）：
     kb-crumb（面包屑逐级可点的路径）/ kb-level（1 目录 + 1 文件的同构取证）/ kb-upload（进「标准」那一级）。
     ⚠ **只声明 `smoke-kb-pad-pixels.mjs` 的矩阵真的会跑的那些组合** —— 那条棘轮要求
       "声明了就必须有人跑"（`kb-back` / `kb-search` / `kb-search-dirs-empty` 只在 jsdom 冒烟里判，
       矩阵不跑它们 ⇒ 不能在这里声明，否则会红在"声明了但没人跑"上）。 */
  'kb|kb-crumb': ['.ks-kb', '.ks-kb-tree', '.ks-dirs', '.ks-page-head', '.ks-kb-row'],
  'kb|kb-level': ['.ks-kb', '.ks-kb-tree', '.ks-dirs', '.ks-list', '.ks-page-head', '.ks-kb-row'],
  /* ⚠ 2026-09-21 第 5 步复核 R3：这一跑**同时**点开「逐篇看」⇒ 复活的入库面板（`.ks-ing`）必须
     真的挂在 DOM 里、并且在真 Chrome 里量得到高度（声明了就必须看得见，见 ksPadCheck 那条新断言）。 */
  'kb|kb-upload': ['.ks-kb', '.ks-kb-tree', '.ks-dirs', '.ks-page-head', '.ks-kb-row', '.ks-ing'],
  'kb|kb-page': ['.ks-kb', '.ks-kb-tree', '.ks-list', '.ks-page-head', '.ks-kb-row'],
  'kb|kb-files': ['.ks-kb', '.ks-kb-tree', '.ks-list', '.ks-page-head', '.ks-kb-row'],
  /* 空目录那一级：没有目录层也没有文件表 ⇒ 主体是空态卡（+ 左列与顶上那一行）。 */
  'kb|kb-empty': ['.ks-kb', '.ks-kb-tree', '.ks-page-head', '.ks-kb-row', '.ks-empty-card'],
  /* 「待分类」层（第 4 步）：导入面板入口 + 待分类列表；**没勾选时没有批量条** ⇒ 不声明 .ks-batch
     （声明了就必须量到，而这一跑确实没有它）。 */
  'kb|kb-inbox': ['.ks-kb', '.ks-kb-tree', '.ks-page-head', '.ks-kb-row'],
  /* 第 6 步：这一跑点了「在此范围内提问」⇒ 范围 chip 与提问面板必须真的渲染（高度 > 0）。
     ⚠ 只声明**规范适用面里已有的**选择器（`.ks-ask*` 由 `askCheck` 在真 Chrome 里单独量高度与
       右缘溢出）—— 往 PAD_REQUIRED 里加新选择器会连带要求改规范第二节的适用面清单
       （四处棘轮），而这一批不需要把它算作"留边适用面"。 */
  'kb|kb-ask': ['.ks-kb', '.ks-kb-tree', '.ks-list', '.ks-page-head', '.ks-kb-row'],
  /* ⚠ **2026-09-22（业主点菜单文案那一轮）**：`kb-filemenu` / `kb-dirmenu` 把**文件行 / 目录行**的
     ⋮ 菜单在真浏览器里打开、逐条判渲染出来的文案（业主定的那一套词）+ 「移出」不是删除那句 title。
     ⚠ 声明了就**必须有人跑**（pad-pixels 的棘轮）⇒ 这两组同时进了那个脚本的 `MATRIX`
       与 `EXPECTED_RUNS`（否则会红在"声明了但没人跑"上）。 */
  'kb|kb-filemenu': ['.ks-kb', '.ks-kb-tree', '.ks-list', '.ks-page-head', '.ks-kb-row'],
  'kb|kb-dirmenu': ['.ks-kb', '.ks-kb-tree', '.ks-dirs', '.ks-page-head', '.ks-kb-row'],
  /* 勾了两篇 ⇒ 悬浮批量条在场，**必须不贴边**（它是第 4 步做回来的真批量条）。 */
  'kb|kb-inbox-picked': ['.ks-kb', '.ks-kb-tree', '.ks-page-head', '.ks-kb-row', '.ks-batch'],
  /* 第 5 步：目录层勾两个 + 删目录确认面板（.ks-act-del）在场。批量条与目录层同屏 ⇒ 两个都得判。 */
  'kb|kb-dir-manage': ['.ks-kb', '.ks-kb-tree', '.ks-dirs', '.ks-batch',
                       '.ks-page-head', '.ks-kb-row'],
  /* ⚠ 2026-09-22（办事台 v3）：`.ks-kb-row`（页内按钮行）**从这一跑的声明里去掉** ——
     卡片式作废后，菜单态**没有**"页内按钮行"这个构件（动作在专门页面里，那里已挂真 .ks-kb-row
     class，将来跑 office-page 组合时可声明它）。判据给的合法出路即此：
     "改回类名，或按设计把它从适用面里去掉"——.ks-kb-row 的**留边保护不丢**（kb 各组合照旧声明）。 */
  'capabilities|': ['.ks-kb', '.ks-page-head'],
  'ingest|ingest-batch': ['.ks-ing'],
  'materials|': ['.ks-mat'],
  /* ⚠⚠ **2026-09-23（接手批）**：`--nav-page` 开出来的**另外三个面**（同一个 KsKnowledgePage
     外壳、`params.page` 不同）。它们的元素集**比 manage 面窄**，所以必须**逐条显式声明** ——
     这正是本表"不同面本来就有不同元素集，不许要求全都有（假红）、也不许找到就判（假绿）"的口径。
     ⚠ 它们**都不含 `.ks-dirs`**：那三个面结构上没有左列目录树/目录层 ⇒ 目录层列几何与表头格
       两条判据对它们**不适用**（走 skipReason，不静默通过）。
     ⚠ 键里带 `nav-<面>`：键的唯一所有者是 `faceComboKey`（见下），它**只有**在
       `--nav-page` 被显式给出时才带这一段 ⇒ `manage` 面（含全部原有场景）走的键
       **与改前逐字相同**（`kb|` 等），本表原有的那些条目一个都不用动。
     ⚠ `DIR_LAYER_COMBOS`（冻结清单）**没有**跟着改：它的三个守卫都只在 `startsWith('kb|')`
       的条目上做双向核对，而这三条**都不含 .ks-dirs** ⇒ 不进那份清单（也不会被守卫判成
       "声明了目录层却没入清单"）。 */
  'kb|nav-channels|': ['.ks-kb', '.ks-page-head'],
  'kb|nav-capabilities|': ['.ks-kb', '.ks-page-head'],
  'kb|nav-materials|': ['.ks-kb', '.ks-page-head'],
}
/**
 * **组合键的唯一所有者**（`PAD_REQUIRED` / `DIR_LAYER_COMBOS` / 各处 skipReason 都读它）。
 *
 * ⚠⚠ **2026-09-23（接手批）**：`--nav-page` **显式给出**时，键里带一段 `nav-<面>` ——
 *   不带的话，`--nav-page channels` 这一跑会算出与 manage 面**逐字相同**的键 `kb|`，
 *   于是套用 manage 面的元素集（含 `.ks-dirs`）⇒ 三个新面**全被假红**（不是回归，是面本来窄）。
 * ⚠ 不给 `--nav-page` 时（`navPage === 'manage'`）键 = 老写法 `${page}|${interacts}`（见下面那行）
 *   —— **逐字相同** ⇒ 原有全部场景解析到的规则与改前**完全一样**（"判据只增不减"的兑现方式：
 *   新面走新键、老面走老键，没有一条老断言被改写或放宽）。 */
const faceComboKey = navPageRaw === ''
  ? `${page}|${interacts.join('+')}`
  : `${page}|nav-${navPage}|${interacts.join('+')}`
const padComboKey = faceComboKey
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
      + `[${uncovered.join(' ')}] —— 给它们各补一组声明；真要从规范里去掉，必须**同时改**：`
      + '规范第二节 / 本文件 PAD_SUBJECTS_ALL / 本文件 PAD_REQUIRED / smoke-kb-pad-pixels 的 SPEC_SUBJECTS'
      + '（前四者已互相绑成棘轮）；另有三处散文/间接副本（jsdom 的 PAD_SUBJECTS、注入的 padSel、'
      + '第六节 5j① 表格）要手动同步')
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
} else if (ksp.pageWrapped !== 1) {
  /* ⚠ 原来的写法是 `ksp.pageN !== 1`（"恰好 1 个 .ks-page"）。第 5 步复核 R3 之后改成
     "**页面根必须被第一个 `.ks-page` 直接包着**"：复活的入库预览面板自带一层 `.ks-page`
     （container-type），面板一打开就有 2 个 —— 那会把整条 ksPad 检查 skip 掉（于是"面板看不看得见"
     根本没人判）。判据强度没降：页面根没被包住、或第一个 `.ks-page` 不是它的父级 ⇒ 仍然红。 */
  ksPadSkipReason = `.ks-page 容器实测 ${String(ksp.pageN)} 个、这一跑的页面根被第一个它包住=`
    + `${String(ksp.pageWrapped === 1)} —— 页面根没被包住（或 .ks-page 不是它的父级），这一跑不判`
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
        continue
      }
      /* ⚠⚠ **2026-09-21 第 5 步复核 R3（真缺陷，已修）**：存在 ≠ 看得见。
         复核的变异 V6（把 `{upPreview ? (` 改成 `{false ? (`）让复活的入库预览面板**永远不挂载** ——
         而四张清单只钉了"bundle 里有『逐篇看』这个字符串"⇒ 全绿。
         现在对**每一个已声明的主体**再加一条：实渲高度必须 > 0（`display:none` / 空盒子的高度都是 0）——
         这就是"真浏览器里量得到"的那一半，配 jsdom 侧的结构判据（K8）一起用。 */
      if (!Number.isFinite(it.h) || it.h <= 0) {
        ksPadProblems.push(`**规范点名的适用面 ${sel} 在真 Chrome 里高度 = ${JSON.stringify(it.h)}px`
          + '（display:none / 没挂载 / 空盒子都会这样）—— **存在不等于看得见**，'
          + '声明了它就必须真的渲染出高度；要么让它可见，要么按设计把它从这一跑的 PAD_REQUIRED 里去掉')
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
  /* ⚠ **批量条"不许被挤成两行"那条已随批量条删除**（2026-09-21 第 3 步）：
     它的主体 `.ks-batch` 不在了（"批量选择动作不在本批"）⇒ 这条判据没有对象。
     留痕：它原本是 5j 页面留边的连带修复（留边吃掉可用宽 ⇒ 条子折行 40→72px），
     现在页面上**没有横排条子**了，同类风险转移到 `.ks-kb-row`（顶上那一排：返回 + 路径 +
     上传 + 刷新）—— 它在窄档会不会折行由 `PAD_REQUIRED` 的存在性 + 截图人眼确认，
     **没有**加像素断言（不凭空造一条没有来历的判据）。 */
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
  /* ⚠⚠ **5j-补×4（2026-09-20，复核 `verify-freeze-5jbbb` 打回 G/C）：把"声明集合本身"报出去。**
     复核实测：`smoke-kb-pad-pixels.mjs` 原来用**正则读本文件源码**去拿这两份表 ⇒ ① 键写成**双引号**
     就漏读 ⇒ "声明了但没人跑"的洞原样复现（exit 0、零诊断）；② 冒号换行 ⇒ 静默少读一个键；
     ③ 在表里写一句含 `'x':` 的**合法注释** ⇒ 假红（注释被当成声明）。
     ⇒ 现在从**活的 JS 对象**自报（`Object.keys(PAD_REQUIRED)` + `PAD_SUBJECTS_ALL` 本体）：
     引号风格、换行、注释都影响不了它；巡查那边读**实测 JSON**，正则那一套（连同它的假红面）整个删掉。 */
  allSubjects: PAD_SUBJECTS_ALL,
  declaredCombos: Object.keys(PAD_REQUIRED),
  missingSubjects: (ksp?.items ?? []).filter((it) => it.missing === true).map((it) => it.sel),
  items: ksp?.items ?? null,
}

/* ══════════ `#dircols` 的**真断言**（2026-09-21；复核 `verify-freeze-dirlist` 的变异 M5） ══════════
 * 打回的是什么：复核把目录层的 `--ks-cols` 换成**文件层那 5 列** ⇒ 本脚本的 `#cols` 自检**照样通过**
 * （它只比"表头 == 行"，两边一起变自然相等），而真机上是**首列 344→88px + 168px 死白** ——
 * "目录层是独立的一套列"这件事在真 Chrome 里**没有任何判据**。
 * ⇒ 这条量**目录层**自己在真浏览器里解析出来的轨道：① 轨道数必须 = 3（目录 / 篇数 / 进入提示，
 *   与 `DIR_COLUMNS` 同数）；② **轨道和 + gap×(n−1) 必须铺满容器内容宽**（±1px）—— 死白就红。
 * ⚠ 只判"能不能铺满"不够：把三轨写成 `1fr 1fr 1fr` 也铺满 —— 而它**不是**我们的模板
 *   （下面那条固定轨判据才拦得住它；这句原写"与①合判"，是**假话**，复核 B③ 已证伪）。
 * ⚠ 适用面：**冻结清单 `DIR_LAYER_COMBOS` 里的组合**必须量到 `#dircols`（并同时要求它们的
 *   `PAD_REQUIRED` 声明里有 `.ks-dirs`）—— 没在清单里才**明说没判**。
 *   ⚠ 第二轮复核（C④c）证伪过上一版：只按 `PAD_REQUIRED` 判"要不要量到" ⇒ **同时改小声明表 +
 *   让探针不产出**就能回到静默 skip + exit 0（并集棘轮不响）。所以"哪些组合必须有目录层"必须是
 *   **本文件的冻结清单**，不是被声明的那张表。 */
const DIR_COLS_EXPECTED = 4
/* ⚠⚠ **2026-09-21（第 5 步）就地更新这四个冻结常数 + 新增第五条判据**：
 *   目录层加了**勾选列**（`dpick`），末列从"只展示的进入箭头"（16px `dgo`）换成
 *   **行尾 ⋮ 菜单**（28px `dmore`：改名/新建下级/挪/复制/删）⇒ 轨道 3 → 4、固定轨多一条。
 *   ⚠ **这四个数不许从被测物反推**（第二轮复核 C④a 证伪过"从 ksGuideStyles 抠 token"那种写法：
 *     改 token 本身两边一起变、全绿）。现在的规矩（同 `PAGE_PAD_*`）：
 *       ① 下面是**规范锚**（冻结）；
 *       ② 同时从 `ksGuideStyles.ts` 抠出 token 声明、从 `KsKnowledgePage.tsx` 抠出 `DIR_COLUMNS`
 *          的条数，**三方必须一致**（谁单方面改就红）；
 *       ③ 真 Chrome 量到的轨道/表头格数必须等于这些常数。
 *   ⚠ 顺序也钉住（px[0]=勾选 / px[2]=篇数 / px[3]=⋮）—— 顺序换了说明模板被人重排了。 */
const DIR_COL_DPICK_EXPECTED = 32
const DIR_COL_DCOUNT_EXPECTED = 64
const DIR_COL_DMORE_EXPECTED = 28
/* 目录层表头格数：与轨道数**同源**（都来自页面那份 `DIR_COLUMNS`）⇒ 用同一个冻结常数。
   ⚠ 这两个数曾经是**各写一份**的（3 / 3），2026-09-21 第 5 步合并成一处 —— 那次改动正是因为
     复核 §5 指出 `dirHeadCheck` **没有**"冻结常数 ↔ 源码声明"的交叉校验（删掉清单里一条就能
     静默收窄覆盖面）。现在两条都读同一个 `dirColsFromPage`。 */
const DIR_HEAD_CELLS_EXPECTED = DIR_COLS_EXPECTED
/** **冻结**：哪些组合必须看得到目录层（+ 它们的 `PAD_REQUIRED` 必须声明 `.ks-dirs`）。
 *  ⚠ 这份清单**只列矩阵（`smoke-kb-pad-pixels.mjs` 的 MATRIX）真的会跑的组合** ——
 *    列了没人跑的组合会让 `dirColsPresenceRequired` 在手动跑那些场景时红（且没有意义）。
 *  ⚠ 第 5 步补了三条守卫（复核 §5 点名）：① **非空**（清空这份清单 = 所有目录层判据静默跳过）；
 *    ② 清单里的每个组合都必须在 `PAD_REQUIRED` 里声明 `.ks-dirs`（下详）；
 *    ③ **反向**：凡是在 `PAD_REQUIRED` 里声明了 `.ks-dirs` 的 kb 组合，都必须在这份清单里
 *    （否则"新加一个目录层组合但不入清单"就是这么绕过去的）。 */
const DIR_LAYER_COMBOS = ['kb|', 'kb|kb-crumb', 'kb|kb-level', 'kb|kb-upload', 'kb|kb-dir-manage',
  /* 2026-09-22：目录行的 ⋮ 菜单（`kb-dirmenu`）—— 它停在最外层，有目录层 ⇒ 入清单
     （否则上面第 ③ 条守卫会红："声明了 .ks-dirs 却不在清单里"）。
     它同时在 `smoke-kb-pad-pixels.mjs` 的 MATRIX 里跑 ⇒ 列几何这一跑真的量得到。 */
  'kb|kb-dirmenu']
/**
 * **这一跑该不该看到目录层** —— 唯一判据 = 本组合在 `PAD_REQUIRED` 里**声明了 `.ks-dirs`**。
 *
 * ⚠⚠ **2026-09-23（接手批）就地改正**：这里原来写 `DIR_LAYER_COMBOS.includes(padComboKey)`
 *   —— 那份冻结清单是"**矩阵会跑的管理面组合**"，把**没有目录层的面**（渠道库/办事台/备料，
 *   见 `PAD_REQUIRED` 里新加的 `kb|nav-*` 三条）也算成"必须有目录层" ⇒ 那三个面一跑就红在
 *   "量不到 #dircols"（假红：不是回归，是**面的元素集本来就窄**）。
 *   ⇒ 改成读 `padRequired` 里**已经声明**的元素集：这既复用了本脚本既有的"逐组合声明"机制
 *   （`PAD_REQUIRED` 是唯一所有者），又**不动**冻结清单 `DIR_LAYER_COMBOS`（它与
 *   `smoke-kb-pad-pixels.mjs` 的 MATRIX 咬着棘轮）。
 *   ⚠ **判据只增不减**：管理面（`kb|` / `kb|kb-*` 全部）在 `PAD_REQUIRED` 里**都**声明了
 *     `.ks-dirs` ⇒ 它们走的分支与改前**逐字相同**（下面那段"量不到就红"一个字没改）。 */
const dirColsPresenceRequired = Array.isArray(padRequired) && padRequired.includes('.ks-dirs')
/* ── 目录层的**页码源声明**（第 5 步 §5 的守卫）：从页面源码抠 `DIR_COLUMNS` 的条数 ──
   ⚠ 抠的是**声明本体**（`DIR_COLUMNS = [ … ] as const` 里的 `key: '…'` 条数），不是"文本里出现过
     几次 DIR_COLUMNS" —— 注释里也写着这个名字，朴素 grep 会把散文判成声明。 */
const pageSrcPath = join(pluginRoot, 'client', 'KsKnowledgePage.tsx')
let dirColsFromPage = null
try {
  const pageSrc = await readFile(pageSrcPath, 'utf8')
  const m = /const DIR_COLUMNS = \[([\s\S]*?)\] as const/.exec(pageSrc)
  dirColsFromPage = m === null ? null : (m[1].match(/key: '/g) ?? []).length
} catch { /* 读不到 ⇒ 下面的判据报红（读不到就不算验过） */ }
const dirColsProblemsShared = []
/* ⚠⚠ **2026-09-21 第 5 步复核 R1（真缺陷，已修）**：这里原来写
   `const dirColsProblems = [...dirColsProblemsShared]` —— 那是在 `dirColsProblemsShared`
   **还是空数组**的时候拍的快照（三条共享守卫在**下面**那个块里才 push 进去）⇒ 共享守卫
   **只**经 `dirHeadCheck`（它自己那份快照在 push 之后）存活，而 `dirHeadCheck` 在没有目录层
   表头的场景（例如冻结清单里的 `kb|kb-page`）会走 skip 分支 ⇒ 复核的变异 A2 + `kb-page`
   **exit 0**、两行都"这一跑不判"、JSON 里 `problems:[]` 却 `checked:true`。
   ⇒ 现在**不拍快照**：共享守卫只在最后与本次的问题清单**合并**（见下面 `dirColsProblemsAll`），
   并且**只看共享守卫**决定要不要 exit 1（它们是全局一致性，与"这一跑有没有目录层"无关）。 */
const dirColsProblems = []
let dirColsSkipReason = null
if (DIR_LAYER_COMBOS.length === 0) {
  dirColsProblemsShared.push('**冻结清单 DIR_LAYER_COMBOS 是空的** —— 目录层的列几何/表头判据'
    + '会**全部静默跳过**（这一跑照样 exit 0）。清单可以改，但不许清空')
}
{
  const declaredDirs = Object.entries(PAD_REQUIRED)
    .filter(([k, v]) => k.startsWith('kb|') && Array.isArray(v) && v.includes('.ks-dirs'))
    .map(([k]) => k)
  const missingFromFrozen = declaredDirs.filter((k) => !DIR_LAYER_COMBOS.includes(k))
  const missingFromDeclared = DIR_LAYER_COMBOS.filter((k) => !declaredDirs.includes(k))
  if (missingFromFrozen.length > 0) {
    dirColsProblemsShared.push(`这些组合的 PAD_REQUIRED 声明了 .ks-dirs（= 有目录层），`
      + `却不在冻结清单 DIR_LAYER_COMBOS 里：[${missingFromFrozen.join(' ')}] —— `
      + '两处必须一致；新加一个目录层组合就要同时进清单（否则它不会被判列几何）')
  }
  if (missingFromDeclared.length > 0) {
    dirColsProblemsShared.push(`冻结清单里的这些组合在 PAD_REQUIRED 里**没有**声明 .ks-dirs：`
      + `[${missingFromDeclared.join(' ')}] —— 同一条棘轮的反方向`)
  }
  if (dirColsFromPage === null) {
    dirColsProblemsShared.push(`读不到 ${pageSrcPath} 里的 DIR_COLUMNS 声明 —— 读不到就不算验过`
      + '（它是"冻结常数 ↔ 源码声明"这条双向校验的另一半）')
  } else if (dirColsFromPage !== DIR_COLS_EXPECTED) {
    dirColsProblemsShared.push(`页面的 DIR_COLUMNS 有 ${String(dirColsFromPage)} 条，`
      + `而本脚本冻结的规范值是 ${String(DIR_COLS_EXPECTED)}（轨道数与表头格数都按它判）—— `
      + '改列就要同步这里的常数与注释')
  }
}
const dirCols = measured['#dircols']
const dircTracks = (tpl) => {
  const out = []
  let depth = 0
  let cur = ''
  for (const ch of String(tpl ?? '')) {
    if (ch === '(') depth += 1
    if (ch === ')') depth -= 1
    if (/\s/.test(ch) && depth === 0) { if (cur !== '') { out.push(cur); cur = '' } continue }
    cur += ch
  }
  if (cur !== '') out.push(cur)
  return out
}
/* ── token 侧的一半：从 `ksGuideStyles.ts` 抠出三条固定轨的声明值 ── */
let dirTokenDpick = null
let dirTokenDcount = null
let dirTokenDmore = null
try {
  const cssSrc = await readFile(stylesSrcPath, 'utf8')
  const tok = (name) => {
    const m = new RegExp(`--${name}\\s*:\\s*(\\d+)px`).exec(cssSrc)
    return m === null ? null : Number(m[1])
  }
  dirTokenDpick = tok('ks-col-dpick')
  dirTokenDcount = tok('ks-col-dcount')
  dirTokenDmore = tok('ks-col-dmore')
} catch { /* 读不到 ⇒ 下面的判据报红（见 dirColsProblems） */ }
if (dirTokenDpick === null || dirTokenDcount === null || dirTokenDmore === null) {
  dirColsProblems.push(`读不到 ksGuideStyles.ts 里的 --ks-col-dpick（${JSON.stringify(dirTokenDpick)}）/`
    + ` --ks-col-dcount（${JSON.stringify(dirTokenDcount)}）/ --ks-col-dmore（${JSON.stringify(dirTokenDmore)}）`
    + ' —— 读不到就不算验过（这三条固定轨是判据的锚）')
}
if (dirCols === undefined) {
  /* ⚠⚠ **"量不到"不许静默跳过**：判据的锚是**冻结清单** `DIR_LAYER_COMBOS`（不是被声明的
     `PAD_REQUIRED` —— 第二轮复核 C④c 证明"同时改小声明表"就能把这条绕回 exit 0）。 */
  if (dirColsPresenceRequired) {
    dirColsProblems.push(`这一跑的组合（${padComboKey}）在**冻结清单** DIR_LAYER_COMBOS 里`
      + '（它必须有目录层），而 #dircols **一点都没产出** —— 量不到就不算验过'
      + '（目录层在页面上却量不到，是探针坏了，不是"不适用"）')
  } else {
    dirColsSkipReason = `这一跑的组合（${padComboKey}）不在冻结清单 DIR_LAYER_COMBOS 里 —— 目录层列几何不适用`
  }
} else if (!String(dirCols.lh ?? '').trim() || dirCols.lh === '(没有网格元素)') {
  dirColsProblems.push(`取不到目录层的 grid-template-columns（拿到 ${JSON.stringify(dirCols.lh)}）—— 取不到就不算验过`)
} else {
  const tracks = dircTracks(dirCols.lh)
  const px = tracks.map((t) => (/^([\d.]+)px$/.exec(t) === null ? null : Number(/^([\d.]+)px$/.exec(t)[1])))
  const gap = Number(dirCols.pad)
  if (tracks.length !== DIR_COLS_EXPECTED) {
    dirColsProblems.push(`目录层列数 = ${String(tracks.length)}，期望 ${String(DIR_COLS_EXPECTED)}`
      + `（勾选 / 目录 / 篇数 / ⋮ —— 与 DIR_COLUMNS 同数）：${JSON.stringify(dirCols.lh)}`
      + ' —— 有人把目录层接到文件层那条 --ks-cols 上了？')
  }
  if (px.some((v) => v === null)) {
    dirColsProblems.push(`目录层轨道里有**非 px** 值（解析后应为纯像素）：${JSON.stringify(tracks)}`
      + ' —— 只有全部解析成像素，"铺满"与"固定轨对不对"才可判')
  } else {
    /* 固定轨**对冻结常数**（不是对从被测文件抠出来的 token —— 那会恒真；复核 C④a 证伪）。
       ⚠ 索引与 `DIR_COLUMNS` 的顺序绑死：0=勾选 / 2=篇数 / 3=⋮（1 是 1fr 的名字列）。 */
    if (px.length >= 4
        && (px[0] !== DIR_COL_DPICK_EXPECTED || px[2] !== DIR_COL_DCOUNT_EXPECTED
          || px[3] !== DIR_COL_DMORE_EXPECTED)) {
      dirColsProblems.push(`目录层的三条固定轨与冻结规范值不符：实测 `
        + `第 1 轨 ${String(px[0])}px / 第 3 轨 ${String(px[2])}px / 第 4 轨 ${String(px[3])}px，`
        + `而冻结值是 ${String(DIR_COL_DPICK_EXPECTED)} / ${String(DIR_COL_DCOUNT_EXPECTED)} / ${String(DIR_COL_DMORE_EXPECTED)}px`
        + `：${JSON.stringify(dirCols.lh)} —— 把勾选/篇数/⋮ 列改成别的宽度（或写成 1fr）就是这条要抓的回归`)
    }
    if (Math.abs(px.reduce((a, b) => a + b, 0) + gap * (tracks.length - 1) - Number(dirCols.y)) > 1) {
      dirColsProblems.push(`目录层轨道**没铺满**容器：轨道和 ${String(px.reduce((a, b) => a + b, 0))}px`
        + ` + gap ${String(gap)}px × ${String(tracks.length - 1)} = ${String(px.reduce((a, b) => a + b, 0) + gap * (tracks.length - 1))}px，`
        + `而容器内容宽 ${String(dirCols.y)}px（差 >1px ⇒ 右侧死白或溢出）：${JSON.stringify(dirCols.lh)}`)
    }
  }
}
/* **规范 ↔ 实现**的棘轮（同 `PAGE_PAD_*` 那一套）：`ksGuideStyles.ts` 里三条 token 的声明必须等于冻结常数，
   谁单方面改（改 token 或改常数）都在这里红 —— 这条才是"改了 token 而没改这里就红"的**真**判据。 */
if (dirTokenDpick !== null && dirTokenDpick !== DIR_COL_DPICK_EXPECTED) {
  dirColsProblems.push(`ksGuideStyles.ts 的 --ks-col-dpick = ${String(dirTokenDpick)}px，`
    + `而本脚本冻结的规范值是 ${String(DIR_COL_DPICK_EXPECTED)}px（改 token 就要同步这里的常数与注释）`)
}
if (dirTokenDcount !== null && dirTokenDcount !== DIR_COL_DCOUNT_EXPECTED) {
  dirColsProblems.push(`ksGuideStyles.ts 的 --ks-col-dcount = ${String(dirTokenDcount)}px，`
    + `而本脚本冻结的规范值是 ${String(DIR_COL_DCOUNT_EXPECTED)}px（改 token 就要同步这里的常数与注释）`)
}
if (dirTokenDmore !== null && dirTokenDmore !== DIR_COL_DMORE_EXPECTED) {
  dirColsProblems.push(`ksGuideStyles.ts 的 --ks-col-dmore = ${String(dirTokenDmore)}px，`
    + `而本脚本冻结的规范值是 ${String(DIR_COL_DMORE_EXPECTED)}px（同上）`)
}
/* **冻结清单 ↔ 声明表**的棘轮：清单里的组合必须真的在 `PAD_REQUIRED` 里声明 `.ks-dirs`
   （否则"声明表被同改小 + 探针不产出"那条路又会打开）。 */
if (dirColsPresenceRequired && !(Array.isArray(padRequired) && padRequired.includes('.ks-dirs'))) {
  dirColsProblems.push(`组合 ${padComboKey} 在冻结清单 DIR_LAYER_COMBOS 里（必须有目录层），`
    + `但它的 PAD_REQUIRED 声明里**没有 .ks-dirs**（拿到 ${JSON.stringify(padRequired)}）`
    + ' —— 这两处必须一致；谁改了一处而没改另一处，就在这里红')
}
/* ⚠ R1（2026-09-21 复核打回后修）：**共享守卫与本次的问题清单在这里才合并** ——
   三条全局一致性守卫（清单非空 / 双向一致 / 源码声明条数）与"这一跑有没有目录层"无关，
   所以：① 它们**任何时候**都要出现在 `problems` 里；② 只要它们响，`checked` 就是 false
   （下面的 stderr 分支也据此 exit 1，不再被 skipReason 吞掉）。 */
const dirColsProblemsAll = [...dirColsProblems, ...dirColsProblemsShared]
const dirColsCheck = {
  checked: dirColsProblemsAll.length === 0 && dirColsSkipReason === null,
  skipReason: dirColsSkipReason,
  problems: dirColsProblemsAll,
  sharedProblems: dirColsProblemsShared,
  template: dirCols?.lh ?? null,
  tracks: dirCols === undefined ? null : dircTracks(dirCols.lh).length,
  containerWidth: dirCols?.y ?? null,
  gap: dirCols?.pad ?? null,
  presenceRequired: dirColsPresenceRequired,
  tokenDpick: dirTokenDpick,
  tokenDcount: dirTokenDcount,
  tokenDmore: dirTokenDmore,
  combos: DIR_LAYER_COMBOS,
  colsFromPage: dirColsFromPage,
}

/* ══════════ `#stagecol` 的**真断言**（2026-09-21 第 3 步；业主："所有文件都要显示处理状态"） ══════════
 * **为什么要加它（自己先证伪过的洞）**：把 ksGuideStyles.ts 那条 `@container (min-width:660px)`
 * 的门槛改成 `99999px` ⇒ 宽档永不生效、**处理状态列在任何宽度都 `display:none`** ——
 * 而这一批的四条 KB 冒烟**全绿**：
 *   · `smoke-kb-page-render`（jsdom）判的是 `textContent`：隐藏元素的文字照样取得到；
 *   · `#cols` 只判"表头 == 行"（两层一起藏，模板仍然逐字相等）；
 *   · `#dircols` 判的是**目录层**的轨道，与文件层这一列无关。
 * ⇒ 业主那句话在**真浏览器**里原本**没有任何判据**。这一条把它变成可量形态，两个方向都钉住：
 *   ① `ksGuideStyles.ts` 里 `@container` 的 min-width 必须等于**冻结常数** `STAGE_COL_MIN_MAIN_PX`；
 *   ② 真 Chrome 量到的主栏内容宽 ≥ 阈值 ⇒ 处理状态列（与生效日期列）**必须** `display != none`；
 *   ③ 窄于阈值 ⇒ **必须**是 `none`（那是**有意**的响应式规则，不是"忘了恢复"）；
 *   ④ 列头文案必须还是 `处理状态`（改名字要显式改这里）。
 * ⚠ 适用面：只有这一跑真的渲染了**文件层且有文件行**时才判；最外层/空目录**明说没判**（skipReason），
 *   不静默通过。 */
const STAGE_COL_MIN_MAIN_PX = 660
const STAGE_COL_HEAD_EXPECTED = '处理状态'
let stageContainerMin = null
try {
  const cssSrc2 = await readFile(stylesSrcPath, 'utf8')
  const m2 = /@container\s*\(\s*min-width\s*:\s*(\d+)px\s*\)/.exec(cssSrc2)
  stageContainerMin = m2 === null ? null : Number(m2[1])
} catch { /* 读不到 ⇒ 下面报红 */ }
const stageCol = measured['#stagecol']
const stageColProblems = []
let stageColSkipReason = null
if (stageContainerMin === null) {
  stageColProblems.push('读不到 ksGuideStyles.ts 里 `@container (min-width:…)` 的阈值'
    + ' —— 读不到就不算验过（那一条就是"宽档恢复这两列"的开关）')
} else if (stageContainerMin !== STAGE_COL_MIN_MAIN_PX) {
  stageColProblems.push(`ksGuideStyles.ts 的 @container 阈值 = ${String(stageContainerMin)}px，`
    + `而本脚本冻结的规范值是 ${String(STAGE_COL_MIN_MAIN_PX)}px —— 改这个阈值就要同步改这里与注释`
    + '（它决定"多宽才看得见处理状态列"）')
}
if (stageCol === undefined) {
  if (page === 'kb') {
    stageColProblems.push('这一跑是 kb 页而 `#stagecol` **一点都没产出** —— 量不到就不算验过（探针坏了？）')
  } else {
    stageColSkipReason = `本页不是知识库页（page=${page}），处理状态列不适用`
  }
} else if (!stageCol.n) {
  stageColSkipReason = '这一跑这一层没有文件行（最外层/空目录），处理状态列没有对象'
} else {
  const mainW = Number(stageCol.y) || 0
  const stageShown = stageCol.w === 1
  const dateShown = stageCol.h === 1
  const wide = mainW >= STAGE_COL_MIN_MAIN_PX
  if (stageCol.fs !== STAGE_COL_HEAD_EXPECTED) {
    stageColProblems.push(`文件表的第 4 列列头是 ${JSON.stringify(stageCol.fs)}，`
      + `期望 ${JSON.stringify(STAGE_COL_HEAD_EXPECTED)} —— 列头文案（或列顺序）被改了`)
  }
  if (!String(stageCol.lh ?? '').startsWith('(没有') && !stageCol.lh) {
    stageColProblems.push(`取不到处理状态列的 computed display（拿到 ${JSON.stringify(stageCol.lh)}）`
      + ' —— 取不到就不算验过')
  }
  if (wide && !stageShown) {
    stageColProblems.push(`主栏内容宽 ${String(mainW)}px ≥ 阈值 ${String(STAGE_COL_MIN_MAIN_PX)}px（宽档），`
      + `而**处理状态列是隐藏的**（computed display = ${JSON.stringify(stageCol.lh)}）—— `
      + '业主「所有文件都要显示处理状态」这条承诺在这一档**没有兑现**'
      + '（典型成因：@container 阈值被调大、那条 display:flex 被删、或列模板里少了这一轨）')
  }
  if (wide && !dateShown) {
    stageColProblems.push(`宽档下**生效日期列**也是隐藏的（computed display = ${JSON.stringify(stageCol.pad)}）——`
      + '宽档应当是 5 列（名称 | 效力 | 生效日期 | 处理状态 | ⋮）')
  }
  if (!wide && (stageShown || dateShown)) {
    stageColProblems.push(`主栏内容宽 ${String(mainW)}px < 阈值 ${String(STAGE_COL_MIN_MAIN_PX)}px（窄档），`
      + `而处理状态列 display=${JSON.stringify(stageCol.lh)} / 生效日期列 display=${JSON.stringify(stageCol.pad)}`
      + ' —— 窄档**故意**藏这两列（与三轨模板配套）；要改成"永远显示"就必须同时改这里与 ksGuideStyles.ts')
  }
}
const stageColCheck = {
  checked: stageColProblems.length === 0 && stageColSkipReason === null,
  skipReason: stageColSkipReason,
  problems: stageColProblems,
  rows: stageCol?.n ?? null,
  mainWidth: stageCol?.y ?? null,
  stageDisplay: stageCol?.lh ?? null,
  dateDisplay: stageCol?.pad ?? null,
  head: stageCol?.fs ?? null,
  containerMin: stageContainerMin,
  frozenMin: STAGE_COL_MIN_MAIN_PX,
}

/* ══════════ `#inboxcols` 的**真断言**（2026-09-21 第 4 步：「待分类」这一层） ══════════
 * 为什么必须真浏览器里量：业主"每篇状态如实显示""好发现哪些要人工修"是**看得见**的要求，
 * 而 jsdom 的 textContent 对 display:none 照样取得到（第 3 步复核自己踩出来的洞）。
 * 判据（两个方向都钉住，与 `stageColCheck` 同一纪律）：
 *   ① 列头与数据行的 grid-template-columns 必须**逐字相同**、且列数 = **冻结的 5**
 *      （勾选 / 文件名 / 状态 / 建议去向 / ⋮ —— 与 `INBOX_COLUMNS` 同数）；
 *   ② 状态列列头文案必须还是「状态」，且**主栏够宽时状态列必须看得见**、窄档也必须看得见
 *      （业主"每篇显示状态"没有"窄了就不显示"这个例外 —— 窄档藏的是**建议去向**那一列）；
 *   ③ 窄档下**建议去向**必须是 `none`、宽档必须是 `flex`（有意规则，两个方向都钉）；
 *   ④ 每一行都要有勾选框与 ⋮（逐行数出来，不是"至少有"）；
 *   ⑤ 量不到 / 取不到值 ⇒ **红**（"没验到"不能渲染成"通过"）。
 * 适用面：只有这一跑**是「待分类」层**（有 `.ks-list-inbox`）时才判；其余**明说没判**。 */
const INBOX_COLS_WIDE = 5
const INBOX_COLS_NARROW = 4
const INBOX_STAGE_HEAD_EXPECTED = '状态'
const inbox = measured['#inboxcols']
const inboxProblems = []
let inboxSkipReason = null
if (inbox === undefined) {
  inboxSkipReason = `这一跑不是「待分类」层（没有 .ks-list-inbox；page=${page}）—— 待分类几何不适用`
} else if (!inbox.n) {
  inboxSkipReason = '这一跑待分类层没有数据行（空列表），列几何没有对象'
} else {
  const mainW = Number(inbox.gap) || 0
  const wide = mainW >= STAGE_COL_MIN_MAIN_PX
  const destShown = String(inbox.pad) !== 'none'
  const tracksOf = (tpl) => String(tpl ?? '').split(/\s+/).filter((s) => s !== '')
  if (!inbox.y || !inbox.w || String(inbox.y).startsWith('(没有') || String(inbox.w).startsWith('(没有')) {
    inboxProblems.push(`取不到待分类层的列模板（表头 ${JSON.stringify(inbox.y)} / 行 ${JSON.stringify(inbox.w)}）`
      + ' —— 取不到就不算验过')
  } else {
    if (String(inbox.y) !== String(inbox.w)) {
      inboxProblems.push(`待分类层表头与行的 grid-template-columns 不一致：表头 ${JSON.stringify(inbox.y)}`
        + ` / 行 ${JSON.stringify(inbox.w)} —— 两层必须共用同一条 --ks-cols`)
    }
    /* 轨道数是**两档各自冻结**的：窄档 4 轨（建议去向被藏，那一格不占轨）、宽档 5 轨。
       两个方向都钉住 —— 窄档少藏一列、或宽档没恢复那一列，都在这里红。 */
    const want = wide ? INBOX_COLS_WIDE : INBOX_COLS_NARROW
    const tracks = tracksOf(inbox.y).length
    if (tracks !== want) {
      inboxProblems.push(`待分类层列数 = ${String(tracks)}，期望 ${String(want)}`
        + `（${wide ? '宽' : '窄'}档：${wide ? '勾选 / 文件名 / 状态 / 建议去向 / ⋮' : '勾选 / 文件名 / 状态 / ⋮'}`
        + ` —— 与 INBOX_COLUMNS + 建议去向列的显隐配套）：${JSON.stringify(inbox.y)}`)
    }
  }
  if (inbox.fs !== INBOX_STAGE_HEAD_EXPECTED) {
    inboxProblems.push(`待分类层的状态列列头是 ${JSON.stringify(inbox.fs)}，`
      + `期望 ${JSON.stringify(INBOX_STAGE_HEAD_EXPECTED)} —— 列头文案（或列顺序）被改了`)
  }
  /* ② 状态列**两个档位都必须看得见**（这是这一条的主要目的）。 */
  if (inbox.h !== 1) {
    inboxProblems.push(`**待分类层的状态列是隐藏的**（computed display = ${JSON.stringify(inbox.lh)}，`
      + `主栏内容宽 ${String(mainW)}px）—— 业主「每篇的状态如实显示」在这一档没有兑现；`
      + '窄档能藏的只有「建议去向」那一列（见 ksGuideStyles.ts 的 .ks-list-inbox 容器查询）')
  }
  /* ③ 建议去向：窄档藏、宽档显（有意规则，两个方向都钉）。 */
  if (wide && !destShown) {
    inboxProblems.push(`宽档（主栏 ${String(mainW)}px ≥ ${String(STAGE_COL_MIN_MAIN_PX)}px）下`
      + `**建议去向列是隐藏的**（display=${JSON.stringify(inbox.pad)}）—— 宽档应当 5 列全在`)
  }
  if (!wide && destShown) {
    inboxProblems.push(`窄档（主栏 ${String(mainW)}px < ${String(STAGE_COL_MIN_MAIN_PX)}px）下`
      + `建议去向列是显示的（display=${JSON.stringify(inbox.pad)}）—— 窄档**故意**藏这一列`
      + '（挤不下）；要改成永远显示就同时改这里与 ksGuideStyles.ts')
  }
  const diag = (() => { try { return JSON.parse(String(inbox.radius ?? '{}')) } catch { return {} } })()
  if (Number(diag.pickN) !== Number(inbox.n)) {
    inboxProblems.push(`待分类层每行都应当有一个勾选框：${String(inbox.n)} 行却有 ${String(diag.pickN)} 个`
      + '（少一个 = 那一篇没法批量处置）')
  }
  if (Number(diag.rows) !== Number(inbox.n)) {
    inboxProblems.push(`待分类层每行都应当有一个 ⋮ 处置按钮：${String(inbox.n)} 行却有 ${String(diag.rows)} 个`)
  }
}
const inboxCheck = {
  checked: inboxProblems.length === 0 && inboxSkipReason === null,
  skipReason: inboxSkipReason,
  problems: inboxProblems,
  rows: inbox?.n ?? null,
  tracks: inbox === undefined || !inbox.y ? null : String(inbox.y).split(/\s+/).filter((s) => s !== '').length,
  header: inbox?.y ?? null,
  row: inbox?.w ?? null,
  stageHead: inbox?.fs ?? null,
  stageDisplay: inbox?.lh ?? null,
  destDisplay: inbox?.pad ?? null,
  mainWidth: inbox?.gap ?? null,
  batchN: (() => { try { return JSON.parse(String(inbox?.radius ?? '{}')).batchN ?? null } catch { return null } })(),
}

/* ══════════ `#ask` 的**真断言**（2026-09-21 第 6 步：按目录范围提问） ══════════
 * 为什么必须真浏览器里量：jsdom 那几条只能证明"元素在 DOM 里、文字对"，而这一批的新界面是
 *   **给业主看**的（入口按钮 / 范围 chip / 提问面板）⇒ 必须有"真 Chrome 里量得到"的那一半：
 *   ① 按钮 / chip / 面板 **高度都 > 0**（display:none、没挂载、空盒子都是 0 —— 存在不等于看得见）；
 *   ② chip **不许溢出页面右缘**（窄档里两个长目录名最容易把它顶出去，而那是"贴边"的一种）；
 *   ③ 量不到 / 取不到值 ⇒ **红**（"没验到"不能渲染成"通过"）。
 * 适用面：只有这一跑**就是"按目录范围提问"那个场景**（`comboKey === 'kb|kb-ask'`）时才判；
 *   ⚠ 不能拿"`#ask` 量点在不在"当门槛 —— 入口按钮 `.ks-ask-open` 在**每一跑**都在 DOM 里
 *     （只是没点开时 chip/面板不存在）⇒ 拿它当门槛会让**别的场景假红**（本批实测踩到：
 *     14 组 kb 全红，只有 kb-ask 自己绿）。其余场景**明说没判**。 */
const ask = measured['#ask']
const askProblems = []
let askSkipReason = null
if (padComboKey !== 'kb|kb-ask') {
  askSkipReason = `这一跑不是"按目录范围提问"场景（comboKey=${padComboKey}）—— 范围提问界面这一跑不判`
} else if (ask === undefined) {
  askSkipReason = '这一跑点了「在此范围内提问」却没量到 #ask 量点 —— 量不到就不算验过'
} else {
  if (ask.n !== 1) {
    askProblems.push(`「在此范围内提问」按钮实测 ${String(ask.n)} 个（期望 1 个，文字应为「在此范围内提问」，`
      + `实测文字=「${String(ask.fs)}」）`)
  } else if (!String(ask.fs).includes('在此范围内提问')) {
    askProblems.push(`入口按钮的文字是「${String(ask.fs)}」，里面没有「在此范围内提问」`)
  }
  /* ①b **它在哪一行**（业主 2026-09-22 亲定的位置）：必须是当前文件夹名那一行（`.ks-list-cap`），
     不许回到工具栏。判据钉住位置 ⇒ "挪回旧工具栏"这种改动**当场红**（变异②）。 */
  if (ask.where !== 'list-cap') {
    askProblems.push(`「在此范围内提问」按钮**不在当前文件夹名那一行**（.ks-list-cap），实测在哪一行：`
      + `${JSON.stringify(ask.where)} —— 业主 2026-09-22 明说"按钮改到搜索栏上面显示文件夹名称的 `
      + `bar 上，这样就很清楚是在这个文件夹内进行搜索"；挪回工具栏/别处都算违反`)
  }
  if (ask.chipN === 1 && ask.chipWhere !== 'list-cap') {
    askProblems.push(`范围 chip **跟着按钮一起搬家**：它应当在同一行（.ks-list-cap），实测 `
      + `${JSON.stringify(ask.chipWhere)}`)
  }
  /* ①c **元素身份**（复核打回 §1 的另一半）：chip 与按钮必须在**同一个行元素**里 ——
     判"哪一行"不许靠"父元素是谁"推（套一层 wrapper 就推错了）。 */
  if (ask.chipN === 1 && ask.chipRowSame !== true) {
    askProblems.push('范围 chip 与入口按钮**不在同一个行元素里**（chipRowSame='
      + `${JSON.stringify(ask.chipRowSame)}；按钮行=${JSON.stringify(ask.where)}、chip 行=`
      + `${JSON.stringify(ask.chipWhere)}）—— 两者必须挂在同一行（.ks-list-cap）`)
  }
  if (!Number.isFinite(ask.w) || ask.w <= 0) {
    askProblems.push(`「在此范围内提问」按钮在真 Chrome 里高度 = ${JSON.stringify(ask.w)}px`
      + ' —— 存在不等于看得见（display:none / 空盒子都是 0）')
  }
  if (ask.x !== 1) {
    askProblems.push(`范围 chip 实测 ${String(ask.x)} 个（期望 1 个）—— 范围必须看得见，`
      + '否则"这次在什么范围里问"用户无从判断')
  }
  if (!Number.isFinite(ask.h) || ask.h <= 0) {
    askProblems.push(`范围 chip 在真 Chrome 里高度 = ${JSON.stringify(ask.h)}px`
      + `（chip 文字=「${String(ask.lh)}」）—— 存在不等于看得见`)
  }
  if (ask.y !== 1) {
    askProblems.push(`提问面板实测 ${String(ask.y)} 个（期望 1 个）`)
  }
  if (!Number.isFinite(ask.pad) || ask.pad <= 0) {
    askProblems.push(`提问面板在真 Chrome 里高度 = ${JSON.stringify(ask.pad)}px —— 存在不等于看得见`)
  }
  /* ② chip 右缘不许越过**它所在那一行**的内容盒右缘（越过 = 被挤出这一行；窄档 + 长目录名最容易）。 */
  if (!Number.isFinite(ask.gap)) {
    askProblems.push(`量不到 chip 的右缘溢出量（gap=${JSON.stringify(ask.gap)}）—— 取不到值就不算验过`)
  } else if (ask.gap > 1) {
    /* ⚠ 容差 1px（渲染取整）：chip 作为 flex 项**本来就允许收缩到正好铺满那一行**
       （`gap == 0` 是正常形态）；真出问题是它**缩不下去**（`min-width:0` 被去掉、
       名字那一格不可收缩）⇒ 顶出这一行 ⇒ gap > 0。 */
    askProblems.push(`范围 chip **被挤出所在那一行** ${String(ask.gap)}px（该行右内边距 `
      + `${String(ask.radius)}px；所在行=${JSON.stringify(ask.chipWhere)}）—— 窄档里长目录名会把这一行顶破，`
      + 'chip 里的名字那一格必须能收缩（min-width:0 + 省略号），这一行还必须能折行')
  }
}
const askCheck = {
  checked: askProblems.length === 0 && askSkipReason === null,
  skipReason: askSkipReason,
  problems: askProblems,
  buttonN: ask?.n ?? null,
  buttonText: ask?.fs ?? null,
  buttonH: ask?.w ?? null,
  chipN: ask?.x ?? null,
  chipText: ask?.lh ?? null,
  chipH: ask?.h ?? null,
  panelN: ask?.y ?? null,
  panelH: ask?.pad ?? null,
  chipOverflowPx: ask?.gap ?? null,
  pagePadRight: ask?.radius ?? null,
  buttonRow: ask?.where ?? null,
  chipRow: ask?.chipWhere ?? null,
  chipRowSameAsButtonRow: ask?.chipRowSame ?? null,
}
/* ══════════ 复核 `verify-freeze-kb-ui3` 打回 §④-C 补回来的两条（2026-09-21）
 * 那两条旧判据在本批重写时**掉了**（主体仍在、判据没了）：
 *   ① 旧第 59 条「每行行内**可见控件 ≤ 3**」（P1-1 的验收口径）—— 本脚本一直在
 *      `'.ks-item#rows'` 里逐行**量** `ctrls`，但 Node 侧**零断言**（量了不判 ⇒ 加一个行内按钮
 *      不会有任何东西响）。现在把它变成会红的判据。
 *   ② 旧第 29 条「目录层表头每一格 display 必须是 flex 不是 grid」（「目录」只剩一个「目」那个坑）。
 * ⚠ 口径不变：`ctrls` 用的是**真控件选择器**（button/input/select/textarea/[role=*]/contenteditable
 *   + 展示用的 .ks-status），不是写死的类名清单（那段更正见 `'.ks-item#rows'` 的注释）。
 * 适用面：只有这一跑**真的有数据行 / 真的有目录层表头**时才判；没有对象**明说没判**（skipReason）。 */
const ROW_CTRLS_MAX = 3
/* **冻结的构成**（2026-09-21）：知识库页的文件行行内**只有两样** —— 行尾「⋮」触发器 + 只展示的
   `.ks-status` 徽章。`ROW_CTRLS_MAX = 3` 是 P1-1 的历史上限（仍然判）；下面这条**等于 2** 才是
   真正有牙的那条：行内再加**任何一样**能点的东西（不管挂什么类名）都会让它红，
   逼着改的人**显式**改这个常数并在注释里说明为什么。
   ⚠ **第 5 步改成 3**（显式改，理由在此）：文件行加了**勾选列**（批量挪/复制/从这一层拿掉用），
   行内因此是「勾选框 + 效力徽章 + ⋮」= 3。上限 `ROW_CTRLS_MAX` 仍是 3（与它相等，不再有余量）——
   再加第四样就会撞上限，两条判据一起响。
   ⚠ 只在 `page === 'kb'` 上判"等于"（其它页面的行构成不同，只吃上面那个上限）。 */
const ROW_CTRLS_EXPECTED = 3
/* **「待分类」行的冻结构成**（第 4 步）：勾选框（真 input） + 行尾「⋮」= 2。
   ⚠ 状态那一列是 `.ks-stage-tag` 之类的**只展示 span**，不是 `.ks-status` 徽章
     （ctrls 口径只把 `.ks-status` 算进来）⇒ 待分类行也是 2；再加任何能点的东西都会红。 */
const ROW_CTRLS_INBOX_EXPECTED = 2
/* **「目录」行的冻结构成**（第 5 步新增这条判据）：勾选框 + 名字那一格里的「进入」真 button
   + 行尾「⋮」= 3。目录行从 button 变成 div 之后**行内没有** `.ks-status` 徽章（篇数是个
   `.ks-kb-badge` span）⇒ 这个数只由这三样决定；加第四样就红。
   ⚠ 同时它把"目录行必须整行可点"那条承诺的**可见形态**钉住了：进入必须是一个真控件
     （键盘可达），不是"靠一行 div 的 onClick 撑着"。 */
const ROW_CTRLS_DIR_EXPECTED = 3
const rowCtrls = measured['.ks-item#rows']
const rowCtrlsProblems = []
let rowCtrlsSkipReason = null
/* ⚠ 逐行数据的字段名是 `rows`（不是 `items`）—— 见量点那里 `{ …, rows: [...] }` 的定义。
   写错的话这里会安静地走"没有文件行"的 skip 分支（我第一版就写错成 `items`，实测到了）。 */
const rowCtrlsRows = Array.isArray(rowCtrls?.rows) ? rowCtrls.rows : []
/* ⚠ 只判**文件行**：`.ks-item` 同时命中目录行（第 3 步时行内 0 个控件；第 5 步起 3 个）——
   不分层就会把目录行当成"少了一样东西"而假红（第一版实测：默认态 4 行目录 ⇒ 实测 [0,0,0,0] ⇒ red）。 */
const rowCtrlsFileRows = rowCtrlsRows.filter((it) => it.kind === 'file')
/* 「待分类」行（第 4 步）—— 与文件行**分开判**（它的构成就是不一样：一个勾选框 + 一个 ⋮）。 */
const rowCtrlsInboxRows = rowCtrlsRows.filter((it) => it.kind === 'inbox')
/* 「目录」行（第 5 步起也判）—— 勾选框 + 「进入」button + ⋮ = 3（见 ROW_CTRLS_DIR_EXPECTED）。 */
const rowCtrlsDirRows = rowCtrlsRows.filter((it) => it.kind === 'dir')
if (rowCtrls === undefined
    || (rowCtrlsFileRows.length === 0 && rowCtrlsInboxRows.length === 0 && rowCtrlsDirRows.length === 0)) {
  rowCtrlsSkipReason = '这一跑没有文件行/待分类行/目录行（空页面），行内控件数没有对象'
} else {
  const counts = rowCtrlsFileRows.map((it) => Number(it.ctrls))
  const inboxCounts = rowCtrlsInboxRows.map((it) => Number(it.ctrls))
  const dirCounts = rowCtrlsDirRows.map((it) => Number(it.ctrls))
  if (page === 'kb' && rowCtrlsFileRows.length > 0) {
    const odd = counts.filter((c) => c !== ROW_CTRLS_EXPECTED)
    if (odd.length > 0) {
      rowCtrlsProblems.push(`知识库页的文件行行内可见控件数应当是**冻结的 ${String(ROW_CTRLS_EXPECTED)}**`
        + `（勾选框 + 行尾「⋮」+ 只展示的 .ks-status 徽章），实测 ${JSON.stringify(counts)}`
        + ' —— 行内加了/少了能点的东西？加了就**显式**改 ROW_CTRLS_EXPECTED 并说明为什么')
    }
    if (new Set(counts).size > 1) {
      rowCtrlsProblems.push(`文件行之间行内控件数**不一致**（${JSON.stringify(counts)}）——`
        + '同一层的行应当长得一样；不一致说明某一行多/少了控件')
    }
  }
  if (page === 'kb' && rowCtrlsDirRows.length > 0) {
    const odd = dirCounts.filter((c) => c !== ROW_CTRLS_DIR_EXPECTED)
    if (odd.length > 0) {
      rowCtrlsProblems.push(`知识库页的目录行行内可见控件数应当是**冻结的 ${String(ROW_CTRLS_DIR_EXPECTED)}**`
        + `（勾选框 + 名字那一格里的「进入」真 button + 行尾「⋮」），实测 ${JSON.stringify(dirCounts)}`
        + ' —— 行内加了/少了能点的东西？加了就**显式**改 ROW_CTRLS_DIR_EXPECTED 并说明为什么')
    }
    if (new Set(dirCounts).size > 1) {
      rowCtrlsProblems.push(`目录行之间行内控件数**不一致**（${JSON.stringify(dirCounts)}）`)
    }
  }
  if (page === 'kb' && rowCtrlsInboxRows.length > 0) {
    const odd = inboxCounts.filter((c) => c !== ROW_CTRLS_INBOX_EXPECTED)
    if (odd.length > 0) {
      rowCtrlsProblems.push(`待分类行的行内可见控件数应当是**冻结的 ${String(ROW_CTRLS_INBOX_EXPECTED)}**`
        + `（勾选框 + 行尾「⋮」），实测 ${JSON.stringify(inboxCounts)}`
        + ' —— 行内又塞了能点的东西？加了就**显式**改 ROW_CTRLS_INBOX_EXPECTED 并说明为什么')
    }
    if (new Set(inboxCounts).size > 1) {
      rowCtrlsProblems.push(`待分类行之间行内控件数**不一致**（${JSON.stringify(inboxCounts)}）`)
    }
  }
  const over = [...counts, ...inboxCounts, ...dirCounts].filter((c) => !Number.isFinite(c) || c > ROW_CTRLS_MAX)
  if (over.length > 0) {
    rowCtrlsProblems.push(`有 ${String(over.length)} 行的行内可见控件数 > ${String(ROW_CTRLS_MAX)}`
      + `（实测 ${JSON.stringify([...counts, ...inboxCounts, ...dirCounts])}）—— 行内又塞了能点的东西`
      + '（不管挂什么类名，这个数都会 +1）；P1-1 的验收口径就是"行内就一个 ⋮"，其余收进溢出菜单')
  }
}
const rowCtrlsCheck = {
  checked: rowCtrlsProblems.length === 0 && rowCtrlsSkipReason === null,
  skipReason: rowCtrlsSkipReason,
  problems: rowCtrlsProblems,
  counts: rowCtrlsFileRows.map((it) => it.ctrls),
  inboxCounts: rowCtrlsInboxRows.map((it) => it.ctrls),
  dirCounts: rowCtrlsDirRows.map((it) => it.ctrls),
  max: ROW_CTRLS_MAX,
}

/* ⚠⚠ **2026-09-21（第 5 步 §5）就地补齐这条判据**（复核点名）：`dirColsCheck` 有"冻结常数 ↔
 * 源码声明"的双向校验，`dirHeadCheck` 原来**只有**"表头格数 == 冻结常数"这一半 ——
 * 把 `DIR_HEAD_CELLS_EXPECTED` 改小、或把清单里一条删掉，就能**静默收窄覆盖面**。
 * 现在它多了两条锚：① 页面 `DIR_COLUMNS` 的条数（`dirColsFromPage`）必须等于这个常数；
 * ② `DIR_LAYER_COMBOS` 那三条守卫（非空 / 双向一致）也一并算进这一跑的问题清单。
 * ⚠ `DIR_HEAD_CELLS_EXPECTED` 的**声明**已经上移到 `DIR_COLS_EXPECTED` 旁边（同源同值），
 *   这里不再重复声明（两处各写一份正是"哪一处都不算数"的老毛病）。 */
const dirHead = measured['#dirhead']
const dirHeadProblems = [...dirColsProblemsShared]
let dirHeadSkipReason = null
const dirHeadPresenceRequired = Array.isArray(padRequired) && padRequired.includes('.ks-dirs')
if (dirHead === undefined || !String(dirHead.lh ?? '').trim()) {
  if (dirHeadPresenceRequired) {
    dirHeadProblems.push(`这一跑的组合（${padComboKey}）在**冻结清单** DIR_LAYER_COMBOS 里（它必须有目录层），`
      + '而目录层表头格的 display **一点都没量到** —— 量不到就不算验过')
  } else {
    dirHeadSkipReason = `这一跑的组合（${padComboKey}）不在冻结清单 DIR_LAYER_COMBOS 里 —— 目录层表头格不适用`
  }
} else {
  const shows = String(dirHead.lh).split(',')
  if (shows.length !== DIR_HEAD_CELLS_EXPECTED) {
    dirHeadProblems.push(`目录层表头格数 = ${String(shows.length)}，期望 ${String(DIR_HEAD_CELLS_EXPECTED)}`
      + `（勾选 / 目录 / 篇数 / ⋮）：${JSON.stringify(shows)}`)
  }
  if (shows.some((d) => d !== 'flex')) {
    dirHeadProblems.push(`目录层表头有格子的 computed display 不是 flex：${JSON.stringify(shows)}`
      + ' —— 那一格一旦被 grid 接管，「目录」两个字会被当成两轨、**只剩一个「目」**（旧第 29 条抓的就是它）')
  }
}
const dirHeadCheck = {
  checked: dirHeadProblems.length === 0 && dirHeadSkipReason === null,
  skipReason: dirHeadSkipReason,
  problems: dirHeadProblems,
  displays: dirHead?.lh ?? null,
  cells: dirHead?.n ?? null,
}

/* ══════════ 新判据①（2026-09-23 接手批）：**四个面观感一致**（骨架 + 页头 + 选中标签） ══════════
 * 业主口径（原话）："四个面行为一致（知识库 / 渠道库 / 办事台 / 预览器），页头观感一致、
 *   **不重叠、不压字**"。改前这件事**一次都没量过** —— `--page kb` 只能截到 `params.page='manage'`
 *   那一个面（见本轮新增的 `--nav-page`），另外三个面从来没进过真浏览器。
 *
 * 判据（每条都"量不到就红"，不静默通过）：
 *   ① 四个面必须有**同一个骨架**：恰好 1 个 `.ks-page`、恰好 1 个 `.ks-kb`、恰好 1 个页头
 *      —— 办事台改前是**两层 `.ks-page` 嵌套**（`.ks-page > .ks-page > .ks-kb`），
 *      这一条就是抓它的（形态上"多套一层外壳"，看着就是另一个界面）。
 *   ② 标签条必须**恰好四枚**、且**恰好一枚**被选中，选中那枚的文字必须与本面的 `params.page`
 *      **对得上**（manage→知识库 / channels→渠道库 / capabilities→办事台）。
 *      改前 `materials` 面实测 `ks-tabfolder-on` **一个都没有**（`--nav-page materials` 那跑）
 *      —— 脸错位了还照样截图，正是这条要抓的。
 *   ③ 页头里**真的看得见**的成员只许是 `.ks-page-sub`（"横幅删掉、大标题删掉、只留一句介绍"）：
 *      报出 headKids 逐个成员，凡 `shown=1` 而类名不是 ks-page-sub ⇒ 红。
 *      ⚠ 这一条判的是**渲染结果**（computed display + 盒子 > 0），不是"源码里写了什么"。
 *
 * ⚠ 适用范围：只在 `--page kb`（= 走 `KsKnowledgePage` 四标签外壳）时判 ——
 *   `--page capabilities|ingest|materials` 挂的是**组件自己**（没有标签条），本条不适用 ⇒ 明说没判。
 *   `--page kb` 但**没有** `.ks-page-head` 的跑（stub 里没有这种）⇒ 也明说没判，不静默通过。 */
/** `params.page` → 本该被选中的那枚标签的文字（唯一所有者）。
 *  ⚠ **`materials` 这一面按设计"不占标签"**：`KsTopTabs` 那四枚是
 *    知识库 / 渠道库 / 办事台 / 预览器，备料（原「参考资料」）是**次级页**、收在开始页卡的 ▾ 里
 *    （见 `KsTopTabs` 上方那段留痕）。⇒ 它的期望值是 `null` = **一枚都不许被选中**
 *    —— 那不是"没登记"，而是**登记过的期望**（登记在下面这个 `null` 上；
 *      `undefined` 才是"忘了登记"）。 */
const FACE_TAB_LABEL = { manage: '知识库', channels: '渠道库', capabilities: '办事台', materials: null }
const faceNavProblems = []
let faceNavSkipReason = null
const faceM = measured['#face']
if (page !== 'kb') {
  faceNavSkipReason = `本页挂的是组件自己（page=${page}）—— 没有四标签条，四个面一致性不适用`
} else if (faceM === undefined) {
  faceNavProblems.push('这一跑**量不到 `#face`**（标签条/页头不在 DOM 里）—— 量不到就不算验过')
} else if (!(navPage in FACE_TAB_LABEL)) {
  faceNavProblems.push(`本脚本的 FACE_TAB_LABEL 没有 ${JSON.stringify(navPage)} 这一面 —— `
    + '加了 --nav-page 的取值却忘了在这里登记"它该选中哪枚标签"（按设计不占标签的面要显式登记成 null）')
} else {
  /* ⚠ `.ks-page` **个数**不是判据（面板自己会带一层，且外壳的形态是
     `.ks-page > .ks-kb > nav`）—— 这里只把个数当信息报出来；
     真正判的是"**标签条与页头共处同一个 `.ks-page`**"（`fs`），以及两者各自到那一层
     之间**没有被第二层 `.ks-page` 夹住**（`lh` = 页头的 `.ks-page` 祖先个数，必须 1）。
     改前办事台面：标签条在**外层** `.ks-page`、页头与内容被**第二层**包着 ⇒ `fs='0'` ⇒ 红。 */
  if (faceM.x < 1) {
    faceNavProblems.push('这一跑一个 .ks-page 都没有（标签条/页头该挂在它里面）—— 量不到就不算验过')
  } else {
    if (faceM.fs !== '1') {
      faceNavProblems.push('**标签条与页头不在同一个 `.ks-page` 之下**（或标签条上面夹了不止一层）'
        + `（本跑 .ks-page 个数 ${String(faceM.x)}）—— 这正是改前办事台面的病：`
        + '标签条在**外层**、页头与页面内容被**第二层** `.ks-page` 包住，'
        + '实测页头/内容左缘因此比另外三个面多缩进 24px')
    }
    if (String(faceM.lh) !== '1') {
      faceNavProblems.push('**页头上面夹了不止一层 `.ks-page`**（页头的 `.ks-page` 祖先个数 = '
        + `${String(faceM.lh)}，必须恰好 1）—— 又成了盒子套盒子`)
    }
  }
  if (faceM.y !== 1) {
    faceNavProblems.push(`这一跑有 ${String(faceM.y)} 个 .ks-kb（必须恰好 1 个）`
      + ' —— 页面根（左列 + 右栏那一层）只许有一层')
  }
  if (faceM.w !== 1) {
    faceNavProblems.push(`这一跑有 ${String(faceM.w)} 个 .ks-page-head（必须恰好 1 个）`)
  }
  const labels = String(faceM.strip?.pad ?? '').split('|')
  if (labels.length !== 4 || labels.some((s) => s === '')) {
    faceNavProblems.push(`标签条里渲染出来的标签不是 4 枚：${JSON.stringify(labels)}`)
  }
  const ons = String(faceM.strip?.gap ?? '').split('|').filter(Boolean)
  const want = FACE_TAB_LABEL[navPage]
  if (want === null) {
    /* 按设计**不占标签**的面（备料）：期望是"一枚都不许被选中"。 */
    if (ons.length !== 0) {
      faceNavProblems.push(`本面（${navPage}）按设计**不占标签**（次级页），`
        + `却有 ${String(ons.length)} 枚被选中：${JSON.stringify(ons)} —— 四枚标签里没有任何一枚该高亮`)
    }
  } else if (ons.length !== 1) {
    faceNavProblems.push(`被选中的标签有 ${String(ons.length)} 枚（必须恰好 1 枚）：${JSON.stringify(ons)}`
      + ` —— 本面是 ${navPage}，该选中「${want}」`)
  } else if (ons[0] !== want) {
    faceNavProblems.push(`选中的标签是「${ons[0]}」，而本面是 ${navPage}（该选中「${want}」）—— 面的脸错位了`)
  }
  const kids = Array.isArray(faceM.headKids) ? faceM.headKids : []
  if (kids.length === 0) {
    faceNavProblems.push('页头里一个成员都没量到 —— 量不到就不算验过')
  }
  const shownNotSub = kids.filter((k) => k.shown === 1 && k.cls !== 'ks-page-sub')
  if (shownNotSub.length > 0) {
    faceNavProblems.push(`页头里**看得见**的成员不止那一句介绍：`
      + `${JSON.stringify(shownNotSub.map((k) => k.cls))} —— 业主口径是"横幅删掉、大标题删掉、只留一句介绍"`
      + '（.ks-page-sub）')
  }
}
const faceNavCheck = {
  checked: faceNavProblems.length === 0 && faceNavSkipReason === null,
  skipReason: faceNavSkipReason,
  problems: faceNavProblems,
  pages: faceM?.x ?? null,
  stripHeadSharedPage: faceM?.fs ?? null,
  headPageAncestors: faceM?.lh ?? null,
  kbRoots: faceM?.y ?? null,
  heads: faceM?.w ?? null,
  labels: faceM?.strip?.pad ?? null,
  on: faceM?.strip?.gap ?? null,
  headKids: faceM?.headKids ?? null,
}

/* ══════════ 新判据②（2026-09-23 接手批）：`.ks-list-cap` 那一行**不压字** ══════════
 * 业主报障的就是这一行：`导出效力总览` 压在 `知识库` 上、`在此范围内提问` 与刷新挤在一处。
 * 判据（**真重叠**才算压字；同时把"贴在一起"的间隙也报出来）：
 *   ① 这一行里可见成员两两的**边框盒**不许相交（ox>0.5 且 oy>0.5 ⇒ 红）；
 *   ② 相邻成员的**水平间隙**必须 ≥ LISTCAP_MIN_GAP（改前实测：`导出效力总览` 与 `知识库`
 *      之间 **0px** —— 两个东西贴成一个词，用户读不出这是两件事）。
 * ⚠ 适用面：**只有** `.ks-list-cap` 真的在 DOM 里时才判（它是 manage 面目录层那一行）；
 *   没有它 ⇒ 明说没判（skipReason），不静默通过。 */
const LISTCAP_MIN_GAP = 4
const listCapProblems = []
let listCapSkipReason = null
const lc = measured['#listcap']
if (lc === undefined) {
  listCapSkipReason = `这一跑没有 .ks-list-cap（page=${page} navPage=${navPage}）—— 这一行不适用`
} else {
  if (!Number.isFinite(Number(lc.n)) || Number(lc.n) < 2) {
    listCapProblems.push(`这一行里只量到 ${String(lc.n)} 个可见成员 —— 量不到成员就不算验过`
      + '（这一行本来就该有"文件夹名 + 导出 + 提问 + 计数"好几件东西）')
  }
  for (const o of (Array.isArray(lc.overlaps) ? lc.overlaps : [])) {
    listCapProblems.push(`**两个可见成员在压字**：${o.a} 与 ${o.b} 的边框盒真重叠`
      + `（水平 ${String(o.ox)}px × 垂直 ${String(o.oy)}px）`)
  }
  for (const g of (Array.isArray(lc.gaps) ? lc.gaps : [])) {
    if (Number(g.gap) < LISTCAP_MIN_GAP) {
      listCapProblems.push(`相邻成员贴在一起（水平间隙 ${String(g.gap)}px < ${String(LISTCAP_MIN_GAP)}px）：`
        + `${g.left} 与 ${g.right} —— 两个东西贴成一个词，用户读不出这是两件事`)
    }
  }
}
const listCapCheck = {
  checked: listCapProblems.length === 0 && listCapSkipReason === null,
  skipReason: listCapSkipReason,
  problems: listCapProblems,
  minGap: LISTCAP_MIN_GAP,
  members: lc?.members ?? null,
  gaps: lc?.gaps ?? null,
  overlaps: lc?.overlaps ?? null,
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
  dirColsCheck,
  stageColCheck,
  inboxCheck,
  askCheck,
  rowCtrlsCheck,
  dirHeadCheck,
  levelCheck,
  faceNavCheck,
  listCapCheck,
  capCardsCheck,
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

/* `#kbtree` / `#levelrows` 的自检结论同样走 **stderr**（理由同上：stdout 必须是完整可 JSON.parse 的产物）。
   ⚠ 这一条**取代**了 5i 起的 `#kbcards`（卡片尺寸统一）—— 卡片带已被业主删掉；判据与来历见
   上面 `levelCheck` 那段注释（"报告值必须有断言兜着"的教训原样搬了过来）。 */
if (levelSkipReason !== null) {
  console.error(`· #kbtree/#levelrows 自检：**这一跑不判**（${levelSkipReason}）`)
} else if (levelProblems.length === 0) {
  console.error(`· #kbtree/#levelrows 自检通过：左列右缘 ${String(levelCheck.treeRight)}px ≤ 右栏左缘 `
    + `${String(levelCheck.mainLeft)}px（左列 ${String(levelCheck.treeWidth)}px / 右栏 ${String(levelCheck.mainWidth)}px）；`
    + (levelCheck.rowHeightJudged
      ? `目录行高 ${String(levelCheck.dirRowH)}px = 文件行高 ${String(levelCheck.fileRowH)}px`
      : '两层行高这一条**这一跑没对象**（没有"目录行 + 文件行"同时在的层级）')
    + `（${String(levelCheck.dirRows)} 目录行 / ${String(levelCheck.fileRows)} 文件行；`
    + `page=${page} width=${width} theme=${themeName}）`)
} else {
  console.error('')
  console.error(`❌ 知识库页几何自检失败（左列并排 + 目录/文件两层行高一致；page=${page} width=${width} theme=${themeName}）：`)
  for (const p of levelProblems) console.error(`   - ${p}`)
  console.error('   ⇒ 左列宽/主栏最小宽在 ksGuideStyles.ts 的 `.ks-kb-tree{flex:0 0 168px...}` 与')
  console.error('      `.ks-main{flex:1 1 320px;min-width:260px...}`（168 + 8 + 260 = 436 < 488 = 520 − 2×16）。')
  console.error('   ⇒ 两层行高都吃 `.ks-item{min-height:var(--ks-row-h-list)}` 这一个 token；')
  console.error('      给目录行另钉行高（或让它不吃 .ks-item）就是这条断言要抓的回归。')
  process.exit(1)
}

/* `#capcards` 的自检结论同样走 **stderr**（理由同上：stdout 必须是完整可 JSON.parse 的一份产物）。 */
if (capCardsSkipReason !== null) {
  console.error(`· #capcards 自检：**这一跑不判**（${capCardsSkipReason}）`)
} else if (capCardsProblems.length === 0) {
  console.error(`· #capcards 自检通过：${String(capCardsCheck.count)} 行菜单**等高** ${JSON.stringify(capCardsCheck.heights)}、`
    + `（page=${page} width=${width} theme=${themeName}）`)
} else {
  console.error('')
  console.error(`❌ 办事台菜单行几何自检失败（全部行等高；page=${page} width=${width} theme=${themeName}）：`)
  for (const p of capCardsProblems) console.error(`   - ${p}`)
  console.error('   ⇒ 口径（2026-09-22 v3）：菜单行**全部等高**（v3 核心不变式）——')
  console.error('      只判 ① 所有 .ks-off-row 等高 ② 至少 2 行（防退化恒真） ③ 量到 0 行即红。')
  console.error('      行宽铺满容器（100%）；行高的唯一所有者是 KsOfficeRow 的固定行高。')
  console.error('      改成参差行高（或探针认错 selector）就是这条要抓的回归。')
  process.exit(1)
}

/* `#dircols` 的自检结论同样走 **stderr**（理由同上：stdout 必须是完整可 JSON.parse 的一份产物）。
   ⚠ 这一条的来历见上面 `#dircols` 那段注释：复核 `verify-freeze-dirlist` 的变异 M5 证明
   "目录层有没有自己的列模板"在真 Chrome 里**没有任何判据**（把文件层那 5 列接上去照样全绿）。
   现在它是一条**会红**的判据：轨道数必须 3、轨道和 + gap 必须铺满容器（差 >1px 即红）。 */
if (dirColsProblemsShared.length > 0) {
  /* ⚠ R1：**共享守卫优先**（它们与"这一跑有没有目录层"无关）—— 不许被 skipReason 吞掉。 */
  console.error('')
  console.error(`❌ 目录层的**全局守卫**失败（page=${page} width=${width} theme=${themeName}；`
    + '与这一跑有没有目录层无关）：')
  for (const p of dirColsProblemsShared) console.error(`   - ${p}`)
  process.exit(1)
} else if (dirColsSkipReason !== null) {
  console.error(`· #dircols 自检：**这一跑不判**（${dirColsSkipReason}）`)
} else if (dirColsProblems.length === 0) {
  console.error(`· #dircols 自检通过：目录层 ${String(dirColsCheck.tracks)} 轨 `
    + `${JSON.stringify(dirColsCheck.template)}，铺满容器 ${String(dirColsCheck.containerWidth)}px`
    + `（gap ${String(dirColsCheck.gap)}px；page=${page} width=${width} theme=${themeName}）`)
} else {
  console.error('')
  console.error(`❌ 目录层列几何自检失败（page=${page} width=${width} theme=${themeName}）：`)
  for (const p of dirColsProblems) console.error(`   - ${p}`)
  console.error('   ⇒ 目录层**只用自己那一条** --ks-cols（4 轨：勾选 / 目录 / 篇数 / ⋮）：')
  console.error('      ksGuideStyles.ts 的 `.ks-list-dirs{--ks-col-dpick:32px;--ks-col-dcount:64px;')
  console.error('      --ks-col-dmore:28px; --ks-cols:var(--ks-col-dpick) minmax(0,1fr)')
  console.error('      var(--ks-col-dcount) var(--ks-col-dmore)}`。')
  console.error('      接到文件层那条（fpick/name/status/date/stage/more）或写成固定宽，就是这条要抓的回归。')
  process.exit(1)
}

/* `#stagecol` 的自检结论同样走 **stderr**（理由同上：stdout 必须是完整可 JSON.parse 的一份产物）。
   ⚠ 这一条的来历见上面 `#stagecol` 那段注释：把 `@container` 阈值改成 99999px ⇒ 处理状态列
   在任何宽度都藏着，而四条 KB 冒烟**全绿** —— 业主"所有文件都要显示处理状态"原本没有判据。 */
if (stageColSkipReason !== null) {
  console.error(`· #stagecol 自检：**这一跑不判**（${stageColSkipReason}）`)
} else if (stageColProblems.length === 0) {
  console.error(`· #stagecol 自检通过：主栏 ${String(stageColCheck.mainWidth)}px`
    + `（阈值 ${String(stageColCheck.frozenMin)}px）下「${String(stageColCheck.head)}」列 `
    + `display=${JSON.stringify(stageColCheck.stageDisplay)} / 生效日期 ${JSON.stringify(stageColCheck.dateDisplay)}`
    + `（${String(stageColCheck.rows)} 行；page=${page} width=${width} theme=${themeName}）`)
} else {
  console.error('')
  console.error(`❌ 处理状态列可见性自检失败（page=${page} width=${width} theme=${themeName}）：`)
  for (const p of stageColProblems) console.error(`   - ${p}`)
  console.error('   ⇒ 口径：ksGuideStyles.ts 的 `.ks-list{--ks-cols:…3 轨…}`（窄档）与')
  console.error('      `@container (min-width:660px){…5 轨 + 这两列 display:flex}`（宽档）；')
  console.error('      窄档两条 `display:none` 必须写在 @container **之前**（同权重靠顺序覆盖）。')
  process.exit(1)
}

/* `#inboxcols` 的自检结论同样走 **stderr**（第 4 步：「待分类」层的列几何 + 状态列可见性）。 */
if (inboxSkipReason !== null) {
  console.error(`· #inboxcols 自检：**这一跑不判**（${inboxSkipReason}）`)
} else if (inboxProblems.length === 0) {
  console.error(`· #inboxcols 自检通过：待分类层 ${String(inboxCheck.rows)} 行、${String(inboxCheck.tracks)} 轨、`
    + `表头=行=${JSON.stringify(inboxCheck.header)}；状态列「${String(inboxCheck.stageHead)}」`
    + `display=${JSON.stringify(inboxCheck.stageDisplay)}、建议去向 display=${JSON.stringify(inboxCheck.destDisplay)}`
    + `（主栏 ${String(inboxCheck.mainWidth)}px、批量条 ${String(inboxCheck.batchN)} 条；`
    + `page=${page} width=${width} theme=${themeName}）`)
} else {
  console.error('')
  console.error(`❌ 待分类层几何/可见性自检失败（page=${page} width=${width} theme=${themeName}）：`)
  for (const p of inboxProblems) console.error(`   - ${p}`)
  console.error('   ⇒ 列模板：ksGuideStyles.ts 的 `.ks-list-inbox{--ks-cols:…5 轨…}`（窄档 4 轨 +')
  console.error('      窄档 `.ks-list .ks-cell.ks-col-idest{display:none}`，宽档 @container 660 恢复）。')
  console.error('   ⇒ **状态列永远可见**是业主的硬要求（"所有文件都要显示处理状态"）；')
  console.error('      窄档能藏的只有「建议去向」。改这一列就是这条断言要抓的回归。')
  process.exit(1)
}

/* `#ask` 的自检结论同样走 **stderr**（第 6 步：范围提问的入口 / chip / 面板**看不看得见**）。 */
if (askSkipReason !== null) {
  console.error(`· #ask 自检：**这一跑不判**（${askSkipReason}）`)
} else if (askProblems.length === 0) {
  console.error(`· #ask 自检通过：入口按钮高 ${String(askCheck.buttonH)}px、`
    + `chip ${String(askCheck.chipH)}px（文字「${String(askCheck.chipText)}」）、`
    + `面板 ${String(askCheck.panelH)}px；chip 右缘溢出 ${String(askCheck.chipOverflowPx)}px`
    + `（同一行元素=${String(askCheck.chipRowSameAsButtonRow)}；`
    + `那一行右内边距 ${String(askCheck.pagePadRight)}px；page=${page} width=${width} theme=${themeName}）`)
} else {
  console.error('')
  console.error(`❌ 范围提问界面自检失败（第 6 步：业主「每一级都能在此范围内提问」；`
    + `page=${page} width=${width} theme=${themeName}）：`)
  for (const p of askProblems) console.error(`   - ${p}`)
  console.error('   ⇒ 入口 / chip / 面板都必须真的渲染出高度；chip 的名字那一格必须能收缩')
  console.error('      （ksGuideStyles.ts 的 .ks-ask-chip-name{min-width:0;text-overflow:ellipsis}），')
  console.error('      否则窄档里长目录名会把工具栏顶出右缘。')
  process.exit(1)
}

/* 复核打回 §④-C 补回来的两条（行内控件数 / 目录层表头格）—— 结论同样走 stderr。 */
if (rowCtrlsSkipReason !== null) {
  console.error(`· #rows 行内控件自检：**这一跑不判**（${rowCtrlsSkipReason}）`)
} else if (rowCtrlsProblems.length === 0) {
  console.error(`· #rows 行内控件自检通过：文件行 ${JSON.stringify(rowCtrlsCheck.counts)}`
    + ` / 待分类行 ${JSON.stringify(rowCtrlsCheck.inboxCounts)}`
    + ` / 目录行 ${JSON.stringify(rowCtrlsCheck.dirCounts)}`
    + `（上限 ${String(ROW_CTRLS_MAX)}，真控件选择器口径；page=${page} width=${width} theme=${themeName}）`)
} else {
  console.error('')
  console.error(`❌ 行内控件数自检失败（P1-1 验收口径；page=${page} width=${width} theme=${themeName}）：`)
  for (const p of rowCtrlsProblems) console.error(`   - ${p}`)
  process.exit(1)
}
if (dirHeadSkipReason !== null) {
  console.error(`· #dirhead 自检：**这一跑不判**（${dirHeadSkipReason}）`)
} else if (dirHeadProblems.length === 0) {
  console.error(`· #dirhead 自检通过：目录层 ${String(dirHeadCheck.cells)} 个表头格的 display 全是 flex`
    + `（page=${page} width=${width} theme=${themeName}）`)
} else {
  console.error('')
  console.error(`❌ 目录层表头格自检失败（旧第 29 条：「目录」只剩一个「目」那个坑；`
    + `page=${page} width=${width} theme=${themeName}）：`)
  for (const p of dirHeadProblems) console.error(`   - ${p}`)
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

/* 新判据①（2026-09-23 接手批）：四个面观感一致。 */
if (faceNavSkipReason !== null) {
  console.error(`· #face 自检：**这一跑不判**（${faceNavSkipReason}）`)
} else if (faceNavProblems.length === 0) {
  console.error(`· #face 自检通过：面 ${navPage}；.ks-page ${String(faceNavCheck.pages)} 个 / `
    + `.ks-kb ${String(faceNavCheck.kbRoots)} 个 / 页头 ${String(faceNavCheck.heads)} 个；`
    + `四枚标签 ${JSON.stringify(String(faceNavCheck.labels).split('|'))}，选中 `
    + `「${String(faceNavCheck.on)}」；页头里看得见的成员 `
    + `${JSON.stringify((faceNavCheck.headKids ?? []).filter((k) => k.shown === 1).map((k) => k.cls))}`
    + `（page=${page} width=${width} theme=${themeName}）`)
} else {
  console.error('')
  console.error(`❌ 四个面一致性自检失败（业主：「四个面行为一致、页头观感一致、不重叠不压字」；`
    + `page=${page} navPage=${navPage} width=${width} theme=${themeName}）：`)
  for (const p of faceNavProblems) console.error(`   - ${p}`)
  console.error('   ⇒ 四个面必须共用同一套骨架（.ks-page > .ks-kb > 标签条 + 页头 + 内容），'
    + '标签条恰好四枚且恰好一枚选中（选中那枚的文字 = 本面名）。')
  console.error('      办事台改前是 `.ks-page > .ks-page > .ks-kb`（多套一层外壳）—— 就是这条要抓的。')
  process.exit(1)
}

/* 新判据②（2026-09-23 接手批）：`.ks-list-cap` 那一行不压字。 */
if (listCapSkipReason !== null) {
  console.error(`· #listcap 自检：**这一跑不判**（${listCapSkipReason}）`)
} else if (listCapProblems.length === 0) {
  const minGap = (listCapCheck.gaps ?? []).reduce((a, g) => Math.min(a, Number(g.gap)), Infinity)
  console.error(`· #listcap 自检通过：这一行 ${String(listCapCheck.members.length)} 个可见成员、`
    + `两两无重叠，相邻最小水平间隙 ${String(Number.isFinite(minGap) ? minGap : '(只有一个成员)')}px`
    + `（下限 ${String(LISTCAP_MIN_GAP)}px）；成员 ${JSON.stringify(listCapCheck.members)}`
    + `（page=${page} width=${width} theme=${themeName}）`)
} else {
  console.error('')
  console.error(`❌ 「当前文件夹名」那一行压字自检失败（业主：「导出效力总览压在知识库上」；`
    + `page=${page} width=${width} theme=${themeName}）：`)
  for (const p of listCapProblems) console.error(`   - ${p}`)
  console.error('   ⇒ 这一行（.ks-list-cap）里的成员（文件夹名 / 导出效力总览 / 在此范围内提问 / 计数）'
    + '必须各自成件：既不许边框盒真重叠，也不许贴成 0px（两个东西贴成一个词）。')
  process.exit(1)
}

