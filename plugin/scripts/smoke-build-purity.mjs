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
 *     同时钉住 `build-client.mjs` 的 onResolve filter 用的是**共享常量**（filter 与判定各写一份，
 *     正是 `x/../…` 那次的另一半原因）。
 *
 * 另有一条**产物级**佐证：现构建的产物里出现的每个 `@deepseek-ai/...` 都必须真的在清单里
 * （用 `KS_CLIENT_OUT` 构建到临时文件，不覆盖被跟踪的 `client.js`）。
 *
 * Run:  node scripts/smoke-build-purity.mjs   (exit 0 = pass)
 */
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
//   锚在串首、**根本没触发**。⇒ 钉住"build-client 用的是共享常量"，别让谁再各写一份 filter。
{
  const buildSrc = await readFile(new URL('./build-client.mjs', import.meta.url), 'utf8')
  check('build-client 的 onResolve filter 用共享常量（不许再各写一份）',
    /filter:\s*PURITY_ONRESOLVE_FILTER/.test(buildSrc),
    'filter: PURITY_ONRESOLVE_FILTER')
  const filterOk = ['x/../@deepseek-ai/dsh-util-values', '@deepseek-ai//dsh-util-values',
    '@DeepSeek-AI/x', 'x/../react'].every((s) => PURITY_ONRESOLVE_FILTER.test(s))
  check('共享 filter 能命中归一化/分隔符/大小写三种绕过写法', filterOk,
    'x/../@deepseek-ai/… · @deepseek-ai//… · @DeepSeek-AI/x · x/../react')
}
// 对照：**子路径**里的正常斜杠当然要放过（别把合法写法一起拒了）。
{
  let v = null
  try { v = classifyExternal('@deepseek-ai/dsh-client-ui-slots/sub/path') } catch (e) { v = `THREW: ${e.message.slice(0, 30)}` }
  check('反例对照：清单内模块的正常子路径仍 external', v === 'external', String(v))
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
