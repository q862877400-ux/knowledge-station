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
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
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
await writeFile(entryPath,
  "export { apply, inject } from './client/entry.ts'\n", 'utf8')
try {
  await build({
    entryPoints: [entryPath], bundle: true, platform: 'node', format: 'esm',
    outfile: outPath, absWorkingDir: pluginRoot, jsx: 'automatic',
    external: ['react', 'react-dom'],
    alias: { 'pdfjs-dist': pdfStubPath },
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
  check('stage 1: exactly one tab TYPE registered (ks-evidence)',
    tabs.registered.length === 1 && tabs.registered[0]?.kind === 'ks-evidence',
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
  // ── 侧栏「开始页」手动入口（官方 guide 胶囊）──
  // 官方 GuideBody 把每个类型贡献的胶囊按 `order` 升序排；实测在用的值：
  // ui-sidebar-files = 10、ui-sidebar-terminal = 20（新建终端）。故 30 = 紧跟在它下面。
  const guide = tabs.registered[0]?.guide
  check('stage 1: the type contributes exactly one guide entry (start-page capsule)',
    Array.isArray(guide) && guide.length === 1,
    JSON.stringify(guide?.map?.((g) => g.id)))
  check('stage 1: the guide entry sorts directly BELOW 新建终端 (files 10 < terminal 20 < ours 30)',
    guide?.[0]?.order === 30 && guide[0].order > 20 && guide[0].order > 10,
    `order=${guide?.[0]?.order}`)
  check('stage 1: the guide entry has a unique id, live title/description and an icon component',
    guide?.[0]?.id === 'pdf'
    && typeof guide[0].title === 'function' && guide[0].title().length > 0
    && typeof guide[0].description === 'function' && guide[0].description().length > 0
    && typeof guide[0].icon === 'function',
    `id=${guide?.[0]?.id} title=${guide?.[0]?.title?.()} icon=${typeof guide?.[0]?.icon}`)
  check('stage 1: the guide capsule and the tab chip use the SAME name (one thing, one label)',
    guide?.[0]?.title?.() === tabs.registered[0]?.title?.('dsh-resource://ks-evidence'),
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
    late.tabs.registered.length === 1 && built.injected.includes('settings.section'),
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
    again.tabs.registered.length === 1, `types=${again.tabs.registered.length}`)
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
    // ---- Phase D-3b：产出入口（研究报告 / PPT，2026-09-17）----
    ['产出按钮：研究报告', '生成研究报告（Markdown/HTML）'],
    ['产出按钮：PPT', '生成 PPT'],
    // 同一份内容这句话必须在界面上说（否则用户会怀疑"报告和 PPT 是不是两套东西"）
    ['报告与 PPT **同源**这件事在界面上写明', '同一份内容'],
    ['引用警告必须显示（不许静默）', '引用警告'],
    ['"只吃已批准材料"在界面上写明', '只吃'],
  ]) {
    check(`client.js 已重新构建并含${what}`, bundle.includes(marker), marker)
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
}

const failed = results.filter((r) => !r.ok)
console.log(`\n== client-entry smoke ${failed.length === 0 ? 'PASS' : 'FAIL'} `
  + `(${results.length - failed.length}/${results.length}) ==`)
process.exit(failed.length === 0 ? 0 : 1)
