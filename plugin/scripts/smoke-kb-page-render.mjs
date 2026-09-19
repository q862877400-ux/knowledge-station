#!/usr/bin/env node
/**
 * 渲染级冒烟：把「知识库」页**真的挂进 DOM** 跑一遍，断言行为而不是字符串。
 *
 * ## 为什么需要它（补的正是之前承认的缺口）
 * `smoke-client-entry.mjs` 里那条注释写着：「这仍是**字符串级**检查…挡不住"条件后面偷偷加
 * `&& false`"——那种要**渲染级**用例（b11 用 jsdom 建过一份，但 jsdom 本仓未安装）」。
 * 于是"我从没在浏览器里渲染过这一页"这件事一直悬着。本文件把它关掉一半：
 * **真 DOM、真 React、真事件**（仍不是像素）。
 *
 * ## jsdom / React 从哪来（不给你加依赖）
 * 它们**已经在 DSH 检出里**（本机实测：`node_modules/jsdom` v29.1.1；
 * `packages/client/web/node_modules/react{,-dom}` v18.3.1）⇒ 用 `--harness` 指过去即可。
 * ⚠ **这不是"顺手装了个依赖"**：我们 `plugin/package.json` 一个依赖都没加。
 *   代价是这套用例**依赖 DSH 检出存在**——见下面 `找不到就报错、不静默跳过`。
 *
 * ## 诚实的边界（别把它读成"像素已验证"）
 * - 宿主的 `ui-primitives` 是**按源码形状生成的桩**（成员名单从源码派生，见
 *   `scripts/lib/ks-primitives-stub.mjs`；加宿主组件**不需要动本文件**）。
 *   所以这里验的是**我们这一页的组装与行为**，不是宿主组件的内部实现，更不是视觉。
 * - 样式（`ksGuideStyles`）只验"注入了"，验不了"长什么样"。
 */
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

import { build } from 'esbuild'

import { ksClientPrimitivesAlias } from './lib/ks-primitives-stub.mjs'

const here = dirname(fileURLToPath(import.meta.url))
const pluginRoot = resolve(here, '..')

/** jsdom/React 的宿主检出（可用 `--harness` 或 `KS_HARNESS_DIR` 覆盖）。 */
const harness = (() => {
  const i = process.argv.indexOf('--harness')
  if (i !== -1 && process.argv[i + 1]) return process.argv[i + 1]
  return process.env.KS_HARNESS_DIR ?? 'D:\\AI\\DSH\\deepseek-harness'
})()
const jsdomDir = join(harness, 'node_modules', 'jsdom')
const webNodeModules = join(harness, 'packages', 'client', 'web', 'node_modules')

const results = []
function check(name, ok, detail) {
  results.push({ name, ok })
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}${detail === undefined ? '' : ` — ${detail}`}`)
}

// ── 缺件时**报错退出**，不静默跳过 ──
// 理由与本仓其它护栏一致：**"没跑" 不能渲染成 "通过"**。缺件就明确红，并告诉你怎么办。
const missing = []
if (!existsSync(join(jsdomDir, 'package.json'))) missing.push(`jsdom: ${jsdomDir}`)
if (!existsSync(join(webNodeModules, 'react', 'package.json'))) missing.push(`react: ${join(webNodeModules, 'react')}`)
if (!existsSync(join(webNodeModules, 'react-dom', 'package.json'))) missing.push(`react-dom: ${join(webNodeModules, 'react-dom')}`)
if (missing.length > 0) {
  console.error('❌ 渲染级用例**没跑**（缺件），这不是通过：')
  for (const m of missing) console.error(`   - ${m}`)
  console.error('   → 用 --harness <DSH 检出> 或设 KS_HARNESS_DIR 指向含 jsdom/react 的检出。')
  process.exit(1)
}

const stubDir = await mkdtemp(join(tmpdir(), 'ks-render-'))
try {
  /* ── 1. 宿主 ui-primitives 的桩：**从源码派生**，单一所有者在 scripts/lib/ks-primitives-stub.mjs ──
   * ⚠ **不再手写名单**（本文件原来那份手写名单就是 2026-10 第三次红的原因：
   *   P0 新用了 IconInfoOutline14 / IconPlusOutline16 / IconFolderOpenOutline16，桩里没有
   *   ⇒ `No matching export in "…/primitives.mjs"` ⇒ 整个 smoke 步 exit 1）。
   *   现在"加一个宿主组件"只要改 `plugin/client/**`，这里一行都不用动。 */
  const primitivesAlias = ksClientPrimitivesAlias(pluginRoot, stubDir)

  /* ── 2. 测试入口：把"挂载"这件事暴露出来 ── */
  const entry = join(stubDir, 'entry.mjs')
  await writeFile(entry, `
import { createElement } from 'react'
import { createRoot } from 'react-dom/client'
import * as React from 'react'
import { KsKnowledgePage } from ${JSON.stringify(join(pluginRoot, 'client/KsKnowledgePage.tsx'))}

export { createElement, React }
export function mount(container, props) {
  const root = createRoot(container)
  root.render(createElement(KsKnowledgePage, props))
  return root
}
`, 'utf8')

  const out = join(stubDir, 'bundle.mjs')
  // ⚠ **必须把 react/react-dom 固定成唯一一份**（alias 到绝对路径）。
  //   第一版只用 nodePaths，结果出现 "Invalid hook call" + `Cannot read properties of null
  //   (reading 'useState')` —— 那是 **两个 React 副本**：component 的 useState 来自副本 A，
  //   而 renderer 把 dispatcher 装在副本 B 上。改用 alias 后只有一份。
  await build({
    entryPoints: [entry],
    bundle: true,
    platform: 'node',
    format: 'esm',
    outfile: out,
    jsx: 'automatic',
    alias: {
      ...primitivesAlias,
      react: join(webNodeModules, 'react', 'index.js'),
      'react/jsx-runtime': join(webNodeModules, 'react', 'jsx-runtime.js'),
      'react-dom': join(webNodeModules, 'react-dom', 'index.js'),
      'react-dom/client': join(webNodeModules, 'react-dom', 'client.js'),
    },
    define: { 'process.env.NODE_ENV': '"test"' },
  })

  /* ── 3. 真 jsdom 环境 ── */
  const { JSDOM } = await import(pathToFileURL(join(jsdomDir, 'lib', 'api.js')).href)
    .catch(async () => import(pathToFileURL(join(jsdomDir, 'lib', 'api.js')).href))
  const dom = new JSDOM('<!doctype html><html><body><div id="root"></div></body></html>', { url: 'http://localhost/' })
  globalThis.window = dom.window
  globalThis.document = dom.window.document
  // ⚠ Node 26 的 `globalThis.navigator` 是**只读 getter**，直接赋值抛 TypeError
  //   （`Cannot set property navigator of #<Object> which has only a getter`）⇒ 必须 defineProperty。
  Object.defineProperty(globalThis, 'navigator', {
    value: dom.window.navigator, configurable: true, writable: true,
  })
  globalThis.HTMLElement = dom.window.HTMLElement
  globalThis.Node = dom.window.Node
  globalThis.Event = dom.window.Event
  globalThis.requestAnimationFrame = (cb) => setTimeout(() => { cb(Date.now()) }, 0)
  globalThis.cancelAnimationFrame = (id) => { clearTimeout(id) }

  const { mount } = await import(pathToFileURL(out).href)
  // ⚠ **刻意不用 `act`**：React 18.3 的 `act` 在 `react-dom/test-utils` 里，
  //   而 import 它会把**第二份 react/react-dom** 引进来（就是上面那个 Invalid hook call 的成因）。
  //   createRoot 的更新本来就会刷到 DOM，只要给它一个 tick。代价：拿不到 act 的同步保证，
  //   所以每次交互后都 `await flush()`（下面每个断言都这么做）。
  const flush = async () => { await new Promise((r) => { setTimeout(r, 0) }) }

  const container = document.getElementById('root')
  /** 页面要的两个 prop：`useTabInfo`（框架给的运行时）与注入面 `dataSource`。 */
  const useTabInfo = () => ({ tab: { navigation: { params: { page: 'manage' } } } })

  const root = mount(container, { useTabInfo, dataSource: 'render-smoke' })
  await flush()

  const q = (sel) => [...container.querySelectorAll(sel)]
  const byText = (sel, text) => q(sel).find((el) => (el.textContent ?? '').includes(text))
  const click = async (el) => {
    el.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true }))
    await flush()
  }
  const setInput = async (el, value) => {
    // ⚠ 受控 input 必须走**原生 setter**：直接 `el.value = x` 会被 React 的 value tracker
    //   判定为"没变化"而**不触发 onChange**（第一版就是这么失败的，表现是"没解析出来"）。
    const nativeSetter = Object.getOwnPropertyDescriptor(dom.window.HTMLInputElement.prototype, 'value').set
    nativeSetter.call(el, value)
    el.dispatchEvent(new dom.window.Event('input', { bubbles: true }))
    await flush()
  }

  // ── 断言 1：真渲染出来了（不是空壳） ──
  check('页面挂载成功且渲染出内容（真 DOM）',
    container.innerHTML.length > 500,
    `${container.innerHTML.length} 字符`)

  // ── 断言 2：样式确实被注入（运行时 <style>，我们的偏离方案） ──
  const styleEl = document.getElementById('ks-dsh-plugin-styles')
  check('运行时注入了样式表（id=ks-dsh-plugin-styles，含 .ks-batch）',
    styleEl !== null && (styleEl.textContent ?? '').includes('.ks-batch'),
    styleEl === null ? '没有 <style>' : `${(styleEl.textContent ?? '').length} 字符`)
  // ⚠ 所有权属性（2026-09-19 M4）：少了它们 ⇒ ①HMR 的 removeOwnedStyles 找不到我们的标签
  //   而 ensureKsStyles 按 id 去重直接 return ⇒ **改样式必须整页刷新**；
  //   ②别的插件 materialize 时 claimStyles 会把我们的无名标签认领走并在卸载时删掉。
  check('样式标签带 data-plugin + data-plugin-css（宿主的样式所有权按这两个属性认）',
    styleEl !== null
    && styleEl.dataset.plugin === 'ks-dsh-plugin'
    && styleEl.dataset.pluginCss === 'ks-dsh-plugin/ksGuideStyles.css',
    styleEl === null ? '没有 <style>' : `data-plugin=${styleEl.dataset.plugin} data-plugin-css=${styleEl.dataset.pluginCss}`)

  // ── 断言 3：文件列表 = 勾选框 + 常驻「＋标签」 ──
  const checkboxes = q('input[type=checkbox]')
  const addTagBtns = q('button').filter((b) => (b.textContent ?? '') === '＋标签')
  // 默认文件夹 P16 工程防火 有 4 篇 ⇒ 4 个行勾选 + 1 个全选
  check('行勾选框 + 全选：勾选框数 = 文档数 + 1', checkboxes.length === 5, `实际 ${checkboxes.length}`)
  check('每行都有常驻「＋标签」按钮', addTagBtns.length === 4, `实际 ${addTagBtns.length}`)

  // ── 断言 4：全选 ──
  const headCheckbox = checkboxes[0]
  await click(headCheckbox)
  const batch = () => container.querySelector('.ks-batch')
  check('点全选 ⇒ 出现悬浮批量条并显示「已选 4 项」',
    batch() !== null && (batch().textContent ?? '').includes('已选 4 项'),
    batch() === null ? '没有批量条' : (batch().textContent ?? '').slice(0, 60))

  // ── 断言 5：批量条五项俱全 ──
  const batchText = batch()?.textContent ?? ''
  check('批量条含全部五项（已选/取消选择/批量打标签/移动到目录/批量删除）',
    ['已选', '取消选择', '批量打标签', '移动到目录', '批量删除'].every((t) => batchText.includes(t)),
    batchText.slice(0, 120))

  // ── 断言 6：批量删除**真的改了状态**（不是假按钮） ──
  await click(byText('.ks-batch button', '批量删除'))
  check('点「批量删除」⇒ 行数真的减少到 0，批量条消失',
    q('.ks-item').length === 0 && batch() === null,
    `剩 ${q('.ks-item').length} 行`)

  // ── 断言 7：详情里的三个日期（业主点名要的） ──
  // 换到「法律法规」树的某个文件夹（删空了 P16），先切到自建夹「公司制度」更稳
  const companyCard = q('.ks-kb-cards .ks-kb-card').find((el) => (el.textContent ?? '').includes('公司制度'))
  await click(companyCard)
  const rows = q('.ks-item')
  check('切到自建夹「公司制度」⇒ 列表换成它的 3 篇',
    rows.length === 3, `实际 ${rows.length}`)
  const detailBtn = rows[0].querySelector('button[aria-label^="打开"]')
  await click(detailBtn)
  const detailText = container.querySelector('.ks-detail')?.textContent ?? ''
  check('详情含 发布日期 / 生效日期 / 废止日期 三个字段',
    ['发布日期', '生效日期', '废止日期'].every((t) => detailText.includes(t)),
    detailText.slice(0, 120))
  check('详情里的日期是**真值**（不是占位破折号）',
    /\d{4}-\d{2}-\d{2}/.test(detailText),
    (detailText.match(/\d{4}-\d{2}-\d{2}/g) ?? []).slice(0, 3).join(' '))

  // ── 断言 8：标签视图（取代收藏）+ 检索语法当场回显 ──
  const tagsPill = q('button').find((b) => (b.textContent ?? '').trim() === '标签')
  await click(tagsPill)
  const tagsView = container.textContent ?? ''
  check('切到「标签」视图：说明它在**跨大文件夹**定义',
    tagsView.includes('跨知识库文件夹定义') && tagsView.includes('覆盖：'),
    tagsView.includes('覆盖：') ? '含「覆盖：」' : '没看到覆盖范围')

  const syntaxInput = q('input').find((i) => (i.getAttribute('aria-label') ?? '').includes('检索语法'))
  await setInput(syntaxInput, '安全+半导体-冶金')
  const preview = container.textContent ?? ''
  check('检索语法当场回显解析结果（含/排除都显示）',
    preview.includes('含 「安全」「半导体」') && preview.includes('排除 「冶金」'),
    (preview.match(/含 [^（]*/)?.[0] ?? '(没解析出来)').slice(0, 60))

  // ── 断言 9：知识库页**没有搜索框**（业主明确要求） ──
  const searchish = q('input').filter((i) => /搜索|search/i.test(i.placeholder ?? ''))
  check('本页没有搜索框（只有"提问侧"的检索语法框）',
    searchish.length === 0, `命中 ${searchish.length} 个搜索框`)

  root.unmount()
  await flush()

  /* ══════════════════ 能力页（业主指定：一功能一卡一窗） ══════════════════ */
  const capContainer = document.createElement('div')
  document.body.appendChild(capContainer)
  const capRoot = mount(capContainer, { useTabInfo: () => ({ tab: { navigation: { params: { page: 'capabilities' } } } }), dataSource: 'render-smoke' })
  await flush()

  const cq = (sel) => [...capContainer.querySelectorAll(sel)]
  const cClick = async (el) => {
    el.dispatchEvent(new dom.window.MouseEvent('click', { bubbles: true }))
    await flush()
  }

  check('能力页：三个分组都在（自带 / 我启用的 / 实验性）',
    ['自带（', '我启用的（', '实验性（'].every((t) => (capContainer.textContent ?? '').includes(t)),
    (capContainer.textContent ?? '').slice(0, 60))

  check('能力页：八项能力都渲染成卡',
    cq('.ks-cap-card').length === 8, `实际 ${cq('.ks-cap-card').length} 张`)

  // 业主边界 2：旋钮少于 3 个的能力**不配窗**，旋钮直接内联在卡上。
  // ⚠ 别把"内联几张"写成硬编码数字（我第一版写死 1 ⇒ 实际 2 就假红）。
  //   断言**真正的不变量**：每张卡**要么**有「设置…」按钮、**要么**内联旋钮，且**不会两者都有**。
  const cards = cq('.ks-cap-card')
  const withButton = cards.filter((c) => [...c.querySelectorAll('button')].some((b) => (b.textContent ?? '').includes('设置')))
  const withInline = cards.filter((c) => (c.textContent ?? '').includes('不单独开窗'))
  check('能力页：每张卡恰好是一种形态（有「设置…」按钮 XOR 内联旋钮）',
    withButton.length + withInline.length === cards.length
    && withButton.every((c) => !(c.textContent ?? '').includes('不单独开窗')),
    `8 张卡 ⇒ 有窗按钮 ${withButton.length} / 内联 ${withInline.length}`)
  check('能力页：内联的正是"旋钮 < 3 个"那几项（业主边界 2）',
    withInline.length === 2
    && ['条款释义', '材料评审'].every((n) => withInline.some((c) => (c.textContent ?? '').includes(n))),
    withInline.map((c) => (c.textContent ?? '').slice(0, 12)).join(' | '))

  // 点「设置…」⇒ 打开**它自己的**窗
  const dutyCard = cq('.ks-cap-card').find((c) => (c.textContent ?? '').includes('义务清单'))
  await cClick(dutyCard.querySelector('button'))
  const dialog = capContainer.querySelector('[role=dialog]')
  check('能力页：点「设置…」⇒ 打开它自己的设置窗，标题带能力名',
    dialog !== null && (dialog.getAttribute('aria-label') ?? '').includes('义务清单'),
    dialog === null ? '没开窗' : (dialog.getAttribute('aria-label') ?? ''))

  // 窗里的旋钮是真的能操作（拨一个开关/点一个选项）
  const dialogText = dialog?.textContent ?? ''
  check('能力页：窗里有该项能力自己的旋钮（类型/范围/模板/出处）',
    ['义务类型', '范围', '输出模板', '带出处链接'].every((t) => dialogText.includes(t)),
    dialogText.slice(0, 80))

  const pillInDialog = dialog.querySelector('button[data-active]')
  const before = pillInDialog?.getAttribute('data-active')
  await cClick(pillInDialog)
  const after = dialog.querySelector('button[data-active="true"]')?.getAttribute('data-active')
  check('能力页：窗里的枚举旋钮**可点且状态真的变**（不是画上去的）',
    before !== undefined && after === 'true',
    `点了之后有 data-active=true 的胶囊：${String(after)}`)

  await cClick(dialog.querySelector('button[aria-label=关闭]') ?? dialog.querySelector('button'))
  check('能力页：关掉窗 ⇒ 窗消失',
    capContainer.querySelector('[role=dialog]') === null,
    capContainer.querySelector('[role=dialog]') === null ? '已关' : '还在')

  capRoot.unmount()
  await flush()

  /* ══════════ 主题 token 存在性：引用不存在的 token 会静默落到硬编码兜底色 ══════════
   * 2026-09-19 实测抓到 7 个**不存在**的 token（`--dsw-alias-warn` / `-danger` / `-border` /
   * `-bg` / `-bg-secondary` / `-danger-bg` / `-state-error-tertiary`），共 32 处：
   * 前 6 个都写了 `, #hex` 兜底 ⇒ 深色下颜色不对但看得见；最后那个**连兜底都没有**
   * ⇒ CSS 声明非法 ⇒ 「已废止」徽章底色**整个不存在**（肉眼才发现得了）。
   * 官方口径（`docs/web-styling.md`）：只用存在的语义 token，**不许写死色值**。
   * ⇒ 这条用例把"我们引用的每个 `--dsw-*` 都必须在主题里定义"变成机械断言。 */
  const themeDir = join(harness, 'packages', 'client', 'ui-theme', 'src', 'styles')
  const { readdir: rd, readFile: rf } = await import('node:fs/promises')
  let themeCss = ''
  try {
    for (const f of await rd(themeDir)) {
      if (f.endsWith('.css')) themeCss += await rf(join(themeDir, f), 'utf8')
    }
  } catch (e) {
    console.error(`❌ 读不到主题 CSS（${themeDir}）：${String(e.message)}`)
    console.error('   渲染级用例依赖 DSH 检出；缺件时**报错**而不是静默跳过。')
    process.exit(1)
  }
  const defined = new Set([...themeCss.matchAll(/(--dsw-[a-z0-9-]+)\s*:/g)].map((m) => m[1]))
  const clientDir = join(pluginRoot, 'client')
  const referenced = new Map()
  for (const f of await rd(clientDir)) {
    if (!f.endsWith('.ts') && !f.endsWith('.tsx')) continue
    const text = await rf(join(clientDir, f), 'utf8')
    // ⚠ 必须要求 token 后面紧跟 `,` 或 `)`（= 真的是一个 `var(--dsw-x)` 调用）：
    //   否则注释里的 `var(--dsw-alias-*)` 这类**通配写法**会被当成一个不存在的 token
    //   （我第一版就是这么误报的）。
    for (const m of text.matchAll(/var\((--dsw-[a-z0-9-]+)\s*[,)]/g)) {
      if (!referenced.has(m[1])) referenced.set(m[1], new Set())
      referenced.get(m[1]).add(f)
    }
  }
  const ghostTokens = [...referenced.entries()].filter(([t]) => !defined.has(t))
  check(`我们引用的 ${referenced.size} 个 --dsw-* token **全部真实存在**（不存在 ⇒ 静默落到兜底色）`,
    ghostTokens.length === 0,
    ghostTokens.length === 0
      ? `主题里共定义 ${defined.size} 个 token`
      : ghostTokens.map(([t, fs]) => `${t}（${[...fs].join(',')}）`).join(' | '))
} finally {
  await rm(stubDir, { recursive: true, force: true })
}

const failed = results.filter((r) => !r.ok)
console.log(`\n== kb-page-render smoke ${failed.length === 0 ? 'PASS' : 'FAIL'} `
  + `(${results.length - failed.length}/${results.length}) ==`)
process.exit(failed.length === 0 ? 0 : 1)
