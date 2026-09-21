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
import { KsKnowledgePage, KB_PAGE_SEARCH } from ${JSON.stringify(join(pluginRoot, 'client/KsKnowledgePage.tsx'))}

export { createElement, React, KB_PAGE_SEARCH }
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

  const { mount, KB_PAGE_SEARCH } = await import(pathToFileURL(out).href)
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

  /* ══════════ 断言 3j：**页面留边**（5j，2026-09-20；业主：「窗口四周要留点边啊」） ══════════
   * 规范：docs/UI-BASELINE.md 第二节「页面留边」；落地记录：第六节 5j。
   * 判据：页面根 / 卡片带外框 / 表格容器 / 批量条 / 页内按钮行 的元素外缘到 shell 边缘
   *   ≥ --ks-page-pad-x（窄 16 / 宽 24）。
   * ⚠ **这一侧没有布局引擎**（jsdom 的 getBoundingClientRect 恒 0）⇒ 它判不了像素，只能钉
   *   **声明与结构**：① 页面根被 `.ks-page` 容器包着（容器查询的前提）；② 页面根的 padding
   *   走留边 token；③ 所有"不得贴边"的元素都在页面根**之内**、且没有被负外边距抵消。
   *   **像素级**（外缘到 shell 内容边 ≥ 该档留边）由 `ui-render-shot.mjs` 的 `ksPadCheck` 在
   *   真 Chrome 里判 —— 两侧合起来才算钉住（同 5i 的 cardsCheck 口径，**别互相顶替**）。
   * ⚠ 期望值是**冻结的规范值**（与 ui-render-shot.mjs 顶部的 PAGE_PAD_* **必须同值**），
   *   并且要与注入样式表里的 token 定义互相核对 —— 谁改了 token 而没改这两处（或反之）就红。 */
  const PAGE_PAD_X_NARROW = 16
  const PAGE_PAD_X_WIDE = 24
  const PAGE_PAD_BREAKPOINT = 660
  const pageWrap = q('.ks-page')
  const kbRoot = q('.ks-kb')[0] ?? null
  check('页面留边：页面根外面有一层 `.ks-page` 容器（宽/窄两档就是按**它**的宽度切的）',
    pageWrap.length === 1 && kbRoot !== null && kbRoot.parentElement === pageWrap[0],
    `根数 .ks-page=${pageWrap.length} / .ks-kb=${q('.ks-kb').length}；`
      + `.ks-kb 的父元素类名=${JSON.stringify(kbRoot?.parentElement?.className ?? null)}`)
  const rootCs = kbRoot === null ? null : dom.window.getComputedStyle(kbRoot)
  const rootPad = rootCs === null
    ? { l: null, r: null, t: null, b: null }
    : {
        l: rootCs.getPropertyValue('padding-left').trim(),
        r: rootCs.getPropertyValue('padding-right').trim(),
        t: rootCs.getPropertyValue('padding-top').trim(),
        b: rootCs.getPropertyValue('padding-bottom').trim(),
      }
  // jsdom 对 `var()` 值**可能**原样保留（同 bandFlex 的 computed flex）、也可能解析成 px；
  // 两种都接受，但**必须是留边 token 或该档的规范值** —— 少了/写成 0 就红（变异要抓的正是它）。
  const padOk = (v) => v === 'var(--ks-page-pad-x)' || v === 'var(--ks-page-pad-y)'
    || v === `${String(PAGE_PAD_X_NARROW)}px` || v === `${String(PAGE_PAD_X_WIDE)}px`
  check('页面留边：页面根的 padding 四个方向都走留边 token（不是 0、不是现场拍的数字）',
    rootPad.l !== null && [rootPad.l, rootPad.r].every(padOk) && [rootPad.t, rootPad.b].every(padOk),
    `padding 左=${JSON.stringify(rootPad.l)} 右=${JSON.stringify(rootPad.r)} `
      + `上=${JSON.stringify(rootPad.t)} 下=${JSON.stringify(rootPad.b)}`)
  const sheetText = styleEl?.textContent ?? ''
  const tokenOf = (name) => {
    const m = new RegExp(`--${name}\\s*:\\s*(\\d+)px`).exec(sheetText)
    return m === null ? null : Number(m[1])
  }
  // ⚠ 只认**页面留边那一条** @container（body 里出现 .ks-page）：本表里另有一条给 .ks-list
  //   切列档的同阈值 @container，取"第一个"会认错对象（那会让阈值改歪却全绿）。
  let bpFound = null
  for (const m of sheetText.matchAll(/@container\s*\(min-width:\s*(\d+)px\)\s*\{([^}]*)\}/g)) {
    if (m[2].includes('.ks-page')) { bpFound = Number(m[1]); break }
  }
  check('页面留边：注入样式表里的两档 token 与阈值 = 规范的冻结值（窄 16 / 宽 24 / 阈值 660）',
    tokenOf('ks-page-pad-x-narrow') === PAGE_PAD_X_NARROW
    && tokenOf('ks-page-pad-x-wide') === PAGE_PAD_X_WIDE
    && bpFound === PAGE_PAD_BREAKPOINT,
    `--ks-page-pad-x-narrow=${JSON.stringify(tokenOf('ks-page-pad-x-narrow'))} `
      + `--ks-page-pad-x-wide=${JSON.stringify(tokenOf('ks-page-pad-x-wide'))} `
      + `@container=${JSON.stringify(bpFound)}`)
  // 适用面（与 UI-BASELINE 第二节逐条一致）：这些元素**必须**是页面根的后代 ——
  // 只要有一个跑到 `.ks-page` 外面，留边就管不到它（那是最容易悄悄发生的回归）。
  const PAD_SUBJECTS = ['.ks-kbband', '.ks-list', '.ks-batch', '.ks-dirs',
    '.ks-page-head', '.ks-kb-row', '.ks-empty-card']
  const outside = []
  const negMargin = []
  for (const sel of PAD_SUBJECTS) {
    for (const el of q(sel)) {
      if (pageWrap.length === 1 && !pageWrap[0].contains(el)) outside.push(sel)
      const cs = dom.window.getComputedStyle(el)
      for (const prop of ['margin-left', 'margin-right']) {
        const v = parseFloat(cs.getPropertyValue(prop))
        if (Number.isFinite(v) && v < 0) negMargin.push(`${sel} ${prop}=${String(v)}`)
      }
    }
  }
  const presentSubjects = PAD_SUBJECTS.filter((sel) => q(sel).length > 0)
  /* ⚠⚠ **5j-补（2026-09-20）："至少有一个"不算判过（复核 `verify-freeze-5j` 打回 E① 的 M6）。**
     复核铁证：把 `.ks-dirs` 的类名改掉让它**整个消失** ⇒ 本文件 **72/72 PASS exit 0**
     —— 因为原判据只是 `presentSubjects.length > 0`（7 类里剩 6 类照样通过）。
     "元素没了"和"元素合规"必须可分辨 ⇒ 这里按**这一跑所处状态的声明集合**逐类判存在性。
     本块跑在**默认态**（卡片带 + 一级目录，还没下钻、还没勾选）⇒ 该有的就是下面 4 类；
     `.ks-list` 由后面"列模板只有一个所有者"那段强制（它要求 `.ks-list` 有真子元素）、
     `.ks-batch` 由"搜索会清空已选"那段强制（它要求搜索前批量条存在）；
     `.ks-empty-card` 在本脚本**没有对应状态**（空态要 `--interact kb-empty-files`）⇒
     它由 `smoke-kb-pad-pixels.mjs`（在门禁链里，真浏览器）的那一组判。
     **写明"这里没判什么"，免得把沉默读成覆盖。** */
  const PAD_REQUIRED_DEFAULT_STATE = ['.ks-kbband', '.ks-dirs', '.ks-page-head', '.ks-kb-row']
  const missingHere = PAD_REQUIRED_DEFAULT_STATE.filter((sel) => q(sel).length === 0)
  check('页面留边：默认态该有的适用面元素一个不少（.ks-kbband/.ks-dirs/.ks-page-head/.ks-kb-row —— 类名被改掉/元素被删都会在这里红）',
    missingHere.length === 0,
    missingHere.length === 0
      ? `4 类都在（本状态不判 .ks-list/.ks-batch/.ks-empty-card：前三者的存在性由本文件后面的断言强制，`
        + `.ks-empty-card 由 smoke-kb-pad-pixels.mjs 的 kb-empty-files 一组判）`
      : `**没量到**：${missingHere.join(' ')}（元素消失/改名 ⇒ 留边管不到它；量不到不算验过）`)
  check('页面留边：卡片带/表格容器/批量条/目录层/页头/按钮行/空态卡**全都在页面根之内**（跑到容器外面就说明留边管不到它）',
    outside.length === 0,
    presentSubjects.length === 0
      ? '这一跑一个适用面元素都没出现（那这条断言等于没判）'
      : `这一跑出现 ${presentSubjects.length} 类：${presentSubjects.join(',')}；越界：${JSON.stringify(outside)}`)
  check('页面留边：适用面元素没有用负外边距把留边抵消掉（负 margin 是"绕过留边"的典型写法）',
    negMargin.length === 0,
    negMargin.length === 0 ? '无负 margin' : negMargin.join(' | '))

  /* ══════════ 断言 2b–2g：**5h 新 IA**（业主 2026-09-20 亲口定的形态） ══════════
   * 为什么这一组必须在**原有断言之前**：默认态的**形状**变了 ——
   *   旧：左轨（两棵目录树 + 自建夹卡）→ 中间直接摆**文件表格**；
   *   新：顶部**卡片带**（一个框 + 左右翻页箭头）→ 下面是**目录层** → 走到**最末一级**才是表格。
   * ⇒ 下面原有那一整套断言（3 号起：勾选框 / ⋮ 菜单 / 真表格 / 列对齐 / 搜索过滤 / 批量条 /
   *   三日期 / 标签视图）**一条没删、一条没放宽**，只是前面**多走几步下钻**（见 `enterStdLeaf`）——
   *   "表格行为"那部分逐字保留。
   * ⚠ 这一组新增的断言钉的是**本轮头条**：卡片带 / 翻页到头的置灰 / 树与那句标签真的没了 /
   *   下钻出「返回上一级」。同样按"真控件/真状态"口径判，不是数类名。
   *
   * ⚠⚠ **5h-补（2026-09-20）就地改口径的断言**（业主把"滑动条"钉实：「所有卡片横在顶端，
   *   **一个小框下面自带一个左右翻页滑动条**」⇒ 窗口切片换成真滚动容器）：
   *   ① 原「卡片带：一屏 3 张卡，且第一屏时左箭头 disabled」—— "一屏 3 张"是**窗口切片**口径
   *      （`BAND_WINDOW=3` + `slice`），已随那个常量作废：现在全部卡片一次渲染进一个
   *      `overflow-x:auto` 容器，DOM 里恒为 5 张 ⇒ 旧判据 `length === 3` 在新实现下**必红且无意义**。
   *   ② 原「点右箭头翻到最后一屏 ⇒ 右箭头 disabled / 左箭头可用」与
   *      ③ 原「再翻回第一屏 ⇒ 左箭头又置灰」—— 语义变成"**按滚动位置**两端置灰"，
   *      合并进下面的 `withBandGeometry`（**假布局**桩：jsdom 没有布局引擎，
   *      `scrollWidth`/`clientWidth` 无条件返回 0 ⇒ 不装几何就永远走"没布局 ⇒ 箭头可用"那一支，
   *      两端状态**根本验不到**；同时另有一条断言钉"没布局时箭头必须可用"，那才是截图链上的真行为）。
   *   ⚠ **判据一条没放宽、一条没删**：5 张卡"一张不少"、树没了、标签没了都逐字保留，
   *     只把"每屏几张"这个**已经不存在**的概念从断言里去掉；新加的是"箭头真的驱动 scrollLeft /
   *     两端真置灰 / 说明文字是总张数口径"。
   */
  const bandCards = () => q('.ks-kb-cards .ks-kb-card')
  /* ⚠⚠ **2026-09-20 头条改口径：目录层从"卡片网格"改成"与文件列表同构的列表"**。
   * 业主原话：「把子目录文件夹的视图，做成和文件列表一样的视图」⇒ 目录不再是 `.ks-dir` 卡片按钮，
   * 而是 `.ks-list-dirs` 里的**行**（`.ks-item.ks-dir-row`），表头是同一个 `.ks-lhead`。
   * ⇒ 这里只换**选择器**（`.ks-dir` → `.ks-dir-row`），**判据一条没放宽**：下面每一条断言
   *   原来数几张"目录卡"、现在就数几行"目录行"，期望条数**逐字不变**。
   * ⚠ 为什么用 `.ks-dir-row`（而不是裸 `.ks-item`）：文件层的行也是 `.ks-item` ——
   *   必须能分辨"这一行的身份是目录"还是"是文件"（否则"目录层显示 3 个目录、0 行文件"
   *   这类断言会自我打脸）。`.ks-dir-row` 是目录行的**身份类**。
   * ⚠ 目录名的选择器从 `.ks-dir-name` 换到 `.ks-col-dname .ks-dir-name`：`.ks-dir-name`
   *   这个名字**保留**在目录行的名字元素上（旧锚点不完全作废），但行里另有路径那一行，
   *   按"列"定位更准（列身份归 DIR_COLUMNS）。 */
  const dirEls = () => q('.ks-dir-row')
  const dirNameOf = (row) => (row?.querySelector('.ks-col-dname .ks-dir-name')?.textContent ?? '').trim()
  /* **文件行**（目录层的行也是 `.ks-item` ⇒ 这两件事从此必须分开数）。
   * 文件行的身份类是 `.ks-check`（文件名就是宿主 Checkbox 的可见 label，见 KsKnowledgePage.tsx
   * 的 name 分支）—— 目录行**没有**勾选框（它的整行是 button），所以这条区分是稳的。
   * ⚠ 下面凡是"这一层有几行**文件**"的断言，一律走 fileRows()；凡是要"当前可见行总数"的
   *   （例如批量选择、搜索过滤文件名），也一律走 fileRows() —— 它们在**文件层**跑，
   *   那一层本来就没有目录行。 */
  const fileRows = () => q('.ks-item').filter((row) => row.querySelector('.ks-check') !== null)
  const navBtn = (which) => q('.ks-kbband-nav').find((b) => (b.getAttribute('aria-label') ?? '').includes(which))
  /** 按**卡名**找那一张卡（名字在 `.ks-kb-ct` 里；卡上还有描述与篇数 ⇒ 整卡文本不能直接比对）。 */
  const cardNamed = (name) => bandCards().find((el) => (el.querySelector('.ks-kb-ct')?.textContent ?? '').trim() === name)
  const namesIn = (sel) => q(sel).map((el) => (el.querySelector('.ks-kb-ct')?.textContent ?? '').trim())
  /** 一个元素的 computed 属性（`null` 元素 ⇒ `null`；取不到值本身不算"相同"）。 */
  const csOf = (el, prop) => el === null ? null : dom.window.getComputedStyle(el).getPropertyValue(prop)
  const seenCards = new Set(namesIn('.ks-kb-cards .ks-kb-card'))
  check('卡片带：**全部 5 张库卡一次渲染进同一个横向滚动容器**（不再是"一屏 3 张"的窗口切片）',
    bandCards().length === 5 && q('.ks-kbband-clip').length === 1
    && seenCards.size === 5
    && ['标准', '法律法规', '公司制度', '内部操作规程', '供应商资料'].every((n) => seenCards.has(n)),
    `卡 ${bandCards().length} 张：${[...seenCards].join(' / ')}；滚动容器 ${q('.ks-kbband-clip').length} 个`)

  /* ── 断言 2b-2：**卡片尺寸统一**（5i 2026-09-20 收尾批；复核 `verify-freeze-5h` 的变异取证） ──
   * 为什么补这一条：复核把卡片带里 `.ks-kb-cards` 的列模板改成 `60px 120px 200px`（三张卡三种宽）
   * 之后，**渲染冒烟 51/51 仍然全绿** —— 因为 `.ks-kb-cards` 的宽度只有一个**报告值**
   * （`ui-render-shot.mjs` 的 `#cards`）兜着，**全仓没有一条断言引用它**。而"知识库卡片尺寸统一"
   * 是业主亲口点名的形态 ⇒ 它当时**没有被任何断言钉住**。
   * 本批按**新实现**（`flex:0 0 var(--ks-band-card-w)`，横向滚动容器）造断言：
   *   · **这一条（jsdom 侧）判**：5 张卡 computed `flex` 简写**逐字相同**且非空 —— `flex` 是
   *     卡宽的**唯一声明来源**（`.ks-kbband .ks-kb-card`），也是 jsdom 会级联的属性（实测：`var()`
   *     不会被解析成像素，但**声明串**原样给出 ⇒ 判"是不是同一条声明"，与 3e-2 判列模板同一口径）。
   *     ⇒ 任何"给某一张卡单独钉一个宽"的改动（例如 `.ks-kb-card:nth-child(2){flex:0 0 60px}`）
   *     在这里**必红**。同时钉 `min-height`（等高那一路的兜底声明）也要逐字相同。
   *   · **这一条不判**：真像素的等宽/等高 —— jsdom **没有布局引擎**，`getBoundingClientRect` 恒 0。
   *     真 Chrome 侧的实测断言在 `ui-render-shot.mjs` 的 `#kbcards`（`cardsCheck`，三档由
   *     `smoke-kb-cols.mjs` 逐档跑）。两边一起，"尺寸统一"才算被钉住（缺一边都只是半个证据）。
   *   · 等高的**结构前提**（`align-items:stretch`）单独一条：jsdom 量不到高，只能钉住这条前提。
   * 变异证据（本批实测，见 docs/UI-BASELINE.md 5i）：
   *   给第 2 张卡加 `.ks-kbband .ks-kb-card:nth-child(2){flex:0 0 60px}` ⇒ 本文件 FAIL（flex 数组
   *   第 2 项变 `0 0 60px`）、`ui-render-shot` 的 cardsCheck 也 FAIL（宽度 172/60/172…）；还原即绿。
   */
  const bandFlex = bandCards().map((el) => dom.window.getComputedStyle(el).getPropertyValue('flex').trim())
  const bandMinH = bandCards().map((el) => dom.window.getComputedStyle(el).getPropertyValue('min-height').trim())
  check('卡片带：5 张卡的 computed `flex`（卡宽的唯一声明）与 `min-height` **逐字相同** —— 任一卡被单独改歪就红',
    bandCards().length === 5
    && bandFlex.every((v) => v !== '' && v === bandFlex[0])
    && bandMinH.every((v) => v !== '' && v === bandMinH[0]),
    `flex = ${JSON.stringify(bandFlex)}；min-height = ${JSON.stringify(bandMinH)}`)
  const bandCardsBox = container.querySelector('.ks-kbband .ks-kb-cards')
  const bandAlign = bandCardsBox === null ? null : dom.window.getComputedStyle(bandCardsBox).getPropertyValue('align-items').trim()
  check('卡片带：容器 `.ks-kb-cards` 的 `align-items` 是 **stretch**（同排等高的前提；像素级等高由 ui-render-shot 判）',
    bandAlign === 'stretch', `align-items = ${JSON.stringify(bandAlign)}`)

  /**
   * **假布局**：jsdom 没有布局引擎 —— `Element-impl` 的 `scrollWidth`/`clientWidth` 是无条件
   * `return 0`。不给它装上几何，`bandNoLayout` 恒真 ⇒ 两端置灰**永远验不到**。
   * 装的是一份**最小滚动几何**：两个宽/位置的存取器 + 一个让 `scrollBy` 真的改变 `scrollLeft`
   * 的桩（jsdom 的 Element **没有** `scrollBy` 方法 —— 组件里那条 `typeof clip.scrollBy ===
   * 'function'` 的兜底就是为它写的：真机走 scrollBy，这里走 `scrollLeft +=`）。
   * ⚠ 用完（含断言抛错）**一定还原**：桩留在 `HTMLElement.prototype` 上会污染后面所有断言。
   */
  const withBandGeometry = async (fn) => {
    const clip = q('.ks-kbband-clip')[0]
    const proto = dom.window.HTMLElement.prototype
    const had = {
      sw: Object.getOwnPropertyDescriptor(proto, 'scrollWidth'),
      cw: Object.getOwnPropertyDescriptor(proto, 'clientWidth'),
      sb: Object.getOwnPropertyDescriptor(proto, 'scrollBy'),
    }
    const geom = { scrollWidth: 908, clientWidth: 640 }
    Object.defineProperty(proto, 'scrollWidth', {
      configurable: true, get() { return this === clip ? geom.scrollWidth : 0 },
    })
    Object.defineProperty(proto, 'clientWidth', {
      configurable: true, get() { return this === clip ? geom.clientWidth : 0 },
    })
    Object.defineProperty(proto, 'scrollBy', {
      configurable: true,
      value(opt) {
        if (this !== clip) return
        const by = typeof opt === 'number' ? opt : ((opt && opt.left) ?? 0)
        const max = geom.scrollWidth - geom.clientWidth
        this.scrollLeft = Math.max(0, Math.min(max, this.scrollLeft + by))
      },
    })
    try {
      clip.scrollLeft = 0
      clip.dispatchEvent(new dom.window.Event('scroll'))
      await flush()
      return await fn(geom)
    } finally {
      for (const [key, desc] of [['scrollWidth', had.sw], ['clientWidth', had.cw], ['scrollBy', had.sb]]) {
        if (desc === undefined) delete proto[key]
        else Object.defineProperty(proto, key, desc)
      }
    }
  }

  /** 滚动位置 + 两个箭头的置灰态（一次读齐，免得三处各读一遍时机不同）。 */
  const bandState = () => {
    const clip = q('.ks-kbband-clip')[0]
    return {
      left: Math.round(clip.scrollLeft),
      atStart: navBtn('上一张').disabled === true,
      atEnd: navBtn('下一张').disabled === true,
    }
  }
  /* ⚠ 这里**先不装几何**跑一条：那才是 jsdom 截图链的真实环境（`scrollWidth` 恒 0）。 */
  check('卡片带：**没布局的环境（jsdom 截图链）里箭头保持可用** —— 那是渲染链限制，不是"忘了置灰"',
    navBtn('上一张').disabled === false && navBtn('下一张').disabled === false
    && q('.ks-kbband-clip')[0].scrollWidth === 0,
    `左 disabled=${String(navBtn('上一张').disabled)} / 右 disabled=${String(navBtn('下一张').disabled)}`
    + ` / scrollWidth=${String(q('.ks-kbband-clip')[0].scrollWidth)}（jsdom 无布局 ⇒ 恒为 0）`)
  await withBandGeometry(async (geom) => {
    const s0 = bandState()
    check('卡片带（装几何）：**停在最左 ⇒ 左箭头置灰、右箭头可用**（"到两端就置灰"在新实现下仍成立）',
      s0.left === 0 && s0.atStart === true && s0.atEnd === false,
      `scrollLeft=${String(s0.left)} / 左 disabled=${String(s0.atStart)} / 右 disabled=${String(s0.atEnd)}`
      + `（几何 scrollWidth=${String(geom.scrollWidth)} clientWidth=${String(geom.clientWidth)}）`)
    const before = q('.ks-kbband-clip')[0].scrollLeft
    await click(navBtn('下一张'))
    await flush(); await flush()
    const moved = q('.ks-kbband-clip')[0].scrollLeft
    check('卡片带（装几何）：点右箭头 ⇒ **scrollLeft 真的增大**（箭头驱动滚动，不是重渲染窗口）',
      moved > before,
      `scrollLeft ${String(before)} → ${String(moved)}（可滚上限 ${String(geom.scrollWidth - geom.clientWidth)}）`)
    for (let i = 0; i < 6; i += 1) await click(navBtn('下一张'))
    await flush(); await flush()
    const sEnd = bandState()
    check('卡片带（装几何）：滚到最右 ⇒ **右箭头置灰**、左箭头可用（另一端同样成立）',
      sEnd.left > 0 && sEnd.atEnd === true && sEnd.atStart === false,
      `scrollLeft=${String(sEnd.left)}（上限 ${String(geom.scrollWidth - geom.clientWidth)}）`
      + ` / 左 disabled=${String(sEnd.atStart)} / 右 disabled=${String(sEnd.atEnd)}`)
    /* ⚠ 连点 6 次右箭头后 `scrollLeft` 必须**恰好停在上限**：真机的 `scrollBy` 自己会夹，
       但**不能指望**每个实现都夹（jsdom 那类不夹 ⇒ 会累加成 3680 这种假数）⇒ 组件里自己夹。
       这一条就是这个"自己夹"的断言（只靠"到两端置灰"是盖不住它的）。 */
    check('卡片带（装几何）：连点到头后 `scrollLeft` **恰好等于上限**（自己夹住，不靠浏览器夹）',
      sEnd.left === geom.scrollWidth - geom.clientWidth,
      `scrollLeft=${String(sEnd.left)} / 上限=${String(geom.scrollWidth - geom.clientWidth)}`)
    for (let i = 0; i < 6; i += 1) await click(navBtn('上一张'))
    await flush(); await flush()
    const sBack = bandState()
    check('卡片带（装几何）：再滚回最左 ⇒ 左箭头**又**置灰（置灰随滚动位置变，不是一次性状态）',
      sBack.left === 0 && sBack.atStart === true,
      `scrollLeft=${String(sBack.left)} / 左 disabled=${String(sBack.atStart)} / 右 disabled=${String(sBack.atEnd)}`)
  })
  /* ⚠ 桩撤了以后**这里故意不再断言箭头置灰**：组件的"有没有布局"是**锁存**的（第一次量到就翻
     true；真机上布局不会消失），撤桩后它仍停在"有布局"那一支 ⇒ 那是**桩的残留**，不是产品行为。
     而箭头 `disabled` 的 DOM 属性要 React 再渲染一次才会跟着变，所以此刻读到的是"装的几何下"那一态。
     **不许**为了让这里变绿去补一次 flush —— 那只会把"桩的残留"伪造成一条产品断言。
     "没布局 ⇒ 箭头可用"那条链已在上面的前置断言里验过（那时还没装桩）。 */
  await flush()

  check('卡片带：全部卡片一次渲染 ⇒ **5 张库卡**（标准 / 法律法规 / 3 个自建夹）一张不少',
    seenCards.size === 5
    && ['标准', '法律法规', '公司制度', '内部操作规程', '供应商资料'].every((n) => seenCards.has(n)),
    `见到的卡：${[...seenCards].join(' / ')}`)
  check('业主点名要删的东西真的没了：**没有目录树**（.ks-kb-tline = 0），也没有「我建的（真文件夹…）」那句标签',
    q('.ks-kb-tline').length === 0 && q('.ks-kb-tree').length === 0
    && !(container.textContent ?? '').includes('我建的（真文件夹'),
    `树节点 ${q('.ks-kb-tline').length} 个 / .ks-kb-tree ${q('.ks-kb-tree').length} 个 / `
    + `含「我建的（真文件夹」=${String((container.textContent ?? '').includes('我建的（真文件夹'))}`)
  check('卡片带：下面那行说明文字是**总张数口径**（"共 5 张 · 可左右滑动或点箭头翻页"），不再是"1-3/共 5 张"',
    (container.textContent ?? '').includes('共 5 张 · 可左右滑动或点箭头翻页')
    && !/卡片\s*1\s*[–-]\s*3/.test(container.textContent ?? ''),
    `说明行：「${(q('.ks-kb-hint')[0]?.textContent ?? '').trim()}」`)

  /* ══════════ 断言 2f–2g：**点卡片 = 进入该库 + 按目录逐级下钻** ══════════
   * 业主原话：「点一个卡片就出来知识库内容，比如点法律法规，就按目录展示，先占上一级目录文件夹，
   * 然后点开是二级目录，进入二级目录就自动出现返回上一级的按钮」。
   * ⚠ 用「法律法规」这一支取证：它的占位数据是**恰好三级目录 + 文件**（法律 → 宪法与行政法 →
   *   安全生产 = 文件层），能把"一级 → 二级 → 文件"整条路走完。 */
  check('默认态：显示**一级目录**（标准库的 3 个 CCS 大类），**不是**直接铺文件',
    dirEls().length === 3 && fileRows().length === 0 && q('.ks-lhead').length === 1,
    `目录行 ${dirEls().length} 行 / 文件行 ${fileRows().length} / 表头 ${q('.ks-lhead').length}`)
  /* ── 断言 2f-1/2f-2（**2026-09-20 头条新增**）：目录层 = **与文件列表同构的列表** ──
   * 业主原话：「把子目录文件夹的视图，做成和文件列表一样的视图」。
   * 为什么必须补这一组：本批之前"目录层是不是列表"**没有任何断言**（它是卡片网格，
   * 而断言只数 `.ks-dir` 的个数）⇒ 把它改回卡片网格，旧断言照样全绿。
   * 这一组按**结构**判（不是像素，像素由 ui-render-shot 的 `#cols`/`#kspad` 判）：
   *   ① 容器是**同一套类** `.ks-list`（+.ks-list-dirs）+ 一条**自己的** `--ks-cols`；
   *   ② 表头与**每一行**都按 DIR_COLUMNS 渲染 ⇒ cell 类名序列**逐字相同**（与文件层 3d 同口径）；
   *   ③ 列模板仍然**只有一个所有者**：行/表头都只写 grid-template-columns:var(--ks-cols)，
   *      且两者的 computed 值**逐字相同**（与文件层 3e-2 同口径）—— 谁偷偷另写一套列宽就红。 */
  const dirList = container.querySelector('.ks-list-dirs')
  const dirHeadCells = dirList === null ? [] : [...(dirList.querySelector('.ks-lhead')?.children ?? [])].map((c) => c.className)
  const dirRowCells = dirEls().map((row) => [...row.children].map((c) => c.className))
  check('目录层：容器是**同一套列表类** `.ks-list`（+`.ks-list-dirs`），表头是同一个 `.ks-lhead`，行是 `.ks-item.ks-dir-row`',
    dirList !== null && dirList.classList.contains('ks-list')
    && dirList.querySelector('.ks-lhead') !== null
    && dirEls().length === 3 && dirEls().every((row) => row.classList.contains('ks-item'))
    && dirEls().every((row) => row.tagName === 'BUTTON'),
    `容器类名=${JSON.stringify(dirList?.className ?? null)}；表头 ${dirList?.querySelectorAll('.ks-lhead').length ?? 0} 个；`
    + `行 ${dirEls().length} 行（都是 button=${String(dirEls().every((r) => r.tagName === 'BUTTON'))}）`)
  check('目录层：表头与**每一行**的 cell 类名序列**逐字相同**（两侧都按同一份 DIR_COLUMNS 渲染，列数 3）',
    dirHeadCells.length === 3 && dirRowCells.length === 3
    && dirRowCells.every((cs) => JSON.stringify(cs) === JSON.stringify(dirHeadCells)),
    `表头 ${JSON.stringify(dirHeadCells)}；第 1 行 ${JSON.stringify(dirRowCells[0] ?? [])}`)
  check('目录层：列头文案就是「目录 / 篇数」（第 3 列无列头，与文件层的 ⋮ 列同一种写法）',
    (dirList?.querySelector('.ks-lhead')?.textContent ?? '').includes('目录')
    && (dirList?.querySelector('.ks-lhead')?.textContent ?? '').includes('篇数'),
    (dirList?.querySelector('.ks-lhead')?.textContent ?? '').replace(/\s+/g, ' '))
  const dirHeadEl = dirList?.querySelector('.ks-lhead') ?? null
  const dirRowEl = dirEls()[0] ?? null
  const dirTpl = csOf(dirHeadEl, 'grid-template-columns')
  const dirRowTpl = csOf(dirRowEl, 'grid-template-columns')
  const dirGap = csOf(dirHeadEl, 'column-gap')
  const dirRowGap = csOf(dirRowEl, 'column-gap')
  /* ⚠ 与文件层**必须不同**：目录层的 --ks-cols 是 3 列（文件层是 3 或 5 列）。
   * ⚠⚠ **2026-09-21 就地更正（复核 verify-freeze-dirlist 的变异 M5 打回）：下面这条原来那句
   *   `dirTpl !== 文件层表头模板` 是「注释声称有牙、实测没牙」的恒真死子句** ——
   *   jsdom **不解析 `var()`**（两侧 computed 都拿不到解析后的轨道），而且**目录层这一刻根本没有文件层**
   *   ⇒ 右边恒为 null、式子恒真。复核实测：把目录层的 `--ks-cols` 换成文件层那 5 列（首列 344→88px、
   *   168px 死白），本文件 **84/84 全绿**、真 Chrome 的 `#cols` 自检也过。
   * ⇒ 真判据换成**读样式表里那两份 `--ks-cols` 声明**（列宽的唯一所有者就是它们）：目录层那份必须
   *   **正好 3 轨**，且**不许引用**文件层那套列变量（status/date/tags/more）。几何真相另由
   *   `ui-render-shot.mjs` 在真 Chrome 里量（轨道数 + 轨道和 + gap == 容器内容宽，见那边的 `#dircols`）。 */
  const tplTracks = (tpl) => {
    const out = []
    let depth = 0
    let cur = ''
    for (const ch of String(tpl ?? '')) {
      if (ch === '(') depth += 1
      if (ch === ')') depth -= 1
      if (/\s/.test(ch) && depth === 0) { if (cur !== '') { out.push(cur); cur = '' } continue }
      cur += ch
    }
    if (cur !== '') out.push(cur)
    return out
  }
  const cssRuleBody = (sel) => {
    const m = new RegExp(`${sel.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*\\{([^}]*)\\}`).exec(sheetText)
    return m === null ? null : m[1]
  }
  const cssColsOf = (sel) => {
    const body = cssRuleBody(sel)
    const m = body === null ? null : /--ks-cols\s*:\s*([^;}]+)/.exec(body)
    return m === null ? null : m[1].trim()
  }
  const dirColsDecl = cssColsOf('.ks-list-dirs')
  const fileColsDecl = cssColsOf('.ks-list')
  const dirTracks = tplTracks(dirColsDecl)
  const fileTracks = tplTracks(fileColsDecl)
  check('目录层：样式表里那份 --ks-cols 是**自己的 3 轨**（不引用文件层的 status/date/tags/more 列）',
    dirColsDecl !== null && dirTracks.length === 3
    && !/--ks-col-(status|date|tags|more)\b/.test(dirColsDecl)
    && dirColsDecl !== fileColsDecl,
    `目录层 --ks-cols=${JSON.stringify(dirColsDecl)}（${String(dirTracks.length)} 轨）；`
    + `文件层（窄档那条）--ks-cols=${JSON.stringify(fileColsDecl)}（${String(fileTracks.length)} 轨）；`
    + '⚠ 轨数**不是**判据：文件层窄档也是 3 轨（宽档才 5 轨）⇒ 判据是"目录层不引用文件层那套列变量"')
  check('目录层：表头行与目录行的 computed grid-template-columns / column-gap **逐字相同**',
    Boolean(dirTpl) && Boolean(dirRowTpl) && Boolean(dirGap) && Boolean(dirRowGap)
    && dirTpl === dirRowTpl && dirGap === dirRowGap,
    `目录 表头 ${JSON.stringify(dirTpl)} / 行 ${JSON.stringify(dirRowTpl)}；`
    + `gap 表头 ${JSON.stringify(dirGap)} / 行 ${JSON.stringify(dirRowGap)}`)
  /* ⚠⚠ **2026-09-21 新增（复核 verify-freeze-dirlist 的变异 M4 打回）**：目录行的**内容**原来一条断言都没有
   *   —— 把 `{child.key}` 那第二行加回去（内部键/内部路径直接印在名字下面）**整套 84 条全绿**。
   *   判据（"目录行只有名字"这件事必须可判），**两条都要**（复核第二轮各绕过一个）：
   *   ① 名字格只有 **2 个**子元素（图标 + 名字）；
   *   ② 名字格的 textContent **逐字等于**名字元素的 textContent；
   *   ③ **名字元素自己的文本必须等于它自己的 `title`**（title 就是显示名）—— 这条专治
   *      "把内部键**嵌进** `.ks-dir-name` 里面"那种换形状绕过（②对它无效：嵌进去之后两侧一起变）。
   *   ⚠⚠ **必须在每一层都判**（复核第二轮：只在 `path.length>0` 时加回第二行 ⇒ 本文件当时只查库根那 3 行
   *      ⇒ 整套 86/86 全绿，而真机页面上印着 `宪法与行政法法律/宪法与行政法`）⇒ 这个 helper 在
   *      **库根 / 一级 / 二级**三处 dir 层状态各调一次（见下面 `dirRowContentCheck` 的三次调用）。 */
  const dirNameCellOk = (row) => {
    const cell = row.querySelector('.ks-col-dname')
    const nameEl = cell?.querySelector('.ks-dir-name') ?? null
    const nameText = (nameEl?.textContent ?? '').trim()
    const nameTitle = (nameEl?.getAttribute('title') ?? '').trim()
    return cell !== null && nameEl !== null && cell.children.length === 2
      && cell.textContent.trim() === nameText
      && nameText !== '' && nameText === nameTitle
  }
  const dirRowContentCheck = (where) => {
    check(`目录层[${where}]：目录行**只有名字**（2 个子元素；名字文本 == 它自己的 title；不夹内部 key/路径）`,
      dirEls().length > 0 && dirEls().every(dirNameCellOk),
      dirEls().map((row) => {
        const cell = row.querySelector('.ks-col-dname')
        const nameEl = cell?.querySelector('.ks-dir-name') ?? null
        return `${String(cell?.children.length)} 个子元素／文本 ${JSON.stringify((cell?.textContent ?? '').trim())}`
          + `／title ${JSON.stringify(nameEl?.getAttribute('title') ?? null)}`
      }).join(' | '))
  }
  dirRowContentCheck('库根')
  /* ⚠⚠ 行高的**声明串**要在这里先量下来（此刻在目录层）：等会儿下钻到文件层再量文件行，
   *   两边比对 —— 不能在目录层就断言（那里没有文件行，写成"没有文件行就算过"= 恒真假绿）。 */
  const dirRowMinH = csOf(dirEls()[0] ?? null, 'min-height')
  /* ── 断言 2f-2b（**本批实测踩坑换来的**）：目录层的列样式**不许漏进表头** ──
   * 踩的是什么：目录名那一列的"嵌套 grid 两行"（16px 图标列 + 1fr）如果选择器写成
   *   .ks-list-dirs .ks-cell.ks-col-dname，它会**同时命中表头**那一格（类名一样）——
   *   表头的「目录」于是被挤进 16px 的第一列、**只剩一个「目」**。
   *   真 Chrome 实测：spClientW=16 / spScrollW=24（两个字的宽度是 24），图上只显示一个字。
   *   jsdom 没有布局引擎 ⇒ 量不到"挤没挤"，但**量得到 display**：表头那格在正确实现下是
   *   flex（来自 .ks-lhead .ks-cell），被那条规则命中时会变成 grid。
   * ⇒ 这一条判"表头每一格都是 flex（= 没被行内的 grid 样式漏进来）"。
   *   ⚠ 这是**结构级**判据（jsdom 能判的那种）；像素级由 ui-render-shot 的真 Chrome 判。 */
  const dirHeadDisplays = [...(dirList?.querySelector('.ks-lhead')?.children ?? [])]
    .map((c) => csOf(c, 'display').trim())
  check('目录层表头：每一格都没有被行内的列样式漏进来（display 必须是 flex，不是 grid）——「目录」只剩一个「目」就是这个坑',
    dirHeadCells.length === 3 && dirHeadDisplays.every((d) => d === 'flex'),
    `表头三格 display = ${JSON.stringify(dirHeadDisplays)}（正确 = 三个 flex）`)
  await click(cardNamed('法律法规'))
  check('点「法律法规」卡 ⇒ 进入该库、显示它的**一级目录**（法律 / 行政法规）；库根**没有**返回上一级按钮',
    dirEls().length === 2 && dirEls().map((el) => (el.textContent ?? '').trim()).join('|').includes('法律')
    && fileRows().length === 0 && q('.ks-back').length === 0,
    `一级目录 ${dirEls().length} 行；返回按钮 ${q('.ks-back').length} 个；`
    + `面包屑「${container.querySelector('.ks-crumb-path')?.textContent ?? '(没有)'}」`)
  /* ══════════ 断言 2f-3..2f-6（**2026-09-20 头条新增**）：**面包屑每一级都能点** ══════════
   * 业主原话：「标准 / P 土木、建筑 / P15/19 工程抗震、工程防火、人防工程 / P16 工程防火
   *   这种路径要**每一级都能点击跳转**」。
   * 此刻的准确状态：刚**进入「法律法规」库根**（还没下钻）⇒ 面包屑只有 **1 个条目**，
   *   它是**当前级**（库名「法律法规」，不可点）。⚠ 这正是"当前级不可点"最干净的一态：
   *   库根时**一个可点条目都没有**（没有上一级可回）。
   * 为什么必须补这一组：本批之前面包屑是**一整行纯文本 span**（`.ks-crumb-path`），
   *   "每一级能不能点"这件事**没有任何断言**（旧断言只比对那一行的 textContent）。
   * 按"真控件/真行为"判，不按类名数：
   *   ① 条目数 = 路径级数（库名 + 每一级目录，一个不落）；
   *   ② **当前级**必须是**不可点**的（不是 button；`aria-current` 标出"你现在在这"）；
   *   ③ 其余每一级都是**真 button**（Tab 可达、有 aria-label）；
   *   ④ 点某一级 ⇒ `path` 真的被切到那一层（按下一层的目录行/文件行回证，不只看面包屑自己）。 */
  const crumbBtns = () => q('.ks-crumb-go')
  const crumbHere = () => q('.ks-crumb-here')
  const crumbItems = () => q('.ks-crumb-path .ks-crumb-item')
  const crumbText = (el) => (el?.textContent ?? '').trim()
  check('面包屑（库根态）：1 个条目 = 库名「法律法规」，且它是**当前级 = 不可点**（0 个可点条目，没有上一级可回）',
    crumbItems().length === 1 && crumbText(crumbHere()[0]) === '法律法规'
    && crumbHere()[0].getAttribute('aria-current') === 'page' && crumbHere()[0].tagName !== 'BUTTON'
    && crumbBtns().length === 0,
    `条目 ${String(crumbItems().length)} 个（${crumbItems().map(crumbText).join(' | ')}）／`
    + `不可点 ${String(crumbHere().length)} 个／可点 ${String(crumbBtns().length)} 个；`
    + `aria-current=${JSON.stringify(crumbHere()[0]?.getAttribute('aria-current') ?? null)}`)
  await click(dirEls().find((el) => dirNameOf(el) === '法律'))
  check('面包屑（一级目录态）：**逐级**渲染成 2 个条目（库名 + 「法律」）；只有**末条**不可点，前 1 条是真 button',
    crumbItems().length === 2 && crumbItems().map(crumbText).join(' | ') === '法律法规 | 法律'
    && crumbHere().length === 1 && crumbText(crumbHere()[0]) === '法律'
    && crumbBtns().length === 1 && crumbText(crumbBtns()[0]) === '法律法规'
    && crumbBtns()[0].tagName === 'BUTTON'
    && (crumbBtns()[0].getAttribute('aria-label') ?? '').includes('法律法规'),
    `条目 ${String(crumbItems().length)} 个：${crumbItems().map(crumbText).join(' | ')}；`
    + `可点 ${String(crumbBtns().length)}：${crumbBtns().map((b) => b.getAttribute('aria-label') ?? '(无)').join(' | ')}；`
    + `不可点「${crumbHere().map(crumbText).join('/')}」`)
  check('面包屑**逐级写全**（`textContent` 与旧的一整行纯文本**逐字相同**：库名 / 一级，分隔符是独立的 `/`）',
    (container.querySelector('.ks-crumb-path')?.textContent ?? '') === '法律法规/法律',
    `面包屑 textContent「${container.querySelector('.ks-crumb-path')?.textContent ?? '(没有)'}」`
    + `（分隔符元素 ${String(q('.ks-crumb-sep').length)} 个）`)
  await click(crumbBtns()[0])  // 第 0 条 = 库名 ⇒ 回库根
  check('点面包屑第 0 级（库名）⇒ 真的回到**库根**（2 行一级目录：「法律」不再被选中，当前级回到库名）',
    dirEls().length === 2 && dirEls().map(dirNameOf).join('|') === '法律|行政法规'
    && q('.ks-crumb-go').length === 0 && crumbHere().length === 1 && crumbText(crumbHere()[0]) === '法律法规',
    `目录行 ${String(dirEls().length)}（${dirEls().map(dirNameOf).join('/')}）／`
    + `可点条目 ${String(q('.ks-crumb-go').length)} 个／当前级「${crumbHere().map(crumbText).join('/')}」`)
  await click(dirEls().find((el) => dirNameOf(el) === '法律'))
  /* ⚠ 又一处 dir 层状态（一级目录）：**内容判据必须在这里再判一次** —— 复核第二轮正是用
     "只在 path.length>0 时加回第二行"绕过了"只查库根那 3 行"的版本（真机上印出内部路径）。 */
  dirRowContentCheck('一级目录')
  await click(dirEls()[0])
  check('二级目录「宪法与行政法」里还有**第三级目录**（安全生产）—— 法律这一支的占位数据就是三级',
    dirEls().length === 1 && dirNameOf(dirEls()[0]) === '安全生产' && fileRows().length === 0
    && crumbItems().length === 3,
    `目录行 ${String(dirEls().length)} 行（${dirEls().map(dirNameOf).join('/')}）/ 文件行 ${String(fileRows().length)}；`
    + `面包屑条目 ${String(crumbItems().length)} 个；`
    + `面包屑「${container.querySelector('.ks-crumb-path')?.textContent ?? '(没有)'}」`)
  dirRowContentCheck('二级目录')   // 第三层级（安全生产）：再判一次内容
  await click(dirEls()[0])   // 再下一级：安全生产（文件层）
  check('面包屑（文件层）：4 个条目（库名 + 3 级目录），**前 3 条都是真 button**，只有末条「安全生产」不可点',
    crumbItems().length === 4 && crumbBtns().length === 3 && crumbHere().length === 1
    && crumbText(crumbHere()[0]) === '安全生产'
    && crumbBtns().map(crumbText).join('|') === '法律法规|法律|宪法与行政法'
    && fileRows().length === 2,
    `条目 ${String(crumbItems().length)}：${crumbItems().map(crumbText).join(' | ')}；`
    + `可点 ${String(crumbBtns().length)}／当前级「${crumbHere().map(crumbText).join('/')}」`)
  /* 点**第 2 级**（「宪法与行政法」）⇒ 从 4 层切回前 2 级：这一层应当又只剩「安全生产」1 个子目录，
   * 且当前级变成「宪法与行政法」。⚠ 这条是"点第 i 级回到第 i 层"的**正向**取证
   * （不是只看面包屑变短 —— 它按下一层的目录行回证）。 */
  await click(crumbBtns()[2])
  check('点面包屑第 2 级（「宪法与行政法」）⇒ 真的切回那一层（当前级变了，且它下面只剩「安全生产」1 行）',
    crumbItems().length === 3 && crumbText(crumbHere()[0]) === '宪法与行政法'
    && dirEls().length === 1 && dirNameOf(dirEls()[0]) === '安全生产' && fileRows().length === 0,
    `当前级「${crumbHere().map(crumbText).join('/')}」／目录行 ${String(dirEls().length)} 行`
    + `（${dirEls().map(dirNameOf).join('/')}）／文件行 ${String(fileRows().length)}`)
  await click(dirEls()[0])
  check('再下一级（安全生产）才是**文件表格**：表头 1 个 + 2 行（安全生产法 / 消防法），返回按钮仍在',
    q('.ks-lhead').length === 1 && fileRows().length === 2 && q('.ks-back').length === 1
    && q('.ks-dir-row').length === 0,
    `表头 ${String(q('.ks-lhead').length)} / 文件行 ${String(fileRows().length)} / 目录行 ${String(q('.ks-dir-row').length)} / 返回 ${String(q('.ks-back').length)}；`
    + `面包屑「${container.querySelector('.ks-crumb-path')?.textContent ?? '(没有)'}」`)
  const crumbFiles = container.querySelector('.ks-crumb-path')?.textContent ?? ''
  /* ⚠ **期望串里的空格没了，这是本批的**可见改动**，不是判据放宽**：
   * 改前面包屑是**一整行纯文本**（`[kb.name, ...pathNames].join(' / ')` ⇒ 段间是 " / "）；
   * 改后每一级是独立条目、分隔符是独立的 `<span class="ks-crumb-sep">/</span>`
   * （**看不到空白**：两条 entry 之间若插一个纯文本空格，在 flex 行里会**多出一个匿名
   * 文本项**、在段之间顶出空隙，那是版式 bug）。⇒ 拼接后的字符串就是
   * `法律法规/法律/宪法与行政法/安全生产`。
   * 判据本身**没有放宽**：仍然是"**逐字**等于库名 + 每一级目录名，一个不落"；
   * 级数与各级名字若有任何缺失/错位，这一条照样红（要"更宽"反而应该去比对各条目，
   * 上面那几条已经逐条比过了）。 */
  check('文件层的面包屑**逐级写全**（库名 + 每一级目录名，一个不落）',
    crumbFiles === '法律法规/法律/宪法与行政法/安全生产', `面包屑「${crumbFiles}」`)
  await click(q('.ks-back')[0])
  check('点「返回上一级」⇒ 真的回到**上一级目录层**（1 行目录、0 行文件），按钮仍在',
    dirEls().length === 1 && fileRows().length === 0 && q('.ks-back').length === 1,
    `目录行 ${dirEls().length} / 文件行 ${fileRows().length} / 返回 ${q('.ks-back').length}；`
    + `面包屑「${container.querySelector('.ks-crumb-path')?.textContent ?? '(没有)'}」`)
  await click(q('.ks-back')[0])
  check('再点一次 ⇒ 又上一层（1 行目录：宪法与行政法），按钮仍在',
    dirEls().length === 1 && fileRows().length === 0 && q('.ks-back').length === 1
    && dirNameOf(dirEls()[0]) === '宪法与行政法',
    `目录行 ${dirEls().length} / 返回 ${q('.ks-back').length}；`
    + `面包屑「${container.querySelector('.ks-crumb-path')?.textContent ?? '(没有)'}」`)
  await click(q('.ks-back')[0])
  check('第三次「返回上一级」⇒ 回到库根（2 行一级目录），按钮**消失**（库根没有上一级）',
    dirEls().length === 2 && q('.ks-back').length === 0,
    `目录行 ${dirEls().length} / 返回按钮 ${q('.ks-back').length}；`
    + `面包屑「${container.querySelector('.ks-crumb-path')?.textContent ?? '(没有)'}」`)

  /* ⚠ 从这里往下，全部是**原有的表格断言**（判据一字未放宽；只把"数文件行"改成 fileRows()，
   * 因为目录行现在也是 `.ks-item`）——先把页面开回
   * 「标准 → P 土木、建筑 → P15/19… → P16 工程防火」，那一层有 **4 篇**文件。 */
  const enterStdLeaf = async () => {
    await click(dirEls().find((el) => dirNameOf(el).includes('P 土木、建筑')))
    await click(dirEls().find((el) => dirNameOf(el).includes('P15/19')))
    await click(dirEls().find((el) => dirNameOf(el).includes('P16 工程防火')))
  }
  /* ⚠⚠ **2026-09-21 第三轮（复核 verify-freeze-dirlist-guards2 的 C④b 打回）：内容判据要**覆盖全部库**。**
     复核造的绕过：把泄漏**按库**加上（只在 `kb.name === '标准'` 且 `path.length > 0` 时加回第二行）⇒
     本文件当时只在**主流程走到的那三个层**判 ⇒ **整套 88/88 全绿**，而真机上照样印内部路径
     （复核独立扫描实测 `P15/19 工程抗震…P 土木、建筑/P15/19 工程抗震…4 篇`）。
     ⇒ 这里**遍历卡片带里的每一个库**：进库 → 在它的目录层判一次；有更深一层就再下钻判一次。
     判据本身没变（还是 `dirRowContentCheck`），变的是**覆盖面** —— 这正是"按库加回"绕不过去的原因。
     ⚠ 位置很讲究：**必须放在 kb 页还挂着、且 `cardNamed` / 目录行 helper 都在**的地方（我第一版放在文件末尾，
     那时页面已切到能力页 ⇒ `.ks-kb-cards` 查不到 ⇒ **循环空转、一条都没跑**）。下面两条"覆盖面"断言
     就是给这种空转兜底的（跑不到 5 张卡 / 内容判据少于 3 次 ⇒ 红）。 */
  const libNames = namesIn('.ks-kb-cards .ks-kb-card')
  check('内容判据覆盖全部库：卡片带里能查到全部 5 张库卡（查不到 ⇒ 循环会空转，那是假绿）',
    libNames.length === 5, `查到 ${String(libNames.length)} 张：[${libNames.join('|')}]`)
  let dirContentChecks = 0
  for (const lib of libNames) {
    await click(cardNamed(lib))
    if (dirEls().length > 0) {
      dirRowContentCheck(`库「${lib}」根`)
      dirContentChecks += 1
      await click(dirEls()[0])
      if (dirEls().length > 0) { dirRowContentCheck(`库「${lib}」下钻一级`); dirContentChecks += 1 }
    }
  }
  check('内容判据的覆盖面：至少真的判过 3 次目录层（占位数据里 标准/法律法规 各有目录层）',
    dirContentChecks >= 3, `实判 ${String(dirContentChecks)} 次（库：${libNames.join('|')}）`)
  await click(cardNamed('标准'))
  check('点回「标准」卡 ⇒ 回到它的库根（一级目录 3 行）——换库后层级归零',
    dirEls().length === 3 && q('.ks-back').length === 0,
    `目录行 ${dirEls().length} / 返回按钮 ${q('.ks-back').length}`)
  await enterStdLeaf()
  check('下钻到最末一级（标准 / P 土木、建筑 / P15/19… / P16 工程防火）⇒ 4 行文件 + 表头 1 个 + 返回上一级在',
    fileRows().length === 4 && q('.ks-lhead').length === 1 && q('.ks-back').length === 1,
    `行 ${fileRows().length} / 表头 ${q('.ks-lhead').length} / 返回 ${q('.ks-back').length}；`
    + `面包屑「${container.querySelector('.ks-crumb-path')?.textContent ?? '(没有)'}」`)
  /* ── 断言 2f-7：目录行与文件行的**行高是同一个 token**（"和文件列表一样的视图"最硬的一条）──
   * ⚠ jsdom 没有布局 ⇒ 这里判的是两层的 computed `min-height` **声明串逐字相同**
   *   （真像素由 ui-render-shot.mjs 在真 Chrome 里量 `.ks-item` 的几何）。
   *   ⇒ 谁给目录行单独拍一个行高（例如 40px），这一条必红。 */
  check('目录行与文件行的 computed `min-height` **逐字相同**（同一个行高 token ⇒ 同一个列表机制）',
    Boolean(dirRowMinH) && dirRowMinH === csOf(fileRows()[0] ?? null, 'min-height'),
    `目录行 ${JSON.stringify(dirRowMinH)} / 文件行 ${JSON.stringify(csOf(fileRows()[0] ?? null, 'min-height'))}`)

  /* ══════════ 断言 2h–2o：**搜索框每一层都在**（5i 2026-09-20 收尾批） ══════════
   * 业主 2026-09-20 只说「搜索框：保留」、**没限定层级** ⇒ 本批按"保留"的**最强解释**执行：
   * 库根 / 一级目录 / 二级目录 / 文件层**每层常驻**（目录层过滤**目录名**、文件层过滤标准号/名称）。
   * 为什么必须补这一组：本批之前只有**最末一级（文件层）**有 `.ks-search`，而"哪一层该有框"
   * 没有任何断言盯着 —— 目录层有没有框，删了/没做都照样绿。
   * ⚠ **判据一条没放宽**：`CTRL_SEL`（行内可见控件 ≤3）数的是 `.ks-item` 行**内部**，目录层的
   *   搜索框不在行里 ⇒ 3b 那条原样保留、原样跑（本块一个字都没动它）。
   * ⚠ **搜索词的处置口径**（唯一所有者：KsKnowledgePage.tsx 顶部第 4b 条）：
   *   切库清空 / 同库内下钻与返回上级**保留** / 切状态筛选**保留**（搜索与筛选是 AND）——
   *   三条在下面逐条取证，不是写在注释里就算。
   * ⚠ 本块跑完必须把页面**还原**到"文件层 / 4 行 / 筛选=全部 / 搜索为空"（后面断言 3 起一字未改地跑）。
   */
  const searchInput = () => container.querySelector('.ks-search input')
  const searchValue = () => searchInput()?.value ?? '(没有搜索框)'
  check('搜索框（文件层）：宿主 Input 在，且 placeholder 指向**文件**口径（标准号或名称）',
    searchInput() !== null && (searchInput().placeholder ?? '').includes('标准号或名称'),
    `框 ${searchInput() === null ? '不在' : '在'}／placeholder「${searchInput()?.placeholder ?? ''}」`)
  await setInput(searchInput(), '喷水')
  check('文件层搜索真的过滤：4 行 →（「喷水」）1 行',
    fileRows().length === 1, `行数 4 → ${fileRows().length}`)
  // ── 2j：返回上一级 ⇒ 搜索词**保留**，并且它按**目录名**过滤 ──
  await click(q('.ks-back')[0])
  const keptValue = searchValue()
  const dirsKept = dirEls().length
  const dirEmptyTitle = container.querySelector('.ks-empty-t')?.textContent ?? '(没有空态卡)'
  check('二级目录层：搜索框在、返回上级**保留**搜索词，且「喷水」在目录名上一个也不命中 ⇒ 目录层空态',
    searchInput() !== null && keptValue === '喷水' && dirsKept === 0
    && dirEmptyTitle === '没有符合搜索的目录',
    `框里还是「${keptValue}」／目录卡 1 → ${dirsKept} 张／空态「${dirEmptyTitle}」`)
  await setInput(searchInput(), '')
  check('二级目录层：清空搜索 ⇒ 目录恢复（P15/19 这一层 1 张）',
    dirEls().length === 1, `目录卡 ${dirEls().length} 张`)
  // ── 2l：上一级（一级目录层）同样有框，同一个词按目录名命中/落空 ──
  await click(q('.ks-back')[0])
  await setInput(searchInput(), '环境')
  const l1None = dirEls().length
  const l1Empty = container.querySelector('.ks-empty-t')?.textContent ?? '(没有空态卡)'
  await setInput(searchInput(), 'P15')
  const l1Hit = dirEls().length
  await setInput(searchInput(), '')
  check('一级目录层：搜索框在；「环境」0 张（+空态）→「P15」1 张 → 清空恢复 1 张',
    searchInput() !== null && l1None === 0 && l1Empty === '没有符合搜索的目录'
    && l1Hit === 1 && dirEls().length === 1,
    `「环境」${l1None} 张（空态「${l1Empty}」）／「P15」${l1Hit} 张／清空后 ${dirEls().length} 张`)
  // ── 2m：库根（一级目录 3 张）── 正向命中 + 切库清空 ──
  await click(q('.ks-back')[0])
  const rootAll = dirEls().length
  await setInput(searchInput(), '环境')
  const rootHit = dirEls().length
  const rootHitName = dirEls()[0]?.querySelector('.ks-dir-name')?.textContent ?? '(没有)'
  check('库根：搜索框在；3 张一级目录 →（「环境」）1 张（Z 环境保护）',
    searchInput() !== null && rootAll === 3 && rootHit === 1 && rootHitName.includes('Z 环境保护'),
    `目录卡 ${rootAll} → ${rootHit} 张；留下的是「${rootHitName}」`)
  await click(cardNamed('法律法规'))
  check('切库 ⇒ 搜索词**清空**（整棵树都换了，留着就是对**新库**的幽灵过滤）',
    searchValue() === '' && dirEls().length === 2,
    `切到「法律法规」后框里「${searchValue()}」／一级目录 ${dirEls().length} 张`)
  // ── 2n：切筛选档 ⇒ 搜索词**保留**（两者是 AND，不清空） ──
  await click(cardNamed('标准'))
  await enterStdLeaf()
  await setInput(searchInput(), '喷水')
  await click(byText('.ks-chip', '已废止'))
  const andValue = searchValue()
  const andRows = fileRows().length
  check('切状态筛选档 ⇒ 搜索词**保留**，两个条件是 AND（「喷水」是现行件；点「已废止」⇒ 0 行）',
    andValue === '喷水' && andRows === 0,
    `框里「${andValue}」／行数 1（喷水）→ ${andRows}（已废止 AND 喷水）`)
  await click(byText('.ks-chip', '全部'))
  await setInput(searchInput(), '')
  // ── 2o：还原 + 兜底（后面所有断言的前提） ──
  check('搜索块收尾：还原到「文件层 / 4 行 / 筛选=全部 / 搜索为空」（后面断言 3 起一字未改地跑）',
    fileRows().length === 4 && searchValue() === ''
    && (container.querySelector('.ks-chip-on')?.textContent ?? '').includes('全部'),
    `行 ${fileRows().length} 行／框里「${searchValue()}」／选中的胶囊「${(container.querySelector('.ks-chip-on')?.textContent ?? '').trim()}」`)

  // ── 断言 3：文件列表 = 勾选框 + 每行一个「⋮」溢出菜单（P1-1 改造后的口径） ──
  const checkboxes = q('input[type=checkbox]')
  // 默认文件夹 P16 工程防火 有 4 篇 ⇒ 4 个行勾选 + 1 个全选
  check('行勾选框 + 全选：勾选框数 = 文档数 + 1', checkboxes.length === 5, `实际 ${checkboxes.length}`)
  // ⚠ **本条断言于 2026-09-20 P1-1 改过（旧断言已过时，不是为了让门禁变绿而削弱）**：
  //   原来钉的是"每行都有**常驻**「＋标签」按钮"（`button` 文本 === '＋标签'，共 4 个）。
  //   P1-1 的施工决定就是**把行内的「＋标签」「详情」收进行尾「⋮」溢出菜单**
  //   （依据 docs/research/weknora-ui-vs-ours.md §7.6，业主本轮任务书 P1-1 的原话"收进行尾一个
  //   「⋮」溢出菜单"）⇒ 常驻按钮**按设计消失**，旧断言必然红。
  //   旧的"在场"证据没有丢：`smoke-client-entry.mjs` 的 13 条需求钉子仍钉着交付产物里的
  //   「＋标签」字面量；这里改成钉**新结构**（触发器存在 + 菜单里真的有那两项）。
  const moreTriggers = q('.ks-item-more button[aria-haspopup=menu]')
  check('每行都有行尾「⋮」溢出菜单触发器（一行一个 = 4 个）',
    moreTriggers.length === 4, `实际 ${moreTriggers.length}`)
  // ── 断言 3b：行内**可见控件数** ≤ 3 —— P1-1 的验收口径 ──
  // ⚠⚠ **2026-09-20 打回更正（复核用变异 M2 证明旧写法是假绿）**：
  //   旧写法数的是**写死的类名清单** `.ks-check,.ks-status,.ks-item-more`。复核把「＋标签」
  //   按钮**加回行内**（`class=ks-item-add`）之后，这条**仍然 PASS 26/26 exit 0** —— 新按钮
  //   不在清单里 ⇒ "行内可见控件 ≤3"这个**性质**根本没被钉住，钉住的只是"这三个类还在不在"。
  //   这是**真正的断言漏洞**，不是措辞问题。
  // ⇒ 新口径 = **按"是不是控件"数，不是按类名数**：`button,input,select,textarea,
  //   [role=button],[role=checkbox],[role=switch],[contenteditable=true]` 是**元素/角色本身**
  //   定义的，再加一个 `.ks-status`（状态徽章是**纯展示** span，没有原生控件角色，语义上由
  //   P1-1 的验收口径点名要算 1 个）。**为什么这样数不会被绕过**：
  //   ① 想再往行内塞任何**能点/能输入**的东西，无论它挂什么类名（`.ks-item-add` / 任意新类 /
  //      干脆不挂类），都必须落到这组标签或角色上 ⇒ 计数必 +1 ⇒ 这条必红；
  //   ② 反过来"把状态徽章摘掉"也逃不掉（`.ks-status` 在口径里，必须回来）；
  //   ③ 残余的口子只有"塞一个既不是控件、又不是 .ks-status 的纯 span" —— 那东西**用户点不了**，
  //      不构成"行内可见控件"，不算被绕过。
  //   证据：把 `class=ks-item-add` 的 `＋标签` 加回行内 ⇒ 旧口径 26/26 PASS、新口径 **FAIL**
  //   （四行 3/3/3/4）；把菜单里的「＋标签」项删掉 ⇒ 下面的 4 行菜单断言 **FAIL**。
  const CTRL_SEL = 'button,input,select,textarea,[role=button],[role=checkbox],[role=switch],[contenteditable=true],.ks-status'
  // 数的是**行元素内部**：`document.querySelectorAll` 会连 portal 到 body 的菜单项一起数进来，
  // 这里只用 row 作用域 ⇒ 菜单内容天然不算"行内"。
  const ctrlCounts = fileRows().map((row) => row.querySelectorAll(CTRL_SEL).length)
  // ⚠ 只读诊断（2026-09-20 打回留痕用，**不参与判定**）：把**已被废弃的旧口径**
  //   （写死类名清单）也数一遍，变异实验里用来复现"旧写法假绿"。跑门禁时这行只是多一次
  //   querySelectorAll，不改任何 PASS/FAIL 语义。
  const oldCtrlCounts = fileRows().map((row) => row.querySelectorAll('.ks-check,.ks-status,.ks-item-more').length)
  if (process.env.KS_CTRL_LEGACY_DIAG === '1') {
    console.log(`  · 只读诊断：旧口径（写死类名清单）四行 = ${oldCtrlCounts.join('/')}`
      + `；新口径（真控件）= ${ctrlCounts.join('/')}`)
  }
  check('每行行内可见控件 ≤ 3（按下述真控件口径数；勾选框 + 状态徽章 + ⋮ = 3）',
    ctrlCounts.length === 4 && ctrlCounts.every((n) => n <= 3),
    `四行分别是 ${ctrlCounts.join('/')}`)
  // ── 断言 3c：**四行**的菜单都必须真有「＋标签」与「详情」（收进去 ≠ 删掉）──
  // ⚠⚠ **2026-09-20 打回更正**：旧写法只核**第 0 行**一个菜单（`q('.ks-item')[0]`）——
  //   于是"第 2/3/4 行的菜单里是空的"这种回归它**看不见**。四行是同一段 JSX 渲染的，
  //   但"渲染出来了"这件事必须**逐行**取证（口径覆盖到哪，才算验到哪）。
  //   `role=menuitem` 由宿主 Menu portal 到 `<body>`，不在 container 里 ⇒ 查 document。
  const menuByRow = []
  const menuMisses = []
  for (const [i, row] of fileRows().entries()) {
    await click(row.querySelector('.ks-item-more button'))
    const texts = [...document.querySelectorAll('[role=menuitem]')].map((el) => (el.textContent ?? ''))
    menuByRow.push(texts)
    if (!texts.includes('＋标签') || !texts.includes('详情')) menuMisses.push(`第${String(i)}行=[${texts.join('|')}]`)
    await click(row.querySelector('.ks-item-more button')) // 收起，再核下一行（同一时刻只开一个）
    if (document.querySelectorAll('[role=menuitem]').length !== 0) menuMisses.push(`第${String(i)}行菜单没收起`)
  }
  check('四行的「⋮」菜单**逐行**都含「＋标签」与「详情」两项（只核第 0 行 = 覆盖不到 3 行）',
    fileRows().length === 4 && menuMisses.length === 0,
    menuMisses.length === 0
      ? `四行菜单：${menuByRow.map((t) => t.length).join('/')} 项`
      : menuMisses.join(' ; '))
  check('每行菜单点开再点一次都收起（四行都试过，同一时刻只开一个）',
    document.querySelectorAll('[role=menuitem]').length === 0,
    `还剩 ${document.querySelectorAll('[role=menuitem]').length} 项`)

  /* ══════════ 断言 3d-3g：**真表格**（P2 头条，2026-09-20） ══════════
   * 这一组替代了原来的 9 号断言（"本页没有搜索框"，依据是业主 2026-09-19 的"这一页不做搜索"）。
   * 本轮任务书明确要求"列表上方加一个搜索框（宿主 Input），**必须真的过滤**" ⇒ 旧断言过时。
   * ⚠ **不是"删掉一条换绿"**：旧的只数了 placeholder 里有没有"搜索"两个字（字符串级、
   *   而且当时那一跑处在**标签视图**里 —— 文件视图的搜索框根本没挂载，所以它即使在
   *   "文件视图有搜索框"的今天也照样 PASS，是一条**假绿**）；新的三条是**行为级**
   *   （行数真的变 1 / 真的恢复）与**结构级**（表头与行的 cell 类名序列逐字相同）。
   *   断言条数因此只增不减（26 → 31）。
   *   ⚠⚠ **2026-09-20 P2 复核打回（D6）：上面这个"26 → 31"是错的，就地更正（原话保留）。**
   *      **实测**（`grep -c '^ *check(' plugin/scripts/smoke-kb-page-render.mjs` = 33；运行时也
   *      打印 `PASS (33/33)`）= **33** —— 转述时少数了两条（复核也是这么数的）。
   *      **本批（verify-freeze-p2 落地）又加 2 条**（3e-2 表头/行的 computed 列模板 + gap 逐字
   *      相同；3g 前"搜索框在/不在 == 声明 `KB_FILE_VIEW_SEARCH`"）⇒ 运行时是 **35/35**
   *      （文件里 `check(` 行 37 条：另有 2 条在"搜索框缺席"分支里，那一支只有在**声明 false**
   *      的退回态才会跑到）。⇒ 以后写条数**一律现数**，别抄。
   *      ⚠ **5i（2026-09-20 收尾批）又加了一批**（卡片尺寸统一 2 条 + 搜索框每一层 2h–2o 8 条）
   *      ⇒ 运行时条数**以那一跑打印的 `PASS (n/n)` 为准**；本文件里凡是"n/n"的历史数字
   *      都是当时的快照，**不要**拿它当现在的基线（那正是 D6 那条错话的成因）。 */
  // ── 断言 3d：列头行是**真列头**，且与行**同构**（同一份 COLUMNS 定义）──
  const cellsOf = (el) => [...el.children].map((c) => c.className)
  const headRow = container.querySelector('.ks-lhead')
  const headCells = headRow === null ? [] : cellsOf(headRow)
  const rowCells = fileRows().map((row) => cellsOf(row))
  check('列头行有 5 个 cell（文件名/效力/生效日期/标签/⋮），且**每一行的 cell 类名序列与表头逐字相同**',
    headCells.length === 5 && rowCells.length === 4 && rowCells.every((cs) => JSON.stringify(cs) === JSON.stringify(headCells)),
    `表头 ${JSON.stringify(headCells)}；第 1 行 ${JSON.stringify(rowCells[0] ?? [])}`)
  check('列头文案就是四个列名（文件名 / 效力 / 生效日期 / 标签）',
    ['文件名', '效力', '生效日期', '标签'].every((t) => (headRow?.textContent ?? '').includes(t)),
    (headRow?.textContent ?? '').replace(/\s+/g, ' '))
  // ── 断言 3e：**列模板只有一个所有者**（.ks-list）+ 行内文件图标真的在每一行里 ──
  // 为什么断言"唯一所有者"：列对齐的机制就是"表头与行都只写 grid-template-columns:var(--ks-cols)"，
  // 而 --ks-cols 定义在 .ks-list 上（窄/宽两档也只覆盖这一个属性）。
  // ⚠ jsdom 不做布局 ⇒ 这里**验不了"量出来像素一样"**（那是 ui-render-shot.mjs 的 #cols 的活，
  //   它在真 Chrome 里量 computed grid-template-columns：表头与行必须逐字相同）。
  //   这里验的是**结构前提**：两者都是 .ks-list 的直接子元素、都用同一份 cell 类名。
  const childrenOfList = container.querySelector('.ks-list') === null
    ? [] : [...container.querySelector('.ks-list').children]
  check('列头行与全部数据行都是同一个 .ks-list 的直接子元素（列模板的唯一所有者）',
    childrenOfList.filter((el) => el.classList.contains('ks-lhead')).length === 1
    && childrenOfList.filter((el) => el.classList.contains('ks-item')).length === 4,
    `盒子里共 ${childrenOfList.length} 个子元素`)
  // ── 断言 3e-2：**表头与第一行的 computed 列模板逐字相同**（P2 复核打回 B，2026-09-20）──
  // ⚠⚠ 为什么补这一条：复核的变异 M4（把表头与行的 `grid-template-columns` 改成**不一致**：
  //   header `416px 100px …` vs row `444px 72px …`）当时 **smoke 33/33 PASS、ui-render-shot exit 0**
  //   ——"列对齐"是本轮的头条验收，却只有一个**报告值**（`#cols`）兜着，**没有断言**。
  //   现在：门禁链里这一条 + ui-render-shot 自己的 `#cols` 自检（真 Chrome 里量，三档由
  //   `smoke-kb-cols.mjs` 逐档跑）。
  // ⚠ 口径：jsdom **不做布局**，但它**会做级联**（实测：这里拿到的是声明里的
  //   `var(--ks-cols)` 字面值，不是解析后的像素）。所以这条断言判的是"**两条声明是不是同一条**"
  //   —— 恰恰就是 M4 破坏的那个不变量（表头一套、行另一套）；像素级的等价仍由 ui-render-shot 判。
  //   **含 gap**：`column-gap` 也必须逐字相同（列对齐含间距，不只是列宽）。
  //   取到空值也算红（"取不到值" ≠ "相同"）。
  const headRowEl = container.querySelector('.ks-lhead')
  const firstRowEl = container.querySelector('.ks-item')
  const headTpl = csOf(headRowEl, 'grid-template-columns')
  const rowTpl = csOf(firstRowEl, 'grid-template-columns')
  const headGap = csOf(headRowEl, 'column-gap')
  const rowGap = csOf(firstRowEl, 'column-gap')
  check('表头行与第一行的 computed grid-template-columns 与 column-gap **逐字相同**（列对齐的门禁锚点）',
    Boolean(headTpl) && Boolean(rowTpl) && Boolean(headGap) && Boolean(rowGap)
    && headTpl === rowTpl && headGap === rowGap,
    `表头 ${JSON.stringify(headTpl)} / 行 ${JSON.stringify(rowTpl)}；gap 表头 ${JSON.stringify(headGap)} / 行 ${JSON.stringify(rowGap)}`)
  check('每一行都有**行内文件图标**（.ks-fileico 里一个真 svg），且带类型说明 title',
    fileRows().length === 4
    && fileRows().every((row) => row.querySelector('.ks-fileico svg') !== null
      && (row.querySelector('.ks-fileico')?.getAttribute('title') ?? '') !== ''),
    fileRows().map((row) => row.querySelector('.ks-fileico')?.getAttribute('title') ?? '(无)').join('/'))
  // ── 断言 3f：行内**标签 chip 可见**（P2 头条要的"行内可见 chip"，不是藏进 ⋮）──
  // ⚠ 与"行内可见控件 ≤3"不冲突：chip 是**纯展示 span**（不在 CTRL_SEL 里）。
  //   "＋标签"的**入口**仍在行尾「⋮」（见 3c 的逐行取证）—— 这是任务书给的允许方案：
  //   "把'标签'做成一列可见 chip、而'加标签'入口留 ⋮"。
  const rowTags = fileRows().map((row) => row.querySelectorAll('.ks-tag').length)
  check('行内**可见**标签 chip（至少一行有 ≥1 个 .ks-tag；纯展示，不是控件）',
    rowTags.some((n) => n > 0), `四行的 chip 数 = ${rowTags.join('/')}`)
  // ── 断言 3g：搜索框**真的过滤**（任务书验收：只命中 1 行的串 ⇒ 行数变 1；清空 ⇒ 恢复）──
  // ⚠⚠ **2026-09-20 P2 复核打回（C）补的一条**：搜索框"在 / 不在"必须与**声明**
  //   `KB_PAGE_SEARCH` 一致（从组件里 import 的真值，不是抄一个 true）。
  //   为什么要它：旧的 9 号断言（"本页没有搜索框"）删掉之后，**搜索框存在与否一度没有任何
  //   断言盯着** —— 悄悄删了它，3g/3h 只会**崩**（`setInput(null)` 抛 TypeError），
  //   既不是"可诊断的红"，也说不清"设计上到底该不该有"。
  //   ⚠ 落点必须是**文件视图**：这一段跑在默认的「文件」视图里（切「标签」视图在后面），
  //     旧的 9 号断言跑在标签视图 ⇒ 文件视图有没有框它都 PASS（那才是它假绿的那一半）。
  //   两个方向都钉住：声明 true ⇒ 框必须在且能过滤；声明 false（退回旧设计）⇒ 框必须真的不在。
  //   ⚠ 5i（2026-09-20 收尾批）：常量**改名**（`KB_FILE_VIEW_SEARCH` → `KB_PAGE_SEARCH`）——
  //     新名字与事实一致（框**每一层**都在，不再只是"文件视图"）；"在/不在 == 声明"这条
  //     判据**一个字没放宽**，另加 2h–2o 逐层取证（见上面）。
  const searchBox = container.querySelector('.ks-search input')
  check('本页的搜索框"在 / 不在"与声明 KB_PAGE_SEARCH 一致（删掉它就红，不是没人管）',
    (searchBox !== null) === KB_PAGE_SEARCH,
    `声明 KB_PAGE_SEARCH=${String(KB_PAGE_SEARCH)}；DOM 里 .ks-search input ${searchBox === null ? '不存在' : '存在'}`
    + `（当前视图 = 文件列表：本页默认视图，切「标签」在后）`)
  const rowCount = () => fileRows().length
  if (searchBox === null) {
    // 声明说"没有框"时，行为级断言**判为失败**（而不是让下面 setInput(null) 崩掉）：
    // 这两条是"框在场才成立"的行为验收 —— 缺席时它们必须红，且要能说清为什么。
    check('搜索框真的过滤：标准号命中 1 行、名称命中 1 行、无命中 0 行（且给空态）、清空恢复 4 行',
      false, '没有 .ks-search input ⇒ 这一条**没验到**，按失败记（"没跑"不能渲染成"通过"）')
    check('搜索变化即清空选择（切换后批量条消失 —— 批量动作不该作用在看不见的行上）',
      false, '没有 .ks-search input ⇒ 这一条**没验到**，按失败记')
  } else {
    const before9 = rowCount()
    await setInput(searchBox, 'GB 50016-2014')            // 只命中**标准号**（d1）
    const byNo = rowCount()
    await setInput(searchBox, '喷水')                      // 只命中**名称**（d3）
    const byName = rowCount()
    await setInput(searchBox, '搜索一个不存在的串')        // 谁都不命中 ⇒ 0 行 + "被筛没了"的空态
    const none = rowCount()
    const emptyTitle = container.querySelector('.ks-empty-t')?.textContent ?? '(没有空态卡)'
    await setInput(searchBox, '')                          // 清空 ⇒ 恢复
    const restored = rowCount()
    check('搜索框真的过滤：标准号命中 1 行、名称命中 1 行、无命中 0 行（且给空态）、清空恢复 4 行',
      before9 === 4 && byNo === 1 && byName === 1 && none === 0 && restored === 4,
      `行数 ${before9} → 标准号 ${byNo} → 名称 ${byName} → 无命中 ${none} → 清空 ${restored}；空态「${emptyTitle}」`)
    // ── 断言 3h：搜索/筛选变化 ⇒ **清空选择**（否则批量动作会作用在看不见的行上）──
    await click(fileRows()[0].querySelector('input[type=checkbox]'))
    const selectedBefore = container.querySelector('.ks-batch') !== null
    await setInput(searchBox, '喷水')
    check('搜索变化即清空选择（切换后批量条消失 —— 批量动作不该作用在看不见的行上）',
      selectedBefore && container.querySelector('.ks-batch') === null,
      `搜索前有批量条=${String(selectedBefore)}；搜索后=${String(container.querySelector('.ks-batch') !== null)}`)
    await setInput(searchBox, '')
    const backTo4 = rowCount()
    check('清空搜索后回到 4 行（搜索没有留下副作用）', backTo4 === 4, `实际 ${backTo4} 行`)
  }

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
    fileRows().length === 0 && batch() === null,
    `剩 ${fileRows().length} 行`)

  // ── 断言 7：详情里的三个日期（业主点名要的） ──
  // 换到「法律法规」树的某个文件夹（删空了 P16），先切到自建夹「公司制度」更稳
  const companyCard = q('.ks-kb-cards .ks-kb-card').find((el) => (el.textContent ?? '').includes('公司制度'))
  await click(companyCard)
  const rows = fileRows()
  check('切到自建夹「公司制度」⇒ 列表换成它的 3 篇',
    rows.length === 3, `实际 ${rows.length}`)
  // ⚠ **本条也随 P1-1 改过（2026-09-20）**：行内常驻的「详情」按钮进了「⋮」菜单
  //   ⇒ 老写法 `button[aria-label^="打开"]` 找不到东西（会 TypeError 崩在 click 里，
  //   上面那次实跑就是这么炸的）。新写法：点该行的「⋮」→ 点菜单里的「详情」。
  const detailBtn = rows[0].querySelector('.ks-item-more button')
  await click(detailBtn)
  const detailItem = [...document.querySelectorAll('[role=menuitem]')].find((el) => (el.textContent ?? '') === '详情')
  await click(detailItem)
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

  // ── 原来的断言 9「本页没有搜索框」在 2026-09-20（P2 头条）**被上面 3g/3h 两条替代** ──
  // ⚠ 就地留痕（本仓规矩：错话保留 + 更正在后）：
  //   旧写法 `q('input').filter((i) => /搜索|search/i.test(i.placeholder))` 数的是
  //   **placeholder 里的两个字**，而且它跑在这一段（**标签视图**已经切过来了）⇒
  //   文件视图的搜索框即使存在也没挂载 ⇒ 它在新设计下**仍然 PASS** —— 那是一条假绿。
  //   ⇒ 已删除，改为 3g（行为级：行数真的 4→1→1→0→4）与 3h（搜索即清空选择）。
  //   与之配套的翻案留痕（业主 2026-09-19 曾说"这一页不做搜索"）写在
  //   plugin/client/KsKnowledgePage.tsx 顶部的第 4 条里，需业主复核。
  //   ⚠⚠ **2026-09-20 P2 复核打回（C）：上面这个替换有一个**覆盖缺口**，已补。**
  //     复核指出：9 号删掉之后，**"文件视图里有没有搜索框"这件事没有任何断言盯着**
  //     （3g/3h 是行为级：框不在时它们只会崩/失败，说不清"设计上该不该有"；而且退回旧设计时
  //     那句"把 3g/3h 换回'本页没有搜索框'"等于把**已证伪的假绿**装回去）。
  //     ⇒ 现在有一条**声明 ↔ DOM 一致性**断言（落点在**文件视图**，默认视图，就在 3g 之前）：
  //     「DOM 里有没有 `.ks-search input`」=== 组件导出的 `KB_PAGE_SEARCH`（5i 改名，见 3g 注释）。
  //     两个方向都判：声明 true ⇒ 必须在且能过滤（3g/3h，**每一层**另有 2h–2o）；声明 false
  //     （退回旧设计）⇒ 必须真的不在。覆盖缺口因此**关掉**了，不再是"有意的取舍"。

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
