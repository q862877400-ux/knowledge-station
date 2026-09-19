/**
 * ks-dsh-plugin — scripts/smoke-build-purity.mjs
 *
 * 守住"**构建纯度**"（2026-09-19，DSH 适配积压第 4 条）：`@deepseek-ai/*` **不许整片 external**。
 *
 * 三条判据（每条都能证伪）：
 *  1. **允许清单 = 官方基线单例 ∪ 我们自己 inject 的模块**，且**必须与 `package.json` 一致**
 *     （对着真文件读，不抄常量 —— 两边漂移正是这类门禁最容易烂掉的地方）；
 *  2. 认识的 `@deepseek-ai/<pkg>`（含子路径）⇒ `external`；`react`/`react-dom`（含子路径）⇒ `external`；
 *  3. **不认识的 `@deepseek-ai/*` ⇒ 抛**（构建期炸，而不是运行时）；而**看着像但不是**的 scope
 *     （`@deepseek-ai-evil/x`）与第三方包（`pdfjs-dist`）⇒ `bundle`（打进去）。
 *  4. **归一化绕过 ⇒ 抛**（2026-09-20 第三轮补）：`@deepseek-ai//x`（重复斜杠）、`@DeepSeek-AI/x`
 *     （大小写）、`x/../@deepseek-ai/x`（`..` 段，复核 r2 真构建复现 +6785B 静默内联）都必须当场抛 ——
 *     因为 esbuild 会归一化后**解析到盘上真包**。反面对照：`x/../lodash` 这类第三方包**不该**受门禁影响。
 *     同时钉住 `build-client.mjs` 的 onResolve 用的是**共享常量**（filter 与判定各写一份，
 *     正是 `x/../…` 那次的另一半原因）。
 *  5. **相对/绝对路径指向宿主单例 ⇒ 抛**（2026-09-20 第四轮补，复核 corr3 A1 —— 改前的**真空洞**）：
 *     `./../node_modules/@deepseek-ai/<pkg>/lib/index.js` / `../node_modules/…` **有门禁时照样 BUILT**
 *     （metafile 实测 7377B / 1068B，input 就是宿主单例）。
 *  6. ⚠⚠ **第五轮（2026-09-20）—— 第 5 条只修了"冒烟里那两条写法"**：独立复核用 esbuild JS API +
 *     `metafile` + 内容标记实测，**8 条变体仍把宿主单例静默内联**（本文件现在逐条钉住，见 2b）：
 *     `x/../../node_modules/…`、`a/b/../../../node_modules/…`、`x/../../node_modules/react/…`、
 *     `../NODE_M~1/…`（8.3 短名）、`../node_modules./…`（尾随点）、`./dsh-util-values/…`（junction）、
 *     `./node_modules/react/…`、绝对路径到 `node_modules/react/…`。三条根因：
 *       (i) `x/../../…` 被当成**包名**（`bare`）⇒ 落点检查那一支根本不跑；
 *       (ii) 落点判据是对**字面 `node_modules`** 的正则 ⇒ 8.3 短名 / 尾随点漏；
 *       (iii) **filter 比判定窄** ⇒ `./node_modules/react/index.js` 连 onResolve 都不触发。
 *     ⇒ **改法：不再看文本，让 esbuild 自己解析**（`build.resolve(path, { resolveDir, importer,
 *     kind, namespace, pluginData })`），拿**真实解析路径 + `realpathSync`** 判落点；
 *     filter 放宽到"含分隔符/相对前缀/绝对路径/短名/我们的 scope/react"。
 *     ⚠ `build.resolve` 从 onResolve 里调会因为**同参数重入**而无限递归（esbuild 文档明说它不做
 *     循环检测）⇒ 用 `pluginData` 打标记，重入即放手（实测递归终止在第二层）。
 *
 * 另有一条**产物级**佐证：现构建的产物里出现的每个 `@deepseek-ai/...` 都必须真的在清单里
 * （用 `KS_CLIENT_OUT` 构建到临时文件，不覆盖被跟踪的 `client.js`）。
 *
 * Run:  node scripts/smoke-build-purity.mjs   (exit 0 = pass)
 */
import { mkdirSync, mkdtempSync, rmSync, rmdirSync, writeFileSync, existsSync, symlinkSync } from 'node:fs'
import { mkdtemp, readFile, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { spawnSync } from 'node:child_process'

import {
  ALLOWED_DEEPSEEK_MODULES,
  DSH_BASELINE_MODULES,
  PLUGIN_INJECT_MODULES,
  PURITY_ONRESOLVE_FILTER,
  classifyExternal,
  purityPlugin,
} from './lib/external-allowlist.mjs'

const results = []
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}

console.log('=== ks-dsh-plugin build-purity smoke ===\n')

// ── 1) 清单与 package.json 一致（**读真文件**，不抄常量） ────────────────────────
const pkg = JSON.parse(await readFile(new URL('../package.json', import.meta.url), 'utf8'))
const declared = [...(pkg.dsh?.client?.inject ?? [])].sort()
const mirrored = [...PLUGIN_INJECT_MODULES].sort()
check('清单镜像与 package.json 的 dsh.client.inject 一致（漂移即红）',
  JSON.stringify(declared) === JSON.stringify(mirrored),
  `pkg=${declared.length} 条 / 清单=${mirrored.length} 条`)
check('官方基线 5 个模块都在允许清单里（出处 seed.ts）',
  DSH_BASELINE_MODULES.every((m) => ALLOWED_DEEPSEEK_MODULES.has(m)),
  DSH_BASELINE_MODULES.join(', '))

// ── 2) 分类判定 ────────────────────────────────────────────────────────────────
for (const spec of [...ALLOWED_DEEPSEEK_MODULES, 'react', 'react-dom', 'react/jsx-runtime',
  'react-dom/client', '@deepseek-ai/dsh-client-ui-slots/sub/path']) {
  let v = null
  try { v = classifyExternal(spec) } catch (e) { v = `THREW: ${e.message.slice(0, 40)}` }
  check(`external：${spec}`, v === 'external', String(v))
}
for (const spec of ['pdfjs-dist', 'pdfjs-dist/build/pdf.mjs', 'lodash', '@deepseek-ai-evil/x']) {
  let v = null
  try { v = classifyExternal(spec) } catch (e) { v = `THREW: ${e.message.slice(0, 40)}` }
  check(`bundle：${spec}（不是宿主提供的）`, v === 'bundle', String(v))
}
{
  let msg = null
  try { classifyExternal('@deepseek-ai/definitely-not-a-real-package') } catch (e) { msg = e.message }
  check('不认识的 @deepseek-ai/* ⇒ **抛**（纯度门禁的核心）', msg !== null, (msg ?? '').slice(0, 60))
}
// ⚠ **大小写变体**（复核 2026-09-20 的对抗性发现，2026-09-20 修）：scope 判定原来大小写敏感，
//   于是 `@DeepSeek-AI/x` 被判 `bundle` —— 今天恰好 fail-closed（解析不到），但 Windows 不区分大小写，
//   盘上真有那个包时**宿主单例会被静默打进产物**。现在两种变体都必须**当场抛**。
for (const spec of ['@DeepSeek-AI/dsh-client-ui-slots', '@DeepSeek-AI/whatever-new-package',
  '@deepseek-AI/dsh-client-runtime', '@DeepSeek-ai/react-probe']) {
  let msg = null
  try { classifyExternal(spec) } catch (e) { msg = e.message }
  check(`大小写变体 ⇒ **抛**（不许静默当 bundle）：${spec}`, msg !== null, (msg ?? 'NOT-THREW').slice(0, 60))
}
// ⚠ 同一条纪律的反面：**大小写正确**的清单内模块仍然照常 external（别把门禁做成"全都抛"）。
{
  let v = null
  try { v = classifyExternal('@deepseek-ai/dsh-client-ui-slots') } catch (e) { v = `THREW: ${e.message.slice(0, 30)}` }
  check('反例对照：全小写的清单内模块仍 external（门禁没有变成一律拒绝）', v === 'external', String(v))
}
// ⚠ **分隔符绕过**（复核 2026-09-20 第二轮的对抗性发现，2026-09-20 修）：`@deepseek-ai//x` 与
//   `@deepseek-ai\x` 都不是规范写法，但 esbuild 会归一化后**解析到盘上真包并静默打进产物**
//   （复核实跑 BUILT 三个真包）⇒ 必须当场抛，而不是判 bundle。
//   ⚠ **第三轮更正（复核 r2 + 本轮自己实测，写在前面免得被误读）**：反斜杠那条的后果**依平台**——
//   本机（Windows）esbuild 把 `\` 也当路径分隔符，metafile 实测 `@deepseek-ai\dsh-util-values`
//   解析到 `node_modules/@deepseek-ai/dsh-util-values/lib/index.js`（产物 6946B）；r2 报的
//   `Could not resolve` 针对的是**包名不存在**的 `@deepseek-ai\x`。⇒ 不能说"`//` 会、`\` 不会"，
//   正确的说法是"**不在 Linux 上赌**：本平台 `\` 照样解析，所以照样拒"。
for (const spec of ['@deepseek-ai//dsh-client-ui-slots', '@deepseek-ai\\dsh-client-ui-slots',
  '@deepseek-ai//dsh-util-values', '@deepseek-ai\\dsh-util-crypto',
  '@deepseek-ai///whatever', '@DeepSeek-AI\\\\dsh-client-runtime']) {
  let msg = null
  try { classifyExternal(spec) } catch (e) { msg = e.message }
  check(`分隔符不规范 ⇒ **抛**（不许静默当 bundle）：${spec}`, msg !== null, (msg ?? 'NOT-THREW').slice(0, 60))
}
// ⚠ **`..` 归一化绕过**（复核 r2 2026-09-20 第三轮，**真构建复现**）：`x/../@deepseek-ai/<pkg>`
//   被 esbuild 归一化后解析到盘上真包、**静默内联**（复核实跑 +6785B）。旧判定只在"**以 `@` 开头**"
//   的串上认 scope（正则锚 `^@`）⇒ 连 scope 都没认出来，判 `bundle`。现在判定建立在**归一化后的
//   整串**上 ⇒ 必须当场抛。连同 filter 一起改（filter 原来也锚在串首，压根不触发）。
for (const spec of ['x/../@deepseek-ai/dsh-util-values', 'x/../@deepseek-ai/dsh-client-ui-slots',
  'x/../../x/../@deepseek-ai/dsh-util-crypto', 'x/..\\@deepseek-ai/dsh-util-values',
  'x/../@DeepSeek-AI/dsh-client-runtime']) {
  let msg = null
  try { classifyExternal(spec) } catch (e) { msg = e.message }
  check(`\`..\` 归一化后落进我们 scope ⇒ **抛**：${spec}`, msg !== null, (msg ?? 'NOT-THREW').slice(0, 60))
}
// 对照：**第三方包**经 `..` 归一化后**不该**受我们的门禁影响（门禁只认我们的 scope，不是"见 `..` 就拒"）。
for (const spec of ['x/../lodash', 'x/../pdfjs-dist/build/pdf.mjs', 'x/../@deepseek-ai-evil/x']) {
  let v = null
  try { v = classifyExternal(spec) } catch (e) { v = `THREW: ${e.message.slice(0, 40)}` }
  check(`bundle（门禁不越界）：${spec}`, v === 'bundle', String(v))
}
// ⚠ **filter 与判定必须同源**：上一轮 `x/../...` 之所以能绕过去，一半原因是 onResolve 的 filter
//   锚在串首、**根本没触发**。⇒ 钉住"build-client 用的是共享工厂"，别让谁再各写一份 filter。
//   ⚠ **第四轮（复核 corr3 A1）**：接线本身就是**第三处**会漏的地方 —— 工厂里少传一个
//   `args.resolveDir`，相对路径那条洞就回来了。所以判定/filter/**接线**现在同在一处
//   （`lib/external-allowlist.mjs` 的 `purityPlugin()`），这里钉"build-client 不许自己接线"。
{
  const buildSrc = await readFile(new URL('./build-client.mjs', import.meta.url), 'utf8')
  check('build-client 挂的是共享工厂 purityPlugin()（不许自己写 filter/接线）',
    /plugins:\s*\[\s*purityPlugin\(\)\s*\]/.test(buildSrc),
    'plugins: [purityPlugin()]')
  check('build-client 里没有第二份 filter/接线（不许自己写 onResolve/filter）',
    !/\bonResolve\s*\(/.test(buildSrc) && !/\bfilter\s*:/.test(buildSrc)
      && !/classifyExternal\s*\(/.test(buildSrc),
    'onResolve/filter/判定只在 lib 的 purityPlugin() 里')
  // ⚠ **第五轮（2026-09-20）：filter 又放宽了一次** —— 旧 filter 只认"文本里带 `@deepseek-ai` /
  //   `..` / `^react`"，于是 `./node_modules/react/index.js`（一个 `.` 段）**压根不触发 onResolve**，
  //   而 `classifyExternal` 本来认得出它（复核实测的三条根因之三）。现在"含分隔符/相对前缀/绝对路径/
  //   短名/我们的 scope/react"任何一条都命中。这里把**第五轮的 8 条变体全量**钉一遍。
  const filterMustHit = ['x/../@deepseek-ai/dsh-util-values', '@deepseek-ai//dsh-util-values',
    '@DeepSeek-AI/x', 'x/../react', 'react', 'react-dom', 'react/jsx-runtime',
    '../node_modules/@deepseek-ai/dsh-util-values/lib/index.js',
    'x/../../node_modules/@deepseek-ai/dsh-util-values/lib/index.js',
    'a/b/../../../node_modules/@deepseek-ai/dsh-util-values/lib/index.js',
    'x/../../node_modules/react/index.js',
    '../NODE_M~1/@deepseek-ai/dsh-util-values/lib/index.js',
    '../node_modules./@deepseek-ai/dsh-util-values/lib/index.js',
    './dsh-util-values/lib/index.js',
    './node_modules/react/index.js',
    'D:\\x\\node_modules\\react\\index.js',
    './vendor/legit.js']
  const filterMissed = filterMustHit.filter((s) => !PURITY_ONRESOLVE_FILTER.test(s))
  check('共享 filter 命中归一化/分隔符/大小写/相对/绝对/短名/尾随点/junction 八类写法',
    filterMissed.length === 0,
    filterMissed.length ? `漏：${filterMissed.join(' · ')}` : `${filterMustHit.length} 条全命中`)
}
// 对照：**子路径**里的正常斜杠当然要放过（别把合法写法一起拒了）。
{
  let v = null
  try { v = classifyExternal('@deepseek-ai/dsh-client-ui-slots/sub/path') } catch (e) { v = `THREW: ${e.message.slice(0, 30)}` }
  check('反例对照：清单内模块的正常子路径仍 external', v === 'external', String(v))
}

// ── 2b) 相对/绝对/短名/尾随点/junction 指向宿主单例 ⇒ 拦（**第五轮 2026-09-20 从根上改**）────
//   第四轮的修法（`path.resolve(resolveDir, spec)` + 对**字面 `node_modules`** 的正则）**只堵住了
//   冒烟里那两条写法**。独立复核用 esbuild JS API + `metafile` + 内容标记实测，**8 条变体仍把宿主
//   单例静默内联**（本文件改前实测，无门禁/有门禁都 BUILT，字节数与 metafile 见下面的 detail）：
//     `x/../../node_modules/@deepseek-ai/dsh-util-values/lib/index.js`   ⇒ 两条都 BUILT 7384B
//     `a/b/../../../node_modules/@deepseek-ai/dsh-util-values/lib/index.js` ⇒ 同上
//     `x/../../node_modules/react/index.js`                              ⇒ 两条都 BUILT 82899B
//     `../NODE_M~1/@deepseek-ai/dsh-util-values/lib/index.js`（8.3 短名） ⇒ BUILT 7380B
//     `../node_modules./@deepseek-ai/dsh-util-values/lib/index.js`（尾随点）⇒ BUILT 7385B
//     `./dsh-util-values/lib/index.js`（junction）                       ⇒ BUILT 7384B
//     `./node_modules/react/index.js` / 绝对路径到 root react            ⇒ BUILT 82899B
//   **修法**：不再看文本 —— 让 **esbuild 自己解析**（`build.resolve`）拿**真实落点 + realpath** 判。
//   ⚠ 递归陷阱：从 onResolve 里调 `build.resolve` 传**同一组参数**会重入自己并无限递归
//     （esbuild 文档："no attempt made to detect infinite path resolution loops"）⇒ 工厂用
//     `pluginData` 打标记，重入即放手。
{
  const pluginRoot = fileURLToPath(new URL('..', import.meta.url))
  const repoRoot = fileURLToPath(new URL('../..', import.meta.url))
  const REL_HOST = [
    './../node_modules/@deepseek-ai/dsh-util-values/lib/index.js',
    '../node_modules/@deepseek-ai/dsh-util-crypto/lib/index.js',
    '../node_modules/@deepseek-ai/dsh-util-values',            // 包目录（不带子路径）
    '../node_modules/react/index.js',
    '../node_modules/react-dom/client.js',
  ]
  for (const spec of REL_HOST) {
    let msg = null
    try { classifyExternal(spec, pluginRoot) } catch (e) { msg = e.message }
    check(`相对路径指向宿主单例 ⇒ **抛**：${spec}`, msg !== null, (msg ?? 'NOT-THREW').slice(0, 60))
  }
  // ⚠ **第五轮更正**：这里原写"不给 resolveDir 也照样抛（fail-closed）"并声称它覆盖"接线漏传的那种
  //   情况" —— **那句话是假的**。`classifyExternal` 不给 resolveDir 时的兜底，**只**对"文本里字面含
  //   `node_modules` + 受管落点"的写法成立（它退化成对 spec 文本做 `isHostProvidedResolvedPath`）。
  //   这两条**保留**，但只声称它们真正证明的事：
  for (const spec of ['../node_modules/@deepseek-ai/dsh-util-values/lib/index.js', './../node_modules/react/index.js']) {
    let msg = null
    try { classifyExternal(spec) } catch (e) { msg = e.message }
    check(`文本层兜底（**只**对文本含 node_modules/受管落点的写法成立）：${spec}`, msg !== null, (msg ?? 'NOT-THREW').slice(0, 60))
  }
  // …而 8.3 短名 / junction **文本层看不见**（不是洞：真构建的"解析层"兜住，见下）。
  for (const spec of ['../NODE_M~1/@deepseek-ai/dsh-util-values/lib/index.js', './dsh-util-values/lib/index.js']) {
    let v = null
    try { v = classifyExternal(spec, pluginRoot) } catch (e) { v = `THREW: ${e.message.slice(0, 40)}` }
    check(`文本层**看不见**它（边界：靠真构建的解析层兜）：${spec}`, v === 'bundle', String(v))
  }
  // 绝对路径同样按落点判。
  {
    const abs = join(pluginRoot, 'node_modules', '@deepseek-ai', 'dsh-util-values', 'lib', 'index.js')
    let msg = null
    try { classifyExternal(abs, pluginRoot) } catch (e) { msg = e.message }
    check('绝对路径指向宿主单例 ⇒ **抛**', msg !== null, (msg ?? 'NOT-THREW').slice(0, 60))
  }
  // 反面对照：**本地**相对路径（只是带 `..`）不许被误伤 —— 门禁只认落点，不是"见 `..` 就拒"。
  for (const spec of ['../ui/legit-local.js', './../scripts/build-client.mjs', '../client/entry.ts']) {
    let v = null
    try { v = classifyExternal(spec, pluginRoot) } catch (e) { v = `THREW: ${e.message.slice(0, 40)}` }
    check(`bundle（相对路径不误伤）：${spec}`, v === 'bundle', String(v))
  }

  // ⚠ 最强的一层：**真 esbuild 构建**（不是只调判定函数）。同一份输入、只换门禁 ——
  //   无门禁 ⇒ BUILT 且 metafile 里就是宿主单例（**断言的前提**：不是"解析不到"）；
  //   挂 `purityPlugin()` ⇒ 被拦。
  const { build } = await import('esbuild')

  // 夹具一律放系统临时目录（仓库里不落文件、不落链接），跑完在 finally 里删干净。
  const FIX = mkdtempSync(join(tmpdir(), 'ks-purity-fixture-'))
  mkdirSync(join(FIX, 'vendor'), { recursive: true })
  writeFileSync(join(FIX, 'vendor', 'legit.js'), 'export const legit = 1\n', 'utf8')
  const JUNC_ROOT = join(FIX, 'junc-root')
  mkdirSync(JUNC_ROOT, { recursive: true })
  const JUNC = join(JUNC_ROOT, 'dsh-util-values')
  symlinkSync(join(pluginRoot, 'node_modules', '@deepseek-ai', 'dsh-util-values'), JUNC, 'junction')

  const runProbe = async (spec, resolveDir, plugin) => {
    try {
      const r = await build({
        stdin: { contents: `import * as m from ${JSON.stringify(spec)}; console.log(m)`, resolveDir, loader: 'js' },
        absWorkingDir: repoRoot, bundle: true, write: false, metafile: true, logLevel: 'silent',
        ...(plugin ? { plugins: [plugin] } : {}),
      })
      return { ok: true, bytes: r.outputFiles[0].contents.length, inputs: Object.keys(r.metafile.inputs) }
    } catch (e) {
      return { ok: false, msg: (e.errors ?? []).map((x) => x.text).join(' | ') || String(e.message) }
    }
  }

  try {
    // 8 条变体：逐条两向断言（无门禁 BUILT 且落点是宿主单例 / 挂门禁被拦）。
    const HOST_CASES = [
      ['R1 x/../../node_modules/@deepseek-ai/…', 'x/../../node_modules/@deepseek-ai/dsh-util-values/lib/index.js', pluginRoot],
      ['R2 a/b/../../../node_modules/@deepseek-ai/…', 'a/b/../../../node_modules/@deepseek-ai/dsh-util-values/lib/index.js', join(pluginRoot, 'scripts')],
      ['R3 x/../../node_modules/react/…', 'x/../../node_modules/react/index.js', repoRoot],
      ['R4 8.3 短名 ../NODE_M~1/…', '../NODE_M~1/@deepseek-ai/dsh-util-values/lib/index.js', join(pluginRoot, 'scripts')],
      ['R5 尾随点 ../node_modules./…', '../node_modules./@deepseek-ai/dsh-util-values/lib/index.js', join(pluginRoot, 'scripts')],
      ['R6 junction ./dsh-util-values/…', './dsh-util-values/lib/index.js', JUNC_ROOT],
      ['R7 ./node_modules/react/index.js', './node_modules/react/index.js', repoRoot],
      ['R8 绝对路径 → root node_modules/react', join(repoRoot, 'node_modules', 'react', 'index.js'), repoRoot],
    ]
    const singletonInput = (inputs) => inputs.find((p) => /(@deepseek-ai\/dsh-util-values\/lib\/index\.js|react\/index\.js)$/.test(p.replace(/\\/g, '/')))
    for (const [name, spec, resolveDir] of HOST_CASES) {
      const free = await runProbe(spec, resolveDir, null)
      check(`真构建·无门禁 ⇒ 宿主单例**真的**被解析进产物（前提）：${name}`,
        free.ok && singletonInput(free.inputs) !== undefined,
        free.ok ? `BUILT ${free.bytes}B metafile input=${singletonInput(free.inputs)}` : free.msg.slice(0, 70))
      const gated = await runProbe(spec, resolveDir, purityPlugin())
      check(`真构建·挂 purityPlugin() ⇒ **被拦**：${name}`,
        !gated.ok && /构建纯度/.test(gated.msg),
        gated.ok ? `BUILT ${gated.bytes}B（洞又开了！）` : gated.msg.slice(0, 70))
    }

    // 负面对照：门禁**不许越界**（第三方包 / 看着像但不是的 scope / 本地相对路径）。
    {
      const legit = await runProbe('./vendor/legit.js', FIX, purityPlugin())
      check('负面对照：本地相对路径 ./vendor/legit.js 挂门禁仍 BUILT（不误伤）',
        legit.ok, legit.ok ? `BUILT ${legit.bytes}B` : legit.msg.slice(0, 70))
      for (const [name, spec] of [['@deepseek-ai-evil/x', '@deepseek-ai-evil/x'], ['lodash', 'lodash']]) {
        const free = await runProbe(spec, FIX, null)
        const gated = await runProbe(spec, FIX, purityPlugin())
        check(`负面对照：${name} 的失败是 **esbuild 的 Could not resolve**，不是被纯度门禁拦（不越界）`,
          !free.ok && !gated.ok && /Could not resolve/.test(gated.msg) && !/构建纯度/.test(gated.msg),
          `gate=${gated.msg.slice(0, 60)}`)
      }
    }

    // ⚠ **变异测试：让上面的断言有牙**（第四轮那句"接线漏传也红"就是没做这一步才变成假绿）。
    //   这里把**接线**改回老样子（只把 `args.path` 交给文本判定：既不传 resolveDir，也不做解析），
    //   同两条探针**必须不再被拦**。若它们仍被拦，说明拦住它们的不是"接线 + 真实解析"，
    //   那两条"被拦"的回归门禁就是假绿。
    const preFixWiring = () => ({
      name: 'ks-build-purity-WIRING-ORACLE(变异：第五轮之前的老接线)',
      setup(b) {
        b.onResolve({ filter: PURITY_ONRESOLVE_FILTER }, (args) => {
          const verdict = classifyExternal(args.path)          // ← 变异点：漏 resolveDir、且完全不解析
          return verdict === 'external' ? { path: args.path, external: true } : undefined
        })
      },
    })
    for (const [name, spec, dir] of [
      ['8.3 短名 ../NODE_M~1/…', '../NODE_M~1/@deepseek-ai/dsh-util-values/lib/index.js', join(pluginRoot, 'scripts')],
      ['junction ./dsh-util-values/…', './dsh-util-values/lib/index.js', JUNC_ROOT],
    ]) {
      const r = await runProbe(spec, dir, preFixWiring())
      check(`变异（接线改回第五轮之前）⇒ 同一探针**不再被拦** ⇒ 上面两条回归门禁有牙：${name}`,
        r.ok, r.ok ? `BUILT ${r.bytes}B（洞开了 —— 正说明"接线 + 解析"才是拦住它的那一层）` : `仍被拦(${r.msg.slice(0, 50)}) —— 这条断言无牙`)
    }
  } finally {
    // ⚠ 夹具（尤其 junction）必须删干净：不能给仓库/磁盘留痕。
    try { rmdirSync(JUNC) } catch { /* 没建成或已删 */ }
    rmSync(FIX, { recursive: true, force: true })
    check('夹具清理干净（临时目录 + junction 都不留痕）',
      !existsSync(JUNC) && !existsSync(FIX), `junction 残留=${existsSync(JUNC)} 目录残留=${existsSync(FIX)}`)
  }
}

// ── 3) 产物级佐证：现构建产物里的 @deepseek-ai/* 必须在清单内 ──────────────────
{
  const dir = await mkdtemp(join(tmpdir(), 'ks-purity-'))
  const outFile = join(dir, 'client.probe.js')
  // ⚠ 用 fileURLToPath 而不是 `.pathname`：Windows 上前者才是 `D:\...`，后者会给出
  //   `/D:/...%20...`（带前导斜杠 + URL 编码的空格）⇒ spawnSync 直接 ENOENT（exit=null）。
  const pluginRoot = fileURLToPath(new URL('..', import.meta.url))
  const r = spawnSync(process.execPath, [join(pluginRoot, 'scripts', 'build-client.mjs')],
    { cwd: pluginRoot, env: { ...process.env, KS_CLIENT_OUT: outFile }, encoding: 'utf8' })
  if (r.status !== 0) {
    check('现构建成功（产物级佐证的先决条件）', false, `exit=${r.status} ${(r.stderr || '').slice(0, 120)}`)
  } else {
    const text = await readFile(outFile, 'utf8')
    const found = new Set([...text.matchAll(/@deepseek-ai\/[a-z0-9-]+/gi)].map((m) => m[0]))
    const strangers = [...found].filter((m) => !ALLOWED_DEEPSEEK_MODULES.has(m))
    check('产物里出现的每个 @deepseek-ai/* 都在允许清单里', strangers.length === 0,
      strangers.length ? `越界：${strangers.join(', ')}` : `共 ${found.size} 个，全部在清单内`)
    await rm(dir, { recursive: true, force: true })
  }
}

const failed = results.filter((x) => !x.ok)
console.log(`\n== build-purity smoke ${failed.length === 0 ? 'PASS' : 'FAIL'} `
  + `(${results.length - failed.length}/${results.length}) ==`)
process.exit(failed.length === 0 ? 0 : 1)
