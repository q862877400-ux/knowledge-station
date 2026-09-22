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
import { mkdtemp, rm, writeFile, readFile } from 'node:fs/promises'
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
// 入口 = 两个纯组件的再导出（同一模块图一次打包；单文件入口拿不到两份导出）。
const tmp = await mkdtemp(join(tmpdir(), 'ks-evwarn-'))
const entryFile = join(tmp, 'entry.ts')
await writeFile(entryFile, [
  `export * from ${JSON.stringify(join(pluginRoot, 'client', 'KsAnchorWarn.tsx'))}`,
  `export * from ${JSON.stringify(join(pluginRoot, 'client', 'KsArrowOverlay.tsx'))}`,
].join('\n'), 'utf8')
await build({
  entryPoints: [entryFile],
  bundle: true, platform: 'node', format: 'esm', outfile,
  absWorkingDir: pluginRoot, loader: { '.tsx': 'tsx', '.ts': 'ts' },
  external: ['react', 'react-dom', 'react/jsx-runtime'],
  logLevel: 'warning',
})
const mod = await import(pathToFileURL(outfile).href)
await rm(outfile, { force: true })
await rm(tmp, { recursive: true, force: true })

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

  // ---- 复核 F0 打回后的补钉：警示样式必须走**主题真 token**、无字面兜底、且单一出处 ----
  const cssText = typeof mod.ksWarnCssText === 'function' ? mod.ksWarnCssText() : ''
  check('警示样式走主题真 token（bg-layer-2 / border-l1 / state-warn-primary），**无字面兜底**',
    cssText.includes('--dsw-alias-bg-layer-2') && cssText.includes('--dsw-alias-border-l1')
    && cssText.includes('--dsw-alias-state-warn-primary') && !cssText.includes('#'),
    cssText)
  {
    const entrySrc = await readFile(join(pluginRoot, 'client', 'entry.ts'), 'utf8')
    check('entry.ts 提示条用同一出处 ksWarnCssText（钉不到它曾是 F0 漏网的原因）',
      entrySrc.includes('ksWarnCssText()') && !entrySrc.includes('#a15c00') && !entrySrc.includes('#ddd'),
      entrySrc.includes('ksWarnCssText()') ? '同源' : '未用共用样式')
  }

  // ---- A1b：红箭头覆盖层（单页/连续共用的视觉本体）----
  // ⚠ forwardRef 组件的 typeof 是 **object** 不是 function（我第一版门槛写错 ⇒ 渲染断言整段没跑）。
  const ArrowOverlay = mod.KsArrowOverlay
  const arrowRenderable = ArrowOverlay !== undefined && ArrowOverlay !== null
  check('KsArrowOverlay 导出为可渲染元素（单页/连续两处共用的箭头覆盖层）', arrowRenderable,
    `typeof=${typeof ArrowOverlay}`)
  if (arrowRenderable) {
    const arrowHtml = renderToStaticMarkup(React.createElement(ArrowOverlay, { ref: { current: null } }))
    check('红箭头图形本体**冻结**（data-URI SVG + 精确路径 + 红色；掏掉路径当场红）',
      arrowHtml.includes('data:image/svg+xml')
      && String(mod.KS_ARROW_SVG ?? '').includes('d="M0 4h11V1l9 4-9 4V6H0z"')
      && String(mod.KS_ARROW_SVG ?? '').includes('e02020'),
      arrowHtml)
    check('覆盖层默认隐藏 + 装饰语义（display:none + aria-hidden）',
      arrowHtml.includes('display:none') && arrowHtml.includes('aria-hidden="true"'), arrowHtml)
  }
}

const failed = results.filter((r) => !r.ok)
console.log(`\n== evidence-warn smoke ${failed.length === 0 ? 'PASS' : 'FAIL'} (${results.filter((r) => r.ok).length}/${results.length}) ==`)
process.exit(failed.length === 0 ? 0 : 1)
