/**
 * ks-dsh-plugin — scripts/smoke-client-entry.mjs
 *
 * 客户端半 `apply(ctx)` 的**门面契约**冒烟。为什么单独写它（verifier 三轮 P0）：
 * DSH 动态客户端插件拿到的不是内核 cordis ctx，而是
 * `packages/extensions/cordis-client-runner/src/client/guard.ts` 的受限门面——
 *   - 白名单 verb 只有 effect/on/once/provide/timeout/interval/setTimeout/setInterval/
 *     throttle/debounce（`CTX_VERBS`）；
 *   - 读**任何**其它属性（包括 `ctx.betterSidebar` 这种未声明服务、以及 `ctx.inject`
 *     这种不在白名单的框架方法）→ `denyRead` → **直接抛**
 *     `dynamic ctx does not expose "..."`；
 *   - `ctx.get(name)` 是允许的（`readService(name, false)`，不要求声明），读不到返回 undefined。
 * 上一轮整改里我在 `apply()` 里写了 `typeof ctx.inject === 'function'`，在真机门面上
 * 直接抛错 → 整块客户端半（tab + 设置栏目 + 📜 查法规模式开关）全都不激活。
 * 本冒烟用一个**逐条镜像**该门面语义的假 ctx 调 `apply()`，把这类"读了不该读的属性"
 * 变成开发期红灯。
 *
 * 覆盖：
 *   1. 门面语义自证（未声明属性抛、get 返回 undefined、白名单 verb 可用）；
 *   2. better-sidebar **不存在** → apply 不抛；不注册任何 tab；
 *   3. better-sidebar **存在** → apply 不抛；3 个 tab（证据 PDF / 收藏 / settings
 *      卡）+ 设置栏目全部注册（效力报告/入库预览 2026-11 迁入设置栏目，不再是 tab）；
 *   4. `inject` 声明只含官方服务（不把第三方插件当门禁）。
 *
 * 用法：node scripts/smoke-client-entry.mjs   （退出码 0 = 全通过）
 */
import { mkdtemp, readFile, readdir, rm, writeFile } from 'node:fs/promises'
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

/* ---------------------------------------------------- 浏览器全局最小桩 */
const docListeners = []
/** 真的记账的 document 桩：add/remove 都按 (type, fn) 记账，才能测"监听器有没有泄漏"。 */
const docHandlers = new Map()
const listenerCount = (type) => (docHandlers.get(type) ?? new Set()).size
/** 驱动当前登记的 click 监听（entry 用 document 级 capture 接管证据锚点）。 */
function dispatchClick(event) {
  for (const fn of docHandlers.get('click') ?? []) {
    fn({ preventDefault() {}, button: 0, metaKey: false, ctrlKey: false, shiftKey: false, altKey: false, ...event })
  }
}
globalThis.document = {
  visibilityState: 'visible',
  addEventListener(type, fn) {
    if (!docHandlers.has(type)) docHandlers.set(type, new Set())
    docHandlers.get(type).add(fn)
    docListeners.push(type)
  },
  removeEventListener(type, fn) {
    docHandlers.get(type)?.delete(fn)
  },
}
const windowHandlers = new Map()
globalThis.window = {
  setTimeout: (fn, ms) => setTimeout(fn, ms),
  addEventListener(type, fn) {
    if (!windowHandlers.has(type)) windowHandlers.set(type, new Set())
    windowHandlers.get(type).add(fn)
  },
  removeEventListener(type, fn) { windowHandlers.get(type)?.delete(fn) },
}

/* ---------------------------------------------------- 打包 client/entry */
const entryPath = join(pluginRoot, '.smoke-entry-apply.mjs')
const outPath = join(pluginRoot, '.smoke-entry-apply.bundle.mjs')
const stubDir = await mkdtemp(join(tmpdir(), 'ks-entry-stub-'))
const pdfStubPath = join(stubDir, 'pdfjs-stub.mjs')
// pdf.js 在 import 期就摸浏览器全局（DOMMatrix 等），而本冒烟测的是 **apply() 怎么用 ctx**，
// 不是 PDF 渲染。把 pdfjs-dist 换成桩（同时也让这个冒烟保持毫秒级）。
await writeFile(pdfStubPath, [
  'export const GlobalWorkerOptions = {}',
  'export const version = "0.0.0-smoke-stub"',
  'export const getDocument = () => ({ promise: Promise.reject(new Error("stub")), destroy: () => {} })',
  'export class RenderingCancelledException extends Error {}',
  'export default { GlobalWorkerOptions, version, getDocument, RenderingCancelledException }',
  '',
].join('\n'), 'utf8')

// 宿主的 `@deepseek-ai/dsh-client-ui-primitives`（Button / Checkbox / Tag / Pill / Input / Menu …）
// ——**这是 baseline 模块**（官方 docs/subsystems/client-modules.zh.md：`external` 只管
// "non-baseline module specifiers"；这一个是 `packages/client/web/src/seed.ts` 里那 9 个
// 平台单例之一），所以浏览器里 require 得到，**不需要在 package.json 里声明**。
// 但本冒烟在 **Node** 里跑、没有宿主模块表，故同样换桩——与上面 pdfjs 的处理同一个理由：
// 我们测的是 apply() 的接线，不是渲染。桩里的成员只需**存在**（本冒烟不渲染它们）。
// ⚠ 这里必须**逐个列出我们真正 import 的成员**：宿主那份是真的，桩漏一个就会
//   `SyntaxError: does not provide an export named …`（比"运行时 undefined"好，至少响）。
const primitivesStubPath = join(stubDir, 'primitives-stub.mjs')
await writeFile(primitivesStubPath, [
  'const Null = () => null',
  'export const Button = Null',
  'export const Checkbox = Null',
  'export const Tag = Null',
  'export const Pill = Null',
  'export const Input = Null',
  'export const Menu = Null',
  'export const IconChevronDownOutline14 = Null',
  '',
].join('\n'), 'utf8')
await writeFile(entryPath,
  "export { apply, inject } from './client/entry.ts'\n", 'utf8')
try {
  await build({
    entryPoints: [entryPath], bundle: true, platform: 'node', format: 'esm',
    outfile: outPath, absWorkingDir: pluginRoot, jsx: 'automatic',
    external: ['react', 'react-dom'],
    alias: { 'pdfjs-dist': pdfStubPath, '@deepseek-ai/dsh-client-ui-primitives': primitivesStubPath },
    loader: { '.tsx': 'tsx', '.ts': 'ts' }, logLevel: 'warning',
  })
} catch (err) {
  console.error('BUILD_FAIL: ' + (err && err.message ? err.message : String(err)))
  await rm(entryPath, { force: true })
  await rm(stubDir, { recursive: true, force: true })
  process.exit(1)
}
await rm(entryPath, { force: true })
const entry = await import(pathToFileURL(outPath).href)
await rm(outPath, { force: true })
await rm(stubDir, { recursive: true, force: true })

/** guard.ts 的 CTX_VERBS / TIMER_VERBS 逐条镜像。 */
const CTX_VERBS = new Set([
  'effect', 'on', 'once', 'provide', 'timeout', 'interval',
  'setTimeout', 'setInterval', 'throttle', 'debounce',
])
const TIMER_VERBS = new Set(['timeout', 'interval', 'setTimeout', 'setInterval', 'throttle', 'debounce'])

/**
 * 造一个门面 ctx：语义与 cordis-client-runner 的 guard **逐条对齐**——
 *  - 白名单 verb 可读可用，但 **timer verb 需要声明 `timer`**（guard.ts:25/219）；
 *  - `get` 可读（guard.ts:214 `readService(name, false)`，不要求声明）；
 *  - `slots` 服务的 `register` 校验 `name`（guard.ts:104-112 同款）；
 *  - 其余属性（含未声明服务、`inject` 这类框架成员）一律**抛**。
 * 假门面若比真门面宽松，这个冒烟就会漏掉真实违规（verifier 四轮实测出过这类失真）。
 */
function buildFacade({ withBetterSidebar = false, withTimer = false } = {}) {
  const injected = []
  const registered = []
  const slots = {
    inject(key, cb) { injected.push(key); cb(); return () => {} },
    register(options, component) {
      if (typeof options?.name !== 'string' || options.name.length === 0) {
        throw new Error('slots.register options need a string `name`')
      }
      registered.push({ options, component })
      return () => {}
    },
  }
  const declared = new Set(['slots'])
  if (withTimer) declared.add('timer')
  /** 官方 tab 类型注册表（`ctx.sidebarRightTabs`）——只需 `register`。 */
  const makeTabs = () => ({
    registered: [],
    register(def) { this.registered.push(def); return () => {} },
  })
  /** 官方右侧栏导航面（`ctx.sidebarRight`）——只需 `openResource`。 */
  const makeRight = () => ({
    opened: [],
    openResource(address, options) { this.opened.push({ address, options }); return undefined },
  })
  // 可变持有者：用来模拟"better-sidebar 在我们 apply 之后才激活"
  // 可变持有者：模拟"官方右侧栏在我们 apply 之后才挂载"。
  const tabsRef = { current: withBetterSidebar ? makeTabs() : null }
  const rightRef = { current: withBetterSidebar ? makeRight() : null }
  const services = { slots }
  const denyRead = (prop) => {
    throw new Error(`dynamic ctx does not expose "${prop}"`)
  }
  const denyTimer = () => {
    throw new Error('service "timer" is not declared by your plugin')
  }
  const effects = []
  const listeners = []
  const facade = new Proxy({}, {
    get(_t, prop) {
      if (prop === 'get') {
        return (name) => {
          if (name === 'sidebarRightTabs') return tabsRef.current ?? undefined
          if (name === 'sidebarRight') return rightRef.current ?? undefined
          return declared.has(name) ? services[name] ?? undefined : undefined
        }
      }
      if (typeof prop !== 'string') return undefined
      if (CTX_VERBS.has(prop)) {
        return (...args) => {
          // 与 guard.ts:217-223 同构：timer verb 未声明 timer 时**调用即抛**
          if (TIMER_VERBS.has(prop) && !declared.has('timer')) return denyTimer()
          if (prop === 'effect') {
            const disposer = args[0]()
            effects.push(disposer)
            return disposer
          }
          if (prop === 'on') {
            listeners.push(args)
            return () => {}
          }
          if (TIMER_VERBS.has(prop)) return Reflect.apply(setTimeout, globalThis, args)
          return undefined
        }
      }
      if (!declared.has(prop)) denyRead(prop)
      return services[prop]
    },
    has: (_t, prop) => prop === 'get'
      || (typeof prop === 'string'
        && ((CTX_VERBS.has(prop) && (!TIMER_VERBS.has(prop) || declared.has('timer')))
          || declared.has(prop))),
    set: () => { throw new Error('dynamic ctx is read-only') },
  })
  /** 模拟"服务此刻才被提供"：置入两面并发出 cordis 的 internal/service 事件。 */
  const provideBetterSidebar = () => {
    tabsRef.current = makeTabs()
    rightRef.current = makeRight()
    for (const [event, listener] of listeners) {
      if (event === 'internal/service') {
        listener('sidebarRightTabs', tabsRef.current)
        listener('sidebarRight', rightRef.current)
      }
    }
    return { tabs: tabsRef.current, right: rightRef.current }
  }
  /** 模拟服务被撤销：cordis 同样发 internal/service，但 value 为 undefined。 */
  const unprovideBetterSidebar = () => {
    tabsRef.current = null
    rightRef.current = null
    for (const [event, listener] of listeners) {
      if (event === 'internal/service') {
        listener('sidebarRight', undefined)
        listener('sidebarRightTabs', undefined)
      }
    }
  }
  return {
    facade, slots, injected, registered, tabsRef, rightRef, effects, listeners,
    provideBetterSidebar, unprovideBetterSidebar,
  }
}

/* ---------------------------------------------------- 1. 门面语义自证 */
{
  const { facade } = buildFacade({})
  let threw = null
  try { void facade.inject } catch (error) { threw = error }
  check('facade mirror: reading an undeclared/framework property really throws',
    threw !== null && /does not expose "inject"/.test(String(threw?.message)),
    String(threw?.message ?? 'no throw').slice(0, 60))
  check('facade mirror: ctx.get on an absent service returns undefined (no throw)',
    facade.get('sidebarRightTabs') === undefined && facade.get('sidebarRight') === undefined)
  check('facade mirror: whitelisted verbs are callable',
    typeof facade.effect === 'function' && typeof facade.on === 'function')
  check('facade mirror: `in` does not advertise undeclared properties',
    !('inject' in facade) && !('sidebarRightTabs' in facade))
  // timer verb 必须声明 timer（guard.ts:25/219）——旧假门面在这里比真门面宽松，
  // 会把"没声明 timer 却用了 ctx.setTimeout"这类真机会抛的写法放过去
  let timerThrew = null
  try { facade.setTimeout(() => {}, 1); } catch (error) { timerThrew = error }
  check('facade mirror: timer verbs throw without declaring timer',
    timerThrew !== null && /timer/.test(String(timerThrew?.message)),
    String(timerThrew?.message ?? 'no throw').slice(0, 50))
  check('facade mirror: `in` hides timer verbs without declaring timer',
    !('setTimeout' in facade))
  let regThrew = null
  try { facade.slots.register({}, () => null) } catch (error) { regThrew = error }
  check('facade mirror: slots.register rejects a missing name (guard.ts:104-112)',
    regThrew !== null && /name/.test(String(regThrew?.message)),
    String(regThrew?.message ?? 'no throw').slice(0, 50))
}

/* ---------------------------------------------------- 2. 无官方右侧栏 */
{
  const built = buildFacade({})
  let error = null
  try { entry.apply(built.facade) } catch (e) { error = e }
  check('apply() does NOT throw when the official sidebar is absent (P0 regression guard)',
    error === null, String(error?.message ?? '').slice(0, 90))
  // 2026-10 收藏目录：夹内提问胶囊回来了（唯一合法的 input.dock 注入——
  // 老的斜杠命令 dock 删除语义只针对当时的 UI；新胶囊不依赖右侧栏）。
  check('the scope chip injects conversation.input.dock even without the official sidebar',
    built.injected.includes('conversation.input.dock'),
    built.injected.join(',') || '(none)')
  const chipNoBs = built.registered.find((r) => r.options?.id === 'ks-scope-chip')
  check('the scope chip registered with the right slot name + session props inject',
    chipNoBs !== undefined
    && chipNoBs.options?.name === 'conversation.input.dock'
    && typeof chipNoBs.options?.inject === 'function',
    built.registered.map((r) => String(r.options?.id)).join(',') || '(none)')
  // 设置栏目走官方 `settings.section`，**不依赖右侧栏** —— 右侧栏缺席时它仍须注册
  // （这是迁移时刻意保持的性质：右侧栏缺失不该连带弄丢设置）。
  check('设置栏目 registers even without the official sidebar (settings.section)',
    built.injected.includes('settings.section'), built.injected.join(','))
  check('no tab body is registered without the official sidebar (chip + settings excepted)',
    built.registered.every((r) => ['ks-scope-chip', 'ks-dsh-plugin'].includes(String(r.options?.id))),
    built.registered.map((r) => String(r.options?.id)).join(',') || '(none)')
}

/* ---------------------------------------------------- 3. 有官方右侧栏 */
{
  const built = buildFacade({ withBetterSidebar: true })
  let error = null
  try { entry.apply(built.facade) } catch (e) { error = e }
  const tabs = built.tabsRef.current
  const right = built.rightRef.current
  check('apply() does not throw when the official sidebar is present',
    error === null, String(error?.message ?? '').slice(0, 90))
  // 2026-10：input.dock 唯一合法占用者是夹内提问胶囊（id ks-scope-chip）。
  check('the input dock is injected exactly once (the ks scope chip)',
    built.injected.filter((k) => k === 'conversation.input.dock').length === 1,
    built.injected.join(','))
  const chip = built.registered.find((r) => r.options?.id === 'ks-scope-chip')
  check('the scope chip passes the sessionId through its props inject',
    chip !== undefined && chip.options.inject('sess-X').sessionId === 'sess-X',
    built.registered.map((r) => String(r.options?.id)).join(','))

  // ── 官方两段式：① 类型注册 ② body 座位注册 ──
  // ⚠ 2026-09-19 起本插件注册**两个**类型（原来只断言 1 个）：
  //   ① ks-evidence —— PDF 证据阅读器（单例、由证据链接驱动）；
  //   ② ks-knowledge —— 知识库页（开始页那张卡片的落点，按 params.page 分发二级页）。
  //   断言**有序的完整集合**而不是"长度=1"：既允许新增，又让"悄悄多/少一个类型"照样红。
  check('stage 1: exactly the two expected tab TYPES registered (ks-evidence, ks-knowledge)',
    tabs.registered.length === 2
    && tabs.registered[0]?.kind === 'ks-evidence'
    && tabs.registered[1]?.kind === 'ks-knowledge',
    tabs.registered.map((d) => String(d.kind)).join(',') || '(none)')
  check('stage 1: the type claims only our own constant resource address',
    Array.isArray(tabs.registered[0]?.patterns)
    && tabs.registered[0].patterns.includes('dsh-resource://ks-evidence'),
    JSON.stringify(tabs.registered[0]?.patterns))
  check('stage 1: canOpen accepts our address and refuses a foreign one',
    tabs.registered[0]?.canOpen('dsh-resource://ks-evidence') === true
    && tabs.registered[0]?.canOpen('dsh-resource://file/x.md') === false)
  check('stage 1: the type is NOT multiple (evidence viewer is a singleton)',
    tabs.registered[0]?.multiple === undefined)

  // ── 第二个类型（知识库，2026-09-19）也必须有同样的契约断言 ──
  // 不加这段，门禁对它就**是空的**：改坏它的地址/canOpen/单例性都不会红。
  const kb = tabs.registered[1]
  check('stage 1: the knowledge type claims only its own address',
    Array.isArray(kb?.patterns) && kb.patterns.length === 1
    && kb.patterns[0] === 'dsh-resource://ks-knowledge',
    JSON.stringify(kb?.patterns))
  check('stage 1: the knowledge type canOpen accepts its address and refuses a foreign one',
    kb?.canOpen('dsh-resource://ks-knowledge') === true
    && kb?.canOpen('dsh-resource://file/x.md') === false
    && kb?.canOpen('dsh-resource://ks-evidence') === false)
  check('stage 1: the knowledge type is NOT multiple (二级页是同一 tab 的四个面，不是四个 tab)',
    kb?.multiple === undefined)
  // 开始页只该有**一张**来自本插件的卡（它就是知识库类型的门）。
  // 若知识库类型也贡献 guide，开始页会出现两张几乎同名的卡。
  check('stage 1: the knowledge type contributes NO guide entry (start page keeps ONE card from us)',
    kb?.guide === undefined || kb.guide.length === 0,
    JSON.stringify(kb?.guide?.map?.((g) => g.id) ?? null))
  // ── 侧栏「开始页」手动入口（官方 guide 胶囊）──
  // 官方 GuideBody 把每个类型贡献的胶囊按 `order` 升序排；实测出货条目占用的号：
  // ui-sidebar-files = 10、ui-sidebar-terminal = 20（新建终端）、
  // ui-sidebar-browser = 30（浏览器，alpha.2 新增）。故取 25 = 终端与浏览器**之间**，
  // 既在终端下面，又**不与任何出货条目同号**（同号时先后只由注册顺序决定，等于随机）。
  const guide = tabs.registered[0]?.guide
  check('stage 1: the type contributes exactly one guide entry (start-page capsule)',
    Array.isArray(guide) && guide.length === 1,
    JSON.stringify(guide?.map?.((g) => g.id)))
  check('stage 1: the guide entry sorts between 新建终端 and 浏览器 (10 < terminal 20 < ours 25 < browser 30)',
    guide?.[0]?.order === 25 && guide[0].order > 20 && guide[0].order < 30,
    `order=${guide?.[0]?.order}`)
  check('stage 1: the guide entry has a unique id, live title/description and an icon component',
    guide?.[0]?.id === 'kb'
    && typeof guide[0].title === 'function' && guide[0].title().length > 0
    && typeof guide[0].description === 'function' && guide[0].description().length > 0
    && typeof guide[0].icon === 'function',
    `id=${guide?.[0]?.id} title=${guide?.[0]?.title?.()} icon=${typeof guide?.[0]?.icon}`)
  // ⚠ 2026-09-19 **故意反转**的一条旧断言。
  //   旧断言："开始页胶囊与 tab 标题必须同名（一个东西一个名字）"——当时两者都是「PDF 查看器」。
  //   业主指令：把开始页那张卡改成「**知识库**」并挂二级目录。于是它们是**两件事**：
  //     卡片 = 入口（进知识库），tab = 你正看着的东西（PDF 阅读器）。
  //   故不再断言相等，而是**各自钉死字面量** —— 比原来的"相等"更强：任一侧被误改都会红，
  //   且"哪一侧改错了"从输出里一眼可辨。
  check('stage 1: guide card and tab chip carry their OWN pinned labels (decoupled on purpose)',
    guide?.[0]?.title?.() === '知识库'
    && tabs.registered[0]?.title?.('dsh-resource://ks-evidence') === 'PDF 查看器',
    `guide=${guide?.[0]?.title?.()} tab=${tabs.registered[0]?.title?.('dsh-resource://ks-evidence')}`)
  const body = built.registered.find((r) => r.options?.name === 'sidebar.right.pane.tab')
  check('stage 2: the body seat registered under the type id',
    body !== undefined && body.options?.key === 'ks-dsh-plugin/evidence-pdf',
    built.registered.map((r) => String(r.options?.key ?? r.options?.id)).join(','))
  // ⚠ 这条是 2026-09-17「点开始页胶囊 → 面板全白」的回归护栏。
  //   真机根因：body 的 `inject` 工厂把**第一参数（sessionId）**当成"框架聚合面"，
  //   断言 `hooks.tabInfo` 存在 → 永远 undefined → 自设守卫挂载即抛 →
  //   官方 `slot entry crashed` → 空白。官方契约里 `useTabInfo` 是**运行时 prop**
  //   （座位 `hookContext: TabHookContext`），inject 工厂的**返回值**才是本插件的面。
  //   这里用"像真框架那样"的第一个参数调用一次，钉住：不抛、且不谎称提供 useTabInfo。
  let bodyFace = null
  let bodyThrew = null
  try { bodyFace = body?.options?.inject?.('session-1', undefined) } catch (error) { bodyThrew = error }
  check('stage 2: the body inject factory takes a sessionId and contributes ONLY openEvidence',
    bodyThrew === null
    && typeof bodyFace?.openEvidence === 'function'
    && bodyFace?.useTabInfo === undefined,
    bodyThrew !== null ? `threw: ${String(bodyThrew?.message).slice(0, 80)}`
      : `keys=${Object.keys(bodyFace ?? {}).join(',')}`)

  check('设置栏目 (settings.section) registered too',
    built.injected.includes('settings.section'), built.injected.join(','))
  check('the click interception is installed globally (evidence links)',
    docListeners.includes('click'))
  check('the probe registered disposers (effects can be cleaned on dispose)',
    built.effects.filter((fn) => typeof fn === 'function').length >= 2,
    `disposers=${built.effects.filter((fn) => typeof fn === 'function').length}`)

  // 2026-09-17 起**不再自动开 tab**（"目录常驻"）：原实现每次页面加载都抛
  //   `sidebarRight: no session surface is mounted`（会话面尚未挂载）—— 也就是它
  //   **从未生效**，只留一条 console.warn。手动入口已由开始页胶囊承担（见 stage 1 的
  //   guide 断言），而自动开还会把开始页顶掉。故这里改为钉住"**加载时不自动开**"。
  check('the plugin does NOT auto-open a tab at load (start page stays the doorway)',
    right.opened.length === 0,
    JSON.stringify(right.opened.map((o) => o.address)))
}

/* ---------------------------- 3b. 证据点击：一次导航即"打开或复用" */
{
  const built = buildFacade({ withBetterSidebar: true })
  entry.apply(built.facade)
  const right = built.rightRef.current
  const url = 'http://127.0.0.1:1/__ks_evidence__?doc=doc_X&page=7'
  // 直接驱动 entry 安装的 click 监听（门面把监听记在 docListeners 里）
  const anchor = {
    href: url,
    closest: () => ({ href: url }),
  }
  dispatchClick({ button: 0, target: anchor })
  check('an evidence click navigates via openResource with the SAME constant address',
    right.opened.length === 1
    && right.opened[0].address === 'dsh-resource://ks-evidence',
    JSON.stringify(right.opened.map((o) => o.address)))
  check('the evidence URL travels in params (keeps the address constant → singleton tab)',
    right.opened[0]?.options?.params?.url === url,
    JSON.stringify(right.opened[0]?.options?.params))
}

/* ---------------------------- 4. 官方右侧栏迟到：事件驱动重注册 */
{
  const built = buildFacade({})
  entry.apply(built.facade)
  check('late sidebar: no tab body registered while it is absent',
    built.registered.every((r) => r.options?.name !== 'sidebar.right.pane.tab'),
    `registered=${built.registered.map((r) => String(r.options?.id)).join(',')}`)
  check('late sidebar: the probe subscribed to internal/service',
    built.listeners.some(([event]) => event === 'internal/service'),
    built.listeners.map(([e]) => String(e)).join(','))
  const late = built.provideBetterSidebar() // 服务此刻才提供 → 触发 internal/service
  check('late sidebar: the tab type registers the moment the services appear',
    late.tabs.registered.length === 2 && built.injected.includes('settings.section'),
    `types=${late.tabs.registered.length} injected=${built.injected.join(',')}`)
  check('late sidebar: the settings column is registered exactly once',
    built.registered.filter((r) => r.options?.id === 'ks-dsh-plugin').length === 1,
    built.registered.map((r) => String(r.options?.id)).join(','))

  // 服务被撤销（官方列热重载）→ 复位；再提供时 tab 必须重新出现
  // （verifier 五轮 P2-4：旧实现"置位后永不回退"导致重生后 tab 再也不出现）
  const clicksBefore = listenerCount('click')
  built.unprovideBetterSidebar()
  check('service unprovide: the old surfaces effect is disposed (no leaked click listener)',
    listenerCount('click') === clicksBefore - 1,
    `before=${clicksBefore} after=${listenerCount('click')}`)
  const again = built.provideBetterSidebar()
  check('service re-provide: the tab type comes back after an unprovide/re-provide cycle',
    again.tabs.registered.length === 2, `types=${again.tabs.registered.length}`)
  check('service re-provide: exactly one click listener again (no accumulation)',
    listenerCount('click') === clicksBefore, `clicks=${listenerCount('click')}`)
}

/* ---------------------------- 4b. probe cleanup: dispose 后事件不再注册任何东西 */
{
  const built = buildFacade({})
  entry.apply(built.facade)
  const before = built.registered.length
  for (const fn of built.effects) if (typeof fn === 'function') fn()
  const late = built.provideBetterSidebar() // 撤销之后再发 internal/service
  check('after dispose the probe registers nothing on a late service event',
    late.tabs.registered.length === 0 && built.registered.length === before,
    `types=${late.tabs.registered.length} registered=${built.registered.length}`)
}

/* ---------------------------------------------------- 5. inject 声明 */
check('inject declares only official services (no third-party hard gate)',
  Array.isArray(entry.inject) && entry.inject.length === 1 && entry.inject[0] === 'slots',
  JSON.stringify(entry.inject))

/* ---------------------------------------------------- 6. 打包产物与源码同步
 *
 * `plugin/client.js` 是**提交进仓库的构建产物**（GUI 直接加载它）。
 * 于是有一类静默失效：改了 `.tsx` 却忘了 `npm run build:client` —— 源码"看起来做了"、
 * GUI 里什么都没有，而 tsc 全绿（它只看源码）。这里用一个**只可能来自面板文案的标记串**
 * 断言产物里真的有它（2026-09-17 加参考资料面板时发现值得钉）。
 *
 * ⚠ **必须先把 `\uXXXX` 解码再找**：esbuild 默认 `charset:'ascii'`，中文在产物里是
 * 转义序列（`\u8BC4\u5BA1…`）。第一版我直接 `bundle.includes('评审是硬门')` —— 假红，
 * 而 ASCII 标记（`ks/materials/list`）却是绿的，看起来像"面板没打进去"，实则只是编码。
 *
 * ⚠⚠ **诚实边界（复核 b12 的 LOW-2 清点：下面这一类共 23 条）**：这些是"**文案在场**"断言
 * ——`bundle.includes(某句字)`。它们挡得住"这句字被删了/改了名"，**挡不住**任何
 * "字还在、渲染不出来"的形状（复核的变异 M13 已证）。**行为级**那一半由
 * `smoke-anchor-mark.mjs`（真渲染锚点标记）与下面的**产物↔源码一致**那节承担；
 * 这 23 条的定位就是**措辞纪律 + 产物新鲜度**（改了 `.tsx` 忘了重建 ⇒ 这里会红），
 * 别把它们读成"界面验过了"。
 */
{
  const raw = await readFile(join(pluginRoot, 'client.js'), 'utf8')
  const bundle = raw.replace(/\\u([0-9a-fA-F]{4})/g,
    (_, hex) => String.fromCharCode(parseInt(hex, 16)))
  for (const [what, marker] of [
    ['参考资料面板', '评审是硬门'],
    ['两个轴的标签（不是合成一个"可信度"）', '轴 A 来源可信度'],
    ['轴 B 标签', '轴 B 任务内效力'],
    ['逐份评审的动作（没有"全部通过"）', '读正文（评审前必看）'],
    ['会话绑定提示', '/materials use '],
    ['材料路由前缀', 'ks/materials/list'],
    // Track L 的**后果**必须在界面上说（批准会**自动写进法条库**，静默通过=用户不知情）
    ['批准后 Track L 结果的可见文案', '已自动入库为法条'],
    // ---- Phase D-3：自采入口（2026-09-17）----
    ['自采入口的按钮文案（改动必须同时改产物）', '自采一条'],
    // ⚠ 下面几条钉的是**纪律在界面上可见 + 接线真的存在**，不是"有个按钮"：
    // ① 采到的东西必须被说成"仅线索 / 不得单独支撑结论"（闸门之外的第二个把关点）
    // ② 抓取失败必须走**如实报告**那条路（不是红字异常）
    // ③ 界面只收网页正文（PDF 要走文件夹），这条在文案里说清
    ['自采的层级纪律（T3=仅线索）在界面上写明', 'T3=仅线索'],
    ['自采的承重纪律（不得单独支撑结论）在界面上写明', '不得单独支撑结论'],
    ['自采只收网页正文（PDF 走文件夹）在界面上写明',
      'PDF / 图片 / 压缩包请下载后放进上面的文件夹'],
    ['没采到时如实报告原因（不是假成功）', '没有采到：'],
    // 这条证明**新的 api 函数真的被打进产物**（只有 api.ts 里那一份措辞）
    ['client 侧自采接线（响应形状不认识时抛，不谎报"没采到"）',
      '自采响应异常：缺少 collected 字段'],
    // ---- Phase D-3b：产出入口（研究报告 / PPT，2026-09-17；§10.92 加 Word）----
    ['产出按钮：研究报告（三形态）', '生成研究报告（Markdown/HTML/Word）'],
    ['产出按钮：PPT', '生成 PPT'],
    // 同一份内容这句话必须在界面上说（否则用户会怀疑"报告和 PPT 是不是两套东西"）
    ['报告与 PPT **同源**这件事在界面上写明', '同一份内容'],
    // ---- Phase D-5b：结论草稿（§10.97）----
    ['产出按钮：结论草稿', '起草结论（草稿）'],
    // ⚠ 三句话少一句都会让"草稿"被读成"已批准的结论"：
    //   ① 它是**未批准**的；② 不得作为依据；③ 要用户点一下才填进结论框。
    ['草稿必须显眼标明「未批准草稿」', '未批准草稿'],
    ['草稿块明说「不得作为依据」', '不得作为依据'],
    ['草稿**不自动填**：要用户点「用这段填进结论框」', '用这段填进结论框'],
    ['引用警告必须显示（不许静默）', '引用警告'],
    ['"只吃已批准材料"在界面上写明', '只吃'],
    // ---- 引用锚点稳定性（§10.49）----
    ['锚点复算按钮（**贵**动作，只由用户点）', '复算锚点'],
    // ⚠ 两句**必须都在**：这是"需复算 ≠ 已坏"与"未验证 ≠ 有问题"这两个区分在界面上的落点，
    // 少一句就等于把"不确定"说成了"有问题"（本项目最忌讳的过度声称）
    ['"需复算"不等于已坏（措辞纪律在前端也守住）', '不代表已经坏了'],
    ['"未验证"不等于有问题（同上）', '不等于'],
  ]) {
    // ⚠ check 名里明写"交付产物"：这些**只**读 `client.js`（交付件），**不**能证明它新鲜
    //   ——新鲜度由本节最后那条"整份一致"断言负责（§10.99，复核 b26 的 F2）。
    check(`交付产物 client.js 含${what}（新鲜度见本节末尾的"整份一致"）`,
      bundle.includes(marker), marker)
  }

  // ⚠ **源码侧的接线断言**（独立复核 2026-09-17 报的覆盖缺口）：上面那组只证明
  // "提交进仓库的产物里有这些字符串"，它**抓不到**两件事：
  //   ① 有人把 `<KsMaterialsPanel … />` 从设置栏目里删了（源码不再挂载，产物却是旧的）；
  //   ② 忘了重新构建（源码改了、产物没跟上）。
  // ①由下面的源码断言覆盖；②由"产物里同时有挂载点与面板标记"间接覆盖
  // （少任何一半都说明两者不同步）。
  const settings = await readFile(join(pluginRoot, 'client', 'KsSettingsSection.tsx'), 'utf8')
  check('设置栏目源码里**挂载**了参考资料面板（不是只有产物里有）',
    settings.includes("import { KsMaterialsPanel }") && settings.includes('<KsMaterialsPanel'))
  check('设置栏目源码里有「参考资料」类目（用户在设置里找得到入口）',
    settings.includes('title="参考资料"'))
  check('产物里同时含面板标记与设置侧文案（源码↔产物同步的间接证据）',
    bundle.includes('评审是硬门') && bundle.includes('/materials use '))
  // ⚠ 产出侧同理：源码里那两个 handler 必须真的接在两个按钮上（否则按钮点了没反应，
  // 而产物里的文案仍然在——只查字符串抓不到"按钮没接 handler"）。
  const panel = await readFile(join(pluginRoot, 'client', 'KsMaterialsPanel.tsx'), 'utf8')
  check('产出按钮在源码里**接了 handler**（不是只有文案）',
    panel.includes('onClick={onExportReport}') && panel.includes('onClick={onExportSlides}'))
  check('产出用**两个不同**的路由函数（报告 ≠ PPT）',
    panel.includes('exportResearchReport(') && panel.includes('exportResearchSlides('))

  // ---- 静默降级护栏（2026-09-18 由**真机** e2e 抓出来的那两处，见 §10.53）----
  // 行为上的真正闸门是 `scripts/e2e-materials-panel.mjs` 的 C3（它要一个浏览器，
  // 没浏览器就 SKIP），所以这里补两条**廉价、离线**的护栏，挡"再写回去"：
  check('层级清单的诚实文案进了产物（失败不许静默）', bundle.includes('来源层级清单'))
  // ⚠ 负向断言：`.catch(() => [] …)` 把"清单没读到"变成"清单就是空的"——
  // 请求失败被渲染成"功能就是这样"。没有任何正当理由这么写。
  check('源码里没有"静默吞掉层级清单失败"的写法',
    !/fetchMaterialTiers\([^)]*\)\s*\.catch\(\(\)\s*=>\s*\[\]/.test(panel))
  // ⚠ 第二条静默路径（更隐蔽）：把失败记进局部变量、等 `Promise.all` 的 await 回来再落地——
  // 项目列表也失败时 `Promise.all` 先 reject，清单失败**永远说不出口**。
  // 真机上就是这么复现的：第一版"修好了"仍然不显示。所以清单必须自己 then/catch。
  // ⚠ 用 `\s*` 而不是 `\n`：仓库里的 TSX 是 CRLF，写死 `\n` 会**静默**匹配不上（本项目栽过）。
  check('层级清单请求**自己落地**成败（不搭项目列表的 Promise.all）',
    /fetchMaterialTiers\(ctl\.signal\)\s*\.then\(/.test(panel),
    '清单与项目列表必须各自结算')

  // ---- "结论没拿到"不许被渲染成"没有标记"（2026-09-18，INFO-3 同族，§10.57）----
  // 后端在单份材料算不出健康度时给 `health_error`（**不是**健康状态）。界面上没有它自己的
  // 分支的话，那种材料会**一个标记都没有**，读起来像"全都健康"——正是要防的静默。
  check('产物里含「锚点健康度算不出来」的提示（失败不许静默）',
    bundle.includes('锚点健康度算不出来'))
  // ⚠ 源码侧的判据跟着 §10.62 的重构改过：标记现在是**一个 switch**（不再是三串 `status === x &&`），
  // 穷尽性由 `assertNever` 在编译期保证 ⇒ 这里钉的是"那个 case 真的在源码里"。
  check('面板源码里 health_error 有独立 case（不是靠 why 兜底）',
    /case 'health_error':/.test(panel))
  check('面板源码里有穷尽性断言（新增 status 忘加分支应编译报错）',
    /assertNever\(/.test(panel) && /default:\s*\n?\s*return assertNever\(/.test(panel))
  // ⚠ `why` 的**接线**要有闸门（复核 b10 的 G4）：把面板里那段 `attention → why` 的映射退回
  // 写死 `''`，冒烟仍是 69/69 全绿——而界面上就再也说不出"为什么需要复算"。
  // ⚠ 判据从"钉右侧表达式原文"**放宽成结构级**（2026-09-18 复核 b12 的 LOW-1）：
  // 原先写死 `/why\[a\.material_id\] = a\.why/`，于是**语义等价**的重写（`String(a.why || '')`）
  // 会**假红**（复核的变异 M10 实测 RED 83/84）。假红的门禁会被训练成"忽略它"。
  // 现在只要求结构：① 真的遍历 `s.attention`；② 在循环里把 `a.why`（任何取自它的写法）
  // 写进某个以 material_id 为键的映射。**行为级**那条（渲染出来的是不是后端那个 why）
  // 由 `smoke-anchor-mark.mjs` 的真渲染用例负责（它用一个假字符串做对照）。
  check('面板源码把后端的 why 接进锚点映射（结构级：遍历 attention 且取自 a.why）',
    /for \(const a of s\.attention\)/.test(panel) && /why\[[^\]]+\]\s*=[^\n]*\ba\.why\b/.test(panel))
  // ⚠ 后端的 note 也不能是死状态（b11 的 INFO-1）：它要真的渲染出来。
  // 2026-09-18（复核 b12 的 LOW-1 + 变异 AA5）把判据**拆成两层**：
  //   · 这里（调用点）钉"那个 state 真的被交给了渲染入口"；
  //   · 行为（空串不出、非空原样出）由 `smoke-anchor-mark.mjs` **真渲染** `AnchorNoteLine` 验。
  // 为什么不再用 `/\{[^}\n]*anchorNote/`：把条件改成 `{false && …}` 时源码里**照样"读"到**
  // `anchorNote`（内层 `<p>{anchorNote}</p>` 还在）⇒ 那种永不上屏的改法能骗过它。
  check('面板源码把后端 anchorNote 交给 AnchorNoteLine 渲染（行为另有渲染级用例）',
    /<AnchorNoteLine\s+note=\{anchorNote\}/.test(panel))
  // ⚠ 禁用复算按钮的判据必须是那个**穷尽**函数（复核 b12 的 LOW-4b）：只在调用点写
  // `=== 'no_locators'` 时 `tsc` 管不到 ⇒ 后端新增状态时那一处**静默**。
  // 这条挡"函数还在、调用点又写回直接比较"；函数本身被删则由 anchor-mark 冒烟挡。
  check('面板源码用 statusDisablesReverify 判禁用（不直接比较状态名）',
    /statusDisablesReverify\(/.test(panel) && !/===\s*'no_locators'/.test(panel))
}

/* ---------------------------------------------------------------- 产物 ↔ 源码一致性
 * ⚠ 这一节是**复核 b11 的 LOW-3**（"闸门空"）逼出来的（2026-09-18）：
 *   上面那些断言只查**产物里有没有那句文案**。于是存在一个**假绿**形状——
 *   只改**产物**（把分支条件改成永不成立），`.tsx` 一个字节不动 ⇒ 文案还在、
 *   断言全绿，而**交付到界面上的标记再也不会出现**。
 *   同理反向：改了 `.tsx` 忘了重新构建 ⇒ 产物是旧的 ⇒ 也全绿。
 *   两种都是"门禁说没事、用户看不到东西"。
 *
 * 做法：**从源码现构建一份**（`KS_CLIENT_OUT` 指到临时文件，绝不覆盖被跟踪的 `client.js`），
 * 把"关键标记"在**两份产物**里各查一遍：
 *   · 交付的 `client.js` 必须有（那才是发出去的东西）；
 *   · 现构建的那份也必须有（源码真的这么写）；
 *   · 两者**必须一致**（不一致就是"产物陈旧或被改过"）。
 * ⚠ **诚实边界**：这仍是**字符串级**检查。它能挡住"删掉/改掉条件"与"忘了重建"，
 *   挡不住"条件后面偷偷加 `&& false`"——那种要**渲染级**用例（b11 用 jsdom 建过一份，
 *   但 jsdom 本仓未安装，收编它需要先决定依赖策略）。这条边界写在台账里，不在这里假装关掉。
 */
{
  const tmpOut = join(tmpdir(), `ks-client-fresh-${process.pid}-${Date.now()}.js`)
  process.env.KS_CLIENT_OUT = tmpOut
  // ⚠ 产物与调用方 cwd **无关**：`build-client.mjs` 现在显式固定 `absWorkingDir: root`
  //   （§10.99 实测：esbuild 会把相对 `absWorkingDir` 的模块注释写进产物 ——
  //   `// client/entry.ts` vs `// plugin/client/entry.ts` ⇒ 从仓库根调用会得到**多一层前缀**的
  //   产物，害得下面"整份一致"假红）。所以这里**不再需要** chdir，也不需要碰运气。
  await import(pathToFileURL(join(pluginRoot, 'scripts', 'build-client.mjs')).href)
  const freshRaw = await readFile(tmpOut, 'utf8')
  await rm(tmpOut, { force: true })
  const decode = (s) => s.replace(/\\u([0-9a-fA-F]{4})/g,
    (_, hex) => String.fromCharCode(parseInt(hex, 16)))
  const fresh = decode(freshRaw)
  const delivered = decode(await readFile(join(pluginRoot, 'client.js'), 'utf8'))

  // 关键标记：锚点标记 switch 的**三个 case**（条件，不是文案）+ 两条纪律文案
  const CRITICAL = [
    ['stale 分支的 case', 'case "stale":'],
    ['unknown 分支的 case', 'case "unknown":'],
    ['health_error 分支的 case', 'case "health_error":'],
    ['health_error 的提示文案', '锚点健康度算不出来'],
    ['"需复算 ≠ 已坏"的纪律文案', '不代表已经坏了'],
  ]
  for (const [what, marker] of CRITICAL) {
    const inDelivered = delivered.includes(marker)
    const inFresh = fresh.includes(marker)
    check(`交付产物里有${what}`, inDelivered, marker)
    check(`${what}在源码现构建里也在（产物↔源码一致）`, inFresh && inDelivered,
      `现构建含=${inFresh} 交付产物含=${inDelivered}`)
  }

  // ⚠ **整份一致性**（§10.99，修复核 b26 的 F2）：上面那 5 条只覆盖 5 个串，
  //   而前面那 23 条"文案在场"断言**只读交付产物** ⇒ "改了 `.tsx` 忘了重建"时它们**全绿**
  //   （b26 实测：改源码不重建 ⇒ 89/89 PASS，check 名里的"已重新构建"是夸大）。
  //   这里把**整份产物**与现构建逐字符对比（行尾归一化：仓库 autocrlf / 平台换行差异
  //   不该算"陈旧"），于是"忘重建"与"产物被手改"这两类都变成**一条真断言**。
  const norm = (s) => s.replace(/\r\n/g, '\n')
  const deliveredN = norm(await readFile(join(pluginRoot, 'client.js'), 'utf8'))
  const freshN = norm(freshRaw)
  const firstDiff = deliveredN === freshN
    ? -1
    : [...deliveredN].findIndex((ch, i) => ch !== freshN[i])
  check('⚠ 交付产物与「从源码现构建」**整份一致**'
    + '（改了 `client/` 却忘了 `build:client` ⇒ 这条红；复核 b26 的 F2）',
  deliveredN === freshN,
  `交付 ${deliveredN.length} 字符 / 现构建 ${freshN.length} 字符`
  + (deliveredN === freshN ? '' : ` / 首个差异位置 ${firstDiff}`))
}

/* ================================================================
 * 静态纪律：几条"写错不会报错、只在真机静默发作"的规则，钉成断言
 * （都在 2026-09-19 那一轮里真实踩过或有官方明文）
 * ================================================================ */

// ── 1. entry.ts **不许有 `export default`** ──
// 官方事故复盘 `docs/postmortem/0001-acp-default-export-drops-inject.md` 根因 #1：
// cordis Loader 的 `unwrapExports` 优先取 `.default` ⇒ **整个命名空间被丢掉**，
// `inject`/`name` 消失，插件在不含任何注入服务的 fiber 里跑，第一个 `ctx.xxx` 就抛
// "cannot get property … without inject"。而单元测试（绕过真实 Loader）**全绿**。
const entrySrc = await readFile(join(pluginRoot, 'client/entry.ts'), 'utf8')
check('entry.ts 没有 `export default`（有它 ⇒ Loader 丢掉 inject/name，真机才炸）',
  !/^\s*export\s+default\b/m.test(entrySrc),
  (entrySrc.match(/^\s*export\s+default\b.*$/m) ?? ['（无）'])[0].trim())

// ── 2. Button 的 variant 只许用官方那 4 档 ──
// `ui-primitives/src/Button.tsx`：`'primary' | 'ghost' | 'outline' | 'toolbar'`（默认 ghost）。
// 写成别的（如 `secondary`/`text`）**不会构建失败**（external，esbuild 不校验命名导出），
// 只是 `css[variant]` 取到 undefined ⇒ 静默没有填充。本插件 d.ts 里就一度写错成那两档。
const OFFICIAL_BUTTON_VARIANTS = ['primary', 'ghost', 'outline', 'toolbar']
const clientSrcFiles = (await readdir(join(pluginRoot, 'client'))).filter((f) => f.endsWith('.tsx') || f.endsWith('.ts'))
const variantUses = []
for (const f of clientSrcFiles) {
  const text = await readFile(join(pluginRoot, 'client', f), 'utf8')
  for (const m of text.matchAll(/variant="([a-zA-Z]+)"/g)) variantUses.push({ f, v: m[1] })
}
const badVariants = variantUses.filter((u) => !OFFICIAL_BUTTON_VARIANTS.includes(u.v))
check(`Button 的 variant 只用官方 4 档（${OFFICIAL_BUTTON_VARIANTS.join('/')}）`,
  badVariants.length === 0,
  badVariants.length === 0
    ? `${variantUses.length} 处用法全部合法`
    : badVariants.map((u) => `${u.f}:${u.v}`).join(', '))

// ── 3. 中性边框必须 0.5px；且不许"中性边框 + 阴影"配对 ──
// `docs/web-styling.md`：「Flat borders and separators that use a neutral --dsw-alias-border-*
// token draw at 0.5px」＋「Never pair a --dsw-alias-border-* border with an lv/elevation shadow」。
// 两者都是**视觉上很轻、肉眼验收不可靠**的规定，所以必须机器判。
const stylesSrc = await readFile(join(pluginRoot, 'client/ksGuideStyles.ts'), 'utf8')
const onePxNeutral = [...stylesSrc.matchAll(/[^-.\d]1px solid var\(--dsw-alias-border-[a-z0-9-]+\)/g)].map((m) => m[0].trim())
check('样式里没有 `1px solid var(--dsw-alias-border-*)`（中性边框统一 0.5px）',
  onePxNeutral.length === 0,
  onePxNeutral.length === 0 ? '0 处' : onePxNeutral.join(' | '))
// 逐条规则块检查"边框 + elevation 阴影"的非法配对。
// ⚠ 必须先**去掉 CSS 注释**再判：我那条"解释这个错误"的注释里就写着
//   `border:.5px solid var(--dsw-alias-border-l4)`，不去注释会**误报自己**（第一版真报了）。
const stylesNoComments = stylesSrc.replace(/\/\*[\s\S]*?\*\//g, '')
const styleBlocks = stylesNoComments.split('}').map((b) => b.trim()).filter((b) => b.includes('{'))
const illegalPair = styleBlocks.filter((b) => b.includes('box-shadow:var(--dsw-elevation')
  && /(^|[;{])border:\s*(?!0[;}\s])/.test(b)
  && b.includes('--dsw-alias-border-'))
check('没有"中性边框 + elevation 阴影"的非法配对（描边应由阴影自己画）',
  illegalPair.length === 0,
  illegalPair.length === 0 ? '0 处' : illegalPair.map((b) => b.slice(0, 60)).join(' | '))

// ── 4. 检索语法：逐例钉住（这是本页唯一的真逻辑）──
// 业主原话：「多个关键词用 + 号链接，然后用 - 号连接关键词那就是屏蔽这个词，比如 安全+半导体-冶金」
// ⚠ 关键一条：`GB 30871-2022` 里的连字符**必须留在词里**（标准号本来就有 `-`）。
// ⚠ 这里**另建临时目录**：本冒烟的 `stubDir` 在产物比对那一节结束时已被删掉
//   （第一版写进 stubDir ⇒ ENOENT，冒烟直接崩在最后一段）。
const syntaxDir = await mkdtemp(join(tmpdir(), 'ks-syntax-'))
const syntaxEntry = join(syntaxDir, 'syntax-entry.mjs')
await writeFile(syntaxEntry,
  `export { parseKsQuery, describeKsQuery } from ${JSON.stringify(join(pluginRoot, 'client/ksSearchSyntax.ts'))}\n`, 'utf8')
const syntaxOut = join(syntaxDir, 'syntax-out.mjs')
await build({ entryPoints: [syntaxEntry], bundle: true, platform: 'node', format: 'esm', outfile: syntaxOut })
const { parseKsQuery, describeKsQuery } = await import(pathToFileURL(syntaxOut).href)
const CASES = [
  // [输入, 必含, 屏蔽]
  ['安全+半导体-冶金', ['安全', '半导体'], ['冶金']],
  ['安全＋半导体－冶金', ['安全', '半导体'], ['冶金']],            // 全角（中文输入法常态）
  ['-冶金', [], ['冶金']],                                        // 只有屏蔽
  ['', [], []],                                                   // 空串不抛
  ['安全++半导体', ['安全', '半导体'], []],                        // 连续分隔符
  ['安全+半导体-冶金-粉尘', ['安全', '半导体'], ['冶金', '粉尘']],  // 多个屏蔽
  ['安全+安全', ['安全'], []],                                     // 去重
  ['GB 30871-2022', ['GB 30871-2022'], []],                       // ⚠ 标准号里的 - 不是屏蔽
  ['GB/T 50016-2014', ['GB/T 50016-2014'], []],                   // 同上（带斜杠）
  ['  安全  ', ['安全'], []],                                      // 首尾空白
]
let syntaxBad = 0
for (const [input, wantIn, wantEx] of CASES) {
  const got = parseKsQuery(input)
  const ok = JSON.stringify(got.include) === JSON.stringify(wantIn)
    && JSON.stringify(got.exclude) === JSON.stringify(wantEx)
  if (!ok) syntaxBad++
  check(`检索语法 ${JSON.stringify(input)} ⇒ 含${JSON.stringify(wantIn)} 排除${JSON.stringify(wantEx)}`,
    ok, `实得 含${JSON.stringify(got.include)} 排除${JSON.stringify(got.exclude)}`)
}
check('检索语法：describeKsQuery 给出人话回显（UI 当场显示，省得用户猜）',
  describeKsQuery(parseKsQuery('安全+半导体-冶金')) === '含 「安全」「半导体」；排除 「冶金」',
  describeKsQuery(parseKsQuery('安全+半导体-冶金')))

// ── 5. 13 条需求的"在场"钉子（删掉任一条 ⇒ 这条红）──
// ⚠ 只用**一定是字符串字面量**的标记。像 `>文件<` 这种依赖 JSX 产物形状的标记很脆
//   （esbuild 产出 `children: "文件"`，不是 HTML 文本节点），不拿来当钉子。
// ⚠ `delivered` 是上面那个块的**块级**变量，这里够不着 ⇒ 自己读一次并按同样方式解码。
const decodeEscapes = (s) => s.replace(/\\u([0-9a-fA-F]{4})/g,
  (_, hex) => String.fromCharCode(parseInt(hex, 16)))
const deliveredText = decodeEscapes(await readFile(join(pluginRoot, 'client.js'), 'utf8'))
const SPEC_STRINGS = [
  ['批量条：取消选择', '取消选择'],
  ['批量条：批量打标签', '批量打标签'],
  ['批量条：移动到目录', '移动到目录'],
  ['批量条：批量删除', '批量删除'],
  ['行内常驻：＋标签', '＋标签'],
  ['详情：发布日期', '发布日期'],
  ['详情：生效日期', '生效日期'],
  ['详情：废止日期', '废止日期'],
  ['详情：所属目录', '所属目录'],
  ['一个新建按钮', '＋ 新建'],
  ['标签可跨文件夹（视图说明）', '跨知识库文件夹定义'],
  ['标签覆盖范围回显', '覆盖：'],
  ['全选', '取消全选'],
]
for (const [what, marker] of SPEC_STRINGS) {
  check(`13 条需求在场：${what}`, deliveredText.includes(marker), marker)
}

// ── 6. 主题债务棘轮：老面板里的"写死颜色"只许减、不许增 ──
// 背景：业主明确要「深色浅色两套配色」。新 UI（`ksGuideStyles.ts` + `KsKnowledgePage.tsx`）
// **只走活的 `--dsw-alias-*` token**，所以天然跟着主题变；但**老面板**里还有一批写死的
// 十六进制颜色 —— 深色主题下它们不会跟着变。
//
// 为什么**现在不改**（写清楚，免得后人以为这是忘了）：
//   ① 约 130 处里有 ~110 处需要**语义判断**（哪个是危险红、哪个是警告黄）；
//   ② 其中还有 `#c0392b55` 这种**带 alpha** 的，换成 token 会**丢掉透明度**（没有对应 token），
//      盲改会让边框从半透明变实心 —— 那是把深色改得更糟；
//   ③ 这些老面板**本来就在交互重设计里等着被重建**（见 `docs/INTERACTION-DESIGN.md`）；
//   ④ 最要紧的：**我看不到像素**，改错了没人能立刻发现。
// ⇒ 所以这一轮只做**棘轮**：数值不许涨。要减就顺手减（重建面板时自然就没了）。
const THEME_DEBT_BASELINE = {
  'KsBookmarksTab.tsx': 3,
  'KsChannelsPanel.tsx': 3,
  'KsEvidenceTab.tsx': 12,
  'KsFilesTab.tsx': 1,
  'KsIngestPanel.tsx': 22,
  'KsMaterialsPanel.tsx': 5,
  'KsReportPanel.tsx': 16,
  'KsScopeChip.tsx': 5,
  'KsSettingsSection.tsx': 48,
}
const BARE_COLOR = /#[0-9a-fA-F]{3,8}\b|rgba?\(|hsla?\(/
const themeDebt = {}
for (const f of clientSrcFiles) {
  const text = await readFile(join(pluginRoot, 'client', f), 'utf8')
  let n = 0
  for (const line of text.split(/\r?\n/)) {
    if (BARE_COLOR.test(line) && !line.includes('var(--dsw-')) n++
  }
  if (n > 0) themeDebt[f] = n
}
const grew = Object.keys(themeDebt).filter((f) => themeDebt[f] > (THEME_DEBT_BASELINE[f] ?? 0))
const shrank = Object.keys(THEME_DEBT_BASELINE).filter((f) => (themeDebt[f] ?? 0) < THEME_DEBT_BASELINE[f])
const debtTotal = Object.values(themeDebt).reduce((a, b) => a + b, 0)
check('主题债务棘轮：写死颜色的行数**不许增加**（只许减）',
  grew.length === 0,
  grew.length === 0
    ? `总 ${debtTotal} 行（基线 115）${shrank.length > 0 ? `；已减少：${shrank.join(', ')}` : ''}`
    : grew.map((f) => `${f}: ${THEME_DEBT_BASELINE[f] ?? 0} → ${themeDebt[f]}`).join(' | '))

const failed = results.filter((r) => !r.ok)
console.log(`\n== client-entry smoke ${failed.length === 0 ? 'PASS' : 'FAIL'} `
  + `(${results.length - failed.length}/${results.length}) ==`)
process.exit(failed.length === 0 ? 0 : 1)
