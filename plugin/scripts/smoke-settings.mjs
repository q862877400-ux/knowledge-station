/**
 * smoke-settings.mjs — 设置栏目渲染冒烟（诊断用）
 *
 * 用 esbuild 把 client/KsSettingsSection.tsx 打包成 node 可执行 ESM，再用
 * react-dom/server 做一次 SSR：渲染期抛错会直接打印堆栈。
 *
 * 断言（2026-11 迁移后升级为硬判据）：
 *   1. 六个折叠类目（证据查看器/效力报告/入库预览/每日巡检/公告发现/API配置）
 *      全部渲染——效力报告与入库预览已从侧栏 tab 迁入设置栏目；
 *   2. 旧「打开效力报告」入口按钮不复存在；
 *   3. 全部 <details> 默认收起（SSR 初始树无 open 属性）；
 *   4. 懒加载门：SSR 期间（=所有面板 visible=false）零网络请求。
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

try {
  const html = renderToString(React.createElement(KsSettingsSection, { service }))
  console.log('SSR_OK html_len=' + html.length)

  // 六个折叠类目全部在场（2026-11 用户拍板：全部进设置、全折叠）。
  for (const cat of ['证据查看器', '效力报告', '入库预览', '每日巡检', '公告发现', 'API配置']) {
    if (!html.includes(cat)) { console.error('MISSING_CATEGORY: ' + cat); process.exit(1) }
  }
  // 旧入口按钮必须消失（不再是“打开效力报告”跳转，而是内嵌面板）。
  if (html.includes('打开效力报告')) { console.error('STALE_ENTRY_BUTTON still rendered'); process.exit(1) }
  // 全部类目默认收起：SSR 初始树不应带 open 属性（<details open>）。
  if (/<details[^>]+open/.test(html)) { console.error('CATEGORY_NOT_FOLDED: some <details> renders open'); process.exit(1) }
  // 懒加载门：SSR 期零请求。
  if (fetched.length > 0) { console.error('FETCH_DURING_SSR: ' + fetched.join(',')); process.exit(1) }
  console.log('CATEGORIES_OK 6 collapsed categories rendered, 0 fetches during SSR')
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
