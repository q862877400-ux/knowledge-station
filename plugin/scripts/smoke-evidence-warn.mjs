/**
 * ks-dsh-plugin — scripts/smoke-evidence-warn.mjs
 *
 * **渲染级**冒烟：引文坐标缺失/失败的提示行必须真的渲染出来（诊断 A1/A8 的判据）。
 * 照 smoke-anchor-mark 的零依赖做法：`react-dom/server` 静态渲染纯组件 `KsAnchorWarn`。
 *
 * 判据（成对）：
 *   · `role="alert"` 在场（无障碍语义 = 失败可见）；
 *   · **后端/异常给的原因原文必须原样出现**（措辞唯一所有者在调用方组合，组件不许吞字）；
 *   · 颜色走 token（`--dsw-alias-state-warn-primary`）不写死色值（主题债棘轮精神）。
 *
 * 用法：node scripts/smoke-evidence-warn.mjs   （cwd = plugin 根；退出码 0 = 全通过）
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

let React, renderToStaticMarkup
try {
  React = await import('react')
  ;({ renderToStaticMarkup } = await import('react-dom/server'))
} catch (err) {
  console.error('根 node_modules 缺少 react / react-dom（本冒烟用它们做静态渲染）：'
    + `${err && err.message ? err.message : String(err)}\n  修法：在仓库根执行 npm install。`)
  process.exit(1)
}

// 产物落 plugin/ 内（react 是 external，Node 按产物位置向上找 node_modules —— smoke-anchor-mark 的教训）
const outfile = join(pluginRoot, '.evidence-warn.smoke.mjs')
await build({
  entryPoints: [join(pluginRoot, 'client', 'KsAnchorWarn.tsx')],
  bundle: true, platform: 'node', format: 'esm', outfile,
  absWorkingDir: pluginRoot, loader: { '.tsx': 'tsx', '.ts': 'ts' },
  external: ['react', 'react-dom', 'react/jsx-runtime'],
  logLevel: 'warning',
})
const mod = await import(pathToFileURL(outfile).href)
await rm(outfile, { force: true })

const KsAnchorWarn = mod.KsAnchorWarn
check('KsAnchorWarn 导出为函数（渲染级冒烟的入口）', typeof KsAnchorWarn === 'function')

if (typeof KsAnchorWarn === 'function') {
  const WHY = '后端给的原文-WHY-ANCHOR-XYZ'
  const html = renderToStaticMarkup(React.createElement(KsAnchorWarn, { message: WHY }))
  check('role="alert" 在场（失败可见的无障碍语义）', html.includes('role="alert"'), html)
  check('原因原文**原样**出现（组件不许吞字/自行解释）', html.includes(WHY), html)
  check('颜色走 token 不写死（主题随宿主切换；字面兜底也算写死——ui-audit-D P2）',
    html.includes('--dsw-alias-state-warn-primary') && !html.includes('#'),
    html)
  check('空消息不渲染成空壳（至少有 ⚠ 与 alert）',
    (() => { const h = renderToStaticMarkup(React.createElement(KsAnchorWarn, { message: '' })); return h.includes('role="alert"') && h.includes('⚠') })())
}

const failed = results.filter((r) => !r.ok)
console.log(`\n== evidence-warn smoke ${failed.length === 0 ? 'PASS' : 'FAIL'} (${results.filter((r) => r.ok).length}/${results.length}) ==`)
process.exit(failed.length === 0 ? 0 : 1)
