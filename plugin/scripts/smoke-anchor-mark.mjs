/**
 * ks-dsh-plugin — scripts/smoke-anchor-mark.mjs
 *
 * **渲染级**冒烟：把锚点标记组件**真的渲染出来**，逐档断言它输出什么。
 *
 * ## 为什么要有它（复核 b11 的 LOW-3 / "闸门空"）
 * 在这之前，UI 那几条护栏都只到**字符串级**（"产物里有那句文案"/"case 在不在"）+
 * 编译期穷尽（`assertNever`）+ 产物↔源码一致。它们挡得住"删条件/改条件/忘了重建"，
 * 但挡不住"条件成立、渲染出来的却是空"这类问题——而 b11 建议的正是**收编一份渲染用例**。
 * b11 那份用 **jsdom**（本仓 `plugin/` 没装 ⇒ 要引依赖）；本脚本用**零依赖**的等价做法：
 * `react-dom/server` 的 `renderToStaticMarkup` 把组件渲染成 HTML 字符串（静态渲染不需要 DOM），
 * react/react-dom 用**仓库根** `node_modules` 里已有的（18.3.1）。
 *
 * ## 判据（逐档，成对）
 *   · `undefined` / `ok` / `no_locators` ⇒ **渲染成空**（不加噪声，这是刻意的）；
 *   · `stale` ⇒ 有「引用锚点需复算」+ **后端给的 why 原文** + "不代表已经坏了"；
 *   · `unknown` ⇒ 有「引用锚点未验证」+ why；
 *   · `health_error` ⇒ 有「锚点健康度算不出来」+ `role="alert"` + why（**红色**：那是我们的问题）。
 * ⚠ `why` 必须**原样出现**：界面不许自己解释 status（措辞的唯一所有者在后端）——
 *   这条断言就是钉这件事的：把 why 换成一个假字符串，渲染结果里必须看到**那个假字符串**。
 *
 * ⚠ 依赖：**根** `node_modules` 的 react / react-dom（`plugin/` 里没有）。
 *   缺了就**明确失败**（不是静默 SKIP）——门禁缺依赖应当是可见的，而不是消失。
 *
 * 用法：node scripts/smoke-anchor-mark.mjs   （cwd = plugin 根；退出码 0 = 全通过）
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

// ⚠ 临时产物必须落在 **plugin/ 里面**（不是 OS 临时目录）：bundle 里 `import 'react'` 是
// **external**，Node 要沿着**它自己的路径**往上找 node_modules —— 放在 %TEMP% 里找不到
// （TEMP 树上没有 node_modules），第一版就是这么报 ERR_MODULE_NOT_FOUND 的。
// 名字与 build-client.mjs 的 `.client.tmp.js` 同款，用完即删。
const outfile = join(pluginRoot, '.anchor-mark.smoke.mjs')

let React, renderToStaticMarkup
try {
  React = await import('react')
  ;({ renderToStaticMarkup } = await import('react-dom/server'))
} catch (err) {
  console.error('根 node_modules 缺少 react / react-dom（本冒烟用它们做静态渲染）：'
    + `${err && err.message ? err.message : String(err)}\n`
    + '  修法：在仓库根执行 npm install（plugin/ 里没有这两个包，也不需要装进去）。')
  process.exit(1)
}

// 把面板打成一个 Node 可 import 的 ESM（react 保持 external ⇒ 用根 node_modules 的那份）
await build({
  entryPoints: [join(pluginRoot, 'client', 'KsMaterialsPanel.tsx')],
  bundle: true, platform: 'node', format: 'esm', outfile,
  absWorkingDir: pluginRoot, loader: { '.tsx': 'tsx', '.ts': 'ts' },
  external: ['react', 'react-dom', 'react/jsx-runtime', 'pdfjs-dist'],
  logLevel: 'warning',
})

const mod = await import(pathToFileURL(outfile).href)
await rm(outfile, { force: true })

const AnchorMark = mod.AnchorMark
check('面板导出了 AnchorMark（渲染级冒烟的入口）', typeof AnchorMark === 'function')

const render = (status, why) =>
  renderToStaticMarkup(React.createElement(mod.AnchorMark, why === undefined ? { status } : { status, why }))

if (typeof AnchorMark === 'function') {
  const WHY = '后端给的原文-WHY-XYZ'
  for (const status of [undefined, 'ok', 'no_locators']) {
    check(`${String(status)} 渲染成空（不加噪声）`, render(status, WHY) === '',
      JSON.stringify(render(status, WHY)).slice(0, 60))
  }
  const stale = render('stale', WHY)
  check('stale 渲染出「引用锚点需复算」', stale.includes('引用锚点需复算'), stale.slice(0, 80))
  check('stale 把后端 why **原样**渲染出来', stale.includes(WHY), '界面不许自己解释 status')
  check('stale 保留"不代表已经坏了"这句纪律', stale.includes('不代表已经坏了'))

  const unknown = render('unknown', WHY)
  check('unknown 渲染出「引用锚点未验证」', unknown.includes('引用锚点未验证'), unknown.slice(0, 80))
  check('unknown 把后端 why 原样渲染出来', unknown.includes(WHY))
  check('unknown 说清"不等于有问题"', unknown.includes('不等于'))

  const boom = render('health_error', WHY)
  check('health_error 渲染出「锚点健康度算不出来」', boom.includes('锚点健康度算不出来'), boom.slice(0, 80))
  check('health_error 用 role="alert"（这是我们的问题，要显眼）', boom.includes('role="alert"'))
  check('health_error 把后端 why 原样渲染出来', boom.includes(WHY))
  check('health_error 说清"是工具缺陷、不代表材料有问题"',
    boom.includes('工具缺陷') && boom.includes('不代表'))
  // 反向：为什么必须逐档断言——把 why 留空时**仍要有**标记（不能因为没原因就不报）
  check('why 缺失时仍渲染标记（只换成"后端未给原因"）',
    render('health_error', undefined).includes('后端未给原因')
    && render('health_error', undefined).includes('锚点健康度算不出来'))
}

const failed = results.filter((r) => !r.ok)
console.log(`\n== anchor-mark smoke ${failed.length === 0 ? 'PASS' : 'FAIL'} `
  + `(${results.length - failed.length}/${results.length}) ==`)
process.exit(failed.length === 0 ? 0 : 1)
