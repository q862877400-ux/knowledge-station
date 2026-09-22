/**
 * ks-dsh-plugin — scripts/smoke-evidence-prefs.mjs
 *
 * **渲染级**冒烟：设置区「显示红色定位箭头」的开关必须**真的**传到证据查看器。
 * 这是诊断 A2（死开关）的判据。
 *
 * ## 做法（为什么这样有牙）
 * 打包 `KsEvidenceHost`，但把 `./KsEvidenceTab` 换成**回显 props 的桩**——桩把收到的
 * `prefs.showArrow` 渲染进 HTML 属性。于是"宿主有没有把偏好传对"变成**行为判据**：
 * 把 KsEvidenceHost 改回硬编码 `showArrow: true`，`data-showarrow="false"` 那条**必须红**
 * （2026-09-22 变异实测过）。字符串级源码断言挡不住"换种写法还是写死"，所以不用它。
 *
 * 偏好走**真实 ksPrefs 模块**（与宿主同包同实例——所以入口文件把两者一起导出），
 * `updatePrefs` 改值后重渲染必须跟着变（订阅链路的牙）。
 *
 * ⚠ 依赖：**根** node_modules 的 react / react-dom（同 smoke-anchor-mark）；缺失 = 明确失败。
 * 用法：node scripts/smoke-evidence-prefs.mjs   （cwd = plugin 根；退出码 0 = 全通过）
 */
import { mkdtemp, rm, writeFile } from 'node:fs/promises'
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
  console.error('根 node_modules 缺少 react / react-dom（本冒烟用它们做静态渲染）：'
    + `${err && err.message ? err.message : String(err)}\n`
    + '  修法：在仓库根执行 npm install。')
  process.exit(1)
}

const tmp = await mkdtemp(join(tmpdir(), 'ks-evprefs-'))

// 回显桩：把收到的 prefs/showArrow 原样写进 DOM 属性（被 onResolve 顶替掉真的 KsEvidenceTab）。
const stubFile = join(tmp, 'evidence-tab-stub.tsx')
await writeFile(stubFile, [
  "import * as React from 'react'",
  'export function KsEvidenceTab(props: { prefs?: { showArrow?: boolean }; tab?: { path?: string } }): React.ReactElement {',
  "  return React.createElement('div', { id: 'ks-evprefs-stub',",
  "    'data-showarrow': String(props?.prefs?.showArrow),",
  "    'data-path': String(props?.tab?.path ?? '') })",
  '}',
].join('\n'), 'utf8')

// 入口：宿主 + 真实 ksPrefs **同一个模块图**（分开打包会有两个偏好实例，判据就假绿了）。
const entryFile = join(tmp, 'entry.ts')
await writeFile(entryFile, [
  `export { KsEvidenceHost } from ${JSON.stringify(join(pluginRoot, 'client', 'KsEvidenceHost.tsx'))}`,
  `export * from ${JSON.stringify(join(pluginRoot, 'client', 'ksPrefs.ts'))}`,
].join('\n'), 'utf8')

const primStubDir = await mkdtemp(join(tmpdir(), 'ks-evprefs-prim-'))
const primitivesAlias = ksClientPrimitivesAlias(pluginRoot, primStubDir)
// 产物必须落 plugin/ 内（react 是 external，Node 按产物位置向上找 node_modules——smoke-anchor-mark 的教训）。
const outfile = join(pluginRoot, '.evidence-prefs.smoke.mjs')

await build({
  entryPoints: [entryFile],
  bundle: true, platform: 'node', format: 'esm', outfile,
  absWorkingDir: pluginRoot, loader: { '.tsx': 'tsx', '.ts': 'ts' },
  external: ['react', 'react-dom', 'react/jsx-runtime', 'pdfjs-dist'],
  alias: { ...primitivesAlias },
  plugins: [{
    name: 'ks-evidence-tab-stub',
    setup(b) {
      b.onResolve({ filter: /^\.\/KsEvidenceTab$/ }, () => ({ path: stubFile }))
    },
  }],
  logLevel: 'warning',
})

const mod = await import(pathToFileURL(outfile).href)
await rm(outfile, { force: true })
await rm(tmp, { recursive: true, force: true })

const { KsEvidenceHost, updatePrefs, getPrefsSnapshot, KS_PREFS_DEFAULT } = mod
check('打包导出 KsEvidenceHost 与真实偏好存储（同一模块实例）',
  typeof KsEvidenceHost === 'function' && typeof updatePrefs === 'function'
  && typeof getPrefsSnapshot === 'function' && KS_PREFS_DEFAULT?.showArrow === true)

if (typeof KsEvidenceHost === 'function' && typeof updatePrefs === 'function') {
  const render = () => renderToStaticMarkup(React.createElement(KsEvidenceHost, {
    useTabInfo: () => ({
      tab: {
        id: 't1', kind: 'ks:doc', title: '证据',
        navigation: { params: { url: 'http://127.0.0.1:1/__ks_evidence__?doc=d1' }, revision: 0 },
        visible: true,
      },
    }),
    openEvidence: () => {},
  }))

  updatePrefs({ showArrow: true })
  const on = render()
  check('开关开：查看器收到 showArrow=true', on.includes('data-showarrow="true"'), on)
  check('顺带钉住 tab.path 的透传（证据地址契约）',
    on.includes('data-path="http://127.0.0.1:1/__ks_evidence__?doc=d1"'), on)

  updatePrefs({ showArrow: false })
  const off = render()
  check('开关关：查看器收到 showArrow=false（A2 的牙——写死 true 在这里必红）',
    off.includes('data-showarrow="false"'), off)

  updatePrefs({ showArrow: true })
  const again = render()
  check('再打开：跟着变回 true（订阅链路双向生效）', again.includes('data-showarrow="true"'), again)
}

await rm(primStubDir, { recursive: true, force: true }).catch(() => {})
const failed = results.filter((r) => !r.ok)
console.log(`\n== evidence-prefs smoke ${failed.length === 0 ? 'PASS' : 'FAIL'} (${results.filter((r) => r.ok).length}/${results.length}) ==`)
process.exit(failed.length === 0 ? 0 : 1)
