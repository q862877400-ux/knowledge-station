/**
 * smoke-settings.mjs — 设置栏目渲染冒烟（诊断用）
 *
 * 用 esbuild 把 client/KsSettingsSection.tsx 打包成 node 可执行 ESM，再用
 * react-dom/server 做一次 SSR：渲染期抛错会直接打印堆栈。
 *
 * 注：组件用了 useSyncExternalStore（浏览器专有第三参），SSR 前把 react 的
 * CJS 对象上的实现包一层 getServerSnapshot 兜底，让 SSR 能继续暴露其它渲染错误。
 *
 * 用法：node scripts/smoke-settings.mjs
 */
import { build } from 'esbuild'
import { mkdtemp, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const here = dirname(fileURLToPath(import.meta.url))
const pluginRoot = resolve(here, '..')

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
}

try {
  const html = renderToString(React.createElement(KsSettingsSection, { service }))
  console.log('SSR_OK html_len=' + html.length)
  if (!html.includes('API')) console.log('WARN: 渲染结果未见 API 配置内容')
} catch (e) {
  console.error('SSR_FAIL: ' + (e && e.stack ? e.stack : String(e)))
  process.exit(1)
}
`

const dir = await mkdtemp(join(tmpdir(), 'ks-smoke-'))
// 入口必须落在 plugin 目录内：相对 import 与 node_modules 解析（react 在仓库根）
// 都按入口所在目录向上查找——放临时目录会导致三者全部解析失败。
const entryPath = join(pluginRoot, '.smoke-settings-entry.jsx')
await writeFile(entryPath, entry, 'utf8')
const outPath = join(pluginRoot, '.smoke-settings-bundle.mjs')

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
    loader: { '.tsx': 'tsx', '.ts': 'ts' },
    logLevel: 'warning',
  })
} catch (err) {
  console.error('BUILD_FAIL: ' + (err && err.message ? err.message : String(err)))
  await rm(entryPath, { force: true })
  process.exit(1)
}
await rm(entryPath, { force: true })

await import(pathToFileURL(outPath).href)
await rm(outPath, { force: true })
