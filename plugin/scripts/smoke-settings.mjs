/**
 * smoke-settings.mjs — 设置栏目渲染冒烟（诊断用）
 *
 * 用 esbuild 把 client/KsSettingsSection.tsx 打包成 node 可执行 ESM，再用
 * react-dom/server 做一次 SSR：渲染期抛错会直接打印堆栈。
 *
 * 断言（2026-11 迁移后升级为硬判据；2026-09-21 第 4 步复核后**补成有牙**）：
 *   1. **类目集合**（不是"点名 5 个"）：三份必须**逐字相等** ——
 *      ① **冻结清单** `EXPECTED_CATEGORIES`（脚本里，谁增删类目都要显式改它）；
 *      ② **源码机械抽出**（`KsSettingsSection.tsx` 里 `<KsCategory …>` 的 `title`）；
 *      ③ **SSR 真渲染出来的**（每个类目的 `<details data-ks-cat="…">`）。
 *      ⚠⚠ **2026-09-21 就打回 §2**：这条原来的写法是
 *      `for (const cat of ['证据查看器','效力报告','每日巡检','公告发现','API配置'])` ——
 *      复核实测它**没有牙**：源码里实际有 **7 组**类目，多出来的两个（参考资料 / 渠道台账）
 *      **一个都没被判**，"多一个未声明类目也会红"**不成立**。现在三份集合互比，多一个少一个都红。
 *   2. **那组只读"入库预览"的入口不许回来**（第 4 步撤掉它：导入只有一个落点 = 知识库页
 *      「待分类」层上的面板）。⚠ 原判据是 `html.includes('入库前只读体检')` ——
 *      **只认那句固定字符串**（复核按提示把入口加回去才红；改一个字就绕过去了）。
 *      现在判**结构性事实**：设置源码里**不许再出现 `KsIngestPanel`**（= 那个面板没被挂回来）。
 *      为什么必须判源码而不是 DOM：面板的 `visible=false` 时 SSR **什么都不渲染**
 *      （懒加载门那条），所以"挂回来了没有"在 HTML 里看不出来 —— 只能看源码。
 *      `入库预览` 这个名字若作为类目回来，也会被上面的类目集合判红（它不在冻结清单里）。
 *   3. 旧「打开效力报告」入口按钮不复存在；
 *   4. 全部 <details> 默认收起（SSR 初始树无 open 属性）；
 *   5. 懒加载门：SSR 期间（=所有面板 visible=false）零网络请求。
 *   6. **不弄脏仓库**：构建中间产物（`.smoke-settings-entry.jsx` / `.smoke-settings-bundle.mjs`）
 *      在退出时**同步清理**（含所有 `process.exit(1)` 分支）—— 见下面 `cleanupArtifacts` 那段。
 *
 * 注：组件用了 useSyncExternalStore（浏览器专有第三参），SSR 前把 react 的
 * CJS 对象上的实现包一层 getServerSnapshot 兜底，让 SSR 能继续暴露其它渲染错误。
 *
 * 用法：node scripts/smoke-settings.mjs
 */
import { build } from 'esbuild'
import { rmSync } from 'node:fs'
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

import {
  HOST_PRIMITIVES_SPECIFIER,
  ksClientPrimitivesAlias,
  primitivesStubGaps,
  stubExportNames,
} from './lib/ks-primitives-stub.mjs'

const here = dirname(fileURLToPath(import.meta.url))
const pluginRoot = resolve(here, '..')

/* ⚠⚠ **2026-09-21（第 4 步复核打回 §2）入口改成"只测量、不判红、不自己 exit"**：
   原来这段在失败分支里直接 `process.exit(1)` ＋ 只打印被人读的行；而"类目集合"要
   **三份互比**（冻结清单 / 源码抽出 / SSR 渲染），比较必须在**能读到三份**的地方做
   ⇒ 现在 entry 只导出一个 `RESULT`（渲染出来的类目 + 三个渲染期事实），
   判红与诊断全部回到 runner（那里同时有源码文本、冻结清单与结果）。 */
const entry = `
import { createRequire } from 'node:module'
import { KsSettingsSection } from './client/KsSettingsSection.tsx'

const require = createRequire(import.meta.url)
const React = require('react')
const { renderToString } = require('react-dom/server')

const _orig = React.useSyncExternalStore
React.useSyncExternalStore = (sub, get, getServer) => _orig(sub, get, getServer ?? get)

const service = {
  getSnapshot: () => ({ prefs: { pluginSettings: { 'ks:settings': { showArrow: true } } } }),
  subscribeState: () => () => {},
  openTab: () => {},
  updateTab: () => {},
}

// 请求门自证：SSR 期间面板 visible=false，任何 /ks/* 或 sidebar 请求都是缺陷
// （details 收起零请求契约——挂载但零网络活动）。
const fetched = []
globalThis.fetch = (input, init) => {
  const url = String(typeof input === 'string' ? input : (input && input.url) || input)
  fetched.push(url)
  return Promise.reject(new Error('SSR 阶段不应发起任何请求: ' + url))
}

export let RESULT = null
try {
  const html = renderToString(React.createElement(KsSettingsSection, { service }))
  RESULT = {
    ok: true,
    htmlLen: html.length,
    // 类目集合：data-ks-cat（机械抽出，不猜文案）
    categories: [...html.matchAll(/data-ks-cat="([^"]*)"/g)].map((m) => m[1]),
    detailsCount: (html.match(/<details/g) ?? []).length,
    staleEntryButton: html.includes('打开效力报告'),
    unfolded: /<details[^>]+open/.test(html),
    fetched: fetched.slice(),
  }
} catch (e) {
  RESULT = { ok: false, error: (e && e.stack ? e.stack : String(e)) }
}
`

const dir = await mkdtemp(join(tmpdir(), 'ks-smoke-'))
// ⚠ **宿主 ui-primitives 必须 alias 到一个桩**（2026-09-20 的真红）：
//   本冒烟原来只写 `external: ['react','react-dom/server']` ⇒ 组件里一旦新增宿主组件的 import
//   （5c 把 `KsIngestPanel` 的按钮换成宿主 `Button`）就会 `X [ERROR] Could not resolve
//   "@deepseek-ai/dsh-client-ui-primitives"` ⇒ **整个 `-Full` 的 smoke 步红**。
// ⚠ **名单不再手写**（手写名单是同一根因的第三次红）：桩由
//   `scripts/lib/ks-primitives-stub.mjs` **从 `plugin/client/**` 派生** ⇒
//   **加宿主组件只改源码，本文件一行都不用动**。
const primitivesAlias = ksClientPrimitivesAlias(pluginRoot, dir)
const primitivesStubPath = primitivesAlias[HOST_PRIMITIVES_SPECIFIER]

/* ── 防复发断言（本条是**最便宜**的那道网；lib 头部写着这条不变量）──────────────
 * 判据：**桩的导出集合 ⊇ 源码里实际具名导入的集合**。缺谁就**点名谁**。
 * 为什么放在这里：它只读文件、不构建，是**最先**能发现"桩漏了"的位置——
 *   三次红的现场都是 esbuild 的 `No matching export …`（不提"该往哪儿加"），
 *   或者更早的 `Could not resolve`（连桩都没接上）。 */
{
  const stubSource = await readFile(primitivesStubPath, 'utf8')
  const gaps = primitivesStubGaps(pluginRoot, stubSource)
  console.log(`${gaps.length === 0 ? 'PASS' : 'FAIL'}  宿主原语桩覆盖源码里全部具名导入`
    + `（${stubExportNames(stubSource).length} 个成员；加宿主组件只需改 plugin/client/**，不必改冒烟）`
    + (gaps.length === 0 ? '' : ` — 桩缺：${gaps.join(', ')}`))
  if (gaps.length > 0) {
    console.error('STUB_GAP: 桩漏了源码真的 import 的宿主成员 ⇒ esbuild 会报 No matching export。')
    process.exit(1)
  }
}
// 入口必须落在 plugin 目录内：相对 import 与 node_modules 解析（react 在仓库根）
// 都按入口所在目录向上查找——放临时目录会导致三者全部解析失败。
const entryPath = join(pluginRoot, '.smoke-settings-entry.jsx')
const outPath = join(pluginRoot, '.smoke-settings-bundle.mjs')
/* ⚠⚠ **2026-09-21（第 4 步复核打回 §3）：这两个构建中间产物写在 plugin/ 里，必须保证清掉。**
   复核实测：冒烟一红就在仓里留下 **171KB 未跟踪产物** `.smoke-settings-bundle.mjs`（`git status` 变脏）。
   根因：`entry` 里的每个失败分支都是 `process.exit(1)` ⇒ **进程直接走人**，
   末尾那句 `await rm(outPath)` 根本不会执行（只有全绿那一趟才清）。
   ⇒ 修法：清理挂到 `process.on('exit')`（**同步** `rmSync`；`process.exit()` 也会走到它），
     并在**开跑前**先清一次（上一跑被强杀留下的，这一跑自带自愈）。
   ⚠ 为什么**不**用 `.gitignore`（两条路选一条，这是理由）：`.gitignore` 会让"真留下了垃圾"
     变成 `git status` **看不见** —— 本仓的纪律是"别把问题藏进配置里、让它在现场可见"
     （同"量不到就必须判红"）。强杀（SIGKILL / 超时）时 exit 钩子来不及跑，
     那时文件**留在工作树里被看见**，那是诚实的结果，不是要掩盖的事故。 */
const cleanupArtifacts = () => {
  for (const p of [entryPath, outPath]) {
    try { rmSync(p, { force: true }) } catch { /* 清不掉就让它留着（可见） */ }
  }
}
process.on('exit', cleanupArtifacts)
cleanupArtifacts()                       // 上一跑被强杀留下的，先清

/* ── 类目集合：两边**机械抽出** + 一份冻结清单 ────────────────────────────────
 * ① 冻结清单（本脚本的 EXPECTED_CATEGORIES）；
 * ② **源码侧**：`<KsCategory … title="X">` 的 title ∪ 源码里**字面**锚点 `data-ks-cat="Y"`
 *    （后者只可能是"不走 KsCategory 的那一组"，当前 = API配置）；
 * ③ **渲染侧**：SSR 真渲染出来的 `data-ks-cat="Y"`。
 * ②③① 三份必须逐字相等 —— **多一个少一个都红**。
 * ⚠ 为什么源码侧要两个来源：只数 `<KsCategory` 会**漏掉**不走它的那一组；
 *   只数字面锚点会**漏掉**新加的 KsCategory（它的锚点是 `{title}` 表达式，不是字面量）。
 *   两边一起收，两个方向就都堵上了（复核实测的三种变异见 §十九·补）。
 * ⚠ 原来还有一条"`<details>` 个数必须等于类目数"—— **删掉并说明为什么**：设置里
 *   **有嵌套 details**（公告/API 面板内部还有），实测渲染出来 9 个而类目 7 组 ⇒
 *   那条比的是两件不同的事，留着只会假红或假绿。它要防的"某组没带锚点"由上面的
 *   三份集合相等兜住（少一个锚点 = 渲染侧少一组 = 红）。
 * ⚠ "识别不了就点名"：`<KsCategory` 出现次数与抽出到的 title 数不一致 ⇒ 直接红，
 *   不静默少读（同 `ks-primitives-stub.mjs` 对无法静态枚举的写法直接抛错那条纪律）。 */
const EXPECTED_CATEGORIES = [
  '证据查看器', '效力报告', '参考资料', '渠道台账', '每日巡检', '公告发现', 'API配置',
]
const settingsSrcPath = join(pluginRoot, 'client', 'KsSettingsSection.tsx')
const settingsSrc = await readFile(settingsSrcPath, 'utf8')
const ksCatCount = (settingsSrc.match(/<KsCategory\b/g) ?? []).length
const ksCatTitles = [...settingsSrc.matchAll(/<KsCategory\b[^>]*?title="([^"]*)"/gs)]
  .map((m) => m[1])
if (ksCatCount !== ksCatTitles.length) {
  console.error(`CATEGORY_SCAN_FAIL: 源码里有 ${ksCatCount} 处 <KsCategory 却只抽出 `
    + `${ksCatTitles.length} 个 title="…" —— 有人换了写法（如 title={'…'}）⇒ `
    + '本冒烟的类目判据**识别不了**，按纪律当场红（不许静默少读）。')
  process.exit(1)
}
/** 源码里**字面**的类目锚点（`data-ks-cat={title}` 那种表达式不会被收到 —— 那是刻意的）。 */
const sourceLiteralAnchors = [...settingsSrc.matchAll(/data-ks-cat="([^"]*)"/g)].map((m) => m[1])
const sourceGroupTitles = [...new Set([...ksCatTitles, ...sourceLiteralAnchors])]

/* 入口文件写在这里（**注意顺序**：`cleanupArtifacts` 刚把上一次的残留清掉，
   现在才轮到写新的 —— 本批第一版把 `writeFile` 连同旧块一起删了，esbuild 当场报
   `Could not resolve .smoke-settings-entry.jsx`）。 */
await writeFile(entryPath, entry, 'utf8')

try {
  await build({
    entryPoints: [entryPath],
    bundle: true,
    platform: 'node',
    format: 'esm',
    outfile: outPath,
    absWorkingDir: pluginRoot,
    jsx: 'automatic',
    external: ['react', 'react-dom/server'],
    alias: { '@deepseek-ai/dsh-client-ui-primitives': primitivesStubPath },
    loader: { '.tsx': 'tsx', '.ts': 'ts' },
    logLevel: 'warning',
  })
} catch (err) {
  console.error('BUILD_FAIL: ' + (err && err.message ? err.message : String(err)))
  process.exit(1)
}
await rm(entryPath, { force: true })

const entryOut = await import(pathToFileURL(outPath).href)
await rm(outPath, { force: true })

const res = entryOut?.RESULT ?? null
if (res === null || res.ok !== true) {
  console.error('SSR_FAIL: ' + (res === null ? 'entry 没导出 RESULT' : String(res.error)))
  process.exit(1)
}
console.log('SSR_OK html_len=' + String(res.htmlLen))

/* ── 渲染期的三个事实（原 entry 里判的，现在回到 runner 判）── */
{
  const problems = []
  if (res.staleEntryButton) problems.push('旧入口按钮「打开效力报告」还在渲染')
  if (res.unfolded) problems.push('有 <details> 是**展开**的（类目必须默认收起）')
  if ((res.fetched ?? []).length > 0) {
    problems.push(`SSR 期间发起了请求：${(res.fetched ?? []).join(',')}（收起态必须零请求）`)
  }
  console.log(`${problems.length === 0 ? 'PASS' : 'FAIL'}  渲染期三个事实`
    + `（无旧入口按钮 / 全部收起 / SSR 零请求）`
    + (problems.length === 0 ? '' : ` — ${problems.join(' ｜ ')}`))
  if (problems.length > 0) process.exit(1)
}

/* ── 类目集合判据（三份互比；多一个少一个都红）────────────────────────────────
 * ⚠ 这份判据取代了原来那段"点名 5 个类目"（复核实测它没有牙：源码实际 7 组，
   多出来的「参考资料」「渠道台账」一个都没判）。原文留痕见本文件头部第 1 条。
 * ⚠ 也取代了 `html.includes('入库前只读体检')` 那条**只认固定字符串**的"不许回来"判据：
   现在分两处判 —— ① 「入库预览」若作为类目回来，会以"不在冻结清单里"的形态在这里红；
   ② 那个面板（`KsIngestPanel`）若被挂回设置，由下面的源码判据红。 */
{
  const rendered = Array.isArray(res.categories) ? res.categories : null
  const sort = (a) => [...a].sort()
  const same = (a, b) => JSON.stringify(sort(a)) === JSON.stringify(sort(b))
  const problems = []
  if (rendered === null) problems.push('拿不到 SSR 渲染出来的类目标题（entry 没报 categories）')
  if (rendered !== null && new Set(rendered).size !== rendered.length) {
    problems.push(`渲染出来的锚点有重复：${JSON.stringify(sort(rendered))}`)
  }
  if (rendered !== null && !same(sourceGroupTitles, rendered)) {
    problems.push(`源码抽出 ${JSON.stringify(sort(sourceGroupTitles))}（KsCategory ${String(ksCatTitles.length)} 个`
      + ` + 字面锚点 ${String(sourceLiteralAnchors.length)} 个）vs 渲染 ${JSON.stringify(sort(rendered))}`
      + ' —— 两边的差通常意味着**某一组少了 data-ks-cat 锚点**（那种组判不出来）')
  }
  if (rendered !== null && !same(rendered, EXPECTED_CATEGORIES)) {
    const only = sort(rendered).filter((x) => !EXPECTED_CATEGORIES.includes(x))
    const missing = EXPECTED_CATEGORIES.filter((x) => !rendered.includes(x))
    problems.push(`冻结清单 ${JSON.stringify(EXPECTED_CATEGORIES)} 与实际不符：`
      + `多出来=[${only.join(' ')}]、少了=[${missing.join(' ')}]`
      + '（加/删设置类目都要**显式**改本脚本的 EXPECTED_CATEGORIES）')
  }
  console.log(`${problems.length === 0 ? 'PASS' : 'FAIL'}  设置类目集合三份一致`
    + `（冻结清单 ${String(EXPECTED_CATEGORIES.length)} 组 / 源码抽出 ${String(sourceGroupTitles.length)} 组`
    + ` / SSR 渲染 ${rendered === null ? '(抽不到)' : String(rendered.length)} 组：`
    + `${JSON.stringify(sort(rendered ?? []))}）`
    + (problems.length === 0 ? '' : ` — ${problems.join(' ｜ ')}`))
  if (problems.length > 0) {
    console.error('CATEGORY_SET_MISMATCH: ' + problems.join(' ｜ '))
    process.exit(1)
  }
}

/* ── "那组只读体检面板"不许挂回设置（第 4 步的裁定）──────────────────────────
 * 判据：设置**源码的代码**里不许出现 `KsIngestPanel`（import 或 JSX 都算）。
 * 为什么判源码而不是 DOM：面板 `visible=false` 时 SSR **什么都不渲染**（上面那条懒加载门
 * 正是这么写的）⇒ "挂回来了没有"在 HTML 里根本看不出来。
 * ⚠⚠ **必须先剥注释再判**（本批第一版没剥，当场假红）：撤掉入口时我在代码旁边留了一段
 * **留痕注释**（写明"KsIngestPanel.tsx 本身留在仓里…"）⇒ 朴素 grep 把**散文**判成了
 * "面板挂回来了"。同 `smoke-client-entry.mjs` 那条"判据要判代码、不判散文"的既有纪律。
 * 代价（照抄那条的诚实边界）：字符串里的 `//` 会被当注释切掉 ⇒ 轻微少计；
 * 而"把面板挂回去"只能发生在**代码**里（JSX/import），不会藏在字符串里，所以少计不伤本判据。
 * 原文（复核打回 §2 指出的"只认固定字符串"）：`if (html.includes('入库前只读体检'))` ——
 * 改一个字（甚至只改 hint 文案）就绕过去了。 */
{
  const stripComments = (s) => s.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/[^\n]*/g, '')
  const settingsCode = stripComments(settingsSrc)
  const hit = /KsIngestPanel/.test(settingsCode)
  const rawMentions = (settingsSrc.match(/KsIngestPanel/g) ?? []).length
  const codeMentions = (settingsCode.match(/KsIngestPanel/g) ?? []).length
  console.log(`${hit ? 'FAIL' : 'PASS'}  设置里没有挂回那组"只读体检"面板`
    + `（**代码**里 ${String(codeMentions)} 处 KsIngestPanel；原文 ${String(rawMentions)} 处，`
    + `差额 ${String(rawMentions - codeMentions)} 处在注释里=留痕文字，不算）`)
  if (hit) {
    console.error('STALE_INGEST_ENTRY: 设置的**代码**里又出现了 KsIngestPanel —— '
      + '第 4 步的裁定是"导入只有一个落点"（知识库页『待分类』层上的面板）。'
      + '真要复活这个入口，必须**同时**说明为什么两个落点是对的、并改这一条判据。')
    process.exit(1)
  }
}
