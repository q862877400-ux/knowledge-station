/**
 * smoke-settings.mjs — 设置栏目渲染冒烟（诊断用）
 *
 * 用 esbuild 把 client/KsSettingsSection.tsx 打包成 node 可执行 ESM，再用
 * react-dom/server 做一次 SSR：渲染期抛错会直接打印堆栈。
 *
 * 断言（2026-11 迁移后升级为硬判据）：
 *   1. **五个**折叠类目（证据查看器/效力报告/每日巡检/公告发现/API配置）全部渲染
 *      —— 效力报告已从侧栏 tab 迁入设置栏目。
 *      ⚠⚠ **2026-09-21（KB-FOLDER-PLAN 第 4 步）就地减一**：原来的第六个是「入库预览」
 *      （挂 `KsIngestPanel` 的只读体检）。业主「不要两个页面」⇒ 导入只有一个落点：
 *      知识库页「待分类」层上的导入面板（来源目录 + 先体检（只读）+ 导入 + 覆盖重导）。
 *      **删掉的是入口，不是能力**（体检那一步并进待分类层，走同一条
 *      `/ks/ingest/preview/batch`）；`KsIngestPanel.tsx` 本身与它在 `smoke-ingest.mjs` /
 *      `ui-render-shot.mjs --page ingest` 上的判据都还在（登记：产品里已无入口，代码暂留）。
 *      判据强度不变：少一个类目、或多一个没声明的类目，这里都会红。
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

  // 五个折叠类目全部在场（2026-11 用户拍板：全部进设置、全折叠；第 4 步撤掉「入库预览」）。
  for (const cat of ['证据查看器', '效力报告', '每日巡检', '公告发现', 'API配置']) {
    if (!html.includes(cat)) { console.error('MISSING_CATEGORY: ' + cat); process.exit(1) }
  }
  // 第 4 步撤掉的那一个**不许回来**：它一回来就是"两个页面"（判据与上面那条同强度）。
  if (html.includes('入库前只读体检')) { console.error('STALE_CATEGORY: 入库预览 又被挂回设置了'); process.exit(1) }
  // 旧入口按钮必须消失（不再是“打开效力报告”跳转，而是内嵌面板）。
  if (html.includes('打开效力报告')) { console.error('STALE_ENTRY_BUTTON still rendered'); process.exit(1) }
  // 全部类目默认收起：SSR 初始树不应带 open 属性（<details open>）。
  if (/<details[^>]+open/.test(html)) { console.error('CATEGORY_NOT_FOLDED: some <details> renders open'); process.exit(1) }
  // 懒加载门：SSR 期零请求。
  if (fetched.length > 0) { console.error('FETCH_DURING_SSR: ' + fetched.join(',')); process.exit(1) }
  console.log('CATEGORIES_OK 5 collapsed categories rendered, 0 fetches during SSR')
} catch (e) {
  console.error('SSR_FAIL: ' + (e && e.stack ? e.stack : String(e)))
  process.exit(1)
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
    alias: { '@deepseek-ai/dsh-client-ui-primitives': primitivesStubPath },
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
